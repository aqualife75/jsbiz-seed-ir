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
