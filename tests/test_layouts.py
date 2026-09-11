# -*- coding: utf-8 -*-
import json
import pytest
from pptx import Presentation
import build_deck, validate
from layouts import LAYOUTS

GROUP1 = ["problem_cascade", "problem_grid", "alt_table", "quadrant", "solution_steps", "product_screens", "tech_moat", "mvp_scope"]

def sample_slots(layout: str) -> dict:
    S = {
      "problem_cascade": {"kicker": "02 · PROBLEM 1", "title": "라인은 아는데, **판독은 3명 중 1명**만 합니다", "lead": "검출은 자동인데 최종 판독은 사람이 하고 있습니다.",
          "bars": [{"label": "검출률", "value": 74.7}, {"label": "판독률", "value": 70.9}, {"label": "조치율", "value": 32.4, "tone": "accent"}, {"label": "재발 방지", "value": 15.9, "tone": "accent"}],
          "kpis": [{"big": "1.18조 원", "label": "연간 불량 손실", "source": "협회 2024"}, {"big": "+25.7%", "label": "5년 증가율", "source": "2019→2023"}, {"big": "48.2%", "label": "야간 미판독 비율", "source": "인터뷰 2026"}],
          "quote": {"text": "사진은 찍히는데, 판독을 사람이 하는 순간 라인이 멈춥니다.", "who": "48세 · 공정 관리자 · 자체 인터뷰 (2026.08)"}, "panel_image": None},
      "problem_grid": {"kicker": "02 · PROBLEM 2", "title": "판독은 '귀찮아서'가 아니라 **구조적으로** 끊깁니다", "lead": "4단계 마찰이 반복됩니다.",
          "stats": [{"big": "60%", "label": "14일 내 사용 중단", "source": "Nutrola 2025"}, {"big": "77%", "label": "30일 내 이탈", "source": "Stanford 2024"}, {"big": "1.2%p", "label": "지속 기록 시 개선", "source": "JMIR 2022"}],
          "points": [{"num": "01", "title": "판단 불가", "sub": "몇 그램일까", "desc": "추정 정확도 44%."}, {"num": "02", "title": "입력 마찰", "sub": "검색·선택·수정", "desc": "반찬 단위 입력."},
                     {"num": "03", "title": "사회적 장벽", "sub": "회식 자리", "desc": "앱을 못 꺼냅니다."}, {"num": "04", "title": "해석 부재", "sub": "뭘 바꿀지 모름", "desc": "원인 구분 불가."}],
          "footnote": "PAID-K 44.6/85점 (KJAN 2020)"},
      "alt_table": {"kicker": "03 · ALTERNATIVES 1", "title": "기존 앱은 '측정'을 돕습니다. **'식사'는 사용자 몫**입니다", "lead": "CGM 연동은 성숙했지만 사진 경로는 비어 있습니다.",
          "table": {"columns": ["파스타", "닥터다이어리", "MyFitnessPal", "우리"], "us_col": 3,
                    "rows": [{"label": "기기 무관", "cells": ["✕", "△", "○", "○"]}, {"label": "한식·배달 인식", "cells": ["✕", "△", "✕", "○"]},
                             {"label": "행동 처방", "cells": ["✕", "✕", "✕", "○"]}, {"label": "유료 레퍼런스", "cells": ["다수", "180만 DL", "글로벌", "0건"], "weakness": True}]},
          "premise_note": "공통 전제 — 사용자가 정확히 입력할 것을 가정 (Meade LT et al., 2016)"},
      "quadrant": {"kicker": "03 · ALTERNATIVES 2", "title": "비어 있는 사분면: **기기 없이, 외식에서**", "lead": "경쟁사는 CGM 착용자와 집밥 식단에 몰려 있습니다.",
          "axes": {"x_left": "집밥 · 계획된 식단", "x_right": "외식 · 배달 · 회식", "y_top": "입력 부담 ↑", "y_bottom": "입력 부담 ↓"},
          "bubbles": [{"name": "MyFitnessPal", "sub": "수기 입력", "x": 0.18, "y": 0.28, "size": 1.6}, {"name": "파스타", "sub": "CGM 한정", "x": 0.42, "y": 0.18, "size": 1.6, "tone": "teal"},
                      {"name": "닥터다이어리", "sub": "커뮤니티", "x": 0.3, "y": 0.75, "size": 1.6, "tone": "amber"}, {"name": "글루코핏", "sub": "고가 코칭", "x": 0.48, "y": 0.58, "size": 1.4, "tone": "purple"},
                      {"name": "우리", "sub": "사진 1장 · 외식 특화", "x": 0.77, "y": 0.72, "size": 2.1, "is_us": True}],
          "gaps": [{"title": "GAP 01 · 기기 종속", "desc": "CGM 착용자만 온전한 경험."}, {"title": "GAP 02 · 한식 인식", "desc": "해외 DB는 한식 부정확."}, {"title": "GAP 03 · 처방 부재", "desc": "기록·시각화에서 끝."}]},
      "solution_steps": {"kicker": "04 · SOLUTION", "title": "입력을 없애고, **해석을 남깁니다**", "lead": "사진 한 장 → 인식 → 보정 → 연결 → 처방.",
          "steps": [{"label": "STEP 01", "title": "사진 촬영", "desc": "회식 자리에서도 3초."}, {"label": "STEP 02", "title": "AI 인식", "desc": "한식·배달 특화."}, {"label": "STEP 03", "title": "2탭 보정", "desc": "버튼 두 번."}, {"label": "STEP 04 · 핵심", "title": "혈당 연결", "desc": "다음 끼니 처방."}],
          "cards": [{"num": "01", "title": "입력이 아니라\n촬영입니다", "desc": "음식명 검색·중량 입력 단계를 제거합니다.", "source": "Meade LT et al. 2016"}, {"num": "02", "title": "기기를\n가리지 않습니다", "desc": "자가혈당측정기 두 번 입력으로 동작.", "source": "CGM 급여 확대 2024.12"}, {"num": "03", "title": "숫자가 아니라\n다음 행동을 줍니다", "desc": "실행 가능한 문장으로만 출력.", "source": "※ 생활 관리 참고 정보"}]},
      "product_screens": {"kicker": "05 · PRODUCT 1", "title": "점심 한 끼, **30초**의 사용자 여정", "lead": "촬영부터 가이드까지 버튼 3번.",
          "screens": [{"image": None, "label": "01 · CAPTURE", "title": "촬영 3초", "desc": "앱을 열면 바로 카메라."}, {"mock_lines": ["김치찌개 백반", "추정 탄수화물 78~94g", "공깃밥 210g 68g"], "label": "02 · RECOGNIZE", "title": "범위로 답합니다", "desc": "단일 수치 대신 범위."},
                      {"mock_lines": ["전부 먹음 / 밥 절반", "보정 후 44~52g"], "label": "03 · ADJUST", "title": "타이핑 0회", "desc": "남긴 양을 버튼으로."}, {"mock_lines": ["198 mg/dL", "다음엔 밥 1/3 남기기"], "label": "04 · ACT", "title": "본인 데이터로 설득", "desc": "내 기록의 비교값.", "tone": "accent"}],
          "footnote": "※ 화면은 MVP 설계안이며 수치는 예시입니다."},
      "tech_moat": {"kicker": "05 · PRODUCT 2 · TECHNOLOGY", "title": "한식 데이터가 **이미 존재**합니다", "lead": "공공 데이터셋 100만 장 이상.",
          "data_cards": [{"big": "53.7만 장", "label": "음식 이미지 + 혈당 매칭", "desc": "204종 · 식후혈당 36,091건"}, {"big": "16.2만 장", "label": "외식·배달 메뉴", "desc": "500종"}, {"big": "84.2만 장", "label": "이미지+영양 텍스트", "desc": "400종 이상"}],
          "pipeline": [{"title": "① 인식 레이어", "desc": "사진 → Top-3 후보 + 영역 분할"}, {"title": "② 정량화 레이어", "desc": "영양 DB 매칭 → 탄수화물 범위"}, {"title": "③ 개인화 레이어", "desc": "같은 메뉴 × 같은 사람의 반응 곡선"}],
          "moat": {"title": "\"한식 사진 × 실제 식후 혈당\" 쌍은 국내 누구도 대규모로 보유하지 못했습니다.", "desc": "1만 명 × 하루 2끼 = 연 730만 건 축적"},
          "safety": "혈당 수치를 예측·진단하지 않습니다. 참고 정보만 제공해 의료기기 규제 밖에서 출시합니다."},
      "mvp_scope": {"kicker": "05 · PRODUCT 3 · SCOPE", "title": "무엇을 만들고, **무엇을 만들지 않는가**", "lead": "MVP는 '외식 한 끼를 30초에 닫는 것' 하나에만 집중합니다.",
          "now": [{"title": "① 사진 기반 식사 기록", "desc": "한식·외식·배달 인식"}, {"title": "② 2탭 섭취량 보정", "desc": "타이핑 0회"}, {"title": "③ 혈당 연결", "desc": "수동 입력 + 리마인더"}, {"title": "④ 다음 끼니 가이드", "desc": "실행 문장 1개"}],
          "target_line": "MVP 목표 — 첫 기록 완료율 70% · 보정 완료율 70% · 연결률 60%",
          "not_now": ["✕ 혈당 수치 예측 — 신뢰 안 함, 규제 리스크", "✕ 커뮤니티·커머스 — 닥터다이어리 점유", "✕ 센서 하드웨어 판매", "✕ 인슐린 용량 제안", "✕ 1형 당뇨 대응"],
          "roadmap": [{"label": "V2 · 7~12개월", "title": "CGM 자동 연동", "desc": "다기종 연동·반응 곡선 리포트"}, {"label": "V3 · 13~24개월", "title": "B2B 대시보드", "desc": "교육센터·검진기관용"}, {"label": "V4 · 25개월~", "title": "임상 근거 확보", "desc": "HbA1c 개선 검증"}]},
    }
    return S[layout]

def _spec_for(layouts, out_dir):
    slides = []
    for i, lay in enumerate(layouts, 1):
        bg = "dark" if lay in ("problem_cascade", "quadrant", "tech_moat") else "cream"
        slides.append({"no": i, "layout": lay, "background": bg, "slots": sample_slots(lay), "source_line": f"출처: 샘플 {lay} · 수집 2026-09-11", "notes": f"{lay} 대본"})
    spec = {"meta": {"team": "셀아이", "assets_dir": str(out_dir)}, "slides": slides}
    p = out_dir / "spec.json"; p.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8"); return p, spec

@pytest.mark.parametrize("layout", GROUP1)
def test_group1_builds_without_warnings(layout, out_dir):
    assert layout in LAYOUTS
    p, spec = _spec_for([layout], out_dir)
    assert validate.validate_obj(spec, "deck_spec") == []
    rep = build_deck.build(p, out_dir / f"{layout}.pptx")
    assert rep["warnings"] == [], rep["warnings"]
    prs = Presentation(str(out_dir / f"{layout}.pptx"))
    texts = "\n".join(sh.text_frame.text for sh in prs.slides[0].shapes if sh.has_text_frame)
    assert "1 / 1" in texts and "출처: 샘플" in texts

def test_alt_table_marks_weakness(out_dir):
    p, _ = _spec_for(["alt_table"], out_dir)
    build_deck.build(p, out_dir / "t.pptx")
    prs = Presentation(str(out_dir / "t.pptx"))
    tables = [sh for sh in prs.slides[0].shapes if sh.has_table]
    assert tables and tables[0].table.cell(4, 4).text == "0건"
