# -*- coding: utf-8 -*-
"""저장소 → 로컬 .claude 설치본 동기화. python scripts/install_local.py --target "D:/BRIAN Dropbox/Lee Dong-Geon/.claude" """
import argparse, shutil
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--target", required=True); a = ap.parse_args()
    tgt = Path(a.target)
    skill_src = ROOT / "plugins/seed-ir/skills/seed-ir"; skill_dst = tgt / "skills/seed-ir"
    if skill_dst.exists(): shutil.rmtree(skill_dst)
    skill_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(skill_src, skill_dst, ignore=shutil.ignore_patterns("__pycache__"))
    (tgt / "agents").mkdir(parents=True, exist_ok=True)
    for f in (ROOT / "plugins/seed-ir/agents").glob("*.md"): shutil.copy(f, tgt / "agents" / f.name)
    print(f"installed → {skill_dst} + agents/ir-*.md")


if __name__ == "__main__": main()
