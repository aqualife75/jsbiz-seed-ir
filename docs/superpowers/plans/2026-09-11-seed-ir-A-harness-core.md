# Part A — 하네스 코어 구현 계획 (Task 1~7)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. 공통 제약은 `2026-09-11-seed-ir-00-index.md`의 Global Constraints를 따른다.

**Goal:** 저장소 스캐폴드, 입력 추출기 7종, 워크스페이스 상태, JSON 스키마 검증, 숫자 추적, 게이트, CLI `harness.py`를 테스트와 함께 완성한다.

**Architecture:** `scripts/` 아래 순수 Python 모듈. `harness.py`는 argparse 서브커맨드로 각 모듈을 호출만 한다. 모든 함수는 워크스페이스 경로(`ws: Path`)를 받아 파일을 읽고 쓴다.

**Tech Stack:** Python 3.10+, olefile, PyMuPDF(fitz), Pillow, python-docx, python-pptx, openpyxl, jsonschema, pytest.

경로 약어: `S` = `plugins/seed-ir/skills/seed-ir`, `SC` = `S/scripts`, `T` = `tests`.

---

### Task 1: 저장소 스캐폴드 · 플러그인 매니페스트 · 테스트 기반

**Files:**
- Create: `.claude-plugin/marketplace.json`, `plugins/seed-ir/.claude-plugin/plugin.json`, `requirements.txt`, `pytest.ini`, `.gitignore`, `LICENSE`, `T/conftest.py`, `T/test_scaffold.py`, `SC/__init__.py`, `SC/extractors/__init__.py`(빈 파일, Task 3에서 채움)

**Interfaces:**
- Produces: `tests/conftest.py`가 `SC`를 `sys.path`에 넣고, `out_dir` 픽스처(`tests/_out/<testname>/`)를 제공한다. 이후 모든 테스트는 `from extractors import ...`, `import harness` 식으로 import 한다.

- [ ] **Step 1: 실패하는 테스트 작성** — `T/test_scaffold.py`

```python
# -*- coding: utf-8 -*-
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_marketplace_manifest():
    m = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    assert m["name"] == "jsbiz-seed-ir"
    assert m["plugins"][0]["name"] == "seed-ir"
    assert m["plugins"][0]["source"] == "./plugins/seed-ir"

def test_plugin_manifest():
    p = json.loads((ROOT / "plugins/seed-ir/.claude-plugin/plugin.json").read_text(encoding="utf-8"))
    assert p["name"] == "seed-ir"
    assert p["version"].count(".") == 2

def test_requirements_lists_core_libs():
    req = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    for lib in ["python-pptx", "pymupdf", "pillow", "olefile", "python-docx", "openpyxl", "jsonschema"]:
        assert lib in req.lower()
```

- [ ] **Step 2: 실행해 실패 확인**

Run: `cd "<repo>" && PYTHONUTF8=1 python -m pytest tests/test_scaffold.py -q`
Expected: FAIL (FileNotFoundError 또는 collection error — conftest 없음)

- [ ] **Step 3: 파일 생성**

`.claude-plugin/marketplace.json`
```json
{
  "name": "jsbiz-seed-ir",
  "owner": { "name": "정석Biz (이동건)", "url": "https://www.youtube.com/@정석Biz" },
  "metadata": { "description": "정석Biz Seed IR Deck 멀티 에이전트 하네스 마켓플레이스", "version": "0.1.0" },
  "plugins": [
    {
      "name": "seed-ir",
      "source": "./plugins/seed-ir",
      "description": "창업팀 자료 폴더 → 정석Biz 노하우 12주제·투자자 질문 기준 Seed IR Deck(PPTX+PDF+피칭가이드) 자동 작성. 6 에이전트(자료 판독·본문·5인 심사·근거 조사·디자인·5분 피칭 검수) + 숫자 추적 하네스",
      "author": { "name": "정석Biz (이동건)" }
    }
  ]
}
```

`plugins/seed-ir/.claude-plugin/plugin.json`
```json
{
  "name": "seed-ir",
  "description": "Seed IR Deck 멀티 에이전트 하네스 — seed-ir 스킬(오케스트레이터) + 6 서브에이전트 + Python 하네스 스크립트",
  "version": "0.1.0",
  "author": { "name": "정석Biz (이동건)" }
}
```

`requirements.txt`
```
python-pptx>=1.0.2
pymupdf>=1.24
pillow>=10.0
olefile>=0.47
python-docx>=1.1
openpyxl>=3.1
jsonschema>=4.0
pytest>=8.0
```

`pytest.ini`
```ini
[pytest]
testpaths = tests
addopts = -p no:cacheprovider
```

`.gitignore`
```
__pycache__/
*.pyc
tests/_out/
_seed_ir_test/
*_SeedIR/
.pytest_cache/
*.tmp
```

`LICENSE` — MIT 전문(저작권자 `2026 Lee Dong-Geon (정석Biz)`).

`T/conftest.py`
```python
# -*- coding: utf-8 -*-
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins" / "seed-ir" / "skills" / "seed-ir" / "scripts"
sys.path.insert(0, str(SCRIPTS))

@pytest.fixture
def out_dir(request):
    d = ROOT / "tests" / "_out" / request.node.name
    d.mkdir(parents=True, exist_ok=True)
    return d

@pytest.fixture
def root():
    return ROOT

@pytest.fixture
def assets_dir():
    return ROOT / "plugins" / "seed-ir" / "skills" / "seed-ir" / "assets"
```

`SC/__init__.py`, `SC/extractors/__init__.py`: 빈 파일(utf-8 헤더 한 줄).

- [ ] **Step 4: 테스트 통과 확인**

Run: `PYTHONUTF8=1 python -m pytest tests/test_scaffold.py -q`
Expected: `3 passed`

- [ ] **Step 5: 커밋**

```bash
git add -A && git -c user.name="Lee Dong-Geon" -c user.email="leedg.brian@gmail.com" commit -m "chore: 플러그인 스캐폴드·매니페스트·테스트 기반

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 2: HWP(OLE) 추출기 — 텍스트 + BinData 이미지

**Files:**
- Create: `SC/extractors/hwp.py`, `T/test_hwp.py`

**Interfaces:**
- Produces: `extract(path: str|Path, out_dir: Path) -> dict` — `{"text": str, "images": [{"file": str, "origin": str, "w": int, "h": int}], "warnings": [str]}`. 이미지는 `out_dir/{stem}_{nn}.png|.jpg`로 저장. 모든 추출기가 같은 반환 형식을 쓴다(Task 3).
- 내부: `decode_para_text(payload: bytes) -> str`, `iter_records(raw: bytes)`, `hwp_text(path) -> str`, `hwp_images(path, out_dir, stem) -> (images, warnings)`.

- [ ] **Step 1: 실패하는 테스트 작성** — `T/test_hwp.py`

```python
# -*- coding: utf-8 -*-
import os, struct
from pathlib import Path
import pytest
from extractors import hwp

def _u16(s: str) -> bytes:
    return s.encode("utf-16-le")

def test_decode_para_text_skips_extended_control():
    # "안녕" + 확장 컨트롤(0x0B, 16바이트) + "세상" + 줄바꿈(13)
    payload = _u16("안녕") + struct.pack("<H", 11) + b"\x00" * 14 + _u16("세상") + struct.pack("<H", 13)
    assert hwp.decode_para_text(payload) == "안녕 세상\n"

def test_iter_records_parses_header_and_long_size():
    # tag=67, level=0, size=4 → header = 67 | (4<<20)
    hdr = struct.pack("<I", 67 | (4 << 20)) + _u16("ab")
    # long size: size field 0xFFF then explicit uint32
    hdr2 = struct.pack("<I", 67 | (0xFFF << 20)) + struct.pack("<I", 4) + _u16("cd")
    recs = list(hwp.iter_records(hdr + hdr2))
    assert [t for t, _ in recs] == [67, 67]
    assert hwp.decode_para_text(recs[1][1]) == "cd"

def test_sniff_image_ext():
    assert hwp.sniff_ext(b"\xff\xd8\xff\xe0" + b"0" * 10) == "jpg"
    assert hwp.sniff_ext(b"\x89PNG\r\n\x1a\n") == "png"
    assert hwp.sniff_ext(b"BM" + b"0" * 10) == "bmp"
    assert hwp.sniff_ext(b"\x00\x01\x02") is None

@pytest.mark.skipif(not os.environ.get("SEED_IR_TEST_HWP"), reason="실파일 경로 env 없음")
def test_real_hwp_extract(out_dir):
    res = hwp.extract(os.environ["SEED_IR_TEST_HWP"], out_dir)
    assert len(res["text"]) > 1000
    assert "사업계획서" in res["text"]
    assert len(res["images"]) >= 1
    assert all(Path(i["file"]).exists() for i in res["images"])
```

- [ ] **Step 2: 실행해 실패 확인**

Run: `PYTHONUTF8=1 python -m pytest tests/test_hwp.py -q`
Expected: FAIL `ImportError: cannot import name 'hwp'`

- [ ] **Step 3: 구현** — `SC/extractors/hwp.py`

```python
# -*- coding: utf-8 -*-
"""HWP 5.0 (OLE 복합문서) → 본문 텍스트 + BinData 이미지.

- 텍스트: BodyText/Section* 스트림을 zlib raw-deflate 해제 후 HWPTAG_PARA_TEXT(67) 레코드 복원.
- 이미지: BinData/* 스트림. 매직 바이트로 형식 판별, 아니면 zlib 해제 후 재판별. BMP/GIF/TIF → PNG 변환.
- 표는 셀 텍스트가 문단 순서로 나열됨(구조 미복원). 40px 미만 이미지는 아이콘으로 보고 건너뜀.
"""
from __future__ import annotations
import io, struct, zlib
from pathlib import Path

import olefile
from PIL import Image

HWPTAG_PARA_TEXT = 67
_EXTENDED_CTRL = {1, 2, 3, 11, 12, 14, 15, 16, 17, 18, 21, 22, 23}
MIN_IMG_PX = 40


def decode_para_text(payload: bytes) -> str:
    chars: list[str] = []
    j, n = 0, len(payload) - 1
    while j < n:
        c = struct.unpack("<H", payload[j:j + 2])[0]
        if c == 0:
            j += 2
        elif c in (10, 13):
            chars.append("\n"); j += 2
        elif c < 32:
            j += 16 if c in _EXTENDED_CTRL else 2
            chars.append(" ")
        elif 0xD800 <= c <= 0xDFFF:
            j += 2
        else:
            chars.append(chr(c)); j += 2
    return "".join(chars)


def iter_records(raw: bytes):
    i = 0
    while i < len(raw) - 3:
        header = struct.unpack("<I", raw[i:i + 4])[0]
        tag = header & 0x3FF
        size = (header >> 20) & 0xFFF
        i += 4
        if size == 0xFFF:
            if i + 4 > len(raw):
                return
            size = struct.unpack("<I", raw[i:i + 4])[0]
            i += 4
        yield tag, raw[i:i + size]
        i += size


def _inflate(raw: bytes) -> bytes | None:
    for wbits in (-15, 15):
        try:
            return zlib.decompress(raw, wbits)
        except zlib.error:
            continue
    return None


def sniff_ext(data: bytes) -> str | None:
    if data[:2] == b"\xff\xd8": return "jpg"
    if data[:4] == b"\x89PNG": return "png"
    if data[:2] == b"BM": return "bmp"
    if data[:4] == b"GIF8": return "gif"
    if data[:4] in (b"II*\x00", b"MM\x00*"): return "tif"
    return None


def hwp_text(path) -> str:
    ole = olefile.OleFileIO(str(path))
    try:
        hdr = ole.openstream("FileHeader").read()
        compressed = bool(struct.unpack("<I", hdr[36:40])[0] & 1)
        sections = [e for e in ole.listdir() if e[0] == "BodyText"]
        sections.sort(key=lambda e: int("".join(ch for ch in e[-1] if ch.isdigit()) or 0))
        paras: list[str] = []
        for e in sections:
            raw = ole.openstream(e).read()
            if compressed:
                raw = _inflate(raw) or b""
            for tag, payload in iter_records(raw):
                if tag == HWPTAG_PARA_TEXT:
                    paras.append(decode_para_text(payload))
        text = "\n".join(paras)
        if not text.strip() and ole.exists("PrvText"):
            text = ole.openstream("PrvText").read().decode("utf-16-le", "ignore")
        return text
    finally:
        ole.close()


def hwp_images(path, out_dir: Path, stem: str) -> tuple[list[dict], list[str]]:
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    images, warnings = [], []
    ole = olefile.OleFileIO(str(path))
    try:
        n = 0
        for e in ole.listdir():
            if e[0] != "BinData":
                continue
            raw = ole.openstream(e).read()
            data = raw if sniff_ext(raw) else (_inflate(raw) or raw)
            ext = sniff_ext(data)
            if not ext:
                warnings.append(f"skip non-image stream {'/'.join(e)}")
                continue
            try:
                im = Image.open(io.BytesIO(data)); im.load()
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"unreadable image {'/'.join(e)}: {exc}")
                continue
            if im.width < MIN_IMG_PX or im.height < MIN_IMG_PX:
                warnings.append(f"skip tiny image {'/'.join(e)} {im.size}")
                continue
            n += 1
            if ext == "jpg":
                dst = out_dir / f"{stem}_{n:02d}.jpg"
                dst.write_bytes(data)
            else:
                dst = out_dir / f"{stem}_{n:02d}.png"
                (im.convert("RGBA") if im.mode in ("P", "LA") else im).save(dst, "PNG")
            images.append({"file": str(dst), "origin": f"{Path(path).name}:{'/'.join(e)}", "w": im.width, "h": im.height})
    finally:
        ole.close()
    return images, warnings


def extract(path, out_dir) -> dict:
    path = Path(path)
    text = hwp_text(path)
    images, warnings = hwp_images(path, Path(out_dir), path.stem[:40])
    return {"text": text, "images": images, "warnings": warnings}
```

- [ ] **Step 4: 테스트 통과 확인 (실파일 포함)**

Run:
```bash
SEED_IR_TEST_HWP="D:/BRIAN Dropbox/Lee Dong-Geon/00. A_창업 교육/00. 2026년도_창업/2026.09.15_포스텍_IR Deck 강의/2026년 제16회 포스텍 창업경진대회_참가신청서_18부 이노폴리스 포항/2026년 제16회 포스텍 창업경진대회_참가신청서_시냅스_김준형.hwp" PYTHONUTF8=1 python -m pytest tests/test_hwp.py -q
```
Expected: `4 passed` (실파일 텍스트 7,000자 이상, 이미지 7장 중 40px 이상만 저장)

- [ ] **Step 5: 커밋**

```bash
git add -A && git -c user.name="Lee Dong-Geon" -c user.email="leedg.brian@gmail.com" commit -m "feat(extract): HWP 5.0 텍스트+BinData 이미지 추출기

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 3: 나머지 추출기(hwpx·pdf·docx·pptx·xlsx·images) + 디스패처

**Files:**
- Create: `SC/extractors/hwpx.py`, `SC/extractors/pdf.py`, `SC/extractors/docx.py`, `SC/extractors/pptx.py`, `SC/extractors/xlsx.py`, `SC/extractors/images.py`
- Modify: `SC/extractors/__init__.py`
- Test: `T/test_extractors.py`

**Interfaces:**
- Consumes: Task 2 `hwp.extract`.
- Produces: `extractors.extract_file(path, out_dir) -> dict` (Task 2와 동일 반환 형식 + `"kind": "hwp"|"hwpx"|"pdf"|"docx"|"pptx"|"xlsx"|"image"|"text"`), `extractors.SUPPORTED: set[str]` (소문자 확장자), `extractors.save_image(im: PIL.Image, out_dir, stem, n) -> dict`.

- [ ] **Step 1: 실패하는 테스트 작성** — `T/test_extractors.py`

```python
# -*- coding: utf-8 -*-
import zipfile
from pathlib import Path
from PIL import Image
import extractors

def _png(path: Path, size=(120, 80), color=(200, 40, 40)):
    Image.new("RGB", size, color).save(path)

def test_docx(out_dir):
    import docx
    d = docx.Document(); d.add_paragraph("문제 정의 MARK1")
    t = d.add_table(rows=1, cols=2); t.rows[0].cells[0].text = "A"; t.rows[0].cells[1].text = "B"
    img = out_dir / "p.png"; _png(img); d.add_picture(str(img))
    src = out_dir / "a.docx"; d.save(src)
    r = extractors.extract_file(src, out_dir / "x")
    assert r["kind"] == "docx" and "MARK1" in r["text"] and "A | B" in r["text"]
    assert len(r["images"]) == 1

def test_pptx(out_dir):
    from pptx import Presentation
    from pptx.util import Inches
    p = Presentation(); s = p.slides.add_slide(p.slide_layouts[6])
    tb = s.shapes.add_textbox(Inches(1), Inches(1), Inches(4), Inches(1)); tb.text_frame.text = "시장 규모 MARK2"
    s.notes_slide.notes_text_frame.text = "노트 MARK3"
    img = out_dir / "p.png"; _png(img); s.shapes.add_picture(str(img), Inches(1), Inches(2))
    src = out_dir / "a.pptx"; p.save(src)
    r = extractors.extract_file(src, out_dir / "x")
    assert "MARK2" in r["text"] and "MARK3" in r["text"] and len(r["images"]) == 1

def test_xlsx(out_dir):
    import openpyxl
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "매출"; ws.append(["월", "매출"]); ws.append([1, 1200])
    src = out_dir / "a.xlsx"; wb.save(src)
    r = extractors.extract_file(src, out_dir / "x")
    assert "[시트: 매출]" in r["text"] and "1 | 1200" in r["text"]

def test_pdf(out_dir):
    import fitz
    doc = fitz.open(); page = doc.new_page(); page.insert_text((72, 72), "TAM SAM SOM MARK4")
    img = out_dir / "p.png"; _png(img); page.insert_image(fitz.Rect(72, 100, 272, 250), filename=str(img))
    src = out_dir / "a.pdf"; doc.save(src)
    r = extractors.extract_file(src, out_dir / "x")
    assert "MARK4" in r["text"] and len(r["images"]) >= 1
    assert any(Path(i["file"]).name.startswith("a_page") for i in r["images"])  # 페이지 렌더 포함

def test_hwpx(out_dir):
    src = out_dir / "a.hwpx"
    sec = '<hs:sec xmlns:hp="x"><hp:p><hp:run><hp:t>팀 역량 MARK5</hp:t></hp:run></hp:p><hp:p><hp:run><hp:t>둘째</hp:t></hp:run></hp:p></hs:sec>'
    img = out_dir / "p.png"; _png(img)
    with zipfile.ZipFile(src, "w") as z:
        z.writestr("mimetype", "application/hwp+zip"); z.writestr("Contents/section0.xml", sec)
        z.write(img, "BinData/image1.png")
    r = extractors.extract_file(src, out_dir / "x")
    assert "MARK5\n둘째" in r["text"] and len(r["images"]) == 1

def test_image_and_bmp(out_dir):
    bmp = out_dir / "photo.bmp"; Image.new("RGB", (300, 200), (1, 2, 3)).save(bmp)
    r = extractors.extract_file(bmp, out_dir / "x")
    assert r["kind"] == "image" and r["images"][0]["file"].endswith(".png")

def test_unsupported(out_dir):
    f = out_dir / "a.zzz"; f.write_text("x")
    r = extractors.extract_file(f, out_dir / "x")
    assert r["kind"] == "unsupported" and r["warnings"]
```

- [ ] **Step 2: 실행해 실패 확인**

Run: `PYTHONUTF8=1 python -m pytest tests/test_extractors.py -q`
Expected: FAIL `AttributeError: module 'extractors' has no attribute 'extract_file'`

- [ ] **Step 3: 구현**

`SC/extractors/images.py`
```python
# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from PIL import Image, ImageOps

MAX_SIDE = 2400
MIN_PX = 40

def save_image(im: Image.Image, out_dir: Path, stem: str, n: int, origin: str, prefer_jpg=False) -> dict | None:
    """PIL 이미지를 정규화해 저장. 너무 작으면 None."""
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    im = ImageOps.exif_transpose(im)
    if im.width < MIN_PX or im.height < MIN_PX:
        return None
    if max(im.size) > MAX_SIDE:
        im.thumbnail((MAX_SIDE, MAX_SIDE))
    if prefer_jpg and im.mode == "RGB":
        dst = out_dir / f"{stem}_{n:02d}.jpg"; im.save(dst, "JPEG", quality=92)
    else:
        dst = out_dir / f"{stem}_{n:02d}.png"
        (im.convert("RGBA") if im.mode in ("P", "LA", "CMYK") else im).save(dst, "PNG")
    return {"file": str(dst), "origin": origin, "w": im.width, "h": im.height}

def extract(path, out_dir) -> dict:
    path = Path(path)
    try:
        im = Image.open(path); im.load()
    except Exception as exc:  # noqa: BLE001
        return {"text": "", "images": [], "warnings": [f"unreadable image {path.name}: {exc}"]}
    rec = save_image(im, Path(out_dir), path.stem[:40], 1, path.name, prefer_jpg=(path.suffix.lower() in (".jpg", ".jpeg")))
    return {"text": "", "images": [rec] if rec else [], "warnings": [] if rec else [f"tiny image {path.name}"]}
```

`SC/extractors/hwpx.py`
```python
# -*- coding: utf-8 -*-
from __future__ import annotations
import html, io, re, zipfile
from pathlib import Path
from PIL import Image
from .images import save_image

_T = re.compile(r"<hp:t[^>]*>(.*?)</hp:t>", re.S)
_P_END = re.compile(r"</hp:p>")

def extract(path, out_dir) -> dict:
    path = Path(path); out_dir = Path(out_dir)
    text_parts, images, warnings = [], [], []
    with zipfile.ZipFile(path) as z:
        secs = sorted([n for n in z.namelist() if re.match(r"Contents/section\d+\.xml$", n)],
                      key=lambda n: int(re.search(r"(\d+)", n.split("/")[-1]).group(1)))
        for n in secs:
            xml = z.read(n).decode("utf-8", "ignore")
            paras = []
            for chunk in _P_END.split(xml):
                t = "".join(html.unescape(m) for m in _T.findall(chunk))
                if t.strip():
                    paras.append(t)
            text_parts.append("\n".join(paras))
        k = 0
        for n in z.namelist():
            if n.startswith("BinData/") and not n.endswith("/"):
                try:
                    im = Image.open(io.BytesIO(z.read(n))); im.load()
                except Exception:  # noqa: BLE001
                    warnings.append(f"skip non-image {n}"); continue
                k += 1
                rec = save_image(im, out_dir, path.stem[:40], k, f"{path.name}:{n}")
                if rec: images.append(rec)
    return {"text": "\n".join(text_parts), "images": images, "warnings": warnings}
```

`SC/extractors/pdf.py`
```python
# -*- coding: utf-8 -*-
from __future__ import annotations
import io
from pathlib import Path
import fitz
from PIL import Image
from .images import save_image

MAX_PAGE_RENDER = 30

def extract(path, out_dir) -> dict:
    path = Path(path); out_dir = Path(out_dir)
    doc = fitz.open(str(path))
    texts, images, warnings = [], [], []
    stem = path.stem[:40]
    k = 0
    for pno, page in enumerate(doc, 1):
        texts.append(f"\n--- p{pno} ---\n" + page.get_text("text"))
        for info in page.get_images(full=True):
            try:
                pix = doc.extract_image(info[0])
                im = Image.open(io.BytesIO(pix["image"])); im.load()
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"p{pno} image xref {info[0]}: {exc}"); continue
            k += 1
            rec = save_image(im, out_dir, stem, k, f"{path.name}:p{pno}")
            if rec: images.append(rec)
        if pno <= MAX_PAGE_RENDER:
            pm = page.get_pixmap(dpi=100)
            dst = out_dir / f"{stem}_page{pno:02d}.png"; out_dir.mkdir(parents=True, exist_ok=True)
            pm.save(str(dst))
            images.append({"file": str(dst), "origin": f"{path.name}:page{pno}", "w": pm.width, "h": pm.height, "page_render": True})
    if len(doc) > MAX_PAGE_RENDER:
        warnings.append(f"page render limited to {MAX_PAGE_RENDER} of {len(doc)} pages")
    return {"text": "".join(texts), "images": images, "warnings": warnings}
```

`SC/extractors/docx.py`
```python
# -*- coding: utf-8 -*-
from __future__ import annotations
import io, zipfile
from pathlib import Path
import docx as _docx
from PIL import Image
from .images import save_image

def extract(path, out_dir) -> dict:
    path = Path(path); out_dir = Path(out_dir)
    d = _docx.Document(str(path))
    lines = [p.text for p in d.paragraphs if p.text.strip()]
    for t in d.tables:
        lines.append("[표]")
        for row in t.rows:
            lines.append(" | ".join(c.text.strip().replace("\n", " ") for c in row.cells))
    images, warnings, k = [], [], 0
    with zipfile.ZipFile(path) as z:
        for n in z.namelist():
            if n.startswith("word/media/"):
                try:
                    im = Image.open(io.BytesIO(z.read(n))); im.load()
                except Exception:  # noqa: BLE001
                    warnings.append(f"skip {n}"); continue
                k += 1
                rec = save_image(im, out_dir, path.stem[:40], k, f"{path.name}:{n}")
                if rec: images.append(rec)
    return {"text": "\n".join(lines), "images": images, "warnings": warnings}
```

`SC/extractors/pptx.py`
```python
# -*- coding: utf-8 -*-
from __future__ import annotations
import io, zipfile
from pathlib import Path
from pptx import Presentation
from PIL import Image
from .images import save_image

def extract(path, out_dir) -> dict:
    path = Path(path); out_dir = Path(out_dir)
    prs = Presentation(str(path))
    lines = []
    for i, s in enumerate(prs.slides, 1):
        lines.append(f"\n--- slide {i} ---")
        for sh in s.shapes:
            if sh.has_text_frame:
                for p in sh.text_frame.paragraphs:
                    if p.text.strip(): lines.append(p.text.strip())
            if getattr(sh, "has_table", False) and sh.has_table:
                for row in sh.table.rows:
                    lines.append(" | ".join(c.text.strip().replace("\n", " ") for c in row.cells))
        if s.has_notes_slide and s.notes_slide.notes_text_frame.text.strip():
            lines.append("[노트] " + s.notes_slide.notes_text_frame.text.strip())
    images, warnings, k = [], [], 0
    with zipfile.ZipFile(path) as z:
        for n in z.namelist():
            if n.startswith("ppt/media/") and not n.endswith("/"):
                try:
                    im = Image.open(io.BytesIO(z.read(n))); im.load()
                except Exception:  # noqa: BLE001
                    warnings.append(f"skip {n}"); continue
                k += 1
                rec = save_image(im, out_dir, path.stem[:40], k, f"{path.name}:{n}")
                if rec: images.append(rec)
    return {"text": "\n".join(lines), "images": images, "warnings": warnings}
```

`SC/extractors/xlsx.py`
```python
# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
import openpyxl

MAX_ROWS = 500

def extract(path, out_dir) -> dict:
    wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
    lines, warnings = [], []
    for ws in wb.worksheets:
        lines.append(f"[시트: {ws.title}]")
        for r, row in enumerate(ws.iter_rows(values_only=True), 1):
            if r > MAX_ROWS:
                warnings.append(f"{ws.title}: rows limited to {MAX_ROWS}"); break
            if any(v is not None for v in row):
                lines.append(" | ".join("" if v is None else str(v) for v in row))
    return {"text": "\n".join(lines), "images": [], "warnings": warnings}
```

`SC/extractors/__init__.py`
```python
# -*- coding: utf-8 -*-
"""입력 파일 → {"kind","text","images","warnings"}. 확장자별 디스패치."""
from __future__ import annotations
from pathlib import Path
from . import hwp, hwpx, pdf, docx, pptx, xlsx, images
from .images import save_image  # re-export

_MAP = {
    ".hwp": ("hwp", hwp.extract), ".hwpx": ("hwpx", hwpx.extract), ".pdf": ("pdf", pdf.extract),
    ".docx": ("docx", docx.extract), ".pptx": ("pptx", pptx.extract), ".xlsx": ("xlsx", xlsx.extract),
    ".png": ("image", images.extract), ".jpg": ("image", images.extract), ".jpeg": ("image", images.extract),
    ".bmp": ("image", images.extract), ".gif": ("image", images.extract), ".webp": ("image", images.extract),
}
SUPPORTED = set(_MAP) | {".md", ".txt", ".csv"}

def extract_file(path, out_dir) -> dict:
    path = Path(path); ext = path.suffix.lower()
    if ext in (".md", ".txt", ".csv"):
        return {"kind": "text", "text": path.read_text(encoding="utf-8", errors="replace"), "images": [], "warnings": []}
    if ext not in _MAP:
        return {"kind": "unsupported", "text": "", "images": [], "warnings": [f"unsupported extension {ext}: {path.name}"]}
    kind, fn = _MAP[ext]
    try:
        res = fn(path, Path(out_dir))
    except Exception as exc:  # noqa: BLE001
        return {"kind": kind, "text": "", "images": [], "warnings": [f"extract failed {path.name}: {exc}"]}
    res["kind"] = kind
    return res
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `PYTHONUTF8=1 python -m pytest tests/test_extractors.py tests/test_hwp.py -q`
Expected: `7 passed, 1 skipped` (실파일 env 없을 때) 

- [ ] **Step 5: 커밋**

```bash
git add -A && git -c user.name="Lee Dong-Geon" -c user.email="leedg.brian@gmail.com" commit -m "feat(extract): hwpx·pdf·docx·pptx·xlsx·image 추출기 + 디스패처

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 4: 워크스페이스 상태(`state.py`) + `harness.py init/extract/status`

**Files:**
- Create: `SC/state.py`, `SC/harness.py`, `T/test_harness.py`

**Interfaces:**
- Produces:
  - `state.PHASES = ["1_facts","2_write","3_review","4_research","5_design","6_pitch"]`
  - `class State: load(ws) -> State`, `.save()`, `.set_phase(name, status, note="")`, `.record_gate(phase, ok, reasons)`, `.approve(key)`, `.data` dict
  - `harness.infer_team(input_dir: Path) -> str`, `harness.cmd_init(args)`, `harness.cmd_extract(args)`, `harness.cmd_status(args)`, `harness.main(argv) -> int`
  - 워크스페이스 파일: `state.json`, `inputs.json`, `01_extract/{stem}.txt`, `01_extract/images/`, `01_extract/manifest.json`
- 이후 Task 5~7·13이 `harness.py`에 서브커맨드를 추가한다(`SUBCOMMANDS` dict에 등록).

- [ ] **Step 1: 실패하는 테스트 작성** — `T/test_harness.py`

```python
# -*- coding: utf-8 -*-
import json
from pathlib import Path
from PIL import Image
import harness, state

def _inputs(out_dir: Path) -> Path:
    d = out_dir / "in"; d.mkdir(parents=True, exist_ok=True)
    (d / "2026년 제16회 포스텍 창업경진대회_참가신청서_시냅스_김준형.txt").write_text("사업계획서 본문 1,234명", encoding="utf-8")
    Image.new("RGB", (200, 100), (9, 9, 9)).save(d / "제품.png")
    return d

def test_infer_team(out_dir):
    d = _inputs(out_dir)
    assert harness.infer_team(d) == "시냅스"

def test_init_creates_workspace(out_dir):
    d = _inputs(out_dir)
    rc = harness.main(["init", str(d), "--out", str(out_dir / "ws")])
    assert rc == 0
    ws = next((out_dir / "ws").glob("*_시냅스_SeedIR"))
    st = json.loads((ws / "state.json").read_text(encoding="utf-8"))
    assert st["team"] == "시냅스" and st["phases"]["1_facts"]["status"] == "pending"
    inputs = json.loads((ws / "inputs.json").read_text(encoding="utf-8"))
    assert len(inputs["files"]) == 2

def test_extract_writes_dumps_and_manifest(out_dir):
    d = _inputs(out_dir)
    harness.main(["init", str(d), "--out", str(out_dir / "ws"), "--team", "테스트팀"])
    ws = next((out_dir / "ws").glob("*_테스트팀_SeedIR"))
    assert harness.main(["extract", "--ws", str(ws)]) == 0
    man = json.loads((ws / "01_extract" / "manifest.json").read_text(encoding="utf-8"))
    assert man["total_chars"] > 0 and man["total_images"] == 1
    assert (ws / "01_extract" / "images").exists()
    txts = list((ws / "01_extract").glob("*.txt"))
    assert len(txts) == 1 and "1,234명" in txts[0].read_text(encoding="utf-8")

def test_state_roundtrip(out_dir):
    ws = out_dir / "ws2"; ws.mkdir(exist_ok=True)
    st = state.State.new(ws, team="T", input_dir=str(ws))
    st.set_phase("1_facts", "done", "ok"); st.record_gate("2", True, []); st.approve("accept_risk"); st.save()
    st2 = state.State.load(ws)
    assert st2.data["phases"]["1_facts"]["status"] == "done"
    assert st2.data["gates"]["2"]["ok"] is True and st2.data["approvals"]["accept_risk"] is True
```

- [ ] **Step 2: 실행해 실패 확인**

Run: `PYTHONUTF8=1 python -m pytest tests/test_harness.py -q`
Expected: FAIL `ModuleNotFoundError: No module named 'harness'`

- [ ] **Step 3: 구현**

`SC/state.py`
```python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path

PHASES = ["1_facts", "2_write", "3_review", "4_research", "5_design", "6_pitch"]

def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

class State:
    def __init__(self, ws: Path, data: dict):
        self.ws = Path(ws); self.data = data

    @classmethod
    def new(cls, ws: Path, team: str, input_dir: str) -> "State":
        data = {
            "team": team, "input_dir": input_dir, "created": _now(), "updated": _now(),
            "phases": {p: {"status": "pending", "started": None, "finished": None, "note": ""} for p in PHASES},
            "gates": {}, "approvals": {"accept_risk": False, "storyline_confirmed": False}, "log": [],
        }
        st = cls(ws, data); st.save(); return st

    @classmethod
    def load(cls, ws: Path) -> "State":
        p = Path(ws) / "state.json"
        if not p.exists():
            raise FileNotFoundError(f"state.json 없음: {p} — 먼저 `harness.py init`을 실행하세요")
        return cls(ws, json.loads(p.read_text(encoding="utf-8")))

    def save(self) -> None:
        self.data["updated"] = _now()
        (self.ws / "state.json").write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")

    def set_phase(self, name: str, status: str, note: str = "") -> None:
        ph = self.data["phases"][name]
        if status == "running": ph["started"] = _now()
        if status in ("done", "failed"): ph["finished"] = _now()
        ph["status"] = status; ph["note"] = note
        self.data["log"].append({"t": _now(), "phase": name, "status": status, "note": note})

    def record_gate(self, phase: str, ok: bool, reasons: list[str]) -> None:
        self.data["gates"][str(phase)] = {"ok": ok, "reasons": reasons, "t": _now()}

    def approve(self, key: str) -> None:
        self.data["approvals"][key] = True
```

`SC/harness.py`
```python
# -*- coding: utf-8 -*-
"""seed-ir 하네스 CLI. 결정적 작업(추출·검증·추적·게이트·빌드·렌더)만 담당한다.

사용:
  python harness.py init <입력폴더> [--team 팀명] [--out 폴더]
  python harness.py extract --ws <워크스페이스>
  python harness.py status  --ws <워크스페이스>
  (Task 5~7, 13에서 validate / trace / gate / build / qa / pdf 추가)
"""
from __future__ import annotations
import argparse, json, re, sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import extractors  # noqa: E402
from state import State, PHASES  # noqa: E402

_TEAM_RE = re.compile(r"참가신청서_(.+?)_[^_]+\.[A-Za-z0-9]+$")  # 포스텍 파일명 규칙: …_참가신청서_{팀명}_{팀장}.hwp

def infer_team(input_dir: Path) -> str:
    for f in sorted(Path(input_dir).iterdir()):
        m = _TEAM_RE.search(f.name)
        if m:
            return m.group(1).strip()
    return Path(input_dir).name.strip()

def _ws_from_args(args) -> Path:
    ws = Path(args.ws).resolve()
    if not (ws / "state.json").exists():
        sys.exit(f"[오류] 워크스페이스가 아닙니다: {ws}")
    return ws

def cmd_init(args) -> int:
    src = Path(args.input_dir).resolve()
    if not src.is_dir():
        print(f"[오류] 입력 폴더 없음: {src}"); return 1
    team = args.team or infer_team(src)
    out_root = Path(args.out).resolve() if args.out else src.parent
    ws = out_root / f"{datetime.now():%Y.%m.%d}_{team}_SeedIR"
    ws.mkdir(parents=True, exist_ok=True)
    files = []
    for f in sorted(src.rglob("*")):
        if f.is_file() and not f.name.startswith(("~$", ".")):
            files.append({"path": str(f), "name": f.name, "ext": f.suffix.lower(), "size": f.stat().st_size,
                          "supported": f.suffix.lower() in extractors.SUPPORTED})
    (ws / "inputs.json").write_text(json.dumps({"input_dir": str(src), "files": files}, ensure_ascii=False, indent=2), encoding="utf-8")
    State.new(ws, team=team, input_dir=str(src))
    (ws / "run_log.md").write_text(f"# {team} Seed IR 실행 로그\n\n- init {datetime.now():%Y-%m-%d %H:%M} · 입력 {len(files)}개\n", encoding="utf-8")
    print(f"WS={ws}")
    print(f"team={team} files={len(files)} unsupported={sum(1 for f in files if not f['supported'])}")
    return 0

def cmd_extract(args) -> int:
    ws = _ws_from_args(args)
    inputs = json.loads((ws / "inputs.json").read_text(encoding="utf-8"))
    ex = ws / "01_extract"; img_dir = ex / "images"; ex.mkdir(exist_ok=True); img_dir.mkdir(exist_ok=True)
    manifest = {"files": [], "total_chars": 0, "total_images": 0, "warnings": []}
    for f in inputs["files"]:
        if not f["supported"]:
            manifest["warnings"].append(f"미지원 건너뜀: {f['name']}"); continue
        res = extractors.extract_file(f["path"], img_dir)
        stem = Path(f["name"]).stem[:60]
        txt = ex / f"{stem}.txt"
        if res["text"].strip():
            txt.write_text(res["text"], encoding="utf-8")
        manifest["files"].append({"name": f["name"], "kind": res["kind"], "text_path": str(txt) if res["text"].strip() else None,
                                  "chars": len(res["text"]), "images": res["images"], "warnings": res["warnings"]})
        manifest["total_chars"] += len(res["text"]); manifest["total_images"] += len(res["images"])
        manifest["warnings"].extend(f"{f['name']}: {w}" for w in res["warnings"])
    (ex / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"extracted files={len(manifest['files'])} chars={manifest['total_chars']:,} images={manifest['total_images']} warnings={len(manifest['warnings'])}")
    for w in manifest["warnings"][:20]:
        print("  !", w)
    return 0

def cmd_status(args) -> int:
    ws = _ws_from_args(args); st = State.load(ws)
    print(f"팀: {st.data['team']}  WS: {ws}")
    for p in PHASES:
        ph = st.data["phases"][p]
        print(f"  {p:12s} {ph['status']:8s} {ph.get('finished') or ph.get('started') or ''}  {ph.get('note','')}")
    for g, v in st.data["gates"].items():
        print(f"  gate→{g}: {'OK' if v['ok'] else 'BLOCK'} {'; '.join(v['reasons'])}")
    return 0

SUBCOMMANDS = {"init": cmd_init, "extract": cmd_extract, "status": cmd_status}

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="harness.py", description="seed-ir 하네스")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init"); p.add_argument("input_dir"); p.add_argument("--team"); p.add_argument("--out")
    for name in ("extract", "status"):
        p = sub.add_parser(name); p.add_argument("--ws", required=True)
    return ap

def main(argv=None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    return SUBCOMMANDS[args.cmd](args)

if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `PYTHONUTF8=1 python -m pytest tests/test_harness.py -q`
Expected: `4 passed`

- [ ] **Step 5: 커밋**

```bash
git add -A && git -c user.name="Lee Dong-Geon" -c user.email="leedg.brian@gmail.com" commit -m "feat(harness): 워크스페이스 state + init/extract/status CLI

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 5: JSON 스키마 8종 + `validate.py` + `harness validate`

**Files:**
- Create: `S/assets/schemas/{fact_pack,image_catalog,storyline,slides,review_summary,evidence,image_ledger,deck_spec}.schema.json`, `S/assets/limits.json`, `SC/validate.py`, `T/test_validate.py`
- Modify: `SC/harness.py` (validate 서브커맨드)

**Interfaces:**
- Produces: `validate.validate_obj(obj: dict, schema_name: str) -> list[str]`, `validate.validate_phase(ws: Path, target: str, file: Path|None=None) -> list[str]` — target ∈ `fact_pack|image_catalog|storyline|slides|review|evidence|ledger|deck_spec`. 빈 리스트 = 통과.
- `limits.json`: `{ "<layout>": { "<slot.path>": max_chars } }` — Task 9~12의 빌더도 같은 파일을 읽는다. 슬롯 경로는 점 표기, 배열은 `[]` (예: `cards[].desc`).
- 데이터 계약은 설계서 §3-4. 주요 열거값: `topic_id` 1~12, `kind` ∈ `fact|estimate|target`, `severity` ∈ `critical|major|minor`, `verdict` ∈ `O|△|X`, `tier` ∈ `A|B|C`, `license` ∈ `team|quote|cc|public|official|unknown`.

- [ ] **Step 1: 실패하는 테스트 작성** — `T/test_validate.py`

```python
# -*- coding: utf-8 -*-
import json
from pathlib import Path
import validate

def _fact_pack():
    return {
        "company": {"name": "셀아이", "one_liner": "이차전지 전극 결함 검사 AI", "founded": "[자료 없음]", "ceo": "홍길동", "headcount": "[자료 없음]"},
        "items": [{"key": k, "value": "v 12건", "asof": "2026.09", "source": "참가신청서 p3", "status": "given"} for k in
                  ["회사 기본", "문제", "제품", "기술", "시장", "경쟁", "트랙션", "재무", "팀", "투자"]],
        "topic_slots": [{"topic_id": i, "facts": ["f"], "images": [], "status": "partial"} for i in range(1, 13)],
        "gaps": [{"item": "시장 규모 출처", "why_needed": "6 시장", "topic_ids": [6]}],
        "contact": {"name": "홍길동", "email": "a@b.c", "phone": "010-0000-0000"},
    }

def _slides(n=13):
    s = []
    for i in range(1, n + 1):
        s.append({"no": i, "topic_id": min(i, 12), "investor_question": "q", "title": "제목", "lead": "리드",
                  "evidence": [{"text": "근거 12건", "source": "s"}], "key_numbers": [{"value": "12", "unit": "건", "label": "l", "kind": "fact", "source": "s"}],
                  "source": "출처", "open_question": "?", "labels": []})
    s[6]["weakness_row"] = "유료 레퍼런스 0건"  # topic 7
    return {"slides": s}

def test_fact_pack_valid():
    assert validate.validate_obj(_fact_pack(), "fact_pack") == []

def test_fact_pack_missing_topic_slot():
    fp = _fact_pack(); fp["topic_slots"].pop()
    errs = validate.validate_obj(fp, "fact_pack")
    assert any("topic_slots" in e for e in errs)

def test_fact_pack_number_without_source():
    fp = _fact_pack(); fp["items"][4]["source"] = ""
    errs = validate.validate_obj(fp, "fact_pack")
    assert any("source" in e and "시장" in e for e in errs)

def test_slides_valid():
    assert validate.validate_obj(_slides(), "slides") == []

def test_slides_count_and_weakness():
    s = _slides(11)
    errs = validate.validate_obj(s, "slides")
    assert any("12" in e for e in errs)
    s = _slides(); del s["slides"][6]["weakness_row"]
    assert any("weakness_row" in e for e in validate.validate_obj(s, "slides"))

def test_deck_spec_limits(assets_dir):
    spec = {"meta": {"team": "T", "accent": "E0492E"}, "slides": [
        {"no": 1, "layout": "statement", "background": "dark", "slots": {"statement": "가" * 80, "sub": "나"}, "source_line": "", "notes": ""}]}
    errs = validate.validate_obj(spec, "deck_spec")
    assert any("statement.statement" in e and "80" in e for e in errs)

def test_validate_phase_reads_file(out_dir):
    (out_dir / "02_fact_pack.json").write_text(json.dumps(_fact_pack(), ensure_ascii=False), encoding="utf-8")
    assert validate.validate_phase(out_dir, "fact_pack") == []
    assert validate.validate_phase(out_dir, "slides")  # 파일 없음 → 오류 메시지
```

- [ ] **Step 2: 실행해 실패 확인**

Run: `PYTHONUTF8=1 python -m pytest tests/test_validate.py -q`
Expected: FAIL `ModuleNotFoundError: No module named 'validate'`

- [ ] **Step 3: 스키마·limits 작성**

`S/assets/schemas/fact_pack.schema.json`
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "fact_pack", "type": "object",
  "required": ["company", "items", "topic_slots", "gaps", "contact"],
  "properties": {
    "company": {"type": "object", "required": ["name", "one_liner"], "properties": {
      "name": {"type": "string", "minLength": 1}, "one_liner": {"type": "string", "minLength": 1},
      "founded": {"type": "string"}, "ceo": {"type": "string"}, "headcount": {"type": "string"}}},
    "items": {"type": "array", "minItems": 10, "maxItems": 10, "items": {"type": "object",
      "required": ["key", "value", "asof", "source", "status"],
      "properties": {"key": {"type": "string"}, "value": {"type": "string"}, "asof": {"type": "string"}, "source": {"type": "string"},
                     "status": {"enum": ["given", "missing", "partial"]}}}},
    "topic_slots": {"type": "array", "minItems": 12, "maxItems": 12, "items": {"type": "object",
      "required": ["topic_id", "facts", "images", "status"],
      "properties": {"topic_id": {"type": "integer", "minimum": 1, "maximum": 12}, "facts": {"type": "array", "items": {"type": "string"}},
                     "images": {"type": "array", "items": {"type": "string"}}, "status": {"enum": ["sufficient", "partial", "missing"]}}}},
    "gaps": {"type": "array", "items": {"type": "object", "required": ["item", "why_needed", "topic_ids"],
      "properties": {"item": {"type": "string"}, "why_needed": {"type": "string"}, "topic_ids": {"type": "array", "items": {"type": "integer"}}}}},
    "contact": {"type": "object", "properties": {"name": {"type": "string"}, "email": {"type": "string"}, "phone": {"type": "string"}}}
  }
}
```

`S/assets/schemas/image_catalog.schema.json`
```json
{"$schema": "http://json-schema.org/draft-07/schema#", "title": "image_catalog", "type": "object", "required": ["images"],
 "properties": {"images": {"type": "array", "items": {"type": "object",
   "required": ["file", "origin", "description", "kind", "suggested_topics", "quality"],
   "properties": {"file": {"type": "string"}, "origin": {"type": "string"}, "w": {"type": "integer"}, "h": {"type": "integer"},
     "description": {"type": "string", "minLength": 5}, "kind": {"enum": ["product", "screen", "chart", "photo", "logo", "cert", "table", "diagram", "other"]},
     "suggested_topics": {"type": "array", "items": {"type": "integer", "minimum": 1, "maximum": 12}},
     "has_korean_text": {"type": "boolean"}, "quality": {"enum": ["ok", "low"]}}}}}}
```

`S/assets/schemas/storyline.schema.json`
```json
{"$schema": "http://json-schema.org/draft-07/schema#", "title": "storyline", "type": "object", "required": ["slides"],
 "properties": {"slides": {"type": "array", "minItems": 12, "maxItems": 16, "items": {"type": "object",
   "required": ["no", "topic_ids", "investor_question", "key_message", "type", "data_status"],
   "properties": {"no": {"type": "integer"}, "topic_ids": {"type": "array", "minItems": 1, "items": {"type": "integer", "minimum": 1, "maximum": 12}},
     "investor_question": {"type": "string", "minLength": 3}, "key_message": {"type": "string", "minLength": 3},
     "type": {"enum": ["cover", "body", "statement", "appendix"]}, "data_status": {"enum": ["sufficient", "partial", "missing"]}}}}}}
```

`S/assets/schemas/slides.schema.json`
```json
{"$schema": "http://json-schema.org/draft-07/schema#", "title": "slides", "type": "object", "required": ["slides"],
 "properties": {"slides": {"type": "array", "minItems": 12, "maxItems": 16, "items": {"type": "object",
   "required": ["no", "topic_id", "investor_question", "title", "lead", "evidence", "key_numbers", "source", "open_question", "labels"],
   "properties": {"no": {"type": "integer"}, "topic_id": {"type": "integer", "minimum": 0, "maximum": 12},
     "investor_question": {"type": "string", "minLength": 3}, "title": {"type": "string", "minLength": 2, "maxLength": 44},
     "lead": {"type": "string", "maxLength": 120},
     "evidence": {"type": "array", "maxItems": 3, "items": {"type": "object", "required": ["text", "source"],
        "properties": {"text": {"type": "string"}, "source": {"type": "string"}, "calc": {"type": "string"}}}},
     "key_numbers": {"type": "array", "maxItems": 3, "items": {"type": "object", "required": ["value", "unit", "label", "kind", "source"],
        "properties": {"value": {"type": "string"}, "unit": {"type": "string"}, "label": {"type": "string"},
          "kind": {"enum": ["fact", "estimate", "target"]}, "source": {"type": "string"}, "calc": {"type": "string"}}}},
     "source": {"type": "string", "minLength": 1}, "open_question": {"type": "string"},
     "labels": {"type": "array", "items": {"type": "string"}}, "weakness_row": {"type": "string"},
     "notes_draft": {"type": "string"}}}},
   "changes": {"type": "array", "items": {"type": "object"}},
   "to_secure": {"type": "array", "items": {"type": "object", "required": ["item", "why", "slide_no"],
     "properties": {"item": {"type": "string"}, "why": {"type": "string"}, "slide_no": {"type": "integer"}}}}}}
```

`S/assets/schemas/review_summary.schema.json`
```json
{"$schema": "http://json-schema.org/draft-07/schema#", "title": "review_summary", "type": "object",
 "required": ["scores", "question_check", "issues", "attack_questions", "to_reach_85"],
 "properties": {
   "scores": {"type": "object", "required": ["vc", "ac", "domain", "finance", "layman", "avg"],
     "additionalProperties": {"type": "number", "minimum": 0, "maximum": 100}},
   "question_check": {"type": "array", "minItems": 12, "maxItems": 12, "items": {"type": "object", "required": ["topic_id", "verdict", "reason"],
     "properties": {"topic_id": {"type": "integer", "minimum": 1, "maximum": 12}, "verdict": {"enum": ["O", "△", "X"]}, "reason": {"type": "string"}}}},
   "issues": {"type": "array", "items": {"type": "object", "required": ["id", "severity", "slide_no", "text", "fix_hint", "status"],
     "properties": {"id": {"type": "string"}, "severity": {"enum": ["critical", "major", "minor"]}, "slide_no": {"type": "integer"},
       "text": {"type": "string"}, "fix_hint": {"type": "string"}, "status": {"enum": ["open", "resolved", "accepted"]}, "resolution": {"type": "string"}}}},
   "attack_questions": {"type": "array", "minItems": 10, "maxItems": 20, "items": {"type": "string"}},
   "to_reach_85": {"type": "array", "items": {"type": "string"}}}}
```

`S/assets/schemas/evidence.schema.json`
```json
{"$schema": "http://json-schema.org/draft-07/schema#", "title": "evidence", "type": "object", "required": ["records"],
 "properties": {"records": {"type": "array", "items": {"type": "object",
   "required": ["id", "topic_id", "claim", "value", "source_title", "publisher", "url", "retrieved", "tier", "confidence"],
   "properties": {"id": {"type": "string"}, "topic_id": {"type": "integer"}, "slide_no": {"type": "integer"}, "claim": {"type": "string"},
     "value": {"type": "string"}, "unit": {"type": "string"}, "asof": {"type": "string"}, "source_title": {"type": "string"}, "publisher": {"type": "string"},
     "url": {"type": "string"}, "retrieved": {"type": "string"}, "tier": {"enum": ["A", "B", "C"]}, "capture_file": {"type": "string"},
     "quote": {"type": "string"}, "confidence": {"enum": ["high", "mid", "low"]}}}}}}
```

`S/assets/schemas/image_ledger.schema.json`
```json
{"$schema": "http://json-schema.org/draft-07/schema#", "title": "image_ledger", "type": "object", "required": ["images"],
 "properties": {"images": {"type": "array", "items": {"type": "object",
   "required": ["file", "license", "retrieved", "used_in_slides", "needs_human_review"],
   "properties": {"file": {"type": "string"}, "url": {"type": "string"}, "page_url": {"type": "string"}, "title": {"type": "string"},
     "author": {"type": "string"}, "license": {"enum": ["team", "quote", "cc", "public", "official", "unknown"]}, "license_note": {"type": "string"},
     "retrieved": {"type": "string"}, "used_in_slides": {"type": "array", "items": {"type": "integer"}}, "needs_human_review": {"type": "boolean"}}}}}}
```

`S/assets/schemas/deck_spec.schema.json`
```json
{"$schema": "http://json-schema.org/draft-07/schema#", "title": "deck_spec", "type": "object", "required": ["meta", "slides"],
 "properties": {
   "meta": {"type": "object", "required": ["team"], "properties": {"team": {"type": "string"}, "accent": {"type": "string", "pattern": "^[0-9A-Fa-f]{6}$"},
     "date": {"type": "string"}, "assets_dir": {"type": "string"}, "footer": {"type": "string"}}},
   "slides": {"type": "array", "minItems": 1, "items": {"type": "object", "required": ["no", "layout", "background", "slots"],
     "properties": {"no": {"type": "integer"}, "layout": {"type": "string"}, "background": {"enum": ["dark", "cream"]},
       "slots": {"type": "object"}, "source_line": {"type": "string"}, "notes": {"type": "string"}, "seconds": {"type": "integer"}}}}}}
```

`S/assets/limits.json` — 설계서 §5-3 상한을 옮긴 것(샘플 데이터 검증 후 일부 완화 — **이 파일이 설계서 표보다 우선**). 키는 `layout.slot.path`(배열은 `[]`). 글자수는 `**` 마크업·줄바꿈 문자를 포함해 센다.
```json
{
  "cover": {"kicker": 30, "brand": 20, "headline": 30, "subtitle": 60, "tags[]": 8, "footer_stats[].label": 8, "footer_stats[].value": 16},
  "statement": {"statement": 34, "sub": 40},
  "trend_cards": {"title": 44, "lead": 120, "cards[].label": 18, "cards[].headline": 22, "cards[].big": 8, "cards[].unit": 6, "cards[].desc": 70, "cards[].source": 40, "band.so_what": 40, "band.why_now[]": 45, "key_gap": 30},
  "problem_cascade": {"title": 44, "lead": 120, "bars[].label": 12, "kpis[].big": 8, "kpis[].label": 22, "kpis[].source": 30, "quote.text": 60, "quote.who": 40},
  "problem_grid": {"title": 44, "lead": 120, "stats[].big": 8, "stats[].label": 22, "stats[].source": 30, "points[].title": 14, "points[].sub": 16, "points[].desc": 60, "footnote": 90},
  "alt_table": {"title": 44, "lead": 120, "table.columns[]": 14, "table.rows[].label": 12, "table.rows[].cells[]": 18, "premise_note": 90},
  "quadrant": {"title": 44, "lead": 120, "axes.x_left": 12, "axes.x_right": 12, "axes.y_top": 12, "axes.y_bottom": 12, "bubbles[].name": 12, "bubbles[].sub": 14, "gaps[].title": 16, "gaps[].desc": 60},
  "solution_steps": {"title": 44, "lead": 120, "steps[].label": 14, "steps[].title": 14, "steps[].desc": 32, "cards[].title": 20, "cards[].desc": 80, "cards[].source": 40},
  "product_screens": {"title": 44, "lead": 120, "screens[].label": 14, "screens[].title": 12, "screens[].desc": 60, "screens[].mock_lines[]": 22, "footnote": 90},
  "tech_moat": {"title": 44, "lead": 120, "data_cards[].big": 8, "data_cards[].label": 22, "data_cards[].desc": 60, "pipeline[].title": 14, "pipeline[].desc": 60, "moat.title": 60, "moat.desc": 60, "safety": 90},
  "mvp_scope": {"title": 44, "lead": 120, "now[].title": 14, "now[].desc": 30, "target_line": 60, "not_now[]": 40, "roadmap[].label": 12, "roadmap[].title": 14, "roadmap[].desc": 40},
  "traction_plan": {"title": 44, "lead": 120, "weeks[].label": 18, "weeks[].big": 14, "weeks[].desc": 70, "table.rows[].metric": 12, "table.rows[].target": 8, "table.rows[].method": 30, "side.title": 14, "side.body": 90, "insight": 80},
  "kpi_chart": {"title": 44, "lead": 120, "chart.categories[]": 8, "chart.series[].name": 10, "kpis[].big": 8, "kpis[].label": 22, "kpis[].source": 30, "note": 80},
  "bm_pricing": {"title": 44, "lead": 120, "tiers[].label": 14, "tiers[].price": 12, "tiers[].sub": 30, "tiers[].bullets[]": 22, "tiers[].note": 60, "unit_econ[].label": 10, "unit_econ[].big": 10, "unit_econ[].sub": 20, "evidence_note": 90},
  "market_tam": {"title": 44, "lead": 120, "tam.label": 22, "tam.desc": 40, "tam.big": 8, "tam.unit": 4, "tam.calc": 30, "sam.label": 22, "sam.desc": 40, "sam.big": 8, "sam.unit": 4, "sam.calc": 30, "som.label": 22, "som.desc": 40, "som.big": 8, "som.unit": 4, "som.calc": 30, "side_stats[].label": 14, "side_stats[].big": 16, "side_stats[].sub": 40, "side_stats[].source": 30, "sanity_note": 100},
  "gtm_funnel": {"title": 44, "lead": 120, "beachhead.title": 28, "beachhead.why": 60, "beachhead.exclude": 60, "channels[].title": 20, "channels[].desc": 70, "funnel[].label": 14, "funnel[].big": 8, "funnel[].unit": 3, "funnel[].desc": 30, "footnote": 90},
  "growth_phases": {"title": 44, "lead": 120, "phases[].label": 18, "phases[].title": 12, "phases[].desc": 80, "phases[].kpi": 40, "flywheel[]": 16, "expansion": 90},
  "milestone_gates": {"title": 44, "lead": 120, "gates[].label": 12, "gates[].title": 10, "gates[].bullets[]": 18, "gates[].gate": 30, "ask_band.amount": 10, "ask_band.runway": 12, "ask_band.use_of_funds": 90},
  "team_cards": {"title": 44, "lead": 120, "members[].role": 26, "members[].title": 14, "members[].desc": 70, "members[].kpi": 40, "advisors[].title": 20, "advisors[].desc": 50, "principle.title": 26, "principle.desc": 80, "principle.list[]": 20, "footnote": 90},
  "vision_close": {"headline": 40, "body": 120, "one_liner": 56, "cards[].label": 8, "cards[].big": 20, "cards[].sub": 40, "tagline": 24, "ask_line": 24},
  "appendix_qa": {"title": 44, "qa[].q": 50, "qa[].a": 120},
  "evidence_capture": {"title": 44, "caption": 60, "source": 80}
}
```

- [ ] **Step 4: `validate.py` 구현**

```python
# -*- coding: utf-8 -*-
"""JSON 스키마 + 필드 규칙 검증. 빈 리스트 = 통과."""
from __future__ import annotations
import json, re
from pathlib import Path
import jsonschema

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"
SCHEMAS = ASSETS / "schemas"
_NUM = re.compile(r"\d")
COMPETITION_TOPIC = 7

_TARGET_FILES = {
    "fact_pack": "02_fact_pack.json", "image_catalog": "01_extract/image_catalog.json", "storyline": "03_storyline.json",
    "slides": "04_slides_v1.json", "review": "05_review/summary.json", "evidence": "06_evidence/evidence.json",
    "ledger": "06_evidence/image_ledger.json", "deck_spec": "08_deck_spec.json",
}
_SCHEMA_OF = {"review": "review_summary", "ledger": "image_ledger"}

def _load_schema(name: str) -> dict:
    return json.loads((SCHEMAS / f"{name}.schema.json").read_text(encoding="utf-8"))

def load_limits() -> dict:
    return json.loads((ASSETS / "limits.json").read_text(encoding="utf-8"))

def _schema_errors(obj, name) -> list[str]:
    v = jsonschema.Draft7Validator(_load_schema(name))
    return [f"[schema:{name}] {'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}" for e in sorted(v.iter_errors(obj), key=lambda e: list(e.absolute_path))]

def _rules_fact_pack(fp: dict) -> list[str]:
    errs = []
    ids = sorted(s["topic_id"] for s in fp.get("topic_slots", []))
    if ids != list(range(1, 13)):
        errs.append(f"topic_slots: topic_id 1~12가 각 1개씩 있어야 함 (현재 {ids})")
    for it in fp.get("items", []):
        if it.get("status") == "given" and _NUM.search(it.get("value", "")):
            if not it.get("source", "").strip(): errs.append(f"items[{it['key']}]: 숫자가 있는데 source 비어 있음")
            if not it.get("asof", "").strip(): errs.append(f"items[{it['key']}]: 숫자가 있는데 asof(기준시점) 비어 있음")
    return errs

def _rules_slides(doc: dict) -> list[str]:
    errs = []
    slides = doc.get("slides", [])
    body = [s for s in slides if s.get("topic_id", 0) > 0]
    if not (12 <= len(body) <= 14):
        errs.append(f"본문 장수는 12~14장이어야 함 (현재 {len(body)})")
    for s in slides:
        if s.get("topic_id") == COMPETITION_TOPIC and not s.get("weakness_row", "").strip():
            errs.append(f"slide {s.get('no')}: 경쟁(topic 7) 장은 weakness_row(우리 약점 1행) 필수")
        if "[기입 필요" in json.dumps(s, ensure_ascii=False) and doc.get("changes") is not None:
            errs.append(f"slide {s.get('no')}: 개정본(v2)에 [기입 필요] 잔존")
    return errs

def _rules_storyline(doc: dict) -> list[str]:
    covered = {t for s in doc.get("slides", []) for t in s.get("topic_ids", [])}
    missing = sorted(set(range(1, 13)) - covered)
    return [f"storyline: 배정되지 않은 주제 {missing}"] if missing else []

def _walk_limits(slots: dict, limits: dict, layout: str) -> list[str]:
    errs = []
    def get(obj, path):
        parts = path.split(".")
        cur = [obj]
        for p in parts:
            nxt = []
            for c in cur:
                if p.endswith("[]"):
                    v = c.get(p[:-2]) if isinstance(c, dict) else None
                    if isinstance(v, list): nxt.extend(v)
                else:
                    v = c.get(p) if isinstance(c, dict) else None
                    if v is not None: nxt.append(v)
            cur = nxt
        return cur
    for path, mx in limits.items():
        for v in get(slots, path):
            if isinstance(v, str) and len(v) > mx:
                errs.append(f"{layout}.{path}: {len(v)}자 > 상한 {mx}자 — '{v[:20]}…'")
    return errs

def _rules_deck_spec(doc: dict) -> list[str]:
    errs, limits = [], load_limits()
    for s in doc.get("slides", []):
        lay = s.get("layout")
        if lay not in limits:
            errs.append(f"slide {s.get('no')}: 알 수 없는 layout '{lay}'"); continue
        errs += [f"slide {s.get('no')} " + e for e in _walk_limits(s.get("slots", {}), limits[lay], lay)]
        if lay not in ("cover", "statement", "vision_close", "appendix_qa") and not s.get("source_line", "").strip():
            errs.append(f"slide {s.get('no')}: 본문 슬라이드는 source_line 필수")
    return errs

_RULES = {"fact_pack": _rules_fact_pack, "slides": _rules_slides, "storyline": _rules_storyline, "deck_spec": _rules_deck_spec}

def validate_obj(obj: dict, schema_name: str) -> list[str]:
    errs = _schema_errors(obj, schema_name)
    if not errs and schema_name in _RULES:
        errs += _RULES[schema_name](obj)
    return errs

def validate_phase(ws: Path, target: str, file: Path | None = None) -> list[str]:
    ws = Path(ws)
    path = Path(file) if file else ws / _TARGET_FILES[target]
    if not path.exists():
        return [f"파일 없음: {path}"]
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"JSON 파싱 실패 {path.name}: {exc}"]
    return validate_obj(obj, _SCHEMA_OF.get(target, target))
```

`SC/harness.py`에 추가 (SUBCOMMANDS·parser):
```python
import validate  # noqa: E402  (import 블록에)

def cmd_validate(args) -> int:
    ws = _ws_from_args(args)
    errs = validate.validate_phase(ws, args.target, Path(args.file) if args.file else None)
    if errs:
        print(f"VALIDATE {args.target}: FAIL ({len(errs)})")
        for e in errs: print("  -", e)
        return 1
    print(f"VALIDATE {args.target}: OK"); return 0

# SUBCOMMANDS["validate"] = cmd_validate
# parser: p = sub.add_parser("validate"); p.add_argument("target", choices=list(validate._TARGET_FILES)); p.add_argument("--ws", required=True); p.add_argument("--file")
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `PYTHONUTF8=1 python -m pytest tests/test_validate.py -q`
Expected: `7 passed`

- [ ] **Step 6: 커밋**

```bash
git add -A && git -c user.name="Lee Dong-Geon" -c user.email="leedg.brian@gmail.com" commit -m "feat(validate): JSON 스키마 8종·limits.json·필드 규칙 검증 + harness validate

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 6: 숫자 추적 `trace_numbers.py` + `harness trace`

**Files:**
- Create: `SC/trace_numbers.py`, `T/test_trace.py`
- Modify: `SC/harness.py`

**Interfaces:**
- Produces: `trace_numbers.tokens(text: str) -> set[str]`(정규화 토큰: 콤마 제거 숫자 문자열, 소수 유지), `collect_allowed(fact_pack: dict, evidence: dict|None) -> set[str]`, `check_slides(slides_doc: dict, allowed: set[str]) -> list[dict]`(미추적 `{slide_no, field, token, context}`), `run(ws: Path, slides_file: Path|None) -> dict` (`{"untraced": [...], "checked": n}` + `05_review/trace_report.json` 저장).
- 규칙: 연도(1990~2035, 단위 없음) 무시 · 20 미만 정수는 단위가 `%·억·만·조·원·배·개월·년·B·M·K`일 때만 검사 · `calc` 문자열이 있는 항목은 calc 안의 숫자가 모두 추적되면 결과 숫자를 허용 · 검사 필드 = `title, lead, evidence[].text, key_numbers[].value, weakness_row`.

- [ ] **Step 1: 실패하는 테스트 작성** — `T/test_trace.py`

```python
# -*- coding: utf-8 -*-
import json
import trace_numbers as tn

def test_tokens_normalize():
    assert tn.tokens("1,939만 명 · 24.4% · 2024년 · 3명 중 1명") == {"1939", "24.4"}
    assert tn.tokens("월 14,900원 · 5,000만 원") == {"14900", "5000"}
    assert tn.tokens("12개월 · 7일") == {"12"}

def test_check_slides_flags_untraced():
    fp = {"items": [{"value": "고객 인터뷰 31명, 이벤트 2,309건"}], "topic_slots": [{"facts": ["시장 233만 9,937명 (2025)"]}]}
    ev = {"records": [{"value": "24.4", "claim": "외식 비중 24.4%"}]}
    allowed = tn.collect_allowed(fp, ev)
    slides = {"slides": [
        {"no": 2, "title": "31명이 2,309건을 남겼다", "lead": "외식 24.4%", "evidence": [{"text": "233만 9,937명", "source": "s"}], "key_numbers": []},
        {"no": 3, "title": "유료 전환 60%", "lead": "", "evidence": [], "key_numbers": [{"value": "1,000", "unit": "명"}]},
        {"no": 4, "title": "SOM 29억", "lead": "", "evidence": [], "key_numbers": [{"value": "29", "unit": "억", "calc": "233만 × 20% × 1% × 4,900원 × 12"}]},
    ]}
    un = tn.check_slides(slides, allowed)
    toks = {(u["slide_no"], u["token"]) for u in un}
    assert (3, "60") in toks and (3, "1000") in toks
    assert not any(u["slide_no"] == 2 for u in un)
    # calc 안의 20%, 1%, 4900은 자료에 없으므로 29도 미추적
    assert (4, "29") in toks

def test_calc_accepts_when_inputs_traced():
    allowed = {"233", "20", "1", "4900", "12"}
    slides = {"slides": [{"no": 4, "title": "SOM 29억", "lead": "", "evidence": [], "key_numbers": [{"value": "29", "unit": "억", "calc": "233만 × 20% × 1% × 4,900원 × 12"}]}]}
    assert tn.check_slides(slides, allowed) == []

def test_run_writes_report(out_dir):
    (out_dir / "02_fact_pack.json").write_text(json.dumps({"items": [{"value": "31명"}], "topic_slots": []}), encoding="utf-8")
    (out_dir / "04_slides_v1.json").write_text(json.dumps({"slides": [{"no": 1, "title": "31명", "lead": "", "evidence": [], "key_numbers": []}]}), encoding="utf-8")
    rep = tn.run(out_dir, None)
    assert rep["untraced"] == [] and (out_dir / "05_review" / "trace_report.json").exists()
```

- [ ] **Step 2: 실행해 실패 확인**

Run: `PYTHONUTF8=1 python -m pytest tests/test_trace.py -q`
Expected: FAIL `ModuleNotFoundError`

- [ ] **Step 3: 구현** — `SC/trace_numbers.py`

```python
# -*- coding: utf-8 -*-
"""슬라이드 본문의 숫자가 사실 팩/증거 원장에 존재하는지 대조한다. 미추적 1건이면 실패."""
from __future__ import annotations
import json, re
from pathlib import Path

_NUM_RE = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?\s*(조|억|만|천|%|p|배|원|명|건|개월|개|년|일|시간|분|초|B|M|K|USD|달러)?")
_STRICT_UNITS = {"%", "억", "만", "조", "원", "배", "개월", "년", "B", "M", "K", "USD", "달러", "p"}
_FIELDS = ("title", "lead", "weakness_row")

def _canon(m: re.Match) -> str | None:
    whole, frac, unit = m.group(1).replace(",", ""), m.group(2), m.group(3) or ""
    tok = whole + (f".{frac}" if frac else "")
    val = float(tok)
    if not frac and 1990 <= val <= 2035 and unit in ("", "년"):
        return None
    if not frac and val < 20 and unit not in _STRICT_UNITS:
        return None
    return tok

def tokens(text: str) -> set[str]:
    out = set()
    for m in _NUM_RE.finditer(text or ""):
        t = _canon(m)
        if t: out.add(t)
    return out

def _all_strings(obj):
    if isinstance(obj, str): yield obj
    elif isinstance(obj, dict):
        for v in obj.values(): yield from _all_strings(v)
    elif isinstance(obj, list):
        for v in obj: yield from _all_strings(v)

def collect_allowed(fact_pack: dict, evidence: dict | None) -> set[str]:
    allowed = set()
    for s in _all_strings(fact_pack): allowed |= tokens(s)
    if evidence:
        for s in _all_strings(evidence): allowed |= tokens(s)
    return allowed

def _check_text(no, field, text, allowed, out, calc=None):
    for tok in sorted(tokens(text)):
        if tok in allowed: continue
        if calc:
            calc_toks = tokens(calc)
            if calc_toks and calc_toks <= allowed:
                continue
        out.append({"slide_no": no, "field": field, "token": tok, "context": (text or "")[:60]})

def check_slides(doc: dict, allowed: set[str]) -> list[dict]:
    out: list[dict] = []
    for s in doc.get("slides", []):
        no = s.get("no")
        for f in _FIELDS:
            if s.get(f): _check_text(no, f, s[f], allowed, out)
        for i, e in enumerate(s.get("evidence", [])):
            _check_text(no, f"evidence[{i}].text", e.get("text", ""), allowed, out, e.get("calc"))
        for i, k in enumerate(s.get("key_numbers", [])):
            _check_text(no, f"key_numbers[{i}].value", f"{k.get('value','')}{k.get('unit','')}", allowed, out, k.get("calc"))
    return out

def run(ws: Path, slides_file: Path | None) -> dict:
    ws = Path(ws)
    fp = json.loads((ws / "02_fact_pack.json").read_text(encoding="utf-8"))
    ev_path = ws / "06_evidence" / "evidence.json"
    ev = json.loads(ev_path.read_text(encoding="utf-8")) if ev_path.exists() else None
    sf = Path(slides_file) if slides_file else (ws / "07_slides_v2.json" if (ws / "07_slides_v2.json").exists() else ws / "04_slides_v1.json")
    doc = json.loads(sf.read_text(encoding="utf-8"))
    allowed = collect_allowed(fp, ev)
    untraced = check_slides(doc, allowed)
    rep = {"slides_file": str(sf), "checked": len(doc.get("slides", [])), "allowed_tokens": len(allowed), "untraced": untraced}
    (ws / "05_review").mkdir(exist_ok=True)
    (ws / "05_review" / "trace_report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    return rep
```

`SC/harness.py`에 추가:
```python
import trace_numbers  # noqa: E402

def cmd_trace(args) -> int:
    ws = _ws_from_args(args)
    rep = trace_numbers.run(ws, Path(args.file) if args.file else None)
    if rep["untraced"]:
        print(f"TRACE: FAIL — 미추적 숫자 {len(rep['untraced'])}건 (자료·증거에 없는 숫자는 만들지 마세요)")
        for u in rep["untraced"][:40]:
            print(f"  - slide {u['slide_no']} {u['field']}: {u['token']}  ← {u['context']}")
        return 1
    print(f"TRACE: OK ({rep['checked']}장, 허용 토큰 {rep['allowed_tokens']}개)"); return 0

# SUBCOMMANDS["trace"] = cmd_trace ; parser: p = sub.add_parser("trace"); p.add_argument("--ws", required=True); p.add_argument("--file")
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `PYTHONUTF8=1 python -m pytest tests/test_trace.py -q`
Expected: `4 passed`

- [ ] **Step 5: 커밋**

```bash
git add -A && git -c user.name="Lee Dong-Geon" -c user.email="leedg.brian@gmail.com" commit -m "feat(trace): 슬라이드 숫자 ↔ 사실 팩/증거 원장 추적 + harness trace

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 7: 게이트 `gate.py` + `harness gate`

**Files:**
- Create: `SC/gate.py`, `T/test_gate.py`
- Modify: `SC/harness.py`

**Interfaces:**
- Produces: `gate.check(ws: Path, phase: str, accept_risk: bool=False) -> tuple[bool, list[str]]` — phase ∈ `"2","3","4","5","6","final"`. 결과를 `State.record_gate`로 기록하고 `accept_risk=True`면 `approvals.accept_risk` 승인 기록.
- 조건(설계서 §3-3): 2=fact_pack validate · 3=slides validate(v1) · 4=summary.json 존재 · 5=trace OK + critical open 0(또는 accept_risk) + `[기입 필요]` 0 · 6=`09_build/qa_report.md` 존재 + `BLOCKING: 0` 포함 · final=10_final 4종 존재 + trace 재통과.

- [ ] **Step 1: 실패하는 테스트 작성** — `T/test_gate.py`

```python
# -*- coding: utf-8 -*-
import json
from pathlib import Path
import gate, state

def _ws(out_dir):
    st = state.State.new(out_dir, team="T", input_dir=str(out_dir))
    fp = {"company": {"name": "T", "one_liner": "x"}, "items": [{"key": str(i), "value": "v", "asof": "", "source": "", "status": "missing"} for i in range(10)],
          "topic_slots": [{"topic_id": i, "facts": [], "images": [], "status": "missing"} for i in range(1, 13)], "gaps": [], "contact": {}}
    (out_dir / "02_fact_pack.json").write_text(json.dumps(fp, ensure_ascii=False), encoding="utf-8")
    return st

def _slides(n=13, fill="ok"):
    s = [{"no": i, "topic_id": min(i, 12), "investor_question": "q", "title": f"제목 {fill}", "lead": "", "evidence": [], "key_numbers": [],
          "source": "s", "open_question": "", "labels": []} for i in range(1, n + 1)]
    s[6]["weakness_row"] = "약점"
    return {"slides": s}

def test_gate2_passes_with_valid_fact_pack(out_dir):
    _ws(out_dir)
    ok, reasons = gate.check(out_dir, "2")
    assert ok, reasons

def test_gate5_blocks_on_critical_then_accept_risk(out_dir):
    _ws(out_dir)
    (out_dir / "07_slides_v2.json").write_text(json.dumps(_slides(), ensure_ascii=False), encoding="utf-8")
    (out_dir / "05_review").mkdir(exist_ok=True)
    (out_dir / "05_review" / "summary.json").write_text(json.dumps({"scores": {}, "question_check": [], "attack_questions": [], "to_reach_85": [],
        "issues": [{"id": "C1", "severity": "critical", "slide_no": 2, "text": "출처 없음", "fix_hint": "", "status": "open"}]}), encoding="utf-8")
    ok, reasons = gate.check(out_dir, "5")
    assert not ok and any("critical" in r for r in reasons)
    ok, _ = gate.check(out_dir, "5", accept_risk=True)
    assert ok
    assert state.State.load(out_dir).data["approvals"]["accept_risk"] is True

def test_gate5_blocks_on_untraced_number_and_placeholder(out_dir):
    _ws(out_dir)
    (out_dir / "05_review").mkdir(exist_ok=True)
    (out_dir / "05_review" / "summary.json").write_text(json.dumps({"scores": {}, "question_check": [], "attack_questions": [], "to_reach_85": [], "issues": []}), encoding="utf-8")
    (out_dir / "07_slides_v2.json").write_text(json.dumps(_slides(fill="1,234명 [기입 필요: 출처]"), ensure_ascii=False), encoding="utf-8")
    ok, reasons = gate.check(out_dir, "5")
    assert not ok and any("미추적" in r for r in reasons) and any("기입 필요" in r for r in reasons)

def test_gate6_requires_qa_report(out_dir):
    _ws(out_dir)
    ok, reasons = gate.check(out_dir, "6")
    assert not ok
    (out_dir / "09_build").mkdir(); (out_dir / "09_build" / "qa_report.md").write_text("# QA\nBLOCKING: 0\n", encoding="utf-8")
    assert gate.check(out_dir, "6")[0]
```

- [ ] **Step 2: 실행해 실패 확인**

Run: `PYTHONUTF8=1 python -m pytest tests/test_gate.py -q`
Expected: FAIL `ModuleNotFoundError: No module named 'gate'`

- [ ] **Step 3: 구현** — `SC/gate.py`

```python
# -*- coding: utf-8 -*-
"""단계 진입 게이트. 설계서 §3-3."""
from __future__ import annotations
import json, re
from pathlib import Path
import validate, trace_numbers
from state import State

_FINAL_REQUIRED = ["*_Seed_IR_Deck.pptx", "*_Seed_IR_Deck.pdf", "피칭가이드.md", "qa_png"]

def _slides_path(ws: Path) -> Path | None:
    for n in ("07_slides_v2.json", "04_slides_v1.json"):
        if (ws / n).exists(): return ws / n
    return None

def check(ws: Path, phase: str, accept_risk: bool = False) -> tuple[bool, list[str]]:
    ws = Path(ws); reasons: list[str] = []
    st = State.load(ws)
    if accept_risk:
        st.approve("accept_risk")
    risk_ok = accept_risk or st.data["approvals"].get("accept_risk", False)

    if phase == "2":
        reasons += validate.validate_phase(ws, "fact_pack")
    elif phase == "3":
        reasons += validate.validate_phase(ws, "slides")
    elif phase == "4":
        if not (ws / "05_review" / "summary.json").exists(): reasons.append("05_review/summary.json 없음 — 모의심사 미완")
    elif phase == "5":
        sp = _slides_path(ws)
        if not sp: reasons.append("슬라이드 파일 없음")
        else:
            reasons += [f"validate: {e}" for e in validate.validate_phase(ws, "slides", sp)]
            rep = trace_numbers.run(ws, sp)
            if rep["untraced"]: reasons.append(f"trace: 미추적 숫자 {len(rep['untraced'])}건 (05_review/trace_report.json)")
            txt = sp.read_text(encoding="utf-8")
            n_fill = len(re.findall(r"\[기입 필요", txt))
            if n_fill: reasons.append(f"[기입 필요] {n_fill}건 잔존 — [확보 필요]로 옮기거나 근거를 채우세요")
        summ = ws / "05_review" / "summary.json"
        if not summ.exists(): reasons.append("05_review/summary.json 없음")
        else:
            issues = json.loads(summ.read_text(encoding="utf-8")).get("issues", [])
            crit = [i for i in issues if i.get("severity") == "critical" and i.get("status") == "open"]
            if crit and not risk_ok:
                reasons.append(f"critical 미해결 {len(crit)}건: " + "; ".join(i["text"][:40] for i in crit[:5]) + " — 해결하거나 --accept-risk로 승인")
    elif phase == "6":
        qa = ws / "09_build" / "qa_report.md"
        if not qa.exists(): reasons.append("09_build/qa_report.md 없음 — harness qa 미실행")
        elif "BLOCKING: 0" not in qa.read_text(encoding="utf-8"): reasons.append("qa_report에 blocking 결함이 남아 있음")
    elif phase == "final":
        fin = ws / "10_final"
        for pat in _FINAL_REQUIRED:
            if not list(fin.glob(pat)): reasons.append(f"10_final/{pat} 없음")
        sp = _slides_path(ws)
        if sp and trace_numbers.run(ws, sp)["untraced"]: reasons.append("최종 trace 실패 — 디자인 중 숫자가 바뀌었는지 확인")
    else:
        reasons.append(f"알 수 없는 phase '{phase}'")

    ok = not reasons
    st.record_gate(phase, ok, reasons); st.save()
    return ok, reasons
```

`SC/harness.py`에 추가:
```python
import gate  # noqa: E402

def cmd_gate(args) -> int:
    ws = _ws_from_args(args)
    ok, reasons = gate.check(ws, args.phase, accept_risk=args.accept_risk)
    print(f"GATE → phase {args.phase}: {'OK' if ok else 'BLOCK'}")
    for r in reasons: print("  -", r)
    return 0 if ok else 1

# SUBCOMMANDS["gate"] = cmd_gate
# parser: p = sub.add_parser("gate"); p.add_argument("phase", choices=["2","3","4","5","6","final"]); p.add_argument("--ws", required=True); p.add_argument("--accept-risk", action="store_true")
```

- [ ] **Step 4: 테스트 통과 확인 (전체)**

Run: `PYTHONUTF8=1 python -m pytest tests -q`
Expected: 모두 통과 (`skipped 1` 허용)

- [ ] **Step 5: 커밋**

```bash
git add -A && git -c user.name="Lee Dong-Geon" -c user.email="leedg.brian@gmail.com" commit -m "feat(gate): 단계 진입 게이트 + harness gate

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

## Part A 완료 기준
- `PYTHONUTF8=1 python -m pytest tests -q` 전부 통과.
- `python plugins/seed-ir/skills/seed-ir/scripts/harness.py init "<시냅스 폴더>" --out tests/_out/ws && harness.py extract --ws <ws>` 실행 시 `01_extract/`에 txt 1개·이미지 6~7장·manifest.json 생성.
- `harness.py --help`에 `init extract status validate trace gate` 6개 서브커맨드 표시.
