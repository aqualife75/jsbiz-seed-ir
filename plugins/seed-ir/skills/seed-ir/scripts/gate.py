# -*- coding: utf-8 -*-
"""단계 진입 게이트. 설계서 §3-3."""
from __future__ import annotations
import json, re
from pathlib import Path
import validate, trace_numbers
from state import State

_FINAL_REQUIRED = ["*_Seed_IR_Deck.pptx", "*_Seed_IR_Deck.pdf", "피칭가이드.md", "qa_png"]

def _slides_path(ws: Path) -> Path | None:
    for n in ("07_slides_v2.json", "04_slides_v1.json"):
        if (ws / n).exists(): return ws / n
    return None

def check(ws: Path, phase: str, accept_risk: bool = False) -> tuple[bool, list[str]]:
    ws = Path(ws); reasons: list[str] = []
    st = State.load(ws)
    if accept_risk:
        st.approve("accept_risk")
    risk_ok = accept_risk or st.data["approvals"].get("accept_risk", False)

    if phase == "2":
        reasons += validate.validate_phase(ws, "fact_pack")
    elif phase == "3":
        reasons += validate.validate_phase(ws, "slides")
    elif phase == "4":
        if not (ws / "05_review" / "summary.json").exists(): reasons.append("05_review/summary.json 없음 — 모의심사 미완")
    elif phase == "5":
        sp = _slides_path(ws)
        if not sp: reasons.append("슬라이드 파일 없음")
        else:
            reasons += [f"validate: {e}" for e in validate.validate_phase(ws, "slides", sp)]
            try:
                rep = trace_numbers.run(ws, sp)
                if rep["untraced"]: reasons.append(f"trace: 미추적 숫자 {len(rep['untraced'])}건 (05_review/trace_report.json)")
            except (FileNotFoundError, ValueError) as exc:
                reasons.append(f"trace: {exc}")
            txt = sp.read_text(encoding="utf-8")
            n_fill = len(re.findall(r"\[기입 필요", txt))
            if n_fill: reasons.append(f"[기입 필요] {n_fill}건 잔존 — [확보 필요]로 옮기거나 근거를 채우세요")
        summ = ws / "05_review" / "summary.json"
        if not summ.exists(): reasons.append("05_review/summary.json 없음")
        else:
            issues = json.loads(summ.read_text(encoding="utf-8")).get("issues", [])
            crit = [i for i in issues if i.get("severity") == "critical" and i.get("status") == "open"]
            if crit and not risk_ok:
                reasons.append(f"critical 미해결 {len(crit)}건: " + "; ".join(i["text"][:40] for i in crit[:5]) + " — 해결하거나 --accept-risk로 승인")
    elif phase == "6":
        qa = ws / "09_build" / "qa_report.md"
        if not qa.exists(): reasons.append("09_build/qa_report.md 없음 — harness qa 미실행")
        elif "BLOCKING: 0" not in qa.read_text(encoding="utf-8"): reasons.append("qa_report에 blocking 결함이 남아 있음")
    elif phase == "final":
        fin = ws / "10_final"
        for pat in _FINAL_REQUIRED:
            if not list(fin.glob(pat)): reasons.append(f"10_final/{pat} 없음")
        sp = _slides_path(ws)
        if sp:
            try:
                if trace_numbers.run(ws, sp)["untraced"]: reasons.append("최종 trace 실패 — 디자인 중 숫자가 바뀌었는지 확인")
            except (FileNotFoundError, ValueError):
                pass
    else:
        reasons.append(f"알 수 없는 phase '{phase}'")

    ok = not reasons
    st.record_gate(phase, ok, reasons); st.save()
    return ok, reasons
