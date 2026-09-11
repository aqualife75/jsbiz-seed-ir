# jsbiz-seed-ir — Seed IR Deck 멀티 에이전트 하네스 설계서

- 작성일: 2026-09-11 · 작성: 이동건(정석Biz) + Claude Code
- 상태: 사용자 구두 승인(2026-09-11) 반영본 — 라이선스 미확인 이미지 수집 허용으로 §6 수정
- 대상: 제16회 포스텍 창업경진대회 참가팀(Seed 준비 극초기) 및 정석Biz 교육생 일반

---

## 0. 한 문장 요약

창업팀 자료 폴더 하나를 넣으면, KDB 창업교육 「IR Deck 작성 Ver4.0」의 **12 주제 × 투자자 질문** 기준으로
6개 에이전트가 ①자료 판독 → ②거버닝 메시지·본문 → ③검산·5인 모의심사 → ④인터넷·논문 근거 보완·개정 →
⑤샘플(글루코픽) 수준 디자인 PPTX → ⑥5분 피칭 최종 검수까지 수행하고,
**덱 안의 모든 숫자가 사실 팩 또는 증거 원장으로 추적되는 것을 스크립트가 강제**하는 Claude Code 플러그인.

---

## 1. 목표 · 비목표

### 목표
1. 입력: 폴더 1개. hwp/hwpx·pdf·docx·pptx·xlsx·md/txt·이미지(jpg/png/bmp) 혼재 허용. 포스텍 참가신청서 hwp 1개만으로도 완주.
2. 출력(항상 4종): `{팀명}_Seed_IR_Deck.pptx`(16:9, Pretendard, 편집 가능) · `.pdf` · `피칭가이드.md` · `qa_png/`.
3. 내용 기준 = KDB 교안 Ver4.0(12 주제, 투자자의 시각 ①②, 주제별 작성 가이드, 슬라이드 해부학 4요소, 작성 고려사항 9) + 정석Biz 프롬프트팩 STEP 0~5.
4. 디자인 기준 = 샘플 `샘플_글루코픽_GlucoPic__사업계획서.pptx`에서 추출한 토큰·레이아웃(§5).
5. 부족한 근거는 사람이 아니라 **근거 조사 에이전트**가 인터넷·논문·통계에서 찾아 출처와 함께 채운다. 그래도 없으면 `[확보 필요]`.
6. 교육생이 두 줄 설치로 쓸 수 있는 배포형(플러그인 마켓플레이스) + 사용법 HTML.

### 비목표
- 영문 덱(→ `jsbiz-global-ir`), 정부지원사업 사업계획서(→ `biz-mentor`), Pre-A 이상 재무모델.
- HTML 발표본(80주차 방식). 본 하네스는 PPTX/PDF만 산출한다.
- 실제 회사 로고 생성, 가짜 고객 리뷰·가짜 수치 생성(절대 금지).

---

## 2. 배포 구조

### 2-1. 저장소 `aqualife75/jsbiz-seed-ir`

```
jsbiz-seed-ir/
├── .claude-plugin/marketplace.json        # name: "jsbiz-seed-ir", plugins: [seed-ir]
├── plugins/seed-ir/
│   ├── .claude-plugin/plugin.json         # name: "seed-ir"
│   ├── agents/                            # 6개 (§4) — 플러그인 설치 시 `seed-ir:ir-intake` 형태로 노출
│   │   ├── ir-intake.md
│   │   ├── ir-writer.md
│   │   ├── ir-panel.md
│   │   ├── ir-researcher.md
│   │   ├── ir-designer.md
│   │   └── ir-finalizer.md
│   └── skills/seed-ir/
│       ├── SKILL.md                       # 오케스트레이터 (`/seed-ir`)
│       ├── references/
│       │   ├── kdb_12_topics.md           # 12 주제 × 투자자 질문 × 작성 가이드 × 증거 우선순위 (KDB 원문 기반)
│       │   ├── investor_lenses.md         # 성장률·리스크 렌즈, PS/PM Fit, 흐름 설계 13 질문, 고려사항 9
│       │   ├── writing_rules.md           # 7필드 형식, 라벨([추정][목표][자료 없음][기입 필요][확보 필요]) 규칙, 톤
│       │   ├── review_rubric.md           # 5인 심사역 페르소나·채점 기준·심각도 정의·12 질문 O/△/X 기준
│       │   ├── evidence_policy.md         # Tier A/B/C, 조사 채널, 주제별 evidence_targets, 원장 필드
│       │   ├── design_system.md           # 토큰·타이포·컬러·해부학 배치·레이아웃 22종 슬롯/글자수 상한
│       │   ├── pitch_5min.md              # 시간 배분표, 대본 분량, 발표자 노트 형식, Q&A 부록 규칙
│       │   └── qa_checklist.md            # 내용 8 + 디자인 7 + 피칭 4
│       ├── scripts/
│       │   ├── harness.py                 # CLI 진입점: init/extract/validate/trace/gate/build/qa/pdf/status
│       │   ├── extractors/                # hwp.py(OLE+BinData) · hwpx.py · pdf.py · docx.py · pptx.py · xlsx.py · images.py
│       │   ├── validate.py                # JSON 스키마 + 필드 규칙 검증
│       │   ├── trace_numbers.py           # 슬라이드 숫자 ↔ 사실 팩/증거 원장 대조
│       │   ├── build_deck.py              # deck_spec.json → PPTX (python-pptx, 레이아웃 22종)
│       │   ├── render_qa.py               # PPTX → PNG(+PDF): PowerPoint COM / LibreOffice / 없음 안내
│       │   ├── capture_evidence.py        # URL → 문단/figure 스크린샷 (Chrome/Edge 헤드리스)
│       │   └── prep_image.py              # 크롭·어둡게·라운딩·BMP→PNG·리사이즈
│       └── assets/
│           ├── schemas/                   # fact_pack · storyline · slides · review · evidence · deck_spec .schema.json
│           ├── spec.example.json          # 셀아이(가상) 덱 스펙 — 이미지 없이 빌드 가능
│           └── icons/                     # 단색 SVG→PNG 아이콘 소수 (틴팅)
├── docs/index.html                        # 교육생 사용법 (GitHub Pages)
├── docs/superpowers/specs/…               # 이 문서
├── evals/fixtures/셀아이/                 # 가상 팀 사실 팩 md + 가상 이미지 3장
├── evals/evals.json
├── README.md
└── LICENSE (MIT)
```

- 설치: `/plugin marketplace add aqualife75/jsbiz-seed-ir` → `/plugin install seed-ir@jsbiz-seed-ir`
- 실행: `/seed-ir "C:/팀자료폴더"` 또는 "이 폴더 자료로 Seed IR덱 만들어줘"
- 개발 원본: `00. A_B_정석Biz/99. 프로젝트/2026.09.11_seed-ir-deck_하네스/jsbiz-seed-ir/` (git). 로컬 설치본: `.claude/skills/seed-ir/`, `.claude/agents/ir-*.md` (수동 동기화, jsbiz-global-ir와 동일 규칙).
- 하네스 스크립트는 **저장소 안에서 자족**한다 — Dropbox `.claude/*.py`를 import 하지 않는다(교육생 환경에 없음).

### 2-2. 교육생 환경 요구사항
| 항목 | 필수 | 용도 |
|---|---|---|
| Claude Code (Windows/Mac) | ● | 실행 |
| Python 3.10+ · `pip install python-pptx pymupdf pillow olefile python-docx openpyxl jsonschema` | ● | 추출·빌드·검증 |
| Chrome 또는 Edge | ● | 근거 캡처(헤드리스) |
| Pretendard 폰트 설치 | ● | 렌더 정확도 (미설치 시 시스템 고딕 대체, 경고) |
| PowerPoint 또는 LibreOffice | ○ | PNG 렌더 검수·PDF. 없으면 PPTX만 산출하고 가이드에 "PowerPoint에서 PDF 저장" 안내 |
| Node/npm | ✕ | 불필요 |

---

## 3. 하네스 (판단은 에이전트, 규칙은 스크립트)

### 3-1. 워크스페이스
실행마다 `{출력폴더 기본=입력폴더 상위}/{YYYY.MM.DD}_{팀명}_SeedIR/`:

```
state.json             단계별 status(pending/running/done/failed) · 게이트 결과 · 타임스탬프 · 사용자 승인 기록
run_log.md             에이전트별 요약 보고 누적
01_extract/            {원본파일명}.txt 덤프 · images/{파일}_{n}.png · image_catalog.json
02_fact_pack.json      10항목 사실 팩 + topic_slots[12] + gaps[] + contact(표지용)
03_storyline.json      slides[12~14]: topic, no, investor_question, key_message, type, data_status
04_slides_v1.json      slides[]: question/title/lead/evidence[≤3]/key_numbers[≤3]/source/open_question/labels
05_review/             numbers_check.json · panel_{vc,ac,domain,finance,layman}.json · summary.json
06_evidence/           evidence.json · captures/*.png · web_images/*.{png,jpg} · image_ledger.json
07_slides_v2.json      개정본 + changes[] + to_secure[] (확보 필요)
08_deck_spec.json      레이아웃 매핑 스펙 (+notes 초안)
09_build/              {팀명}_Seed_IR_Deck_v1.pptx · qa_png/ · qa_report.md
10_final/              {팀명}_Seed_IR_Deck.pptx · .pdf · 피칭가이드.md · qa_png/
```

### 3-2. `harness.py` CLI (결정적 작업 전담)
| 명령 | 동작 |
|---|---|
| `init <입력폴더> [--team 팀명] [--out 폴더]` | 워크스페이스·state.json 생성, 입력 파일 목록 기록 |
| `extract` | 확장자별 추출기 실행 → `01_extract/`. hwp: OLE BodyText 텍스트 + BinData 이미지(BMP→PNG, ole 객체 제외). hwpx: `Contents/section*.xml` `<hp:t>` + BinData. pdf: PyMuPDF 텍스트+임베디드 이미지+페이지 렌더(표 많은 페이지용). docx/pptx: 텍스트+media. xlsx: 시트→CSV 텍스트. 이미지: 그대로 복사(+EXIF 회전 보정) |
| `validate <phase>` | `assets/schemas/*.schema.json` + 필드 규칙(§3-4) 검증. 실패 시 항목별 메시지, exit 1 |
| `trace` | `07_slides_v2.json`(또는 v1)의 모든 숫자 토큰을 `02_fact_pack.json` + `06_evidence/evidence.json`의 값과 대조. 단위·천단위 구분 정규화. 미추적 숫자 목록 출력, 1건이라도 있으면 exit 1 |
| `gate <phase>` | 다음 단계 진입 조건 판정(§3-3). 통과/거부 사유를 state.json에 기록 |
| `build [--spec 08_deck_spec.json]` | PPTX 빌드 + 슬롯 글자수 상한 초과 목록 |
| `qa [--slides N M]` | PNG 렌더 + 자동 검사(빈 슬롯·출처 누락·페이지번호·텍스트박스 경계 초과 추정) → `qa_report.md` |
| `pdf` | PowerPoint COM / LibreOffice로 PDF. 둘 다 없으면 안내 후 exit 2 |
| `status` | 단계 진행표 출력(재개 지점 확인용) |

### 3-3. 게이트 (순서 강제)
| 진입 단계 | 조건 |
|---|---|
| Phase 2 (작성) | `validate fact_pack` 통과 · topic_slots 12개 존재(빈 슬롯은 `[자료 없음]` 명시) |
| Phase 3 (심사) | `validate slides` 통과 · 장수 12~14 · 모든 장에 investor_question·title·source |
| Phase 4 (조사·개정) | `05_review/summary.json` 존재 |
| Phase 5 (디자인) | `trace` 통과 · summary.critical 중 unresolved 0 **또는** 사용자가 `--accept-risk`로 승인(state에 기록) · `[기입 필요]` 0건 |
| Phase 6 (피칭 검수) | `qa_report.md`에 blocking 결함 0 |
| 완료 | 10_final 4종 존재 · `trace` 재통과(디자인 중 숫자 변형 방지) |

### 3-4. 데이터 계약 (스키마 핵심 필드)
- **fact_pack**: `company{name, one_liner, founded, ceo, headcount}`, `items[10]{key, value, asof, source, status: given|missing}`, `topic_slots[12]{topic_id, facts[], images[], status}`, `gaps[]{item, why_needed, topic_ids}`, `contact{name, email, phone}`(표지 전용, 학번·주민번호 제외).
- **image_catalog**: `images[]{file, origin_file, w, h, description(비전 판독 1~2문장), kind: product|screen|chart|photo|logo|cert|table|other, suggested_topics[], has_korean_text, quality: ok|low}`.
- **storyline**: `slides[]{no, topic_id, investor_question, key_message, type: cover|body|statement|appendix, data_status: sufficient|partial|missing}` — 12 주제 전부 어딘가에 배정되어야 함(합치기 허용, 표시).
- **slides(v1/v2)**: `slides[]{no, topic_id, investor_question, title, lead, evidence[≤3]{text, number?, source}, key_numbers[≤3]{value, unit, label, kind: fact|estimate|target, source}, source, open_question, weakness_row?(경쟁 장 필수), labels[]}`.
- **review/summary**: `scores{vc, ac, domain, finance, layman, avg}`, `question_check[12]{topic_id, verdict: O|△|X, reason}`, `issues[]{id, severity: critical|major|minor, slide_no, text, fix_hint, status: open|resolved|accepted}`, `attack_questions[15]`, `to_reach_85[]`.
- **evidence**: `records[]{id, topic_id, slide_no, claim, value, unit, asof, source_title, publisher, url, retrieved, tier: A|B|C, capture_file?, quote?, confidence: high|mid|low}`; **image_ledger**: `images[]{file, url, page_url, title, author, license: cc|public|official|team|unknown, license_note, retrieved, used_in_slides[], needs_human_review: bool}`.
- **deck_spec**: `meta{team, accent, date}`, `slides[]{no, layout, background: dark|cream, slots{…}, source_line, notes, images[]}` — 슬롯·글자수 상한은 `design_system.md` §레이아웃 표를 스키마로 옮긴 것.

---

## 4. 에이전트 6개

공통 규칙(모든 에이전트 정의 상단에 포함):
- 시작 시 `references/` 중 지정 파일을 읽는다. 사실의 유일한 원천은 `02_fact_pack.json` + `06_evidence/evidence.json`.
- 없는 숫자는 만들지 않는다. 라벨: `[자료 없음]`(팀 자료에 없음) · `[기입 필요: 항목]`(작성 단계 임시) · `[추정]` · `[목표]` · `[확보 필요]`(조사로도 못 채움, 팀이 확보).
- 팀 내부 사실(트랙션·팀 경력·가격 결정·자금 사용처)은 **외부 조사로 대체하지 않는다** — 외부 조사는 문제·시장·경쟁·기술·정책 근거에만.
- 반환은 지정 JSON 파일 저장 + 10줄 이내 요약(경로·건수·미해결). 과정 서술 금지.
- 모델은 지정하지 않는다(사용자 기본값 상속). `model: inherit` 사용 금지.

| # | 에이전트 | 입력 → 출력 | 도구 | 핵심 규칙 |
|---|---|---|---|---|
| 1 | **ir-intake** | `01_extract/` → `02_fact_pack.json`, `image_catalog.json` | Read, Write, Bash, Glob, Grep | 파일마다 전량 읽기(긴 PDF는 페이지 분할). 이미지는 Read(비전)로 1장씩 보고 설명·종류·추천 주제 기록. 표 셀 나열(hwp)에서 표 구조 복원 시 `[표 복원: 추정]` 표시. 개인정보는 contact만 |
| 2 | **ir-writer** | fact_pack → `03_storyline.json` → `04_slides_v1.json` | Read, Write | STEP 1: 12 주제 → 12~14장(5분+Q&A 3분), 논리 전환점에 statement 1~2장. STEP 2: 7필드, 제목 = 질문의 답 문장(결론), 근거 불릿 ≤3 각각 숫자 포함, 경쟁 장 약점 1행 필수, Seed 무게중심(문제·팀·시장 두껍게, 재무 얇게: 런웨이·사용처만) |
| 3 | **ir-panel** | slides_v1 → `05_review/*` | Read, Write | 인자 `persona`: numbers(검산 6항목) / vc / ac / domain / finance / layman. 각자 100점 적대적 채점 + 공격질문 3 + 지적(심각도). 오케스트레이터가 6개를 동시에 띄우고, 마지막에 `ir-panel persona=chair`가 병합해 `summary.json`(12 질문 O/△/X, 85점 처방) |
| 4 | **ir-researcher** | summary + slides_v1 + fact_pack → `06_evidence/*` → `07_slides_v2.json` | Read, Write, Bash, WebSearch, WebFetch, Glob | 인자 `mode=gap topic_id=…`(갭별 병렬) / `mode=merge`. 갭별: evidence_targets 충족까지 조사 → 캡처(`capture_evidence.py`) → 원장 기록. merge: 근거 반영해 X·△ 장부터 다시 쓰기, critical→major→minor, 못 고친 것은 to_secure. 숫자 바꿀 때 근거 id 병기 |
| 5 | **ir-designer** | slides_v2 + catalog + ledger → `08_deck_spec.json` → `09_build/` | Read, Write, Edit, Bash, Glob | 장마다 레이아웃 1개 선택(§5 매핑표) · 배경 교차 · 이미지 배치(Tier A 우선, 캡처는 caption+source) · `build` → `qa` → PNG를 Read로 전장 육안 검수 → 넘침·겹침·강조색 남용 수정 반복(최대 3회) · 텍스트를 줄여야 하면 **글자를 줄이지 않고 어느 문장을 줄일지 slides_v2 기준으로 판단해 spec만 수정**(숫자 불변) |
| 6 | **ir-finalizer** | 09_build + slides_v2 → `10_final/*` | Read, Write, Edit, Bash | 5분 타임 테이블(§7) 대로 장별 초 배정·합 300±30 · 발표자 노트에 장별 대본(한국어 1,500~1,700자 총량) · 시각 우선순위 점검(가장 큰 글자=핵심 수치, 한 장 한 메시지) · 앞뒤 숫자 일치 · Q&A 부록(공격질문 15 → 답 또는 [확보 필요]) 2~3장 추가 · `pdf` · 피칭가이드.md 작성 |

### 4-1. 오케스트레이터 `seed-ir` SKILL 흐름
```
0 INTAKE   인자 파싱(입력폴더·팀명·--accept-risk·--resume) → harness init/extract → 요약 표시
1 FACTS    Agent(ir-intake)  → gate 2
2 WRITE    Agent(ir-writer)  → 스토리라인 표를 사용자에게 보여주고 확인(기본 체크포인트 1) → 본문 → gate 3
3 REVIEW   Agent×6 병렬(ir-panel personas) → Agent(ir-panel chair) → 점수·O/△/X 표 표시
4 RESEARCH Agent×N 병렬(ir-researcher gap, N=X·△ 주제 수 ≤ 8) → Agent(ir-researcher merge) → trace
           critical 잔존 시 목록 표시 후 사용자 선택(계속=accept-risk / 중단) (체크포인트 2)
5 DESIGN   Agent(ir-designer) → gate 6
6 PITCH    Agent(ir-finalizer) → 완료 보고(경로 · 장별 제목 · 확보 필요 목록 · 라이선스 확인 필요 이미지 수)
```
- `--resume`: state.json에서 done 단계는 건너뜀. `--from N`으로 특정 단계부터 재실행(하위 산출물 보존, 새 버전 파일명).
- 에이전트 이름 해석: 플러그인 설치면 `seed-ir:ir-intake`, 로컬 `.claude/agents` 설치면 `ir-intake`. SKILL은 "사용 가능한 에이전트 목록에서 `ir-intake`로 끝나는 이름"을 쓰도록 지시.
- 오케스트레이터는 내용 판단을 하지 않는다(요약 표시·게이트·재개만).

---

## 5. 디자인 시스템 (샘플에서 추출)

### 5-1. 토큰
| 토큰 | 값 | 출처(샘플 실측) |
|---|---|---|
| 캔버스 | 20 × 11.25 in (1920×1080) | slide_width/height |
| 폰트 | Pretendard 단일(한글·숫자·라틴). 미설치 시 Malgun Gothic/Apple SD Gothic Neo 대체 | runs 824/824 |
| 배경 | 다크 `#10141B` · 크림 `#F5F2EB` · (표지·비전 다크 + 우측 사진 패널) | bg fill |
| 카드 | 크림 위 흰색 `#FFFFFF` 1px `#E6E2DA` 보더 · 다크 위 `#FFFFFF@4%` + 보더 `#FFFFFF@10%` · 강조 카드 `#E0492E` 그라데이션(→`#F2A33C`) | shape fills |
| 텍스트 | 주 `#10141B`(크림) / `#FFFFFF`(다크) · 부 `#5C6572` · 흐림 `#8A93A0` · 다크 부 `#B3BAC4` | run colors |
| 강조 | 코랄 `#E0492E`(크림) / `#FF6A4D`(다크) — **한 장 한 군데 원칙** · 보조 앰버 `#F2A33C` · 틸 `#4FD1C5`(긍정) · 퍼플 `#8A5BD6`(드묾) | |
| 킥커 | 12.75pt, 자간 0.25em, 대문자 라틴+한글 `01 · BACKGROUND & TREND`, 강조색 | |
| 제목 | 49.5pt Bold, 최대 2줄, 핵심 구절만 강조색 | |
| 리드 | 18.75pt Regular, 부 텍스트색, 최대 2줄, 굵은 키워드 허용 | |
| 카드 라벨 | 10.5~11.25pt 자간 0.15em 강조색 | |
| 핵심 수치 | 49.5pt Bold + 단위 15.75pt | |
| 본문 | 13.5~14.25pt, 줄간 1.5 | |
| 출처 | 9.75~10.5pt 흐림색, 슬라이드 하단 좌 | |
| 페이지 | `n / N` 10.5pt 흐림색 우하단 | |
| 여백 | 좌우 108px, 상 80px(킥커), 카드 간격 24px, 카드 라운드 8px | |
| 사진 패널 | 우측 폭 6.5~8.3in 풀블리드, 다크 오버레이 55~70%(Pillow 전처리), 팀 이미지 또는 캡처만 | |

### 5-2. 장표 해부학 → 슬롯 매핑
Navigator=`kicker`, Governing Message=`title`, 세부 설명·증거=`lead`+레이아웃 슬롯, 뒷받침 이미지=`images[]`/`panel_image`, 출처=`source_line`, 페이지 번호=자동.

### 5-3. 레이아웃 22종 (KDB 주제 → 권장)
| 레이아웃 | 주제 | 주요 슬롯(상한) |
|---|---|---|
| `cover` | 1 표지 | kicker(30자) · brand(20) · headline 2줄(각 14자, 강조 구절) · subtitle 2줄(각 28자) · tags 3(8자) · panel_image · footer_stats 4{label 8, value 16} |
| `statement` | 전환점 | statement 2줄(각 16자) · sub(40자) |
| `trend_cards` | 2 문제 배경 | title·lead · cards 3{label 14, headline 22, big 8, unit 6, desc 70, source 40} · band{so_what 40, why_now 3×45} · key_gap(옵션 30) |
| `problem_cascade` | 2 문제 정의 | bars 2~4{label 12, value} · kpis 3{big 8, label 22, source 30} · quote{text 60, who 40} · panel_image(옵션) |
| `problem_grid` | 2 문제 정의(마찰) | stats 3{big, label, source} · points 4{num, title 14, sub 16, desc 60} · footnote 90 |
| `alt_table` | 2·7 대체재/경쟁 | table cols≤4 rows≤5(cell 18) · us_col · weakness_cells[] · premise_note 90 |
| `quadrant` | 7 경쟁 포지셔닝 | axes 4(12자) · bubbles≤6{name 12, sub 14, x,y ∈[0,1], size, is_us} · gaps 3{title 14, desc 60} |
| `solution_steps` | 3 해결방안 | steps 4{label 10, title 14, desc 32} · cards 3{num, title 2줄×10, desc 80, source 40} |
| `product_screens` | 3 제품 소개 | screens 3~4{image 또는 mock_lines≤4, label 14, title 12, desc 60} · footnote 90 |
| `tech_moat` | 3 기술·강점 | data_cards 3{big, label 22, desc 60} · pipeline 3{title 14, desc 60} · moat{title 40, desc 60} · safety 90 |
| `mvp_scope` | 3·9 범위·로드맵 | now 4{title 14, desc 30} · target_line 60 · not_now≤5(40) · roadmap 3{label 12, title 14, desc 40} |
| `traction_plan` | 4 성과 지표 | weeks 4{label 16, big 10, desc 70} · table rows≤5{지표 12, 목표 8, 측정 30} · side{title 14, body 90} · insight 80 |
| `kpi_chart` | 4 성과(실적 있을 때) | chart{type: column|bar|line, categories≤8, series≤2} · kpis 3 · note 80 — python-pptx 네이티브 차트 |
| `bm_pricing` | 5 수익 모델 | tiers 3{label 14, price 12, sub 30, bullets 3×22, note 60} · unit_econ 4{label 10, big 10, sub 20} · evidence_note 90 |
| `market_tam` | 6 시장 규모 | tam/sam/som{label 22, desc 40, big 8, unit 4, calc 30} · side_stats 3{label 14, big 14, sub 40, source 30} · sanity_note 100 |
| `gtm_funnel` | 8 진입 전략 | beachhead{title 2줄×14, why 60, exclude 60} · channels 3{title 20, desc 70} · funnel 5{label 10, big 8, unit 3, desc 30} · footnote 90 |
| `growth_phases` | 8·9 성장 전략 | phases 3{label 14, title 12, desc 80, kpi 40} · flywheel 4(12자) · expansion 90 |
| `milestone_gates` | 9·12 마일스톤·Ask | gates 4{label 12, title 10, bullets≤4×18, gate 30} · ask_band{amount 10, runway 12, use_of_funds 90} |
| `team_cards` | 10 팀 | members 3{role 22, title 14, desc 70, kpi 40} · advisors 3{title 16, desc 50} · principle{title 3줄×8, desc 80, list≤3×20} · footnote 90 |
| `vision_close` | 11 비전 | headline 3줄(각 10자) · body 3줄(각 40자) · one_liner 2줄(각 24자) · cards 3{label 8, big 12, sub 40} · tagline 24 · ask_line 24 · panel_image |
| `appendix_qa` | 부록 | qa≤4{q 50, a 120} |
| `evidence_capture` | 부록/본문 보조 | image · caption 60 · source 80 — Tier B 캡처 전용 |

- 스펙 검증(`validate deck_spec`)이 상한을 강제하고, 빌더는 초과 시 1단계(−1.5pt)만 자동 축소 후 경고. 그 이상은 디자이너가 문장을 줄인다(숫자 불변).
- 배경 교차: 표지·statement·비전 다크, 본문은 크림 기본, 문제 정의·수익 모델·마일스톤은 다크 허용(샘플과 동일 리듬).
- 차트는 `kpi_chart`와 `problem_cascade`(막대 도형)만. 값 없는 차트 금지.

---

## 6. 근거·이미지 수집 정책

### 6-1. 등급
| Tier | 무엇 | 사용 | 원장 표기 |
|---|---|---|---|
| A | 팀 제출 자료의 숫자·이미지 | 그대로 | `license: team` |
| B | 인용한 기사·논문·통계 페이지의 **해당 문단/figure 캡처**(`capture_evidence.py`: URL·CSS 선택자 또는 좌표 → PNG) + 숫자는 네이티브 차트로 재작성 | 출처줄에 `출처: 발행처, 제목, 기준 YYYY.MM, 수집 YYYY-MM-DD, URL` | `license: quote`(인용) |
| C | 웹 이미지(제품 사진·현장 사진·경쟁사 화면·인포그래픽 등) | **라이선스 확인 여부와 무관하게 수집·배치 허용**(사용자 결정 2026-09-11). 라이선스가 확인되면 기록, 미확인이면 `unknown` + `needs_human_review: true` | 피칭가이드에 "라이선스 확인 필요 이미지" 표(파일·슬라이드·URL·페이지) 제공 → 사람이 최종 정리 |

### 6-2. 조사 채널(WebSearch/WebFetch)
뉴스·기사 / 통계청 KOSIS·e-나라지표·정부 부처 보도자료 / 협회·시장조사 리포트 요약 페이지 / 논문: Semantic Scholar API, Google Scholar, KCI, DBpia(초록), PubMed / 특허: KIPRIS / 경쟁사·대체재 공식 사이트·앱스토어 페이지 / 학술 figure는 오픈액세스 논문 우선.

### 6-3. 주제별 evidence_targets (최소)
| 주제 | 최소 근거 | 외부 조사 허용 |
|---|---|---|
| 1 표지 | 제품·현장 이미지 1 | ✕(팀 자료, 없으면 Tier C 현장 이미지 1) |
| 2 문제 배경 | 통계 2 + 기사/리포트 1 | ● |
| 2 문제 정의 | 고객 인터뷰/설문 인용 1(팀) 또는 논문·조사 1 | ● |
| 2 대체재 | 대체재·경쟁 공식 페이지 캡처 2 | ● |
| 3 해결방안·제품 | 제품 이미지/화면 1(팀) + 기술 근거(논문·특허·공공데이터) 1 | ●(기술 근거만) |
| 4 성과 지표 | 팀 실적/MVP 반응/인터뷰 — **외부 대체 금지** | ✕ |
| 5 수익 모델 | 가격 근거 1(경쟁 가격 캡처 또는 지불의향 조사) | ● |
| 6 시장 규모 | 공식 수치 2 + 산식(SOM→SAM→TAM) | ● |
| 7 경쟁 차별점 | 경쟁사 3 공식 페이지 + 비교 항목 근거 | ● |
| 8 진입 전략 | 채널 실재 근거 1(커뮤니티·기관·전시) | ● |
| 9 마일스톤 | 팀 계획 + 유사 사례 벤치마크 1 | ●(벤치마크만) |
| 10 팀 | 팀 자료 — 외부는 공식 프로필·수상 확인만 | △ |
| 11 비전 | — | ✕ |
| 12 The Ask | 팀 자금 계획 + Seed 라운드 규모 벤치마크 1(옵션) | △ |

### 6-4. 인용 형식(슬라이드 출처줄)
`출처: {발행처} 「{제목}」 ({기준 YYYY.MM}) · 수집 {YYYY-MM-DD}` — 여러 개는 ` · `로 연결, URL은 피칭가이드 증거 원장에만.

---

## 7. 5분 피칭 규칙 (`pitch_5min.md`)
| 주제 | 초 | 비고 |
|---|---|---|
| 표지 | 15 | 한 줄 정의 읽기 |
| 문제 배경·정의 (1~2장) | 60 | 트렌드 → 문제 크기 → 대체재 한계 |
| 해결방안·제품 (1~2장) | 60 | 문제와 1:1 연결, 정량 benefit |
| 성과 지표 | 30 | 있는 것만 |
| 수익 모델 | 25 | 누가 얼마 왜 반복 |
| 시장 규모 | 25 | SOM 먼저 |
| 경쟁 차별점 | 25 | 약점 1행 포함 |
| 진입·성장 전략 | 20 | 첫 고객 확보 순서 |
| 마일스톤 + Ask | 25 | 12개월 자금·사용처·다음 증명 |
| 팀 | 15 | 왜 이 팀 |
| 비전 | 10 | 한 문장 |
| 합계 | 300 | 허용 ±30 |
- 대본 총량 1,500~1,700자(한국어 발화 300~340자/분). 장마다 발표자 노트에 `[초] 대본` 형식.
- Q&A 부록은 발표 시간에 포함하지 않으며 `appendix_qa`로 15개 질문·답(또는 `[확보 필요]`)을 2~4장.

---

## 8. QA 체크리스트 · 완료 기준 (`qa_checklist.md`)
**내용 8**: 장마다 투자자 질문 1개에 답하는 제목 / 모든 숫자에 기준시점·출처 / `[기입 필요]` 0 / 앞뒤 숫자 일치(`trace`) / 경쟁 장 약점 1행 / [추정][목표] 라벨 유지 / 한 장 한 메시지 / The Ask 4종(금액·밸류 또는 "미정" 명시·사용처·마일스톤).
**디자인 7**: 장수 = 스토리라인 / 숫자 대조 0건(`trace` 재실행) / 가장 큰 글자 = 핵심 수치 / 킥커·출처·페이지번호 누락 0 / 단어 중간 줄바꿈·넘침·겹침 0(PNG 육안) / 강조색 한 장 한 군데 / PDF 장수 일치·배경색 유지.
**피칭 4**: 합 300±30초 / 전 장 발표자 노트 / 부록 Q&A 15 / 피칭가이드에 확보 필요·라이선스 확인 필요 표.

---

## 9. 사용법 HTML (`docs/index.html`) 목차
1. 무엇이 나오나 (결과물 4종 + 샘플 슬라이드 이미지 3장)
2. 준비물 — 처음 한 번만 (Claude Code·Python·pip·Chrome·Pretendard·PowerPoint/LibreOffice, OS별)
3. 설치 — 두 줄
4. 자료 폴더 만드는 법 (참가신청서 hwp + 있으면 사진·발표자료·설문 결과)
5. 실행 — 한 문장 + 진행 중 두 번의 확인(스토리라인·잔여 critical) 설명
6. 결과 확인 — 이 3가지만 (덱 PNG · 피칭가이드의 확보 필요 · 라이선스 확인 필요)
7. 수정 요청은 대화로 (문장 예시 8 — 80주차 STEP 7 표 재사용)
8. 원리 — KDB 12 주제와 투자자의 질문 (표)
9. 자주 묻는 질문 (hwp 안 읽힘 → PDF로 저장 / Office 없음 / 폰트 / 시간·비용 / 개인정보)
10. 면책 — 최종 책임은 발표자, 모든 숫자 검증

디자인은 `.claude/refs/jeongseokbiz_design.md`(Pretendard + Rausch + 슬레이트) 준수.

---

## 10. 검증 계획
1. **단위**: 추출기(시냅스 hwp → 텍스트 7.5천자·이미지 7장 PNG), `trace`(양성/음성 케이스), `validate`(스키마 위반 케이스), `build`(spec.example.json 22 레이아웃 전부 1장씩 렌더 → PNG 육안).
2. **통합**: 시냅스 팀 전 과정 → `3교시…/_seed_ir_test/2026.09.11_시냅스_SeedIR/` (로컬 보관, 저장소 제외, .gitignore).
3. **픽스처**: 셀아이(가상) 사실 팩 + 가상 이미지 3장으로 `evals/evals.json` 2건(전 과정 완주 · `--from 5` 재개).
4. **배포 점검**: 새 세션에서 `/plugin marketplace add`(로컬 경로) → 설치 → `/seed-ir` 트리거 확인. GitHub push·Pages는 사용자 확인 후.

---

## 11. 리스크 · 대응
| 리스크 | 대응 |
|---|---|
| hwp 파싱 실패(암호화·비표준) | `extract`가 파일별 실패를 보고, SKILL이 "한글에서 PDF로 저장 후 다시" 안내. 나머지 파일로 계속 |
| Office·LibreOffice 없음 | PNG 검수·PDF 생략, PPTX만 산출 + 가이드 안내. 디자이너는 텍스트 QA(`qa --text-only`) |
| Pretendard 미설치 | 빌더가 경고, 폰트명은 Pretendard 유지(뷰어 대체) |
| WebSearch/WebFetch 제한·차단 사이트 | 근거 confidence low + [확보 필요]로 남김. 페이지 캡처 실패 시 텍스트 인용만 |
| 토큰·시간(1팀 40~60분) | 단계별 산출물 저장·`--resume`; 심사 6개·조사 N개는 병렬 |
| 디자인 단계 숫자 변형 | 완료 전 `trace` 재실행이 게이트 |
| 개인정보 | fact_pack contact만 보존, 학번·주민번호·계좌 등은 추출 텍스트에서 제거하지 않되 산출물(JSON 이후)에는 넣지 않음. 저장소에 실팀 자료 금지 |
| 라이선스 미확인 이미지 | 사용자 결정으로 배치 허용, 원장·가이드 표로 사람이 최종 정리 |
