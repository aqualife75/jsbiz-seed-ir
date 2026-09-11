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
