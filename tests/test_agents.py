# -*- coding: utf-8 -*-
import re
from pathlib import Path

AG = Path(__file__).resolve().parents[1] / "plugins/seed-ir/agents"
NAMES = ["ir-intake", "ir-writer", "ir-panel", "ir-researcher", "ir-designer", "ir-finalizer"]

def _front(name):
    t = (AG / f"{name}.md").read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", t, re.S); assert m, name
    return m.group(1), m.group(2)

def test_agents_exist_with_frontmatter_and_no_model():
    for n in NAMES:
        fm, body = _front(n)
        assert f"name: {n}" in fm and "description:" in fm and "tools:" in fm
        assert not re.search(r"^model:", fm, re.M), f"{n}: model 필드 금지"
        assert "WS=" in body and "SKILL_DIR=" in body

def test_tool_sets():
    assert "WebSearch" in _front("ir-researcher")[0] and "WebFetch" in _front("ir-researcher")[0]
    assert "WebSearch" not in _front("ir-writer")[0]
    assert "Bash" in _front("ir-designer")[0]

def test_rules_present():
    for n in NAMES:
        body = _front(n)[1]
        assert "없는 숫자" in body or "숫자를 만들" in body, n
