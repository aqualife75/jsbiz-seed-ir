# -*- coding: utf-8 -*-
import shutil
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins" / "seed-ir" / "skills" / "seed-ir" / "scripts"
sys.path.insert(0, str(SCRIPTS))

@pytest.fixture
def out_dir(request):
    """테스트별 격리 출력 폴더 — 이전 실행 잔재를 지우고 새로 만든다(재실행 flake 방지)."""
    d = ROOT / "tests" / "_out" / request.node.name
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True, exist_ok=True)
    return d

@pytest.fixture
def root():
    return ROOT

@pytest.fixture
def assets_dir():
    return ROOT / "plugins" / "seed-ir" / "skills" / "seed-ir" / "assets"
