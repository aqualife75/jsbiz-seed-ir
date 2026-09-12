# -*- coding: utf-8 -*-
"""디자인 토큰 — 정석Biz 표준(설계서 §5-1). 이 파일이 유일한 원천."""
CANVAS_W, CANVAS_H = 20.0, 11.25
FONT = "Pretendard"
BG = {"dark": "10141B", "cream": "F5F2EB"}
C = {
    "ink": "10141B", "white": "FFFFFF", "sub": "5C6572", "muted": "8A93A0", "sub_dark": "B3BAC4", "muted_dark": "6B7480",
    "card_border": "E6E2DA", "card_dark": "1A2130", "accent": "E0492E", "accent_dark": "FF6A4D", "amber": "F2A33C",
    "teal": "4FD1C5", "teal_deep": "177B72", "purple": "8A5BD6", "gradient_end": "F2A33C", "accent_tint": "FBE9E5", "amber_tint": "FDF3E3",
}
SZ = {"kicker": 12.75, "title": 49.5, "title_sm": 42.0, "statement": 60.0, "lead": 18.75, "label": 11.25, "big": 49.5, "big_md": 36.0,
      "big_sm": 27.0, "unit": 15.75, "body": 14.25, "body_sm": 13.5, "small": 12.0, "source": 10.5, "page": 10.5, "card_title": 20.25}
MX, CW, GAP = 1.125, 17.75, 0.25
KICKER_Y, TITLE_Y, LEAD_Y = 0.78, 1.15, 2.95
BODY_Y, BODY_B = 3.90, 10.30
SRC_Y = 10.50
PANEL_X, PANEL_W = 12.5, 7.5
RADIUS_ADJ = 0.02  # roundRect adjustment (≈8px)

def accent(bg: str) -> str: return C["accent_dark"] if bg == "dark" else C["accent"]
def ink(bg: str) -> str: return C["white"] if bg == "dark" else C["ink"]
def sub(bg: str) -> str: return C["sub_dark"] if bg == "dark" else C["sub"]
def muted(bg: str) -> str: return C["muted_dark"] if bg == "dark" else C["muted"]
def card_style(bg: str) -> dict:
    if bg == "dark":
        return {"fill": "FFFFFF", "alpha": 4, "line": "FFFFFF", "line_alpha": 10}
    return {"fill": "FFFFFF", "alpha": None, "line": C["card_border"], "line_alpha": None}
def col_w(n: int, total: float = CW, gap: float = GAP) -> float: return (total - (n - 1) * gap) / n
