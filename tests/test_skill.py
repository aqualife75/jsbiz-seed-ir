# -*- coding: utf-8 -*-
import re
from pathlib import Path
S = Path(__file__).resolve().parents[1] / "plugins/seed-ir/skills/seed-ir/SKILL.md"

def test_skill_frontmatter_and_phases():
    t = S.read_text(encoding="utf-8")
    assert t.startswith("---\nname: seed-ir\n") and "description:" in t
    for k in ["HARNESS init", "HARNESS extract --ws", "gate 2", "gate 3", "gate 4", "gate 5", "gate 6", "gate final", "ir-intake", "ir-writer", "ir-panel", "ir-researcher", "ir-designer", "ir-finalizer", "PERSONA=chair", "MODE=merge", "MODE=storyline", "--accept-risk", "--resume", "WS=", "SKILL_DIR=", "scripts/harness.py"]:
        assert k in t, k
    assert "model" not in re.match(r"^---\n(.*?)\n---", t, re.S).group(1)
