# -*- coding: utf-8 -*-
import json
import pytest
from pptx import Presentation
import build_deck, validate
from layouts import LAYOUTS

GROUP1 = ["problem_cascade", "problem_grid", "alt_table", "quadrant", "solution_steps", "product_screens", "tech_moat", "mvp_scope"]
GROUP2 = ["traction_plan", "kpi_chart", "bm_pricing", "market_tam", "gtm_funnel", "growth_phases"]

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
      "traction_plan": {"kicker": "06 · EARLY TRACTION", "title": "말이 아니라 **결제와 행동**으로 검증합니다", "lead": "9,900원 예약금 결제와 7일 기록 로그만 지표로 인정합니다.",
          "weeks": [{"label": "WEEK 1 · 문제 인터뷰", "big": "8명", "desc": "솔루션 화면은 마지막 10분까지 감춥니다."}, {"label": "WEEK 2 · 사용성 테스트", "big": "7명", "desc": "실제 식사 사진 3장으로 전 과정 수행."},
                    {"label": "WEEK 3 · 7일 기록 실험", "big": "10명 · 핵심 관문", "desc": "5회 기록·3회 보정·2회 연결 달성자만 환급.", "tone": "dark"}, {"label": "WEEK 4 · 통합 분석", "big": "고객군별 비교", "desc": "3개 군 완료율·전환률 비교."}],
          "table": {"rows": [{"metric": "문제 공감률", "target": "70% 이상", "method": "최근 30일 실제 사례 진술"}, {"metric": "솔루션 사용 의향", "target": "50% 이상", "method": "9,900원 예약금 실제 결제"},
                             {"metric": "지불 의향", "target": "30% 이상", "method": "월 14,900원 사전 결제"}, {"metric": "첫 기록 완료율", "target": "70% 이상", "method": "업로드–확인–보정 로그"}]},
          "side": {"title": "확보한 모집 채널 20곳", "body": "온라인 커뮤니티 10곳, 교육센터 5곳, 학회·전시 5곳"},
          "insight": "1차 인터뷰 확인 — 예측 기능 신뢰 안 함 → MVP에서 제외"},
      "kpi_chart": {"kicker": "06 · TRACTION", "title": "월 활성 사용자 **3개월 연속 40% 성장**", "lead": "베타 출시 이후 실측 지표입니다.",
          "chart": {"type": "column", "categories": ["6월", "7월", "8월", "9월"], "series": [{"name": "MAU", "values": [120, 170, 240, 335]}], "unit": "명"},
          "kpis": [{"big": "335명", "label": "9월 MAU", "source": "자체 대시보드"}, {"big": "+40%", "label": "월 성장률", "source": "3개월 평균"}, {"big": "38%", "label": "7일 리텐션", "source": "코호트"}], "note": "출시 전 팀은 이 장 대신 traction_plan을 쓴다."},
      "bm_pricing": {"kicker": "07 · BUSINESS MODEL", "title": "기기를 팔지 않습니다. **습관을 구독**합니다", "lead": "소프트웨어 구독 단일 축으로 시작합니다.",
          "tiers": [{"label": "FREE", "price": "무료", "sub": "획득 단계", "bullets": ["하루 2끼 사진 기록", "탄수화물 범위 추정", "혈당 수동 입력"], "note": "첫 7일 기록 완료가 전환 선행 지표."},
                    {"label": "PRO · 핵심 수익원", "price": "월 14,900원", "sub": "연 결제 시 월 11,900원", "bullets": ["무제한 기록 + CGM 연동", "개인별 반응 곡선", "다음 끼니 가이드"], "note": "경쟁 월 27,900원 대비 47% 낮은 가격.", "highlight": True},
                    {"label": "B2B2C · 13개월~", "price": "계약 단가", "sub": "보험사 · 검진기관", "bullets": ["단체 라이선스", "사후관리 리포트", "상담 보조 도구"], "note": "닥터다이어리–한독 제휴가 선례."}],
          "unit_econ": [{"label": "ARPU", "big": "13,400원/월", "sub": "월·연 혼합 가정"}, {"label": "월 이탈률 목표", "big": "6% 이하", "sub": "평균 유지 16.7개월"}, {"label": "LTV", "big": "약 224,000원", "sub": "ARPU × 유지 개월"}, {"label": "목표 LTV/CAC", "big": "3.0배 이상", "sub": "CAC 상한 7.5만 원"}],
          "evidence_note": "비대면 건강관리에 월평균 10만 5,000원 지불 경험 (보건사회연구원 2023)"},
      "market_tam": {"kicker": "08 · MARKET SIZE", "title": "1,939만 명의 혈당 관리 인구, **9,700억 원**의 국내 잠재 시장", "lead": "수익 모델 기반으로 SOM → SAM → TAM 순서로 계산했습니다.",
          "tam": {"label": "TAM · 국내 혈당 관리 대상 인구", "desc": "당뇨 530만 + 전단계 1,409만 = 1,939만 명", "big": "9,700", "unit": "억원", "calc": "1,939만 명 × 연 5만 원"},
          "sam": {"label": "SAM · 외식 비중 높은 당뇨인", "desc": "30~64세 당뇨인 중 170만~200만 명", "big": "2,730", "unit": "억원", "calc": "170만 × 13,400원 × 12"},
          "som": {"label": "SOM · 3년 내 확보 목표", "desc": "SAM의 5~10% · 유료 10만~20만 명", "big": "180~360", "unit": "억원", "calc": "연 환산 매출"},
          "side_stats": [{"label": "글로벌 디지털 당뇨 관리", "big": "$13.4B → $21.9B", "sub": "2024→2030, CAGR 8.7%", "source": "Grand View Research"}, {"label": "국내 디지털헬스케어", "big": "6조 4,930억 원", "sub": "2023, 전년比 +13.5%", "source": "KODHIA 2024"}, {"label": "공적 지출", "big": "1.18조 원", "sub": "당뇨 진료비, 5년 +25.7%", "source": "HIRA 2024"}],
          "sanity_note": "국내 1위 닥터다이어리는 누적 180만 DL로 2024년 매출 150억 원. SOM 하단(연 180억)은 시장이 증명한 범위 안에 있습니다."},
      "gtm_funnel": {"kicker": "09 · GO-TO-MARKET", "title": "전국이 아니라 **성남·강남 직장인**부터", "lead": "첫 1,000명은 광고로 사지 않습니다.",
          "beachhead": {"title": "주 3회 이상 외식·배달\n35~55세 당뇨 직장인", "why": "문제 빈도 최고, 본인 결제 의사결정권자.", "exclude": "인슐린 조절 잦은 환자, 1형 당뇨는 MVP 범위 밖."},
          "channels": [{"title": "1순위 · 병원 교육센터 5곳", "desc": "교육 후 자발 신청 방식으로만 모집."}, {"title": "2순위 · 당뇨 커뮤니티 10곳", "desc": "7일 기록 실험 참여자 공모."}, {"title": "3순위 · 유튜브 당뇨 채널", "desc": "유료 광고는 PMF 확인 후."}],
          "funnel": [{"label": "STEP 1 · 도달", "big": "20,000", "unit": "명", "desc": "게시물·안내문 노출"}, {"label": "STEP 2 · 신청", "big": "4,000", "unit": "명", "desc": "사전 선별 폼"}, {"label": "STEP 3 · 설치", "big": "2,400", "unit": "명", "desc": "첫 사진 업로드"},
                     {"label": "STEP 4 · 습관화", "big": "1,680", "unit": "명", "desc": "7일 중 5회 기록"}, {"label": "STEP 5 · 결제", "big": "1,000", "unit": "명", "desc": "유료 전환 60%", "tone": "dark"}],
          "footnote": "전환율은 4주 검증 목표 지표 기준 자체 가정이며 1차 결과에 따라 조정합니다."},
      "growth_phases": {"kicker": "10 · GROWTH STRATEGY", "title": "개인 구독에서 채널 계약으로, **기록에서 근거**로", "lead": "성장은 광고비가 아니라 데이터 축적의 함수입니다.",
          "phases": [{"label": "PHASE 1 · 0~12개월", "title": "습관을 증명한다", "desc": "유료 1,000명, 월 이탈 6% 이하.", "kpi": "7일 기록 70% · 연결률 60%"}, {"label": "PHASE 2 · 13~24개월", "title": "채널로 확장한다", "desc": "보험사·검진기관 B2B2C 계약.", "kpi": "계약 3건 · 유료 3만 명"}, {"label": "PHASE 3 · 25개월~", "title": "근거를 자산화한다", "desc": "HbA1c 개선 임상 검증.", "kpi": "논문 1편 · 유료 10만 명"}],
          "flywheel": ["사진을 찍는다", "인식률이 오른다", "반응 곡선이 정교해진다", "이탈이 줄고 LTV가 는다"],
          "expansion": "당뇨 전단계 1,409만 명, 임신성 당뇨, 만성신장질환 — 엔진은 그대로, 가이드 규칙만 교체."},
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

@pytest.mark.parametrize("layout", GROUP2)
def test_group2_builds_without_warnings(layout, out_dir):
    p, spec = _spec_for([layout], out_dir)
    assert validate.validate_obj(spec, "deck_spec") == []
    rep = build_deck.build(p, out_dir / f"{layout}.pptx")
    assert rep["warnings"] == [], rep["warnings"]

def test_kpi_chart_has_native_chart(out_dir):
    p, _ = _spec_for(["kpi_chart"], out_dir); build_deck.build(p, out_dir / "k.pptx")
    prs = Presentation(str(out_dir / "k.pptx"))
    assert any(sh.has_chart for sh in prs.slides[0].shapes)
