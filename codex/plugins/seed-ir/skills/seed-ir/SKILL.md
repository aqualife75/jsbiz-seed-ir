---
name: seed-ir
description: 창업팀 문서·표·사진에서 정석biz 노하우 목차의 Seed 투자 IR 마스터 덱과 5분 피칭 덱을 만들거나 수정할 때 사용한다. 투자자 질문별 논증, 외부 근거 조사, 복합 시각화와 수정 이력을 관리한다.
---

# Seed IR v1.5.0 멀티 에이전트

사용자 지정 순서는 표지 → 문제 배경 및 최근 트렌드 → 문제 정의 → 기존 대체재의 문제점 → 해결방안 → 제품 및 서비스 소개 → 초기 고객 반응 → 수익 모델 → 시장 규모 → 초기 시장 진입 전략 → 성장 전략 → 마일스톤 → 팀 구성 → 비전이다. 문제 정의·기존 대안·제품 소개·초기 시장 진입은 각각 독립 장표 2개 이상, 나머지는 1개 이상으로 master와 pitch 각각 최소 18장을 만든다. 초기 고객 확보와 이후 성장을 분리하며 기존 대안 2장은 문제 정의 뒤·해결방안 앞에 둔다. 이번 교육 범위에서는 투자 요청·조달·금액·사용 계획을 덱·대본·질문에 넣지 않는다. 마일스톤은 목표·일정·산출물·검증 기준으로 구성한다. v1.2 장표는 한 목차만 포함하며 section_ids를 쓰면 [section] 한 항목이어야 한다.

원문에서 투자자 질문의 답과 논거를 찾고 충분한 마스터 덱을 만든 다음 300초 발표 덱으로 압축한다. Python은 추출·형식·참조·지문을 검사하고 Codex가 원문 의미·투자자 판단·시각화를 검수한다.

먼저 [계약](references/contracts.md)과 [실행 절차](references/orchestration.md)를 읽는다. 자료·이미지 조사에는 [조사 절차](references/research-protocol.md), 장표 설계·제품 자산·렌더 검수에는 [시각 제작 절차](references/visual-production.md), 대본·시간 편집에는 [디자인과 피칭](references/design-and-pitch.md)을 읽는다. 예시는 프로젝트 설치 기준이며 플러그인 경로라면 활성 SKILL.md 기준으로 스킬 경로를 바꾼다.

## 시작

교육생이 `정석biz-IR-프로젝트` 폴더를 열고 “우리 팀 IR Deck 만들어줘”라고 요청하면 현재 폴더에서 바로 준비한다. 교육생에게 Python·터미널 명령·별도 설치·새 작업 폴더 생성을 요구하지 않는다. 신규 자료 위치는 `자료넣는곳`이다. 먼저 프로젝트 설정과 `work/setup/runtime.json`을 확인하며, 기존 프로젝트의 `input/` 등 설정된 입력 경로는 보존한다.

1. Codex의 `load_workspace_dependencies`로 사용 가능한 Python·Node 실행 파일과 node_modules 경로를 확인한다. 실제 발견한 경로를 사용하며 없는 실행 파일이나 라이브러리 경로를 추정하지 않는다.
2. 발견한 Python으로 아래 준비 스크립트를 실행한다. `<NODE>`와 `<NODE_MODULES>`는 실제 경로로 바꾸고 팀 이름이 원문이나 사용자 메시지에 없으면 우선 `우리팀`으로 진행한다. 기존·번들 환경을 먼저 사용하며 부족한 Python 의존성은 스크립트가 프로젝트 전용 환경에 준비한다.

```text
<PYTHON> .agents/skills/seed-ir/scripts/prepare_project.py --project . --team "우리팀" --install-missing --node "<NODE>" --node-modules "<NODE_MODULES>"
```

3. `work/setup/runtime.json`의 `ready`, `python`, `node`, `node_modules`를 읽는다. `ready`가 참인 현재 환경의 경로를 이후 추출·검사·렌더 명령에 사용한다. 아래 문서의 `python`은 이 확인된 실행 파일을 뜻한다. 첫 준비에는 인터넷이나 Codex의 실행 권한 승인이 필요할 수 있다. 실패하면 Codex가 원인과 준비 상태를 확인해 복구하고, 준비하지 못한 단계는 미완료로 알린다. 교육생에게 설치 명령을 맡기지 않는다.
4. `project.json`의 `input_dir`에서 실제 입력 디렉터리를 읽어 `ingest.py --input <설정된 입력 경로> --output data/raw`로 추출하고 `harness.py status --project .`를 확인한다. 준비 스크립트가 초기화했다면 init을 반복하지 않는다. 자료가 없으면 `자료넣는곳` 또는 기존 설정된 자료 폴더를 짧게 안내한다.

기존 작업은 status와 변경된 입력부터 확인한다. v1.0/1.1 이행은 `harness.py migrate --project .`로 백업과 새 질문 틀을 만들고 재분류한다. 이행이 답변을 자동 완성하지는 않는다. 외부 원본은 수정하지 않으며 원본이 바뀌면 프로젝트의 자료 사본도 갱신·재추출한다. gate의 추적 기준은 설정된 프로젝트 입력 폴더다. 여러 팀을 한 덱에 섞지 않는다.

## 역할

| 역할 | 결과 |
|---|---|
| ir_ingestor | 원본 위치·이미지 판독·추출 한계 |
| ir_evidence | 14목차 분류와 18개 질문의 답·논거·coverage·missing |
| ir_writer | 질문 원고, 공통 장표 pool, master/pitch 구성 |
| ir_investor | 질문별 근거·논증 검수와 중요 결함 |
| ir_researcher | 실제 검색·원문·상충 자료·조사 한계 |
| ir_designer | 샘플 스타일, 복합 blocks, 양 덱 실제 렌더 검수 |
| ir_pitch | master 근거를 보존한 300초 구조·대본·리허설 |

native 역할이 없으면 .codex/agents의 지침을 일반 하위 에이전트에 전달한다. 하위 에이전트가 없으면 순차 역할 검수였음을 기록한다. 독립 업무를 최대 3개 병렬 실행한다. 각 역할에 `work/<run_id>/<role>/` 쓰기 소유권을 주고 타인의 편집을 되돌리지 않도록 명시한다. 총괄만 정본을 병합한다.

## 작업과 제작

v1.5.0 신규 프로젝트는 require_visual_briefs:true와 require_visual_plan:true를 유지한다. deck schema_version은 1.2다. 매 장표의 visual_brief를 실제 blocks와 맞추고 design/visual-plan.json에 근거·표시 블록·자료 경로·자산·한계·준비 상태를 기록한다. 시각 계획은 design 단계부터 검사한다.

사용자의 추가 지시를 기다리지 않고 장표별 증거 시각화와 제품 사진·화면을 기획한다. 원본·공식 근거 이미지의 출처와 권리를 조사하고, 필요한 설명용 자산은 확인한 설계 범위 안에서 생성한다. 적합한 이미지나 권리가 없으면 확인한 데이터의 native 차트·표·도식을 선택하고 이유를 기록한다. 생성 자산은 실제 구현·고객·성과의 증거가 아니다.

[시각 제작 절차](references/visual-production.md)에 따라 재사용 자산과 대표 관계 장표를 먼저 확인한 뒤 양 덱 전체를 실제 PPTX로 렌더·직접 검수한다. custom composition은 현재 blocks/items의 문구·값을 바인딩하고 실제 그린 블록만 coverage에 기록한다. 원본 비율·캡션·출처를 보존하며, 코드 실행이나 pilot pass를 전체 디자인 pass로 대신하지 않는다.

교육용 가상 사업 글루코픽(GlucoPic)은 장표의 표현 방식만 참고한다. 샘플의 인터뷰·성과·인물·가격·전망을 팀 자료로 바꾸고, 가정·계획·가상 화면 표기를 실제 근거 없이 제거하지 않는다. 샘플 전체를 우리 팀 사실로 읽지 않는다.

추출과 샘플 분석을 병렬로 시작한다. [정석biz 노하우 기준](references/kdb-curriculum.json)의 required_data를 deck/section-briefs.json에 질문별로 답하고 논거·누락을 저장한다. [투자자 검수](references/investor-rubric.md)의 공백을 [조사 절차](references/research-protocol.md)로 보완한다.

schema 1.2의 slides는 공통 풀이다. views.master는 충분한 근거 덱, views.pitch는 target_seconds 300의 발표 덱이다. 압축 장표의 source_slide_ids·section_ids로 원본 대응을 보존한다. [디자인 기준](references/design-and-pitch.md)의 blocks로 표·차트·사진·산식·흐름을 함께 구성한다. v1.0의 본문 3줄·이미지차트 동시배치 금지를 새 blocks에 적용하지 않는다.

```text
python .agents/skills/seed-ir/scripts/render_deck.py --check-runtime
python .agents/skills/seed-ir/scripts/render_deck.py --project . --variant master
python .agents/skills/seed-ir/scripts/render_deck.py --project . --variant pitch
```

Node·artifact-tool 런타임이 없으면 Codex의 load_workspace_dependencies로 환경 경로를 찾는다. SEED_IR_NODE는 Node 실행 파일, SEED_IR_NODE_MODULES는 @oai 폴더를 포함하는 node_modules 디렉터리다. 설정 후 다시 검사하며 준비하지 못하면 제작을 미완료로 남긴다. 다른 유료 도구는 필수가 아니다. 출력은 output/master와 output/pitch이며 피칭은 output에도 호환 사본을 둔다.

## 상태와 완료

intake, evidence, story, research, review, design, pitch 순서로 check 뒤 record한다. final은 check만 하고 통과한 경우 `harness.py finalize --project .`를 실행한다. 변경 뒤 status로 무효화된 첫 단계부터 재검수한다. 같은 결함의 자동 수정은 최대 2회 뒤 원인·필요 자료를 남긴다.

질문 답변·기초자료가 부족해도 초안은 만들 수 있다. missing을 보존하며 final 완료를 주장하지 않는다. 원문을 읽기 전 confirmed를 쓰지 않고 외부 통계를 자사 실적으로 전용하지 않는다. 온라인 도구가 없으면 research pending이다. 사용자 명시 범위 없이 기본 research_required:true를 낮추거나 가짜 검색 로그를 만들지 않는다.

두 덱의 실제 렌더, 18개 질문의 의미 검수, 현재 해시를 확인한다. 시간 추정은 estimated, 실제 리허설은 measured다. 코드 실행만으로 사실·디자인·투자 준비가 모두 검증되었다고 보고하지 않는다. v1.0 시연 출력은 최종 품질 기준이 아니며 실제 팀 결과를 배포 예시로 전용하지 않는다.

실제 PPTX에서 만든 현재 렌더 이미지를 눈으로 검수한 뒤 각 이미지의 SHA256을 계산한다. `reviews/visual.json`의 루트(발표본)와 `views.master`(상세본)에 각각 `render_sha256: {"프로젝트 상대 렌더 경로": "SHA256"}` 맵을 기록한다. 이미지가 바뀌면 재검수·재계산하며, 지문 기록만으로 시각 검수를 대신하지 않는다. 다른 원고·근거·검수 지문 계약도 그대로 유지한다.

현재 story 검사, 투자자 검수(pass/revise), 시각 검수(pass), 피칭 검수(pass)와 각 지문을 확인한 뒤 준비된 Python으로 `.agents/skills/seed-ir/scripts/publish_results.py --project .`를 실행한다. 이 스크립트는 실제 final 검사 결과에 따라 초안/완료를 구분하고 `결과물/날짜-고유ID/`에 한글 이름의 덱·대본·질문·검수 보고서를 모으며 `결과물/결과보기.html`을 최신 결과로 갱신한다. 오래되거나 미검수인 렌더는 게시하지 않는다. 교육생에게 결과보기 경로와 필요한 추가 자료를 짧게 알리고, 수정 요청은 같은 프로젝트에서 반영·재검수·다시 게시한다.
