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
