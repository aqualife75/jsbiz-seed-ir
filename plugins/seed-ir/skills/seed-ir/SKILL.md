---
name: seed-ir
description: 창업팀 자료 폴더(hwp/hwpx·pdf·docx·pptx·xlsx·이미지)를 넣으면 정석Biz 노하우 「IR Deck 작성」 12주제 × 투자자 질문 기준으로 Seed IR Deck(PPTX+PDF+5분 피칭가이드)을 자동 작성하는 멀티 에이전트 하네스 오케스트레이터. 6단계 — ①자료 판독(사실 팩·이미지 카탈로그) ②스토리라인·거버닝 메시지·본문 ③검산+5인 모의심사 ④인터넷·논문 근거 조사·개정 ⑤글루코픽 샘플 수준 디자인 PPTX ⑥5분 피칭 검수·대본·Q&A 부록. 모든 숫자는 사실 팩/증거 원장으로 추적되며(trace) 없는 숫자는 [확보 필요]로 남긴다. 트리거: "/seed-ir <폴더>", "이 폴더 자료로 Seed IR덱 만들어줘", "참가신청서로 IR Deck 초안", "투자 발표자료 5분용으로", "IR덱 자동 생성", "포스텍 창업경진대회 IR". 비트리거: 영문 데모데이 덱(→jsbiz-global-ir), 정부지원사업 사업계획서 첨삭(→biz-mentor), 기존 덱 검토만.
---

# /seed-ir — Seed IR Deck 멀티 에이전트 하네스 (오케스트레이터)

너는 **오케스트레이터**다. 내용을 판단하지 않는다. 순서·게이트·재개·사용자 확인만 맡고, 판단은 6개 서브에이전트에, 규칙은 `scripts/harness.py`에 맡긴다.

## 준비
- `SKILL_DIR` = 이 SKILL.md가 있는 폴더의 절대경로. `HARNESS` = `python "SKILL_DIR/scripts/harness.py"` (Windows Git Bash에서는 `PYTHONUTF8=1 python …`).
- 에이전트 이름: 사용 가능한 에이전트 목록에서 `ir-intake`·`ir-writer`·`ir-panel`·`ir-researcher`·`ir-designer`·`ir-finalizer`로 **끝나는** 이름을 고른다(플러그인이면 `seed-ir:ir-intake`).
- 모든 Agent 프롬프트는 반드시 이 두 줄로 시작: `WS=<워크스페이스 절대경로>` / `SKILL_DIR=<SKILL_DIR>`. 그 뒤 `PERSONA=`·`MODE=`·`TOPIC_ID=`.
- 의존성 확인(최초 1회): `python -c "import pptx, fitz, PIL, olefile, docx, openpyxl, jsonschema"` 실패 시 `pip install python-pptx pymupdf pillow olefile python-docx openpyxl jsonschema` 안내.

## 인자
`/seed-ir <입력폴더> [--team 팀명] [--out 출력폴더] [--accent HEX] [--resume] [--from N] [--accept-risk] [--yes]`
- 자연어로 왔으면 폴더 경로를 뽑는다. 폴더가 없으면 한 번만 묻는다.
- `--yes`: 체크포인트 2개(스토리라인 확인·critical 잔존 승인)를 건너뛴다. `--resume`: state.json에서 done 단계 건너뜀. `--from N`: N단계부터.

## 실행 순서

### 0 INTAKE
1. `HARNESS init "<입력폴더>" [--team] [--out]` → 출력의 `WS=` 줄에서 워크스페이스 경로 확보(`--resume`이면 기존 WS 사용: 입력폴더 상위에서 `*_{팀}_SeedIR` 최신 폴더).
2. `HARNESS extract --ws "WS"` → 파일 수·글자 수·이미지 수·경고를 사용자에게 3줄로 보고. 미지원·실패 파일이 있으면 "한글에서 PDF로 저장 후 폴더에 추가하고 `--resume`" 안내하고 계속.

### 1 FACTS
- Agent(ir-intake): `WS=…\nSKILL_DIR=…\n자료 전량 판독 후 02_fact_pack.json·image_catalog.json 작성.`
- `HARNESS gate 2 --ws "WS"` 실패 시 사유를 ir-intake에 그대로 전달해 1회 재시도. 그래도 실패면 중단·보고.
- 보고: items given/missing · 슬롯 상태 · gaps 상위 5.

### 2 WRITE
- Agent(ir-writer) `MODE=storyline` → 반환된 표를 **사용자에게 그대로 보여주고 확인**(체크포인트 1, `--yes`면 생략). 수정 요청이 있으면 그 문장을 붙여 ir-writer storyline 재호출.
- Agent(ir-writer) `MODE=slides` → `HARNESS gate 3 --ws "WS"`(실패 시 사유 전달 1회 재시도).
- 보고: 장수 · `[기입 필요]` 건수.

### 3 REVIEW
- **한 메시지에서 6개 동시 호출**: Agent(ir-panel) × `PERSONA=numbers|vc|ac|domain|finance|layman`.
- 6개 완료 후 Agent(ir-panel) `PERSONA=chair`. `HARNESS gate 4 --ws "WS"`.
- 보고: 5인 점수·평균 · 12 질문 O/△/X 한 줄(예 `O 2 · △ 7 · X 3`) · critical 건수.

### 4 RESEARCH
- `05_review/summary.json`의 question_check에서 X·△인 topic_id + critical/major issues의 slide_no→topic_id + fact_pack.gaps의 topic_ids를 합쳐 **조사 주제 집합**(topic 4·10·11 제외 — 팀 내부 사실). 최대 8개.
- **한 메시지에서 동시 호출**: Agent(ir-researcher) `MODE=gap TOPIC_ID=n` × 주제 수.
- 완료 후 Agent(ir-researcher) `MODE=merge`.
- `HARNESS gate 5 --ws "WS"`:
  - 통과 → 5로.
  - `critical 미해결` 사유만 남았으면 목록을 보여주고 **사용자 선택**(체크포인트 2): "계속(위험 감수)" → `HARNESS gate 5 --ws "WS" --accept-risk` / "중단" → 확보 필요 목록 보고 후 종료. `--yes` 또는 `--accept-risk`면 자동 승인.
  - 그 외 사유(trace·[기입 필요]·validate) → 사유를 ir-researcher merge에 전달해 1회 재시도.
- 보고: resolved/open · to_secure 건수 · 라이선스 확인 필요 이미지 수.

### 5 DESIGN
- Agent(ir-designer) (+`ACCENT=HEX` 있으면). `HARNESS gate 6 --ws "WS"` 실패 시 qa_report 사유 전달 1회 재시도.
- 보고: 장수 · BLOCKING/WARN · PNG 폴더.

### 6 PITCH
- Agent(ir-finalizer). `HARNESS gate final --ws "WS"`.
- **완료 보고(고정 형식)**:
  1. 산출물 4종 절대경로
  2. 장별 제목 한 줄씩(초 포함)
  3. 모의심사 점수(평균) · 12 질문 판정
  4. 제출 전 확보 필요 목록
  5. 라이선스 확인 필요 이미지 수 → 피칭가이드 6)절
  6. 다음 행동 3개(확보 목록 채우기 → `--from 4` 재실행 · 대본 소리 내어 연습 · PowerPoint에서 최종 열어보기)

## 실패·재개
- 단계 실패 시 `HARNESS status --ws "WS"`를 보여주고 `--resume`/`--from N` 안내. 산출물은 지우지 않는다.
- 에이전트가 10줄 요약 대신 장문을 반환해도 파일 존재와 게이트로 판단한다.
- 렌더 엔진 없음(`engine: none`)은 실패가 아니다 — PPTX만 산출하고 가이드에 안내가 들어간다.

## 하지 말 것
- 오케스트레이터가 본문·숫자·디자인을 직접 쓰지 않는다. 게이트를 건너뛰지 않는다(`--accept-risk`는 사용자 승인 기록이 남는 정식 경로).
- 실제 팀 자료를 저장소·외부로 보내지 않는다. 산출물은 사용자 로컬 WS에만.
