#!/usr/bin/env python3
"""Publish current reviewed IR artifacts into the beginner's results folder."""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import html
import importlib.util
import json
from pathlib import Path
import re
import sys
from urllib.parse import quote
import uuid
import zipfile


_spec = importlib.util.spec_from_file_location('publication_harness', Path(__file__).with_name('harness.py'))
h = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(h)

VISUAL_CHECKS = ('text_overflow', 'font_substitution', 'contrast', 'chart_labels', 'image_crops')


def destination_directory(project, relative):
    if not isinstance(relative, str) or not relative.strip():
        raise ValueError('결과 폴더 이름이 필요합니다')
    relative = relative.replace('\\', '/')
    parts = relative.split('/')
    if relative.startswith('/') or ':' in relative or any(x in ('', '.', '..') for x in parts):
        raise ValueError('결과 폴더는 프로젝트 안의 상대 폴더여야 합니다')
    blocked = {x.casefold() for x in h.INTERNAL_DIRECTORIES if x != '결과물'} | {'input'}
    if any(x.casefold() in blocked for x in parts):
        raise ValueError('결과 폴더가 내부 작업 폴더와 겹칩니다')
    result = h.safe_path(project, relative)
    if any(x.casefold() in blocked for x in result.relative_to(project).parts):
        raise ValueError('결과 폴더가 내부 작업 폴더와 겹칩니다')
    source = h.input_directory(project)
    if result == project or result.is_relative_to(source) or source.is_relative_to(result):
        raise ValueError('결과 폴더와 자료 폴더는 겹칠 수 없습니다')
    return result


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def ensure(condition, message):
    if not condition:
        raise ValueError(message)


def page(title, body):
    return ('<!doctype html><html lang="ko"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>' + html.escape(title) + '</title><style>'
            'body{font:17px/1.7 "Malgun Gothic",sans-serif;background:#f6f3ed;color:#19312b;margin:0}'
            'main{max-width:960px;margin:auto;padding:64px 24px}h1{font-size:36px;line-height:1.3}'
            'h2{margin-top:40px}a{color:#006d56;text-underline-offset:4px}'
            '.badge{font-weight:bold;color:#82570f}.card{background:white;padding:24px;border-radius:14px;margin:18px 0}'
            '.files{display:flex;gap:12px;flex-wrap:wrap}.files a{border:1px solid #b8c7bd;border-radius:8px;padding:12px 16px}'
            'pre{white-space:pre-wrap;font:inherit}small{color:#52695f}li{margin:8px 0}'
            'a:focus-visible{outline:3px solid #006d56;outline-offset:5px}'
            '.brand-learning{border-top:1px solid #cbd8cf;background:#eaf0eb}'
            '.brand-learning-inner{max-width:960px;margin:auto;padding:32px 24px 40px}'
            '.brand-learning h2{margin:0;font-size:24px;line-height:1.4}'
            '.brand-learning p{max-width:720px;margin:12px 0 20px}'
            '.brand-links{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px}'
            '.brand-links a{display:inline-block;background:#fff;border:1px solid #b8c7bd;'
            'border-radius:8px;padding:10px 14px;text-decoration:none;font-weight:bold}'
            '.brand-links a:hover{text-decoration:underline;background:#f7faf7}'
            '@media(max-width:560px){main{padding:36px 20px}.brand-learning-inner{padding:28px 20px}'
            '.brand-links{flex-direction:column}.brand-links a{align-self:flex-start}}'
            '</style><main><p>정석biz 노하우 · IR Deck</p><h1>' + html.escape(title) + '</h1>' + body + '</main>'
            '<footer class="brand-learning" aria-labelledby="brand-learning-title"><div class="brand-learning-inner">'
            '<h2 id="brand-learning-title">정석biz와 창업 공부를 이어가세요</h2>'
            '<p>사업계획서와 IR Deck에 담을 고객의 문제, 사업의 근거, 설득의 흐름을 정석biz와 함께 공부하세요. '
            '영상을 보며 우리 팀의 원고를 다듬고, 커뮤니티에서 배움을 이어갈 수 있습니다.</p>'
            '<nav class="brand-links" aria-label="정석biz 학습과 커뮤니티">'
            '<a href="https://www.youtube.com/@%EC%A0%95%EC%84%9DBiz" target="_blank" rel="noopener noreferrer">유튜브 시청·구독</a>'
            '<a href="https://bit.ly/startup_bizplan" target="_blank" rel="noopener noreferrer">정석biz 커뮤니티 참여</a>'
            '<a href="https://campiel.com" target="_blank" rel="noopener noreferrer">campiel.com 방문</a>'
            '</nav><small>외부 링크는 새 탭에서 열리며, 인터넷 연결이 필요합니다.</small>'
            '</div></footer></html>')


def link(filename, label):
    return '<a href="' + quote(filename, safe='/') + '">' + html.escape(label) + '</a>'


def notes_and_questions(deck, briefs):
    pitch = h.quality.select_slides(deck, 'pitch')
    lines = ['# 5분 발표 대본', '', '장표별 배정 시간입니다. 실제 발표 시간은 리허설로 확인하세요.', '']
    for i, slide in enumerate(pitch, 1):
        lines += [f"## {i}. {slide.get('governing_message', '')} ({slide.get('seconds', 0)}초)",
                  '', str(slide.get('speaker_notes', '대본 보완 필요')), '']
    questions = ['# 예상 질문과 답변', '', '현재 원고를 기준으로 정리했습니다. 비어 있는 답변은 추가 자료가 필요합니다.', '']
    labels = {topic['id']: topic['label_ko'] for topic in h.quality.load_curriculum(deck.get('schema_version'))['topics']}
    def claim_text(value):
        return value.get('text', '') if isinstance(value, dict) else str(value or '')
    for section in briefs.get('sections', []):
        questions += ['## ' + str(labels.get(section.get('section'), '목차')), '']
        for item in section.get('questions', []):
            questions += ['### ' + str(item.get('question', item.get('id', '질문'))), '',
                          claim_text(item.get('answer')) or '추가 자료와 답변이 필요합니다.', '']
            if item.get('argument'):
                questions += ['근거: ' + '\n\n'.join(claim_text(value) for value in item['argument']), '']
            if item.get('missing'):
                questions += ['추가로 확인할 내용: ' + '; '.join(item['missing']), '']
    return '\n'.join(lines), '\n'.join(questions)


def publish(project: Path, output_dir='결과물'):
    project = Path(project).resolve()
    destination = destination_directory(project, output_dir)
    snapshots = {}

    def read(relative):
        path = h.safe_path(project, relative)
        ensure(path.is_file(), '현재 검토 파일이 없습니다: ' + relative)
        snapshots[relative] = path.read_bytes()
        return snapshots[relative]

    def obj(relative):
        value = json.loads(read(relative).decode('utf-8-sig'))
        ensure(isinstance(value, dict), '검토 파일 형식이 올바르지 않습니다: ' + relative)
        return value

    config = obj('project.json')
    deck = obj('deck/deck.json')
    briefs = obj('deck/section-briefs.json')
    for rel in ('evidence/evidence.json', 'data/raw/documents.json', 'data/raw/inventory.json',
                'data/raw/assets.json', 'state.json'):
        read(rel)
    source_fingerprint = h.fingerprint(project, 'pitch')
    story = h.check(project, 'story')
    ensure(story['passed'], '현재 자료와 원고를 먼저 보완·검증하세요: ' + '\n'.join(story['errors']))
    require_visual_briefs = config.get('require_visual_briefs', False) is True
    if require_visual_briefs:
        ledger = json.loads(snapshots['evidence/evidence.json'].decode('utf-8-sig'))
        evidence = {item['id']: item for item in ledger.get('items', []) if isinstance(item, dict) and 'id' in item}
        for slide in deck.get('slides', []):
            report = h.quality.validate_visual_brief(slide, evidence, required=True, final=True)
            ensure(not report['errors'], '게시 전 장표 구성과 제품 이미지를 보완하세요: ' + '\n'.join(report['errors']))
    plan_path = h.safe_path(project, 'design/visual-plan.json')
    require_visual_plan = config.get('require_visual_plan', False) is True
    if require_visual_plan or plan_path.exists():
        plan = obj('design/visual-plan.json') if plan_path.exists() else None
        ledger = json.loads(snapshots['evidence/evidence.json'].decode('utf-8-sig'))
        evidence = {item['id']: item for item in ledger.get('items', []) if isinstance(item, dict) and 'id' in item}
        report = h.visual_plan.validate(plan, deck, evidence, project,
                                        required=require_visual_plan, final=True)
        ensure(not report['errors'], '게시 전 시각 자료 계획을 보완하세요: ' + '\n'.join(report['errors']))
    common = {
        'deck_sha256': 'deck/deck.json',
        'evidence_sha256': 'evidence/evidence.json',
        'source_documents_sha256': 'data/raw/documents.json',
    }

    def review(name, allowed):
        receipt = obj('reviews/' + name + '.json')
        for key, rel in common.items():
            ensure(receipt.get(key) == sha_bytes(snapshots[rel]), name + ': 현재 원고·근거와 검토 지문이 다릅니다. 재검토하세요.')
        ensure(receipt.get('verdict') in allowed and receipt.get('reviewer') and receipt.get('rationale'),
               name + ': 현재 자료를 읽은 검토자의 판정과 설명이 필요합니다.')
        return receipt

    investor = review('investor', ('pass', 'revise'))
    ensure(investor.get('briefs_sha256') == sha_bytes(snapshots['deck/section-briefs.json']),
           '투자자 질문별 원고가 검토 이후 바뀌었습니다. 재검토하세요.')
    visual = review('visual', ('pass',))
    pitch_review = review('pitch', ('pass',))
    duration = pitch_review.get('duration_seconds')
    ensure(isinstance(duration, (int, float)) and not isinstance(duration, bool)
           and 0 < duration <= config.get('pitch_target_seconds', 300), '현재 대본의 발표시간 검토가 필요합니다.')
    ensure(pitch_review.get('method') in ('estimated', 'measured'), '발표시간 검토 방법이 필요합니다.')
    ensure(pitch_review.get('method') != 'estimated' or pitch_review.get('estimation_basis'),
           '발표시간 추정 근거가 필요합니다.')
    for view in ('master', 'pitch'):
        receipt = visual.get('views', {}).get('master', {}) if view == 'master' else visual
        ensure(isinstance(receipt, dict), view + ': 시각검토 기록이 필요합니다.')
        pptx_rel = 'output/master/seed-ir-draft.pptx' if view == 'master' else 'output/seed-ir-draft.pptx'
        pptx = read(pptx_rel)
        ensure(receipt.get('verdict') == 'pass' and receipt.get('pptx_sha256') == sha_bytes(pptx),
               view + ': 현재 PPTX와 시각검토 지문이 다릅니다. 재검토하세요.')
        selection = h.quality.select_slides(deck, view)
        expected_ids = [slide['id'] for slide in selection]
        if require_visual_briefs:
            visual_errors = h.quality.validate_visual_review(receipt, expected_ids, view)
            ensure(not visual_errors, '게시 전 실제 화면의 관찰 기록을 보완하세요: ' + '\n'.join(visual_errors))
        ensure(sorted(receipt.get('slides_reviewed', [])) == sorted(expected_ids), view + ': 모든 장표의 시각검토가 필요합니다.')
        ensure(receipt.get('render_method') in ('powerpoint', 'libreoffice', 'artifact-tool'),
               view + ': 실제 PPTX 렌더 검토가 필요합니다.')
        ensure(all(receipt.get('checks', {}).get(key) == 'pass' for key in VISUAL_CHECKS),
               view + ': 글자·글꼴·대비·차트·이미지 검토를 완료하세요.')
        for finding in receipt.get('findings', []):
            ensure(finding.get('severity') not in ('P0', 'P1') or finding.get('status') == 'resolved',
                   view + ': 중대한 시각검토 지적을 먼저 해결하세요.')
        renders = receipt.get('render_files', [])
        hashes = receipt.get('render_sha256', {})
        ensure(isinstance(renders, list) and len(renders) == len(expected_ids) and len(set(renders)) == len(renders),
               view + ': 장표별 렌더 파일이 필요합니다.')
        ensure(isinstance(hashes, dict) and set(hashes) == set(renders),
               view + ': 검토한 렌더 이미지 지문(render_sha256)을 기록한 후 다시 게시하세요.')
        for relative in renders:
            image = read(relative)
            ensure(image.startswith((b'\x89PNG\r\n\x1a\n', b'\xff\xd8\xff')) and hashes[relative] == sha_bytes(image),
                   view + ': 렌더 이미지 지문이 바뀌었습니다. 재검토하세요: ' + relative)
        with zipfile.ZipFile(h.safe_path(project, pptx_rel)) as archive:
            slide_count = sum(bool(re.fullmatch(r'ppt/slides/slide\d+\.xml', name)) for name in archive.namelist())
            ensure('ppt/presentation.xml' in archive.namelist() and slide_count == len(selection),
                   view + ': PPTX 장표 수와 현재 원고가 일치하지 않습니다.')
    ensure(pitch_review.get('pptx_sha256') == sha_bytes(snapshots['output/seed-ir-draft.pptx']),
           '발표시간 검토가 현재 PPTX와 다릅니다. 재검토하세요.')

    final_gate = h.check(project, 'final')
    status = 'final' if final_gate['passed'] else 'draft'
    label = '최종' if status == 'final' else '보완초안'
    run_id = datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8]
    run_dir = destination / run_id
    pending = destination / ('.준비중-' + run_id)
    script, questions = notes_and_questions(deck, briefs)
    files = {
        f'5분_발표본_{label}.pptx': snapshots['output/seed-ir-draft.pptx'],
        f'상세본_{label}.pptx': snapshots['output/master/seed-ir-draft.pptx'],
        '5분_발표대본.md': script.encode('utf-8'),
        '예상질문과_답변.md': questions.encode('utf-8'),
    }
    title = str(config.get('team_name', '우리 팀')) + ' IR Deck 결과'
    body = '<p class="badge">' + label + ' · ' + html.escape(run_id) + '</p>'
    if status == 'draft':
        body += '<p>현재 검토한 보완초안입니다. 확인할 사업 근거와 검토 항목이 남아 있어 최종본으로 표시하지 않았습니다.</p>'
    else:
        body += '<p>현재 자료를 기준으로 모든 최종 검증을 통과했습니다.</p>'
    body += '<div class="files">' + ''.join(link(name, name.rsplit('.', 1)[0]) for name in files) + '</div>'
    body += '<div class="card"><h2>발표 준비</h2><p>발표시간 ' + str(duration) + '초 · '
    body += ('대본 기준 추정입니다. 실제 리허설로 확인하세요.' if pitch_review['method'] == 'estimated' else '실제 측정 기록을 사용했습니다.')
    body += '</p><p>' + html.escape(str(investor['rationale'])) + '</p></div>'
    if not final_gate['passed']:
        body += '<h2>보완할 내용</h2><p>Codex에 “남은 보완 사항을 정리하고 함께 수정해줘”라고 요청하세요.</p><ul>'
        # Technical gate detail remains in work/publications; the learner sees actionable gaps.
        gaps = [question for section in briefs.get('sections', []) for question in section.get('questions', [])
                if question.get('status') != 'answered' or question.get('missing')]
        for gap in gaps[:18]:
            text = str(gap.get('question', '추가 확인 필요'))
            missing = gap.get('missing', [])
            body += '<li><strong>' + html.escape(text) + '</strong>'
            if missing:
                body += '<br>' + html.escape('; '.join(missing))
            body += '</li>'
        if not gaps:
            body += '<li>현재 투자자 검토와 단계별 확인에서 남은 항목을 Codex와 보완하세요.</li>'
        body += '</ul>'
    body += '<details><summary>발표 대본 보기</summary><pre>' + html.escape(script) + '</pre></details>'
    body += '<details><summary>예상 질문과 답변 보기</summary><pre>' + html.escape(questions) + '</pre></details>'
    files['결과보기.html'] = page(title, body).encode('utf-8')

    ensure(h.fingerprint(project, 'pitch') == source_fingerprint, '검증 중 자료가 바뀌었습니다. 다시 검토한 후 게시하세요.')
    for relative, expected in snapshots.items():
        ensure(h.safe_path(project, relative).read_bytes() == expected, '검증 중 파일이 바뀌었습니다: ' + relative)
    destination.mkdir(parents=True, exist_ok=True)
    pending.mkdir()
    for filename, value in files.items():
        (pending / filename).write_bytes(value)
    try:
        pending.rename(run_dir)
    except PermissionError:
        # Windows sync clients can hold the staging directory open. Use only
        # already verified byte snapshots; never move or delete another run.
        # Failed copies remain unlisted: the latest pointer is updated last.
        ensure(pending.is_dir() and not run_dir.exists(), '게시 경로 상태를 다시 확인해야 합니다.')
        run_dir.mkdir()
        for filename, value in files.items():
            target = run_dir / filename
            target.write_bytes(value)
            ensure(target.read_bytes() == value, '게시 사본 검증 실패: ' + filename)
    manifest = {'created_at': h.now(), 'status': status,
                'run_dir': run_dir.relative_to(project).as_posix(),
                'report': (run_dir / '결과보기.html').relative_to(project).as_posix(),
                'source_sha256': {rel: sha_bytes(value) for rel, value in snapshots.items()},
                'files': {name: sha_bytes(value) for name, value in files.items()},
                'final_gate': final_gate}
    private_manifest = h.safe_path(project, 'work/publications/' + run_id + '.json')
    h.write_json(private_manifest, manifest)
    landing = page(title, '<p>가장 최근에 게시한 결과입니다. 게시 당시 자료를 기준으로 검토했습니다.</p>'
                   + '<p class="badge">' + label + ' · ' + html.escape(run_id) + '</p><p>'
                   + link(run_id + '/결과보기.html', '결과와 발표자료 열기') + '</p>'
                   + '<small>자료를 바꿨다면 Codex에 다시 작성을 요청하세요. 이전 결과는 각 날짜 폴더에 보관됩니다.</small>')
    landing_path = h.safe_path(project, (destination / '결과보기.html').relative_to(project).as_posix())
    temporary = destination / ('.결과보기-' + run_id + '.html')
    temporary.write_text(landing, encoding='utf-8')
    temporary.replace(landing_path)
    return {key: manifest[key] for key in ('status', 'run_dir', 'report')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path('.'))
    parser.add_argument('--output-dir', default='결과물')
    args = parser.parse_args()
    try:
        result = publish(args.project, args.output_dir)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, TypeError, KeyError, zipfile.BadZipFile) as error:
        print('결과물 정리를 완료하지 못했습니다. Codex가 다음 항목을 확인해야 합니다: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
