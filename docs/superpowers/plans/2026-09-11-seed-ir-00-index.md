# jsbiz-seed-ir 구현 계획 — 인덱스

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 설계서 `docs/superpowers/specs/2026-09-11-seed-ir-harness-design.md`대로, 창업팀 자료 폴더 → KDB 12주제 기준 Seed IR Deck(PPTX+PDF+피칭가이드)을 6개 에이전트가 만들고 스크립트가 숫자 추적·게이트를 강제하는 Claude Code 플러그인 `seed-ir`를 완성한다.

**Architecture:** 결정적 작업(추출·검증·숫자 추적·게이트·빌드·렌더)은 `plugins/seed-ir/skills/seed-ir/scripts/`의 Python CLI `harness.py`가, 판단 작업은 `plugins/seed-ir/agents/`의 6개 서브에이전트가, 순서·게이트·재개는 `skills/seed-ir/SKILL.md` 오케스트레이터가 맡는다. 워크스페이스 `{날짜}_{팀명}_SeedIR/`에 번호순 JSON 산출물과 `state.json`이 쌓인다.

**Tech Stack:** Python 3.10+, python-pptx 1.0.x, PyMuPDF, Pillow, olefile, python-docx, openpyxl, jsonschema, pytest. Node 없음. 렌더는 PowerPoint COM(Windows) / LibreOffice(Mac) 폴백.

## Global Constraints (모든 태스크 공통)
- 저장소 루트: `00. A_B_정석Biz/99. 프로젝트/2026.09.11_seed-ir-deck_하네스/jsbiz-seed-ir/` — 이하 경로는 모두 이 루트 기준.
- 스크립트는 저장소 안에서 자족한다. Dropbox `.claude/*.py`를 import 하지 않는다.
- Python 파일 첫 줄에 `# -*- coding: utf-8 -*-`, 표준 출력은 `sys.stdout.reconfigure(encoding="utf-8")` 시도.
- 테스트 실행은 항상 `PYTHONUTF8=1 python -m pytest tests -q` (Windows Git Bash). 테스트가 만드는 파일은 `tests/_out/`(gitignore).
- 커밋 메시지 끝에 `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`. git 사용자: `-c user.name="Lee Dong-Geon" -c user.email="leedg.brian@gmail.com"`.
- 폰트는 Pretendard 단일, 캔버스 20×11.25in, 팔레트는 설계서 §5-1 값 그대로(`design_system.py`가 유일한 원천).
- 숫자 창작 금지 규칙은 에이전트 프롬프트와 `trace_numbers.py` 양쪽에서 강제한다.
- 한국어 산출물. 코드 주석은 한국어 또는 영어 혼용 허용.
- 실제 참가팀 자료(개인정보)는 저장소에 절대 커밋하지 않는다(`.gitignore`에 `_seed_ir_test/`, `*_SeedIR/`).

## 파트 (실행 순서)
| 파트 | 파일 | 태스크 | 산출 |
|---|---|---|---|
| A 하네스 코어 | [A](2026-09-11-seed-ir-A-harness-core.md) | 1~7 | 스캐폴드·추출기 7종·state·validate·trace·gate·CLI |
| B 덱 빌더 | [B](2026-09-11-seed-ir-B-deck-builder.md) | 8~13 | 디자인 토큰·이미지 전처리·레이아웃 22종·render_qa·pdf |
| C 지식·에이전트·오케스트레이터 | [C](2026-09-11-seed-ir-C-agents-orchestrator.md) | 14~17 | references 8·capture_evidence·agents 6·SKILL.md |
| D 배포·검증 | [D](2026-09-11-seed-ir-D-distribution-validation.md) | 18~21 | docs/index.html·README·evals·로컬 설치·시냅스 통합 실행·GitHub |

파트 간 인터페이스는 각 태스크의 **Interfaces** 블록에 적혀 있다. A→B→C→D 순서로 실행하되, B와 C의 14(references)는 A 완료 후 병렬 가능.

## 파일 구조 (전체)
```
jsbiz-seed-ir/
├── .claude-plugin/marketplace.json
├── .gitignore  LICENSE  README.md  requirements.txt  pytest.ini
├── plugins/seed-ir/
│   ├── .claude-plugin/plugin.json
│   ├── agents/{ir-intake,ir-writer,ir-panel,ir-researcher,ir-designer,ir-finalizer}.md
│   └── skills/seed-ir/
│       ├── SKILL.md
│       ├── references/{kdb_12_topics,investor_lenses,writing_rules,review_rubric,evidence_policy,design_system,pitch_5min,qa_checklist}.md
│       ├── scripts/
│       │   ├── harness.py  state.py  validate.py  trace_numbers.py  gate.py
│       │   ├── design_system.py  prep_image.py  build_deck.py  layouts/{__init__,base,l_cover_intro,l_problem,l_solution,l_market_bm,l_plan_team}.py
│       │   ├── render_qa.py  capture_evidence.py
│       │   └── extractors/{__init__,hwp,hwpx,pdf,docx,pptx,xlsx,images}.py
│       └── assets/
│           ├── schemas/{fact_pack,image_catalog,storyline,slides,review_summary,evidence,image_ledger,deck_spec}.schema.json
│           ├── limits.json
│           └── spec.example.json
├── docs/index.html
├── docs/superpowers/{specs,plans}/…
├── evals/evals.json  evals/fixtures/셀아이/{사실팩.md, 이미지/*.png}
└── tests/{conftest,test_scaffold,test_hwp,test_extractors,test_harness,test_validate,test_trace,test_gate,test_prep_image,test_build,test_layouts,test_render_qa,test_references,test_capture,test_agents,test_docs}.py
```
