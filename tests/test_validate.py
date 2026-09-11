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
    s = _slides(15)
    errs = validate.validate_obj(s, "slides")
    assert any("12~14" in e for e in errs)
    s = _slides(); del s["slides"][6]["weakness_row"]
    assert any("weakness_row" in e for e in validate.validate_obj(s, "slides"))

def test_deck_spec_limits():
    spec = {"meta": {"team": "T", "accent": "E0492E"}, "slides": [
        {"no": 1, "layout": "statement", "background": "dark", "slots": {"statement": "가" * 80, "sub": "나"}, "source_line": "", "notes": ""}]}
    errs = validate.validate_obj(spec, "deck_spec")
    assert any("statement.statement" in e and "80" in e for e in errs)

def test_validate_phase_reads_file(out_dir):
    (out_dir / "02_fact_pack.json").write_text(json.dumps(_fact_pack(), ensure_ascii=False), encoding="utf-8")
    assert validate.validate_phase(out_dir, "fact_pack") == []
    assert validate.validate_phase(out_dir, "slides")  # 파일 없음 → 오류 메시지
