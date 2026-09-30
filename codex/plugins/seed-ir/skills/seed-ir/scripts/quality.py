#!/usr/bin/env python3
"""정석biz 노하우 question contracts and typed slide blocks, with explicit draft gaps.

These deterministic checks validate completeness and evidence references, not
whether a cited source logically entails a claim. An investor review is still
required. Unknown information stays missing rather than becoming a fact.
"""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import re


def load_curriculum(schema_version=None):
    path = Path(__file__).resolve().parents[1] / 'references/kdb-curriculum.json'
    curriculum=json.loads(path.read_text(encoding='utf-8-sig'))
    version='.'.join(str(schema_version).split('.')[:2]) if schema_version else None
    if version in curriculum.get('legacy_contracts',{}):
        return curriculum['legacy_contracts'][version]
    return curriculum


def question_contracts(topic):
    """Stable question IDs. Required data are collected once on the first question."""
    return topic.get('question_contracts') or [
        {'id': f"{topic['id']}.q{i}", 'question': question,
         'required_data': topic.get('required_data', []) if i == 1 else []}
        for i, question in enumerate(topic.get('investor_questions', []), 1)]


def initial_briefs(curriculum=None):
    curriculum = curriculum or load_curriculum()
    return {'schema_version': curriculum.get('schema_version','1.2'), 'sections': [
        {'section': topic['id'], 'questions': [
            {'question_id': contract['id'], 'question': contract['question'],
             'status': 'missing', 'answer': None, 'argument': [],
             'coverage': [{'requirement': requirement, 'claim': None}
                          for requirement in contract.get('required_data', [])],
             'evidence_ids': [], 'visual_refs': [],
             'missing': ['투자자 질문의 답변과 논거를 원본 자료에서 확인하세요']}
            for contract in question_contracts(topic)]}
        for topic in curriculum['topics']]}


def select_slides(deck, variant='pitch'):
    if variant not in ('master', 'pitch'):
        raise ValueError('variant는 master 또는 pitch여야 합니다')
    slides = deck.get('slides', [])
    if not isinstance(slides, list) or any(not isinstance(s, dict) for s in slides):
        raise ValueError('slides는 객체 배열이어야 합니다')
    if str(deck.get('schema_version', '1.0')).startswith('1.0') and 'views' not in deck:
        return slides
    views = deck.get('views')
    view = views.get(variant) if isinstance(views, dict) else None
    if not isinstance(view, dict) or not isinstance(view.get('slide_ids'), list) or not view['slide_ids']:
        raise ValueError(f'views.{variant}.slide_ids에 렌더할 슬라이드 ID가 필요합니다')
    ids = view['slide_ids']
    if any(not isinstance(sid, str) for sid in ids) or len(ids) != len(set(ids)):
        raise ValueError(f'views.{variant}.slide_ids에 잘못되거나 중복된 ID가 있습니다')
    lookup = {s.get('id'): s for s in slides if isinstance(s.get('id'), str)}
    if len(lookup) != len(slides):
        raise ValueError('슬라이드 ID 누락/중복')
    unknown = [sid for sid in ids if sid not in lookup]
    if unknown:
        raise ValueError(f'views.{variant}: 존재하지 않는 슬라이드 ID ' + ', '.join(unknown))
    return [lookup[sid] for sid in ids]


def slide_sections(slide):
    value = slide.get('section_ids', [slide.get('section')])
    return value if isinstance(value, list) else []


def contains_excluded_funding(value):
    """Inspect authored content, excluding IDs and other structural metadata."""
    excluded=re.compile(r'투자\s*(?:요청|금|유치\s*금액)|요청\s*(?:금액|액)|자금\s*(?:조달|사용)|조달\s*계획|(?:펀딩|seed|시드)\s*요청|fundrais(?:ing|e)|investment\s+ask',re.I)
    visible_keys={'governing_message','key_message','subtitle','speaker_notes','title','text','value','detail',
                  'caption','alt','label','formula','result','basis','period','gate','name','role',
                  'proof','contribution','problem','solution','columns','rows','deliverables',
                  'question','requirement'}

    def strings(child):
        if isinstance(child,str): yield child
        elif isinstance(child,dict):
            for nested in child.values(): yield from strings(nested)
        elif isinstance(child,list):
            for nested in child: yield from strings(nested)

    def words(child):
        if isinstance(child,dict):
            for key,nested in child.items():
                if key in visible_keys: yield from strings(nested)
                elif isinstance(nested,(dict,list)): yield from words(nested)
        elif isinstance(child,list):
            for nested in child: yield from words(nested)
    return any(excluded.search(text) for text in words(value))


def validate_view_contract(deck, variant, curriculum=None):
    """Apply the user's v1.2 independent-slide counts and fixed section order."""
    if not str(deck.get('schema_version','1.0')).startswith('1.2'): return []
    curriculum=curriculum or load_curriculum('1.2')
    topics=curriculum['topics']; order={topic['id']:i for i,topic in enumerate(topics)}
    counts={topic['id']:0 for topic in topics}; errors=[]; positions=[]
    try: slides=select_slides(deck,variant)
    except ValueError as exc: return [str(exc)]
    for slide in slides:
        sid=str(slide.get('id','?')); section=slide.get('section'); sections=slide_sections(slide)
        if not isinstance(section,str) or section not in order:
            errors.append(variant+' '+sid+': v1.2의 지정 목차가 필요합니다'); continue
        if sections!=[section]:
            errors.append(variant+' '+sid+': 각 장표는 한 목차의 독립 장표여야 합니다 (section_ids 중복 계산 금지)')
        else:
            if not slide.get('appendix'): counts[section]+=1
        positions.append(order[section])
        if slide.get('layout')=='roadmap_funding' or contains_excluded_funding(slide):
            errors.append(variant+' '+sid+': v1.2에는 투자 요청·요청 금액·자금 조달 내용을 포함하지 않습니다')
    if positions!=sorted(positions): errors.append(variant+': 사용자 지정 목차 순서를 유지하세요')
    for topic in topics:
        minimum=topic.get('min_slides',1)
        if counts[topic['id']]<minimum:
            errors.append(f"{variant}: {topic['id']} ({topic['label_ko']}) 독립 장표 최소 {minimum}개 필요")
    return errors


def validate_briefs(briefs, curriculum, evidence, slides, validate_claim, final=False):
    errors, warnings, gaps = [], [], []
    sections = briefs.get('sections', []) if isinstance(briefs, dict) else []
    if not isinstance(sections, list) or any(not isinstance(x, dict) for x in sections):
        return {'errors': ['section-briefs.sections는 객체 배열이어야 합니다'],
                'warnings': [], 'complete': False, 'gaps': []}
    expected = {t['id']: t for t in curriculum['topics']}
    names = [s.get('section') for s in sections]
    if any(not isinstance(s, str) for s in names) or sorted(names) != sorted(expected):
        errors.append(f'section-briefs에는 지정된 {len(expected)}목차를 각각 한 번씩 저장하세요')
    slide_lookup = {s.get('id'): s for s in slides}

    def gap(label, message):
        item = label + ': ' + message
        gaps.append(item)
        (errors if final else warnings).append(item)

    def claim(value, label):
        if not isinstance(value, dict) or not isinstance(value.get('text'), str) or not value['text'].strip():
            gap(label, '답변/주장 누락'); return
        errors.extend(validate_claim(value, evidence, label))

    for section in sections:
        topic = expected.get(section.get('section'))
        if not topic:
            continue
        contracts = {c['id']: c for c in question_contracts(topic)}
        questions = section.get('questions', [])
        if not isinstance(questions, list) or any(not isinstance(q, dict) for q in questions):
            errors.append(topic['id'] + ': questions는 객체 배열이어야 합니다'); continue
        qids = [q.get('question_id') for q in questions]
        if any(not isinstance(qid, str) for qid in qids) or len(qids) != len(set(qids)):
            errors.append(topic['id'] + ': question_id 누락/중복'); continue
        for qid in set(contracts) - set(qids):
            gap(qid, '필수 투자자 질문 누락')
        for q in questions:
            qid = q.get('question_id', '?')
            if qid not in contracts:
                errors.append(str(qid) + ': 알 수 없는 투자자 질문'); continue
            if str(curriculum.get('schema_version','')).startswith('1.2'):
                content={key:q.get(key) for key in ('question','answer','argument','coverage')}
                if contains_excluded_funding(content):
                    errors.append(qid + ': v1.2 질문 원고에 투자 요청·자금 사용·조달 내용을 포함하지 않습니다')
            if q.get('status') not in ('answered', 'partial', 'missing'):
                errors.append(qid + ': status는 answered/partial/missing이어야 합니다')
            elif q['status'] != 'answered':
                gap(qid, '아직 답변이 완료되지 않았습니다 (' + q['status'] + ')')
            missing = q.get('missing')
            if not isinstance(missing, list) or any(not isinstance(x, str) or not x.strip() for x in missing):
                errors.append(qid + ': missing에는 부족한 정보를 문자열 배열로 기록하세요')
            elif missing:
                gap(qid, '미확인 정보: ' + '; '.join(missing))
            elif q.get('status') in ('partial', 'missing'):
                errors.append(qid + ': 미완료 답변은 missing에 부족한 정보를 명시하세요')
            claim(q.get('answer'), qid + ' answer')
            argument = q.get('argument', [])
            if not isinstance(argument, list):
                errors.append(qid + ': argument는 주장 배열이어야 합니다')
            elif not argument:
                gap(qid, 'argument 논거 누락')
            else:
                for i, item in enumerate(argument): claim(item, f'{qid} argument[{i}]')
            coverage = q.get('coverage', [])
            if not isinstance(coverage, list) or any(not isinstance(x, dict) for x in coverage):
                errors.append(qid + ': coverage는 객체 배열이어야 합니다'); coverage = []
            covered = [x.get('requirement') for x in coverage]
            if any(not isinstance(x, str) for x in covered) or len(covered) != len(set(covered)):
                errors.append(qid + ': coverage requirement 누락/중복')
            for requirement in contracts[qid].get('required_data', []):
                if requirement not in covered:
                    gap(qid, 'coverage 필수 내용 누락: ' + requirement)
            for item in coverage:
                if item.get('requirement') not in contracts[qid].get('required_data', []):
                    errors.append(qid + ': 알 수 없는 coverage requirement ' + str(item.get('requirement')))
                claim(item.get('claim'), qid + ' coverage ' + str(item.get('requirement')))
            refs = q.get('evidence_ids', [])
            if not isinstance(refs, list) or any(not isinstance(x, str) for x in refs):
                errors.append(qid + ': evidence_ids 배열 필요')
            else:
                for eid in refs:
                    if eid not in evidence: errors.append(qid + ': 존재하지 않는 근거 ' + eid)
            visuals = q.get('visual_refs', [])
            if not isinstance(visuals, list) or any(not isinstance(x, dict) for x in visuals):
                errors.append(qid + ': visual_refs는 객체 배열이어야 합니다'); continue
            for visual in visuals:
                slide = slide_lookup.get(visual.get('slide_id'))
                if not slide:
                    errors.append(qid + ': visual_refs 슬라이드가 없습니다'); continue
                block_ids = {b.get('id') for b in slide.get('blocks', []) if isinstance(b, dict)}
                if visual.get('block_id') not in block_ids:
                    errors.append(qid + ': visual_refs 블록이 없습니다')
    return {'errors': errors, 'warnings': warnings, 'complete': not errors and not gaps, 'gaps': gaps}


BLOCK_FIELDS = {
    'text': ('text',), 'metric': ('value', 'detail'),
    'image': ('path', 'caption', 'source', 'rights', 'alt'),
    'table': ('columns', 'rows'),
    'chart': ('chart_type', 'categories', 'series', 'unit', 'source'),
    'steps': ('items',), 'mapping': ('items',), 'formula': ('items',),
    'roadmap': ('items',), 'team': ('items',),
}
ITEM_FIELDS = {'steps': ('title', 'text'), 'mapping': ('problem', 'solution', 'proof'),
               'formula': ('label', 'formula', 'result', 'basis'),
               'roadmap': ('period', 'title', 'deliverables', 'gate'),
               'team': ('name', 'role', 'proof', 'contribution')}
TEXT_FIELDS = {'text', 'title', 'value', 'detail', 'caption', 'alt', 'problem', 'solution',
               'proof', 'label', 'formula', 'result', 'basis', 'period', 'gate', 'name',
               'role', 'contribution'}


def validate_blocks(slide, evidence, validate_claim):
    errors = []
    sid = str(slide.get('id', '?'))
    blocks = slide.get('blocks', [])
    if not isinstance(blocks, list) or any(not isinstance(b, dict) for b in blocks):
        return [sid + ': blocks는 객체 배열이어야 합니다']
    if not blocks:
        return [sid + ': blocks 내용이 비어 있습니다']
    ids = [b.get('id') for b in blocks]
    if any(not isinstance(b, str) or not b for b in ids) or len(ids) != len(set(ids)):
        errors.append(sid + ': block id 누락/중복')
    types={b.get('type') for b in blocks if isinstance(b.get('type'),str)}
    layout=slide.get('layout')
    # These limits describe implemented renderer layouts, not 정석biz 노하우 content quotas.
    layout_required={
        'problem_solution': [('mapping',), ('text','image')],
        'product_journey': [('steps',), ('text',)],
        'market_model': [('formula',), ('text','chart')],
        'competition_matrix': [('table',), ('text',)],
        'roadmap_funding': [('roadmap',), ('metric',), ('text','table')],
        'milestone_roadmap': [('roadmap',)],
        'team_evidence': [('team',), ('text',)],
        'evidence_board': [('image','chart','table','metric'), ('text',)],
    }
    for alternatives in layout_required.get(layout,[]):
        if not any(t in types for t in alternatives):
            errors.append(sid+': '+str(layout)+' layout에 '+ '/'.join(alternatives)+' block 필요')
    if layout=='milestone_roadmap':
        if sum(b.get('type')=='roadmap' for b in blocks)!=1:
            errors.append(sid+': milestone_roadmap에는 roadmap block이 정확히 1개 필요합니다')
        auxiliary=[b for b in blocks if b.get('type')!='roadmap']
        if len(auxiliary)>2 or any(b.get('type') not in ('text','metric') for b in auxiliary):
            errors.append(sid+': milestone_roadmap 보조 block은 text/metric 최대 2개입니다')
    if layout=='evidence_board' and sum(b.get('type') in ('image','chart','table','metric') for b in blocks)>2:
        errors.append(sid+': evidence_board는 시각자료 2개까지 지원합니다. 별도 장표로 나누세요')

    def required(obj, fields, label):
        for field in fields:
            value = obj.get(field)
            if value is None or value == '' or value == []:
                errors.append(label + ': 필수 내용 ' + field + ' 필요')

    def descendant(obj, parent, label):
        # Claims inherit epistemic labels; explicit child labels override them.
        context = {key: obj.get(key, parent.get(key)) for key in ('kind', 'evidence_ids', 'scope', 'disclosure')}
        words = [str(obj[k]) for k in TEXT_FIELDS if k in obj and isinstance(obj[k], (str, int, float))]
        for key in ('columns', 'rows', 'deliverables', 'categories', 'values'):
            if key in obj: words.append(json.dumps(obj[key], ensure_ascii=False))
        text = ' '.join(words)
        if text:
            # The renderer displays kind for every block/item, so its visible
            # label is part of the claim. No prefix is added for facts.
            prefix = {'plan': '계획: ', 'assumption': '가정: '}.get(context['kind'], '')
            errors.extend(validate_claim({'text': prefix + text, 'kind': context['kind'],
                                          'evidence_ids': context['evidence_ids'],
                                          'scope': context['scope']}, evidence, label))
        for key in ('items', 'series'):
            for i, item in enumerate(obj.get(key, []) if isinstance(obj.get(key, []), list) else []):
                if isinstance(item, dict): descendant(item, context, f'{label}.{key}[{i}]')
        if isinstance(obj.get('asset'), dict): descendant(obj['asset'], context, label + '.asset')

    for i, block in enumerate(blocks):
        label = f'{sid} block[{i}]'
        kind = block.get('type')
        if kind not in BLOCK_FIELDS:
            errors.append(label + ': 알 수 없는 block type ' + str(kind)); continue
        required(block, ('id', 'title', 'kind') + BLOCK_FIELDS[kind], label)
        if 'evidence_ids' not in block: errors.append(label + ': evidence_ids 필요')
        descendant(block, {}, label)
        if kind in ITEM_FIELDS:
            items = block.get('items')
            if not isinstance(items, list) or not items or any(not isinstance(x, dict) for x in items):
                errors.append(label + ': items는 비어 있지 않은 객체 배열이어야 합니다')
            else:
                upper=3 if kind=='formula' else 4
                if not 2<=len(items)<=upper:
                    errors.append(label+f': 현재 renderer의 {kind} items는 2~{upper}개를 지원합니다')
                for j, item in enumerate(items):
                    required(item, ITEM_FIELDS[kind], f'{label}.items[{j}]')
                    if kind == 'roadmap' and (not isinstance(item.get('deliverables'), list)
                            or any(not isinstance(x, str) for x in item.get('deliverables', []))):
                        errors.append(label + ': roadmap deliverables는 문자열 배열이어야 합니다')
        if kind == 'table':
            columns, rows = block.get('columns'), block.get('rows')
            if not isinstance(columns, list) or len(columns) < 2 or any(not isinstance(x, str) for x in columns):
                errors.append(label + ': table columns에 비교 열 2개 이상 필요')
            elif layout=='competition_matrix' and len(columns)<3:
                errors.append(label+': competition_matrix에는 비교 columns 3개 이상 필요')
            if not isinstance(rows, list) or not rows:
                errors.append(label + ': table rows 필요')
            elif isinstance(columns, list) and any(not isinstance(row, list) or len(row) != len(columns)
                    or any(not isinstance(cell, str) for cell in row) for row in rows):
                errors.append(label + ': table 각 행의 열 수는 columns와 같아야 합니다')
        if kind == 'chart':
            categories, series = block.get('categories'), block.get('series')
            if block.get('chart_type') not in ('bar', 'line'):
                errors.append(label + ': chart_type은 bar/line이어야 합니다')
            if not isinstance(categories, list) or not categories or any(not isinstance(x, str) for x in categories):
                errors.append(label + ': chart categories 문자열 배열 필요')
            if not isinstance(series, list) or not series or any(not isinstance(x, dict) for x in series):
                errors.append(label + ': chart series 객체 배열 필요')
            else:
                for item in series:
                    values = item.get('values')
                    if not item.get('name') or not isinstance(values, list) or not isinstance(categories, list) or len(values) != len(categories):
                        errors.append(label + ': chart series name/values와 categories 수를 확인하세요')
                    elif any(not isinstance(v, (int, float)) or isinstance(v, bool) for v in values):
                        errors.append(label + ': chart values에는 숫자만 허용됩니다')
        if kind == 'image' and block.get('rights') not in ('owned', 'licensed', 'permission', 'public-domain'):
            errors.append(label + ': 이미지 사용권 확인 필요')
    return errors


VISUAL_VARIANTS = {
    'evidence_focus': ('image', 'chart', 'table', 'metric', 'text', 'steps', 'mapping'),
    'comparison_focus': ('table', 'mapping'),
    'product_hero': ('image', 'steps'),
    'market_layers': ('formula',),
    'timeline_focus': ('steps', 'roadmap'),
    'team_focus': ('team',),
    'cover_focus': tuple(BLOCK_FIELDS),
}
VISUAL_REVIEW_CHECKS = ('text_overflow', 'font_substitution', 'contrast', 'chart_labels',
                        'image_crops', 'hierarchy', 'evidence_legibility', 'composition_variation')


def block_images(block):
    """Return image records with the containing item's evidence inheritance."""
    if not isinstance(block, dict):
        return []
    if block.get('type') == 'image':
        return [block]
    images = []
    items = block.get('items', [])
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get('asset'), dict):
                continue
            asset = dict(item['asset'])
            asset.setdefault('evidence_ids', item.get('evidence_ids', block.get('evidence_ids', [])))
            images.append(asset)
    return images


def validate_visual_brief(slide, evidence, required=False, final=False):
    """Check visual decisions and references; never claim to measure design quality.

    Missing briefs/assets remain disclosed draft gaps until the design gate.
    Invalid supplied references and incompatible variants always fail.
    """
    errors, warnings, gaps = [], [], []
    label = str(slide.get('id', '?')) + ' visual_brief'

    def gap(message):
        item = label + ': ' + message
        gaps.append(item)
        (errors if final else warnings).append(item)

    brief = slide.get('visual_brief')
    blocks = slide.get('blocks', [])
    blocks = [b for b in blocks if isinstance(b, dict)] if isinstance(blocks, list) else []
    if 'visual_brief' not in slide:
        if required:
            gap('핵심 메시지·주요 블록·읽는 순서·구성·이유를 작성하세요 (design 전에 필요)')
    elif not isinstance(brief, dict):
        errors.append(label + ': 객체여야 합니다')
    else:
        for key in ('key_message', 'primary_block_id', 'layout_variant', 'visual_reason'):
            if not isinstance(brief.get(key), str) or not brief[key].strip():
                errors.append(label + ': ' + key + '에 구체적인 내용을 입력하세요')
        lookup = {b['id']: b for b in blocks if isinstance(b.get('id'), str) and b['id']}
        primary_id = brief.get('primary_block_id')
        primary = lookup.get(primary_id) if isinstance(primary_id, str) else None
        if primary is None:
            errors.append(label + ': primary_block_id가 실제 blocks의 ID를 참조해야 합니다')
        order = brief.get('reading_order')
        if (not isinstance(order, list) or any(not isinstance(x, str) for x in order)
                or len(order) != len(set(order)) or set(order) != set(lookup)
                or len(order) != len(blocks) or not order):
            errors.append(label + ': reading_order에 모든 block ID를 중복·누락 없이 한 번씩 쓰세요')
        variant = brief.get('layout_variant')
        allowed = VISUAL_VARIANTS.get(variant) if isinstance(variant, str) else None
        if allowed is None:
            errors.append(label + ': layout_variant는 ' + ', '.join(VISUAL_VARIANTS) + ' 중 하나입니다')
        elif primary is not None and primary.get('type') not in allowed:
            errors.append(label + ': ' + variant + '의 primary block은 ' + '/'.join(allowed) + '여야 합니다')
        if variant == 'product_hero' and (primary is None or not block_images(primary)):
            errors.append(label + ': product_hero primary에 image 또는 화면 asset을 가진 steps가 필요합니다')

    # A v1.4 product slide cannot quietly fall back to a text-only journey.
    images = [asset for block in blocks for asset in block_images(block)]
    if required and slide.get('section') == 'product' and not images:
        gap('제품 장표에 원본 화면·사진 또는 가상 설계임을 표시한 image/steps.asset이 필요합니다')
    primary_images = []
    if isinstance(brief, dict) and brief.get('layout_variant') == 'product_hero':
        primary_images = block_images(next((b for b in blocks if b.get('id') == brief.get('primary_block_id')), {}))
    checked_images = images if required and slide.get('section') == 'product' else primary_images
    for asset in checked_images:
        for key in ('path', 'source'):
            if not isinstance(asset.get(key), str) or not asset[key].strip():
                errors.append(label + ': 제품 이미지 ' + key + '를 원본 자산에 연결하세요')
        refs = asset.get('evidence_ids')
        if not isinstance(refs, list) or not refs or any(not isinstance(ref, str) for ref in refs):
            errors.append(label + ': 제품 이미지 evidence_ids에 원본 근거를 연결하세요')
        else:
            for ref in refs:
                if ref not in evidence:
                    errors.append(label + ': 제품 이미지의 근거가 없습니다: ' + ref)
    return {'errors': errors, 'warnings': warnings, 'gaps': gaps, 'complete': not errors and not gaps}


def validate_visual_review(review, slide_ids, label):
    """Require written observations of actual renderings, not numeric design scores."""
    errors = []
    if not isinstance(review, dict):
        return [label + ': 시각검수 객체가 필요합니다']
    checks = review.get('checks', {})
    checks = checks if isinstance(checks, dict) else {}
    for key in VISUAL_REVIEW_CHECKS:
        if checks.get(key) != 'pass':
            errors.append(label + ': 실제 렌더 시각검수 항목 필요: ' + key)
    for key in ('reviewer', 'rationale', 'composition_review'):
        if not isinstance(review.get(key), str) or not review[key].strip():
            errors.append(label + ': ' + key + '에 검토자·관찰 근거·연속 장표 구성 판단을 기록하세요')
    observations = review.get('visual_observations')
    if not isinstance(observations, list) or any(not isinstance(row, dict) for row in observations):
        observations = []
    ids = [row.get('slide_id') for row in observations]
    if any(not isinstance(sid, str) for sid in ids) or sorted(ids) != sorted(slide_ids):
        errors.append(label + ': visual_observations에 모든 slide_id를 각각 한 번 기록하세요')
    for row in observations:
        for key in ('hierarchy', 'evidence_legibility'):
            if not isinstance(row.get(key), str) or not row[key].strip():
                errors.append(label + ': ' + str(row.get('slide_id')) + ' ' + key + '의 실제 관찰 내용을 기록하세요')
    return errors


def validate_slide_blocks(slide, evidence_map):
    """Renderer API; same claim validation as the cumulative harness gate."""
    spec = importlib.util.spec_from_file_location('seed_ir_claim_validation', Path(__file__).with_name('harness.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return validate_blocks(slide, evidence_map, module.validate_claim)
