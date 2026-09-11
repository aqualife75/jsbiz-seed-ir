# -*- coding: utf-8 -*-
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_marketplace_manifest():
    m = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    assert m["name"] == "jsbiz-seed-ir"
    assert m["plugins"][0]["name"] == "seed-ir"
    assert m["plugins"][0]["source"] == "./plugins/seed-ir"

def test_plugin_manifest():
    p = json.loads((ROOT / "plugins/seed-ir/.claude-plugin/plugin.json").read_text(encoding="utf-8"))
    assert p["name"] == "seed-ir"
    assert p["version"].count(".") == 2

def test_requirements_lists_core_libs():
    req = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    for lib in ["python-pptx", "pymupdf", "pillow", "olefile", "python-docx", "openpyxl", "jsonschema"]:
        assert lib in req.lower()
