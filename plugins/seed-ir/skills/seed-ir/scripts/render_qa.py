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
