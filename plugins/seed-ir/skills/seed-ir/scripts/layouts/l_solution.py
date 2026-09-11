# -*- coding: utf-8 -*-
from . import register
from .l_problem import _chrome, _TONE
import design_system as ds

@register("solution_steps")
def solution_steps(cv, s, slide):
    _chrome(cv, s, slide)
    steps = s.get("steps") or []; y = ds.BODY_Y; h = 2.2
    if steps:
        n = len(steps); w = ds.CW / n
        for i, st in enumerate(steps):
            x = ds.MX + i * w; last = (i == n - 1)
            cv.rect(x, y, w, h, fill=ds.C["card_dark"] if not last else ds.C["muted"], alpha=None if not last else 35, radius=(i == 0 or last))
            cv.label(x + 0.45, y + 0.35, w - 0.9, st.get("label", ""), color=ds.C["amber"] if not last else ds.C["accent"])
            cv.text(x + 0.45, y + 0.75, w - 0.9, 0.5, st.get("title", ""), ds.SZ["card_title"], ds.C["white"], bold=True, max_lines=1, slot="steps.title")
            cv.text(x + 0.45, y + 1.3, w - 0.9, 0.8, st.get("desc", ""), ds.SZ["body_sm"], ds.C["sub_dark"], line_spacing=1.4, max_lines=2, slot="steps.desc")
            if i < n - 1: cv.rect(x + w - 0.35, y + h / 2, 0.3, 0.02, fill=ds.C["amber"])
        y += h + 0.4
    cards = s.get("cards") or []
    if cards:
        cw = ds.col_w(len(cards)); ch = ds.BODY_B - y
        for i, c in enumerate(cards):
            x = ds.MX + i * (cw + ds.GAP); accent_card = (i == len(cards) - 1)
            cv.card(x, y, cw, ch, style="accent" if accent_card else "plain")
            ink = ds.C["white"] if accent_card else cv.ink; sub = ds.C["white"] if accent_card else cv.sub; mut = ds.C["white"] if accent_card else cv.muted
            cv.text(x + 0.45, y + 0.35, cw - 0.9, 0.7, c.get("num", f"0{i+1}"), 40, ds.C["white"] if accent_card else ds.C["amber"], bold=True, max_lines=1, slot="cards.num")
            cv.text(x + 0.45, y + 1.2, cw - 0.9, 1.1, c.get("title", ""), 27, ink, bold=True, line_spacing=1.2, max_lines=2, slot="cards.title")
            cv.text(x + 0.45, y + 2.4, cw - 0.9, ch - 3.0, c.get("desc", ""), ds.SZ["body"], sub, line_spacing=1.45, max_lines=3, slot="cards.desc")
            cv.text(x + 0.45, y + ch - 0.5, cw - 0.9, 0.3, c.get("source", ""), ds.SZ["source"], mut, max_lines=1, slot="cards.source")

@register("product_screens")
def product_screens(cv, s, slide):
    _chrome(cv, s, slide)
    scr = s.get("screens") or []; n = max(1, len(scr)); w = ds.col_w(n); y = ds.BODY_Y; h = ds.BODY_B - y - 0.6
    for i, sc in enumerate(scr):
        x = ds.MX + i * (w + ds.GAP); tone = sc.get("tone"); dark = (i == 0 and not tone); acc = tone == "accent"
        cv.card(x, y, w, h, style="dark" if dark else ("accent" if acc else "plain"))
        ink = ds.C["white"] if (dark or acc) else cv.ink; sub = ds.C["sub_dark"] if dark else (ds.C["white"] if acc else cv.sub)
        if sc.get("image"):
            cv.picture(sc["image"], x + 0.2, y + 0.2, w - 0.4, h * 0.5, cover=True, radius=16)
        else:
            lines = sc.get("mock_lines") or []
            for k, ln in enumerate(lines[:4]):
                cv.rect(x + 0.4, y + 0.5 + k * 0.7, w - 0.8, 0.55, fill=("FFFFFF" if not (dark or acc) else "FFFFFF"), alpha=(None if not (dark or acc) else 12), line=ds.C["card_border"] if not (dark or acc) else None, radius=True)
                cv.text(x + 0.6, y + 0.5 + k * 0.7, w - 1.2, 0.55, ln, ds.SZ["body_sm"], ink, bold=True, anchor="middle", max_lines=1, slot="screens.mock_lines")
        by = y + h * 0.5 + 0.45
        cv.label(x + 0.4, by, w - 0.8, sc.get("label", ""), color=ds.C["amber"] if dark else (ds.C["white"] if acc else cv.accent))
        cv.text(x + 0.4, by + 0.4, w - 0.8, 0.5, sc.get("title", ""), ds.SZ["card_title"], ink, bold=True, max_lines=1, slot="screens.title")
        cv.text(x + 0.4, by + 0.95, w - 0.8, h - (by - y) - 1.1, sc.get("desc", ""), ds.SZ["body"], sub, line_spacing=1.4, max_lines=3, slot="screens.desc")
    if s.get("footnote"): cv.text(ds.MX, ds.BODY_B - 0.4, ds.CW, 0.35, s["footnote"], ds.SZ["small"], cv.muted, max_lines=1, slot="footnote")

@register("tech_moat")
def tech_moat(cv, s, slide):
    _chrome(cv, s, slide)
    lw = 9.2; rx = ds.MX + lw + 0.5; rw = ds.CW - lw - 0.5
    cards = s.get("data_cards") or []; y = ds.BODY_Y
    cv.label(ds.MX, y, lw, "확보 가능한 학습 데이터", color=ds.C["amber"])
    ch = (ds.BODY_B - y - 0.5 - 0.2 * 2) / 3
    for i, c in enumerate(cards[:3]):
        cy = y + 0.45 + i * (ch + 0.2); cv.card(ds.MX, cy, lw, ch)
        cv.stat(ds.MX + 0.4, cy + 0.3, 3.4, c.get("big", ""), big_size=ds.SZ["big_sm"], color=cv.accent if i == 0 else cv.ink)
        cv.text(ds.MX + 4.0, cy + 0.3, lw - 4.4, 0.45, c.get("label", ""), ds.SZ["body"], cv.ink, bold=True, max_lines=1, slot="data_cards.label")
        cv.text(ds.MX + 4.0, cy + 0.8, lw - 4.4, ch - 1.0, c.get("desc", ""), ds.SZ["body_sm"], cv.sub, line_spacing=1.4, max_lines=2, slot="data_cards.desc")
    pipe = s.get("pipeline") or []
    cv.label(rx, y, rw, "파이프라인", color=ds.C["amber"])
    ph = 0.82
    for i, p in enumerate(pipe[:3]):
        py = y + 0.45 + i * (ph + 0.10); cv.rect(rx, py, 0.05, ph, fill=list(_TONE.values())[i % 3])
        cv.text(rx + 0.3, py, rw - 0.3, 0.4, p.get("title", ""), ds.SZ["body"], cv.ink, bold=True, max_lines=1, slot="pipeline.title")
        cv.text(rx + 0.3, py + 0.4, rw - 0.3, ph - 0.4, p.get("desc", ""), ds.SZ["body_sm"], cv.sub, line_spacing=1.35, max_lines=2, slot="pipeline.desc")
    moat = s.get("moat") or {}; my = y + 0.45 + 3 * (ph + 0.10) + 0.15; mh = ds.BODY_B - my - 0.95
    cv.card(rx, my, rw, mh, style="accent"); cv.label(rx + 0.4, my + 0.28, rw - 0.8, "DATA MOAT", color="FFFFFF")
    cv.text(rx + 0.4, my + 0.58, rw - 0.8, 1.05, moat.get("title", ""), ds.SZ["card_title"], ds.C["white"], bold=True, line_spacing=1.15, max_lines=2, slot="moat.title")
    cv.text(rx + 0.4, my + mh - 0.40, rw - 0.8, 0.35, moat.get("desc", ""), ds.SZ["body_sm"], ds.C["white"], max_lines=1, slot="moat.desc")
    if s.get("safety"):
        sy = ds.BODY_B - 0.85; cv.card(rx, sy, rw, 0.75); cv.text(rx + 0.35, sy + 0.08, rw - 0.7, 0.6, "SAFETY · " + s["safety"], ds.SZ["small"], cv.sub, anchor="middle", line_spacing=1.25, max_lines=3, slot="safety")

@register("mvp_scope")
def mvp_scope(cv, s, slide):
    _chrome(cv, s, slide)
    lw = 8.4; rx = ds.MX + lw + 0.4; rw = ds.CW - lw - 0.4; y = ds.BODY_Y
    cv.card(ds.MX, y, lw, 3.9, style="dark"); cv.label(ds.MX + 0.4, y + 0.3, lw - 0.8, "MVP · 0~6개월 · 지금 만드는 것", color=ds.C["teal"])
    now = s.get("now") or []
    for i, it in enumerate(now[:4]):
        col, row = i % 2, i // 2; ix = ds.MX + 0.4 + col * (lw / 2 - 0.3); iy = y + 0.8 + row * 1.15
        cv.text(ix, iy, lw / 2 - 0.6, 0.4, it.get("title", ""), ds.SZ["body"], ds.C["white"], bold=True, max_lines=1, slot="now.title")
        cv.text(ix, iy + 0.4, lw / 2 - 0.6, 0.6, it.get("desc", ""), ds.SZ["body_sm"], ds.C["sub_dark"], max_lines=2, slot="now.desc")
    if s.get("target_line"):
        cv.rect(ds.MX + 0.4, y + 3.25, lw - 0.8, 0.02, fill="FFFFFF", alpha=15)
        cv.text(ds.MX + 0.4, y + 3.35, lw - 0.8, 0.45, s["target_line"], ds.SZ["body_sm"], ds.C["amber"], bold=True, max_lines=1, slot="target_line")
    nn = s.get("not_now") or []; ny = y + 4.2
    cv.label(ds.MX, ny, lw, "NOT NOW · 의도적으로 미루는 것", color=cv.accent)
    cv.body_bullets(ds.MX, ny + 0.4, lw, ds.BODY_B - ny - 0.5, nn, size=ds.SZ["body_sm"], bullet="")
    rm = s.get("roadmap") or []
    cv.label(rx, y, rw, "이후 로드맵", color=ds.C["amber"])
    rh = (ds.BODY_B - y - 0.45 - 0.2 * 2) / 3
    for i, r in enumerate(rm[:3]):
        ry = y + 0.45 + i * (rh + 0.2); cv.card(rx, ry, rw, rh); cv.rect(rx, ry, 0.05, rh, fill=list(_TONE.values())[i % 3])
        cv.label(rx + 0.35, ry + 0.25, rw - 0.6, r.get("label", ""), color=cv.muted)
        cv.text(rx + 0.35, ry + 0.6, rw - 0.6, 0.45, r.get("title", ""), ds.SZ["card_title"], cv.ink, bold=True, max_lines=1, slot="roadmap.title")
        cv.text(rx + 0.35, ry + 1.1, rw - 0.6, rh - 1.2, r.get("desc", ""), ds.SZ["body_sm"], cv.sub, line_spacing=1.35, max_lines=2, slot="roadmap.desc")
