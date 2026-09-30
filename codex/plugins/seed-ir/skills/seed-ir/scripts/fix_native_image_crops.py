"""Preserve source image bytes and apply explicit native OOXML source crops.

Artifact Tool's current contain-image export omits explicit crop metadata.
This narrow package repair keeps the source bitmap editable and embedded whole.
"""
import json
from pathlib import Path
import sys
from xml.etree import ElementTree as ET
from zipfile import ZipFile
from PIL import Image

NS = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'p': 'http://schemas.openxmlformats.org/presentationml/2006/main'}
for prefix, uri in NS.items(): ET.register_namespace(prefix, uri)


def repair(pptx_path, manifest_path):
    target = Path(pptx_path)
    manifest = json.loads(Path(manifest_path).read_text('utf-8'))
    if not manifest: return
    with ZipFile(target) as source:
        entries = {item.filename: (item, source.read(item.filename)) for item in source.infolist()}
    roots = {}
    for item in manifest:
        rel = f'ppt/slides/slide{item["slide"]}.xml'
        root = roots.setdefault(rel, ET.fromstring(entries[rel][1]))
        pictures = root.findall('.//p:pic', NS)
        picture = pictures[item['image_index']]
        fill = picture.find('p:blipFill', NS)
        crop = fill.find('a:srcRect', NS)
        if crop is None:
            crop = ET.Element('{%s}srcRect' % NS['a'])
            fill.insert(1, crop)
        crop.attrib.update({key[0]: str(round(item['crop'][key] * 100000)) for key in ('left', 'top', 'right', 'bottom')})
        with Image.open(item['source']) as image:
            iw, ih = image.size
        visible_w = iw * (1 - item['crop']['left'] - item['crop']['right'])
        visible_h = ih * (1 - item['crop']['top'] - item['crop']['bottom'])
        x, y, w, h = item['frame']
        scale = min(w / visible_w, h / visible_h)
        pw, ph = visible_w * scale, visible_h * scale
        transform = picture.find('p:spPr/a:xfrm', NS)
        transform.find('a:off', NS).attrib.update({'x': str(round((x + (w-pw)/2) * 9525)), 'y': str(round((y + (h-ph)/2) * 9525))})
        transform.find('a:ext', NS).attrib.update({'cx': str(round(pw * 9525)), 'cy': str(round(ph * 9525))})
    temporary = target.with_suffix('.crop.pptx')
    with ZipFile(temporary, 'w') as output:
        for name, (metadata, data) in entries.items():
            output.writestr(metadata, ET.tostring(roots[name], encoding='utf-8', xml_declaration=True) if name in roots else data)
    temporary.replace(target)


if __name__ == '__main__': repair(*sys.argv[1:3])
