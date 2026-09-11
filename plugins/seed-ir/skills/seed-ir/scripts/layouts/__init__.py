# -*- coding: utf-8 -*-
"""레이아웃 레지스트리. 각 l_*.py가 import 시 register()로 등록한다."""
from __future__ import annotations
from typing import Callable
LAYOUTS: dict[str, Callable] = {}

def register(name: str):
    def deco(fn):
        LAYOUTS[name] = fn; return fn
    return deco

from . import l_cover_intro  # noqa: E402,F401
from . import l_problem, l_solution  # noqa: E402,F401
from . import l_market_bm  # noqa: E402,F401
# Task 12에서 추가: from . import l_plan_team
