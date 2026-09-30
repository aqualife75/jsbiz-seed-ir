#!/usr/bin/env python3
"""Rebuild the public v1.4 GlucoPic teaching deck from adjacent JSON/MD/assets.

All business content is fictional. Creates 20 master slides, an 18-slide / 300-second
pitch, and 18 question briefs. Use a new project directory. --publish-examples copies
both successfully rendered PPTX views and resets any previous manual review record.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / 'examples'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def build(project):
    load('demo_installer', ROOT / 'install.py').install(project, 'GlucoPic · 교육용 가상', False)
    scripts = project / '.agents/skills/seed-ir/scripts'
    h = load('demo_harness', scripts / 'harness.py')
    q = load('demo_quality', scripts / 'quality.py')
    manifest = read(EXAMPLES / 'sample-assets.json')
    deck = read(EXAMPLES / 'demo-deck.json')
    used_paths = {a['path'] for a in h.image_records(deck)}
    source_assets = [a for a in manifest['assets']
                     if a['path'].replace('examples/', 'input/', 1) in used_paths]
    for asset in manifest['assets']:
        path = (ROOT / asset['path']).resolve()
        if not path.is_relative_to(EXAMPLES / 'assets') or h.sha(path) != asset['sha256']:
            raise ValueError('검토한 GlucoPic 샘플 이미지와 다릅니다: ' + asset['path'])
    shutil.copyfile(EXAMPLES / 'demo-input.md', project / 'input/demo-input.md')
    # The newer design gallery is separate from the original public deck fixture.
    for asset in source_assets:
        target = project / asset['path'].replace('examples/', 'input/', 1)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / asset['path'], target)
    config = h.read_json(project / 'project.json')
    config.update(require_visual_briefs=True, source_fictional=True,
                  sample_id='glucopic-fictional')
    h.write_json(project / 'project.json', config)
    subprocess.run([sys.executable, str(scripts / 'ingest.py'), '--input', str(project / 'input'),
                    '--output', str(project / 'data/raw')], check=True)
    inventory = h.read_json(project / 'data/raw/inventory.json')
    source_id = next(f['source_id'] for f in inventory['files']
                     if f['source_file'].replace('\\', '/').endswith('demo-input.md'))
    documents = h.read_json(project / 'data/raw/documents.json')['segments']
    # Reuse the package's hash-bound source-image audit, never a new deck review.
    # The author inspected these exact crops and original photos against all 19
    # source PDF pages. Unknown/changed assets fail the hash check above.
    audited = {a['sha256'] for a in source_assets}
    reviewed_ids = [f['source_id'] for f in inventory['files'] if f['sha256'] in audited]
    h.write_json(project / 'reviews/extraction.json', {
        'inventory_sha256': h.sha(project / 'data/raw/inventory.json'),
        'reviewed_source_ids': reviewed_ids, 'ocr_review_complete': True,
        'reviewer': 'GlucoPic 공개 샘플 제작 시 원안·추출 이미지 직접 시각 검토',
        'rationale': 'sample-assets.json의 지문과 일치하는 이미지에 한해 원안 검토를 재사용. 가상 MVP 화면의 수치는 예시이며 실제 성과가 아님. 최종 장표 시각 검토와 별개.',
        'sample_asset_manifest_sha256': h.sha(EXAMPLES / 'sample-assets.json')})
    evidence = read(EXAMPLES / 'demo-evidence.json')
    for item in evidence['items']:
        segment = next(s for s in documents if s['source_id'] == source_id
                       and item['claim'] in s.get('text', ''))
        item.update(source_id=source_id, locator=segment['locator'])
    deck = read(EXAMPLES / 'demo-deck.json')
    briefs = read(EXAMPLES / 'demo-section-briefs.json')
    h.write_json(project / 'evidence/evidence.json', evidence)
    h.write_json(project / 'deck/deck.json', deck)
    h.write_json(project / 'deck/section-briefs.json', briefs)
    plans = []
    for slide in deck['slides']:
        blocks = slide['blocks']
        assets = list(h.visual_plan.displayed_assets(slide))
        types = {b['type'] for b in blocks}
        visual_type = ('product_ui' if slide['section'] == 'product' else 'photo') if assets else (
            'table' if 'table' in types else 'chart' if 'chart' in types else
            'diagram' if types & {'steps', 'mapping', 'formula', 'roadmap', 'team'} else
            'mixed' if 'metric' in types else 'quote')
        plans.append({'slide_id': slide['id'], 'block_ids': [b['id'] for b in blocks],
            'evidence_ids': slide['evidence_ids'], 'visual_type': visual_type,
            'source_strategy': 'original' if assets else 'native',
            'asset_refs': [{**{k: a[k] for k in ('path', 'source', 'rights', 'caption')},
                'origin': 'original', 'sha256': h.sha(project / a['path']),
                'claim_boundary': '승인된 교육용 가상 원안. 실제 고객·구현·성과의 증거 아님'} for a in assets],
            'disclosure': '교육용 가상 사례 · 가정 및 계획',
            'claim_boundary': '교육용 가상 사업의 표현 예시이며 실제 사업 검증 결과가 아니다',
            'status': 'ready', 'search_note': '승인된 기존 교육용 원안에서 재현. 신규 외부 조사를 했다는 의미가 아님'})
    plan = {'schema_version': '1.0', 'slides': plans}
    plan_check = h.visual_plan.validate(plan, deck, {e['id']: e for e in evidence['items']}, project, required=True, final=True)
    if plan_check['errors']: raise ValueError('\n'.join(plan_check['errors']))
    h.write_json(project / 'design/visual-plan.json', plan)
    raw_assets = h.read_json(project / 'data/raw/assets.json')['assets']
    def section_assets(section):
        paths = {b['path'].removeprefix('input/') for s in deck['slides']
                 if s['section'] == section for b in s.get('blocks', [])
                 if b.get('type') == 'image'}
        return [a['asset_id'] for a in raw_assets if a['source_file'] in paths]
    h.write_json(project / 'evidence/section-map.json', {'schema_version': '1.2', 'sections': [
        {'section': section, 'evidence_ids': list(dict.fromkeys(
            eid for s in deck['slides'] if s['section'] == section for eid in s['evidence_ids'])),
         'asset_ids': section_assets(section),
         'missing_data': ['교육용 가상 사례입니다. 실제 자료로 대체하세요.']}
        for section in h.SECTIONS]})
    for stage in ['intake', 'evidence', 'story']:
        h.record(project, stage)
    validation = q.validate_briefs(briefs, q.load_curriculum(),
        {e['id']: e for e in evidence['items']}, deck['slides'], h.validate_claim)
    if validation['errors']:
        raise ValueError('\n'.join(validation['errors']))
    return scripts, h, validation


def contact_sheet(render_dir, target):
    from PIL import Image, ImageOps
    files = sorted(render_dir.glob('slide-*.png'))
    if not files:
        raise ValueError('실제 PPTX 렌더 PNG가 없습니다: ' + str(render_dir))
    thumbnails = []
    for path in files:
        with Image.open(path) as original:
            thumbnails.append(ImageOps.contain(original.convert('RGB'), (640, 360)))
    columns = 3
    canvas = Image.new('RGB', (2000, ((len(thumbnails) + 2) // 3) * 380 + 20), '#e6e9ed')
    for i, thumbnail in enumerate(thumbnails):
        canvas.paste(thumbnail, (20 + (i % columns) * 660, 20 + (i // columns) * 380))
    canvas.save(target, quality=92)
    return len(files)


def publish(project, h):
    counts = {}
    for view, prefix in [('pitch', 'demo'), ('master', 'demo-master')]:
        output = project / 'output' / view
        shutil.copyfile(output / 'seed-ir-draft.pptx', EXAMPLES / (prefix + '-deck.pptx'))
        shutil.copyfile(output / 'storyboard.html', EXAMPLES / (prefix + '-storyboard.html'))
        counts[view] = contact_sheet(output / 'renders', EXAMPLES / (prefix + '-preview.jpg'))
    # Persist new ingest locators; the public fixtures remain the reproducible authoring inputs.
    for source, name in [('deck/deck.json', 'demo-deck.json'),
                         ('deck/section-briefs.json', 'demo-section-briefs.json'),
                         ('evidence/evidence.json', 'demo-evidence.json'),
                         ('input/demo-input.md', 'demo-input.md')]:
        shutil.copyfile(project / source, EXAMPLES / name)
    deck = h.read_json(project / 'deck/deck.json')
    briefs = h.read_json(project / 'deck/section-briefs.json')
    reports = {view: h.read_json(project / 'output' / view / 'render-report.json')
               for view in ['master', 'pitch']}
    validation = {'schema_version': '1.2', 'release_version': '1.4.0',
        'sample_id': 'glucopic-fictional', 'source_fictional': True,
        'disclosure': deck['disclosure'],
        'status': 'public-fictional-draft', 'counts': counts, 'section_count': 14,
        'question_count': sum(len(s['questions']) for s in briefs['sections']),
        'pitch_planned_seconds': sum(s['seconds'] for s in deck['slides']
            if s['id'] in deck['views']['pitch']['slide_ids']),
        'actual_pptx_rendered': all(r.get('actual_pptx_rendered') for r in reports.values()),
        'pptx_sha256': {v: h.sha(project / 'output' / v / 'seed-ir-draft.pptx') for v in reports},
        'editable_chart_count': {v: r['editable_chart_count'] for v, r in reports.items()},
        'editable_table_count': {v: r['editable_table_count'] for v, r in reports.items()},
        'source_sha256': {name: h.sha(EXAMPLES / name) for name in
            ['demo-deck.json', 'demo-section-briefs.json', 'demo-evidence.json', 'demo-input.md']},
        'semantic_complete': False, 'research_review': 'not_performed',
        'investor_final_review': 'not_performed', 'visual_review': 'not_performed',
        'timing_review': 'planned only; no speaker rehearsal',
        'note': '실제 렌더를 생성했습니다. 공개 전 모든 장표의 시각 검토 결과는 별도로 기록합니다.'}
    h.write_json(EXAMPLES / 'demo-validation.json', validation)
    manifest = h.read_json(EXAMPLES / 'sample-assets.json')
    generated = []
    for filename in ['demo-input.md','demo-evidence.json','demo-deck.json',
                     'demo-section-briefs.json','demo-validation.json',
                     'demo-storyboard.html','demo-master-storyboard.html']:
        generated.append({'path':'examples/'+filename,'sha256':h.sha(EXAMPLES/filename),
                          'kind':'fictional-sample-content','source_fictional':True})
    for view, prefix in [('pitch', 'demo'), ('master', 'demo-master')]:
        for suffix, kind in [('-deck.pptx', 'editable-presentation'),
                             ('-preview.jpg', 'actual-render-contact-sheet')]:
            filename = prefix + suffix
            generated.append({'path': 'examples/' + filename,
                              'sha256': h.sha(EXAMPLES / filename), 'kind': kind,
                              'source_fictional': True,
                              'notes': 'GlucoPic 가상 JSON에서 생성한 ' + view + ' 보기'})
    preserved = [a for a in manifest.get('artifacts', [])
                 if a['path'] not in {x['path'] for x in generated}]
    manifest['artifacts'] = preserved + generated
    h.write_json(EXAMPLES / 'sample-assets.json', manifest)
    return validation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--skip-render', action='store_true')
    parser.add_argument('--publish-examples', action='store_true')
    args = parser.parse_args()
    if args.skip_render and args.publish_examples:
        parser.error('--publish-examples에는 실제 렌더가 필요합니다')
    project = args.project.resolve()
    scripts, h, validation = build(project)
    if not args.skip_render:
        for view in ['master', 'pitch']:
            subprocess.run([sys.executable, str(scripts / 'render_deck.py'), '--project',
                            str(project), '--view', view], check=True)
    if args.publish_examples:
        print(json.dumps(publish(project, h), ensure_ascii=False, indent=2))
    print(json.dumps({'claim_errors': validation['errors'], 'semantic_complete': False,
                      'notice': '공개 교육용 가상 초안. 실제 기업 검수 완료 사례가 아닙니다.'},
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
