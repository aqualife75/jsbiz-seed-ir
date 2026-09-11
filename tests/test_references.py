# -*- coding: utf-8 -*-
from pathlib import Path
import re

R = Path(__file__).resolve().parents[1] / "plugins/seed-ir/skills/seed-ir/references"
FILES = ["jsbiz_12_topics", "investor_lenses", "writing_rules", "review_rubric", "evidence_policy", "design_system", "pitch_5min", "qa_checklist"]

def test_all_reference_files_exist_with_title():
    for f in FILES:
        p = R / f"{f}.md"; assert p.exists(), f
        assert p.read_text(encoding="utf-8").startswith("# "), f

def test_jsbiz_topics_has_12_rows_and_questions():
    t = (R / "jsbiz_12_topics.md").read_text(encoding="utf-8")
    for k in ["| 1 | 표지", "| 6 | 시장 규모", "| 12 | 자금 조달 계획", "투자자의 질문", "작성 가이드", "증거 우선순위", "Navigator", "Governing Message"]:
        assert k in t, k

def test_rubric_has_five_personas_and_severity():
    t = (R / "review_rubric.md").read_text(encoding="utf-8")
    for k in ["vc", "ac", "domain", "finance", "layman", "critical", "major", "minor", "O/△/X"]:
        assert k in t, k

def test_evidence_policy_targets_and_tiers():
    t = (R / "evidence_policy.md").read_text(encoding="utf-8")
    assert "Tier A" in t and "Tier C" in t and "needs_human_review" in t and "외부 대체 금지" in t

def test_design_system_lists_22_layouts():
    t = (R / "design_system.md").read_text(encoding="utf-8")
    for lay in ["cover", "statement", "trend_cards", "problem_cascade", "problem_grid", "alt_table", "quadrant", "solution_steps", "product_screens", "tech_moat", "mvp_scope", "traction_plan", "kpi_chart", "bm_pricing", "market_tam", "gtm_funnel", "growth_phases", "milestone_gates", "team_cards", "vision_close", "appendix_qa", "evidence_capture"]:
        assert f"`{lay}`" in t, lay
    assert "E0492E" in t and "Pretendard" in t

def test_pitch_timing_sums_to_300():
    t = (R / "pitch_5min.md").read_text(encoding="utf-8")
    secs = [int(m) for m in re.findall(r"\|\s*(\d{2,3})\s*\|", t.split("## 시간 배분")[1].split("##")[0])]
    assert sum(secs[:-1]) == 300 and secs[-1] == 300
