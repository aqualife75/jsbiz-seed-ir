# -*- coding: utf-8 -*-
import json
from pathlib import Path
from PIL import Image
import harness, state

def _inputs(out_dir: Path) -> Path:
    d = out_dir / "in"; d.mkdir(parents=True, exist_ok=True)
    (d / "2026년 제16회 포스텍 창업경진대회_참가신청서_시냅스_김준형.txt").write_text("사업계획서 본문 1,234명", encoding="utf-8")
    Image.new("RGB", (200, 100), (9, 9, 9)).save(d / "제품.png")
    return d

def test_infer_team(out_dir):
    d = _inputs(out_dir)
    assert harness.infer_team(d) == "시냅스"

def test_init_creates_workspace(out_dir):
    d = _inputs(out_dir)
    rc = harness.main(["init", str(d), "--out", str(out_dir / "ws")])
    assert rc == 0
    ws = next((out_dir / "ws").glob("*_시냅스_SeedIR"))
    st = json.loads((ws / "state.json").read_text(encoding="utf-8"))
    assert st["team"] == "시냅스" and st["phases"]["1_facts"]["status"] == "pending"
    inputs = json.loads((ws / "inputs.json").read_text(encoding="utf-8"))
    assert len(inputs["files"]) == 2

def test_extract_writes_dumps_and_manifest(out_dir):
    d = _inputs(out_dir)
    harness.main(["init", str(d), "--out", str(out_dir / "ws"), "--team", "테스트팀"])
    ws = next((out_dir / "ws").glob("*_테스트팀_SeedIR"))
    assert harness.main(["extract", "--ws", str(ws)]) == 0
    man = json.loads((ws / "01_extract" / "manifest.json").read_text(encoding="utf-8"))
    assert man["total_chars"] > 0 and man["total_images"] == 1
    assert (ws / "01_extract" / "images").exists()
    txts = list((ws / "01_extract").glob("*.txt"))
    assert len(txts) == 1 and "1,234명" in txts[0].read_text(encoding="utf-8")

def test_state_roundtrip(out_dir):
    ws = out_dir / "ws2"; ws.mkdir(exist_ok=True)
    st = state.State.new(ws, team="T", input_dir=str(ws))
    st.set_phase("1_facts", "done", "ok"); st.record_gate("2", True, []); st.approve("accept_risk"); st.save()
    st2 = state.State.load(ws)
    assert st2.data["phases"]["1_facts"]["status"] == "done"
    assert st2.data["gates"]["2"]["ok"] is True and st2.data["approvals"]["accept_risk"] is True
