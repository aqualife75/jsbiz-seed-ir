# 디자인과 5분 피칭 · v1.5.0

장표별 시각 계획, 제품 사진·화면 생성, 근거 이미지 조사, custom composition과 변경 렌더 검수는 [시각 제작 절차](visual-production.md)를 먼저 읽고 적용한다. 사용자에게 별도 이미지 지시를 받기 전에도 현재 주장과 자료에 맞는 시각화를 기획·제작한다. 본 문서는 목차·장표 편집·피칭과 결과 전달 기준을 설명한다.

## 상세본을 만든 뒤 발표본을 편집한다

사용자 지정 순서는 표지 → 문제 배경 및 최근 트렌드 → 문제 정의 → 기존 대체재의 문제점 → 해결방안 → 제품 및 서비스 소개 → 초기 고객 반응 → 수익 모델 → 시장 규모 → 초기 시장 진입 전략 → 성장 전략 → 마일스톤 → 팀 구성 → 비전이다. 문제 정의·기존 대안·제품 소개·초기 시장 진입은 각각 독립 장표 2개 이상, 나머지는 1개 이상으로 master와 pitch 각각 최소 18장을 만든다. 초기 고객 확보와 이후 성장을 분리하며 기존 대안 2장은 문제 정의 뒤·해결방안 앞에 둔다. 이번 교육 범위에서는 투자 요청·조달·금액·사용 계획을 덱·대본·질문에 넣지 않는다. 마일스톤은 목표·일정·산출물·검증 기준으로 구성한다. v1.2 장표는 한 목차만 포함하며 section_ids를 쓰면 [section] 한 항목이어야 한다.

사용자 지정 14개 목차와 18개 투자자 질문을 먼저 `deck/section-briefs.json`에 답한다. 답·논거·필수 데이터가 부족하면 장표의 외형을 채워 완료시키지 않는다. 상세본 master는 논증과 증거를 보존하며 최소 18장 이상으로 구성한다. 발표본 pitch는 이 자료에서 300초 안에 전달할 핵심 흐름을 선택한다. 발표본도 최소 18장을 유지한다.

`deck/deck.json`의 공통 `slides`에서 `views.master.slide_ids`와 `views.pitch.slide_ids`가 각각 순서를 정한다. 그대로 재사용하는 장표도 가능하다. 별도로 압축한 pitch 장표는 `source_slide_ids`로 같은 `section_ids`를 포함하는 master 장표에 연결한다. 압축해도 중요한 한계, 단위와 출처를 삭제하지 않는다.

## 샘플을 해석하는 방식

[디자인 프로필](design-profile.json)은 폰트·색상·위계·여백·의미별 배치를 재사용하는 기준이다. 배포 예시는 사용자 소유의 교육용 가상 사업 글루코픽(GlucoPic)이며 승인된 가상 자산만 포함한다. 예시의 인물·가격·반응·전망은 실제 팀 근거로 전용하지 않는다. 새로운 참고 자료를 받으면 테마·텍스트 런·레이아웃·미디어와 실제 렌더를 함께 확인한다. 파일의 폰트 선언과 렌더된 폰트를 구분하며 발견한 사용 가능 폰트를 제작 런타임에 등록한다.

샘플 수준의 완성도는 팔레트를 적용하거나 카드 형태를 반복하는 것으로 보장되지 않는다. 각 주장에 맞는 시각 구조를 고르고, 내용의 상대적 중요도와 시선 흐름을 만들어야 한다. 원본 사진과 제품 화면은 주장에 직접 연결된 캡션을 붙인다. 설명용 생성 이미지를 실제 제품·실험·고객의 증거로 사용하지 않는다.

## 복합 시각 구성

모든 신규 장표에 [visual_brief 계약](contracts.md)의 key_message, primary_block_id, reading_order, layout_variant, visual_reason을 작성한다. 먼저 핵심 결론과 가장 강한 증거를 고르고, 비교·흐름·시장 범위·일정 등 관계에 맞춰 구성한다. 읽는 순서에는 모든 블록을 담고 주요 증거는 크게, 보조 설명은 그 다음으로 배치한다. 슬라이드 번호만으로 밝고 어두운 배경을 번갈아 쓰지 말고 메시지와 장면 전환에 맞춘다.

대표 장표는 문제의 현장 증거, 동일 조건 대안 비교, 제품 핵심 작동부, 고객 반응의 측정 조건, 초기 진입의 실행 흐름을 먼저 실제 PPTX로 렌더해 방향을 확인한다. 복잡한 시장·일정 관계는 필요에 따라 추가하며 특정 장표 ID나 개수를 고정하지 않는다. 대표 검수와 양 덱 전체 검수는 구별한다. 제품 장표에는 실제 입력 자료의 화면·사진 또는 가상 설계임을 명시한 자산을 사용한다. 중요한 UI가 읽히도록 원본 전체와 발표용 확대 부분을 구분하고 실제 크롭 파일이나 crop 좌표, 원본 위치·출처·사용권을 자산 대장에 남긴다. 이미지·필수 캡션·출처/footer는 별도 공간으로 예약한다. 핵심 버튼·결과·단위를 잘라 없애지 않는다. product_hero는 이미지가 없으면 텍스트로 대신 완료하지 않는다.

관찰되지 않은 고객 수·매출·성능 변화는 차트로 꾸미지 않는다. 가정 계산은 가정 표기와 입력 산식을 보여 주고, 정성 자료는 인용·비교·흐름으로 표현한다. 제품 화면 속 시연 수치는 실적이 아니다.

v1.2은 `blocks`로 내용의 관계를 표현한다. 모든 장표를 세 줄 본문으로 제한하지 않는다. 이미지와 표·차트를 같은 장표의 서로 다른 블록에 배치할 수 있다. 이는 이전 `body/assets/visual` 제작기의 제한과 구분한다.

| 전달할 내용 | 권장 레이아웃 | 핵심 구성 |
|---|---|---|
| 주장을 입증하는 데이터와 현장 | evidence_board | 핵심 지표 + 차트/표 + 사진 또는 근거 설명 |
| 고객 문제와 해결 효과 | problem_solution | 문제–해결–증거를 행별로 대응 |
| 제품 사용 경험 | product_journey | 단계·실제 화면·고객 편익의 연결 |
| 시장 산정 | market_model | 고객 수·가격·범위·계산식과 각 입력 근거 |
| 경쟁 차별점 | competition_matrix | 동일 조건의 비교표와 중요한 해석 |
| 개발과 검증 일정 | milestone_roadmap | 기간·목표·산출물·다음 단계 진행 기준 |
| 팀의 실행 역량 | team_evidence | 역할·관련 경력·확인 근거·계획 기여 |

지원 블록은 text, metric, image, table, chart, steps, mapping, formula, roadmap, team이다. 세부 필드는 [데이터 계약](contracts.md)을 따른다. 표의 셀, 차트 값, 팀 경력, 단계 설명에도 사실·가정·계획 구분과 근거를 적용한다. 자사 실적은 company 범위와 내부 근거를 사용한다.

정보가 많으면 읽을 수 있는 상세본 장표를 추가한다. 한 장에 밀어 넣기 위해 폰트를 줄이지 않는다. 발표본에서는 비교에 필요한 행·열과 핵심 장면을 남기고 세부 증거는 master에서 찾아볼 수 있게 한다.

신규 프로젝트는 design/visual-plan.json에 모든 사용 장표의 block_ids·evidence_ids·visual_type·source_strategy·asset_refs·disclosure·claim_boundary·status·search_note를 기록한다. require_visual_plan:true를 유지하며 design 단계에서 준비 상태와 실제 장표·파일·권리·해시를 검사한다. 표·차트·도식을 고른 장표는 native 선택과 이미지 미사용 이유를 기록한다. 정확한 구조는 [계약](contracts.md)과 [시각 제작 절차](visual-production.md)를 따른다.

프로젝트별 custom composition은 현재 deck의 blocks/items에서 모든 표시 문구·숫자를 바인딩하고 실제 출력한 블록만 coverage에 기록한다. 고정 데모 내용이나 특정 slide ID 분기를 새 팀에 복사하지 않는다. 사용 자산은 자산 대장·실제 blocks/visual_brief와 연결하며 native 표·차트와 텍스트 검사 경로를 유지한다.

## 런타임과 제작

복합 장표 제작에는 Node.js와 `@oai/artifact-tool`이 필요하다. 제작기는 PATH 및 Codex의 번들 런타임을 탐색한다. 특정 유료 앱 설치는 필수가 아니다. 다음 명령으로 실제 사용 가능 여부를 확인한다.

```text
python .agents/skills/seed-ir/scripts/render_deck.py --check-runtime
python .agents/skills/seed-ir/scripts/render_deck.py --project . --variant master
python .agents/skills/seed-ir/scripts/render_deck.py --project . --variant pitch
```

`--view`는 `--variant`와 같은 옵션이다. 필요한 경우 `SEED_IR_NODE`와 `SEED_IR_NODE_MODULES`로 준비된 런타임 위치를 지정한다. 런타임이 없으면 오류 안내를 따르고 디자인 단계를 미완료로 둔다. 내용이 누락된 이전 제작기로 바꿔 성공을 선언하지 않는다.

출력은 `output/master/`와 `output/pitch/` 아래 각각 `seed-ir-draft.pptx`, `storyboard.html`, `render-report.json`, `renders/`다. pitch는 호환을 위해 `output/` 루트에도 PPTX·스토리보드·보고서를 복사한다.

## 실제 PPTX 검수

HTML 스토리보드는 PPTX 렌더의 대체물이 아니다. 생성한 실제 PPTX의 장표 이미지를 확인한다. 렌더러가 PNG를 생성했더라도 검수자의 시각 검토는 별도다. PowerPoint·LibreOffice·artifact-tool 중 실제 사용한 방법만 기록한다.

상세본과 발표본의 모든 장표에서 글자 잘림·겹침·밀도, 한글 폰트 대체, 대비, 차트 축·값·단위·범례·출처, 이미지 크롭·비율·캡션, 편집 가능한 표·차트의 값과 원문 일치를 직접 확인한다. 폰트·이미지의 사용 권리도 확인한다.

`reviews/visual.json`의 루트 필드는 pitch 검수다. 공통 deck_sha256와 함께 evidence_sha256(evidence/evidence.json), source_documents_sha256(data/raw/documents.json)를 기록한다. 근거·원문이 바뀌면 덱 문장이 그대로여도 출처와 발표자 노트를 다시 확인해야 한다. `views.master`에는 master의 verdict, pptx_sha256, render_method, render_files, slides_reviewed, checks를 별도로 기록한다. 체크 항목은 text_overflow, font_substitution, contrast, chart_labels, image_crops다. 해당 출력과 실제 검토 결과가 있을 때만 pass다. 수정 후에는 현재 PPTX와 deck의 해시로 다시 검수한다.

## 300초 배분과 대본

v1.5 신규 프로젝트는 기존 다섯 시각 검사에 hierarchy, evidence_legibility, composition_variation을 추가한다. pitch 루트와 views.master마다 reviewer/rationale, 모든 장표의 `visual_observations: [{slide_id, hierarchy, evidence_legibility}]`, 연속 구성의 `composition_review`를 작성한다. 핵심 결론이 먼저 보이는지, 출처·단위·UI의 중요 부분을 실제 크기에서 읽을 수 있는지, 내용 관계에 따라 구성이 달라지는지 직접 보고 판단한다. 주관적 숫자 점수나 UI 자동화 성공을 디자인 통과의 근거로 쓰지 않는다. 눈으로 확인한 렌더 파일의 render_sha256을 각 view에 저장하고 수정하면 다시 렌더·검수한다.

다음은 목차별 연습용 예산이다. 정석biz 노하우 교안의 공식 시간 규칙이나 고정 장수 규칙이 아니다.

| 순서 | 목차 | 최소 장수 | 기본 초 |
|---|---|---:|---:|
| 01 | 표지 | 1 | 10 |
| 02 | 문제 배경 및 최근 트렌드 | 1 | 15 |
| 03 | 문제 정의 | 2 | 20 + 20 |
| 04 | 기존 대체재의 문제점 | 2 | 20 + 20 |
| 05 | 해결방안 | 1 | 20 |
| 06 | 제품 및 서비스 소개 | 2 | 20 + 20 |
| 07 | 초기 고객 반응 | 1 | 20 |
| 08 | 수익 모델 | 1 | 20 |
| 09 | 시장 규모 | 1 | 20 |
| 10 | 초기 시장 진입 전략 | 2 | 15 + 15 |
| 11 | 성장 전략 | 1 | 15 |
| 12 | 마일스톤 | 1 | 15 |
| 13 | 팀 구성 | 1 | 10 |
| 14 | 비전 | 1 | 5 |

발표본의 `seconds` 합계를 `views.pitch.target_seconds: 300`에 맞춘다. 전환·호흡·제품 화면을 보여주는 시간도 포함한다. 지정 목차 순서와 최소 장수를 유지하면서 시간을 다시 배정한다.

`output/pitch-script.md`에 발표본의 장표별 대본·시간·전환과 예상 질문을 쓴다. 화면의 모든 텍스트를 낭독하지 않는다. 각 단계의 목표·일정·검증 기준을 연결하고 세부 질문의 master 장표 위치를 적는다.

실제 리허설이나 사용자의 측정 기록이 있으면 `method: measured`와 측정 시간을 쓴다. 없으면 `method: estimated`, `duration_seconds`, 발화량·속도·전환 시간을 설명한 `estimation_basis`를 기록한다. 추정만으로 실제 리허설 완료를 주장하지 않는다.

## 최종 전달

필수 질문과 데이터가 비어 있으면 초안은 만들 수 있지만 final은 통과할 수 없다. 자료가 없는 값을 생성하지 않고 보완 요청을 남긴다. 구조 검사는 참조·누락·해시를 확인하며 주장 의미와 사업 논리를 자동 증명하지 않는다.

단계 기록과 두 출력의 실제 검수가 완료되면 `harness.py check --project . --stage final` 후 `harness.py finalize --project .`를 실행한다. 검수한 초안과 동일한 바이트의 최종본을 전달한다. 미완료 단계가 있으면 초안·누락 목록·다음 조치로 마무리한다.
