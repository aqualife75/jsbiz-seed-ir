#!/usr/bin/env python3
"""Local, evidence-first state and quality gates. Does not call a model or the web."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import sys
import time
import zipfile

_quality_spec = importlib.util.spec_from_file_location('seed_ir_quality', Path(__file__).with_name('quality.py'))
quality = importlib.util.module_from_spec(_quality_spec)
_quality_spec.loader.exec_module(quality)
_visual_plan_spec = importlib.util.spec_from_file_location('seed_ir_visual_plan', Path(__file__).with_name('visual_plan.py'))
visual_plan = importlib.util.module_from_spec(_visual_plan_spec)
_visual_plan_spec.loader.exec_module(visual_plan)

STAGES = ['intake', 'evidence', 'story', 'research', 'review', 'design', 'pitch']
CURRICULUM = quality.load_curriculum('1.2')
SECTIONS = [topic['id'] for topic in CURRICULUM['topics']]
TIMES = [seconds for topic in CURRICULUM['topics'] for seconds in topic['default_slide_seconds']]
DEPENDENCIES = {
    'intake':['input', 'data/raw', 'reviews/extraction.json'],
    'evidence':['evidence'], 'story':['deck'], 'research':['research'],
    'review':['reviews/investor.json'],
    'design':['design', 'output/seed-ir-draft.pptx', 'output/renders',
              'output/master/seed-ir-draft.pptx', 'output/master/renders',
              'output/pitch/seed-ir-draft.pptx', 'output/pitch/renders', 'reviews/visual.json'],
    'pitch':['reviews/pitch.json', 'output/pitch-script.md'],
}


def now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp=path.with_name(path.name+'.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    # Windows sync/antivirus readers can briefly lock the destination. Keep the
    # old file intact and retry only the atomic replacement, never delete it.
    for attempt,delay in enumerate((0,.05,.1,.2,.4)):
        if delay: time.sleep(delay)
        try:
            tmp.replace(path)
            return
        except PermissionError:
            if attempt==4: raise


def read_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path: Path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def safe_path(project: Path, relative: str):
    p=(project/relative).resolve()
    if not p.is_relative_to(project.resolve()):
        raise ValueError('프로젝트 밖 경로: '+relative)
    return p


INTERNAL_DIRECTORIES = frozenset(('data', 'evidence', 'deck', 'research', 'reviews',
    'design', 'output', 'work', '.agents', '.codex', '.venv', 'node_modules', '결과물'))


def input_directory(project: Path, config=None):
    """Resolve a configurable input folder without overlapping internal state."""
    project=project.resolve()
    if config is None:
        config=read_json(project/'project.json') if (project/'project.json').is_file() else {}
    relative=config.get('input_dir','input')
    if not isinstance(relative,str) or not relative.strip():
        raise ValueError('input_dir에는 프로젝트 안의 자료 폴더 이름이 필요합니다')
    relative=relative.replace('\\','/')
    parts=relative.split('/')
    if relative.startswith('/') or ':' in relative or any(part in ('','.', '..') for part in parts):
        raise ValueError('input_dir는 프로젝트 안의 상대 폴더여야 합니다: '+relative)
    blocked={part.casefold() for part in INTERNAL_DIRECTORIES}
    if any(part.casefold() in blocked for part in parts):
        raise ValueError('자료 폴더가 내부 작업/결과 폴더와 겹칩니다: '+relative)
    path=safe_path(project,relative)
    if path==project or any(part.casefold() in blocked for part in path.relative_to(project).parts):
        raise ValueError('자료 폴더가 프로젝트 루트 또는 내부 작업 폴더와 겹칩니다: '+relative)
    if path.exists() and not path.is_dir():
        raise ValueError('자료 폴더 경로가 폴더가 아닙니다: '+relative)
    return path


def image_records(value):
    """Walk both legacy assets and images nested in rich blocks/items."""
    if isinstance(value,dict):
        if value.get('type')=='image' or 'path' in value:
            yield value
        for nested in value.values():
            yield from image_records(nested)
    elif isinstance(value,list):
        for nested in value:
            yield from image_records(nested)


def referenced_image_paths(project: Path):
    deck_path=project/'deck/deck.json'
    if not deck_path.is_file(): return []
    deck=read_json(deck_path)
    if not isinstance(deck,dict): raise ValueError('deck.json은 객체여야 합니다')
    paths=set()
    for slide in deck.get('slides',[]):
        if not isinstance(slide,dict): continue
        for value in (slide.get('assets',[]),slide.get('blocks',[]),slide.get('visual_brief',{})):
            for asset in image_records(value):
                relative=asset.get('path')
                if isinstance(relative,str) and relative:
                    paths.add(safe_path(project,relative).relative_to(project.resolve()).as_posix())
    return sorted(paths)


def fingerprint(project: Path, stage: str):
    project=project.resolve()
    input_rel=input_directory(project).relative_to(project).as_posix()
    paths=['project.json']
    for s in STAGES[:STAGES.index(stage)+1]:
        paths.extend(input_rel if s=='intake' and rel=='input' else rel for rel in DEPENDENCIES[s])
    if STAGES.index(stage)>=STAGES.index('story'):
        paths.extend(referenced_image_paths(project))
    h=hashlib.sha256()
    for rel in sorted(set(paths)):
        p=project/rel
        files=sorted(p.rglob('*')) if p.is_dir() else [p]
        if not p.exists():
            h.update(('missing:'+rel).encode())
        for f in files:
            if f.is_file():
                if not f.resolve().is_relative_to(project.resolve()):
                    raise ValueError('프로젝트 밖 symlink를 검사할 수 없습니다')
                if rel==input_rel and not f.resolve().is_relative_to(input_directory(project)):
                    raise ValueError('자료 폴더 밖 symlink 원본은 사용할 수 없습니다')
                h.update(f.relative_to(project).as_posix().encode())
                h.update(sha(f).encode())
    return h.hexdigest()


def initial_slides():
    slides=[]
    for topic in CURRICULUM['topics']:
        for part,seconds in enumerate(topic['default_slide_seconds'],1):
            section=topic['id']; i=len(slides)+1
            slides.append({'id':f'S{i:02}','section':section,'section_ids':[section],
                'governing_message':'','governing_kind':'fact','governing_evidence_ids':[],
                'body':[],'evidence_ids':[],'assets':[],
                'layout':'cover' if section=='cover' else 'closing' if section=='vision' else 'evidence',
                'seconds':seconds,'speaker_notes':'','visual':{'type':'none'}})
    return slides


def initial_section_map():
    return {'schema_version':'1.2','sections':[
        {'section':section,'evidence_ids':[],'asset_ids':[],
         'missing_data':['이 목차에 필요한 원본 자료를 검토하세요']} for section in SECTIONS]}


def initial_deck(team, target_seconds=300):
    slides=initial_slides()
    return {'schema_version':'1.2','team_name':team,'slides':slides,
        'views':{'master':{'slide_ids':[s['id'] for s in slides]},
                 'pitch':{'slide_ids':[s['id'] for s in slides],'target_seconds':target_seconds}}}


def initialize(project: Path, team: str, input_dir: str='input'):
    project=project.resolve()
    if (project/'project.json').exists() or (project/'state.json').exists():
        raise FileExistsError('이미 초기화된 프로젝트입니다. status를 사용하세요.')
    input_path=input_directory(project,{'input_dir':input_dir})
    input_relative=input_path.relative_to(project).as_posix()
    targets=[input_relative,'data/raw','evidence','deck','research','reviews','design','output','work']
    # Never overwrite user evidence when initialization is accidentally repeated.
    for rel in ['evidence/evidence.json','evidence/section-map.json','deck/deck.json','deck/section-briefs.json']:
        if (project/rel).exists():
            raise FileExistsError('기존 자료를 보존합니다: '+rel)
    for t in targets:
        safe_path(project,t).mkdir(parents=True,exist_ok=True)
    write_json(project/'project.json',{'schema_version':'1.2','team_name':team,
        'input_dir':input_relative,
        'created_at':now(),'pitch_target_seconds':300,'max_revision_rounds':2,
        'research_required':True,'data_policy':'one-team-per-project',
        'harness_version':'1.5.1','require_visual_briefs':True,'require_visual_plan':True})
    write_json(project/'state.json',{'schema_version':'1.0','checkpoints':{},'events':[]})
    write_json(project/'evidence/evidence.json',{'schema_version':'1.0','items':[]})
    write_json(project/'evidence/section-map.json',initial_section_map())
    write_json(project/'deck/deck.json',initial_deck(team))
    write_json(project/'deck/section-briefs.json',quality.initial_briefs())
    profile=Path(__file__).resolve().parents[1]/'references/design-profile.json'
    if profile.exists() and not (project/'design/design-profile.json').exists():
        shutil.copyfile(profile,project/'design/design-profile.json')


def migrate(project: Path):
    """Back up legacy work before creating unresolved v1.2 section scaffolds."""
    project=project.resolve()
    path=project/'deck/deck.json'
    deck=read_json(path)
    version='.'.join(str(deck.get('schema_version','1.0')).split('.')[:2])
    if version=='1.2':
        if not (project/'deck/section-briefs.json').exists():
            write_json(project/'deck/section-briefs.json',quality.initial_briefs())
        return {'migrated':False,'schema_version':'1.2','note':'기존 v1.2 자료를 보존했습니다'}
    if version not in ('1.0','1.1'): raise ValueError('지원하지 않는 이행 원본 버전: '+version)
    quality.select_slides(deck,'master')
    config=read_json(project/'project.json')
    files=['deck/deck.json','deck/section-briefs.json','evidence/section-map.json','project.json']
    backups={relative:str(Path(relative).with_name(Path(relative).stem+f'.pre-v1.2.v{version}.json'))
             for relative in files if (project/relative).is_file()}
    for relative in list(backups)+list(backups.values()): safe_path(project,relative)
    for relative in backups.values():
        if (project/relative).exists(): raise FileExistsError('기존 이행 백업을 보존합니다: '+relative)
    for source,destination in backups.items(): shutil.copyfile(project/source,project/destination)
    config['schema_version']='1.2'
    config['pitch_target_seconds']=300
    write_json(project/'project.json',config)
    write_json(path,initial_deck(deck.get('team_name',config.get('team_name','팀명')),config.get('pitch_target_seconds',300)))
    write_json(project/'deck/section-briefs.json',quality.initial_briefs())
    write_json(project/'evidence/section-map.json',initial_section_map())
    return {'migrated':True,'schema_version':'1.2','backup':backups['deck/deck.json'],'backups':backups,
            'note':'기존 원고·질문·목차 맵·설정을 백업했습니다. 원문과 근거는 유지합니다. 새 목차의 빈 18장과 질문을 백업에서 재작성하고 검수하세요.'}


def validate_claim(claim: dict, evidence: dict, label: str):
    errors=[]
    if not isinstance(claim,dict): return [label+': 주장은 JSON 객체여야 합니다']
    text=claim.get('text','')
    kind=claim.get('kind')
    if not isinstance(text,str) or not text.strip():
        return [label+': 빈 주장']
    if kind not in ('fact','assumption','plan'):
        return [label+': kind는 fact/assumption/plan이어야 합니다']
    refs=claim.get('evidence_ids',[])
    if not isinstance(refs,list) or any(not isinstance(e,str) for e in refs):
        return [label+': evidence_ids 배열 필요']
    if kind=='fact' and not refs:
        errors.append(label+': 사실 주장에 evidence_ids 필요')
    if kind=='assumption' and not any(s in text for s in ('가정','추정','예시')):
        errors.append(label+': 가정/추정/예시를 화면 문구에 표시하세요')
    if kind=='plan' and not any(s in text for s in ('목표','계획','예정','검증할')):
        errors.append(label+': 목표/계획/예정을 화면 문구에 표시하세요')
    for eid in refs:
        if eid not in evidence:
            errors.append(label+': 존재하지 않는 근거 '+str(eid))
        elif kind=='fact' and (evidence[eid].get('status')!='confirmed' or evidence[eid].get('kind')=='assumption'):
            errors.append(label+': 확인되지 않은 근거 '+str(eid))
    company = claim.get('scope')=='company' or bool(re.search(r'(당사|우리|자사).{0,12}(매출|고객|계약|실적|효능|전환|유료)',text))
    if kind=='fact' and company and not any(evidence.get(e,{}).get('kind')=='internal' for e in refs):
        errors.append(label+': 회사 실적은 internal 근거가 필요합니다')
    return errors


def check(project: Path, stage: str):
    """Cumulative checks. Errors block; warnings must be disclosed to the user."""
    project=project.resolve()
    errors=[]; warnings=[]
    upto=len(STAGES)-1 if stage=='final' else STAGES.index(stage)
    def get(rel,default):
        p=project/rel
        if not p.exists():
            errors.append('필수 파일 없음: '+rel); return default
        try:
            result=read_json(p)
            if not isinstance(result,type(default)):
                raise ValueError('잘못된 최상위 타입')
            return result
        except (ValueError,OSError) as e:
            errors.append('JSON 읽기 실패 '+rel+': '+str(e)); return default
    def rows(obj,key):
        value=obj.get(key,[])
        if not isinstance(value,list) or any(not isinstance(x,dict) for x in value):
            errors.append('JSON '+key+'는 객체 배열이어야 합니다'); return []
        return value
    config=get('project.json',{})
    if 'require_visual_briefs' in config and not isinstance(config['require_visual_briefs'],bool):
        errors.append('project.json require_visual_briefs는 true/false여야 합니다')
    if 'require_visual_plan' in config and not isinstance(config['require_visual_plan'],bool):
        errors.append('project.json require_visual_plan은 true/false여야 합니다')
    curriculum=quality.load_curriculum(config.get('schema_version','1.0'))
    sections_expected=[topic['id'] for topic in curriculum['topics']]
    inventory=get('data/raw/inventory.json',{})
    documents=get('data/raw/documents.json',{})
    raw_assets=get('data/raw/assets.json',{})
    files=rows(inventory,'files')
    segments=rows(documents,'segments')
    asset_rows=rows(raw_assets,'assets')
    if not files: errors.append('입력 자료가 없습니다')
    if not documents.get('segments') and not documents.get('ocr_queue'):
        errors.append('추출된 본문/검토 가능한 시각자료가 없습니다')
    extraction={}
    if (project/'reviews/extraction.json').exists():
        extraction=get('reviews/extraction.json',{})
        inv_sha=sha(project/'data/raw/inventory.json') if (project/'data/raw/inventory.json').exists() else ''
        if extraction.get('inventory_sha256')!=inv_sha:
            errors.append('추출 검토가 현재 inventory와 다릅니다')
            extraction={}
    covered=set(extraction.get('reviewed_source_ids',[]))
    for f in files:
        if f.get('status') in ('error','unsupported','partial') and f.get('source_id') not in covered:
            errors.append('추출 문제 검토 필요: '+f.get('source_file',f.get('source_id','?')))
    if documents.get('ocr_queue') and not extraction.get('ocr_review_complete'):
        errors.append('스캔/이미지 OCR 또는 직접 시각검토 기록 필요')
    source_ids={f.get('source_id') for f in files}
    source_ids.discard(None)
    source_ids.discard('')
    try:
        input_root=input_directory(project,config)
        current={p.relative_to(input_root).as_posix():p for p in input_root.rglob('*') if p.is_file()}
    except (OSError,ValueError,TypeError) as e:
        errors.append('자료 폴더 확인 실패: '+str(e)); input_root=project/'input'; current={}
    indexed={f.get('source_file') for f in files if isinstance(f.get('source_file'),str)}
    if set(current)!=indexed:
        errors.append('자료 폴더 파일 목록이 추출 목록과 다릅니다. 자료를 다시 ingest 하세요')
    for f in files:
        rel=f.get('source_file')
        if not f.get('source_id') or not f.get('sha256') or not rel:
            errors.append('inventory에 source_id/source_file/sha256이 필요합니다'); continue
        actual=current.get(rel)
        if actual:
            if not actual.resolve().is_relative_to(input_root):
                errors.append('자료 폴더 밖 symlink 원본은 사용할 수 없습니다: '+rel)
            elif sha(actual)!=f['sha256']:
                errors.append('원본이 바뀌었습니다. 다시 ingest 하세요: '+rel)
    for segment in segments:
        if segment.get('source_id') not in source_ids or not segment.get('locator'):
            errors.append('추출 본문 source_id/locator가 원본 목록과 연결되지 않습니다')
    for asset in asset_rows:
        if asset.get('source_id') not in source_ids or not asset.get('locator'):
            errors.append('추출 이미지 source_id/locator가 원본 목록과 연결되지 않습니다')
        try:
            path=safe_path(project,'data/raw/'+asset.get('path',''))
            if not path.is_file() or sha(path)!=asset.get('sha256'):
                errors.append('추출 이미지 파일 또는 지문 불일치: '+str(asset.get('asset_id')))
        except (ValueError,TypeError) as e: errors.append(str(e))
    evidence={}
    if upto>=1:
        data=get('evidence/evidence.json',{})
        for item in rows(data,'items'):
            eid=item.get('id')
            if not eid or eid in evidence: errors.append('근거 ID 누락/중복: '+str(eid))
            evidence[eid]=item
            if not item.get('claim'): errors.append(str(eid)+': claim 필요')
            if item.get('status') not in ('confirmed','unverified','contradicted'):
                errors.append(str(eid)+': status 확인 필요')
            kind=item.get('kind')
            if kind=='internal':
                if item.get('source_id') not in source_ids: errors.append(str(eid)+': 내부 source_id 불일치')
                if not item.get('locator'): errors.append(str(eid)+': 페이지/표/행 locator 필요')
            elif kind=='external':
                for key in ('url','publisher','accessed_at','locator','verification_note'):
                    if not item.get(key): errors.append(str(eid)+': 외부 근거 '+key+' 필요')
                if not re.match(r'^https?://',item.get('url','')): errors.append(str(eid)+': 실제 출처 URL 필요')
            elif kind!='assumption': errors.append(str(eid)+': kind 오류')
        if not evidence: errors.append('근거 데이터가 비어 있습니다')
        mapping=rows(get('evidence/section-map.json',{}),'sections')
        if sorted(x.get('section','') for x in mapping)!=sorted(sections_expected):
            errors.append(f'section-map에는 지정된 {len(sections_expected)}목차를 각각 한 번씩 저장하세요')
        asset_ids={a.get('asset_id') for a in asset_rows}
        for section in mapping:
            label=section.get('section','?')
            for eid in section.get('evidence_ids',[]):
                if eid not in evidence: errors.append(label+': 목차 데이터의 존재하지 않는 근거 '+str(eid))
            for aid in section.get('asset_ids',[]):
                if aid not in asset_ids: errors.append(label+': 목차 데이터의 존재하지 않는 이미지 '+str(aid))
            if not section.get('evidence_ids') and not section.get('missing_data'):
                errors.append(label+': 자료가 없으면 missing_data에 필요한 자료를 기록하세요')
    slides=[]
    semantic_complete=False
    semantic_report={'errors':[],'warnings':[],'complete':False,'gaps':[]}
    deck={}
    master_slides=[]
    pitch_slides=[]
    deck_path=project/'deck/deck.json'
    deck_sha=sha(deck_path) if deck_path.exists() else ''
    if upto>=2:
        deck=get('deck/deck.json',{}); slides=rows(deck,'slides')
        if not slides: errors.append('장표가 없습니다')
        version='.'.join(str(deck.get('schema_version','1.0')).split('.')[:2])
        if version not in ('1.0','1.1','1.2'): errors.append('지원하지 않는 deck schema_version')
        is_v11=version in ('1.1','1.2')
        curriculum=quality.load_curriculum(version)
        sections_expected=[topic['id'] for topic in curriculum['topics']]
        try:
            master_slides=quality.select_slides(deck,'master')
            pitch_slides=quality.select_slides(deck,'pitch')
        except ValueError as e:
            errors.append(str(e))
        main=[s for s in pitch_slides if not s.get('appendix')]
        for variant,selection in (('master',master_slides),('pitch',pitch_slides)):
            errors.extend(quality.validate_view_contract(deck,variant,curriculum))
            present={section for s in selection for section in quality.slide_sections(s)
                     if isinstance(section,str)}
            for section in sections_expected:
                if section not in present: errors.append(variant+' 정석biz 노하우 목차 누락: '+section)
        master_ids={s.get('id') for s in master_slides}
        master_by_id={s.get('id'):s for s in master_slides}
        for s in pitch_slides:
            refs=s.get('source_slide_ids',[])
            if not isinstance(refs,list) or any(not isinstance(ref,str) or ref not in master_ids for ref in refs):
                errors.append(str(s.get('id'))+': source_slide_ids는 master 장표를 참조해야 합니다')
            elif is_v11 and s.get('id') not in master_ids and not refs:
                errors.append(str(s.get('id'))+': 압축 pitch 장표에 source_slide_ids가 필요합니다')
            elif version=='1.2' and any(master_by_id[ref].get('section')!=s.get('section') for ref in refs):
                errors.append(str(s.get('id'))+': v1.2 압축 pitch의 목차 연결 오류: 모든 원본 master 장표는 같은 목차여야 합니다')
            elif refs:
                source_sections={section for ref in refs for section in quality.slide_sections(master_by_id[ref])
                                 if isinstance(section,str)}
                if any(section not in source_sections for section in quality.slide_sections(s)):
                    errors.append(str(s.get('id'))+': 압축 pitch와 원본 master의 목차 연결이 일치하지 않습니다')
        briefs_path=project/'deck/section-briefs.json'
        if briefs_path.exists():
            briefs=get('deck/section-briefs.json',{})
            semantic_report=quality.validate_briefs(briefs,curriculum,evidence,slides,
                                                     validate_claim,final=stage=='final')
            errors.extend(semantic_report['errors']); warnings.extend(semantic_report['warnings'])
            semantic_complete=semantic_report['complete']
        else:
            message='deck/section-briefs.json 필요: migrate 후 투자자 질문별 답변과 누락을 기록하세요'
            (errors if stage=='final' or is_v11 else warnings).append(message)
        if version!='1.2':
            message='이전 버전 덱은 초안 호환 모드입니다. final 전에 migrate 명령으로 v1.2 목차 계약을 적용하세요'
            (errors if stage=='final' else warnings).append(message)
        ids=set()
        for s in slides:
            sid=s.get('id','?')
            if sid=='?' or sid in ids: errors.append('슬라이드 ID 누락/중복: '+sid)
            ids.add(sid)
            gm={'text':s.get('governing_message',''),'kind':s.get('governing_kind'),
                'evidence_ids':s.get('governing_evidence_ids',[]),'scope':s.get('governing_scope')}
            errors.extend(validate_claim(gm,evidence,sid+' governing'))
            if isinstance(gm['text'],str) and len(gm['text'])>66:
                (warnings if is_v11 else errors).append(sid+': 긴 핵심 메시지의 실제 렌더 가독성을 확인하세요')
            body=rows(s,'body')
            if not s.get('blocks') and len(body)>3: errors.append(sid+': legacy 본문 핵심 주장 3개 이내로 압축하세요')
            for i,claim in enumerate(body):
                errors.extend(validate_claim(claim,evidence,f'{sid} body[{i}]'))
            if 'blocks' in s:
                errors.extend(quality.validate_blocks(s,evidence,validate_claim))
            visual_report=quality.validate_visual_brief(s,evidence,
                required=config.get('require_visual_briefs',False) is True,final=upto>=5)
            errors.extend(visual_report['errors']); warnings.extend(visual_report['warnings'])
            sections=quality.slide_sections(s)
            if not sections or any(section not in sections_expected for section in sections):
                errors.append(sid+': 올바른 section/section_ids가 필요합니다')
            if not isinstance(s.get('seconds'),(int,float)) or s.get('seconds',0)<0:
                errors.append(sid+': seconds는 0 이상의 숫자여야 합니다')
            if not s.get('speaker_notes'): errors.append(sid+': 발표 대본 필요')
            images=rows(s,'assets')+list(image_records(s.get('blocks',[])))
            for a in images:
                if a.get('rights') not in ('owned','licensed','permission','public-domain'):
                    errors.append(sid+': 이미지 사용권 확인 필요')
                for key in ('path','caption','source','alt'):
                    if not a.get(key): errors.append(sid+': 이미지 '+key+' 필요')
                try:
                    if not safe_path(project,a.get('path','')).is_file(): errors.append(sid+': 이미지 파일 없음')
                except (ValueError,TypeError) as e: errors.append(str(e))
            visual=s.get('visual',{})
            if visual.get('type') not in (None,'none'):
                if not visual.get('evidence_ids') or not visual.get('source'):
                    errors.append(sid+': 차트/지표의 evidence_ids와 source 필요')
                for eid in visual.get('evidence_ids',[]):
                    if evidence.get(eid,{}).get('status')!='confirmed': errors.append(sid+': 차트 미검증 근거 '+str(eid))
        total=sum(s.get('seconds',0) for s in main if isinstance(s.get('seconds'),(int,float)))
        pitch_target=deck.get('views',{}).get('pitch',{}).get('target_seconds',config.get('pitch_target_seconds',300))
        if not isinstance(pitch_target,(int,float)) or not 0<pitch_target<=config.get('pitch_target_seconds',300):
            errors.append('pitch target_seconds는 프로젝트 발표시간 이내여야 합니다')
            pitch_target=config.get('pitch_target_seconds',300)
        if total>pitch_target: errors.append(f'계획 발표시간 초과: {total}초')
        if total<=0: errors.append('발표시간 배분 필요')
    if upto>=3 and config.get('research_required',True):
        research=get('research/search-log.json',{})
        queries=rows(research,'queries')
        if not queries: errors.append('검색 로그가 없습니다. 조사 범위와 실제 검색기록을 저장하세요')
        if not research.get('scope') or not research.get('limitations'):
            errors.append('research scope와 limitations 필요; 인터넷 전수조사 완료 주장 금지')
        for q in queries:
            for k in ('query','engine','accessed_at','selected_urls'):
                if k not in q: errors.append('검색 로그 필드 없음: '+k)
        for gap in rows(research,'gaps'):
            if gap.get('status') not in ('resolved','disclosed'):
                errors.append('미해결 근거 공백: '+str(gap.get('id')))
            if gap.get('status')=='disclosed' and not gap.get('disclosure_slide_id'):
                errors.append('근거 공백을 표시한 슬라이드 ID 필요')
            if gap.get('status')=='disclosed' and gap.get('disclosure_slide_id') not in {s.get('id') for s in slides}:
                errors.append('근거 공백을 표시한 실제 슬라이드가 없습니다')
    def review(rel,need_pptx=False):
        r=get(rel,{})
        if r.get('deck_sha256')!=deck_sha: errors.append(rel+': 현재 덱과 검수 지문 불일치')
        if r.get('verdict')!='pass': errors.append(rel+': pass 검수 필요')
        for finding in rows(r,'findings'):
            if finding.get('severity') in ('P0','P1') and finding.get('status')!='resolved':
                errors.append(rel+': 중대 지적 미해결 '+str(finding.get('id','')))
        if need_pptx:
            p=project/'output/seed-ir-draft.pptx'
            if not p.exists() or r.get('pptx_sha256')!=sha(p): errors.append(rel+': PPTX와 검수 지문 불일치')
        return r
    def review_sources(r,rel):
        if not str(deck.get('schema_version','1.0')).startswith(('1.1','1.2')): return
        for field,source in (('evidence_sha256','evidence/evidence.json'),
                             ('source_documents_sha256','data/raw/documents.json')):
            path=project/source
            if not path.is_file() or r.get(field)!=sha(path):
                errors.append(rel+': '+field+'가 현재 원문·근거와 다릅니다. 다시 검수하세요')
    if upto>=4:
        r=review('reviews/investor.json')
        review_sources(r,'reviews/investor.json')
        if not r.get('reviewer') or not r.get('rationale'): errors.append('투자자 검수 reviewer와 rationale 필요')
        if str(deck.get('schema_version','1.0')).startswith(('1.1','1.2')):
            briefs_path=project/'deck/section-briefs.json'
            if not briefs_path.exists() or r.get('briefs_sha256')!=sha(briefs_path):
                errors.append('투자자 검수 briefs_sha256이 현재 질문별 원고와 다릅니다')
            expected={c['id'] for t in curriculum['topics'] for c in quality.question_contracts(t)}
            verdicts=rows(r,'question_verdicts')
            if sorted(str(v.get('question_id','')) for v in verdicts)!=sorted(expected):
                errors.append('투자자 검수 question_verdicts에 모든 투자자 질문이 각각 한 번 필요합니다')
            for verdict in verdicts:
                if verdict.get('verdict')!='pass' or not verdict.get('rationale'):
                    errors.append('투자자 질문의 근거·논증 검토 미완료: '+str(verdict.get('question_id')))
    if upto>=5:
        get('design/design-profile.json',{})
        plan_path=project/'design/visual-plan.json'
        plan_report=visual_plan.validate(get('design/visual-plan.json',{}) if plan_path.exists() else None,
            deck,evidence,project,required=config.get('require_visual_plan',False) is True,final=True)
        errors.extend(plan_report['errors']); warnings.extend(plan_report['warnings'])
        r=review('reviews/visual.json',True)
        review_sources(r,'reviews/visual.json')
        if config.get('require_visual_briefs',False) is True:
            errors.extend(quality.validate_visual_review(r,[s.get('id') for s in pitch_slides],'pitch'))
        try:
            with zipfile.ZipFile(project/'output/seed-ir-draft.pptx') as z:
                if 'ppt/presentation.xml' not in z.namelist(): errors.append('유효한 PPTX presentation 없음')
                slide_count=len([n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',n)])
                if slide_count!=len(pitch_slides): errors.append('PPTX 슬라이드 수와 pitch view 불일치')
        except (OSError,zipfile.BadZipFile): errors.append('PPTX 파일을 열 수 없습니다')
        if r.get('render_method') not in ('powerpoint','libreoffice','artifact-tool'):
            errors.append('실제 PPTX 렌더를 검사하세요. HTML storyboard는 대체 증거가 아닙니다')
        if set(r.get('slides_reviewed',[]))!={s.get('id') for s in pitch_slides}:
            errors.append('모든 슬라이드 시각검토 필요')
        renders=r.get('render_files',[])
        if len(renders)!=len(pitch_slides) or not renders: errors.append('슬라이드별 실제 렌더 파일 필요')
        for rel in renders:
            try:
                p=safe_path(project,rel)
                if not p.is_file() or p.suffix.lower() not in ('.png','.jpg','.jpeg'): errors.append('렌더 이미지 없음: '+rel)
                elif not p.read_bytes()[:8].startswith((b'\x89PNG\r\n\x1a\n',b'\xff\xd8\xff')):
                    errors.append('렌더 파일이 이미지가 아닙니다: '+rel)
            except ValueError as e: errors.append(str(e))
        if r.get('deck_sha256')==deck_sha:
            for k in ('text_overflow','font_substitution','contrast','chart_labels','image_crops'):
                if r.get('checks',{}).get(k)!='pass': errors.append('시각검수 항목 필요: '+k)
        if str(deck.get('schema_version','1.0')).startswith(('1.1','1.2')):
            views=r.get('views',{})
            master_review=views.get('master',{}) if isinstance(views,dict) else {}
            if not isinstance(master_review,dict): master_review={}
            if config.get('require_visual_briefs',False) is True:
                errors.extend(quality.validate_visual_review(master_review,
                    [s.get('id') for s in master_slides],'master'))
            master_path=project/'output/master/seed-ir-draft.pptx'
            if master_review.get('verdict')!='pass': errors.append('master 시각검수 pass 필요')
            if not master_path.exists() or master_review.get('pptx_sha256')!=sha(master_path):
                errors.append('master PPTX와 검수 지문 불일치')
            try:
                with zipfile.ZipFile(master_path) as z:
                    count=len([n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',n)])
                    if 'ppt/presentation.xml' not in z.namelist() or count!=len(master_slides):
                        errors.append('master PPTX 슬라이드 수와 master view 불일치')
            except (OSError,zipfile.BadZipFile): errors.append('master PPTX 파일을 열 수 없습니다')
            if master_review.get('render_method') not in ('powerpoint','libreoffice','artifact-tool'):
                errors.append('master의 실제 PPTX 렌더를 검사하세요')
            if set(master_review.get('slides_reviewed',[]))!={s.get('id') for s in master_slides}:
                errors.append('master의 모든 장표 시각검토 필요')
            render_files=master_review.get('render_files',[])
            if not isinstance(render_files,list) or len(render_files)!=len(master_slides) or not render_files:
                errors.append('master 장표별 실제 렌더 파일 필요'); render_files=[]
            for rel in render_files:
                try:
                    path=safe_path(project,rel)
                    if not path.is_file() or not path.read_bytes()[:8].startswith((b'\x89PNG\r\n\x1a\n',b'\xff\xd8\xff')):
                        errors.append('master 렌더 이미지 없음: '+str(rel))
                except (ValueError,TypeError) as e: errors.append(str(e))
            for key in ('text_overflow','font_substitution','contrast','chart_labels','image_crops'):
                if master_review.get('checks',{}).get(key)!='pass': errors.append('master 시각검수 항목 필요: '+key)
    if upto>=6:
        r=review('reviews/pitch.json',True)
        duration=r.get('duration_seconds',0)
        if not isinstance(duration,(int,float)) or not 0<duration<=config.get('pitch_target_seconds',300):
            errors.append('피칭 검수 duration_seconds가 0~300초 범위여야 합니다')
        if r.get('method')=='estimated':
            warnings.append('5분 적합성은 대본 기반 추정입니다. 발표자의 실제 리허설이 필요합니다')
            if not r.get('estimation_basis'): errors.append('시간 추정 근거(말하기 속도·전환시간) 필요')
        elif r.get('method')!='measured': errors.append('피칭 method는 estimated 또는 measured')
        if not (project/'output/pitch-script.md').is_file(): errors.append('output/pitch-script.md 필요')
    if stage=='final':
        try:
            for name,flag in status(project)['stages'].items():
                if flag!='passed': errors.append('단계 기록 재확인 필요: '+name+' ('+flag+')')
        except (OSError,ValueError,KeyError,TypeError): errors.append('유효한 state.json 단계 기록 필요')
    return {'stage':stage,'passed':not errors,'errors':errors,'warnings':warnings,'checked_at':now(),
            'semantic_complete':semantic_complete,'semantic_gaps':semantic_report['gaps']}


def status(project: Path):
    state=read_json(project/'state.json')
    out={}
    stale=False
    for s in STAGES:
        cp=state.get('checkpoints',{}).get(s)
        if not cp: out[s]='pending'
        elif stale or cp.get('fingerprint')!=fingerprint(project,s): out[s]='stale'; stale=True
        else: out[s]='passed'
    return {'stages':out,'next_stage':next((s for s in STAGES if out[s]!='passed'),None)}


def record(project: Path, stage: str):
    result=check(project,stage)
    if not result['passed']: raise ValueError('\n'.join(result['errors']))
    state=read_json(project/'state.json')
    idx=STAGES.index(stage)
    if idx:
        prev=STAGES[idx-1]
        if status(project)['stages'][prev]!='passed':
            raise ValueError('선행 단계부터 검증/기록하세요: '+prev)
    state['checkpoints'][stage]={'fingerprint':fingerprint(project,stage),'at':now()}
    for s in STAGES[idx+1:]: state['checkpoints'].pop(s,None)
    state['events'].append({'stage':stage,'at':now(),'action':'pass'})
    write_json(project/'state.json',state)
    return result


def finalize(project: Path):
    result=check(project,'final')
    if not result['passed']: raise ValueError('\n'.join(result['errors']))
    source=project/'output/seed-ir-draft.pptx'
    target=project/'output/seed-ir-final.pptx'
    shutil.copyfile(source,target)
    master_source=project/'output/master/seed-ir-draft.pptx'
    master_target=project/'output/master/seed-ir-final.pptx'
    shutil.copyfile(master_source,master_target)
    write_json(project/'output/final-review.json',result)
    manifest={'created_at':now(),'deck_sha256':sha(project/'deck/deck.json'),
              'pptx_sha256':sha(target),'master_pptx_sha256':sha(master_target),
              'files':['seed-ir-final.pptx','master/seed-ir-final.pptx','pitch-script.md','final-review.json'],
              'timing':read_json(project/'reviews/pitch.json').get('method'),
              'semantic_validation':'Question-by-question reviewer attestation plus required-data coverage and evidence-reference checks; not automatic entailment proof'}
    write_json(project/'output/deliverables.json',manifest)
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    subs=parser.add_subparsers(dest='command',required=True)
    for c in ('init','status','check','record','hash','finalize','migrate'):
        p=subs.add_parser(c); p.add_argument('--project',type=Path,default=Path('.'))
        if c=='init':
            p.add_argument('--team',required=True)
            p.add_argument('--input-dir',default='input')
        if c in ('check','record'): p.add_argument('--stage',choices=STAGES+(['final'] if c=='check' else []),required=True)
        if c=='hash': p.add_argument('file')
    a=parser.parse_args(); project=a.project.resolve()
    try:
        if a.command=='init': initialize(project,a.team,a.input_dir); result={'initialized':True}
        elif a.command=='migrate': result=migrate(project)
        elif a.command=='status': result=status(project)
        elif a.command=='record': result=record(project,a.stage)
        elif a.command=='hash': result={'sha256':sha(safe_path(project,a.file))}
        elif a.command=='finalize': result=finalize(project)
        else:
            result=check(project,a.stage)
            write_json(project/'reviews'/('gate-'+a.stage+'.json'),result)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 0 if result.get('passed',True) else 2
    except (OSError,ValueError,KeyError,TypeError) as e:
        print(json.dumps({'error':str(e)},ensure_ascii=False),file=sys.stderr); return 2


if __name__=='__main__':
    raise SystemExit(main())
