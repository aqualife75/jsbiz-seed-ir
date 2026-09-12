# 디자인 시스템 — 정석Biz 표준 (ir-designer)

## 토큰 (scripts/design_system.py와 동일)
- 캔버스 20×11.25in(1920×1080) · 폰트 **Pretendard** 단일 · 배경 다크 `#10141B` / 크림 `#F5F2EB`
- 텍스트: 주 `#10141B`(크림)/`#FFFFFF`(다크) · 부 `#5C6572` · 흐림 `#8A93A0` · 다크 부 `#B3BAC4`
- 강조: 코랄 `#E0492E`(크림 위) / `#FF6A4D`(다크 위) — **한 장 한 군데** · 보조 앰버 `#F2A33C` · 틸 `#4FD1C5` · 퍼플 `#8A5BD6`(드묾)
- 카드: 크림 위 흰색+`#E6E2DA` 보더 / 다크 위 흰색 4%+보더 10% / 강조 카드 코랄→앰버 그라데이션
- 타이포: 킥커 12.75pt 자간 0.25em 강조색 / 제목 49.5pt Bold 2줄 / 리드 18.75pt / 핵심 수치 49.5pt+단위 15.75pt / 본문 13.5~14.25pt / 출처 10.5pt / 페이지 `n / N`

## 장표 해부학 → 슬롯
kicker(Navigator) → title(Governing Message, `**핵심 구절**`만 강조) → lead → 본문 슬롯 → source_line → 페이지(자동) → notes(대본)

## 레이아웃 22종 — 주제 매핑과 배경
| layout | 정석Biz 노하우 주제 | 배경 | 언제 |
|---|---|---|---|
| `cover` | 1 | dark | 항상 1장. 우측 패널 = 제품 이미지(Tier A) 또는 현장 이미지 |
| `statement` | 전환점 | dark | 문제→해결 전환, 투자 모멘텀. 최대 2장 |
| `trend_cards` | 2 배경 | cream | 트렌드 3개 + so what/why now |
| `problem_cascade` | 2 정의 | dark | 단계별 이탈 막대 + 인용 + KPI 3 |
| `problem_grid` | 2 정의(마찰) | cream | 4개 마찰 지점 |
| `alt_table` | 2 대체재 / 7 경쟁 | cream | 비교표(우리 열 강조, 약점 행 표시) |
| `quadrant` | 7 포지셔닝 | dark | 2×2 버블 + GAP 3 |
| `solution_steps` | 3 해결방안 | cream | 4단계 밴드 + 3 카드 |
| `product_screens` | 3 제품 | cream | 화면·사진 3~4 |
| `tech_moat` | 3 기술 강점 | dark | 데이터·파이프라인·해자 |
| `mvp_scope` | 3·9 범위 | cream | 지금/미루는 것/로드맵 |
| `traction_plan` | 4 성과(출시 전) | cream | 검증 설계·Go/Pivot 표 |
| `kpi_chart` | 4 성과(실적 있음) | cream | 네이티브 차트 + KPI 3 |
| `bm_pricing` | 5 수익 모델 | dark | 티어 3 + 유닛 이코노믹스 |
| `market_tam` | 6 시장 | cream | TAM→SAM→SOM 계단 + 시장 성장 3 + 기준 검증 |
| `gtm_funnel` | 8 진입 | cream | 교두보·채널·퍼널 5 |
| `growth_phases` | 8·9 성장 | cream | 3 phase + 플라이휠 + 확장 |
| `milestone_gates` | 9·12 | dark | 4 관문 + Ask 밴드 |
| `team_cards` | 10 | cream | 멤버 3 + 자문 3 + 채용 원칙 |
| `vision_close` | 11 (+12 한 줄) | dark | 비전 3줄 + 카드 3 + Ask 한 줄 |
| `appendix_qa` | 부록 | cream | 공격 질문 Q&A 4/장 |
| `evidence_capture` | 부록 | cream | Tier B 캡처 원문 |

배경 리듬: 표지·statement·비전 다크, 본문 크림 기본, 문제 정의·수익 모델·마일스톤·기술은 다크 허용(연속 다크 3장 이상 금지).

## 슬롯 글자수 상한
`assets/limits.json`이 원본. 상한을 넘기면 `harness.py validate deck_spec`이 막는다. **글자를 줄이지 말고 문장을 줄인다. 숫자는 바꾸지 않는다.**

## 디자이너 규칙 (정석Biz IR 전용 규칙 + 정석Biz 노하우 이미지 원칙)
1. 한 장 한 메시지. 제목 = slides_v2의 title 그대로(핵심 숫자 하나만 강조색)
2. 그 장에서 가장 큰 글자는 핵심 수치(카드 `big`), 단위는 작게
3. 킥커에 주제 번호·서브넘버링(`02 · PROBLEM 1`)
4. 모든 본문 장 하단 출처줄. `[추정]·[목표]·[확보 필요]` 라벨은 텍스트에 그대로 유지
5. 경쟁표의 우리 약점 행은 감추지 말고 `weakness: true`로 강조
6. 이미지는 장 내용과 직접 연결된 것만. 제목·캡션 없는 사진 금지. 솔루션 오인 유발 이미지 금지
7. 강조색 한 장 한 군데. 글자 색 3종 이내
8. 값 없는 차트 금지. 이미지가 없으면 `[이미지 확보 필요]` 자리표시(빌더 자동)
9. 렌더 PNG를 전장 눈으로 본다. 넘침·겹침·대비 부족은 spec 수정(문장 축약·카드 수 조정)으로 해결, 최대 3회
