# -*- coding: utf-8 -*-
import shutil
import time
import tempfile
import os
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins" / "seed-ir" / "skills" / "seed-ir" / "scripts"
sys.path.insert(0, str(SCRIPTS))

@pytest.fixture
def out_dir(request):
    """테스트별 격리 출력 폴더.

    Dropbox 동기화 폴더 안(tests/_out)에 쓰면 실시간 동기화가 파일을 잠가 rmtree/mkdir가
    간헐적으로 실패하므로 기본은 시스템 임시 폴더를 쓴다. SEED_IR_TEST_OUT로 바꿀 수 있다.
    """
    base = Path(os.environ.get("SEED_IR_TEST_OUT") or Path(tempfile.gettempdir()) / "seed_ir_tests")
    d = base / request.node.name
    for _ in range(5):
        shutil.rmtree(d, ignore_errors=True)
        if not d.exists():
            break
        time.sleep(0.3)
    d.mkdir(parents=True, exist_ok=True)
    return d

@pytest.fixture
def root():
    return ROOT

@pytest.fixture
def assets_dir():
    return ROOT / "plugins" / "seed-ir" / "skills" / "seed-ir" / "assets"
