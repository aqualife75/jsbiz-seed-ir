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
    return [f"[schema:{name}] {'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}" for e in sorted(v.iter_errors(obj), key=lambda e: [str(x) for x in e.absolute_path])]

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
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return [f"JSON 파싱 실패 {path.name}: {exc}"]
    return validate_obj(obj, _SCHEMA_OF.get(target, target))
