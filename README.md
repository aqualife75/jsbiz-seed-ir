# seed-ir — 자료 폴더 하나로 Seed IR Deck 만들기

## Codex 교육생용 v1.5.1

현재 교육생용 배포본은 **Codex에서 여는 `정석biz-IR-프로젝트` 작업 폴더**입니다.

1. [교육생 ZIP 다운로드](https://github.com/aqualife75/jsbiz-seed-ir/releases/download/codex-v1.5.1/seed-ir-codex-learner.zip)를 받아 압축을 풉니다.
2. Codex에서 `정석biz-IR-프로젝트`를 열고 `자료넣는곳`에 한 팀의 자료를 넣습니다.
3. **“우리 팀 IR Deck 만들어줘”**라고 요청합니다. 장표별 이미지 조사와 필요한 시각물의 직접 제작을 기본으로 수행합니다.

[전체 사용법](https://accelerating.co.kr/resources/seed-ir-deck) · [변경사항](https://github.com/aqualife75/jsbiz-seed-ir/releases/tag/codex-v1.5.1) · [제작 과정과 회고](codex/docs/visual-retrospective.md) · [유지보수하는 Codex 원본](codex/)

v1.5.1은 **각 슬라이드의 주장과 증거를 뒷받침하는 이미지를 조사해 실제로 넣는 작업**을 기본 지침에 명시합니다. 적합한 이미지나 사용권이 없으면 제품 컷·MVP 화면·설명 이미지 또는 편집 가능한 차트·도식을 전문가 수준으로 직접 기획·제작합니다. 제품 외형·화면·구도·조명과 발표 크기의 가독성까지 설계하며 양 덱의 전체 실제 PPTX 화면을 직접 검수합니다. 생성 이미지는 설계·설명용으로 표시하며 고객 반응이나 제품 구현의 증거로 사용하지 않습니다. 상세본과 5분 발표본 모두 14목차·최소 18장이고, 이번 교육 범위에서는 투자 요청·조달 금액·자금 사용 계획을 제외합니다. 사업 근거가 부족하면 검수한 **초안**으로 전달합니다.

> 우리 팀 IR Deck 만들어줘. 각 슬라이드의 주장과 증거 자료를 뒷받침하는 이미지를 찾아 넣고, 적합한 이미지나 사용권이 없으면 제품 컷·MVP 화면·설명 이미지 또는 편집 가능한 차트·도식을 전문가 수준으로 직접 기획·제작해줘. 생성물은 설명용으로 표시하고 상세본과 발표본의 전체 실제 PPTX 화면을 검수해줘.

Codex 소스와 허용 목록 기반 배포 도구는 `codex/`에 있습니다. [개발·검증 안내](codex/docs/architecture.md)를 참고하세요. 아래는 별도로 유지하는 **Claude Code 플러그인** 안내이며 목차·실행 환경이 다릅니다.

## 실제 제작 결과 예시 · 2026.09.30

**[글루코픽 전체 슬라이드 40장 보기](https://aqualife75.github.io/jsbiz-seed-ir/examples/glucopic-20260930/index.html)** · [홈페이지에서 보기](https://accelerating.co.kr/resources/seed-ir-deck/examples/glucopic-20260930/index.html) · [전체 파일 다운로드](https://github.com/aqualife75/jsbiz-seed-ir/releases/tag/example-glucopic-20260930)

상세본 22장과 5분 발표본 18장의 실제 PPTX 렌더 PNG를 원본 그대로 제공합니다. PPTX·이미지 기반 PDF·원본 PNG·대본·예상 질문을 받을 수 있습니다. **계획·가정·미확인 표시를 유지한 보완 초안**이며 실제 제품 구현이나 고객 성과 검증을 뜻하지 않습니다. 기존 38장 교육 예시 및 v1.5.0 실행 도구 ZIP과 별도입니다.

## Claude Code 플러그인

창업팀 자료 폴더(참가신청서·사업계획서·사진)를 넣고 한 문장만 말하면, 6개 AI 에이전트가 정석Biz 노하우 「IR Deck 작성」 12주제 × 투자자의 질문 기준으로 **Seed IR Deck(PPTX + PDF + 5분 피칭가이드)** 초안을 만들어 주는 Claude Code 플러그인입니다. 자료에 없는 숫자는 만들지 않고 `[확보 필요]`로 남깁니다.

👉 **[교육생용 사용법 가이드 보기](https://aqualife75.github.io/jsbiz-seed-ir/)**

## 무엇이 나오나요

| 산출물 | 설명 |
|---|---|
| `{팀명}_Seed_IR_Deck.pptx` | 본문 12~14장 + 예상 질문 부록. 파워포인트에서 바로 수정 가능 |
| `{팀명}_Seed_IR_Deck.pdf` | 배포·제출용. PowerPoint 또는 LibreOffice가 있으면 자동 생성 |
| `피칭가이드.md` | 5분 대본(장별 초 배분) · 예상 Q&A · **제출 전 확보 필요 목록** · 라이선스 확인 필요 이미지 |
| `qa_png/` | 장표 검수용 PNG. 글자 넘침·여백을 눈으로 바로 확인 |

## 설치

```
/plugin marketplace add aqualife75/jsbiz-seed-ir
/plugin install seed-ir@jsbiz-seed-ir
```

설치 후 Claude Code를 새 세션으로 다시 시작하세요. `/seed-ir`가 자동완성되면 성공입니다.

## 실행

```
/seed-ir "C:\Users\나\Desktop\우리팀_자료"
```

"이 폴더 자료로 Seed IR덱 만들어줘"처럼 말로 부탁해도 됩니다.
주요 옵션: `--team 팀명` · `--out 출력폴더` · `--accent #1B3A5C` · `--resume` · `--from N` · `--yes`

## 최소 요구사항

| 항목 | 필수 | 용도 |
|---|---|---|
| Claude Code (Windows·Mac) | ● | 실행 |
| Python 3.10+ | ● | 추출·빌드·검증 |
| `pip install python-pptx pymupdf pillow olefile python-docx openpyxl jsonschema` | ● | 의존 패키지 |
| Chrome 또는 Edge | ● | 근거 캡처(헤드리스) |
| Pretendard 폰트 | ● | 렌더 정확도(미설치 시 시스템 고딕 대체, 경고) |
| PowerPoint 또는 LibreOffice | ○ | PDF·PNG 렌더. 없으면 PPTX만 산출 |
| Node / npm | ✕ | 불필요 |

## 6단계 요약

| 단계 | 에이전트 | 하는 일 | 산출 |
|---|---|---|---|
| 1. 자료 판독 | `ir-intake` | hwp·pdf·이미지 추출 → 사실 팩 10항목·이미지 카탈로그 | `02_fact_pack.json` |
| 2. 본문 작성 | `ir-writer` | 스토리라인(12~14장) · 거버닝 메시지 · 본문 | `04_slides_v1.json` |
| 3. 검산·모의심사 | `ir-panel` | 숫자 검산 + VC·AC·도메인·재무·비전문가 5인 채점 | `05_review/` |
| 4. 근거 조사 | `ir-researcher` | 약한 주제만 통계·기사·논문 조사 후 캡처·개정 | `06_evidence/`, `07_slides_v2.json` |
| 5. 디자인 | `ir-designer` | 레이아웃 매핑 · PPTX 빌드 · PNG 검수 | `09_build/` |
| 6. 피칭 대본 | `ir-finalizer` | 5분 대본 · Q&A 부록 · 확보 필요 목록 | `10_final/` |

소요 40~60분. 진행 중 두 번 확인합니다 — ① 스토리라인 표 ② 남은 critical 승인.

## 꼭 알아두세요

- **최종 책임은 발표자에게 있습니다.** 이 플러그인은 초안을 만듭니다.
- **모든 숫자와 출처는 직접 검증하세요.** `trace`가 숫자의 근거를 추적하지만 출처의 최신성·해석까지 보장하지는 않습니다.
- **라이선스 미확인 이미지는 제출 전에 정리하세요.** 피칭가이드의 표에 상태가 정리됩니다.
- **개인정보·팀 자료는 로컬에만 저장됩니다.** 저장소나 외부 서버로 업로드하지 않습니다.
- **교육용 예시 팀 「셀아이」는 가상입니다.** 실제 회사가 아니며 모든 수치는 예시입니다.

## 개발자용

```bash
pip install -r requirements.txt
PYTHONUTF8=1 python -m pytest tests -q

# 예시 덱 빌드
PYTHONUTF8=1 python plugins/seed-ir/skills/seed-ir/scripts/build_deck.py \
  plugins/seed-ir/skills/seed-ir/assets/spec.example.json --out tests/_out/example.pptx

# 로컬 .claude 설치본 동기화
python scripts/install_local.py --target "<.claude 폴더>"
```

## 라이선스

MIT — [LICENSE](LICENSE) 참조.

만든이: 정석Biz · 이동건 · 유튜브 [@정석Biz](https://www.youtube.com/@정석Biz) · [GitHub](https://github.com/aqualife75/jsbiz-seed-ir)
