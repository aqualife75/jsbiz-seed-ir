# Seed IR Harness v1.5.0 설계

## 실행 경계

사용자 지정 순서는 표지 → 문제 배경 및 최근 트렌드 → 문제 정의 → 기존 대체재의 문제점 → 해결방안 → 제품 및 서비스 소개 → 초기 고객 반응 → 수익 모델 → 시장 규모 → 초기 시장 진입 전략 → 성장 전략 → 마일스톤 → 팀 구성 → 비전이다. 문제 정의·기존 대안·제품 소개·초기 시장 진입은 각각 독립 장표 2개 이상, 나머지는 1개 이상으로 master와 pitch 각각 최소 18장을 만든다. 초기 고객 확보와 이후 성장을 분리하며 기존 대안 2장은 문제 정의 뒤·해결방안 앞에 둔다. 이번 교육 범위에서는 투자 요청·조달·금액·사용 계획을 덱·대본·질문에 넣지 않는다. 마일스톤은 목표·일정·산출물·검증 기준으로 구성한다.

교육생 ZIP은 `.agents/skills/seed-ir`, `.codex/agents`, `AGENTS.md`를 포함한 하나의 프로젝트 폴더다. Codex에서 같은 폴더를 열면 Codex가 `load_workspace_dependencies`로 실행 환경을 찾고 `prepare_project.py`로 준비하며 `work/setup/runtime.json`에 확인된 경로와 ready를 기록한다. Python 3.11 이상·Node·라이브러리는 기존 또는 번들 환경을 우선 사용하고 부족한 Python 라이브러리는 프로젝트 전용 환경에 준비한다. 교육생이 직접 설치 명령을 실행하지 않는다. 강사용 소스 패키지와 기존 방식은 `install.py --project <새 폴더>`를 지원하며 기존 파일 충돌 시 보존하고 중단한다. 전역 설정과 모델명·API 키를 고정하지 않는다. Codex 인증과 도구 사용 가능 여부는 교육생 환경을 따른다.

Python은 추출·저장·구조 검사·출력을 담당한다. 원문 해석, 외부 조사, 투자자 판단과 실제 화면 검토는 Codex가 수행한다. 복합 장표 제작은 Node.js의 @oai/artifact-tool을 사용하며 PATH와 Codex 번들 런타임을 탐색한다. `render_deck.py --check-runtime`으로 확인한다. 특정 유료 앱을 필수화하지 않는다.

## 근거에서 발표까지

1. project.json의 input_dir를 읽고 한 팀의 원문을 설정된 입력 폴더에 복사하고 문서·표·이미지를 출처 위치와 함께 추출한다.
2. 사용자 지정 14목차별 데이터·이미지와 18개 투자자 질문의 답·논거·필수 데이터를 저장한다.
3. 원문과 주장 관계를 확인하고 내부 확인·외부 조사·재추출 과제를 분리한다.
4. 충분한 설명과 복합 시각 자료를 갖춘 master 상세본을 만든다.
5. 투자자 검수·조사·수정 후 master에서 pitch 발표본을 편집한다.
6. 두 PPTX를 실제로 렌더·검수하고 300초 대본과 시간을 검토한다.

자료가 없는 질문은 빈 답과 구체적인 missing을 남긴다. 누락이 있는 초안은 가능하지만 final은 차단한다. 검사를 통과하려고 근거 없는 사실이나 임의 수치를 만들지 않는다.

## 데이터 계약

| 경로 | 역할 |
|---|---|
| 프로젝트 설정의 input_dir | 신규 교육생 프로젝트는 자료넣는곳, 기존은 input/ 등 설정 유지. 한 팀의 추적 대상 사본이며 외부 원본 변경 시 갱신 |
| data/raw/ | inventory, documents, assets. 파일 집합·해시·source_id·locator 보존 |
| evidence/evidence.json | 주장·내부/외부/가정 구분·상태·출처·기간·단위·한계 |
| evidence/section-map.json | 14목차별 evidence_ids·asset_ids·missing_data |
| deck/section-briefs.json | 18개 질문의 answer·argument·필수 항목 coverage·visual_refs·missing |
| deck/deck.json | 공통 slides와 master/pitch 선택·순서, 주장별 근거와 blocks |
| research/ | 실제 검색 범위·쿼리·선정/제외 이유·상충 증거·미해결 공백 |
| reviews/ | 투자자·양쪽 PPTX 시각 검수·발표 검수와 당시 해시 |
| design/ | 추상 디자인 프로필·권리를 확인한 자산 |
| output/master/, output/pitch/ | 각각 PPTX·스토리보드·실제 렌더·제작 보고서 |
| state.json | 단계 완료 시 지문. 변경 시 관련 완료 상태 무효화 |

정확한 JSON 필드는 [계약](../plugins/seed-ir/skills/seed-ir/references/contracts.md)을 따른다. 기존 1.0/1.1 프로젝트는 `harness.py migrate --project .`로 원문을 백업하고 1.2 질문 틀로 옮긴다. 이 명령이 빈 답변을 자동 완성하거나 검수를 통과시키지는 않는다.

## 질문과 장표의 관계

정석biz 노하우 목차를 기준으로 한 18개 질문은 답변, 그 답을 뒷받침하는 논거, required_data 항목별 주장으로 구성한다. 첫 질문이 해당 목차의 필수 항목을 담당하며 나머지 질문도 답과 논거를 갖는다. evidence ID가 존재하는 것만으로 논증이 충족되었다고 보지 않는다.

공통 slides는 두 view가 선택한다. master는 상세 설명을 보존하고 최소 18장 이상으로 구성한다. pitch는 목표 300초와 프로젝트의 발표 장수 조건에 맞춰 편집한다. 별도 압축 장표는 source_slide_ids로 같은 section_ids를 포함한 master 장표에 연결한다. 이 구조와 300초 기준은 하네스 운영 설계다.

blocks는 text, metric, image, table, chart, steps, mapping, formula, roadmap, team을 지원한다. 문제–해결–증거, 고객 여정, 시장 산식, 경쟁표, 검증 일정처럼 내용 관계에 맞춰 구성한다. v1.0의 세 줄 제한과 이미지·차트 동시 사용 제한은 blocks에 적용하지 않는다. 텍스트를 늘리기만 하는 방식도 피하고 장표 추가와 핵심 비교 선택으로 읽기 쉬운 밀도를 만든다.

## 역할과 소유권

ir_ingestor가 추출, ir_evidence가 근거·질문, ir_writer가 논증·장표, ir_investor가 독립 검수, ir_researcher가 조사, ir_designer가 시각화·출력 검수, ir_pitch가 발표 편집·리허설을 맡는다. 총괄만 정본을 병합한다. 기본 작업 경로는 work/<run_id>/<role>/다.

독립적인 최대 3개 하위 작업을 병렬 실행한다. 의존 입력이 준비되기 전 후속 업무를 시작하지 않는다. 같은 결함의 자동 수정은 최대 2회 후 미해결 이유를 인계한다. 하위 에이전트를 지원하지 않으면 순차 역할 수행 사실을 기록한다. native 에이전트 TOML에는 name, description, developer_instructions만 두며 권한과 모델을 고정하지 않는다.

## 완료 조건과 한계

intake → evidence → story → research → review → design → pitch → final 순으로 검사·기록한다. 형식·참조 오류는 초안도 차단하고, 명시적 기초 자료 누락은 초안 경고지만 final 오류다. 원본 집합·해시 또는 덱 내용이 달라지면 이전 검수를 재사용하지 않는다.

투자자 검수는 deck_sha256, briefs_sha256, evidence_sha256, source_documents_sha256와 18개 question_verdicts를 포함한다. 시각 검수 루트에도 evidence_sha256와 source_documents_sha256가 필요하다. 근거·추출 원문이 바뀌면 오래된 검수 기록을 재기록해 통과시킬 수 없다. 참조 이미지가 기본 자료 폴더 밖의 프로젝트 경로에 있더라도 파일 변경은 story 이후 상태에 반영한다. 시각 검수 루트는 pitch이며 views.master에 상세본의 별도 PPTX 해시·렌더·모든 장표 검토를 기록한다. 발표 검수는 실제 측정 또는 근거가 있는 추정으로 구분한다.

내부 실적은 팀 원문으로 확인한다. 외부 통계가 내부 고객·매출·효능을 입증하지 않는다. 온라인 도구가 없으면 research를 pending으로 남기고 초안을 진행한다. 기본 research_required는 true이며 사용자 명시 요청 없이 면제하지 않는다. 이미지와 폰트 권리를 확인한다. 구조 검사와 해시는 주장의 진실이나 디자인 완성도를 자동 보장하지 않는다.

finalize는 현재 검수한 draft와 동일 바이트의 최종 PPTX를 복사하고 결과 목록을 만든다. 상세본과 발표본 검수 중 하나라도 미완료이면 완료라고 전달하지 않는다.

## 시각화 계약

신규 프로젝트는 `require_visual_briefs:true`를 사용합니다. 장표별 `visual_brief`에 핵심 메시지, 주요 근거 블록, 읽는 순서, 구성 변형과 선택 이유를 남깁니다. 렌더러는 핵심 화면 확대, 비교 중심, 시장 계산, 실행 일정 등의 구성을 선택하고 실제 배치를 보고서에 기록합니다. 새 제품 소개 장표에는 출처가 연결된 제품 화면이나 사진을 포함합니다. 자료가 부족하면 필요한 자료를 요청하며 없는 화면을 실제 제품처럼 생성하지 않습니다.

기존 5개 시각 검사에 정보 위계·근거 가독성·구성 다양성을 더합니다. 실제 양쪽 덱을 확인한 관찰 기록과 현재 이미지 지문이 있어야 게시합니다. 이전 프로젝트의 초안은 읽을 수 있으며 새 기준 미충족 사항을 표시합니다.

## 배포 범위

공개 예제는 사용자가 교육 활용을 승인한 AI 가상 사업계획서 글루코픽입니다. 입력·근거 원장·원고·디자인 자산·PPTX·PDF·실제 렌더 미리보기를 제공합니다. 가상의 고객·성과를 실제 자료로 해석하지 않도록 모든 장표에 상태를 표시합니다.

실제 팀 원본과 결과, 과거 비공개 작업 기록은 배포 목록에서 제외합니다. 배포기는 승인된 자산·산출물 목록과 SHA256을 대조하고 텍스트, PPTX 내부 XML·미디어, PDF와 HTML 내장 이미지도 검사합니다. 알 수 없는 예제 파일이나 변경된 바이너리가 발견되면 ZIP 생성을 중단합니다. 검증 결과와 한계는 [배포 검증보고서](validation-report.md)에 기록합니다.


## v1.5.0 제작·검증 변경

신규 프로젝트의 `require_visual_plan: true`는 `design/visual-plan.json`과 현재 장표·근거·표시 이미지의 관계를 검사한다. 생성 이미지의 명시 캡션, 출처·권리·해시, 미완료 상태를 검사하며, 실제 화면이 없는 제품 설명을 완성 시각화로 보지 않는다. 기존 프로젝트는 계약 플래그가 없으면 이전 검수 규약을 읽을 수 있다. 계획이 존재하면 유효성은 항상 검사한다.

범용 렌더러는 현재 blocks의 문구와 수치만 사용한다. 특정 사업의 장표 ID와 내용을 고정한 제작 모듈은 공통 엔진에 넣지 않는다. 작성 절차는 [시각 제작](../plugins/seed-ir/skills/seed-ir/references/visual-production.md), 회고는 [이번 개선의 배경](visual-retrospective.md)에 있다.

동기화 폴더 밖 임시 경로에서 PPTX 내보내기 → native crop 복구 → 차트 데이터 스냅숏 → byte-identical media 중복 제거 → 실제 PPTX 재열기·렌더 순서로 처리한다. 최종 파일과 실제 렌더를 기준으로 검수한다. 로컬 결과 게시 중 디렉터리 이동이 잠기면 이미 검증한 바이트를 새 결과 폴더에 복사하고 재확인한다. 실패한 결과를 최신 링크로 가리키지 않는다.

## 유지보수와 배포

저장소의 Claude Code 구현과 Codex 구현은 별도다. 저장소 루트의 `codex/`에서 다음을 실행한다. Python·Node 경로는 현재 사용 가능한 런타임에서 발견한다. 실제 PPTX 통합 테스트는 `SEED_IR_NODE`와 `SEED_IR_NODE_MODULES`가 필요하며 없으면 건너뛴 내역을 남긴다.

```text
python -m unittest discover -s tests -v
python build_release.py --audience both --output ../release-output
```

빌더는 유지보수 파일 허용 목록·개인 경로/알려진 비공개 자료 검사·승인된 공개 예시 해시를 먼저 확인한다. 출력은 소스 폴더 밖에 저장한다. 교육생 GitHub asset의 파일명은 `seed-ir-codex-learner.zip`이며, 빌드 ZIP을 그대로 복사해 이름만 통일한다. 원본 파일 바이트와 SHA256, ZIP 내 파일별 manifest를 확인한 뒤 GitHub release와 웹페이지의 버전·다운로드·크기·SHA256을 함께 갱신한다.

공개 HTML 갤러리는 AI 제품 설계 이미지의 사용법을 보여 준다. 기존 교육용 PPTX 20/18장과 새 제품 설계 자산 갤러리는 별개이며, 갤러리만 갱신하고 기존 PPTX를 새로 제작했다고 표현하지 않는다. 실제 팀의 input/data/evidence/work/결과물은 배포 대상으로 선택하지 않는다.
