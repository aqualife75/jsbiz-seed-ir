# Part D — 배포·검증 구현 계획 (Task 18~21)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. 공통 제약은 `2026-09-11-seed-ir-00-index.md`의 Global Constraints를 따른다. Part A·B·C가 완료되어 있어야 한다.

**Goal:** 교육생 사용법 HTML·README, 가상 팀 픽스처와 evals, 로컬 설치·플러그인 트리거 확인, 시냅스 팀 통합 실행으로 하네스를 검증하고, 사용자 확인 후 GitHub에 배포한다.

**Architecture:** `docs/index.html`은 정석Biz DESIGN.md(Pretendard·Rausch `#FF385C`·슬레이트) 단일 파일. 픽스처는 `실습기초자료_셀아이_Pack.md`를 재사용한 가상 팀. 통합 실행 산출물은 저장소 밖(`_seed_ir_test/`, gitignore).

경로 약어: `S` = `plugins/seed-ir/skills/seed-ir`, `SC` = `S/scripts`, `T` = `tests`, `DB` = `D:/BRIAN Dropbox/Lee Dong-Geon`.

---

### Task 18: 사용법 HTML `docs/index.html` + `README.md`

**Files:**
- Create: `docs/index.html`, `README.md`, `T/test_docs.py`

**Interfaces:**
- `docs/index.html` 목차(설계서 §9) 10개 섹션, 각 `<h2 id="...">`. 설치 명령 두 줄과 실행 예시는 `<pre><code>` + 복사 버튼(인라인 JS `navigator.clipboard.writeText`). 외부 리소스는 Pretendard CDN 하나만(`https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css`).
- README는 index.html의 요약 + 설치 두 줄 + 요구사항 + 면책. 링크: `https://aqualife75.github.io/jsbiz-seed-ir/`, 유튜브 `@정석Biz`.

- [ ] **Step 1: 실패하는 테스트 작성** — `T/test_docs.py`

```python
# -*- coding: utf-8 -*-
import re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def test_index_html_sections_and_install():
    t = (ROOT / "docs/index.html").read_text(encoding="utf-8")
    for sid in ["outputs", "prereq", "install", "folder", "run", "check", "revise", "principle", "faq", "disclaimer"]:
        assert f'id="{sid}"' in t, sid
    assert "/plugin marketplace add aqualife75/jsbiz-seed-ir" in t and "/plugin install seed-ir@jsbiz-seed-ir" in t
    assert "Pretendard" in t and "#FF385C" in t.upper() or "#ff385c" in t
    assert "<script src=" not in t  # 외부 JS 없음(인라인만)

def test_readme_links():
    t = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "aqualife75.github.io/jsbiz-seed-ir" in t and "@정석Biz" in t and "seed-ir@jsbiz-seed-ir" in t
```

- [ ] **Step 2: 실행해 실패 확인** — Run: `PYTHONUTF8=1 python -m pytest tests/test_docs.py -q` → FAIL

- [ ] **Step 3: 작성**

`docs/index.html` 골격(스타일 토큰은 DESIGN.md: 배경 `#F8FAFC`, 텍스트 `#1E293B`, 보조 `#94A3B8`, 카드 `#FFFFFF`, 보더 `#E2E8F0`, 강조 `#FF385C`, 8px 그리드, H1 28/700, H2 21/700 좌측 4px 강조 보더, 본문 15/1.7):
```html
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>seed-ir — 자료 폴더 하나로 Seed IR Deck 만들기 (정석Biz)</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css">
<style>
:root{--brand:#FF385C;--brand-soft:#FFE4EA;--text:#1E293B;--muted:#94A3B8;--heading:#374151;--bg:#F8FAFC;--surface:#fff;--surface-alt:#F1F5F9;--border:#E2E8F0;--code-bg:#1E293B;--success:#059669;--warning:#D97706;--danger:#DC2626}
*{box-sizing:border-box}body{margin:0;font-family:'Pretendard','Apple SD Gothic Neo','Malgun Gothic',sans-serif;font-size:15px;line-height:1.7;color:var(--text);background:var(--bg)}
header{background:var(--surface);border-bottom:1px solid var(--border);padding:32px 24px}
.wrap{max-width:960px;margin:0 auto;padding:0 24px}
h1{font-size:28px;font-weight:700;color:var(--brand);letter-spacing:-.02em;margin:0 0 8px}
h2{font-size:21px;font-weight:700;margin:48px 0 16px;padding-left:12px;border-left:4px solid var(--brand);letter-spacing:-.02em}
h3{font-size:17px;font-weight:600;color:var(--heading);margin:24px 0 8px}
.lead{color:var(--heading);font-size:17px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:24px;margin:16px 0}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px}
pre{position:relative;background:var(--code-bg);color:#E2E8F0;padding:16px 56px 16px 16px;border-radius:8px;overflow:auto;font-size:14px}
pre button{position:absolute;top:8px;right:8px;border:0;background:var(--brand);color:#fff;border-radius:6px;padding:4px 10px;font-size:12px;cursor:pointer}
table{width:100%;border-collapse:collapse;font-size:14px}th,td{border-bottom:1px solid var(--border);padding:8px 12px;text-align:left;vertical-align:top}th{background:var(--surface-alt)}
.badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;font-weight:600;background:var(--brand-soft);color:var(--brand)}
.note{background:var(--brand-soft);border-radius:8px;padding:12px 16px}
nav a{color:var(--heading);margin-right:16px;text-decoration:none;font-size:14px}
footer{color:var(--muted);font-size:13px;padding:48px 24px;text-align:center}
img{max-width:100%;border-radius:8px;border:1px solid var(--border)}
</style>
</head>
<body>
<header><div class="wrap"><span class="badge">정석Biz · Claude Code 플러그인</span>
<h1>seed-ir — 자료 폴더 하나로 Seed IR Deck 만들기</h1>
<p class="lead">참가신청서·사업계획서·사진을 폴더에 넣고 한 문장만 말하면, 6개 AI 에이전트가 정석Biz 노하우 「IR Deck 작성」 12주제 기준으로 <b>거버닝 메시지 → 5인 모의심사 → 근거 조사 → 디자인 → 5분 피칭 대본</b>까지 만들어 줍니다. 자료에 없는 숫자는 만들지 않고 <b>[확보 필요]</b>로 남깁니다.</p>
<nav>…10개 섹션 앵커…</nav></div></header>
<main class="wrap">
<section id="outputs"><h2>1. 무엇이 나오나요?</h2> … 결과물 4종 카드(PPTX·PDF·피칭가이드.md·검수 PNG) + 예시 슬라이드 이미지 3장(`docs/img/example_01.png` 등 — Task 19에서 셀아이 예시 덱 PNG 3장 복사) </section>
<section id="prereq"><h2>2. 준비물 — 처음 한 번만</h2> 표: Claude Code / Python 3.10+ + pip 한 줄 / Chrome 또는 Edge / Pretendard 폰트(다운로드 링크 https://github.com/orioncactus/pretendard) / PowerPoint 또는 LibreOffice(선택). Windows·Mac 각각의 설치 명령 `<pre>` </section>
<section id="install"><h2>3. 설치 — 두 줄이면 끝</h2>
<pre><button onclick="copy(this)">복사</button><code>/plugin marketplace add aqualife75/jsbiz-seed-ir
/plugin install seed-ir@jsbiz-seed-ir</code></pre> 새 세션에서 `/seed-ir`가 자동완성되면 성공 </section>
<section id="folder"><h2>4. 자료 폴더 만드는 법</h2> 폴더 하나에 참가신청서(hwp/hwpx/pdf)·사업계획서·발표자료·제품 사진·인터뷰 정리·설문 결과. 파일명에 팀명. 없는 자료는 없는 대로(하네스가 부족 목록을 만든다) </section>
<section id="run"><h2>5. 실행 — 한 문장</h2>
<pre><button onclick="copy(this)">복사</button><code>/seed-ir "C:\Users\나\Desktop\우리팀_자료"</code></pre>
진행 중 두 번 물어봅니다: ① 스토리라인 표(12~14장) 확인 ② 조사로도 못 채운 critical이 남으면 "계속/중단". 소요 40~60분, 6단계 진행 표 </section>
<section id="check"><h2>6. 결과 확인 — 이 3가지만</h2> ① `10_final/qa_png/` 슬라이드 그림 ② `피칭가이드.md`의 "제출 전 확보 필요 목록" ③ 같은 파일의 "라이선스 확인 필요 이미지" 표 — 사람이 최종 판단 </section>
<section id="revise"><h2>7. 수정 요청은 대화로</h2> 문장 예시 8(80주차 STEP 7 표 재사용: 숫자가 안 보인다/강조색이 많다/표가 출처와 겹친다/제목이 길다/카드가 넘친다/여백/줄바꿈/숫자 대조표) + "확보 목록 채운 뒤 `/seed-ir <폴더> --from 4`" </section>
<section id="principle"><h2>8. 원리 — 정석Biz 노하우 12 주제와 투자자의 질문</h2> 12행 표(주제 | 투자자의 질문) + 슬라이드 해부학 4요소 + "없는 숫자는 만들지 않는다 → trace" 설명 </section>
<section id="faq"><h2>9. 자주 묻는 질문</h2> hwp가 안 읽힘(한글에서 PDF 저장) / Office 없음(PPTX만, PDF는 PowerPoint·Keynote) / 폰트 깨짐(Pretendard 설치) / 비용·시간 / 개인정보(로컬 저장만, 외부 전송 없음) / 영문 덱은(jsbiz-global-ir) </section>
<section id="disclaimer"><h2>10. 꼭 알아두세요</h2> 최종 책임은 발표자 · 모든 숫자·출처 직접 검증 · 라이선스 미확인 이미지는 제출 전 정리 · 교육용 예시(셀아이)는 가상 </section>
</main>
<footer>정석Biz · 이동건 · <a href="https://www.youtube.com/@정석Biz">유튜브 @정석Biz</a> · <a href="https://github.com/aqualife75/jsbiz-seed-ir">GitHub</a></footer>
<script>function copy(b){navigator.clipboard.writeText(b.parentElement.querySelector('code').innerText).then(()=>{b.textContent='복사됨';setTimeout(()=>b.textContent='복사',1200)})}</script>
</body></html>
```
각 `…` 자리는 위 설명대로 실제 문장·표·카드로 채운다(placeholder를 남기지 않는다).

`README.md` 구성: 제목 · 한 줄 소개 · 무엇이 나오나(4종) · 👉 사용법 가이드 링크 · 설치 두 줄 · 실행 예시 · 최소 요구사항 표 · 6단계 요약 표 · 꼭 알아두세요(숫자 검증·라이선스·개인정보) · 개발자용(테스트 `pytest tests -q`, 예시 덱 빌드 명령) · 라이선스 MIT.

- [ ] **Step 4: 테스트 통과** — Run: `PYTHONUTF8=1 python -m pytest tests/test_docs.py -q` → `2 passed`
- [ ] **Step 5: 브라우저 확인** — `mcp__Claude_Browser__preview_start {url: "file:///<repo>/docs/index.html"}` 후 스크린샷으로 모바일(375px)·데스크톱 레이아웃 확인, 복사 버튼 동작 확인.
- [ ] **Step 6: 커밋**

```bash
git add -A && git -c user.name="Lee Dong-Geon" -c user.email="leedg.brian@gmail.com" commit -m "docs: 교육생 사용법 HTML + README

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 19: 픽스처(셀아이)·evals·예시 이미지·로컬 설치·플러그인 트리거 확인

**Files:**
- Create: `evals/fixtures/셀아이/셀아이_사실팩.md`, `evals/fixtures/셀아이/이미지/{product_module.png, line_photo.png, defect_chart.png}`, `evals/evals.json`, `docs/img/example_{01,02,03}.png`, `scripts/install_local.py`(저장소 루트)
- Modify: `DB/.claude/skills/seed-ir/`(복사본), `DB/.claude/agents/ir-*.md`(복사본), `DB/CLAUDE.md`(자동화 스크립트 절에 1줄 추가)

**Interfaces:**
- `scripts/install_local.py` : 저장소의 `plugins/seed-ir/skills/seed-ir` → `<대상 .claude>/skills/seed-ir`, `plugins/seed-ir/agents/*.md` → `<대상 .claude>/agents/` 복사(기존 덮어쓰기). 인자 `--target "<.claude 폴더>"`. jsbiz-global-ir와 같은 수동 동기화 규칙.
- `evals/evals.json`: 2건 — `full_run`(셀아이 폴더로 `/seed-ir` 완주, 기대: 10_final 4종·trace OK·BLOCKING 0), `resume_from_5`(`--from 5`로 디자인만 재실행, 기대: 09_build 갱신·numbers 불변).

- [ ] **Step 1: 픽스처 작성**
  - `셀아이_사실팩.md`: `DB/00. A_창업 교육/00. 2026년도_창업/2026.09.15_포스텍_IR Deck 강의/3교시_AI로 만드는 Seed IR Deck 초안/실습자료/실습기초자료_셀아이_Pack.md`를 복사하고 첫 줄에 `> 교육용 가상 팀 — 실제 회사 아님. 모든 수치는 예시.` 추가.
  - 이미지 3장은 PIL로 생성(글자 없는 도형: 남색 사각 모듈·회색 라인 사진 느낌 그라데이션·막대 3개 차트), 각 1200×800.
  ```python
  from PIL import Image, ImageDraw
  im = Image.new("RGB", (1200, 800), (16, 20, 27)); d = ImageDraw.Draw(im); d.rounded_rectangle((200, 150, 1000, 650), 40, fill=(27, 58, 92)); d.rectangle((300, 250, 900, 550), fill=(224, 73, 46)); im.save("product_module.png")
  ```
  (line_photo·defect_chart도 같은 방식으로 도형만.)
- [ ] **Step 2: `evals/evals.json`**
```json
{"skill": "seed-ir", "cases": [
  {"id": "full_run", "input": "evals/fixtures/셀아이", "command": "/seed-ir \"evals/fixtures/셀아이\" --yes --out tests/_out/evals",
   "expect": ["10_final/*_Seed_IR_Deck.pptx", "10_final/피칭가이드.md", "05_review/trace_report.json:untraced==[]", "09_build/qa_report.md:BLOCKING: 0", "slides 12~14 + appendix"]},
  {"id": "resume_from_5", "input": "tests/_out/evals/*_셀아이_SeedIR", "command": "/seed-ir \"evals/fixtures/셀아이\" --resume --from 5 --yes",
   "expect": ["09_build rebuilt", "07_slides_v2.json unchanged (sha256 same)", "trace OK"]}
]}
```
- [ ] **Step 3: 예시 이미지** — `python SC/build_deck.py S/assets/spec.example.json --out tests/_out/example.pptx` → `harness`가 아닌 `render_qa.render(..., slides=[1,3,15])` → 3장을 `docs/img/example_01~03.png`로 복사(1920×1080 → 1280×720 리사이즈).
- [ ] **Step 4: `scripts/install_local.py`**
```python
# -*- coding: utf-8 -*-
"""저장소 → 로컬 .claude 설치본 동기화. python scripts/install_local.py --target "D:/BRIAN Dropbox/Lee Dong-Geon/.claude" """
import argparse, shutil
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--target", required=True); a = ap.parse_args()
    tgt = Path(a.target)
    skill_src = ROOT / "plugins/seed-ir/skills/seed-ir"; skill_dst = tgt / "skills/seed-ir"
    if skill_dst.exists(): shutil.rmtree(skill_dst)
    shutil.copytree(skill_src, skill_dst, ignore=shutil.ignore_patterns("__pycache__"))
    (tgt / "agents").mkdir(exist_ok=True)
    for f in (ROOT / "plugins/seed-ir/agents").glob("*.md"): shutil.copy(f, tgt / "agents" / f.name)
    print(f"installed → {skill_dst} + agents/ir-*.md")
if __name__ == "__main__": main()
```
- [ ] **Step 5: 로컬 설치 + CLAUDE.md 1줄** — `python scripts/install_local.py --target "DB/.claude"` 실행. `DB/CLAUDE.md` '자동화 스크립트' 절 끝에 추가:
  `- **Seed IR Deck 하네스(`seed-ir`)** — 창업팀 자료 폴더 → 정석Biz 노하우 12주제 기준 Seed IR Deck(PPTX+PDF+피칭가이드) 6 에이전트 자동 작성. 개발 원본 `00. A_B_정석Biz/99. 프로젝트/2026.09.11_seed-ir-deck_하네스/jsbiz-seed-ir/`(git, GitHub aqualife75/jsbiz-seed-ir), 설치본 `.claude/skills/seed-ir` + `.claude/agents/ir-*.md`(저장소 수정 시 `python scripts/install_local.py --target .claude`로 재복사). 사용: `/seed-ir "<자료폴더>"`.`
- [ ] **Step 6: 플러그인 트리거 확인** — 저장소 루트에서 새 세션: `/plugin marketplace add <저장소 절대경로>` → `/plugin install seed-ir@jsbiz-seed-ir` → `/seed-ir` 자동완성과 에이전트 목록에 `seed-ir:ir-intake` 등 6개가 보이는지 확인. 확인 결과를 `docs/superpowers/plans/…D….md` 하단 '실행 기록'에 적는다.
- [ ] **Step 7: 커밋**

```bash
git add -A && git -c user.name="Lee Dong-Geon" -c user.email="leedg.brian@gmail.com" commit -m "chore: 셀아이 픽스처·evals·예시 이미지·로컬 설치 스크립트

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 20: 통합 실행 — 시냅스 팀 전 과정 (검증)

**Files:**
- 입력: `DB/00. A_창업 교육/00. 2026년도_창업/2026.09.15_포스텍_IR Deck 강의/2026년 제16회 포스텍 창업경진대회_참가신청서_18부 이노폴리스 포항/2026년 제16회 포스텍 창업경진대회_참가신청서_시냅스_김준형.hwp` 1개를 `DB/…/3교시_AI로 만드는 Seed IR Deck 초안/_seed_ir_test/시냅스_입력/`로 복사
- 출력: `DB/…/3교시_AI로 만드는 Seed IR Deck 초안/_seed_ir_test/2026.09.11_시냅스_SeedIR/` (저장소 밖, 개인정보 포함, 커밋 금지)
- 기록: `docs/superpowers/plans/2026-09-11-seed-ir-D-distribution-validation.md` 하단 '실행 기록' 절(숫자·소요·발견 결함·수정 커밋 해시)

**Interfaces:** Consumes 전체. 발견된 결함은 해당 파트의 코드/문서를 고치고 **회귀 테스트를 추가**한 뒤 커밋한다.

- [ ] **Step 1: 실행** — 로컬 설치본으로 새 세션에서
```
/seed-ir "D:\BRIAN Dropbox\Lee Dong-Geon\00. A_창업 교육\00. 2026년도_창업\2026.09.15_포스텍_IR Deck 강의\3교시_AI로 만드는 Seed IR Deck 초안\_seed_ir_test\시냅스_입력" --out "D:\BRIAN Dropbox\Lee Dong-Geon\00. A_창업 교육\00. 2026년도_창업\2026.09.15_포스텍_IR Deck 강의\3교시_AI로 만드는 Seed IR Deck 초안\_seed_ir_test"
```
  체크포인트 1(스토리라인)·2(critical)는 사용자(이동건)에게 그대로 보여주고 결정을 받는다.
- [ ] **Step 2: 검증 항목** (모두 기록)
  - 추출: 텍스트 7,000자 이상, 이미지 6~7장, contact에 학번 없음
  - 사실 팩: items 10, 슬롯 12, gaps에 '시장 규모 출처'·'경쟁사 가격'류 포함
  - 스토리라인 12~14장, 12 주제 전부 배정
  - 심사: 5인 점수 범위 20~60(극초기 정상), finance 최저, X 주제 목록
  - 조사: records ≥ 10, Tier B 캡처 ≥ 3, 이미지 원장에 team 7 + web n, `needs_human_review` 표기
  - trace OK, `[기입 필요]` 0, `[확보 필요]` 목록 존재
  - 덱: 본문 12~14 + 부록 3~6장, BLOCKING 0, PNG 전장 육안(넘침·겹침 0), Pretendard, 다크/크림 리듬
  - 피칭가이드 8절 모두 존재, 총 초 300±30, 대본 1,500~1,700자
  - 소요 시간·대략 토큰
- [ ] **Step 3: 결함 수정** — 발견마다: 원인 파트 코드 수정 → 회귀 테스트 → `pytest tests -q` → 커밋(`fix(...)`) → 해당 단계부터 `--from N` 재실행.
- [ ] **Step 4: 사용자 검수** — 10_final PNG 5장(표지·문제·시장·마일스톤·비전)과 피칭가이드 확보 목록을 SendUserFile로 전달해 이동건의 의견을 받고 반영.
- [ ] **Step 5: 기록·커밋** — 실행 기록을 이 파일 하단에 추가하고 커밋(`docs: 시냅스 통합 실행 기록`). 실팀 산출물은 커밋하지 않는다(`.gitignore` 확인: `git status`에 `_seed_ir_test` 없음).

---

### Task 21: GitHub 배포 (사용자 확인 후)

**Files:** 저장소 전체. 원격 `https://github.com/aqualife75/jsbiz-seed-ir`.

- [ ] **Step 1: 사전 점검** — `git status` 클린, `pytest tests -q` 통과, `git log --oneline | wc -l` ≥ 20, 저장소에 실팀 파일·개인정보·시크릿 없음(`grep -rn "010-" --include=*.json --include=*.md . | grep -v evals` 결과 0).
- [ ] **Step 2: 사용자 확인** — "aqualife75/jsbiz-seed-ir 공개 저장소를 만들고 push + GitHub Pages(main:/docs) 활성화합니다. 진행할까요?" — **명시적 승인 후에만** 다음 단계.
- [ ] **Step 3: 생성·push**
```bash
gh repo create aqualife75/jsbiz-seed-ir --public --source . --remote origin --description "정석Biz Seed IR Deck 멀티 에이전트 하네스 — Claude Code 플러그인" --push
gh api -X POST repos/aqualife75/jsbiz-seed-ir/pages -f "source[branch]=main" -f "source[path]=/docs"
```
- [ ] **Step 4: 설치 리허설** — 새 세션에서 `/plugin marketplace add aqualife75/jsbiz-seed-ir` → `/plugin install seed-ir@jsbiz-seed-ir` → `/seed-ir` 트리거 확인. Pages URL `https://aqualife75.github.io/jsbiz-seed-ir/` 열어 렌더 확인(배포 반영 1~3분).
- [ ] **Step 5: 메모리·CLAUDE.md** — `C:/Users/leedg/.claude/projects/D--BRIAN-Dropbox-Lee-Dong-Geon/memory/`에 `jsbiz-seed-ir-distribution.md`(project) 작성 + `MEMORY.md` 한 줄. 내용: 저장소·Pages URL·설치 두 줄·설치본 동기화 규칙·시냅스 테스트 산출물 위치.
- [ ] **Step 6: 완료 보고** — 사용자에게: 설치 두 줄 · Pages URL · 시냅스 결과물 경로 · 확보 필요/라이선스 확인 필요 요약 · 다음 수업(9/12) 배포 안내 문구 초안 3줄.

---

## Part D 완료 기준
- `docs/index.html`이 브라우저에서 모바일·데스크톱 모두 정상, 설치 두 줄 복사 동작.
- 셀아이 evals `full_run` 완주(4종 산출·trace OK·BLOCKING 0).
- 시냅스 통합 실행 완주 + 사용자 검수 반영 + 실행 기록.
- GitHub 공개 저장소·Pages 활성화(사용자 승인 후) + 새 세션 설치 리허설 성공.

## 실행 기록
(Task 19 Step 6 · Task 20 · Task 21 결과를 여기에 날짜와 함께 적는다.)

### 2026-09-12 실행 기록 (Task 19 Step 6 · 빌드 완료 시점)
- 구현 커밋 39건, `pytest tests -q` 86 passed / 1 skipped(실파일 env 없을 때).
- `claude plugin validate .` ✔ · `claude plugin validate plugins/seed-ir` ✔ (프론트매터 description을 YAML 블록 스칼라로 수정 후).
- 로컬 설치(`scripts/install_local.py --target .claude`) 후 현재 세션의 스킬 목록에 `seed-ir`(설명 전문)이 노출됨 — 트리거 확인. 마켓플레이스 경로(`/plugin marketplace add`) 리허설은 GitHub 배포(Task 21) 후 새 세션에서 수행.
- 렌더 검수: 셀아이 예시 22장 PNG 육안 확인, 3장 좌표 수정(5c1bf7f) + 한글 단어 중간 줄바꿈 방지(976be23, Pretendard 실측 폭 기반 명시적 줄바꿈 — `eaLnBrk` 속성은 한글에 무효함을 실험으로 확인).
- 사용법 HTML: 10개 섹션·설치 두 줄·복사 버튼 확인(브라우저 미리보기 텍스트 검사).
- 미완: Task 20 시냅스 통합 실행, Task 21 GitHub 배포 — 사용자 결정 대기.

### Task 20 — 시냅스 팀 통합 실행 기록 (2026-09-12)

**입력** 포스텍 창업경진대회 참가신청서 hwp 1개 → 7,529자 · 이미지 7장 · 경고 0

**단계별 결과**
| 단계 | 결과 |
|---|---|
| 1 사실 팩 | items 10(확보 4·부분 4·없음 2), 슬롯 12(충분 2·부분 9·없음 1), gaps 5 |
| 2 작성 | 스토리라인 14장(사용자 확인) → 본문 14장, trace OK, `[기입 필요]` 11 |
| 3 심사 | 평균 **30.4점**(vc 26·ac 36·domain 34·finance 10·layman 46) · O 0·△ 2·X 10 · critical 11·major 4·minor 3 · 공격질문 15 |
| 4 조사 | 주제 8개 병렬 → 근거 **31건**, Tier B 캡처 8, 웹 이미지 4(unknown 3) → 개정본 14장, resolved 10 / open 8, `[확보 필요]` 21, to_secure 10 |
| 5 디자인 | **24장**(본문 16 + Q&A 4 + 근거캡처 4), BLOCKING 0, 반복 3회, PNG 전장 검수 |
| 6 피칭 | 총 **305초**, 대본 **1,700자**, Q&A 15, 확보 필요 15건, 라이선스 확인 12건. gate final OK |

**하네스가 실제로 잡아낸 것**
- 검산 에이전트: SOM 자릿수 오류(50만×1%×4,900원×12 = 2.9억인데 29억 표기) → 개정본 제목에 2.9억으로 반영
- 조사: 재학생 233만 9,937명이 공식 수치임을 원문 캡처로 확인(재적학생 301만과 다른 지표임을 덱에 명시)
- 조사: 기관 라이선스 팀 가정 연 300만 원 vs 유사 기관 실계약 연 2,100만~2,880만 원 → 9장 제목을 "기관가는 재설정이 필요합니다"로

**통합 실행이 찾아낸 결함 5건**(단위 테스트로는 원리적으로 불가)
| # | 결함 | 커밋 |
|---|---|---|
| 1 | 테스트 출력이 Dropbox 동기화 폴더 → 파일 잠금 간헐 실패 | a5d63d6 |
| 2 | 조사 8개 병렬 시 Chrome `--user-data-dir` 공유 → 캡처 전량 실패 | 9bc6efe |
| 3 | 게이트가 `changes[].before`(수정 전 문장 인용)의 `[기입 필요]`까지 세어 오작동 | 7dbaa33 |
| 4 | `solution_steps` 마지막 밴드 muted@35% + 흰 글자 → 판독 불가 | e21a5b2 |
| 5 | 표지에 팀 이미지 없으면 우측 7.5in 죽은 공간 | fecb68f |

**남은 한계** 팀 내부 사실(재무·지분·실험 효과 크기)은 조사로 대체 불가 — 설계대로 `[확보 필요]`로 남기고 피칭가이드 4)에 액션 아이템 15건으로 정리. 이것이 팀에 전달할 산출물.
