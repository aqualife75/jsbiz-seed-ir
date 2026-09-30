#!/usr/bin/env python3
"""Deduplicate identical PPTX media in place, without altering image bytes.

Only ppt/media entries with the same extension AND identical bytes are merged.
Untouched ZIP members retain their uncompressed bytes. Affected XML is patched
at the relevant attribute/element spans instead of being reserialized.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import html
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import stat
import tempfile
import time
from urllib.parse import quote, unquote, urlsplit, urlunsplit
import xml.etree.ElementTree as ET
import zipfile


REL_NS = 'http://schemas.openxmlformats.org/package/2006/relationships'
CT_NS = 'http://schemas.openxmlformats.org/package/2006/content-types'
ATTR = re.compile(rb'''(?P<name>[A-Za-z_][\w.:-]*)\s*=\s*(?P<quote>["'])(?P<value>.*?)(?P=quote)''', re.S)
REL_TAG = re.compile(rb'<(?:[A-Za-z_][\w.-]*:)?Relationship\b(?:[^>"\']|"[^"]*"|\'[^\']*\')*>', re.S)
OVERRIDE_TAG = re.compile(rb'<(?:[A-Za-z_][\w.-]*:)?Override\b(?:[^>"\']|"[^"]*"|\'[^\']*\')*(?:/>|>\s*</(?:[A-Za-z_][\w.-]*:)?Override\s*>)', re.S)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def xml_attr(tag: bytes, name: str):
    hits = [m for m in ATTR.finditer(tag) if m.group('name').decode('ascii') == name]
    if len(hits) != 1:
        raise ValueError(f'Expected one {name} attribute in XML element')
    return hits[0]


def attr_value(match) -> str:
    return html.unescape(match.group('value').decode('utf-8'))


def relationship_base(rels_name: str) -> str:
    if rels_name == '_rels/.rels':
        return ''
    path = PurePosixPath(rels_name)
    if path.parent.name != '_rels' or not path.name.endswith('.rels'):
        raise ValueError(f'Unexpected relationships part name: {rels_name}')
    base = str(path.parent.parent)
    return '' if base == '.' else base


def resolve_target(base: str, target: str) -> str:
    uri = urlsplit(target)
    if uri.scheme or uri.netloc:
        raise ValueError(f'Internal relationship uses an external URI: {target}')
    decoded = unquote(uri.path)
    if '\\' in decoded:
        raise ValueError(f'Backslash in OPC relationship target: {target}')
    joined = decoded.lstrip('/') if decoded.startswith('/') else posixpath.join(base, decoded)
    normalized = posixpath.normpath(joined)
    if normalized in ('.', '..') or normalized.startswith('../'):
        raise ValueError(f'Relationship escapes package: {target}')
    return normalized


def replacement_target(base: str, old_target: str, survivor: str) -> str:
    uri = urlsplit(old_target)
    relative = posixpath.relpath(survivor, base or '.')
    encoded = quote(relative, safe="/!$&'()*+,-.:;=@_~")
    return urlunsplit(('', '', encoded, uri.query, uri.fragment))


def read_relationships(name: str, payload: bytes):
    root = ET.fromstring(payload)
    if root.tag != f'{{{REL_NS}}}Relationships':
        raise ValueError(f'Unexpected relationship namespace in {name}')
    result = []
    seen = set()
    for element in root:
        if element.tag != f'{{{REL_NS}}}Relationship':
            raise ValueError(f'Unexpected relationship child in {name}')
        rid = element.attrib['Id']
        if rid in seen:
            raise ValueError(f'Duplicate relationship Id {rid} in {name}')
        seen.add(rid)
        result.append(element.attrib)
    return result


def patch_relationships(name: str, payload: bytes, removed: dict[str, str]):
    rels = read_relationships(name, payload)
    base = relationship_base(name)
    changes = {}
    for rel in rels:
        if rel.get('TargetMode', '').lower() == 'external':
            continue
        resolved = resolve_target(base, rel['Target'])
        if resolved in removed:
            changes[rel['Id']] = replacement_target(base, rel['Target'], removed[resolved])
    if not changes:
        return payload, 0
    # The narrow byte patch deliberately rejects unsupported XML encodings.
    payload.decode('utf-8-sig')
    matches = list(REL_TAG.finditer(payload))
    if len(matches) != len(rels):
        raise ValueError(f'Cannot safely locate XML elements for {name}; file unchanged')
    patches = []
    matched = set()
    expected = {r['Id']: r for r in rels}
    for match in matches:
        tag = match.group(0)
        rid = attr_value(xml_attr(tag, 'Id'))
        target_match = xml_attr(tag, 'Target')
        if rid not in expected or attr_value(target_match) != expected[rid]['Target']:
            raise ValueError(f'XML patch semantic mismatch in {name}')
        if rid in changes:
            if rid in matched:
                raise ValueError(f'Duplicate patch target in {name}')
            matched.add(rid)
            value = html.escape(changes[rid], quote=True).encode('utf-8')
            patches.append((match.start() + target_match.start('value'), match.start() + target_match.end('value'), value))
    if matched != set(changes):
        raise ValueError(f'Not all relationship edits located in {name}')
    for start, end, value in reversed(patches):
        payload = payload[:start] + value + payload[end:]
    actual = {r['Id']: r for r in read_relationships(name, payload)}
    for rid, rel in expected.items():
        after = dict(rel)
        if rid in changes:
            after['Target'] = changes[rid]
        if actual[rid] != after:
            raise ValueError(f'Unexpected relationship mutation in {name}')
    return payload, len(changes)


def patch_content_types(payload: bytes, removed: dict[str, str]):
    root = ET.fromstring(payload)
    if root.tag != f'{{{CT_NS}}}Types':
        raise ValueError('Unexpected content-types namespace')
    doomed = {el.attrib['PartName'] for el in root if el.tag == f'{{{CT_NS}}}Override' and unquote(el.attrib['PartName']).lstrip('/') in removed}
    if not doomed:
        return payload, 0
    payload.decode('utf-8-sig')
    matches = list(OVERRIDE_TAG.finditer(payload))
    patches = []
    matched = []
    for match in matches:
        part = attr_value(xml_attr(match.group(0), 'PartName'))
        if part in doomed:
            patches.append((match.start(), match.end()))
            matched.append(part)
    expected_count = sum(el.tag == f'{{{CT_NS}}}Override' and el.attrib['PartName'] in doomed for el in root)
    if len(matched) != expected_count or set(matched) != doomed:
        raise ValueError('Cannot safely locate content-type overrides; file unchanged')
    for start, end in reversed(patches):
        payload = payload[:start] + payload[end:]
    def element_without_tail(el):
        el = copy.deepcopy(el)
        el.tail = None
        return ET.tostring(el)
    expected = [element_without_tail(el) for el in root if not (el.tag == f'{{{CT_NS}}}Override' and el.attrib['PartName'] in doomed)]
    actual = [element_without_tail(el) for el in ET.fromstring(payload)]
    if actual != expected:
        raise ValueError('Unexpected content-types mutation')
    return payload, expected_count


def validate_relationships(members: dict[str, bytes]) -> int:
    count = 0
    for name, payload in members.items():
        if not name.endswith('.rels'):
            continue
        base = relationship_base(name)
        for rel in read_relationships(name, payload):
            if rel.get('TargetMode', '').lower() == 'external':
                continue
            target = resolve_target(base, rel['Target'])
            if target not in members:
                raise ValueError(f'Unresolved internal relationship: {name} -> {rel["Target"]}')
            count += 1
    return count


def deduplicate_pptx_media(path: str | Path) -> dict:
    path = Path(path).resolve(strict=True)
    if path.suffix.lower() != '.pptx':
        raise ValueError('Input must be a .pptx file')
    before_hash = file_digest(path)
    before_size = path.stat().st_size
    mode = stat.S_IMODE(path.stat().st_mode)
    with zipfile.ZipFile(path, 'r') as archive:
        if archive.testzip() is not None:
            raise ValueError('Input ZIP CRC validation failed')
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if len(names) != len(set(names)):
            raise ValueError('Duplicate ZIP member names are not supported')
        members = {info.filename: archive.read(info) for info in infos}
        comment = archive.comment
    if file_digest(path) != before_hash:
        raise RuntimeError('Input changed during read; no output written')
    if '[Content_Types].xml' not in members:
        raise ValueError('Missing [Content_Types].xml')
    media = [name for name in names if name.startswith('ppt/media/') and not name.endswith('/')]
    groups = {}
    removed = {}
    for name in media:
        payload = members[name]
        key = (PurePosixPath(name).suffix, digest(payload))
        candidates = groups.setdefault(key, [])
        survivor = next((other for other in candidates if members[other] == payload), None)
        if survivor is None:
            candidates.append(name)
        else:
            removed[name] = survivor
    relationships_before = validate_relationships(members)
    result = {
        'input': str(path),
        'changed': bool(removed),
        'media_count_before': len(media),
        'media_count_after': len(media) - len(removed),
        'media_bytes_before': sum(len(members[n]) for n in media),
        'media_bytes_after': sum(len(members[n]) for n in media if n not in removed),
        'file_bytes_before': before_size,
        'file_bytes_after': before_size,
        'sha256_before': before_hash,
        'sha256_after': before_hash,
        'removed_to_survivor': removed,
        'rewritten_relationships': 0,
        'removed_content_type_overrides': 0,
        'internal_relationships_validated': relationships_before,
        'preserved_media_identical': True,
        'untouched_members_identical': True,
        'changed_members': [],
    }
    if not removed:
        return result
    updated = {}
    for name, payload in members.items():
        if name in removed:
            continue
        after = payload
        if name.endswith('.rels'):
            after, count = patch_relationships(name, payload, removed)
            result['rewritten_relationships'] += count
        elif name == '[Content_Types].xml':
            after, count = patch_content_types(payload, removed)
            result['removed_content_type_overrides'] += count
        updated[name] = after
        if after != payload:
            result['changed_members'].append(name)
    relationships_after = validate_relationships(updated)
    if relationships_after != relationships_before:
        raise ValueError('Relationship count changed unexpectedly')
    for name in media:
        if name not in removed and updated[name] != members[name]:
            raise ValueError(f'Image bytes changed: {name}')
    fd, temporary = tempfile.mkstemp(prefix=f'.{path.stem}.media-dedup-', suffix='.pptx', dir=path.parent)
    os.close(fd)
    temporary_path = Path(temporary)
    try:
        with zipfile.ZipFile(temporary_path, 'w') as output:
            output.comment = comment
            for info in infos:
                if info.filename in updated:
                    output.writestr(copy.copy(info), updated[info.filename])
        with zipfile.ZipFile(temporary_path, 'r') as check:
            if check.testzip() is not None:
                raise ValueError('Output ZIP CRC validation failed')
            if set(check.namelist()) != set(updated):
                raise ValueError('Unexpected ZIP member set after write')
            if check.comment != comment:
                raise ValueError('Archive comment changed')
            reread = {name: check.read(name) for name in check.namelist()}
            if reread != updated:
                raise ValueError('Output member bytes changed during ZIP write')
            validate_relationships(reread)
        os.chmod(temporary_path, mode)
        result['file_bytes_after'] = temporary_path.stat().st_size
        result['sha256_after'] = file_digest(temporary_path)
        # Windows sync/antivirus readers can hold a brief delete-sharing lock.
        # Retry only that final atomic operation, checking for concurrent edits
        # every time; do not use a delete-and-rename fallback.
        for attempt in range(6):
            if file_digest(path) != before_hash:
                raise RuntimeError('Input changed before replacement; original not overwritten')
            try:
                os.replace(temporary_path, path)
                result['atomic_replace_attempts'] = attempt + 1
                break
            except PermissionError as exc:
                if getattr(exc, 'winerror', None) not in (5, 32, 33) or attempt == 5:
                    raise
                time.sleep(0.2 * (2 ** attempt))
    finally:
        if temporary_path.exists():
            temporary_path.unlink()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pptx', help='PPTX file to update in place after validation')
    parser.add_argument('--report', help='Optional JSON report path')
    args = parser.parse_args()
    if args.report and Path(args.report).resolve() == Path(args.pptx).resolve():
        raise ValueError('Report path must differ from input')
    result = deduplicate_pptx_media(args.pptx)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.report:
        report = Path(args.report)
        report.write_text(text + '\n', encoding='utf-8')
    print(text)


if __name__ == '__main__':
    main()
