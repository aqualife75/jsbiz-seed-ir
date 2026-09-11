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
        # 같은 슬라이드의 evidence/key_numbers 중 calc가 완전히 추적된 항목은
        # 그 결과 숫자를 이 슬라이드의 title/lead/weakness_row에서도 허용한다
        # (이미 검증된 동일 숫자를 제목 등에서 재진술하는 경우를 오탐하지 않기 위함).
        verified = set()
        for e in s.get("evidence", []):
            calc = e.get("calc")
            if calc:
                calc_toks = tokens(calc)
                if calc_toks and calc_toks <= allowed:
                    verified |= tokens(e.get("text", ""))
        for k in s.get("key_numbers", []):
            calc = k.get("calc")
            if calc:
                calc_toks = tokens(calc)
                if calc_toks and calc_toks <= allowed:
                    verified |= tokens(f"{k.get('value','')}{k.get('unit','')}")
        field_allowed = allowed | verified
        for f in _FIELDS:
            if s.get(f): _check_text(no, f, s[f], field_allowed, out)
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
