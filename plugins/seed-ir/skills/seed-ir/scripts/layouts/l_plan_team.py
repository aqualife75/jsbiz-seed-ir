# -*- coding: utf-8 -*-
from . import register
from .l_problem import _chrome, _TONE
import design_system as ds

@register("milestone_gates")
def milestone_gates(cv, s, slide):
    _chrome(cv, s, slide)
    gates = s.get("gates") or []; y = ds.BODY_Y
    if gates:
        n = len(gates); w = ds.col_w(n)
        cv.rect(ds.MX, y + 0.1, ds.CW, 0.03, fill=ds.C["amber"])
        for i in range(n):
            cx = ds.MX + i * (w + ds.GAP) + 0.2
            cv.rect(cx, y + 0.02, 0.2, 0.2, fill=list(_TONE.values())[i % 4] if gates[i].get("tone") != "teal" else ds.C["teal"], radius=0.5)
        gy = y + 0.55; gh = ds.BODY_B - gy - 1.65
        for i, g in enumerate(gates):
            x = ds.MX + i * (w + ds.GAP); teal = g.get("tone") == "teal"; tone = ds.C["teal"] if teal else list(_TONE.values())[i % 3]
            cv.card(x, gy, w, gh)
            if teal: cv.rect(x, gy, w, gh, fill=None, line=ds.C["teal"], line_alpha=70, radius=True)
            cv.label(x + 0.35, gy + 0.3, w - 0.7, g.get("label", ""), color=tone)
            cv.text(x + 0.35, gy + 0.65, w - 0.7, 0.5, g.get("title", ""), ds.SZ["card_title"], cv.ink, bold=True, max_lines=1, slot="gates.title")
            cv.body_bullets(x + 0.35, gy + 1.2, w - 0.7, gh - 2.35, g.get("bullets") or [], size=ds.SZ["body_sm"])
            by = gy + gh - 1.05; cv.rect(x + 0.35, by, w - 0.7, 0.85, fill=tone, alpha=18, radius=True); cv.rect(x + 0.35, by, 0.05, 0.85, fill=tone)
            cv.label(x + 0.55, by + 0.1, w - 1.0, "GATE", color=cv.muted)
            cv.text(x + 0.55, by + 0.38, w - 1.0, 0.45, g.get("gate", ""), ds.SZ["body_sm"], cv.ink, bold=True, max_lines=1, slot="gates.gate")
    ask = s.get("ask_band") or {}
    if ask:
        ay = ds.BODY_B - 1.35; cv.card(ds.MX, ay, ds.CW, 1.25, style="accent")
        cv.label(ds.MX + 0.4, ay + 0.25, 5, f"SEED ASK · {ask.get('runway','')}", color="FFFFFF")
        cv.text(ds.MX + 0.4, ay + 0.55, 5, 0.65, ask.get("amount", ""), 34, ds.C["white"], bold=True, max_lines=1, slot="ask_band.amount")
        cv.label(ds.MX + 5.6, ay + 0.25, 10, "자금 사용 계획", color="FFFFFF")
        cv.text(ds.MX + 5.6, ay + 0.6, ds.CW - 6.0, 0.6, ask.get("use_of_funds", ""), ds.SZ["body"], ds.C["white"], bold=True, line_spacing=1.3, max_lines=2, slot="ask_band.use_of_funds")

@register("team_cards")
def team_cards(cv, s, slide):
    _chrome(cv, s, slide)
    mem = s.get("members") or []; y = ds.BODY_Y; lw = 12.9; h = 3.4
    if mem:
        w = ds.col_w(len(mem), lw)
        for i, m in enumerate(mem):
            x = ds.MX + i * (w + ds.GAP); dark = m.get("tone") == "dark"
            cv.card(x, y, w, h, style="dark" if dark else "plain", top_bar=None if dark else list(_TONE.values())[i % 3])
            ink, sub = (ds.C["white"], ds.C["sub_dark"]) if dark else (cv.ink, cv.sub)
            cv.label(x + 0.35, y + 0.35, w - 0.7, m.get("role", ""), color=ds.C["amber"] if dark else list(_TONE.values())[i % 3])
            cv.text(x + 0.35, y + 0.75, w - 0.7, 0.5, m.get("title", ""), ds.SZ["card_title"], ink, bold=True, max_lines=1, slot="members.title")
            cv.text(x + 0.35, y + 1.3, w - 0.7, 1.15, m.get("desc", ""), ds.SZ["body_sm"], sub, line_spacing=1.4, max_lines=3, slot="members.desc")
            cv.text(x + 0.35, y + 2.5, w - 0.7, 0.3, "담당 지표", ds.SZ["small"], ds.C["teal"], bold=True, max_lines=1)
            cv.text(x + 0.35, y + 2.8, w - 0.7, 0.45, m.get("kpi", ""), ds.SZ["body_sm"], sub, max_lines=1, slot="members.kpi")
        y += h + 0.4
    adv = s.get("advisors") or []
    if adv:
        cv.label(ds.MX, y, lw, "자문단 구성 계획 — 안전성이 곧 신뢰입니다", color=cv.accent)
        aw = ds.col_w(len(adv), lw); ah = ds.BODY_B - y - 0.95
        for i, a in enumerate(adv):
            x = ds.MX + i * (aw + ds.GAP); cv.card(x, y + 0.4, aw, ah)
            cv.text(x + 0.35, y + 0.7, aw - 0.7, 0.45, a.get("title", ""), ds.SZ["body"], cv.ink, bold=True, max_lines=1, slot="advisors.title")
            cv.text(x + 0.35, y + 1.15, aw - 0.7, ah - 0.9, a.get("desc", ""), ds.SZ["body_sm"], cv.sub, line_spacing=1.4, max_lines=3, slot="advisors.desc")
    pr = s.get("principle") or {}; px = ds.MX + lw + 0.35; pw = ds.CW - lw - 0.35
    cv.card(px, ds.BODY_Y, pw, ds.BODY_B - ds.BODY_Y - 0.55, style="accent"); cv.label(px + 0.4, ds.BODY_Y + 0.35, pw - 0.8, "채용 원칙", color="FFFFFF")
    cv.text(px + 0.4, ds.BODY_Y + 0.75, pw - 0.8, 1.9, pr.get("title", ""), 27, ds.C["white"], bold=True, line_spacing=1.2, max_lines=3, slot="principle.title")
    cv.text(px + 0.4, ds.BODY_Y + 2.75, pw - 0.8, 1.3, pr.get("desc", ""), ds.SZ["body_sm"], ds.C["white"], line_spacing=1.4, max_lines=4, slot="principle.desc")
    cv.rect(px + 0.4, ds.BODY_Y + 4.15, pw - 0.8, 0.01, fill="FFFFFF", alpha=35)
    cv.label(px + 0.4, ds.BODY_Y + 4.3, pw - 0.8, "M3 이후 충원 계획", color="FFFFFF")
    cv.body_bullets(px + 0.4, ds.BODY_Y + 4.65, pw - 0.8, 1.2, pr.get("list") or [], size=ds.SZ["body_sm"], color=ds.C["white"])
    if s.get("footnote"): cv.text(ds.MX, ds.BODY_B - 0.4, lw, 0.35, s["footnote"], ds.SZ["small"], cv.muted, max_lines=1, slot="footnote")

@register("vision_close")
def vision_close(cv, s, slide):
    cv.panel_image(s.get("panel_image"), strength=0.6, x=11.6, w=8.4)
    cv.rect(ds.MX, 1.2, 0.05, 3.2, fill=cv.accent)
    cv.text(ds.MX + 0.4, 1.25, 9.5, 0.35, s.get("kicker", ""), ds.SZ["kicker"], ds.C["amber"], bold=True, spacing=0.25, max_lines=1, slot="kicker")
    cv.text(ds.MX + 0.4, 1.7, 9.5, 3.0, s.get("headline", ""), 54, ds.C["white"], bold=True, line_spacing=1.12, max_lines=3, slot="headline")
    cv.text(ds.MX + 0.4, 4.9, 9.6, 1.6, s.get("body", ""), ds.SZ["lead"], ds.C["sub_dark"], line_spacing=1.45, max_lines=3, slot="body")
    cv.rect(ds.MX + 0.4, 6.75, 9.6, 0.01, fill="FFFFFF", alpha=20)
    cv.label(ds.MX + 0.4, 6.95, 6, "THE ONE-LINER", color=ds.C["amber"])
    cv.text(ds.MX + 0.4, 7.35, 9.6, 1.4, s.get("one_liner", ""), 27, ds.C["white"], bold=True, line_spacing=1.25, max_lines=2, slot="one_liner")
    cards = s.get("cards") or []; cx = 12.6; cw = 6.4; ch = 1.95
    for i, c in enumerate(cards[:3]):
        cy = 2.0 + i * (ch + 0.25); acc = c.get("tone") == "accent"
        cv.rect(cx, cy, cw, ch, fill=ds.C["accent"] if acc else ds.BG["dark"], alpha=None if acc else 65, line=None if acc else "FFFFFF", line_alpha=None if acc else 12, radius=True)
        cv.label(cx + 0.4, cy + 0.25, cw - 0.8, c.get("label", ""), color="FFFFFF" if acc else ds.C["muted_dark"])
        cv.text(cx + 0.4, cy + 0.6, cw - 0.8, 0.85, c.get("big", ""), 26, ds.C["teal"] if c.get("tone") == "teal" else ds.C["white"], bold=True, line_spacing=1.15, max_lines=2, slot="cards.big")
        cv.text(cx + 0.4, cy + ch - 0.55, cw - 0.8, 0.45, c.get("sub", ""), ds.SZ["small"], ds.C["white"] if acc else ds.C["sub_dark"], max_lines=1, slot="cards.sub")
    if s.get("brand"):
        cv.rect(ds.MX + 0.4, 9.7, 3.0, 0.7, fill="FFFFFF", radius=True); cv.text(ds.MX + 0.6, 9.7, 2.6, 0.7, s["brand"], 20, ds.C["ink"], bold=True, anchor="middle", max_lines=1, slot="brand")
    cv.text(ds.MX + 3.8, 9.7, 6.5, 0.7, s.get("tagline", ""), ds.SZ["body"], ds.C["sub_dark"], bold=True, anchor="middle", max_lines=1, slot="tagline")
    cv.text(12.6, 9.7, 6.4, 0.7, s.get("ask_line", ""), ds.SZ["body"], ds.C["amber"], bold=True, align="right", anchor="middle", max_lines=1, slot="ask_line")
    cv.notes(slide.get("notes"))

@register("appendix_qa")
def appendix_qa(cv, s, slide):
    cv.kicker(s.get("kicker", "APPENDIX · Q&A")); cv.title(s.get("title", "예상 질문과 답"), size=ds.SZ["title_sm"], max_lines=1)
    qa = s.get("qa") or []; y = 2.6; h = (ds.BODY_B - y - 0.2 * (len(qa) - 1)) / max(1, len(qa))
    for i, item in enumerate(qa[:4]):
        iy = y + i * (h + 0.2); cv.card(ds.MX, iy, ds.CW, h); cv.rect(ds.MX, iy, 0.05, h, fill=cv.accent)
        cv.text(ds.MX + 0.4, iy + 0.2, 6.0, h - 0.4, f"Q{i+1}. {item.get('q','')}", ds.SZ["body"], cv.ink, bold=True, line_spacing=1.35, anchor="middle", max_lines=3, slot="qa.q")
        cv.text(ds.MX + 6.7, iy + 0.2, ds.CW - 7.1, h - 0.4, item.get("a", ""), ds.SZ["body_sm"], cv.sub, line_spacing=1.4, anchor="middle", max_lines=4, slot="qa.a")
    cv.page_no(slide["no"], cv.ctx.total); cv.notes(slide.get("notes"))

@register("evidence_capture")
def evidence_capture(cv, s, slide):
    cv.kicker(s.get("kicker", "APPENDIX · EVIDENCE")); cv.title(s.get("title", ""), size=ds.SZ["title_sm"], max_lines=2)
    y = 3.0; h = ds.BODY_B - y - 0.9
    cv.card(ds.MX, y, ds.CW, h)
    cv.picture(s.get("image"), ds.MX + 0.3, y + 0.3, ds.CW - 0.6, h - 0.6, cover=False, radius=12)
    cv.text(ds.MX, ds.BODY_B - 0.8, ds.CW, 0.35, s.get("caption", ""), ds.SZ["body_sm"], cv.ink, bold=True, max_lines=1, slot="caption")
    cv.text(ds.MX, ds.BODY_B - 0.45, ds.CW, 0.35, s.get("source", ""), ds.SZ["source"], cv.muted, max_lines=1, slot="source")
    cv.page_no(slide["no"], cv.ctx.total); cv.notes(slide.get("notes"))
