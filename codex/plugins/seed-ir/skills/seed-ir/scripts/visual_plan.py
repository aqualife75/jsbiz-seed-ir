"""Validate the visual production plan; existence never proves a business claim."""
import hashlib
import re
from pathlib import Path

STRATEGIES = {'original', 'official', 'generated', 'native'}
TYPES = {'photo', 'product_ui', 'chart', 'table', 'diagram', 'quote', 'mixed'}
RIGHTS = {'owned', 'licensed', 'permission', 'public-domain'}

def choice(value, options):
    return isinstance(value, str) and value in options

def disclosed(value):
    return isinstance(value, str) and bool(re.search(r'생성|가상|설계|예시', value))

def displayed_assets(slide):
    """Only slots the shipped renderer consumes count as displayed."""
    for asset in slide.get('assets', []):
        if isinstance(asset, dict) and isinstance(asset.get('path'), str): yield asset
    for block in slide.get('blocks', []):
        if not isinstance(block, dict): continue
        if block.get('type') == 'image' and isinstance(block.get('path'), str): yield block
        if block.get('type') == 'steps':
            for item in block.get('items', []):
                asset = item.get('asset') if isinstance(item, dict) else None
                if isinstance(asset, dict) and isinstance(asset.get('path'), str): yield asset


def assets_in(value):
    if isinstance(value, dict):
        if isinstance(value.get('path'), str):
            yield value
        for child in value.values():
            yield from assets_in(child)
    elif isinstance(value, list):
        for child in value:
            yield from assets_in(child)


def validate(plan, deck, evidence, project, *, required=False, final=False):
    errors, warnings = [], []
    def issue(text):
        (errors if final else warnings).append('visual-plan: ' + text)
    if plan is None:
        if required:
            issue('장표별 시각 자료 계획 design/visual-plan.json이 필요합니다')
        return {'errors': errors, 'warnings': warnings}
    if not isinstance(plan, dict) or plan.get('schema_version') != '1.0' or not isinstance(plan.get('slides'), list):
        return {'errors': ['visual-plan: schema_version 1.0과 slides 배열이 필요합니다'], 'warnings': []}
    slides = {s['id']: s for s in deck.get('slides', []) if isinstance(s, dict) and isinstance(s.get('id'), str)}
    views = deck.get('views', {})
    used = set().union(*(set(x for x in v.get('slide_ids', []) if isinstance(x, str)) for v in views.values() if isinstance(v, dict))) if views else set(slides)
    seen = set()
    root = Path(project).resolve()
    for item in plan['slides']:
        if not isinstance(item, dict):
            errors.append('visual-plan: 장표 항목은 객체여야 합니다'); continue
        sid = item.get('slide_id')
        if not isinstance(sid, str) or sid not in slides or sid in seen:
            errors.append('visual-plan: 중복 또는 알 수 없는 slide_id'); continue
        seen.add(sid)
        def fail(message): errors.append(f'visual-plan {sid}: {message}')
        for field in ('claim_boundary', 'search_note'):
            if not isinstance(item.get(field), str) or not item[field].strip(): fail(field + ' 설명 필요')
        if not choice(item.get('source_strategy'), STRATEGIES): fail('source_strategy 오류')
        if not choice(item.get('visual_type'), TYPES): fail('visual_type 오류')
        if not choice(item.get('status'), {'planned', 'ready', 'missing'}): fail('status 오류')
        elif item['status'] != 'ready': issue(sid + ' 시각 자료 준비 미완료: ' + item['status'])
        refs = item.get('evidence_ids')
        if not isinstance(refs, list) or not refs or any(not isinstance(x, str) or x not in evidence for x in refs):
            fail('현재 근거 목록의 evidence_ids 필요')
        elif len(refs) != len(set(refs)): fail('evidence_ids 중복')
        blocks = {b['id']: b for b in slides[sid].get('blocks', []) if isinstance(b, dict) and isinstance(b.get('id'), str)}
        ids = item.get('block_ids')
        if not isinstance(ids, list) or not ids or any(not isinstance(x, str) or x not in blocks for x in ids):
            fail('실제 표시 블록을 가리키는 block_ids 필요')
        elif len(ids) != len(set(ids)): fail('block_ids 중복')
        else:
            types = {blocks[x].get('type') for x in ids if isinstance(blocks[x].get('type'), str)}
            expected = {'chart': {'chart'}, 'table': {'table'},
                'photo': {'image', 'steps'}, 'product_ui': {'image', 'steps'},
                'diagram': {'steps', 'mapping', 'formula', 'roadmap', 'team'}, 'quote': {'text'},
                'mixed': {'image', 'chart', 'table', 'steps', 'mapping', 'formula', 'roadmap', 'team', 'metric'}}
            if choice(item.get('visual_type'), expected) and not types & expected[item['visual_type']]:
                fail('visual_type에 맞는 실제 블록이 없습니다')
        disclosure = item.get('disclosure')
        if not isinstance(disclosure, str): fail('disclosure 문자열 필요')
        if item.get('source_strategy') == 'generated' and not disclosed(disclosure):
            fail('생성 이미지의 가상·설계 표기를 명시하세요')
        assets = item.get('asset_refs', [])
        if not isinstance(assets, list): fail('asset_refs 배열 필요'); continue
        selected = [blocks[x] for x in ids if isinstance(x, str) and x in blocks] if isinstance(ids, list) else []
        rendered = {a['path']: a for a in displayed_assets({'blocks': selected})}
        if choice(item.get('visual_type'), {'photo', 'product_ui'}) and not rendered:
            fail('사진·제품 화면에는 실제 이미지 블록 또는 steps의 asset이 필요합니다')
        if rendered and not assets: fail('선택한 이미지의 출처·권리·해시를 asset_refs에 기록하세요')
        listed_paths = {a.get('path') for a in assets if isinstance(a, dict) and isinstance(a.get('path'), str)}
        if set(rendered) - listed_paths: fail('선택한 이미지의 asset_refs 누락')
        if choice(item.get('source_strategy'), {'original', 'official', 'generated'}) and not assets:
            issue(sid + ' 계획한 이미지 자산이 없습니다')
        for asset in assets:
            if not isinstance(asset, dict): fail('asset_refs 항목은 객체여야 합니다'); continue
            for field in ('path', 'source', 'caption', 'claim_boundary'):
                if not isinstance(asset.get(field), str) or not asset[field].strip(): fail('자산 ' + field + ' 필요')
            relative = asset.get('path')
            if not isinstance(relative, str): continue
            try:
                path = (root / relative.replace('\\', '/')).resolve()
            except (OSError, ValueError):
                fail('자산 경로를 확인할 수 없습니다'); continue
            if ':' in relative or relative.startswith(('/', '\\')) or not path.is_relative_to(root):
                fail('자산 경로는 프로젝트 내부 상대경로여야 합니다'); continue
            if relative not in rendered: fail('장표에 연결되지 않은 자산: ' + relative)
            if not choice(asset.get('rights'), RIGHTS): fail('자산 사용권 확인 필요')
            if not choice(asset.get('origin'), {'original', 'official', 'generated'}): fail('자산 origin 필요')
            if asset.get('origin') == 'generated' and not disclosed(asset.get('caption')):
                fail('생성 자산의 가상·설계 캡션 필요')
            if asset.get('origin') == 'generated' and not disclosed(rendered.get(relative, {}).get('caption')):
                fail('실제 장표 자산에도 생성·설계 캡션이 필요합니다')
            try:
                if not path.is_file(): issue(sid + ' 자산 파일 없음: ' + relative)
                elif asset.get('sha256') != hashlib.sha256(path.read_bytes()).hexdigest(): fail('자산 SHA256 불일치: ' + relative)
            except (OSError, ValueError):
                fail('자산 파일을 읽을 수 없습니다: ' + relative)
    if used - seen: issue('사용 장표 계획 누락: ' + ', '.join(sorted(str(x) for x in used - seen)))
    return {'errors': errors, 'warnings': warnings}
