# v1.5.0 자료·질문·시각 구성 계약

총괄은 정본을 병합하고 하위 에이전트는 `work/<run_id>/<role>/`에 후보를 쓴다. [deck 스키마](../schemas/deck.schema.json), [evidence 스키마](../schemas/evidence.schema.json), `scripts/quality.py`와 실제 검사 결과가 기계 계약이다. 필드가 있다는 사실과 원문이 주장을 지지하는지는 별도 검수한다.

## 입력과 근거

사용자 지정 외부 폴더를 읽을 수 있다. 추출 전에는 `project.json`의 `input_dir`를 읽고 선택한 한 팀의 사본을 그 폴더에 복사한다. 신규 교육생 프로젝트는 `자료넣는곳`, 기존 프로젝트는 `input/` 등 기존 설정을 유지한다. 원래 파일은 수정하지 않는다. 외부 원본이 바뀌면 사본도 갱신·재추출한다. 여러 팀의 신청서를 한 덱에 섞지 않는다.

gate는 설정된 입력 폴더의 파일 집합·해시를 inventory의 `source_file`, `source_id`, `sha256`과 대조한다. 외부 경로만 ingest하거나 프로젝트 밖 symlink로 대체하지 않는다. documents의 본문과 assets의 이미지 각각 `source_id`, `locator`가 원본에 연결되어야 한다. HWP 문단 위치와 쪽 번호, 이미지 추출과 이미지 판독을 구분한다.

`evidence/evidence.json`은 `items` 배열이다.

| 필드 | 의미 |
|---|---|
| id, claim | 안정적인 근거 ID와 정확한 주장 |
| kind | internal, external, assumption |
| status | confirmed, unverified, contradicted |
| source_id, locator | 내부 원본 ID와 쪽·문단·표·그림 위치 |
| url, publisher, accessed_at, verification_note | 외부 원문 URL·기관·확인일·실제 읽은 범위 |
| period, unit, limitations | 기간·단위·측정 및 적용 한계 |

원문을 읽고 주장·대상·기간·단위를 확인한 경우에만 confirmed다. 자기기재 경력을 읽은 것과 경력을 독립 검증한 것을 구분한다. 내부 매출·고객·제품 성능은 내부 근거로 확인하며 외부 통계·타사 연구로 대체하지 않는다. 가정에서 계산한 결과는 추정이고 모든 입력 근거와 계산식을 남긴다.

`evidence/section-map.json`은 `sections: [{section, evidence_ids, asset_ids, missing_data}]` 구조다. 사용자 지정 14목차를 각각 한 번 포함하고 근거·추출 이미지 ID를 연결한다. 이 자료 분류표는 질문에 답한 원고를 대신하지 않는다.

## 질문별 원고

사용자 지정 순서는 표지 → 문제 배경 및 최근 트렌드 → 문제 정의 → 기존 대체재의 문제점 → 해결방안 → 제품 및 서비스 소개 → 초기 고객 반응 → 수익 모델 → 시장 규모 → 초기 시장 진입 전략 → 성장 전략 → 마일스톤 → 팀 구성 → 비전이다. 문제 정의·기존 대안·제품 소개·초기 시장 진입은 각각 독립 장표 2개 이상, 나머지는 1개 이상으로 master와 pitch 각각 최소 18장을 만든다. 초기 고객 확보와 이후 성장을 분리하며 기존 대안 2장은 문제 정의 뒤·해결방안 앞에 둔다. 이번 교육 범위에서는 투자 요청·조달·금액·사용 계획을 덱·대본·질문에 넣지 않는다. 마일스톤은 목표·일정·산출물·검증 기준으로 구성한다.

`deck/section-briefs.json`에는 14목차의 투자자 질문 18개를 저장한다. [정석biz 노하우 기준](kdb-curriculum.json)의 `topics[].question_contracts`가 기준이다. `quality.initial_briefs()`와 프로젝트 init/migrate가 같은 빈 원고를 만든다. 질문 ID와 required_data 문구를 임의로 바꾸지 않는다.

```json
{
  "schema_version": "1.2",
  "sections": [{
    "section": "solution",
    "questions": [{
      "question_id": "solution.q1",
      "question": "고객 문제를 대안보다 어떻게 더 잘 해결하는가",
      "status": "partial",
      "answer": {"text": "계획: 고객의 반복 작업을 줄인다", "kind": "plan", "evidence_ids": []},
      "argument": [{"text": "계획: 동일 과업에서 현재 대안과 작업시간을 비교한다", "kind": "plan", "evidence_ids": []}],
      "coverage": [{"requirement": "측정 조건", "claim": null}],
      "evidence_ids": [],
      "visual_refs": [],
      "missing": ["기존 대비 실측 편익과 측정 조건 필요"]
    }]
  }]
}
```

한 질문의 일부를 설명한 예시다. 실제 파일에는 모든 질문과 해당 required_data의 coverage가 필요하다.

- status는 answered, partial, missing이다. 미완료이면 구체적인 missing을 남긴다.
- answer는 질문의 직접 답변 claim 또는 null이다.
- argument는 답을 뒷받침하는 claim 배열이다. 요약문만 있고 논거가 없으면 완료가 아니다.
- coverage는 `{requirement, claim}` 배열이다. 첫 질문에 해당 목차의 required_data를 모으고 뒤 질문은 중복 coverage 없이 답과 논거를 쓴다. 모르는 claim은 null이다.
- visual_refs는 `{slide_id, block_id}` 배열이며 답·논거를 보여 주는 실제 장표 블록에 연결한다.
- claim 형태는 `{text, kind: fact|assumption|plan, evidence_ids, scope?}`다. 회사 실적은 scope: company로 표시한다.

기초자료 누락은 초안 warning과 semantic_gaps로 보존할 수 있으나 **final에서는 오류**다. 적절한 계획·가정과 아직 모르는 필수 사실을 구분한다. 없는 근거를 answered로 바꾸지 않는다. 잘못된 fact 참조는 초안에서도 오류다.

## 공통 장표와 master/pitch

`deck/deck.json` schema_version은 1.2이다. slides는 공통 장표 풀이고 views의 slide_ids는 각 덱의 순서다.

```json
{
  "schema_version": "1.2",
  "team_name": "팀명",
  "slides": [],
  "views": {
    "master": {"slide_ids": ["M01", "M02"]},
    "pitch": {"slide_ids": ["P01"], "target_seconds": 300}
  }
}
```

구조 설명용 예시다. 실제 slides에는 모든 참조 ID의 장표가 있어야 한다. 마스터 장표를 그대로 발표하면 같은 ID를 선택한다. 따로 압축한 P01에는 `source_slide_ids: ["M01", "M02"]`로 원본 장표를 연결한다. v1.2의 `section_ids`는 지정할 때 반드시 `[section]` 한 항목이다. 하나의 목차만 가진 master 장표 여러 개를 같은 목차의 pitch 장표로 압축할 수 있지만, 여러 목차를 섞은 복합 목차 장표는 오류다. 두 view 모두 지정한 14목차 순서를 지키고 최소 18장의 독립 장표를 둔다. problem, alternatives, product, go_to_market은 각각 2장 이상, 나머지는 1장 이상이다. section_ids 여러 개를 붙인 한 장으로 필수 장수를 대신하지 않는다.

장표 공통 필드는 id, section, 필요 시 section_ids/source_slide_ids, governing_message, governing_kind, governing_evidence_ids, layout, blocks, seconds, speaker_notes다. 회사 실적 거버닝은 governing_scope: company다. 거버닝 메시지는 66자 이내를 기본 목표로 한다. v1.2의 더 긴 메시지는 경고와 실제 렌더 가독성 검토를 요구한다. 피칭 시간을 target_seconds에 맞추며 마스터 전체에 300초 상한을 적용하지 않는다.

## 장표별 시각 구성안 — visual_brief

파일의 schema_version은 1.2를 유지한다. v1.5.0 신규 프로젝트는 `project.json`에 `harness_version: "1.5.0"`, `require_visual_briefs: true`, `require_visual_plan: true`를 기록한다. 기존 프로젝트에 이 플래그가 없으면 이전 초안과 검수 기록을 읽을 수 있다. 새 작업의 검사를 통과시키기 위해 플래그를 끄지 않는다.

모든 새 장표의 `visual_brief`에 아래 다섯 필드를 작성한다. `key_message`는 거버닝 메시지와 같은 결론을 전달하며 새로운 미검증 주장을 추가하지 않는다.

```json
{
  "key_message": "계획: 사진 입력으로 기록 단계를 줄인다",
  "primary_block_id": "PRODUCT_SCREEN",
  "reading_order": ["PRODUCT_SCREEN", "USER_BENEFIT"],
  "layout_variant": "product_hero",
  "visual_reason": "가상 설계 화면의 입력부를 크게 보여 주고 고객 편익을 연결한다"
}
```

`primary_block_id`는 실제 블록을 가리키며 `reading_order`는 모든 블록 ID를 누락·중복 없이 포함한다. 빈 문구나 잘못된 참조는 초안에서도 오류다. 구성안 자체가 없으면 story/research/review에서는 보완 경고로 남기고 design/pitch/final에서는 오류로 처리한다.

| layout_variant | 주요 블록과 구성 목적 |
|---|---|
| evidence_focus | image/chart/table/metric/text/steps/mapping: 근거와 해석의 중요도 구분 |
| comparison_focus | table/mapping: 동일 기준 비교 또는 대응 관계 |
| product_hero | image 또는 화면 asset이 있는 steps: 제품의 핵심 작동부 확대 |
| market_layers | formula: 시장 범위와 산정 입력의 단계 관계 |
| timeline_focus | roadmap/steps: 시간·실행·검증 단계 |
| team_focus | team: 역할·경험·실행 책임 |
| cover_focus | 내용에 맞는 블록: 사업의 한 문장과 첫 인상 |

신규 제품 장표마다 원본 화면·사진 또는 **가상 설계라고 표시한 이미지**가 필요하다. product_hero의 주요 블록 자체가 이미지를 포함해야 하며 설명 텍스트만으로 통과할 수 없다. image 또는 steps.items[].asset에 path/source와 원본 evidence_ids를 연결한다. 하위 asset은 item/block의 evidence_ids를 상속할 수 있다. 파일 존재·프로젝트 내부 경로·사용권도 검사한다. 자료가 없으면 필요한 화면·촬영 범위를 구체적으로 기록하고 디자인 완료를 보류한다. 표·차트도 실제 데이터 또는 명시한 교육용 가정에서 만들며, 빈 근거를 꾸민 추세선으로 대체하지 않는다.

## 복합 시각 블록

v1.2은 blocks로 본문·표·차트·사진·설명 도식을 함께 구성한다. 블록 공통 필드는 id, type, title, kind, evidence_ids다. 하위 item은 kind/evidence_ids를 상속하거나 재정의한다.

| type | 필수 내용 |
|---|---|
| text | text |
| metric | value, detail |
| image | path, caption, source, rights, alt |
| table | columns, rows. 각 행의 열 수가 같고 문자열 셀 사용 |
| chart | chart_type: bar 또는 line, categories, series: [{name, values}], unit, source |
| steps | items: [{title, text}] |
| mapping | items: [{problem, solution, proof}] |
| formula | items: [{label, formula, result, basis}] |
| roadmap | items: [{period, title, deliverables: [], gate}] |
| team | items: [{name, role, proof, contribution}] |

복합 layout은 evidence_board, problem_solution, product_journey, market_model, competition_matrix, milestone_roadmap, team_evidence와 cover/closing이다. quality.py의 BLOCK_FIELDS·ITEM_FIELDS 및 제작기 구현을 따른다. 논증에 맞는 구성을 고르고 실제 렌더로 공간을 확인한다.

현재 복합 레이아웃이 요구하는 최소 블록은 다음과 같다. 대괄호 안은 한 가지 이상을 선택한다. 이 목록은 제작기의 구성 계약이며 정석biz 노하우의 정보 분량 제한이 아니다.

| layout | 필요한 블록 |
|---|---|
| problem_solution | mapping + [text, image] |
| product_journey | steps + text |
| market_model | formula + [text, chart] |
| competition_matrix | table + text |
| milestone_roadmap | roadmap 정확히 1개(items 2~4개) + 선택 text/metric 합계 0~2개 |
| team_evidence | team + text |
| evidence_board | [image, chart, table, metric] + text. 시각자료는 최대 2개 |

표·이미지·차트를 사용할 수 있다는 것은 임의의 개수와 길이를 한 화면에 넣어도 된다는 뜻이 아니다. 현재 제작기의 공간 한도를 확인하고 넘는 내용은 상세본의 다른 장표로 보존한다.

**blocks에는 본문 3줄 제한이나 이미지·차트 동시 배치 금지를 적용하지 않는다.** 이는 v1.0 legacy body/assets/visual 계약의 제약이었다. 새 덱은 blocks를 사용하고 밀도가 높으면 마스터 장표를 나눈 뒤 피칭으로 재구성한다. 논거를 버리고 같은 카드 몇 개로 맞추지 않는다.

이미지 rights는 확인한 owned, licensed, permission, public-domain 중 하나다. 권리 미확인 이미지는 후보 대장에 남긴다. 생성 이미지는 설명용이며 실제 제품·실험·고객의 증거가 아니다.

## 제작과 검수

```text
python .agents/skills/seed-ir/scripts/render_deck.py --project . --variant master
python .agents/skills/seed-ir/scripts/render_deck.py --project . --variant pitch
```

--view는 같은 옵션이다. output/master와 output/pitch에 각각 seed-ir-draft.pptx, storyboard.html, render-report.json, renders가 생성된다. 피칭 PPTX·스토리보드·보고서는 호환 경로 output에도 복사한다. 렌더 파일 생성과 내용의 직접 검수는 다르다.

- reviews/extraction.json: inventory_sha256, reviewed_source_ids, ocr_review_complete와 실제 판독 범위·한계.
- reviews/investor.json: deck_sha256, briefs_sha256, evidence_sha256, source_documents_sha256, reviewer, rationale, verdict, findings, question_verdicts. 마지막 배열은 질문 18개의 question_id, verdict, rationale를 각각 포함한다. 답·논거·coverage의 의미를 대조한다.
- reviews/visual.json: reviewer, rationale, 공통 deck_sha256, evidence_sha256, source_documents_sha256와 피칭 pptx_sha256, render_method, render_files, render_sha256, slides_reviewed, checks, verdict, findings. views.master 안에도 마스터의 pptx_sha256, 실제 렌더 방법·파일·장표 목록, render_sha256, checks와 verdict를 담는다. render_sha256는 실제로 눈으로 확인한 현재 렌더 이미지의 프로젝트 상대 경로를 키로, SHA256을 값으로 저장한 맵이다.
- checks: text_overflow, font_substitution, contrast, chart_labels, image_crops. 신규 v1.4 프로젝트는 hierarchy, evidence_legibility, composition_variation도 각각 실제 검수 뒤에만 pass다.
- reviews/pitch.json: 현재 deck_sha256, evidence_sha256, source_documents_sha256, pptx_sha256, reviewer, rationale, duration_seconds, method: estimated 또는 measured, verdict, findings. 추정은 발화량·속도·전환시간의 estimation_basis가 필요하다.

두 view 모두 모든 장표를 확인한다. evidence_sha256는 evidence/evidence.json, source_documents_sha256는 data/raw/documents.json의 현재 SHA256이다. investor와 visual 루트에 둘 다 기록한다. 덱 문장이 같더라도 근거 내용·추출 원문이 바뀌면 예전 receipt로 다시 record할 수 없다. 실제 재검수 후 새 지문을 기록한다. 참조 이미지의 바이트 변경도 story 이후 상태를 무효화한다. 실제 render_method는 powerpoint, libreoffice, artifact-tool 중 수행한 도구다. P0/P1이 남으면 pass를 쓰지 않는다. 질문 원고·장표가 바뀌면 이전 해시를 재사용하지 않는다. `harness.py hash --project . <상대경로>`로 계산한다. 최종 검사 뒤 finalize를 실행하며 최종 출력 목록은 deliverables.json을 따른다.

신규 프로젝트의 시각 검수에는 **pitch 루트와 views.master 각각** reviewer, rationale, `visual_observations: [{slide_id, hierarchy, evidence_legibility}]`, `composition_review`를 추가한다. 모든 장표를 한 번씩 기록하고 hierarchy에는 먼저 읽힌 제목·증거·보조 정보, evidence_legibility에는 실제 화면에서 읽은 수치·제품 작동부·단위·출처와 수정 내용을 구체적으로 적는다. composition_review에는 연속 장표에서 비교·제품·시장·실행의 관계가 구별되는지 적는다. 임의의 주관적 숫자 점수는 요구하지 않는다. 프로그램은 기록의 누락·참조를 검사하며 화면의 설득력을 자동 판정하지 않는다.

교육용 배포 예시는 사용자 소유 가상 사업 **글루코픽(GlucoPic)**이다. 인터뷰·반응·인물·가격·성과·전망은 가상 사례, 가정 또는 계획으로 표시한다. 원본 교육 문서에서 확인한 내용은 현실에서 검증된 사업 사실과 구분하며 실제 팀 자료로 바꿀 때 예시 값을 옮기지 않는다.

## 도구 부재

온라인 도구가 없으면 research pending과 초안 산출을 유지한다. 실행하지 않은 온라인 로그를 만들지 않는다. 기본 research_required:true는 사용자가 외부조사 제외 범위를 명시한 경우에만 총괄이 요청을 기록하고 바꿀 수 있다. disclosed 공백의 disclosure_slide_id는 현재 덱에 존재하고 실제 장표에 한계가 보여야 한다.

복합 제작은 Codex 환경의 Node와 @oai/artifact-tool 런타임을 탐색한다. 없으면 설정 안내를 진행하거나 제작을 미완료로 남긴다. 다른 유료 서비스는 필수가 아니다.

## 1.0/1.1 이행

`harness.py migrate --project .`는 기존 deck·briefs·section-map·project를 `.pre-v1.2.v1.0.json` 또는 `.pre-v1.2.v1.1.json` 이름으로 백업한 뒤, 14목차·18질문의 빈 원고와 최소 18장 틀로 재분류한다. 원문과 evidence는 보존한다. 기존 12장 장표를 새 기준을 충족한 완성본으로 자동 전환하지 않으며, 백업의 답·근거를 새 목차에 다시 연결하고 검수해야 한다.


## 장표별 시각 자료 계획 — v1.5.0

`design/visual-plan.json`의 `schema_version: "1.0"`, `slides`에 두 view에서 사용하는 모든 장표를 각각 한 번 기록한다. `scripts/visual_plan.py`가 현재 근거·장표·파일 바이트를 검사한다. 신규 프로젝트는 디자인 단계부터 필수다. 기존 프로젝트에 플래그가 없으면 이전 기록을 읽을 수 있으며, 작성한 계획 파일이 있으면 동일하게 검사한다. 검사를 피하려고 새 프로젝트의 플래그를 낮추지 않는다.

항목: `slide_id`, 현재 근거의 `evidence_ids`, 실제 표시하는 `block_ids`, `visual_type`(photo/product_ui/chart/table/diagram/quote/mixed), `source_strategy`(original/official/generated/native), `asset_refs`, `disclosure`, `claim_boundary`, `status`(planned/ready/missing), `search_note`.

`asset_refs`는 객체 배열이며 각 객체에 `path`, `sha256`, `source`, `rights`(owned/licensed/permission/public-domain), `origin`(original/official/generated), `caption`, `claim_boundary`가 필요하다. 자산 경로는 해당 장표에서 block_ids가 선택한 image 블록 또는 steps.items[].asset과 연결된 프로젝트 내부 상대 경로다. 생성 자산은 계획과 실제 장표 캡션에 AI 생성·설계·예시임을 표시한다. 사진 사용권이 확인되지 않으면 후보 기록으로 남기고 native 표·차트·도식을 설계한다. native 전략은 빈 asset_refs가 가능하며 search_note에 이미지 대신 사용한 근거와 표현 이유를 기록한다.

`visual_brief.supporting_assets`에 이미지 객체를 둘 수 있다. 자산 경로는 stale 지문에 포함하지만, 메타데이터만으로 화면에 표시된 것으로 인정하지 않는다. 실제로 사용하는 이미지는 image 블록 또는 steps.items[].asset에도 연결해 렌더하고 출처·권리·캡션을 유지한다. 선택한 renderer가 해석하지 않는 art_direction 필드나 문서상의 배치만으로 표시 완료를 기록하지 않는다. 프로젝트별 구성을 작성할 때는 표시 문구·숫자를 현재 blocks에서 가져오고 실제 표시한 ID만 coverage에 기록한다. 고정 예시 문구를 화면에 그린 뒤 모든 블록을 소비했다고 일괄 표시하지 않는다.

파일·해시 검사는 내용의 사실 여부나 전문가 디자인 판정을 대신하지 않는다. 상세 기획·생성·대표 화면·전체 검수 절차는 [시각 제작 절차](visual-production.md)를 따른다.
