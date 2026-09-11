# -*- coding: utf-8 -*-
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins" / "seed-ir" / "skills" / "seed-ir" / "scripts"
sys.path.insert(0, str(SCRIPTS))

@pytest.fixture
def out_dir(request):
    d = ROOT / "tests" / "_out" / request.node.name
    d.mkdir(parents=True, exist_ok=True)
    return d

@pytest.fixture
def root():
    return ROOT

@pytest.fixture
def assets_dir():
    return ROOT / "plugins" / "seed-ir" / "skills" / "seed-ir" / "assets"
