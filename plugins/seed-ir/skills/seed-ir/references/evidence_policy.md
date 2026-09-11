# 근거·이미지 수집 정책 (ir-researcher)

## 등급
| Tier | 무엇 | 사용 | image_ledger.license |
|---|---|---|---|
| Tier A | 팀 제출 자료의 숫자·이미지 | 그대로 | `team` |
| Tier B | 인용한 기사·논문·통계 페이지의 해당 문단/figure **캡처**(`scripts/capture_evidence.py`) + 숫자는 네이티브 차트로 재작성 | 출처줄 필수 | `quote` |
| Tier C | 웹 이미지(제품·현장·경쟁사 화면·인포그래픽) | **라이선스 확인 여부와 무관하게 수집·배치 허용**(사용자 결정 2026-09-11). 확인되면 `cc/public/official`, 아니면 `unknown` + `needs_human_review: true`. 피칭가이드 "라이선스 확인 필요" 표로 사람이 최종 정리 | `cc`·`public`·`official`·`unknown` |

## 조사 채널
뉴스·기사 / 통계청 KOSIS·e-나라지표·부처 보도자료 / 협회·시장조사 리포트 요약 페이지 / 논문: Semantic Scholar API(`https://api.semanticscholar.org/graph/v1/paper/search?query=...&fields=title,year,venue,abstract,url,openAccessPdf`), Google Scholar, KCI, DBpia(초록), PubMed / 특허: KIPRIS / 경쟁사·대체재 공식 사이트·앱스토어 / 오픈액세스 논문 figure 우선.

## 주제별 evidence_targets (최소)
| topic_id | 최소 근거 | 외부 조사 |
|---|---|---|
| 1 | 제품·현장 이미지 1 | ✕ (팀 자료, 없으면 Tier C 현장 이미지 1) |
| 2 | 통계 2 + 기사/리포트 1 + 인터뷰 인용 1(팀) 또는 논문 1 + 대체재 캡처 2 | ● |
| 3 | 제품 이미지/화면 1(팀) + 기술 근거(논문·특허·공공데이터) 1 | ● 기술 근거만 |
| 4 | 팀 실적·MVP 반응·인터뷰 — **외부 대체 금지** | ✕ |
| 5 | 가격 근거 1(경쟁 가격 캡처 또는 지불의향 조사) | ● |
| 6 | 공식 수치 2 + 산식(SOM→SAM→TAM) | ● |
| 7 | 경쟁사 3 공식 페이지 + 비교 항목 근거 | ● |
| 8 | 채널 실재 근거 1(커뮤니티·기관·전시) | ● |
| 9 | 팀 계획 + 유사 사례 벤치마크 1 | ● 벤치마크만 |
| 10 | 팀 자료. 외부는 공식 프로필·수상 확인만 | △ |
| 11 | — | ✕ |
| 12 | 팀 자금 계획 + Seed 규모 벤치마크 1(옵션) | △ |

## 원장 필드
- `evidence.json.records[]`: id(E01…), topic_id, slide_no, claim, value, unit, asof(기준 YYYY.MM), source_title, publisher, url, retrieved(YYYY-MM-DD), tier, capture_file, quote(원문 1~2문장), confidence(high/mid/low)
- `image_ledger.json.images[]`: file, url, page_url, title, author, license, license_note, retrieved, used_in_slides[], needs_human_review

## 인용 형식(슬라이드 출처줄)
`출처: {발행처} 「{제목}」 ({기준 YYYY.MM}) · 수집 {YYYY-MM-DD}` — 여러 개는 ` · `로 연결. URL은 원장에만.

## 금지
- 팀 내부 사실을 외부 자료로 대체(트랙션·팀·가격 결정·사용처).
- 출처를 특정할 수 없는 숫자(블로그 재인용 등)는 confidence low로 두고 원출처를 찾는다. 못 찾으면 쓰지 않고 `[확보 필요]`.
- 가짜 로고·가짜 고객 리뷰·가짜 수치 생성.
