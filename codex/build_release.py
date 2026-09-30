#!/usr/bin/env python3
"""Build a ready-to-open learner ZIP and an optional developer distribution."""
import argparse
import base64
import hashlib
import html
import io
import json
import re
from pathlib import Path
import tomllib
import unicodedata
import zipfile
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parent
FOLDERS={'plugins','custom-agents','docs','examples','tests','learner-template'}
FILES={'README.md','사용설명서.html','NOTICE.md','requirements.txt','install.py',
       'install-windows.cmd','install-macos.sh','build_release.py','.gitignore'}
EXTENSIONS={'.py','.mjs','.js','.md','.json','.toml','.html','.ps1','.txt','.cmd','.sh','.jpg','.jpeg','.png','.pptx','.pdf'}
LEARNER_ROOT='정석biz-IR-프로젝트'
SKILL_PREFIX='plugins/seed-ir/skills/seed-ir/'
LEARNER_DOCS={'docs/advanced-guide.html','docs/beginner-start.md','docs/validation-report.md','docs/visual-retrospective.md'}
PUBLIC_DOCS=LEARNER_DOCS|{'docs/architecture.md'}
SAMPLE_TEXT={'make_demo.py','demo-input.md','demo-evidence.json','demo-deck.json',
             'demo-section-briefs.json','demo-storyboard.html','demo-master-storyboard.html',
             'demo-validation.json','demo-viewer.html','visual-design-guide.html','sample-assets.json'}
BINARY_EXTENSIONS={'.jpg','.jpeg','.png','.pptx','.pdf'}
# One-way fingerprints allow release checks without publishing private identifiers.
PRIVATE_TOKEN_DIGESTS={
    '49af9dff333677c44f0492f867a9835ca84ee9dad025ca6797c33263443e72c0',
    '19712d5ea958dc9f971cb4641a269b833d41fc7eabd45be69827c2b80542378e',
    '9d7959f07171e5b353a5041e319ef9c944d198501875c9fe7dec6205d4a5046e',
}
PRIVATE_TOKEN_LENGTHS={3,6,68}
PRIVATE_FILE_DIGESTS={
    '054d59bd082d3d1257ac23136dcf21b575206eee9380f921f27e396f77461e8e',
    '1dcdd1521ded21db9eeeb12beaae1617c4db7ade71eb695ad80f834425a74724',
    '1eb106b76f4decb1520ef1ce41e7612cd463dccfbe6f90570a71a00e319c4817',
    '204a3ccf41b889b8112f24e6001aaf216d7e2b700297a5bd8bdcf0513dbaba61',
    '31e261a95b62e6945459970a9c7a5851afc8ebe78f85fa58c82335640957956a',
    '33ea952f399d8b9c050a4dc55b4ba0e5e4433f2d1004a05af202fc22814f33f2',
    '41c447b3ab3e87dc567e2ccd0d1e98ae21c18661a115ec42016c7b9a34a18d0b',
    '5b8b1671dc098bbe8d04be63bf63e0ab67f387ef0ce6e30ec74a6e12eeda5d1c',
    '73e95e2b937cc12c765101ca18cf6caa7c1c62f7218f7c0b063f58112174b708',
    '746e3123b50c985ac9d132b42c11a6cd78abd11770c54080320512901016a05d',
    '8a66e8b569435201975a696ce3bf46ca1414b08e1f05e3ae5fa727511e8a26dc',
    '8a704035d03321c6c3f601e3b236a742e0457da19cc340c6f273574f7fa6f3b9',
    '8ca8d6354a44d27ae649144c382a553ec633343c4b8513380c7dad490c2b8926',
    '93f4cfd9d9e01dc0310e831ebac32ac91f8e908749d9c6959453c7a4e9fa255a',
    '9b231a2798af462911f384db46285ddd8d4659611075052bc663199b74845c40',
    'a9ac7d6dd8cfec19daf38196b21c7cf009be24b4e3e9c1c69719ec527f67244e',
    'b44c3b3508099414dc61976c6ac47e967e6cb19dbaff4e2609be8200c95b710f',
    'b7cf362c99fc141387549586a8c22515332f77270a798c7f4edb58daba33f1f3',
    'bbeb227c02540f6dba0844b853cbfff10ebe5e0ab413dd86b73401068bfc83dc',
    'c7b83d287b148487c466959b3bfd9b5bd26ce83eae59dc67f250d0fc300e7361',
    'caa7af7774c722d967a9c93e50c560577ca3cb39f75491b85fc87899213ba9a8',
    'cb7701370cdcdf6bb2ab23e6bd6f5dc6ce16ea2e45af75651c7cb00a3e80cc4d',
    'd08dc8bb28d2e89e7dd373bfdd48aaa8e7790aba4d89556897e316475c17cc34',
    'e13c70c1d8c5da9c3b8b011f0bd2b02fa7605abfa0dfc6c2ca4b0fdb52318527',
    'e271835f6126cff1014ca0aa64b11eb2e79e36ce5762337cf6e9936684879b65',
    'e3bf7a3178d535be01cae1ec47a9822a90240fe236b563cd6c2f3191c412db91',
    'eb3d5238a79eedc9b41ca0380e49196dea2ad70e4a9e07d90b79a985aef238fc',
    'eeee1426ba056cbab597173a32f3a171d2a7ea440a8cab47bbeae4d751ec1ff3',
}


def audit_text(value, label):
    """Inspect visible and escaped text, including OOXML text split across runs."""
    value=unicodedata.normalize('NFKC',html.unescape(value))
    try:
        parsed=json.loads(value)
        value+='\n'+json.dumps(parsed,ensure_ascii=False)
    except (ValueError,TypeError): pass
    if value.lstrip().startswith('<'):
        try: value+='\n'+''.join(ET.fromstring(value).itertext())
        except ET.ParseError: pass
    if re.search(r'(?i)[a-z]:[\\/](?:Users|[^\\/\n]*Dropbox)[\\/]',value):
        raise ValueError('Private absolute path in release: '+label)
    tokens=set(re.findall(r'[\w-]+|[a-z]+|[가-힣]+',value.casefold()))
    tokens.update(re.findall(r'[a-z]+|[가-힣]+',value.casefold()))
    candidates=set(tokens)
    for token in tokens:
        for size in PRIVATE_TOKEN_LENGTHS:
            candidates.update(token[i:i+size] for i in range(max(0,len(token)-size+1)))
    if any(hashlib.sha256(token.encode()).hexdigest() in PRIVATE_TOKEN_DIGESTS for token in candidates):
        raise ValueError('Private identifier in release: '+label)


def audit_payload(data, label, *, depth=0, text_expected=False):
    """Fail closed on nested private content; no filenames or IDs are echoed."""
    if depth>2: raise ValueError('Unexpected nested archive: '+label)
    if hashlib.sha256(data).hexdigest() in PRIVATE_FILE_DIGESTS:
        raise ValueError('Private asset in release: '+label)
    if data.startswith(b'PK\x03\x04'):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for member in archive.infolist():
                if member.file_size>64*1024*1024: raise ValueError('Oversized archive member: '+label)
                audit_text(member.filename,label)
                if not member.is_dir():
                    expected=Path(member.filename).suffix.lower() in {'.xml','.rels','.json','.txt','.md','.html'}
                    audit_payload(archive.read(member),label+' (archive content)',depth=depth+1,text_expected=expected)
    elif data.startswith(b'%PDF-'):
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise ValueError('pypdf is required to audit sample PDFs') from exc
        reader=PdfReader(io.BytesIO(data))
        audit_text(str(reader.metadata or {}),label+' (PDF metadata)')
        for page in reader.pages:
            audit_text(page.extract_text() or '',label+' (PDF text)')
            for image in page.images:
                if hashlib.sha256(image.data).hexdigest() in PRIVATE_FILE_DIGESTS:
                    raise ValueError('Private asset in PDF: '+label)
    else:
        # XML permits UTF-16 and declared encodings; inspect decoded attributes
        # and runs, never silently discard text on UTF-8 decoding failure.
        value=None
        if data.lstrip().startswith(b'<') or data.startswith((b'\xff\xfe',b'\xfe\xff',b'\x00<')):
            try: value=ET.tostring(ET.fromstring(data),encoding='unicode')
            except (ET.ParseError,ValueError): pass
        if value is None:
            encoding='utf-32' if data.startswith((b'\xff\xfe\x00\x00',b'\x00\x00\xfe\xff')) else 'utf-16' if data.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig'
            try: value=data.decode(encoding)
            except UnicodeDecodeError:
                if text_expected or Path(label).suffix.lower() in {'.xml','.rels','.json','.txt','.md','.html','.py','.mjs','.js','.toml'}:
                    raise ValueError('Undecodable text in release: '+label)
                return
        for encoded in re.findall(r'data:image/[^;]+;base64,([A-Za-z0-9+/=]+)',value):
            audit_payload(base64.b64decode(encoded,validate=True),label+' (embedded image)',depth=depth+1)
        value=re.sub(r'data:image/[^;]+;base64,[A-Za-z0-9+/=]+','[embedded image inspected]',value)
        audit_text(value,label)


def approved_sample_files():
    manifest_path=ROOT/'examples/sample-assets.json'
    if not manifest_path.is_file(): raise ValueError('Approved fictional sample manifest is missing')
    data=json.loads(manifest_path.read_text('utf-8-sig'))
    if data.get('sample_id')!='glucopic-fictional': raise ValueError('Only the approved fictional sample is distributable')
    approved={}
    for item in [*data.get('assets',[]),*data.get('artifacts',[])]:
        name=item.get('path','').replace('\\','/')
        p=Path(name)
        if p.is_absolute() or '..' in p.parts or not name.startswith('examples/') or name in approved:
            raise ValueError('Invalid or duplicate sample manifest path')
        if not re.fullmatch(r'[0-9a-f]{64}',item.get('sha256','')):
            raise ValueError('Sample manifest needs SHA256: '+name)
        approved[name]=item['sha256']
    return approved


def checked_files():
    """Select maintained source and fictional fixtures, never a live project."""
    selected=[]
    approved=approved_sample_files()
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file(): continue
        rel=p.relative_to(ROOT)
        if '__pycache__' in rel.parts or p.suffix=='.pyc': continue
        if rel.parts[0]=='docs' and rel.as_posix() not in PUBLIC_DOCS: continue
        if rel.parts[0]=='examples' and p.suffix.lower() not in BINARY_EXTENSIONS and rel.as_posix() not in {'examples/'+name for name in SAMPLE_TEXT}:
            raise ValueError('Unapproved example file: '+rel.as_posix())
        if len(rel.parts)==1 and p.name in FILES: selected.append(p)
        elif rel.parts[0] in FOLDERS and p.suffix.lower() in EXTENSIONS: selected.append(p)
    forbidden=('input','자료넣는곳','결과물','work','data','output','.venv','node_modules','build-analysis')
    for p in selected:
        rel=p.relative_to(ROOT)
        if any(part in forbidden for part in rel.parts):
            raise ValueError('Private/generated path in release: '+str(rel))
        if any(part.is_symlink() for part in [p,*p.parents] if part!=ROOT and part.is_relative_to(ROOT)):
            raise ValueError('Symlinks are not distributed')
        payload=p.read_bytes()
        audit_text(rel.as_posix(),rel.as_posix())
        audit_payload(payload,rel.as_posix())
        if p.suffix.lower() in BINARY_EXTENSIONS or (rel.parts[0]=='examples' and rel.name not in {'sample-assets.json','make_demo.py'}):
            if approved.get(rel.as_posix())!=hashlib.sha256(payload).hexdigest():
                raise ValueError('Unapproved or changed sample content: '+rel.as_posix())
        if p.suffix.lower()=='.pptx' and rel.as_posix() not in {
                'examples/demo-deck.pptx','examples/demo-master-deck.pptx'}:
            raise ValueError('Only the fictional pitch and master demo decks can be distributed')
    return selected


def validate_source():
    manifest=json.loads((ROOT/'plugins/seed-ir/.codex-plugin/plugin.json').read_text(encoding='utf-8'))
    if manifest['name']!='seed-ir': raise ValueError('Plugin name mismatch')
    agents=list((ROOT/'custom-agents').glob('*.toml'))
    if len(agents)!=7: raise ValueError('Exactly seven custom agents required')
    for p in agents:
        data=tomllib.loads(p.read_text(encoding='utf-8'))
        if not all(data.get(k) for k in ('name','description','developer_instructions')):
            raise ValueError('Incomplete custom agent: '+p.name)
    required=['사용설명서.html','docs/validation-report.md',
              SKILL_PREFIX+'SKILL.md',SKILL_PREFIX+'scripts/render_rich.mjs',
              SKILL_PREFIX+'scripts/quality.py']
    for rel in required:
        if not (ROOT/rel).is_file(): raise ValueError('Required deliverable missing: '+rel)
    return manifest


def write_archive(out, filename, root_name, entries, empty_dirs=()):
    out=out.resolve()
    if out==ROOT or out.is_relative_to(ROOT):
        raise ValueError('Release output must be outside package source')
    out.mkdir(parents=True,exist_ok=True)
    target=out/filename
    if target.is_symlink() or target.with_suffix('.zip.sha256').is_symlink():
        raise ValueError('Release destination must not be a symlink')
    hashes={}
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for relative,data in sorted(entries.items()):
            audit_text(relative,relative)
            audit_payload(data,relative)
            name=root_name+'/'+relative
            hashes[name]=hashlib.sha256(data).hexdigest()
            info=zipfile.ZipInfo(name,(2026,9,12,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,data)
        for relative in empty_dirs:
            info=zipfile.ZipInfo(root_name+'/'+relative+'/',(2026,9,12,0,0,0))
            info.external_attr=(0o40755<<16)|0x10
            z.writestr(info,b'')
        info=zipfile.ZipInfo(root_name+'/FILE-MANIFEST.json',(2026,9,12,0,0,0))
        info.compress_type=zipfile.ZIP_DEFLATED
        z.writestr(info,json.dumps(hashes,ensure_ascii=False,indent=2))
    digest=hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix('.zip.sha256').write_text(digest+'  '+target.name+'\n',encoding='utf-8')
    with zipfile.ZipFile(target) as z:
        if z.testzip() is not None: raise ValueError('ZIP CRC verification failed')
    print(json.dumps({'zip':str(target),'file_count':len(hashes)+1,
                      'bytes':target.stat().st_size,'sha256':digest},ensure_ascii=False,indent=2))
    return target


def build_learner(out: Path):
    """A ready-to-open project: no installer or separate destination directory."""
    manifest=validate_source()
    entries={}
    for p in checked_files():
        rel=p.relative_to(ROOT).as_posix()
        destination=None
        if rel.startswith(SKILL_PREFIX):
            destination='.agents/skills/seed-ir/'+rel[len(SKILL_PREFIX):]
        elif rel.startswith('custom-agents/'):
            destination='.codex/agents/'+p.name
        elif rel=='learner-template/AGENTS.md': destination='AGENTS.md'
        elif rel=='requirements.txt': destination='.agents/skills/seed-ir/requirements.txt'
        elif rel in {'사용설명서.html','README.md','NOTICE.md'}: destination=rel
        elif rel in LEARNER_DOCS: destination=rel
        elif rel.startswith('examples/') and p.suffix!='.py': destination=rel
        if destination:
            if destination in entries: raise ValueError('Duplicate destination: '+destination)
            entries[destination]=p.read_bytes()
    required={'AGENTS.md','사용설명서.html','docs/advanced-guide.html',
              '.agents/skills/seed-ir/SKILL.md','.agents/skills/seed-ir/requirements.txt',
              '.agents/skills/seed-ir/scripts/prepare_project.py',
              '.agents/skills/seed-ir/scripts/publish_results.py'}
    missing=required-entries.keys()
    if missing: raise ValueError('Missing beginner entrypoints: '+', '.join(sorted(missing)))
    entries['VERSION.txt']=(manifest['version']+'\n').encode()
    return write_archive(out,f'정석biz-IR-Deck-v{manifest["version"]}.zip',LEARNER_ROOT,
                         entries,('자료넣는곳','결과물'))


def build(out: Path):
    """Keep the existing developer build API and installer layout."""
    manifest=validate_source()
    return write_archive(out,f'seed-ir-harness-v{manifest["version"]}.zip','seed-ir-harness',
                         {p.relative_to(ROOT).as_posix():p.read_bytes() for p in checked_files()})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT.parent/'dist')
    p.add_argument('--audience',choices=['learner','developer','both'],default='both')
    args=p.parse_args()
    if args.audience in ('learner','both'): build_learner(args.output)
    if args.audience in ('developer','both'): build(args.output)
