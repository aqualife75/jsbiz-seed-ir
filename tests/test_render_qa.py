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
