# Part B — 덱 빌더 구현 계획 (Task 8~13)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. 공통 제약은 `2026-09-11-seed-ir-00-index.md`의 Global Constraints를 따른다. Part A(Task 1~7)가 먼저 완료되어 있어야 한다.

**Goal:** `08_deck_spec.json` → 글루코픽 샘플 수준의 16:9 PPTX(20×11.25in, Pretendard, 다크/크림 교차, 카드·통계·사진 패널·네이티브 차트)를 만드는 `build_deck.py`(레이아웃 22종)와 이미지 전처리, 렌더 검수(PNG/PDF), `harness build/qa/pdf`를 완성한다.

**Architecture:** `design_system.py`(토큰 유일 원천) → `layouts/base.py`의 `Canvas` 프리미티브(배경·킥커·제목·리드·카드·통계·출처·페이지·사진 패널·노트, 텍스트 넘침 추정+자동 축소) → `layouts/l_*.py`가 레이아웃 함수를 `LAYOUTS` 레지스트리에 등록 → `build_deck.build(spec, out)`가 순회. `render_qa.py`는 PowerPoint COM(Windows)/LibreOffice(Mac) 폴백으로 PNG·PDF.

**Tech Stack:** python-pptx 1.0.x(도형·텍스트·표·네이티브 차트·XML alpha), Pillow(사진 전처리), PowerShell COM / soffice.

경로 약어: `S` = `plugins/seed-ir/skills/seed-ir`, `SC` = `S/scripts`, `L` = `SC/layouts`, `T` = `tests`.

### 좌표 규약 (모든 레이아웃 공통, 단위 inch, 캔버스 20×11.25)
| 요소 | x | y | w | h |
|---|---|---|---|---|
| 좌우 여백 `MX` | 1.125 | | 콘텐츠 폭 `CW` = 17.75 | |
| 킥커 | MX | 0.78 | 12 | 0.35 |
| 제목(2줄, 49.5pt) | MX | 1.15 | CW | 1.70 |
| 리드(2줄, 18.75pt) | MX | 2.95 | CW | 0.80 |
| 본문 영역 `BODY_Y`~`BODY_B` | MX | 3.90 | CW | 10.30 − 3.90 = 6.40 |
| 출처줄 | MX | 10.50 | 14 | 0.30 |
| 페이지 `n / N` | 17.5 | 10.50 | 1.375 | 0.30 (우측 정렬) |
| 카드 간격 `GAP` | 0.25 | | 카드 라운드 adj 0.02 | |
| 우측 사진 패널 | 12.5 | 0 | 7.5 | 11.25 (표지·비전·문제1) |

3열 카드 폭 = (CW − 2·GAP)/3 = 5.75 · 4열 = (CW − 3·GAP)/4 = 4.25 · 5열 = (CW − 4·GAP)/5 = 3.35.

---

### Task 8: 디자인 토큰 `design_system.py` + 이미지 전처리 `prep_image.py`

**Files:**
- Create: `SC/design_system.py`, `SC/prep_image.py`, `T/test_prep_image.py`

**Interfaces:**
- Produces (`design_system`): `CANVAS_W=20.0, CANVAS_H=11.25, FONT="Pretendard"`, `BG={"dark":"10141B","cream":"F5F2EB"}`, `C` dict(색 토큰), `SZ` dict(pt), `MX, CW, GAP, BODY_Y, BODY_B, SRC_Y, PANEL_X, PANEL_W`, 함수 `accent(bg)`, `ink(bg)`, `sub(bg)`, `muted(bg)`, `card_style(bg) -> dict(fill, alpha, line, line_alpha)`, `col_w(n) -> float`.
- Produces (`prep_image`): `to_png(src, dst)`, `fit_cover(src, dst, w_px, h_px)`, `darken(src, dst, strength=0.6, tint="10141B")`, `round_corners(src, dst, radius_px=24)`, `crop(src, dst, box=(l,t,r,b))`, `panel(src, dst, w_px, h_px, strength)`(=fit_cover+darken), CLI `python prep_image.py <op> src dst [옵션]`.

- [ ] **Step 1: 실패하는 테스트 작성** — `T/test_prep_image.py`

```python
# -*- coding: utf-8 -*-
from PIL import Image
import design_system as ds
import prep_image as pi

def test_tokens_match_spec():
    assert (ds.CANVAS_W, ds.CANVAS_H) == (20.0, 11.25) and ds.FONT == "Pretendard"
    assert ds.BG == {"dark": "10141B", "cream": "F5F2EB"}
    assert ds.accent("cream") == "E0492E" and ds.accent("dark") == "FF6A4D"
    assert ds.ink("dark") == "FFFFFF" and ds.ink("cream") == "10141B"
    assert abs(ds.col_w(3) - 5.75) < 1e-6 and abs(ds.col_w(4) - 4.25) < 1e-6

def test_fit_cover_and_darken(out_dir):
    src = out_dir / "s.jpg"; Image.new("RGB", (800, 300), (200, 200, 200)).save(src)
    dst = out_dir / "d.png"; pi.fit_cover(src, dst, 400, 400)
    im = Image.open(dst); assert im.size == (400, 400)
    dk = out_dir / "k.png"; pi.darken(dst, dk, 0.6)
    px = Image.open(dk).convert("RGB").getpixel((10, 10))
    assert px[0] < 120  # 어두워짐

def test_round_and_crop_and_bmp(out_dir):
    src = out_dir / "b.bmp"; Image.new("RGB", (100, 60), (1, 2, 3)).save(src)
    png = out_dir / "b.png"; pi.to_png(src, png); assert Image.open(png).format == "PNG"
    rc = out_dir / "r.png"; pi.round_corners(png, rc, 20); assert Image.open(rc).mode == "RGBA"
    cr = out_dir / "c.png"; pi.crop(png, cr, (10, 10, 50, 40)); assert Image.open(cr).size == (40, 30)
```

- [ ] **Step 2: 실행해 실패 확인** — Run: `PYTHONUTF8=1 python -m pytest tests/test_prep_image.py -q` → FAIL `ModuleNotFoundError`

- [ ] **Step 3: 구현**

`SC/design_system.py`
```python
# -*- coding: utf-8 -*-
"""디자인 토큰 — 글루코픽 샘플에서 추출(설계서 §5-1). 이 파일이 유일한 원천."""
CANVAS_W, CANVAS_H = 20.0, 11.25
FONT = "Pretendard"
BG = {"dark": "10141B", "cream": "F5F2EB"}
C = {
    "ink": "10141B", "white": "FFFFFF", "sub": "5C6572", "muted": "8A93A0", "sub_dark": "B3BAC4", "muted_dark": "6B7480",
    "card_border": "E6E2DA", "card_dark": "1A2130", "accent": "E0492E", "accent_dark": "FF6A4D", "amber": "F2A33C",
    "teal": "4FD1C5", "teal_deep": "177B72", "purple": "8A5BD6", "gradient_end": "F2A33C", "accent_tint": "FBE9E5", "amber_tint": "FDF3E3",
}
SZ = {"kicker": 12.75, "title": 49.5, "title_sm": 42.0, "statement": 60.0, "lead": 18.75, "label": 11.25, "big": 49.5, "big_md": 36.0,
      "big_sm": 27.0, "unit": 15.75, "body": 14.25, "body_sm": 13.5, "small": 12.0, "source": 10.5, "page": 10.5, "card_title": 20.25}
MX, CW, GAP = 1.125, 17.75, 0.25
KICKER_Y, TITLE_Y, LEAD_Y = 0.78, 1.15, 2.95
BODY_Y, BODY_B = 3.90, 10.30
SRC_Y = 10.50
PANEL_X, PANEL_W = 12.5, 7.5
RADIUS_ADJ = 0.02  # roundRect adjustment (≈8px)

def accent(bg: str) -> str: return C["accent_dark"] if bg == "dark" else C["accent"]
def ink(bg: str) -> str: return C["white"] if bg == "dark" else C["ink"]
def sub(bg: str) -> str: return C["sub_dark"] if bg == "dark" else C["sub"]
def muted(bg: str) -> str: return C["muted_dark"] if bg == "dark" else C["muted"]
def card_style(bg: str) -> dict:
    if bg == "dark":
        return {"fill": "FFFFFF", "alpha": 4, "line": "FFFFFF", "line_alpha": 10}
    return {"fill": "FFFFFF", "alpha": None, "line": C["card_border"], "line_alpha": None}
def col_w(n: int, total: float = CW, gap: float = GAP) -> float: return (total - (n - 1) * gap) / n
```

`SC/prep_image.py`
```python
# -*- coding: utf-8 -*-
"""이미지 전처리: PNG 변환·커버 맞춤·어둡게·라운딩·크롭. 빌더와 에이전트가 CLI/함수로 사용."""
from __future__ import annotations
import argparse, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps

def _open(p) -> Image.Image:
    im = Image.open(p); im.load(); return ImageOps.exif_transpose(im)

def to_png(src, dst):
    im = _open(src); (im.convert("RGBA") if im.mode in ("P", "LA", "CMYK") else im).save(dst, "PNG"); return dst

def fit_cover(src, dst, w_px: int, h_px: int):
    im = _open(src).convert("RGB")
    im = ImageOps.fit(im, (int(w_px), int(h_px)), method=Image.LANCZOS, centering=(0.5, 0.5))
    im.save(dst, "PNG"); return dst

def darken(src, dst, strength: float = 0.6, tint: str = "10141B"):
    im = _open(src).convert("RGBA")
    r, g, b = int(tint[0:2], 16), int(tint[2:4], 16), int(tint[4:6], 16)
    overlay = Image.new("RGBA", im.size, (r, g, b, int(255 * max(0.0, min(1.0, strength)))))
    Image.alpha_composite(im, overlay).convert("RGB").save(dst, "PNG"); return dst

def round_corners(src, dst, radius_px: int = 24):
    im = _open(src).convert("RGBA")
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, im.width - 1, im.height - 1), radius=radius_px, fill=255)
    im.putalpha(mask); im.save(dst, "PNG"); return dst

def crop(src, dst, box):
    im = _open(src); im.crop(tuple(int(v) for v in box)).save(dst, "PNG"); return dst

def panel(src, dst, w_px: int, h_px: int, strength: float = 0.6):
    fit_cover(src, dst, w_px, h_px); return darken(dst, dst, strength)

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="prep_image.py")
    sub = ap.add_subparsers(dest="op", required=True)
    for op in ("to_png", "fit_cover", "darken", "round", "crop", "panel"):
        p = sub.add_parser(op); p.add_argument("src"); p.add_argument("dst")
        if op in ("fit_cover", "panel"): p.add_argument("--size", default="1440x1080", help="WxH px")
        if op in ("darken", "panel"): p.add_argument("--strength", type=float, default=0.6)
        if op == "round": p.add_argument("--radius", type=int, default=24)
        if op == "crop": p.add_argument("--box", required=True, help="l,t,r,b px")
    a = ap.parse_args(argv)
    if a.op == "to_png": to_png(a.src, a.dst)
    elif a.op == "fit_cover": w, h = a.size.lower().split("x"); fit_cover(a.src, a.dst, int(w), int(h))
    elif a.op == "darken": darken(a.src, a.dst, a.strength)
    elif a.op == "round": round_corners(a.src, a.dst, a.radius)
    elif a.op == "crop": crop(a.src, a.dst, [int(v) for v in a.box.split(",")])
    elif a.op == "panel": w, h = a.size.lower().split("x"); panel(a.src, a.dst, int(w), int(h), a.strength)
    print(a.dst); return 0

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: 테스트 통과** — Run: `PYTHONUTF8=1 python -m pytest tests/test_prep_image.py -q` → `3 passed`

- [ ] **Step 5: 커밋**

```bash
git add -A && git -c user.name="Lee Dong-Geon" -c user.email="leedg.brian@gmail.com" commit -m "feat(design): 디자인 토큰 + 이미지 전처리

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 9: 빌더 프레임워크 `layouts/base.py` + `build_deck.py` + 레이아웃 `cover`·`statement`·`trend_cards`

**Files:**
- Create: `L/__init__.py`, `L/base.py`, `L/l_cover_intro.py`, `SC/build_deck.py`, `T/test_build.py`

**Interfaces:**
- Produces:
  - `layouts.base.Canvas(slide, bg, ctx)` 메서드: `rect(x,y,w,h, fill=None, alpha=None, line=None, line_alpha=None, radius=False, gradient_to=None) -> shape`, `text(x,y,w,h, content, size, color, bold=False, align="left", anchor="top", spacing=0.0, line_spacing=1.2, max_lines=None, slot="") -> shape` (content: str with `**강조**`/`__굵게__` 마크업, `\n` 문단), `kicker(text)`, `title(text, y=TITLE_Y, size=None, w=CW)`, `lead(text, y=LEAD_Y, w=CW)`, `card(x,y,w,h, style="plain"|"dark"|"accent"|"outline", top_bar=None) -> shape`, `stat(x,y,w, big, unit="", label="", source=None, big_size=SZ["big"], color=None, label_color=None)`, `label(x,y,w, text, color=None)`(작은 자간 라벨), `source_line(text)`, `page_no(n, total)`, `picture(path, x,y,w,h, cover=True, darken=None, radius=None) -> shape|None`, `panel_image(path, strength=0.6)`, `notes(text)`, `body_bullets(x,y,w,h, items, size=SZ["body"], color=None, bullet="·")`.
  - `layouts.base.DeckCtx`: `.team, .accent_override, .assets_dir, .tmp, .warnings: list[dict], .total`.
  - `layouts.LAYOUTS: dict[str, Callable[[Canvas, dict, dict], None]]` — 함수 시그니처 `fn(cv, slots, slide)`; 각 `l_*.py`가 `register("name")` 데코레이터로 등록.
  - `build_deck.build(spec_path, out_path) -> dict` (`{"out": str, "slides": n, "warnings": [...]}`), CLI `python build_deck.py spec.json --out deck.pptx`.
- 마크업: `**텍스트**` → 강조색(accent) 굵게, `__텍스트__` → 굵게(같은 색), 그 외 일반.
- 텍스트 넘침 추정: `est_lines(text, size_pt, width_in)` — 한글 폭 0.92em, ASCII 0.55em 평균 → 상한 초과면 1.5pt 축소 1회 후 재계산, 여전히 초과면 `ctx.warnings.append({"slide": no, "slot": slot, "text": text[:30], "lines": est, "max": max_lines})`.

- [ ] **Step 1: 실패하는 테스트 작성** — `T/test_build.py`

```python
# -*- coding: utf-8 -*-
import json
from pathlib import Path
from PIL import Image
from pptx import Presentation
from pptx.util import Inches
import build_deck
from layouts import base, LAYOUTS

def _spec(out_dir, img=None):
    return {"meta": {"team": "셀아이", "accent": "E0492E", "assets_dir": str(out_dir)}, "slides": [
        {"no": 1, "layout": "cover", "background": "dark", "slots": {
            "kicker": "TEAM CELLEYE · 사업계획서 2026", "brand": "CellEye", "headline": "라인 위 결함을\n**0.3초**에 잡습니다",
            "subtitle": "이차전지 전극 공정을 위한\nAI 비전 검사 모듈", "tags": ["0.3초 판독", "라인 무정지", "기존 장비 호환"],
            "panel_image": img, "footer_stats": [{"label": "TEAM", "value": "셀아이 · CELLEYE"}, {"label": "TARGET", "value": "전극 라인 400개"},
                                                 {"label": "MODEL", "value": "월 300만 원 구독"}, {"label": "STAGE", "value": "Seed · PoC"}]}, "notes": "표지 대본"},
        {"no": 2, "layout": "statement", "background": "dark", "slots": {"statement": "검사는 자동인데,\n**판독**은 아직 사람입니다", "sub": "문제의 위치"}, "notes": ""},
        {"no": 3, "layout": "trend_cards", "background": "cream", "slots": {
            "title": "라인은 늘고, **불량 비용**은 커지고, 검사 인력은 줍니다", "lead": "세 곡선이 동시에 꺾이는 지점에 공백이 있습니다.",
            "cards": [{"label": "TREND 01 · 라인 증설", "headline": "국내 전극 라인", "big": "400", "unit": "개", "desc": "2년 새 30% 증가했습니다.", "source": "한국배터리산업협회 2025", "tone": "accent"},
                      {"label": "TREND 02 · 불량 비용", "headline": "셀 1개 불량 손실", "big": "12", "unit": "만 원", "desc": "후공정에서 발견 시 3배.", "source": "업계 인터뷰 2026.08", "tone": "amber"},
                      {"label": "TREND 03 · 인력", "headline": "검사원 이직률", "big": "28", "unit": "%", "desc": "야간 판독 인력 부족.", "source": "고용노동부 2025", "tone": "dark"}],
            "band": {"so_what": "판독만 사람이 합니다.", "why_now": ["AI 비전 원가 60% 하락 (2024)", "라인 데이터 표준화", "품질 규제 강화"]},
            "key_gap": "측정은 자동인데 판독은 손"}, "source_line": "출처: 한국배터리산업협회 「전극 라인 현황」 (2025.03) · 수집 2026-09-11", "notes": "트렌드 대본"}]}

def test_build_three_layouts(out_dir):
    img = out_dir / "p.jpg"; Image.new("RGB", (1200, 900), (90, 60, 40)).save(img)
    spec = _spec(out_dir, str(img)); sp = out_dir / "spec.json"; sp.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    rep = build_deck.build(sp, out_dir / "deck.pptx")
    prs = Presentation(str(out_dir / "deck.pptx"))
    assert len(prs.slides) == 3 and prs.slide_width == Inches(20) and prs.slide_height == Inches(11.25)
    texts = "\n".join(sh.text_frame.text for s in prs.slides for sh in s.shapes if sh.has_text_frame)
    assert "0.3초" in texts and "3 / 3" in texts and "출처: 한국배터리산업협회" in texts
    assert prs.slides[0].notes_slide.notes_text_frame.text == "표지 대본"
    pics = [sh for sh in prs.slides[0].shapes if sh.shape_type == 13]
    assert len(pics) == 1
    fonts = {r.font.name for s in prs.slides for sh in s.shapes if sh.has_text_frame for p in sh.text_frame.paragraphs for r in p.runs if r.font.name}
    assert fonts == {"Pretendard"}
    assert rep["warnings"] == []

def test_markup_runs(out_dir):
    spec = _spec(out_dir); spec["slides"] = spec["slides"][1:2]
    sp = out_dir / "s.json"; sp.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    build_deck.build(sp, out_dir / "d.pptx")
    prs = Presentation(str(out_dir / "d.pptx"))
    runs = [r for sh in prs.slides[0].shapes if sh.has_text_frame for p in sh.text_frame.paragraphs for r in p.runs]
    accent_runs = [r for r in runs if r.text == "판독"]
    assert accent_runs and str(accent_runs[0].font.color.rgb) == "FF6A4D"

def test_overflow_warning(out_dir):
    spec = _spec(out_dir); spec["slides"] = spec["slides"][1:2]
    spec["slides"][0]["slots"]["statement"] = "매우 " * 40
    sp = out_dir / "o.json"; sp.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    rep = build_deck.build(sp, out_dir / "o.pptx")
    assert rep["warnings"] and rep["warnings"][0]["slide"] == 2

def test_registry_has_first_three():
    assert {"cover", "statement", "trend_cards"} <= set(LAYOUTS)
```

- [ ] **Step 2: 실행해 실패 확인** — Run: `PYTHONUTF8=1 python -m pytest tests/test_build.py -q` → FAIL `ModuleNotFoundError: No module named 'build_deck'`

- [ ] **Step 3: 구현**

`L/__init__.py`
```python
# -*- coding: utf-8 -*-
"""레이아웃 레지스트리. 각 l_*.py가 import 시 register()로 등록한다."""
from __future__ import annotations
from typing import Callable
LAYOUTS: dict[str, Callable] = {}

def register(name: str):
    def deco(fn):
        LAYOUTS[name] = fn; return fn
    return deco

from . import l_cover_intro  # noqa: E402,F401
# Task 10~12에서 추가: from . import l_problem, l_solution, l_market_bm, l_plan_team
```

`L/base.py`
```python
# -*- coding: utf-8 -*-
"""Canvas 프리미티브 — 모든 레이아웃이 이것만으로 그린다."""
from __future__ import annotations
import math, os, re, tempfile
from dataclasses import dataclass, field
from pathlib import Path
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR, MSO_AUTO_SIZE
from pptx.oxml.ns import qn
import design_system as ds
import prep_image

_ALIGN = {"left": PP_ALIGN.LEFT, "center": PP_ALIGN.CENTER, "right": PP_ALIGN.RIGHT}
_ANCHOR = {"top": MSO_ANCHOR.TOP, "middle": MSO_ANCHOR.MIDDLE, "bottom": MSO_ANCHOR.BOTTOM}
_MARK = re.compile(r"(\*\*.+?\*\*|__.+?__)")

@dataclass
class DeckCtx:
    team: str
    total: int
    assets_dir: Path
    accent_override: str | None = None
    tmp: Path = field(default_factory=lambda: Path(tempfile.mkdtemp(prefix="seed_ir_")))
    warnings: list = field(default_factory=list)
    current_no: int = 0

def rgb(h: str) -> RGBColor: return RGBColor.from_string(h.lstrip("#").upper())

def est_lines(text: str, size_pt: float, width_in: float) -> int:
    """문단별 예상 줄 수 합. 한글 0.92em·ASCII 0.55em 평균 폭."""
    total = 0
    for para in (text or "").split("\n"):
        if not para: total += 1; continue
        w = sum(0.55 if ord(ch) < 0x2E80 else 0.92 for ch in para) * size_pt / 72.0
        total += max(1, math.ceil(w / max(width_in - 0.1, 0.1)))
    return total

def _set_font(run, name, size, bold, color, spacing=0.0):
    run.font.name = name; run.font.size = Pt(size); run.font.bold = bold; run.font.color.rgb = rgb(color)
    rPr = run._r.get_or_add_rPr()
    for tag in ("a:ea", "a:cs"):
        el = rPr.find(qn(tag))
        if el is None:
            el = rPr.makeelement(qn(tag), {}); rPr.append(el)
        el.set("typeface", name)
    if spacing:
        rPr.set("spc", str(int(spacing * size * 100)))

def _alpha(color_elm_parent, pct: int):
    clr = color_elm_parent.find(qn("a:srgbClr"))
    if clr is not None:
        a = clr.makeelement(qn("a:alpha"), {"val": str(int(pct * 1000))}); clr.append(a)

class Canvas:
    def __init__(self, slide, bg: str, ctx: DeckCtx):
        self.s, self.bg, self.ctx = slide, bg, ctx
        self.accent = ctx.accent_override if (ctx.accent_override and bg == "cream") else ds.accent(bg)
        self.ink, self.sub, self.muted = ds.ink(bg), ds.sub(bg), ds.muted(bg)
        slide.background.fill.solid(); slide.background.fill.fore_color.rgb = rgb(ds.BG[bg])

    # ── 도형 ──
    def rect(self, x, y, w, h, fill=None, alpha=None, line=None, line_alpha=None, radius=False, gradient_to=None):
        shp = self.s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
        if radius: shp.adjustments[0] = ds.RADIUS_ADJ if radius is True else radius
        shp.shadow.inherit = False
        if fill is None: shp.fill.background()
        elif gradient_to:
            shp.fill.gradient(); shp.fill.gradient_angle = 0
            shp.fill.gradient_stops[0].color.rgb = rgb(fill); shp.fill.gradient_stops[1].color.rgb = rgb(gradient_to)
        else:
            shp.fill.solid(); shp.fill.fore_color.rgb = rgb(fill)
            if alpha is not None: _alpha(shp.fill._xPr.find(qn("a:solidFill")), alpha)
        if line is None: shp.line.fill.background()
        else:
            shp.line.color.rgb = rgb(line); shp.line.width = Pt(1)
            if line_alpha is not None: _alpha(shp.line._get_or_add_ln().find(qn("a:solidFill")), line_alpha)
        return shp

    # ── 텍스트 ──
    def text(self, x, y, w, h, content, size, color, bold=False, align="left", anchor="top", spacing=0.0, line_spacing=1.2, max_lines=None, slot=""):
        content = content or ""
        if max_lines:
            est = est_lines(re.sub(r"\*\*|__", "", content), size, w)
            if est > max_lines:
                size -= 1.5; est = est_lines(re.sub(r"\*\*|__", "", content), size, w)
                if est > max_lines:
                    self.ctx.warnings.append({"slide": self.ctx.current_no, "slot": slot, "text": content[:30], "lines": est, "max": max_lines})
        tb = self.s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = tb.text_frame; tf.word_wrap = True; tf.auto_size = MSO_AUTO_SIZE.NONE; tf.vertical_anchor = _ANCHOR[anchor]
        tf.margin_left = tf.margin_right = Inches(0.02); tf.margin_top = tf.margin_bottom = Inches(0.01)
        for i, para in enumerate(content.split("\n")):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = _ALIGN[align]; p.line_spacing = line_spacing; p.space_after = Pt(0)
            for piece in _MARK.split(para):
                if not piece: continue
                r = p.add_run()
                if piece.startswith("**"): r.text = piece[2:-2]; _set_font(r, ds.FONT, size, True, self.accent, spacing)
                elif piece.startswith("__"): r.text = piece[2:-2]; _set_font(r, ds.FONT, size, True, color, spacing)
                else: r.text = piece; _set_font(r, ds.FONT, size, bold, color, spacing)
        return tb

    def kicker(self, text):
        return self.text(ds.MX, ds.KICKER_Y, 12, 0.35, text, ds.SZ["kicker"], self.accent, bold=True, spacing=0.25, max_lines=1, slot="kicker")

    def title(self, text, y=ds.TITLE_Y, size=None, w=ds.CW, max_lines=2):
        return self.text(ds.MX, y, w, 1.70, text, size or ds.SZ["title"], self.ink, bold=True, line_spacing=1.1, max_lines=max_lines, slot="title")

    def lead(self, text, y=ds.LEAD_Y, w=ds.CW):
        return self.text(ds.MX, y, w, 0.80, text, ds.SZ["lead"], self.sub, line_spacing=1.35, max_lines=2, slot="lead")

    def label(self, x, y, w, text, color=None):
        return self.text(x, y, w, 0.3, text, ds.SZ["label"], color or self.accent, bold=True, spacing=0.15, max_lines=1, slot="label")

    def card(self, x, y, w, h, style="plain", top_bar=None):
        st = ds.card_style(self.bg)
        if style == "dark": shp = self.rect(x, y, w, h, fill=ds.BG["dark"], radius=True)
        elif style == "accent": shp = self.rect(x, y, w, h, fill=ds.C["accent"], gradient_to=ds.C["gradient_end"], radius=True)
        elif style == "outline": shp = self.rect(x, y, w, h, fill=None, line=self.accent, radius=True)
        elif style == "tint": shp = self.rect(x, y, w, h, fill=ds.C["accent_tint"], line=ds.C["card_border"], radius=True)
        else: shp = self.rect(x, y, w, h, fill=st["fill"], alpha=st["alpha"], line=st["line"], line_alpha=st["line_alpha"], radius=True)
        if top_bar: self.rect(x, y, w, 0.06, fill=top_bar)
        return shp

    def stat(self, x, y, w, big, unit="", label="", source=None, big_size=None, color=None, label_color=None):
        big_size = big_size or ds.SZ["big"]; color = color or self.ink
        tb = self.text(x, y, w, big_size / 72 * 1.25, big, big_size, color, bold=True, max_lines=1, slot="stat.big")
        if unit:
            p = tb.text_frame.paragraphs[0]; r = p.add_run(); r.text = " " + unit; _set_font(r, ds.FONT, ds.SZ["unit"], True, color)
        yy = y + big_size / 72 * 1.25 + 0.05
        if label: self.text(x, yy, w, 0.35, label, ds.SZ["body_sm"], self.sub if label_color is None else label_color, max_lines=1, slot="stat.label"); yy += 0.38
        if source: self.text(x, yy, w, 0.3, source, ds.SZ["source"], self.muted, max_lines=1, slot="stat.source")
        return tb

    def body_bullets(self, x, y, w, h, items, size=None, color=None, bullet="·"):
        return self.text(x, y, w, h, "\n".join(f"{bullet} {it}" for it in items), size or ds.SZ["body"], color or self.sub, line_spacing=1.45, slot="bullets")

    def source_line(self, text):
        if text: self.text(ds.MX, ds.SRC_Y, 14.5, 0.3, text, ds.SZ["source"], self.muted, max_lines=1, slot="source_line")

    def page_no(self, n, total):
        self.text(17.5, ds.SRC_Y, 1.375, 0.3, f"{n} / {total}", ds.SZ["page"], self.muted, align="right")

    # ── 이미지 ──
    def _resolve(self, path):
        if not path: return None
        p = Path(path)
        if not p.is_absolute(): p = self.ctx.assets_dir / p
        return p if p.exists() else None

    def picture(self, path, x, y, w, h, cover=True, darken=None, radius=None):
        p = self._resolve(path)
        if not p:
            self.rect(x, y, w, h, fill=ds.C["card_dark"] if self.bg == "dark" else ds.C["card_border"], radius=True)
            self.text(x, y, w, h, "[이미지 확보 필요]", ds.SZ["small"], self.muted, align="center", anchor="middle")
            self.ctx.warnings.append({"slide": self.ctx.current_no, "slot": "image", "text": f"missing {path}", "lines": 0, "max": 0}); return None
        out = self.ctx.tmp / f"s{self.ctx.current_no}_{abs(hash((str(p), x, y, w, h)))}.png"
        px = (int(w * 96), int(h * 96))
        if cover: prep_image.fit_cover(p, out, *px)
        else: prep_image.to_png(p, out)
        if darken: prep_image.darken(out, out, darken)
        if radius: prep_image.round_corners(out, out, radius)
        return self.s.shapes.add_picture(str(out), Inches(x), Inches(y), Inches(w), Inches(h) if cover else None)

    def panel_image(self, path, strength=0.6, x=ds.PANEL_X, w=ds.PANEL_W):
        shp = self.picture(path, x, 0, w, ds.CANVAS_H, cover=True, darken=strength)
        if shp is None: self.rect(x, 0, w, ds.CANVAS_H, fill=ds.C["card_dark"])
        return shp

    def notes(self, text):
        if text: self.s.notes_slide.notes_text_frame.text = text
```

`L/l_cover_intro.py`
```python
# -*- coding: utf-8 -*-
from . import register
import design_system as ds

@register("cover")
def cover(cv, s, slide):
    cv.panel_image(s.get("panel_image"), strength=0.55)
    left_w = ds.PANEL_X - ds.MX - 0.6
    cv.rect(ds.MX, 0.95, 0.04, 4.6, fill=cv.accent)
    cv.text(ds.MX + 0.4, 0.95, left_w, 0.35, s.get("kicker", ""), ds.SZ["kicker"], ds.C["amber"], bold=True, spacing=0.25, max_lines=1, slot="kicker")
    if s.get("brand"):
        cv.rect(ds.MX + 0.4, 1.55, 4.2, 1.0, fill="FFFFFF", radius=True)
        cv.text(ds.MX + 0.7, 1.55, 3.7, 1.0, s["brand"], 30, ds.C["ink"], bold=True, anchor="middle", max_lines=1, slot="brand")
    cv.text(ds.MX + 0.4, 3.1, left_w, 2.6, s.get("headline", ""), 66, ds.C["white"], bold=True, line_spacing=1.08, max_lines=2, slot="headline")
    cv.text(ds.MX + 0.4, 5.85, left_w, 1.1, s.get("subtitle", ""), 24, ds.C["sub_dark"], line_spacing=1.35, max_lines=2, slot="subtitle")
    tags = s.get("tags") or []
    if tags:
        cv.text(ds.MX + 0.4, 7.3, left_w, 0.4, "   ·   ".join(tags), ds.SZ["body"], ds.C["amber"], bold=True, max_lines=1, slot="tags")
    stats = s.get("footer_stats") or []
    if stats:
        cv.rect(ds.MX + 0.4, 9.35, 18.0, 0.01, fill="FFFFFF", alpha=15)
        w = 4.4
        for i, st in enumerate(stats[:4]):
            x = ds.MX + 0.4 + i * w
            cv.text(x, 9.65, w - 0.2, 0.3, st.get("label", ""), ds.SZ["label"], ds.C["muted_dark"], bold=True, spacing=0.2, max_lines=1, slot="footer_stats.label")
            cv.text(x, 9.98, w - 0.2, 0.45, st.get("value", ""), 20, ds.C["amber"] if i == 3 else ds.C["white"], bold=True, max_lines=1, slot="footer_stats.value")
    cv.notes(slide.get("notes"))

@register("statement")
def statement(cv, s, slide):
    cv.rect(ds.MX, 3.3, 0.06, 3.2, fill=cv.accent)
    cv.text(ds.MX + 0.5, 3.2, 16.5, 3.4, s.get("statement", ""), ds.SZ["statement"], cv.ink, bold=True, line_spacing=1.12, anchor="middle", max_lines=2, slot="statement")
    if s.get("sub"):
        cv.text(ds.MX + 0.5, 6.9, 16.5, 0.6, s["sub"], ds.SZ["lead"], cv.sub, max_lines=1, slot="sub")
    cv.page_no(slide["no"], cv.ctx.total); cv.notes(slide.get("notes"))

_TONE = {"accent": ds.C["accent"], "amber": ds.C["amber"], "teal": ds.C["teal"], "dark": ds.C["teal"]}

@register("trend_cards")
def trend_cards(cv, s, slide):
    cv.kicker(s.get("kicker", "")); cv.title(s.get("title", "")); cv.lead(s.get("lead", ""))
    if s.get("key_gap"):
        cv.card(16.1, 0.75, 2.75, 2.8); cv.label(16.4, 1.0, 2.2, "KEY GAP")
        cv.text(16.4, 1.4, 2.2, 2.0, s["key_gap"], ds.SZ["card_title"], cv.ink, bold=True, line_spacing=1.25, max_lines=4, slot="key_gap")
    cards = s.get("cards") or []
    n = max(1, len(cards)); w = ds.col_w(n); y, h = ds.BODY_Y, 3.45
    for i, c in enumerate(cards):
        x = ds.MX + i * (w + ds.GAP); tone = c.get("tone", ["accent", "amber", "teal"][i % 3])
        dark = tone == "dark"
        cv.card(x, y, w, h, style="dark" if dark else "plain", top_bar=_TONE[tone])
        ink, sub, mut = (ds.C["white"], ds.C["sub_dark"], ds.C["muted_dark"]) if dark else (cv.ink, cv.sub, cv.muted)
        cv.label(x + 0.4, y + 0.35, w - 0.8, c.get("label", ""), color=_TONE[tone] if not dark else ds.C["teal"])
        cv.text(x + 0.4, y + 0.75, w - 0.8, 0.5, c.get("headline", ""), ds.SZ["card_title"], ink, bold=True, max_lines=1, slot="cards.headline")
        cv.stat(x + 0.4, y + 1.3, w - 0.8, c.get("big", ""), c.get("unit", ""), color=ink)
        cv.text(x + 0.4, y + 2.25, w - 0.8, 0.7, c.get("desc", ""), ds.SZ["body"], sub, line_spacing=1.4, max_lines=2, slot="cards.desc")
        cv.text(x + 0.4, y + 3.0, w - 0.8, 0.3, c.get("source", ""), ds.SZ["source"], mut, max_lines=1, slot="cards.source")
    band = s.get("band")
    if band:
        by = y + h + 0.35; bh = ds.BODY_B - by
        cv.card(ds.MX, by, ds.CW, bh, style="accent")
        cv.label(ds.MX + 0.45, by + 0.4, 6, "SO WHAT", color="FFFFFF")
        cv.text(ds.MX + 0.45, by + 0.85, 8.2, bh - 1.1, band.get("so_what", ""), 27, ds.C["white"], bold=True, line_spacing=1.25, max_lines=2, slot="band.so_what")
        cv.label(ds.MX + 9.4, by + 0.4, 6, "WHY NOW", color="FFFFFF")
        cv.body_bullets(ds.MX + 9.4, by + 0.85, 7.8, bh - 1.0, band.get("why_now", []), size=ds.SZ["body"], color=ds.C["white"])
    cv.source_line(slide.get("source_line", "")); cv.page_no(slide["no"], cv.ctx.total); cv.notes(slide.get("notes"))
```

`SC/build_deck.py`
```python
# -*- coding: utf-8 -*-
"""deck_spec.json → PPTX. 사용: python build_deck.py spec.json --out deck.pptx"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import design_system as ds  # noqa: E402
from layouts import LAYOUTS  # noqa: E402
from layouts.base import Canvas, DeckCtx  # noqa: E402

def build(spec_path, out_path) -> dict:
    spec_path = Path(spec_path); spec = json.loads(spec_path.read_text(encoding="utf-8"))
    meta = spec.get("meta", {}); slides = spec["slides"]
    assets = Path(meta.get("assets_dir") or spec_path.parent)
    ctx = DeckCtx(team=meta.get("team", ""), total=len(slides), assets_dir=assets, accent_override=meta.get("accent") if meta.get("accent") not in (None, "", "E0492E") else None)
    prs = Presentation(); prs.slide_width = Inches(ds.CANVAS_W); prs.slide_height = Inches(ds.CANVAS_H)
    blank = prs.slide_layouts[6]
    for sl in slides:
        lay = sl["layout"]
        if lay not in LAYOUTS:
            raise SystemExit(f"unknown layout: {lay} (slide {sl.get('no')})")
        ctx.current_no = sl.get("no", 0)
        cv = Canvas(prs.slides.add_slide(blank), sl.get("background", "cream"), ctx)
        LAYOUTS[lay](cv, sl.get("slots", {}), sl)
    out_path = Path(out_path); out_path.parent.mkdir(parents=True, exist_ok=True); prs.save(str(out_path))
    return {"out": str(out_path), "slides": len(slides), "warnings": ctx.warnings}

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("spec"); ap.add_argument("--out", required=True)
    a = ap.parse_args(argv); rep = build(a.spec, a.out)
    print(f"built {rep['slides']} slides → {rep['out']}  warnings={len(rep['warnings'])}")
    for w in rep["warnings"]: print(f"  ! slide {w['slide']} {w['slot']}: {w['lines']}줄 > {w['max']} '{w['text']}'")
    return 0
if __name__ == "__main__": sys.exit(main())
```

- [ ] **Step 4: 테스트 통과** — Run: `PYTHONUTF8=1 python -m pytest tests/test_build.py -q` → `4 passed`
- [ ] **Step 5: 육안 확인** — Run: `powershell -NoProfile -File "<Dropbox>/00. A_창업 교육/00. 2026년도_창업/2026.09.15_포스텍_IR Deck 강의/_harness/export_all.ps1" -Pptx tests/_out/test_build_three_layouts/deck.pptx -OutDir tests/_out/png9` 후 PNG 3장을 Read로 열어 표지 패널·카드 3장·밴드가 샘플 슬라이드 1·2와 같은 구도인지 확인. 어긋나면 좌표만 수정(테스트 재실행).
- [ ] **Step 6: 커밋**

```bash
git add -A && git -c user.name="Lee Dong-Geon" -c user.email="leedg.brian@gmail.com" commit -m "feat(build): Canvas 프리미티브 + build_deck + cover/statement/trend_cards

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 10: 레이아웃 그룹 1 — 문제·경쟁·솔루션 (`l_problem.py`, `l_solution.py`)

**Files:**
- Create: `L/l_problem.py`(problem_cascade · problem_grid · alt_table · quadrant), `L/l_solution.py`(solution_steps · product_screens · tech_moat · mvp_scope), `T/test_layouts.py`
- Modify: `L/__init__.py` (import 추가)

**Interfaces:**
- Consumes: Task 9 `Canvas`, `register`. 슬롯 이름·상한은 `limits.json`(Task 5)과 일치해야 한다.
- Produces: 8개 레이아웃 등록. 테스트 헬퍼 `T/test_layouts.py::sample_slots(layout) -> dict`(모든 레이아웃의 예시 슬롯 — Task 12 `spec.example.json`의 재료).

- [ ] **Step 1: 실패하는 테스트 작성** — `T/test_layouts.py`

```python
# -*- coding: utf-8 -*-
import json
import pytest
from pptx import Presentation
import build_deck, validate
from layouts import LAYOUTS

GROUP1 = ["problem_cascade", "problem_grid", "alt_table", "quadrant", "solution_steps", "product_screens", "tech_moat", "mvp_scope"]

def sample_slots(layout: str) -> dict:
    S = {
      "problem_cascade": {"kicker": "02 · PROBLEM 1", "title": "라인은 아는데, **판독은 3명 중 1명**만 합니다", "lead": "검출은 자동인데 최종 판독은 사람이 하고 있습니다.",
          "bars": [{"label": "검출률", "value": 74.7}, {"label": "판독률", "value": 70.9}, {"label": "조치율", "value": 32.4, "tone": "accent"}, {"label": "재발 방지", "value": 15.9, "tone": "accent"}],
          "kpis": [{"big": "1.18조 원", "label": "연간 불량 손실", "source": "협회 2024"}, {"big": "+25.7%", "label": "5년 증가율", "source": "2019→2023"}, {"big": "48.2%", "label": "야간 미판독 비율", "source": "인터뷰 2026"}],
          "quote": {"text": "사진은 찍히는데, 판독을 사람이 하는 순간 라인이 멈춥니다.", "who": "48세 · 공정 관리자 · 자체 인터뷰 (2026.08)"}, "panel_image": None},
      "problem_grid": {"kicker": "02 · PROBLEM 2", "title": "판독은 '귀찮아서'가 아니라 **구조적으로** 끊깁니다", "lead": "4단계 마찰이 반복됩니다.",
          "stats": [{"big": "60%", "label": "14일 내 사용 중단", "source": "Nutrola 2025"}, {"big": "77%", "label": "30일 내 이탈", "source": "Stanford 2024"}, {"big": "1.2%p", "label": "지속 기록 시 개선", "source": "JMIR 2022"}],
          "points": [{"num": "01", "title": "판단 불가", "sub": "몇 그램일까", "desc": "추정 정확도 44%."}, {"num": "02", "title": "입력 마찰", "sub": "검색·선택·수정", "desc": "반찬 단위 입력."},
                     {"num": "03", "title": "사회적 장벽", "sub": "회식 자리", "desc": "앱을 못 꺼냅니다."}, {"num": "04", "title": "해석 부재", "sub": "뭘 바꿀지 모름", "desc": "원인 구분 불가."}],
          "footnote": "PAID-K 44.6/85점 (KJAN 2020)"},
      "alt_table": {"kicker": "03 · ALTERNATIVES 1", "title": "기존 앱은 '측정'을 돕습니다. **'식사'는 사용자 몫**입니다", "lead": "CGM 연동은 성숙했지만 사진 경로는 비어 있습니다.",
          "table": {"columns": ["파스타", "닥터다이어리", "MyFitnessPal", "우리"], "us_col": 3,
                    "rows": [{"label": "기기 무관", "cells": ["✕", "△", "○", "○"]}, {"label": "한식·배달 인식", "cells": ["✕", "△", "✕", "○"]},
                             {"label": "행동 처방", "cells": ["✕", "✕", "✕", "○"]}, {"label": "유료 레퍼런스", "cells": ["다수", "180만 DL", "글로벌", "0건"], "weakness": True}]},
          "premise_note": "공통 전제 — 사용자가 정확히 입력할 것을 가정 (Meade LT et al., 2016)"},
      "quadrant": {"kicker": "03 · ALTERNATIVES 2", "title": "비어 있는 사분면: **기기 없이, 외식에서**", "lead": "경쟁사는 CGM 착용자와 집밥 식단에 몰려 있습니다.",
          "axes": {"x_left": "집밥 · 계획된 식단", "x_right": "외식 · 배달 · 회식", "y_top": "입력 부담 ↑", "y_bottom": "입력 부담 ↓"},
          "bubbles": [{"name": "MyFitnessPal", "sub": "수기 입력", "x": 0.18, "y": 0.28, "size": 1.6}, {"name": "파스타", "sub": "CGM 한정", "x": 0.42, "y": 0.18, "size": 1.6, "tone": "teal"},
                      {"name": "닥터다이어리", "sub": "커뮤니티", "x": 0.3, "y": 0.75, "size": 1.6, "tone": "amber"}, {"name": "글루코핏", "sub": "고가 코칭", "x": 0.48, "y": 0.58, "size": 1.4, "tone": "purple"},
                      {"name": "우리", "sub": "사진 1장 · 외식 특화", "x": 0.77, "y": 0.72, "size": 2.1, "is_us": True}],
          "gaps": [{"title": "GAP 01 · 기기 종속", "desc": "CGM 착용자만 온전한 경험."}, {"title": "GAP 02 · 한식 인식", "desc": "해외 DB는 한식 부정확."}, {"title": "GAP 03 · 행동 처방 부재", "desc": "기록·시각화에서 끝."}]},
      "solution_steps": {"kicker": "04 · SOLUTION", "title": "입력을 없애고, **해석을 남깁니다**", "lead": "사진 한 장 → 인식 → 보정 → 연결 → 처방.",
          "steps": [{"label": "STEP 01", "title": "사진 촬영", "desc": "회식 자리에서도 3초."}, {"label": "STEP 02", "title": "AI 인식", "desc": "한식·배달 특화."}, {"label": "STEP 03", "title": "2탭 보정", "desc": "버튼 두 번."}, {"label": "STEP 04 · 핵심", "title": "혈당 연결", "desc": "다음 끼니 처방."}],
          "cards": [{"num": "01", "title": "입력이 아니라\n촬영입니다", "desc": "음식명 검색·중량 입력 단계를 제거합니다.", "source": "Meade LT et al. 2016"}, {"num": "02", "title": "기기를\n가리지 않습니다", "desc": "자가혈당측정기 두 번 입력으로 동작.", "source": "CGM 급여 확대 2024.12"}, {"num": "03", "title": "숫자가 아니라\n다음 행동을 줍니다", "desc": "실행 가능한 문장으로만 출력.", "source": "※ 생활 관리 참고 정보"}]},
      "product_screens": {"kicker": "05 · PRODUCT 1", "title": "점심 한 끼, **30초**의 사용자 여정", "lead": "촬영부터 가이드까지 버튼 3번.",
          "screens": [{"image": None, "label": "01 · CAPTURE", "title": "촬영 3초", "desc": "앱을 열면 바로 카메라."}, {"mock_lines": ["김치찌개 백반", "추정 탄수화물 78~94g", "공깃밥 210g 68g"], "label": "02 · RECOGNIZE", "title": "범위로 답합니다", "desc": "단일 수치 대신 범위."},
                      {"mock_lines": ["전부 먹음 / 밥 절반", "보정 후 44~52g"], "label": "03 · ADJUST", "title": "타이핑 0회", "desc": "남긴 양을 버튼으로."}, {"mock_lines": ["198 mg/dL", "다음엔 밥 1/3 남기기"], "label": "04 · ACT", "title": "본인 데이터로 설득", "desc": "내 기록의 비교값.", "tone": "accent"}],
          "footnote": "※ 화면은 MVP 설계안이며 수치는 예시입니다."},
      "tech_moat": {"kicker": "05 · PRODUCT 2 · TECHNOLOGY", "title": "한식 데이터가 **이미 존재**합니다", "lead": "공공 데이터셋 100만 장 이상.",
          "data_cards": [{"big": "53.7만 장", "label": "음식 이미지 + 혈당 매칭", "desc": "204종 · 식후혈당 36,091건"}, {"big": "16.2만 장", "label": "외식·배달 메뉴", "desc": "500종"}, {"big": "84.2만 장", "label": "이미지+영양 텍스트", "desc": "400종 이상"}],
          "pipeline": [{"title": "① 인식 레이어", "desc": "사진 → Top-3 후보 + 영역 분할"}, {"title": "② 정량화 레이어", "desc": "영양 DB 매칭 → 탄수화물 범위"}, {"title": "③ 개인화 레이어", "desc": "같은 메뉴 × 같은 사람의 반응 곡선"}],
          "moat": {"title": "\"한식 사진 × 실제 식후 혈당\" 쌍은 국내 누구도 대규모로 보유하지 못했습니다.", "desc": "1만 명 × 하루 2끼 = 연 730만 건 축적"},
          "safety": "혈당 수치를 예측·진단하지 않습니다. 참고 정보만 제공해 의료기기 규제 밖에서 출시합니다."},
      "mvp_scope": {"kicker": "05 · PRODUCT 3 · SCOPE", "title": "무엇을 만들고, **무엇을 만들지 않는가**", "lead": "MVP는 '외식 한 끼를 30초에 닫는 것' 하나에만 집중합니다.",
          "now": [{"title": "① 사진 기반 식사 기록", "desc": "한식·외식·배달 인식"}, {"title": "② 2탭 섭취량 보정", "desc": "타이핑 0회"}, {"title": "③ 혈당 연결", "desc": "수동 입력 + 리마인더"}, {"title": "④ 다음 끼니 가이드", "desc": "실행 문장 1개"}],
          "target_line": "MVP 목표 — 첫 기록 완료율 70% · 보정 완료율 70% · 연결률 60%",
          "not_now": ["✕ 혈당 수치 예측 — 신뢰 안 함, 규제 리스크", "✕ 커뮤니티·커머스 — 닥터다이어리 점유", "✕ 센서 하드웨어 판매", "✕ 인슐린 용량 제안", "✕ 1형 당뇨 대응"],
          "roadmap": [{"label": "V2 · 7~12개월", "title": "CGM 자동 연동", "desc": "다기종 연동·반응 곡선 리포트"}, {"label": "V3 · 13~24개월", "title": "B2B 대시보드", "desc": "교육센터·검진기관용"}, {"label": "V4 · 25개월~", "title": "임상 근거 확보", "desc": "HbA1c 개선 검증"}]},
    }
    return S[layout]

def _spec_for(layouts, out_dir):
    slides = []
    for i, lay in enumerate(layouts, 1):
        bg = "dark" if lay in ("problem_cascade", "quadrant", "tech_moat") else "cream"
        slides.append({"no": i, "layout": lay, "background": bg, "slots": sample_slots(lay), "source_line": f"출처: 샘플 {lay} · 수집 2026-09-11", "notes": f"{lay} 대본"})
    spec = {"meta": {"team": "셀아이", "assets_dir": str(out_dir)}, "slides": slides}
    p = out_dir / "spec.json"; p.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8"); return p, spec

@pytest.mark.parametrize("layout", GROUP1)
def test_group1_builds_without_warnings(layout, out_dir):
    assert layout in LAYOUTS
    p, spec = _spec_for([layout], out_dir)
    assert validate.validate_obj(spec, "deck_spec") == []
    rep = build_deck.build(p, out_dir / f"{layout}.pptx")
    assert rep["warnings"] == [], rep["warnings"]
    prs = Presentation(str(out_dir / f"{layout}.pptx"))
    texts = "\n".join(sh.text_frame.text for sh in prs.slides[0].shapes if sh.has_text_frame)
    assert "1 / 1" in texts and "출처: 샘플" in texts

def test_alt_table_marks_weakness(out_dir):
    p, _ = _spec_for(["alt_table"], out_dir)
    build_deck.build(p, out_dir / "t.pptx")
    prs = Presentation(str(out_dir / "t.pptx"))
    tables = [sh for sh in prs.slides[0].shapes if sh.has_table]
    assert tables and tables[0].table.cell(4, 4).text == "0건"
```

- [ ] **Step 2: 실행해 실패 확인** — Run: `PYTHONUTF8=1 python -m pytest tests/test_layouts.py -q` → FAIL (`assert layout in LAYOUTS`)

- [ ] **Step 3: 구현**

`L/l_problem.py`
```python
# -*- coding: utf-8 -*-
from pptx.util import Inches, Pt
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from . import register
from .base import rgb, _set_font
import design_system as ds

_TONE = {"accent": ds.C["accent"], "amber": ds.C["amber"], "teal": ds.C["teal"], "purple": ds.C["purple"]}
_PP_ALIGN = {"left": PP_ALIGN.LEFT, "center": PP_ALIGN.CENTER, "right": PP_ALIGN.RIGHT}

def _chrome(cv, s, slide, lead_w=ds.CW):
    cv.kicker(s.get("kicker", "")); cv.title(s.get("title", ""), w=lead_w); cv.lead(s.get("lead", ""), w=lead_w)
    cv.source_line(slide.get("source_line", "")); cv.page_no(slide["no"], cv.ctx.total); cv.notes(slide.get("notes"))

@register("problem_cascade")
def problem_cascade(cv, s, slide):
    has_panel = bool(s.get("panel_image")) or bool(s.get("quote"))
    left_w = (ds.PANEL_X - ds.MX - 0.6) if has_panel else ds.CW
    if s.get("panel_image"): cv.panel_image(s["panel_image"], strength=0.65)
    _chrome(cv, s, slide, lead_w=left_w)
    bars = s.get("bars") or []
    cv.card(ds.MX, ds.BODY_Y, left_w, 3.0)
    cv.label(ds.MX + 0.4, ds.BODY_Y + 0.35, left_w - 0.8, "CASCADE · 단계별 이탈")
    if bars:
        mx = max(b["value"] for b in bars) or 1; bw = ds.col_w(len(bars), left_w - 0.8, 0.2); bx = ds.MX + 0.4; base_y = ds.BODY_Y + 2.35
        for i, b in enumerate(bars):
            x = bx + i * (bw + 0.2); h = 0.9 * b["value"] / mx; tone = _TONE.get(b.get("tone", ["teal", "amber", "accent", "accent"][i % 4]))
            cv.text(x, base_y - h - 0.5, bw, 0.45, f"{b['value']}%", 24, tone if b.get("tone") == "accent" else cv.ink, bold=True, max_lines=1, slot="bars.value")
            cv.rect(x, base_y - h, bw, h, fill=tone)
            cv.text(x, base_y + 0.08, bw, 0.3, b["label"], ds.SZ["body_sm"], cv.ink, bold=True, max_lines=1, slot="bars.label")
    kpis = s.get("kpis") or []
    if kpis:
        kw = ds.col_w(len(kpis), left_w, 0.2); ky = ds.BODY_Y + 3.35; kh = ds.BODY_B - ky
        for i, k in enumerate(kpis):
            x = ds.MX + i * (kw + 0.2); tone = list(_TONE.values())[i % 3]
            cv.card(x, ky, kw, kh); cv.rect(x, ky, 0.05, kh, fill=tone)
            cv.stat(x + 0.35, ky + 0.35, kw - 0.6, k.get("big", ""), label=k.get("label", ""), source=k.get("source"), big_size=ds.SZ["big_md"])
    q = s.get("quote")
    if q:
        qx, qy, qw, qh = ds.PANEL_X + 0.4, 4.5, ds.PANEL_W - 0.8, 3.3
        cv.rect(qx, qy, qw, qh, fill=ds.BG["dark"], alpha=70, line=ds.C["amber"], line_alpha=60, radius=True)
        cv.label(qx + 0.4, qy + 0.35, qw - 0.8, "현장의 언어", color=ds.C["amber"])
        cv.text(qx + 0.4, qy + 0.8, qw - 0.8, 1.9, f"“{q.get('text','')}”", ds.SZ["card_title"], ds.C["white"], bold=True, line_spacing=1.3, max_lines=4, slot="quote.text")
        cv.text(qx + 0.4, qy + 2.75, qw - 0.8, 0.5, q.get("who", ""), ds.SZ["small"], ds.C["sub_dark"], max_lines=2, slot="quote.who")

@register("problem_grid")
def problem_grid(cv, s, slide):
    _chrome(cv, s, slide)
    stats = s.get("stats") or []
    y = ds.BODY_Y
    if stats:
        cv.label(ds.MX, y, 8, "EVIDENCE · 이탈률")
        sw = ds.col_w(len(stats)); 
        for i, st in enumerate(stats):
            cv.stat(ds.MX + i * (sw + ds.GAP), y + 0.4, sw - 0.3, st.get("big", ""), label=st.get("label", ""), source=st.get("source"), big_size=ds.SZ["big_md"], color=cv.accent if i == 0 else cv.ink)
        y += 2.0
    pts = s.get("points") or []
    if pts:
        pw = ds.col_w(len(pts)); ph = ds.BODY_B - y - 0.5
        for i, p in enumerate(pts):
            x = ds.MX + i * (pw + ds.GAP); cv.card(x, y, pw, ph)
            cv.text(x + 0.35, y + 0.3, pw - 0.7, 0.5, p.get("num", f"0{i+1}"), 30, cv.accent, bold=True, max_lines=1, slot="points.num")
            cv.text(x + 0.35, y + 0.95, pw - 0.7, 0.5, p.get("title", ""), ds.SZ["card_title"], cv.ink, bold=True, max_lines=1, slot="points.title")
            cv.text(x + 0.35, y + 1.45, pw - 0.7, 0.4, p.get("sub", ""), ds.SZ["body"], cv.accent, bold=True, max_lines=1, slot="points.sub")
            cv.text(x + 0.35, y + 1.95, pw - 0.7, ph - 2.2, p.get("desc", ""), ds.SZ["body"], cv.sub, line_spacing=1.45, max_lines=4, slot="points.desc")
    if s.get("footnote"): cv.text(ds.MX, ds.BODY_B - 0.4, ds.CW, 0.35, s["footnote"], ds.SZ["small"], cv.muted, max_lines=1, slot="footnote")

@register("alt_table")
def alt_table(cv, s, slide):
    _chrome(cv, s, slide)
    t = s.get("table") or {}; cols = t.get("columns") or []; rows = t.get("rows") or []; us = t.get("us_col", len(cols) - 1)
    n_r, n_c = len(rows) + 1, len(cols) + 1
    th = min(0.85, (ds.BODY_B - ds.BODY_Y - 1.2) / n_r)
    gf = cv.s.shapes.add_table(n_r, n_c, Inches(ds.MX), Inches(ds.BODY_Y), Inches(ds.CW), Inches(th * n_r)); tbl = gf.table
    tbl.columns[0].width = Inches(3.6)
    for j in range(1, n_c): tbl.columns[j].width = Inches((ds.CW - 3.6) / len(cols))
    def cell(r, c, text, size, color, bold=False, fill=None, align="left"):
        ce = tbl.cell(r, c); ce.text = ""; ce.margin_left = ce.margin_right = Inches(0.2); ce.margin_top = ce.margin_bottom = Inches(0.08)
        ce.fill.solid(); ce.fill.fore_color.rgb = rgb(fill or ("1A2130" if cv.bg == "dark" else "FFFFFF"))
        p = ce.text_frame.paragraphs[0]; p.alignment = _PP_ALIGN[align]; run = p.add_run(); run.text = text; _set_font(run, ds.FONT, size, bold, color)
    cell(0, 0, "비교 항목", ds.SZ["body_sm"], ds.C["amber"], True, fill=ds.BG["dark"])
    for j, c in enumerate(cols, 1):
        cell(0, j, c, ds.SZ["body_sm"], ds.C["white"] if j - 1 != us else ds.C["accent_dark"], True, fill=ds.BG["dark"], align="center")
    for i, r in enumerate(rows, 1):
        weak = r.get("weakness", False)
        cell(i, 0, r.get("label", ""), ds.SZ["body"], cv.ink, True, fill=ds.C["amber_tint"] if weak else None)
        for j, v in enumerate(r.get("cells", []), 1):
            is_us = (j - 1 == us)
            color = (ds.C["amber"] if weak else cv.accent) if is_us else cv.sub
            cell(i, j, v, ds.SZ["body"], color, is_us, fill=(ds.C["amber_tint"] if weak else (ds.C["accent_tint"] if is_us and cv.bg == "cream" else None)), align="center")
    if any(r.get("weakness") for r in rows):
        cv.text(ds.MX, ds.BODY_Y + th * n_r + 0.15, ds.CW, 0.3, "▲ 강조 행 = 우리가 뒤지는 항목(솔직하게 표시)", ds.SZ["small"], ds.C["amber"], bold=True, max_lines=1)
    if s.get("premise_note"):
        cv.card(ds.MX, ds.BODY_B - 1.0, ds.CW, 0.85, style="tint" if cv.bg == "cream" else "plain")
        cv.text(ds.MX + 0.4, ds.BODY_B - 0.9, ds.CW - 0.8, 0.65, s["premise_note"], ds.SZ["body"], cv.ink, anchor="middle", max_lines=2, slot="premise_note")

@register("quadrant")
def quadrant(cv, s, slide):
    _chrome(cv, s, slide)
    ax = s.get("axes") or {}
    qx, qy, qw, qh = ds.MX, ds.BODY_Y, 10.4, ds.BODY_B - ds.BODY_Y - 0.4
    line = ds.C["muted_dark"] if cv.bg == "dark" else ds.C["card_border"]
    cv.rect(qx, qy, 0.02, qh, fill=line); cv.rect(qx, qy + qh, qw, 0.02, fill=line)
    cv.rect(qx + qw / 2, qy, 0.015, qh, fill=line, alpha=50); cv.rect(qx, qy + qh / 2, qw, 0.015, fill=line, alpha=50)
    cv.text(qx + 0.2, qy + 0.1, 4, 0.3, ax.get("x_left", ""), ds.SZ["small"], cv.muted, max_lines=1); cv.text(qx + qw - 4.2, qy + 0.1, 4, 0.3, ax.get("x_right", ""), ds.SZ["small"], cv.muted, align="right", max_lines=1)
    cv.text(qx - 1.0, qy + qh / 2 - 0.5, 1.0, 0.9, f"{ax.get('y_top','')}\n{ax.get('y_bottom','')}", ds.SZ["small"], cv.muted, align="right")
    for b in s.get("bubbles") or []:
        d = b.get("size", 1.6); cx = qx + b["x"] * qw - d / 2; cy = qy + (1 - b["y"]) * qh - d / 2
        us = b.get("is_us"); tone = _TONE.get(b.get("tone", ""), ds.C["muted_dark"] if cv.bg == "dark" else ds.C["sub"])
        shp = cv.s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(cx), Inches(cy), Inches(d), Inches(d)); shp.shadow.inherit = False
        shp.fill.solid(); shp.fill.fore_color.rgb = rgb(cv.accent if us else tone)
        if not us:
            from .base import _alpha; from pptx.oxml.ns import qn
            _alpha(shp.fill._xPr.find(qn("a:solidFill")), 22); shp.line.color.rgb = rgb(tone); shp.line.width = Pt(1)
        else: shp.line.fill.background()
        txt_color = ds.C["white"] if us else (ds.C["white"] if cv.bg == "dark" else cv.ink)
        cv.text(cx, cy + d * 0.28, d, 0.45, b.get("name", ""), 17 if us else 14, txt_color, bold=True, align="center", max_lines=1, slot="bubbles.name")
        cv.text(cx, cy + d * 0.28 + 0.45, d, 0.5, b.get("sub", ""), ds.SZ["small"], txt_color if us else cv.muted, align="center", max_lines=2, slot="bubbles.sub")
    gaps = s.get("gaps") or []
    gx, gw = ds.MX + qw + 0.7, ds.CW - qw - 0.7
    cv.label(gx, ds.BODY_Y, gw, "대체재가 남긴 공백", color=ds.C["amber"])
    gh = (ds.BODY_B - ds.BODY_Y - 0.6 - 0.2 * (len(gaps) - 1)) / max(1, len(gaps))
    for i, g in enumerate(gaps):
        y = ds.BODY_Y + 0.45 + i * (gh + 0.2); cv.card(gx, y, gw, gh); cv.rect(gx, y, 0.05, gh, fill=list(_TONE.values())[i % 3])
        cv.text(gx + 0.35, y + 0.25, gw - 0.6, 0.45, g.get("title", ""), ds.SZ["card_title"], cv.ink, bold=True, max_lines=1, slot="gaps.title")
        cv.text(gx + 0.35, y + 0.75, gw - 0.6, gh - 0.9, g.get("desc", ""), ds.SZ["body"], cv.sub, line_spacing=1.4, max_lines=3, slot="gaps.desc")
```

`L/l_solution.py`
```python
# -*- coding: utf-8 -*-
from . import register
from .l_problem import _chrome, _TONE
import design_system as ds

@register("solution_steps")
def solution_steps(cv, s, slide):
    _chrome(cv, s, slide)
    steps = s.get("steps") or []; y = ds.BODY_Y; h = 2.2
    if steps:
        n = len(steps); w = ds.CW / n
        for i, st in enumerate(steps):
            x = ds.MX + i * w; last = (i == n - 1)
            cv.rect(x, y, w, h, fill=ds.C["card_dark"] if not last else ds.C["muted"], alpha=None if not last else 35, radius=(i == 0 or last))
            cv.label(x + 0.45, y + 0.35, w - 0.9, st.get("label", ""), color=ds.C["amber"] if not last else ds.C["accent"])
            cv.text(x + 0.45, y + 0.75, w - 0.9, 0.5, st.get("title", ""), ds.SZ["card_title"], ds.C["white"], bold=True, max_lines=1, slot="steps.title")
            cv.text(x + 0.45, y + 1.3, w - 0.9, 0.8, st.get("desc", ""), ds.SZ["body_sm"], ds.C["sub_dark"], line_spacing=1.4, max_lines=2, slot="steps.desc")
            if i < n - 1: cv.rect(x + w - 0.35, y + h / 2, 0.3, 0.02, fill=ds.C["amber"])
        y += h + 0.4
    cards = s.get("cards") or []
    if cards:
        cw = ds.col_w(len(cards)); ch = ds.BODY_B - y
        for i, c in enumerate(cards):
            x = ds.MX + i * (cw + ds.GAP); accent_card = (i == len(cards) - 1)
            cv.card(x, y, cw, ch, style="accent" if accent_card else "plain")
            ink = ds.C["white"] if accent_card else cv.ink; sub = ds.C["white"] if accent_card else cv.sub; mut = ds.C["white"] if accent_card else cv.muted
            cv.text(x + 0.45, y + 0.35, cw - 0.9, 0.7, c.get("num", f"0{i+1}"), 40, ds.C["white"] if accent_card else ds.C["amber"], bold=True, max_lines=1, slot="cards.num")
            cv.text(x + 0.45, y + 1.2, cw - 0.9, 1.1, c.get("title", ""), 27, ink, bold=True, line_spacing=1.2, max_lines=2, slot="cards.title")
            cv.text(x + 0.45, y + 2.4, cw - 0.9, ch - 3.0, c.get("desc", ""), ds.SZ["body"], sub, line_spacing=1.45, max_lines=3, slot="cards.desc")
            cv.text(x + 0.45, y + ch - 0.5, cw - 0.9, 0.3, c.get("source", ""), ds.SZ["source"], mut, max_lines=1, slot="cards.source")

@register("product_screens")
def product_screens(cv, s, slide):
    _chrome(cv, s, slide)
    scr = s.get("screens") or []; n = max(1, len(scr)); w = ds.col_w(n); y = ds.BODY_Y; h = ds.BODY_B - y - 0.6
    for i, sc in enumerate(scr):
        x = ds.MX + i * (w + ds.GAP); tone = sc.get("tone"); dark = (i == 0 and not tone); acc = tone == "accent"
        cv.card(x, y, w, h, style="dark" if dark else ("accent" if acc else "plain"))
        ink = ds.C["white"] if (dark or acc) else cv.ink; sub = ds.C["sub_dark"] if dark else (ds.C["white"] if acc else cv.sub)
        if sc.get("image"):
            cv.picture(sc["image"], x + 0.2, y + 0.2, w - 0.4, h * 0.5, cover=True, radius=16)
        else:
            lines = sc.get("mock_lines") or []
            for k, ln in enumerate(lines[:4]):
                cv.rect(x + 0.4, y + 0.5 + k * 0.7, w - 0.8, 0.55, fill=("FFFFFF" if not (dark or acc) else "FFFFFF"), alpha=(None if not (dark or acc) else 12), line=ds.C["card_border"] if not (dark or acc) else None, radius=True)
                cv.text(x + 0.6, y + 0.5 + k * 0.7, w - 1.2, 0.55, ln, ds.SZ["body_sm"], ink, bold=True, anchor="middle", max_lines=1, slot="screens.mock_lines")
        by = y + h * 0.5 + 0.45
        cv.label(x + 0.4, by, w - 0.8, sc.get("label", ""), color=ds.C["amber"] if dark else (ds.C["white"] if acc else cv.accent))
        cv.text(x + 0.4, by + 0.4, w - 0.8, 0.5, sc.get("title", ""), ds.SZ["card_title"], ink, bold=True, max_lines=1, slot="screens.title")
        cv.text(x + 0.4, by + 0.95, w - 0.8, h - (by - y) - 1.1, sc.get("desc", ""), ds.SZ["body"], sub, line_spacing=1.4, max_lines=3, slot="screens.desc")
    if s.get("footnote"): cv.text(ds.MX, ds.BODY_B - 0.4, ds.CW, 0.35, s["footnote"], ds.SZ["small"], cv.muted, max_lines=1, slot="footnote")

@register("tech_moat")
def tech_moat(cv, s, slide):
    _chrome(cv, s, slide)
    lw = 9.2; rx = ds.MX + lw + 0.5; rw = ds.CW - lw - 0.5
    cards = s.get("data_cards") or []; y = ds.BODY_Y
    cv.label(ds.MX, y, lw, "확보 가능한 학습 데이터", color=ds.C["amber"])
    ch = (ds.BODY_B - y - 0.5 - 0.2 * 2) / 3
    for i, c in enumerate(cards[:3]):
        cy = y + 0.45 + i * (ch + 0.2); cv.card(ds.MX, cy, lw, ch)
        cv.stat(ds.MX + 0.4, cy + 0.3, 3.4, c.get("big", ""), big_size=ds.SZ["big_sm"], color=cv.accent if i == 0 else cv.ink)
        cv.text(ds.MX + 4.0, cy + 0.3, lw - 4.4, 0.45, c.get("label", ""), ds.SZ["body"], cv.ink, bold=True, max_lines=1, slot="data_cards.label")
        cv.text(ds.MX + 4.0, cy + 0.8, lw - 4.4, ch - 1.0, c.get("desc", ""), ds.SZ["body_sm"], cv.sub, line_spacing=1.4, max_lines=2, slot="data_cards.desc")
    pipe = s.get("pipeline") or []
    cv.label(rx, y, rw, "파이프라인", color=ds.C["amber"])
    ph = 0.95
    for i, p in enumerate(pipe[:3]):
        py = y + 0.45 + i * (ph + 0.12); cv.rect(rx, py, 0.05, ph, fill=list(_TONE.values())[i % 3])
        cv.text(rx + 0.3, py, rw - 0.3, 0.4, p.get("title", ""), ds.SZ["body"], cv.ink, bold=True, max_lines=1, slot="pipeline.title")
        cv.text(rx + 0.3, py + 0.4, rw - 0.3, ph - 0.4, p.get("desc", ""), ds.SZ["body_sm"], cv.sub, line_spacing=1.35, max_lines=2, slot="pipeline.desc")
    moat = s.get("moat") or {}; my = y + 0.45 + 3 * (ph + 0.12) + 0.15; mh = ds.BODY_B - my - 1.15
    cv.card(rx, my, rw, mh, style="accent"); cv.label(rx + 0.4, my + 0.3, rw - 0.8, "DATA MOAT", color="FFFFFF")
    cv.text(rx + 0.4, my + 0.7, rw - 0.8, mh - 1.3, moat.get("title", ""), ds.SZ["card_title"], ds.C["white"], bold=True, line_spacing=1.3, max_lines=3, slot="moat.title")
    cv.text(rx + 0.4, my + mh - 0.55, rw - 0.8, 0.45, moat.get("desc", ""), ds.SZ["body_sm"], ds.C["white"], max_lines=1, slot="moat.desc")
    if s.get("safety"):
        sy = ds.BODY_B - 1.0; cv.card(rx, sy, rw, 0.9); cv.text(rx + 0.35, sy + 0.1, rw - 0.7, 0.7, "SAFETY · " + s["safety"], ds.SZ["small"], cv.sub, anchor="middle", line_spacing=1.3, max_lines=3, slot="safety")

@register("mvp_scope")
def mvp_scope(cv, s, slide):
    _chrome(cv, s, slide)
    lw = 8.4; rx = ds.MX + lw + 0.4; rw = ds.CW - lw - 0.4; y = ds.BODY_Y
    cv.card(ds.MX, y, lw, 3.9, style="dark"); cv.label(ds.MX + 0.4, y + 0.3, lw - 0.8, "MVP · 0~6개월 · 지금 만드는 것", color=ds.C["teal"])
    now = s.get("now") or []
    for i, it in enumerate(now[:4]):
        col, row = i % 2, i // 2; ix = ds.MX + 0.4 + col * (lw / 2 - 0.3); iy = y + 0.8 + row * 1.15
        cv.text(ix, iy, lw / 2 - 0.6, 0.4, it.get("title", ""), ds.SZ["body"], ds.C["white"], bold=True, max_lines=1, slot="now.title")
        cv.text(ix, iy + 0.4, lw / 2 - 0.6, 0.6, it.get("desc", ""), ds.SZ["body_sm"], ds.C["sub_dark"], max_lines=2, slot="now.desc")
    if s.get("target_line"):
        cv.rect(ds.MX + 0.4, y + 3.25, lw - 0.8, 0.02, fill="FFFFFF", alpha=15)
        cv.text(ds.MX + 0.4, y + 3.35, lw - 0.8, 0.45, s["target_line"], ds.SZ["body_sm"], ds.C["amber"], bold=True, max_lines=1, slot="target_line")
    nn = s.get("not_now") or []; ny = y + 4.2
    cv.label(ds.MX, ny, lw, "NOT NOW · 의도적으로 미루는 것", color=cv.accent)
    cv.body_bullets(ds.MX, ny + 0.4, lw, ds.BODY_B - ny - 0.5, nn, size=ds.SZ["body_sm"], bullet="")
    rm = s.get("roadmap") or []
    cv.label(rx, y, rw, "이후 로드맵", color=ds.C["amber"])
    rh = (ds.BODY_B - y - 0.45 - 0.2 * 2) / 3
    for i, r in enumerate(rm[:3]):
        ry = y + 0.45 + i * (rh + 0.2); cv.card(rx, ry, rw, rh); cv.rect(rx, ry, 0.05, rh, fill=list(_TONE.values())[i % 3])
        cv.label(rx + 0.35, ry + 0.25, rw - 0.6, r.get("label", ""), color=cv.muted)
        cv.text(rx + 0.35, ry + 0.6, rw - 0.6, 0.45, r.get("title", ""), ds.SZ["card_title"], cv.ink, bold=True, max_lines=1, slot="roadmap.title")
        cv.text(rx + 0.35, ry + 1.1, rw - 0.6, rh - 1.2, r.get("desc", ""), ds.SZ["body_sm"], cv.sub, line_spacing=1.35, max_lines=2, slot="roadmap.desc")
```

`L/__init__.py`에 `from . import l_problem, l_solution  # noqa` 추가.

- [ ] **Step 4: 테스트 통과** — Run: `PYTHONUTF8=1 python -m pytest tests/test_layouts.py -q` → `9 passed`
- [ ] **Step 5: 육안 확인** — 8장을 한 스펙으로 빌드(`_spec_for(GROUP1, …)`)해 export_all.ps1로 PNG 렌더 → Read로 열어 겹침·넘침 확인. 문제 시 좌표 수정 후 재실행.
- [ ] **Step 6: 커밋**

```bash
git add -A && git -c user.name="Lee Dong-Geon" -c user.email="leedg.brian@gmail.com" commit -m "feat(layouts): 문제·경쟁·솔루션 레이아웃 8종

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 11: 레이아웃 그룹 2 — 성과·수익·시장·진입·성장 (`l_market_bm.py`)

**Files:**
- Create: `L/l_market_bm.py`(traction_plan · kpi_chart · bm_pricing · market_tam · gtm_funnel · growth_phases)
- Modify: `L/__init__.py`, `T/test_layouts.py`(GROUP2 + sample_slots 확장)

**Interfaces:** Consumes Task 9·10. `kpi_chart`는 python-pptx 네이티브 차트(`XL_CHART_TYPE.COLUMN_CLUSTERED|BAR_CLUSTERED|LINE_MARKERS`) — 값 없는 시리즈 금지(빈 배열이면 경고 후 카드만).

- [ ] **Step 1: 테스트 확장** — `T/test_layouts.py`에 추가

```python
GROUP2 = ["traction_plan", "kpi_chart", "bm_pricing", "market_tam", "gtm_funnel", "growth_phases"]

# sample_slots의 S 딕셔너리에 추가:
      "traction_plan": {"kicker": "06 · EARLY TRACTION", "title": "말이 아니라 **결제와 행동**으로 검증합니다", "lead": "9,900원 예약금 결제와 7일 기록 로그만 지표로 인정합니다.",
          "weeks": [{"label": "WEEK 1 · 문제 인터뷰", "big": "8명", "desc": "솔루션 화면은 마지막 10분까지 감춥니다."}, {"label": "WEEK 2 · 사용성 테스트", "big": "7명", "desc": "실제 식사 사진 3장으로 전 과정 수행."},
                    {"label": "WEEK 3 · 7일 기록 실험", "big": "10명 · 핵심 관문", "desc": "5회 기록·3회 보정·2회 연결 달성자만 환급.", "tone": "dark"}, {"label": "WEEK 4 · 통합 분석", "big": "고객군별 비교", "desc": "3개 군 완료율·전환률 비교."}],
          "table": {"rows": [{"metric": "문제 공감률", "target": "70% 이상", "method": "최근 30일 실제 사례 진술"}, {"metric": "솔루션 사용 의향", "target": "50% 이상", "method": "9,900원 예약금 실제 결제"},
                             {"metric": "지불 의향", "target": "30% 이상", "method": "월 14,900원 사전 결제"}, {"metric": "첫 기록 완료율", "target": "70% 이상", "method": "업로드–확인–보정 로그"}]},
          "side": {"title": "확보한 모집 채널 20곳", "body": "온라인 커뮤니티 10곳, 교육센터 5곳, 학회·전시 5곳"},
          "insight": "1차 인터뷰 확인 — 예측 기능 신뢰 안 함 → MVP에서 제외"},
      "kpi_chart": {"kicker": "06 · TRACTION", "title": "월 활성 사용자 **3개월 연속 40% 성장**", "lead": "베타 출시 이후 실측 지표입니다.",
          "chart": {"type": "column", "categories": ["6월", "7월", "8월", "9월"], "series": [{"name": "MAU", "values": [120, 170, 240, 335]}], "unit": "명"},
          "kpis": [{"big": "335명", "label": "9월 MAU", "source": "자체 대시보드"}, {"big": "+40%", "label": "월 성장률", "source": "3개월 평균"}, {"big": "38%", "label": "7일 리텐션", "source": "코호트"}], "note": "출시 전 팀은 이 장 대신 traction_plan을 쓴다."},
      "bm_pricing": {"kicker": "07 · BUSINESS MODEL", "title": "기기를 팔지 않습니다. **습관을 구독**합니다", "lead": "소프트웨어 구독 단일 축으로 시작합니다.",
          "tiers": [{"label": "FREE", "price": "무료", "sub": "획득 단계", "bullets": ["하루 2끼 사진 기록", "탄수화물 범위 추정", "혈당 수동 입력"], "note": "첫 7일 기록 완료가 전환 선행 지표."},
                    {"label": "PRO · 핵심 수익원", "price": "월 14,900원", "sub": "연 결제 시 월 11,900원", "bullets": ["무제한 기록 + CGM 연동", "개인별 반응 곡선", "다음 끼니 가이드"], "note": "경쟁 월 27,900원 대비 47% 낮은 가격.", "highlight": True},
                    {"label": "B2B2C · 13개월~", "price": "계약 단가", "sub": "보험사 · 검진기관", "bullets": ["단체 라이선스", "사후관리 리포트", "상담 보조 도구"], "note": "닥터다이어리–한독 제휴가 선례."}],
          "unit_econ": [{"label": "ARPU", "big": "13,400원/월", "sub": "월·연 혼합 가정"}, {"label": "월 이탈률 목표", "big": "6% 이하", "sub": "평균 유지 16.7개월"}, {"label": "LTV", "big": "약 224,000원", "sub": "ARPU × 유지 개월"}, {"label": "목표 LTV/CAC", "big": "3.0배 이상", "sub": "CAC 상한 7.5만 원"}],
          "evidence_note": "비대면 건강관리에 월평균 10만 5,000원 지불 경험 (보건사회연구원 2023)"},
      "market_tam": {"kicker": "08 · MARKET SIZE", "title": "1,939만 명의 혈당 관리 인구, **9,700억 원**의 국내 잠재 시장", "lead": "수익 모델 기반으로 SOM → SAM → TAM 순서로 계산했습니다.",
          "tam": {"label": "TAM · 국내 혈당 관리 대상 인구 전체", "desc": "당뇨 530만 + 전단계 1,409만 = 1,939만 명", "big": "9,700", "unit": "억원", "calc": "1,939만 명 × 연 5만 원"},
          "sam": {"label": "SAM · 외식 비중 높은 경제활동 당뇨인", "desc": "30~64세 당뇨인 중 170만~200만 명", "big": "2,730", "unit": "억원", "calc": "170만 × 13,400원 × 12"},
          "som": {"label": "SOM · 3년 내 확보 목표", "desc": "SAM의 5~10% · 유료 10만~20만 명", "big": "180~360", "unit": "억원", "calc": "연 환산 매출"},
          "side_stats": [{"label": "글로벌 디지털 당뇨 관리", "big": "$13.4B → $21.9B", "sub": "2024→2030, CAGR 8.7%", "source": "Grand View Research"}, {"label": "국내 디지털헬스케어", "big": "6조 4,930억 원", "sub": "2023, 전년比 +13.5%", "source": "KODHIA 2024"}, {"label": "공적 지출", "big": "1.18조 원", "sub": "당뇨 진료비, 5년 +25.7%", "source": "HIRA 2024"}],
          "sanity_note": "국내 1위 닥터다이어리는 누적 180만 DL로 2024년 매출 150억 원. SOM 하단(연 180억)은 시장이 증명한 범위 안에 있습니다."},
      "gtm_funnel": {"kicker": "09 · GO-TO-MARKET", "title": "전국이 아니라 **성남·강남 직장인**부터", "lead": "첫 1,000명은 광고로 사지 않습니다.",
          "beachhead": {"title": "주 3회 이상 외식·배달하는\n35~55세 2형 당뇨 직장인", "why": "문제 빈도 최고, 본인 결제 의사결정권자.", "exclude": "인슐린 조절 잦은 환자, 1형 당뇨는 MVP 범위 밖."},
          "channels": [{"title": "1순위 · 병원 교육센터 5곳", "desc": "교육 후 자발 신청 방식으로만 모집."}, {"title": "2순위 · 당뇨 커뮤니티 10곳", "desc": "7일 기록 실험 참여자 공모."}, {"title": "3순위 · 유튜브 당뇨 채널", "desc": "유료 광고는 PMF 확인 후."}],
          "funnel": [{"label": "STEP 1 · 도달", "big": "20,000", "unit": "명", "desc": "게시물·안내문 노출"}, {"label": "STEP 2 · 신청", "big": "4,000", "unit": "명", "desc": "사전 선별 폼"}, {"label": "STEP 3 · 설치", "big": "2,400", "unit": "명", "desc": "첫 사진 업로드"},
                     {"label": "STEP 4 · 습관화", "big": "1,680", "unit": "명", "desc": "7일 중 5회 기록"}, {"label": "STEP 5 · 결제", "big": "1,000", "unit": "명", "desc": "유료 전환 60%", "tone": "dark"}],
          "footnote": "전환율은 4주 검증 목표 지표 기준 자체 가정이며 1차 결과에 따라 조정합니다."},
      "growth_phases": {"kicker": "10 · GROWTH STRATEGY", "title": "개인 구독에서 채널 계약으로, **기록에서 근거**로", "lead": "성장은 광고비가 아니라 데이터 축적의 함수입니다.",
          "phases": [{"label": "PHASE 1 · 0~12개월", "title": "습관을 증명한다", "desc": "유료 1,000명, 월 이탈 6% 이하.", "kpi": "7일 기록 70% · 연결률 60%"}, {"label": "PHASE 2 · 13~24개월", "title": "채널로 확장한다", "desc": "보험사·검진기관 B2B2C 계약.", "kpi": "계약 3건 · 유료 3만 명"}, {"label": "PHASE 3 · 25개월~", "title": "근거를 자산화한다", "desc": "HbA1c 개선 임상 검증.", "kpi": "논문 1편 · 유료 10만 명"}],
          "flywheel": ["사진을 찍는다", "인식률이 오른다", "반응 곡선이 정교해진다", "이탈이 줄고 LTV가 는다"],
          "expansion": "당뇨 전단계 1,409만 명, 임신성 당뇨, 만성신장질환 — 엔진은 그대로, 가이드 규칙만 교체."},

@pytest.mark.parametrize("layout", GROUP2)
def test_group2_builds_without_warnings(layout, out_dir):
    p, spec = _spec_for([layout], out_dir)
    assert validate.validate_obj(spec, "deck_spec") == []
    rep = build_deck.build(p, out_dir / f"{layout}.pptx")
    assert rep["warnings"] == [], rep["warnings"]

def test_kpi_chart_has_native_chart(out_dir):
    p, _ = _spec_for(["kpi_chart"], out_dir); build_deck.build(p, out_dir / "k.pptx")
    prs = Presentation(str(out_dir / "k.pptx"))
    assert any(sh.has_chart for sh in prs.slides[0].shapes)
```

- [ ] **Step 2: 실행해 실패 확인** — Run: `PYTHONUTF8=1 python -m pytest tests/test_layouts.py -q -k "group2 or kpi"` → FAIL

- [ ] **Step 3: 구현** — `L/l_market_bm.py`

```python
# -*- coding: utf-8 -*-
from pptx.util import Inches, Pt
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION
from . import register
from .base import rgb, _set_font
from .l_problem import _chrome, _TONE
import design_system as ds

def _big_with_unit(cv, x, y, w, big, unit, size, color, align="left", slot=""):
    """큰 숫자 + 작은 단위 run (market_tam 계단 박스용)."""
    tb = cv.text(x, y, w, size / 72 * 1.3, big, size, color, bold=True, align=align, max_lines=1, slot=slot)
    if unit:
        r = tb.text_frame.paragraphs[0].add_run(); r.text = unit; _set_font(r, ds.FONT, ds.SZ["unit"], True, color)
    return tb

@register("traction_plan")
def traction_plan(cv, s, slide):
    _chrome(cv, s, slide)
    weeks = s.get("weeks") or []; y = ds.BODY_Y
    cv.label(ds.MX, y, ds.CW, "행동 기반 검증 설계", color=cv.accent)
    if weeks:
        w = ds.col_w(len(weeks)); h = 2.35
        for i, wk in enumerate(weeks):
            x = ds.MX + i * (w + ds.GAP); dark = wk.get("tone") == "dark"; tone = list(_TONE.values())[i % 4]
            cv.card(x, y + 0.4, w, h, style="dark" if dark else "plain", top_bar=tone)
            ink, sub = (ds.C["white"], ds.C["sub_dark"]) if dark else (cv.ink, cv.sub)
            cv.label(x + 0.35, y + 0.75, w - 0.7, wk.get("label", ""), color=ds.C["teal"] if dark else tone)
            cv.text(x + 0.35, y + 1.1, w - 0.7, 0.55, wk.get("big", ""), 24, ink, bold=True, max_lines=1, slot="weeks.big")
            cv.text(x + 0.35, y + 1.7, w - 0.7, 1.0, wk.get("desc", ""), ds.SZ["body_sm"], sub, line_spacing=1.4, max_lines=3, slot="weeks.desc")
        y += h + 0.75
    rows = (s.get("table") or {}).get("rows") or []
    lw = 11.0
    if rows:
        cv.label(ds.MX, y, lw, "진행 판단 기준 (Go / Pivot Signal)", color=cv.accent)
        n_r = len(rows) + 1; th = min(0.6, (ds.BODY_B - y - 0.5) / n_r)
        tbl = cv.s.shapes.add_table(n_r, 3, Inches(ds.MX), Inches(y + 0.4), Inches(lw), Inches(th * n_r)).table
        tbl.columns[0].width = Inches(3.6); tbl.columns[1].width = Inches(2.0); tbl.columns[2].width = Inches(lw - 5.6)
        from .base import _set_font
        def cell(r, c, t, color, bold=False, fill=None):
            ce = tbl.cell(r, c); ce.text = ""; ce.margin_top = ce.margin_bottom = Inches(0.05); ce.fill.solid(); ce.fill.fore_color.rgb = rgb(fill or ("1A2130" if cv.bg == "dark" else "FFFFFF"))
            run = ce.text_frame.paragraphs[0].add_run(); run.text = t; _set_font(run, ds.FONT, ds.SZ["body_sm"], bold, color)
        for j, hd in enumerate(["지표", "목표", "측정 방법 — 말이 아닌 행동"]): cell(0, j, hd, ds.C["amber"] if j == 0 else ds.C["white"], True, fill=ds.BG["dark"])
        for i, r in enumerate(rows, 1):
            cell(i, 0, r.get("metric", ""), cv.ink, True); cell(i, 1, r.get("target", ""), cv.accent, True); cell(i, 2, r.get("method", ""), cv.sub)
    side = s.get("side") or {}; sx = ds.MX + lw + 0.35; sw = ds.CW - lw - 0.35
    if side:
        cv.card(sx, y + 0.4, sw, 1.9); cv.label(sx + 0.35, y + 0.65, sw - 0.7, side.get("title", ""), color=cv.accent)
        cv.text(sx + 0.35, y + 1.05, sw - 0.7, 1.1, side.get("body", ""), ds.SZ["body_sm"], cv.sub, line_spacing=1.4, max_lines=3, slot="side.body")
    if s.get("insight"):
        iy = y + 2.5; ih = ds.BODY_B - iy
        if ih > 0.8:
            cv.card(sx, iy, sw, ih, style="accent"); cv.label(sx + 0.35, iy + 0.25, sw - 0.7, "이미 확인된 것", color="FFFFFF")
            cv.text(sx + 0.35, iy + 0.6, sw - 0.7, ih - 0.75, s["insight"], ds.SZ["body"], ds.C["white"], bold=True, line_spacing=1.35, max_lines=3, slot="insight")

@register("kpi_chart")
def kpi_chart(cv, s, slide):
    _chrome(cv, s, slide)
    ch = s.get("chart") or {}; cats = ch.get("categories") or []; series = [x for x in (ch.get("series") or []) if x.get("values")]
    cw = 11.0; y = ds.BODY_Y; h = ds.BODY_B - y - 0.7
    if cats and series:
        cd = CategoryChartData(); cd.categories = cats
        for se in series: cd.add_series(se["name"], se["values"])
        ctype = {"column": XL_CHART_TYPE.COLUMN_CLUSTERED, "bar": XL_CHART_TYPE.BAR_CLUSTERED, "line": XL_CHART_TYPE.LINE_MARKERS}.get(ch.get("type", "column"), XL_CHART_TYPE.COLUMN_CLUSTERED)
        cv.card(ds.MX, y, cw, h)
        gf = cv.s.shapes.add_chart(ctype, Inches(ds.MX + 0.3), Inches(y + 0.3), Inches(cw - 0.6), Inches(h - 0.6), cd); chart = gf.chart
        chart.has_legend = len(series) > 1; chart.has_title = False
        chart.font.name = ds.FONT; chart.font.size = Pt(12); chart.font.color.rgb = rgb(cv.sub)
        plot = chart.plots[0]; plot.has_data_labels = True; plot.data_labels.font.size = Pt(13); plot.data_labels.font.bold = True; plot.data_labels.font.color.rgb = rgb(cv.ink)
        plot.data_labels.number_format = '#,##0'; plot.data_labels.number_format_is_linked = False
        if ctype != XL_CHART_TYPE.LINE_MARKERS: plot.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END; plot.gap_width = 80
        for k, se in enumerate(plot.series):
            se.format.fill.solid(); se.format.fill.fore_color.rgb = rgb([cv.accent, ds.C["amber"], ds.C["teal"]][k % 3])
        chart.value_axis.has_major_gridlines = False; chart.value_axis.visible = False
        chart.category_axis.format.line.color.rgb = rgb(ds.C["card_border"]); chart.category_axis.tick_labels.font.size = Pt(12)
    else:
        cv.ctx.warnings.append({"slide": cv.ctx.current_no, "slot": "chart", "text": "값 없는 차트 — 카드만 표시", "lines": 0, "max": 0})
    kpis = s.get("kpis") or []; kx = ds.MX + cw + 0.35; kw = ds.CW - cw - 0.35; kh = (h - 0.2 * 2) / 3
    for i, k in enumerate(kpis[:3]):
        ky = y + i * (kh + 0.2); cv.card(kx, ky, kw, kh); cv.rect(kx, ky, 0.05, kh, fill=list(_TONE.values())[i % 3])
        cv.stat(kx + 0.35, ky + 0.3, kw - 0.6, k.get("big", ""), label=k.get("label", ""), source=k.get("source"), big_size=ds.SZ["big_md"], color=cv.accent if i == 0 else cv.ink)
    if s.get("note"): cv.text(ds.MX, ds.BODY_B - 0.45, ds.CW, 0.35, s["note"], ds.SZ["small"], cv.muted, max_lines=1, slot="note")

@register("bm_pricing")
def bm_pricing(cv, s, slide):
    _chrome(cv, s, slide)
    tiers = s.get("tiers") or []; y = ds.BODY_Y; h = 3.7
    if tiers:
        w = ds.col_w(len(tiers))
        for i, t in enumerate(tiers):
            x = ds.MX + i * (w + ds.GAP); hi = t.get("highlight")
            cv.card(x, y, w, h, style="accent" if hi else ("plain" if cv.bg == "cream" else "plain"))
            if not hi and i == len(tiers) - 1 and cv.bg == "dark": cv.rect(x, y, w, h, fill=None, line=ds.C["teal"], line_alpha=60, radius=True)
            ink, sub = (ds.C["white"], ds.C["white"]) if hi else (cv.ink, cv.sub)
            cv.label(x + 0.4, y + 0.35, w - 0.8, t.get("label", ""), color=ds.C["white"] if hi else (ds.C["teal"] if i == len(tiers) - 1 else cv.accent))
            cv.text(x + 0.4, y + 0.7, w - 0.8, 0.75, t.get("price", ""), 34, ink, bold=True, max_lines=1, slot="tiers.price")
            cv.text(x + 0.4, y + 1.45, w - 0.8, 0.35, t.get("sub", ""), ds.SZ["body_sm"], sub, max_lines=1, slot="tiers.sub")
            cv.body_bullets(x + 0.4, y + 1.9, w - 0.8, 1.1, t.get("bullets") or [], size=ds.SZ["body_sm"], color=ink if hi else cv.ink)
            cv.text(x + 0.4, y + 3.0, w - 0.8, 0.6, t.get("note", ""), ds.SZ["small"], sub, bold=hi, line_spacing=1.3, max_lines=2, slot="tiers.note")
        y += h + 0.35
    ue = s.get("unit_econ") or []
    lw = 11.0
    if ue:
        cv.label(ds.MX, y, lw, "유닛 이코노믹스 가정", color=ds.C["amber"])
        uh = ds.BODY_B - y - 0.45; cv.card(ds.MX, y + 0.4, lw, uh); uw = (lw - 0.8) / len(ue)
        for i, u in enumerate(ue):
            ux = ds.MX + 0.4 + i * uw
            cv.label(ux, y + 0.7, uw - 0.2, u.get("label", ""), color=[cv.ink, cv.ink, ds.C["teal"], ds.C["amber"]][i % 4] if i >= 2 else cv.sub)
            cv.text(ux, y + 1.05, uw - 0.2, 0.55, u.get("big", ""), 24, [cv.ink, cv.ink, ds.C["teal"], ds.C["amber"]][i % 4], bold=True, max_lines=1, slot="unit_econ.big")
            cv.text(ux, y + 1.6, uw - 0.2, 0.35, u.get("sub", ""), ds.SZ["small"], cv.muted, max_lines=1, slot="unit_econ.sub")
    if s.get("evidence_note"):
        ex = ds.MX + lw + 0.35; ew = ds.CW - lw - 0.35
        cv.rect(ex, y + 0.4, ew, ds.BODY_B - y - 0.45, fill=None, line=ds.C["amber"], line_alpha=70, radius=True)
        cv.label(ex + 0.35, y + 0.7, ew - 0.7, "지불 의향 근거", color=ds.C["amber"])
        cv.text(ex + 0.35, y + 1.05, ew - 0.7, ds.BODY_B - y - 1.2, s["evidence_note"], ds.SZ["body_sm"], cv.sub, line_spacing=1.4, max_lines=4, slot="evidence_note")

@register("market_tam")
def market_tam(cv, s, slide):
    _chrome(cv, s, slide, lead_w=11.5)
    lw = 11.0; y = ds.BODY_Y
    boxes = [("tam", 0.0, "tint"), ("sam", 0.75, "plain"), ("som", 1.5, "dark")]
    bh = 1.45
    for i, (key, indent, style) in enumerate(boxes):
        b = s.get(key) or {}; x = ds.MX + indent; w = lw - indent * 2; by = y + i * (bh + 0.2)
        cv.card(x, by, w, bh, style=style if cv.bg == "cream" else ("dark" if key == "som" else "plain"))
        dark = style == "dark" or cv.bg == "dark"; ink, sub, mut = (ds.C["white"], ds.C["sub_dark"], ds.C["muted_dark"]) if dark else (cv.ink, cv.sub, cv.muted)
        cv.label(x + 0.4, by + 0.25, w - 4.4, b.get("label", ""), color=cv.accent if not dark else ds.C["amber"])
        cv.text(x + 0.4, by + 0.6, w - 4.4, 0.75, b.get("desc", ""), ds.SZ["body"], ink, bold=True, line_spacing=1.3, max_lines=2, slot=f"{key}.desc")
        _big_with_unit(cv, x + w - 4.0, by + 0.2, 3.6, b.get("big", ""), b.get("unit", ""), ds.SZ["big_md"], ink, align="right", slot=f"{key}.big")
        cv.text(x + w - 4.0, by + 0.95, 3.6, 0.35, b.get("calc", ""), ds.SZ["small"], mut, align="right", max_lines=1, slot=f"{key}.calc")
    if s.get("sanity_note"):
        sy = y + 3 * (bh + 0.2) + 0.1; sh = ds.BODY_B - sy
        cv.rect(ds.MX, sy, lw, sh, fill=("E8F3EE" if cv.bg == "cream" else "FFFFFF"), alpha=(None if cv.bg == "cream" else 6), line=ds.C["teal_deep"], line_alpha=50, radius=True)
        cv.text(ds.MX + 0.4, sy + 0.15, lw - 0.8, sh - 0.3, "**기준 검증** — " + s["sanity_note"], ds.SZ["body"], cv.ink, bold=False, anchor="middle", line_spacing=1.4, max_lines=3, slot="sanity_note")
    st = s.get("side_stats") or []; sx = ds.MX + lw + 0.6; sw = ds.CW - lw - 0.6
    cv.label(sx, y, sw, "시장은 커지는 중", color=cv.accent)
    sh_ = (ds.BODY_B - y - 0.45 - 0.2 * 2) / 3
    for i, it in enumerate(st[:3]):
        iy = y + 0.45 + i * (sh_ + 0.2); cv.card(sx, iy, sw, sh_)
        cv.label(sx + 0.35, iy + 0.25, sw - 0.6, it.get("label", ""), color=[cv.accent, ds.C["amber"], cv.accent][i % 3])
        cv.text(sx + 0.35, iy + 0.6, sw - 0.6, 0.6, it.get("big", ""), 26, cv.ink, bold=True, max_lines=1, slot="side_stats.big")
        cv.text(sx + 0.35, iy + 1.2, sw - 0.6, 0.35, it.get("sub", ""), ds.SZ["body_sm"], cv.sub, max_lines=1, slot="side_stats.sub")
        cv.text(sx + 0.35, iy + sh_ - 0.4, sw - 0.6, 0.3, it.get("source", ""), ds.SZ["source"], cv.muted, max_lines=1, slot="side_stats.source")

@register("gtm_funnel")
def gtm_funnel(cv, s, slide):
    _chrome(cv, s, slide)
    bh = s.get("beachhead") or {}; y = ds.BODY_Y; lw = 8.6; h = 3.3
    cv.card(ds.MX, y, lw, h, style="dark"); cv.label(ds.MX + 0.4, y + 0.35, lw - 0.8, "BEACHHEAD · 교두보 고객", color=ds.C["teal"])
    cv.text(ds.MX + 0.4, y + 0.75, lw - 0.8, 1.2, bh.get("title", ""), 26, ds.C["white"], bold=True, line_spacing=1.25, max_lines=2, slot="beachhead.title")
    cv.rect(ds.MX + 0.4, y + 2.0, lw - 0.8, 0.01, fill="FFFFFF", alpha=15)
    half = (lw - 1.0) / 2
    cv.text(ds.MX + 0.4, y + 2.1, half, 0.3, "왜 이 고객군인가", ds.SZ["body_sm"], ds.C["teal"], bold=True, max_lines=1)
    cv.text(ds.MX + 0.4, y + 2.4, half, 0.85, bh.get("why", ""), ds.SZ["small"], ds.C["sub_dark"], line_spacing=1.35, max_lines=3, slot="beachhead.why")
    cv.text(ds.MX + 0.6 + half, y + 2.1, half, 0.3, "초기 제외 대상", ds.SZ["body_sm"], ds.C["amber"], bold=True, max_lines=1)
    cv.text(ds.MX + 0.6 + half, y + 2.4, half, 0.85, bh.get("exclude", ""), ds.SZ["small"], ds.C["sub_dark"], line_spacing=1.35, max_lines=3, slot="beachhead.exclude")
    chs = s.get("channels") or []; cx = ds.MX + lw + 0.35; cw = ds.CW - lw - 0.35
    cv.card(cx, y, cw, h); cv.label(cx + 0.4, y + 0.35, cw - 0.8, "채널 우선순위 — 신뢰가 CAC를 결정합니다")
    for i, c in enumerate(chs[:3]):
        cy = y + 0.8 + i * 0.8
        cv.text(cx + 0.4, cy, cw - 0.8, 0.32, c.get("title", ""), ds.SZ["body"], cv.ink, bold=True, max_lines=1, slot="channels.title")
        cv.text(cx + 0.4, cy + 0.32, cw - 0.8, 0.45, c.get("desc", ""), ds.SZ["small"], cv.sub, max_lines=2, slot="channels.desc")
    fun = s.get("funnel") or []; fy = y + h + 0.4
    cv.label(ds.MX, fy, ds.CW, "확보 퍼널", color=cv.accent)
    if fun:
        fw = ds.col_w(len(fun)); fh = ds.BODY_B - fy - 0.85
        for i, f in enumerate(fun):
            fx = ds.MX + i * (fw + ds.GAP); dark = f.get("tone") == "dark"
            cv.card(fx, fy + 0.4, fw, fh, style="dark" if dark else "plain", top_bar=list(_TONE.values())[i % 4])
            ink, sub = (ds.C["white"], ds.C["sub_dark"]) if dark else (cv.ink, cv.sub)
            cv.label(fx + 0.3, fy + 0.7, fw - 0.6, f.get("label", ""), color=ds.C["accent_dark"] if dark else cv.accent)
            cv.stat(fx + 0.3, fy + 1.05, fw - 0.6, f.get("big", ""), f.get("unit", ""), big_size=ds.SZ["big_sm"], color=ink)
            cv.text(fx + 0.3, fy + 1.75, fw - 0.6, fh - 1.5, f.get("desc", ""), ds.SZ["small"], sub, max_lines=2, slot="funnel.desc")
    if s.get("footnote"): cv.text(ds.MX, ds.BODY_B - 0.35, ds.CW, 0.3, s["footnote"], ds.SZ["small"], cv.muted, max_lines=1, slot="footnote")

@register("growth_phases")
def growth_phases(cv, s, slide):
    _chrome(cv, s, slide)
    ph = s.get("phases") or []; y = ds.BODY_Y; h = 3.5
    if ph:
        w = ds.col_w(len(ph))
        for i, p in enumerate(ph):
            x = ds.MX + i * (w + ds.GAP); cv.card(x, y, w, h, top_bar=list(_TONE.values())[i % 3])
            cv.label(x + 0.4, y + 0.35, w - 0.8, p.get("label", ""), color=list(_TONE.values())[i % 3])
            cv.text(x + 0.4, y + 0.75, w - 0.8, 0.55, p.get("title", ""), 24, cv.ink, bold=True, max_lines=1, slot="phases.title")
            cv.text(x + 0.4, y + 1.35, w - 0.8, 1.2, p.get("desc", ""), ds.SZ["body"], cv.sub, line_spacing=1.4, max_lines=3, slot="phases.desc")
            cv.rect(x + 0.4, y + 2.6, w - 0.8, 0.01, fill=ds.C["card_border"])
            cv.text(x + 0.4, y + 2.7, w - 0.8, 0.3, "핵심 지표", ds.SZ["small"], ds.C["teal_deep"], bold=True, max_lines=1)
            cv.text(x + 0.4, y + 3.0, w - 0.8, 0.4, p.get("kpi", ""), ds.SZ["body_sm"], cv.ink, bold=True, max_lines=1, slot="phases.kpi")
        y += h + 0.4
    fw_items = s.get("flywheel") or []; lw = 11.0
    if fw_items:
        cv.card(ds.MX, y, lw, ds.BODY_B - y, style="dark" if cv.bg == "cream" else "plain"); cv.label(ds.MX + 0.4, y + 0.3, lw, "데이터 플라이휠", color=ds.C["teal"])
        n = len(fw_items); iw = (lw - 0.8) / n
        for i, it in enumerate(fw_items):
            cv.text(ds.MX + 0.4 + i * iw, y + 0.75, iw - 0.5, ds.BODY_B - y - 0.9, it, ds.SZ["body"], ds.C["white"], bold=True, anchor="middle", line_spacing=1.3, max_lines=3, slot="flywheel")
            if i < n - 1: cv.text(ds.MX + 0.4 + (i + 1) * iw - 0.5, y + 0.75, 0.5, ds.BODY_B - y - 0.9, "→", 22, ds.C["amber"], bold=True, align="center", anchor="middle")
    if s.get("expansion"):
        ex = ds.MX + lw + 0.35; ew = ds.CW - lw - 0.35
        cv.card(ex, y, ew, ds.BODY_B - y, style="tint" if cv.bg == "cream" else "plain"); cv.label(ex + 0.35, y + 0.3, ew - 0.7, "확장 옵션 · 같은 엔진, 다른 고객")
        cv.text(ex + 0.35, y + 0.7, ew - 0.7, ds.BODY_B - y - 0.85, s["expansion"], ds.SZ["body_sm"], cv.sub, line_spacing=1.4, max_lines=4, slot="expansion")
```

`L/__init__.py`에 `from . import l_market_bm  # noqa` 추가. (`market_tam`의 `unit`은 파일 상단의 `_big_with_unit` 헬퍼가 15.75pt 단위 run으로 덧붙인다.)

- [ ] **Step 4: 테스트 통과** — Run: `PYTHONUTF8=1 python -m pytest tests/test_layouts.py -q` → 전부 통과(16)
- [ ] **Step 5: 육안 확인** — GROUP2 6장 빌드 → PNG 렌더 → Read로 확인. 특히 `market_tam` 계단(들여쓰기 0/0.75/1.5in)·`gtm_funnel` 5열 카드 넘침.
- [ ] **Step 6: 커밋**

```bash
git add -A && git -c user.name="Lee Dong-Geon" -c user.email="leedg.brian@gmail.com" commit -m "feat(layouts): 성과·수익·시장·진입·성장 레이아웃 6종(네이티브 차트 포함)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 12: 레이아웃 그룹 3 — 마일스톤·팀·비전·부록 (`l_plan_team.py`) + `spec.example.json`

**Files:**
- Create: `L/l_plan_team.py`(milestone_gates · team_cards · vision_close · appendix_qa · evidence_capture), `S/assets/spec.example.json`, `T/test_example_spec.py`
- Modify: `L/__init__.py`, `T/test_layouts.py`(GROUP3 + sample_slots)

**Interfaces:** `spec.example.json`은 셀아이(가상) 22장 — 레이아웃 22종을 각 1장씩, 이미지 없이 빌드 가능(`panel_image: null`). 에이전트 `ir-designer`가 스펙 작성 예시로 읽는다.

- [ ] **Step 1: 테스트 확장** — `T/test_layouts.py`에 GROUP3 추가, `T/test_example_spec.py` 작성

```python
# test_layouts.py 추가
GROUP3 = ["milestone_gates", "team_cards", "vision_close", "appendix_qa", "evidence_capture"]
# sample_slots S에 추가:
      "milestone_gates": {"kicker": "11 · MILESTONE", "title": "24개월, **4개의 관문**", "lead": "각 구간은 다음 단계로 넘어갈 자격을 증명하는 지표 하나로 판정합니다.",
          "gates": [{"label": "M1 · 0~3개월", "title": "문제 검증", "bullets": ["인터뷰 20명 이상", "7일 기록 실험", "시제품 사용성 테스트", "안전 문구 전문가 검토"], "gate": "예약금 결제 기반 사용 의향 50%"},
                    {"label": "M2 · 4~9개월", "title": "MVP 출시", "bullets": ["인식 모델 v1 학습", "iOS·Android 출시", "유료 결제 오픈", "교육센터 파일럿 3곳"], "gate": "유료 1,000명 · 월 이탈 6% 이하"},
                    {"label": "M3 · 10~18개월", "title": "채널 확장", "bullets": ["CGM 다기종 연동", "의료진용 리포트", "보험사·검진기관 계약", "반응 곡선 고도화"], "gate": "B2B2C 계약 3건 · 유료 3만 명"},
                    {"label": "M4 · 19~24개월", "title": "근거 확보", "bullets": ["HbA1c 개선 연구 착수", "학회 발표·논문 투고", "의료기기 트랙 검토", "시리즈 A 라운드"], "gate": "임상 근거 1편 · 유료 10만 명", "tone": "teal"}],
          "ask_band": {"amount": "5,000만 원", "runway": "12개월 런웨이", "use_of_funds": "AI 인식 모델 개발·데이터 라이선스 45% · 앱 개발 및 인프라 30% · 고객 검증·파일럿 15% · 법무·규제 자문 10%"}},
      "team_cards": {"kicker": "12 · TEAM", "title": "기술·임상·현장을 **한 팀 안에**", "lead": "세 역량이 모두 필요하고, 하나라도 비면 제품이 성립하지 않습니다.",
          "members": [{"role": "FOUNDER · CEO", "title": "제품 · 고객 검증", "desc": "고객 인터뷰 20건과 4주 행동 검증을 직접 설계·실행합니다.", "kpi": "문제 공감률 · 유료 전환률 · 이탈률", "tone": "dark"},
                      {"role": "AI LEAD · 채용 진행", "title": "음식 인식 모델", "desc": "AI Hub 공공 데이터(53.7만 장)로 인식 모델을 학습합니다.", "kpi": "Top-3 인식 정확도"},
                      {"role": "PRODUCT ENGINEER · 채용 진행", "title": "앱 · 데이터 파이프라인", "desc": "3초 촬영과 2탭 보정을 실제로 구현합니다.", "kpi": "첫 기록 완료율 70%"}],
          "advisors": [{"title": "내분비내과 전문의", "desc": "분석 결과 표현의 의학적 타당성 검토"}, {"title": "당뇨병 교육 간호사 · 임상영양사", "desc": "행동 가이드 문구의 현장 적합성 검증"}, {"title": "의료기기 규제 자문", "desc": "비의료기기 범위 유지 조건 설계"}],
          "principle": {"title": "인원을 늘리기 전에\n지표를 먼저\n통과합니다", "desc": "시드 12개월은 3인 코어 팀으로 운영합니다.", "list": ["임상 검증 담당", "B2B2C 사업개발", "데이터 엔지니어"]},
          "footnote": "※ AI Lead·Product Engineer는 시드 자금 집행과 함께 채용 예정."},
      "vision_close": {"kicker": "13 · VISION", "headline": "식사 관리가\n**참는 일**이 아니라\n**아는 일**이 되도록", "body": "당뇨 관리는 오랫동안 '금지 목록'이었습니다.\n글루코픽은 그 자리를 데이터로 대체합니다.",
          "one_liner": "파스타는 CGM 착용자, 닥터다이어리는 커뮤니티,\n**우리는 외식하는 당뇨인 전용**입니다.",
          "cards": [{"label": "3년 후", "big": "유료 10만 명", "sub": "연 환산 매출 약 180억 원"}, {"label": "증명하려는 것", "big": "HbA1c 개선", "sub": "주 5일 기록 시 1.2%p 추가 감소", "tone": "teal"}, {"label": "궁극적으로", "big": "1,939만 명의\n혈당 관리 인프라로", "sub": "전단계·임신성·만성신장질환까지", "tone": "accent"}],
          "brand": "GlucoPic", "tagline": "사진 한 장이 오늘의 혈당을 바꿉니다", "ask_line": "Seed 5,000만 원 · 12개월 런웨이", "panel_image": None},
      "appendix_qa": {"kicker": "APPENDIX · Q&A", "title": "예상 질문과 답", "qa": [{"q": "경쟁사 대비 기술적 해자는?", "a": "한식 사진 × 실제 식후 혈당 쌍 데이터. 사용자 1만 명 기준 연 730만 건 축적."}, {"q": "의료기기 규제는?", "a": "예측·진단을 하지 않는 생활 관리 참고 정보로 출시. 임상 근거 확보 후 트랙 검토."},
                     {"q": "CAC는 얼마인가?", "a": "[확보 필요] 1차 검증 후 실측. 상한 7.5만 원 가정."}, {"q": "왜 지금인가?", "a": "CGM 급여 확대(2024.12)·만성질환관리 본사업 전환(2024.09)."}]},
      "evidence_capture": {"kicker": "APPENDIX · EVIDENCE", "title": "대한당뇨병학회 Diabetes Fact Sheet 2024 — 조절률 32.4%", "image": None, "caption": "원문 캡처 — 인지율·치료율·조절률 표", "source": "대한당뇨병학회 「Diabetes Fact Sheet 2024」 p.12 · 수집 2026-09-11 · URL은 증거 원장 참조"},

@pytest.mark.parametrize("layout", GROUP3)
def test_group3_builds_without_warnings(layout, out_dir):
    p, spec = _spec_for([layout], out_dir)
    assert validate.validate_obj(spec, "deck_spec") == []
    rep = build_deck.build(p, out_dir / f"{layout}.pptx")
    # evidence_capture는 이미지 None → '이미지 확보 필요' 경고 1건 허용
    assert [w for w in rep["warnings"] if w["slot"] != "image"] == [], rep["warnings"]
```

`T/test_example_spec.py`
```python
# -*- coding: utf-8 -*-
import json
from pptx import Presentation
import build_deck, validate
from layouts import LAYOUTS

def test_example_spec_covers_all_layouts_and_builds(assets_dir, out_dir):
    spec = json.loads((assets_dir / "spec.example.json").read_text(encoding="utf-8"))
    assert validate.validate_obj(spec, "deck_spec") == []
    used = [s["layout"] for s in spec["slides"]]
    assert set(used) == set(LAYOUTS) and len(LAYOUTS) == 22
    rep = build_deck.build(assets_dir / "spec.example.json", out_dir / "example.pptx")
    assert [w for w in rep["warnings"] if w["slot"] != "image"] == [], rep["warnings"]
    prs = Presentation(str(out_dir / "example.pptx"))
    assert len(prs.slides) == 22 and all(s.notes_slide.notes_text_frame.text for s in prs.slides)
```

- [ ] **Step 2: 실행해 실패 확인** — Run: `PYTHONUTF8=1 python -m pytest tests/test_layouts.py tests/test_example_spec.py -q` → FAIL

- [ ] **Step 3: 구현** — `L/l_plan_team.py`

```python
# -*- coding: utf-8 -*-
from . import register
from .l_problem import _chrome, _TONE
import design_system as ds

@register("milestone_gates")
def milestone_gates(cv, s, slide):
    _chrome(cv, s, slide)
    gates = s.get("gates") or []; y = ds.BODY_Y
    if gates:
        n = len(gates); w = ds.col_w(n)
        cv.rect(ds.MX, y + 0.1, ds.CW, 0.03, fill=ds.C["amber"])
        for i in range(n):
            cx = ds.MX + i * (w + ds.GAP) + 0.2
            cv.rect(cx, y + 0.02, 0.2, 0.2, fill=list(_TONE.values())[i % 4] if gates[i].get("tone") != "teal" else ds.C["teal"], radius=0.5)
        gy = y + 0.55; gh = ds.BODY_B - gy - 1.65
        for i, g in enumerate(gates):
            x = ds.MX + i * (w + ds.GAP); teal = g.get("tone") == "teal"; tone = ds.C["teal"] if teal else list(_TONE.values())[i % 3]
            cv.card(x, gy, w, gh); 
            if teal: cv.rect(x, gy, w, gh, fill=None, line=ds.C["teal"], line_alpha=70, radius=True)
            cv.label(x + 0.35, gy + 0.3, w - 0.7, g.get("label", ""), color=tone)
            cv.text(x + 0.35, gy + 0.65, w - 0.7, 0.5, g.get("title", ""), ds.SZ["card_title"], cv.ink, bold=True, max_lines=1, slot="gates.title")
            cv.body_bullets(x + 0.35, gy + 1.2, w - 0.7, gh - 2.35, g.get("bullets") or [], size=ds.SZ["body_sm"])
            by = gy + gh - 1.05; cv.rect(x + 0.35, by, w - 0.7, 0.85, fill=tone, alpha=18, radius=True); cv.rect(x + 0.35, by, 0.05, 0.85, fill=tone)
            cv.label(x + 0.55, by + 0.1, w - 1.0, "GATE", color=cv.muted)
            cv.text(x + 0.55, by + 0.38, w - 1.0, 0.45, g.get("gate", ""), ds.SZ["body_sm"], cv.ink, bold=True, max_lines=1, slot="gates.gate")
    ask = s.get("ask_band") or {}
    if ask:
        ay = ds.BODY_B - 1.35; cv.card(ds.MX, ay, ds.CW, 1.25, style="accent")
        cv.label(ds.MX + 0.4, ay + 0.25, 5, f"SEED ASK · {ask.get('runway','')}", color="FFFFFF")
        cv.text(ds.MX + 0.4, ay + 0.55, 5, 0.65, ask.get("amount", ""), 34, ds.C["white"], bold=True, max_lines=1, slot="ask_band.amount")
        cv.label(ds.MX + 5.6, ay + 0.25, 10, "자금 사용 계획", color="FFFFFF")
        cv.text(ds.MX + 5.6, ay + 0.6, ds.CW - 6.0, 0.6, ask.get("use_of_funds", ""), ds.SZ["body"], ds.C["white"], bold=True, line_spacing=1.3, max_lines=2, slot="ask_band.use_of_funds")

@register("team_cards")
def team_cards(cv, s, slide):
    _chrome(cv, s, slide)
    mem = s.get("members") or []; y = ds.BODY_Y; lw = 12.9; h = 3.4
    if mem:
        w = ds.col_w(len(mem), lw)
        for i, m in enumerate(mem):
            x = ds.MX + i * (w + ds.GAP); dark = m.get("tone") == "dark"
            cv.card(x, y, w, h, style="dark" if dark else "plain", top_bar=None if dark else list(_TONE.values())[i % 3])
            ink, sub = (ds.C["white"], ds.C["sub_dark"]) if dark else (cv.ink, cv.sub)
            cv.label(x + 0.35, y + 0.35, w - 0.7, m.get("role", ""), color=ds.C["amber"] if dark else list(_TONE.values())[i % 3])
            cv.text(x + 0.35, y + 0.75, w - 0.7, 0.5, m.get("title", ""), ds.SZ["card_title"], ink, bold=True, max_lines=1, slot="members.title")
            cv.text(x + 0.35, y + 1.3, w - 0.7, 1.15, m.get("desc", ""), ds.SZ["body_sm"], sub, line_spacing=1.4, max_lines=3, slot="members.desc")
            cv.text(x + 0.35, y + 2.5, w - 0.7, 0.3, "담당 지표", ds.SZ["small"], ds.C["teal"], bold=True, max_lines=1)
            cv.text(x + 0.35, y + 2.8, w - 0.7, 0.45, m.get("kpi", ""), ds.SZ["body_sm"], sub, max_lines=1, slot="members.kpi")
        y += h + 0.4
    adv = s.get("advisors") or []
    if adv:
        cv.label(ds.MX, y, lw, "자문단 구성 계획 — 안전성이 곧 신뢰입니다", color=cv.accent)
        aw = ds.col_w(len(adv), lw); ah = ds.BODY_B - y - 0.95
        for i, a in enumerate(adv):
            x = ds.MX + i * (aw + ds.GAP); cv.card(x, y + 0.4, aw, ah)
            cv.text(x + 0.35, y + 0.7, aw - 0.7, 0.45, a.get("title", ""), ds.SZ["body"], cv.ink, bold=True, max_lines=1, slot="advisors.title")
            cv.text(x + 0.35, y + 1.15, aw - 0.7, ah - 0.9, a.get("desc", ""), ds.SZ["body_sm"], cv.sub, line_spacing=1.4, max_lines=3, slot="advisors.desc")
    pr = s.get("principle") or {}; px = ds.MX + lw + 0.35; pw = ds.CW - lw - 0.35
    cv.card(px, ds.BODY_Y, pw, ds.BODY_B - ds.BODY_Y - 0.55, style="accent"); cv.label(px + 0.4, ds.BODY_Y + 0.35, pw - 0.8, "채용 원칙", color="FFFFFF")
    cv.text(px + 0.4, ds.BODY_Y + 0.75, pw - 0.8, 1.9, pr.get("title", ""), 27, ds.C["white"], bold=True, line_spacing=1.2, max_lines=3, slot="principle.title")
    cv.text(px + 0.4, ds.BODY_Y + 2.75, pw - 0.8, 1.3, pr.get("desc", ""), ds.SZ["body_sm"], ds.C["white"], line_spacing=1.4, max_lines=4, slot="principle.desc")
    cv.rect(px + 0.4, ds.BODY_Y + 4.15, pw - 0.8, 0.01, fill="FFFFFF", alpha=35)
    cv.label(px + 0.4, ds.BODY_Y + 4.3, pw - 0.8, "M3 이후 충원 계획", color="FFFFFF")
    cv.body_bullets(px + 0.4, ds.BODY_Y + 4.65, pw - 0.8, 1.2, pr.get("list") or [], size=ds.SZ["body_sm"], color=ds.C["white"])
    if s.get("footnote"): cv.text(ds.MX, ds.BODY_B - 0.4, lw, 0.35, s["footnote"], ds.SZ["small"], cv.muted, max_lines=1, slot="footnote")

@register("vision_close")
def vision_close(cv, s, slide):
    cv.panel_image(s.get("panel_image"), strength=0.6, x=11.6, w=8.4)
    cv.rect(ds.MX, 1.2, 0.05, 3.2, fill=cv.accent)
    cv.text(ds.MX + 0.4, 1.25, 9.5, 0.35, s.get("kicker", ""), ds.SZ["kicker"], ds.C["amber"], bold=True, spacing=0.25, max_lines=1, slot="kicker")
    cv.text(ds.MX + 0.4, 1.7, 9.5, 3.0, s.get("headline", ""), 54, ds.C["white"], bold=True, line_spacing=1.12, max_lines=3, slot="headline")
    cv.text(ds.MX + 0.4, 4.9, 9.6, 1.6, s.get("body", ""), ds.SZ["lead"], ds.C["sub_dark"], line_spacing=1.45, max_lines=3, slot="body")
    cv.rect(ds.MX + 0.4, 6.75, 9.6, 0.01, fill="FFFFFF", alpha=20)
    cv.label(ds.MX + 0.4, 6.95, 6, "THE ONE-LINER", color=ds.C["amber"])
    cv.text(ds.MX + 0.4, 7.35, 9.6, 1.4, s.get("one_liner", ""), 27, ds.C["white"], bold=True, line_spacing=1.25, max_lines=2, slot="one_liner")
    cards = s.get("cards") or []; cx = 12.6; cw = 6.4; ch = 1.95
    for i, c in enumerate(cards[:3]):
        cy = 2.0 + i * (ch + 0.25); acc = c.get("tone") == "accent"
        cv.rect(cx, cy, cw, ch, fill=ds.C["accent"] if acc else ds.BG["dark"], alpha=None if acc else 65, line=None if acc else "FFFFFF", line_alpha=None if acc else 12, radius=True)
        cv.label(cx + 0.4, cy + 0.25, cw - 0.8, c.get("label", ""), color="FFFFFF" if acc else ds.C["muted_dark"])
        cv.text(cx + 0.4, cy + 0.6, cw - 0.8, 0.85, c.get("big", ""), 26, ds.C["teal"] if c.get("tone") == "teal" else ds.C["white"], bold=True, line_spacing=1.15, max_lines=2, slot="cards.big")
        cv.text(cx + 0.4, cy + ch - 0.55, cw - 0.8, 0.45, c.get("sub", ""), ds.SZ["small"], ds.C["white"] if acc else ds.C["sub_dark"], max_lines=1, slot="cards.sub")
    if s.get("brand"):
        cv.rect(ds.MX + 0.4, 9.7, 3.0, 0.7, fill="FFFFFF", radius=True); cv.text(ds.MX + 0.6, 9.7, 2.6, 0.7, s["brand"], 20, ds.C["ink"], bold=True, anchor="middle", max_lines=1, slot="brand")
    cv.text(ds.MX + 3.8, 9.7, 6.5, 0.7, s.get("tagline", ""), ds.SZ["body"], ds.C["sub_dark"], bold=True, anchor="middle", max_lines=1, slot="tagline")
    cv.text(12.6, 9.7, 6.4, 0.7, s.get("ask_line", ""), ds.SZ["body"], ds.C["amber"], bold=True, align="right", anchor="middle", max_lines=1, slot="ask_line")
    cv.notes(slide.get("notes"))

@register("appendix_qa")
def appendix_qa(cv, s, slide):
    cv.kicker(s.get("kicker", "APPENDIX · Q&A")); cv.title(s.get("title", "예상 질문과 답"), size=ds.SZ["title_sm"], max_lines=1)
    qa = s.get("qa") or []; y = 2.6; h = (ds.BODY_B - y - 0.2 * (len(qa) - 1)) / max(1, len(qa))
    for i, item in enumerate(qa[:4]):
        iy = y + i * (h + 0.2); cv.card(ds.MX, iy, ds.CW, h); cv.rect(ds.MX, iy, 0.05, h, fill=cv.accent)
        cv.text(ds.MX + 0.4, iy + 0.2, 6.0, h - 0.4, f"Q{i+1}. {item.get('q','')}", ds.SZ["body"], cv.ink, bold=True, line_spacing=1.35, anchor="middle", max_lines=3, slot="qa.q")
        cv.text(ds.MX + 6.7, iy + 0.2, ds.CW - 7.1, h - 0.4, item.get("a", ""), ds.SZ["body_sm"], cv.sub, line_spacing=1.4, anchor="middle", max_lines=4, slot="qa.a")
    cv.page_no(slide["no"], cv.ctx.total); cv.notes(slide.get("notes"))

@register("evidence_capture")
def evidence_capture(cv, s, slide):
    cv.kicker(s.get("kicker", "APPENDIX · EVIDENCE")); cv.title(s.get("title", ""), size=ds.SZ["title_sm"], max_lines=2)
    y = 3.0; h = ds.BODY_B - y - 0.9
    cv.card(ds.MX, y, ds.CW, h)
    cv.picture(s.get("image"), ds.MX + 0.3, y + 0.3, ds.CW - 0.6, h - 0.6, cover=False, radius=12)
    cv.text(ds.MX, ds.BODY_B - 0.8, ds.CW, 0.35, s.get("caption", ""), ds.SZ["body_sm"], cv.ink, bold=True, max_lines=1, slot="caption")
    cv.text(ds.MX, ds.BODY_B - 0.45, ds.CW, 0.35, s.get("source", ""), ds.SZ["source"], cv.muted, max_lines=1, slot="source")
    cv.page_no(slide["no"], cv.ctx.total); cv.notes(slide.get("notes"))
```

`L/__init__.py`에 `from . import l_plan_team  # noqa` 추가.

`S/assets/spec.example.json` — 셀아이 22장. 각 장은 `T/test_layouts.py::sample_slots`의 데이터를 **셀아이(이차전지 전극 결함 검사 AI, 가상) 맥락으로 바꿔** 작성한다: 팀명 셀아이, 고객 = 이차전지 전극 코팅 라인 품질 관리자, 제품 = 라인 위 검사 모듈(0.3초 판독), 가격 = 월 300만 원 구독, Ask = Seed 3억 원 12개월. 순서: cover → statement → trend_cards → problem_cascade → problem_grid → alt_table → quadrant → solution_steps → product_screens → tech_moat → mvp_scope → traction_plan → kpi_chart → bm_pricing → market_tam → gtm_funnel → growth_phases → milestone_gates → team_cards → vision_close → appendix_qa → evidence_capture. 모든 장에 `notes`(대본 2~3문장)와 본문 장에 `source_line`("출처: 가상 데이터 · 교육용 예시"). 이미지 슬롯은 모두 `null`. **모든 숫자에 `[예시]` 표기는 넣지 않되 `meta.footer: "교육용 가상 사례 — 실제 회사 아님"`**을 둔다.

- [ ] **Step 4: 테스트 통과** — Run: `PYTHONUTF8=1 python -m pytest tests/test_layouts.py tests/test_example_spec.py -q` → 전부 통과
- [ ] **Step 5: 육안 확인** — `python SC/build_deck.py S/assets/spec.example.json --out tests/_out/example22.pptx` → export_all.ps1로 22장 PNG → 22장 모두 Read로 열어 검수(넘침·겹침·색 대비). 수정 후 재렌더.
- [ ] **Step 6: 커밋**

```bash
git add -A && git -c user.name="Lee Dong-Geon" -c user.email="leedg.brian@gmail.com" commit -m "feat(layouts): 마일스톤·팀·비전·부록 레이아웃 5종 + 셀아이 예시 스펙 22장

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 13: 렌더 검수 `render_qa.py` + `harness build/qa/pdf`

**Files:**
- Create: `SC/render_qa.py`, `T/test_render_qa.py`
- Modify: `SC/harness.py`

**Interfaces:**
- Produces: `render_qa.detect() -> "com"|"soffice"|None`, `render_qa.render(pptx: Path, out_dir: Path, slides: list[int]|None=None, pdf: bool=False) -> dict` (`{"engine", "pngs": [...], "pdf": str|None}`), `render_qa.auto_checks(spec: dict, build_report: dict) -> list[dict]` (`{"slide", "level": "blocking"|"warn", "msg"}`), `render_qa.write_report(ws, checks, engine, pngs) -> Path`(`09_build/qa_report.md`, 첫 줄에 `BLOCKING: n`).
- `harness build --ws` : `08_deck_spec.json` → `09_build/{팀}_Seed_IR_Deck_v1.pptx` + 빌드 경고 → `qa_report.md` 초안. `harness qa --ws [--slides ..]` : PNG 렌더 + auto_checks → `qa_report.md` 갱신. `harness pdf --ws [--src pptx] [--out pdf]`.
- 자동 검사: (blocking) 빌드 경고 중 `slot != image`인 텍스트 넘침 · 본문 장 `source_line` 비어 있음 · 레이아웃 미등록; (warn) 이미지 누락 `[이미지 확보 필요]` · 강조색 마크업 `**` 3회 초과인 제목 · `notes` 비어 있음.

- [ ] **Step 1: 실패하는 테스트 작성** — `T/test_render_qa.py`

```python
# -*- coding: utf-8 -*-
import json, shutil
import pytest
import render_qa, build_deck

def test_auto_checks_levels():
    spec = {"slides": [{"no": 1, "layout": "cover", "background": "dark", "slots": {}, "notes": ""},
                       {"no": 2, "layout": "trend_cards", "background": "cream", "slots": {"title": "**a** **b** **c** **d**"}, "source_line": "", "notes": "x"}]}
    rep = {"warnings": [{"slide": 2, "slot": "title", "text": "..", "lines": 3, "max": 2}, {"slide": 1, "slot": "image", "text": "missing", "lines": 0, "max": 0}]}
    checks = render_qa.auto_checks(spec, rep)
    levels = {(c["slide"], c["level"]) for c in checks}
    assert (2, "blocking") in levels and (1, "warn") in levels
    assert sum(1 for c in checks if c["level"] == "blocking") == 2  # 넘침 + source_line 없음

def test_write_report_header(out_dir):
    p = render_qa.write_report(out_dir, [{"slide": 1, "level": "warn", "msg": "m"}], engine=None, pngs=[])
    txt = p.read_text(encoding="utf-8")
    assert txt.startswith("# QA Report") and "BLOCKING: 0" in txt and "WARN: 1" in txt

@pytest.mark.skipif(render_qa.detect() is None, reason="렌더 엔진 없음")
def test_render_pngs(assets_dir, out_dir):
    build_deck.build(assets_dir / "spec.example.json", out_dir / "e.pptx")
    r = render_qa.render(out_dir / "e.pptx", out_dir / "png", slides=[1, 2], pdf=True)
    assert len(r["pngs"]) == 2 and r["pdf"] and (out_dir / "e.pdf").exists()
```

- [ ] **Step 2: 실행해 실패 확인** — Run: `PYTHONUTF8=1 python -m pytest tests/test_render_qa.py -q` → FAIL

- [ ] **Step 3: 구현** — `SC/render_qa.py`

```python
# -*- coding: utf-8 -*-
"""PPTX → PNG(+PDF) 렌더와 자동 검사. 엔진: PowerPoint COM(Windows) → LibreOffice → 없음."""
from __future__ import annotations
import glob, os, platform, shutil, subprocess, sys, tempfile
from pathlib import Path

_PS = r"""
$ErrorActionPreference = "Stop"
$pp = New-Object -ComObject PowerPoint.Application
$pres = $pp.Presentations.Open("{src}", $true, $false, $false)
{exports}
{pdf}
$pres.Close(); $pp.Quit()
Get-Process POWERPNT -ErrorAction SilentlyContinue | Where-Object {{ $_.MainWindowHandle -eq 0 }} | Stop-Process -Force -ErrorAction SilentlyContinue
Write-Output "COM-OK"
"""

def _soffice():
    for c in [shutil.which("soffice"), "/Applications/LibreOffice.app/Contents/MacOS/soffice",
              r"C:\Program Files\LibreOffice\program\soffice.exe", r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"]:
        if c and os.path.exists(c): return c
    return None

def detect() -> str | None:
    if platform.system() == "Windows":
        try:
            r = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-ItemProperty 'HKLM:\\SOFTWARE\\Classes\\PowerPoint.Application' -ErrorAction Stop | Out-Null; Write-Output OK"], capture_output=True, text=True, timeout=30)
            if "OK" in (r.stdout or ""): return "com"
        except Exception:  # noqa: BLE001
            pass
    return "soffice" if _soffice() else None

def _render_com(src: Path, out: Path, slides, pdf: bool) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    if slides:
        exports = "\n".join(f'$pres.Slides.Item({i}).Export("{out}\\slide-{i:02d}.png", "PNG", 1920, 1080)' for i in slides)
    else:
        exports = '$i = 1; foreach ($s in $pres.Slides) { $s.Export("' + str(out) + '\\slide-$("{0:d2}" -f $i).png", "PNG", 1920, 1080); $i++ }'
    pdf_path = src.with_suffix(".pdf")
    script = _PS.format(src=str(src), exports=exports, pdf=(f'$pres.SaveAs("{pdf_path}", 32)' if pdf else ""))
    ps1 = Path(tempfile.gettempdir()) / "seed_ir_render.ps1"; ps1.write_text(script, encoding="utf-8-sig")
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1)], capture_output=True, text=True, timeout=600)
    if "COM-OK" not in (r.stdout or ""): raise RuntimeError(f"PowerPoint COM 실패: {r.stderr[-500:]}")
    return {"engine": "com", "pngs": sorted(glob.glob(str(out / "slide-*.png"))), "pdf": str(pdf_path) if pdf else None}

def _render_soffice(src: Path, out: Path, slides, pdf: bool) -> dict:
    import fitz
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        subprocess.run([_soffice(), "--headless", "--convert-to", "pdf", "--outdir", td, str(src)], check=True, capture_output=True, timeout=600)
        tmp_pdf = Path(td) / (src.stem + ".pdf"); doc = fitz.open(str(tmp_pdf))
        pngs = []
        for i, page in enumerate(doc, 1):
            if slides and i not in slides: continue
            p = out / f"slide-{i:02d}.png"; page.get_pixmap(dpi=96).save(str(p)); pngs.append(str(p))
        pdf_path = None
        if pdf: pdf_path = src.with_suffix(".pdf"); shutil.copy(tmp_pdf, pdf_path)
    return {"engine": "soffice", "pngs": pngs, "pdf": str(pdf_path) if pdf_path else None}

def render(pptx, out_dir, slides=None, pdf=False) -> dict:
    eng = detect(); src = Path(pptx).resolve(); out = Path(out_dir).resolve()
    if eng == "com": return _render_com(src, out, slides, pdf)
    if eng == "soffice": return _render_soffice(src, out, slides, pdf)
    return {"engine": None, "pngs": [], "pdf": None}

_NO_SOURCE = {"cover", "statement", "vision_close", "appendix_qa"}

def auto_checks(spec: dict, build_report: dict) -> list[dict]:
    checks = []
    for w in build_report.get("warnings", []):
        if w.get("slot") == "image": checks.append({"slide": w["slide"], "level": "warn", "msg": f"이미지 누락 → [이미지 확보 필요] 표시됨 ({w['text']})"})
        elif w.get("slot") == "chart": checks.append({"slide": w["slide"], "level": "warn", "msg": w["text"]})
        else: checks.append({"slide": w["slide"], "level": "blocking", "msg": f"텍스트 넘침 {w['slot']}: {w['lines']}줄 > {w['max']}줄 '{w['text']}' — 문장을 줄일 것(숫자 불변)"})
    for s in spec.get("slides", []):
        if s.get("layout") not in _NO_SOURCE and not (s.get("source_line") or "").strip():
            checks.append({"slide": s["no"], "level": "blocking", "msg": "본문 슬라이드 출처줄 없음"})
        title = (s.get("slots") or {}).get("title") or (s.get("slots") or {}).get("headline") or ""
        if title.count("**") > 6: checks.append({"slide": s["no"], "level": "warn", "msg": "제목 강조색 3회 초과 — 한 장 한 군데 원칙"})
        if not (s.get("notes") or "").strip(): checks.append({"slide": s["no"], "level": "warn", "msg": "발표자 노트 비어 있음(finalizer가 채움)"})
    return sorted(checks, key=lambda c: (c["slide"], c["level"] != "blocking"))

def write_report(ws, checks: list[dict], engine, pngs) -> Path:
    ws = Path(ws); out = ws / "09_build"; out.mkdir(exist_ok=True)
    nb = sum(1 for c in checks if c["level"] == "blocking"); nw = len(checks) - nb
    lines = ["# QA Report", f"BLOCKING: {nb}", f"WARN: {nw}", f"engine: {engine or 'none (텍스트 QA만 — PowerPoint에서 직접 확인 필요)'}", f"pngs: {len(pngs)}", ""]
    for c in checks: lines.append(f"- slide {c['slide']:02d} [{c['level'].upper()}] {c['msg']}")
    if pngs:
        lines += ["", "## 육안 검수 대상 PNG (Read로 전장 확인)"] + [f"- {p}" for p in pngs]
    p = out / "qa_report.md"; p.write_text("\n".join(lines), encoding="utf-8"); return p
```

`SC/harness.py`에 추가:
```python
import build_deck, render_qa  # noqa: E402

def _deck_paths(ws: Path):
    team = State.load(ws).data["team"]
    return ws / "08_deck_spec.json", ws / "09_build" / f"{team}_Seed_IR_Deck_v1.pptx"

def cmd_build(args) -> int:
    ws = _ws_from_args(args); spec_p, out_p = _deck_paths(ws)
    if args.spec: spec_p = Path(args.spec)
    errs = validate.validate_phase(ws, "deck_spec", spec_p)
    if errs:
        print("VALIDATE deck_spec: FAIL"); [print("  -", e) for e in errs]; return 1
    rep = build_deck.build(spec_p, out_p)
    (ws / "09_build" / "build_report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    spec = json.loads(spec_p.read_text(encoding="utf-8"))
    render_qa.write_report(ws, render_qa.auto_checks(spec, rep), engine=None, pngs=[])
    print(f"BUILD: {rep['out']} ({rep['slides']}장) warnings={len(rep['warnings'])}")
    for w in rep["warnings"]: print(f"  ! slide {w['slide']} {w['slot']}: {w['text']}")
    return 0

def cmd_qa(args) -> int:
    ws = _ws_from_args(args); spec_p, pptx = _deck_paths(ws)
    if not pptx.exists(): print("BUILD 먼저 실행"); return 1
    slides = [int(x) for x in args.slides] if args.slides else None
    r = render_qa.render(pptx, ws / "09_build" / "qa_png", slides=slides, pdf=False)
    spec = json.loads(spec_p.read_text(encoding="utf-8")); rep = json.loads((ws / "09_build" / "build_report.json").read_text(encoding="utf-8"))
    p = render_qa.write_report(ws, render_qa.auto_checks(spec, rep), r["engine"], r["pngs"])
    print(p.read_text(encoding="utf-8")[:400]); return 0

def cmd_pdf(args) -> int:
    ws = _ws_from_args(args); _, pptx = _deck_paths(ws)
    src = Path(args.src) if args.src else pptx
    r = render_qa.render(src, ws / "09_build" / "_pdf_tmp", slides=[1], pdf=True)
    if not r["pdf"]:
        print("PDF 엔진 없음 — PowerPoint/Keynote에서 '내보내기 → PDF'로 저장하세요"); return 2
    if args.out: shutil.move(r["pdf"], args.out); print(f"PDF: {args.out}")
    else: print(f"PDF: {r['pdf']}")
    return 0

# SUBCOMMANDS 등록: build, qa, pdf
# parser: build: --ws --spec ; qa: --ws --slides nargs="*" ; pdf: --ws --src --out
```

(`import shutil` 추가.)

- [ ] **Step 4: 테스트 통과** — Run: `PYTHONUTF8=1 python -m pytest tests -q` → 전부 통과(엔진 없으면 render 1건 skip)
- [ ] **Step 5: 실기 확인** — 워크스페이스에 `spec.example.json`을 `08_deck_spec.json`으로 복사한 뒤 `harness.py build/qa/pdf --ws` 순서 실행 → `09_build/qa_report.md` 첫 줄 `BLOCKING: 0`, `qa_png/` 22장, PDF 생성 확인.
- [ ] **Step 6: 커밋**

```bash
git add -A && git -c user.name="Lee Dong-Geon" -c user.email="leedg.brian@gmail.com" commit -m "feat(qa): PNG/PDF 렌더 + 자동 검사 + harness build/qa/pdf

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

## Part B 완료 기준
- `pytest tests -q` 전부 통과.
- `spec.example.json` 22장이 경고 0(이미지 누락 경고 제외)으로 빌드되고, PNG 22장 육안 검수에서 넘침·겹침 0.
- 샘플 글루코픽 PNG(슬라이드 1·2·3·7·13·17·19)와 나란히 놓았을 때 구도·타이포·색 리듬이 같은 계열로 읽힌다.
