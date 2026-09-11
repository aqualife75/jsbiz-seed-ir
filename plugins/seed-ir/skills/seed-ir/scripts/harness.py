# -*- coding: utf-8 -*-
"""seed-ir 하네스 CLI. 결정적 작업(추출·검증·추적·게이트·빌드·렌더)만 담당한다.

사용:
  python harness.py init <입력폴더> [--team 팀명] [--out 폴더]
  python harness.py extract --ws <워크스페이스>
  python harness.py status  --ws <워크스페이스>
  (Task 5~7, 13에서 validate / trace / gate / build / qa / pdf 추가)
"""
from __future__ import annotations
import argparse, json, re, sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import extractors  # noqa: E402
from state import State, PHASES  # noqa: E402

_TEAM_RE = re.compile(r"참가신청서_(.+?)_[^_]+\.[A-Za-z0-9]+$")  # 포스텍 파일명 규칙: …_참가신청서_{팀명}_{팀장}.hwp

def infer_team(input_dir: Path) -> str:
    for f in sorted(Path(input_dir).iterdir()):
        m = _TEAM_RE.search(f.name)
        if m:
            return m.group(1).strip()
    return Path(input_dir).name.strip()

def _ws_from_args(args) -> Path:
    ws = Path(args.ws).resolve()
    if not (ws / "state.json").exists():
        sys.exit(f"[오류] 워크스페이스가 아닙니다: {ws}")
    return ws

def cmd_init(args) -> int:
    src = Path(args.input_dir).resolve()
    if not src.is_dir():
        print(f"[오류] 입력 폴더 없음: {src}"); return 1
    team = args.team or infer_team(src)
    out_root = Path(args.out).resolve() if args.out else src.parent
    ws = out_root / f"{datetime.now():%Y.%m.%d}_{team}_SeedIR"
    ws.mkdir(parents=True, exist_ok=True)
    files = []
    for f in sorted(src.rglob("*")):
        if f.is_file() and not f.name.startswith(("~$", ".")):
            files.append({"path": str(f), "name": f.name, "ext": f.suffix.lower(), "size": f.stat().st_size,
                          "supported": f.suffix.lower() in extractors.SUPPORTED})
    (ws / "inputs.json").write_text(json.dumps({"input_dir": str(src), "files": files}, ensure_ascii=False, indent=2), encoding="utf-8")
    State.new(ws, team=team, input_dir=str(src))
    (ws / "run_log.md").write_text(f"# {team} Seed IR 실행 로그\n\n- init {datetime.now():%Y-%m-%d %H:%M} · 입력 {len(files)}개\n", encoding="utf-8")
    print(f"WS={ws}")
    print(f"team={team} files={len(files)} unsupported={sum(1 for f in files if not f['supported'])}")
    return 0

def cmd_extract(args) -> int:
    ws = _ws_from_args(args)
    inputs = json.loads((ws / "inputs.json").read_text(encoding="utf-8"))
    ex = ws / "01_extract"; img_dir = ex / "images"; ex.mkdir(exist_ok=True); img_dir.mkdir(exist_ok=True)
    manifest = {"files": [], "total_chars": 0, "total_images": 0, "warnings": []}
    for f in inputs["files"]:
        if not f["supported"]:
            manifest["warnings"].append(f"미지원 건너뜀: {f['name']}"); continue
        res = extractors.extract_file(f["path"], img_dir)
        stem = Path(f["name"]).stem[:60]
        txt = ex / f"{stem}.txt"
        if res["text"].strip():
            txt.write_text(res["text"], encoding="utf-8")
        manifest["files"].append({"name": f["name"], "kind": res["kind"], "text_path": str(txt) if res["text"].strip() else None,
                                  "chars": len(res["text"]), "images": res["images"], "warnings": res["warnings"]})
        manifest["total_chars"] += len(res["text"]); manifest["total_images"] += len(res["images"])
        manifest["warnings"].extend(f"{f['name']}: {w}" for w in res["warnings"])
    (ex / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"extracted files={len(manifest['files'])} chars={manifest['total_chars']:,} images={manifest['total_images']} warnings={len(manifest['warnings'])}")
    for w in manifest["warnings"][:20]:
        print("  !", w)
    return 0

def cmd_status(args) -> int:
    ws = _ws_from_args(args); st = State.load(ws)
    print(f"팀: {st.data['team']}  WS: {ws}")
    for p in PHASES:
        ph = st.data["phases"][p]
        print(f"  {p:12s} {ph['status']:8s} {ph.get('finished') or ph.get('started') or ''}  {ph.get('note','')}")
    for g, v in st.data["gates"].items():
        print(f"  gate→{g}: {'OK' if v['ok'] else 'BLOCK'} {'; '.join(v['reasons'])}")
    return 0

SUBCOMMANDS = {"init": cmd_init, "extract": cmd_extract, "status": cmd_status}

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="harness.py", description="seed-ir 하네스")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init"); p.add_argument("input_dir"); p.add_argument("--team"); p.add_argument("--out")
    for name in ("extract", "status"):
        p = sub.add_parser(name); p.add_argument("--ws", required=True)
    return ap

def main(argv=None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    return SUBCOMMANDS[args.cmd](args)

if __name__ == "__main__":
    raise SystemExit(main())
