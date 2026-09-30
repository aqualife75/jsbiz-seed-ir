"""Embed editable XLSX snapshots for this renderer's literal bar/line chart data.

Uses only the Python standard library. Existing workbook references are never
replaced; incomplete caches and unbacked formulas fail instead of guessing data.
No source workbook or source formulas are claimed to be preserved by a snapshot.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import io
import json
import math
from pathlib import Path
import posixpath
import re
from xml.etree import ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED

C = 'http://schemas.openxmlformats.org/drawingml/2006/chart'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
P = 'http://schemas.openxmlformats.org/package/2006/relationships'
S = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
CT = 'http://schemas.openxmlformats.org/package/2006/content-types'
NS = {'c': C, 'r': R, 'p': P, 's': S}
for prefix, namespace in [('c', C), ('r', R)]: ET.register_namespace(prefix, namespace)


def xml(root):
    namespace = root.tag.split('}')[0].lstrip('{')
    if namespace in (CT, P, S):
        ET.register_namespace('', namespace)
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def column_name(number):
    value = ''
    while number:
        number, remainder = divmod(number - 1, 26)
        value = chr(65 + remainder) + value
    return value


def read_cache(cache):
    count = cache.find(f'{{{C}}}ptCount')
    if count is None or not count.get('val', '').isdigit():
        raise ValueError('Chart literal cache has no complete point count')
    n = int(count.get('val'))
    points = cache.findall(f'{{{C}}}pt')
    values = {}
    for point in points:
        index = int(point.get('idx', '-1'))
        value = point.find(f'{{{C}}}v')
        if index in values or value is None or value.text is None:
            raise ValueError('Chart literal cache has missing or duplicate points')
        values[index] = value.text
    if n < 1 or set(values) != set(range(n)):
        raise ValueError('Chart literal cache must contain every ordered data point')
    ordered = [values[i] for i in range(n)]
    numeric = cache.tag == f'{{{C}}}numLit'
    if numeric and any(not math.isfinite(float(v)) for v in ordered):
        raise ValueError('Chart values must be finite')
    return ordered, numeric


def workbook_bytes(columns):
    """Columns are (header, ordered strings, numeric); numeric text stays exact."""
    sheet = ET.Element(f'{{{S}}}worksheet')
    rows = ET.SubElement(sheet, f'{{{S}}}sheetData')
    for ri in range(max(len(c[1]) for c in columns) + 1):
        row = ET.SubElement(rows, f'{{{S}}}row', {'r': str(ri + 1)})
        for ci, (header, values, numeric) in enumerate(columns, 1):
            if ri > len(values):
                continue
            value = header if ri == 0 else values[ri - 1]
            if re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', value):
                raise ValueError('Workbook labels contain unsupported XML control characters')
            cell = ET.SubElement(row, f'{{{S}}}c', {'r': column_name(ci) + str(ri + 1)})
            if ri and numeric:
                ET.SubElement(cell, f'{{{S}}}v').text = value
            else:
                cell.set('t', 'inlineStr')
                inline = ET.SubElement(cell, f'{{{S}}}is')
                ET.SubElement(inline, f'{{{S}}}t', {'{http://www.w3.org/XML/1998/namespace}space': 'preserve'}).text = value
    workbook = ET.Element(f'{{{S}}}workbook')
    sheets = ET.SubElement(workbook, f'{{{S}}}sheets')
    ET.SubElement(sheets, f'{{{S}}}sheet', {'name': 'Data', 'sheetId': '1', f'{{{R}}}id': 'rId1'})
    rels = ET.Element(f'{{{P}}}Relationships')
    ET.SubElement(rels, f'{{{P}}}Relationship', {'Id': 'rId1', 'Type': R + '/worksheet', 'Target': 'worksheets/sheet1.xml'})
    package_rels = ET.Element(f'{{{P}}}Relationships')
    ET.SubElement(package_rels, f'{{{P}}}Relationship', {'Id': 'rId1', 'Type': R + '/officeDocument', 'Target': 'xl/workbook.xml'})
    types = ET.Element(f'{{{CT}}}Types')
    ET.SubElement(types, f'{{{CT}}}Default', {'Extension': 'rels', 'ContentType': 'application/vnd.openxmlformats-package.relationships+xml'})
    ET.SubElement(types, f'{{{CT}}}Default', {'Extension': 'xml', 'ContentType': 'application/xml'})
    ET.SubElement(types, f'{{{CT}}}Override', {'PartName': '/xl/workbook.xml', 'ContentType': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml'})
    ET.SubElement(types, f'{{{CT}}}Override', {'PartName': '/xl/worksheets/sheet1.xml', 'ContentType': 'application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml'})
    buffer = io.BytesIO()
    with ZipFile(buffer, 'w', ZIP_DEFLATED) as package:
        for name, root in [('[Content_Types].xml', types), ('_rels/.rels', package_rels),
                           ('xl/workbook.xml', workbook), ('xl/_rels/workbook.xml.rels', rels),
                           ('xl/worksheets/sheet1.xml', sheet)]:
            package.writestr(name, xml(root))
    return buffer.getvalue()


def replace_literal(container, cache, formula):
    numeric = cache.tag == f'{{{C}}}numLit'
    ref = ET.Element(f'{{{C}}}' + ('numRef' if numeric else 'strRef'))
    ET.SubElement(ref, f'{{{C}}}f').text = formula
    copied = copy.deepcopy(cache)
    copied.tag = f'{{{C}}}' + ('numCache' if numeric else 'strCache')
    ref.append(copied)
    container.remove(cache)
    container.append(ref)


def materialize(source, destination, workspace, receipt):
    source, destination, workspace, receipt = map(lambda p: Path(p).resolve(), (source, destination, workspace, receipt))
    if any(not p.is_relative_to(workspace) for p in (source, destination, receipt)):
        raise ValueError('Chart staging paths must stay inside the project')
    if destination.exists() or source == destination:
        raise ValueError('Destination must be a new staged file')
    original = source.read_bytes()
    with ZipFile(io.BytesIO(original)) as package:
        entries = {entry.filename: (entry, package.read(entry.filename)) for entry in package.infolist()}
    changed, converted, preserved = {}, [], []
    types = ET.fromstring(entries['[Content_Types].xml'][1])
    chart_parts = [name for name in entries if re.search(r'/charts/[^/]+\.xml$', name)]
    for index, part in enumerate(chart_parts, 1):
        chart = ET.fromstring(entries[part][1])
        if chart.tag != f'{{{C}}}chartSpace':
            continue
        parent, filename = posixpath.split(part)
        rel_name = parent + '/_rels/' + filename + '.rels'
        relationships = ET.fromstring(entries[rel_name][1]) if rel_name in entries else ET.Element(f'{{{P}}}Relationships')
        external = chart.find('c:externalData', NS)
        if external is not None:
            rid = external.get(f'{{{R}}}id')
            relation = next((r for r in relationships if r.get('Id') == rid), None)
            target = posixpath.normpath(posixpath.join(parent, relation.get('Target', ''))) if relation is not None else None
            if relation is None or relation.get('TargetMode') == 'External' or target not in entries:
                raise ValueError('Existing chart workbook reference cannot be verified; it was not replaced')
            with ZipFile(io.BytesIO(entries[target][1])) as workbook:
                if 'xl/workbook.xml' not in workbook.namelist():
                    raise ValueError('Existing chart workbook is not a valid XLSX')
            preserved.append(part)
            continue
        if chart.findall('.//c:numRef', NS) or chart.findall('.//c:strRef', NS):
            raise ValueError('Chart has workbook formulas without a workbook; refuse to replace unknown lineage')
        series = chart.findall('.//c:ser', NS)
        if not series:
            raise ValueError('Chart has no series')
        columns = []
        for si, item in enumerate(series):
            cat, val = item.find('c:cat', NS), item.find('c:val', NS)
            if cat is None or val is None:
                raise ValueError('Only complete category/value bar and line charts are supported')
            cat_cache = next((x for x in cat if x.tag in (f'{{{C}}}strLit', f'{{{C}}}numLit')), None)
            val_cache = val.find('c:numLit', NS)
            if cat_cache is None or val_cache is None:
                raise ValueError('Literal categories and numeric values are required')
            cats, cat_numeric = read_cache(cat_cache)
            values, _ = read_cache(val_cache)
            if len(cats) != len(values):
                raise ValueError('Chart category and value counts differ')
            name = item.findtext('c:tx/c:v', '', NS)
            if not name:
                raise ValueError('Every series must have an explicit name')
            ccol, vcol = column_name(si * 2 + 1), column_name(si * 2 + 2)
            columns += [('Category', cats, cat_numeric), (name, values, True)]
            replace_literal(cat, cat_cache, f"'Data'!${ccol}$2:${ccol}${len(cats)+1}")
            replace_literal(val, val_cache, f"'Data'!${vcol}$2:${vcol}${len(values)+1}")
            tx = item.find('c:tx', NS)
            tx.clear()
            ref = ET.SubElement(tx, f'{{{C}}}strRef')
            ET.SubElement(ref, f'{{{C}}}f').text = f"'Data'!${vcol}$1"
            cache = ET.SubElement(ref, f'{{{C}}}strCache')
            ET.SubElement(cache, f'{{{C}}}ptCount', {'val': '1'})
            point = ET.SubElement(cache, f'{{{C}}}pt', {'idx': '0'})
            ET.SubElement(point, f'{{{C}}}v').text = name
        workbook_part = f'ppt/embeddings/seed-ir-chart-{index}.xlsx'
        if workbook_part in entries:
            raise ValueError('Generated workbook name would overwrite an existing part')
        changed[workbook_part] = workbook_bytes(columns)
        rid = 'rIdSeedIRData'
        if any(r.get('Id') == rid for r in relationships):
            raise ValueError('Generated workbook relationship ID already exists')
        ET.SubElement(relationships, f'{{{P}}}Relationship', {'Id': rid, 'Type': R + '/package', 'Target': posixpath.relpath(workbook_part, parent)})
        data = ET.SubElement(chart, f'{{{C}}}externalData', {f'{{{R}}}id': rid})
        ET.SubElement(data, f'{{{C}}}autoUpdate', {'val': '0'})
        ET.SubElement(types, f'{{{CT}}}Override', {'PartName': '/' + workbook_part, 'ContentType': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'})
        changed[part], changed[rel_name] = xml(chart), xml(relationships)
        converted.append(part)
    changed['[Content_Types].xml'] = xml(types)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(destination, 'w', ZIP_DEFLATED) as package:
        for name, (metadata, data) in entries.items():
            package.writestr(metadata, changed.pop(name, data))
        for name, data in changed.items():
            package.writestr(name, data)
    report = {'schema_version': 'seed-ir.literal-chart-snapshot.v1', 'conversion': 'literal_input_workbook_snapshot',
              'source_formulas_preserved': False, 'new_formulas_describe_snapshot_only': True,
              'converted_chart_parts': converted, 'preserved_existing_workbook_chart_parts': preserved,
              'input_sha256': hashlib.sha256(original).hexdigest(), 'output_sha256': hashlib.sha256(destination.read_bytes()).hexdigest()}
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(materialize(args.source, args.destination, args.workspace, args.receipt), ensure_ascii=False))
