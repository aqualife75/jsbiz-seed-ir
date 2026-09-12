# -*- coding: utf-8 -*-
from . import register
import design_system as ds

@register("cover")
def cover(cv, s, slide):
    # 쓸 만한 팀 이미지가 없는 팀이 많다. 그럴 땐 우측 패널을 비워 두지 말고
    # 본문이 전폭을 쓰게 한다(빈 패널은 "준비가 덜 된 덱"으로 읽힌다).
    has_panel = cv._resolve(s.get("panel_image")) is not None
    if has_panel:
        cv.panel_image(s.get("panel_image"), strength=0.55)
    left_w = (ds.PANEL_X - ds.MX - 0.6) if has_panel else (ds.CW - 0.4)
    cv.rect(ds.MX, 0.95, 0.04, 4.6, fill=cv.accent)
    cv.text(ds.MX + 0.4, 0.95, left_w, 0.35, s.get("kicker", ""), ds.SZ["kicker"], ds.C["amber"], bold=True, spacing=0.25, max_lines=1, slot="kicker")
    if s.get("brand"):
        cv.rect(ds.MX + 0.4, 1.55, 4.2, 1.0, fill="FFFFFF", radius=True)
        cv.text(ds.MX + 0.7, 1.55, 3.7, 1.0, s["brand"], 30, ds.C["ink"], bold=True, anchor="middle", max_lines=1, slot="brand")
    cv.text(ds.MX + 0.4, 3.1, left_w, 2.6, s.get("headline", ""), 66, ds.C["white"], bold=True, line_spacing=1.08, max_lines=2, slot="headline")
    cv.text(ds.MX + 0.4, 5.85, left_w, 1.1, s.get("subtitle", ""), 24, ds.C["sub_dark"], line_spacing=1.35, max_lines=2, slot="subtitle")
    tags = s.get("tags") or []
    if tags:
        cv.text(ds.MX + 0.4, 7.3, left_w, 0.4, "   ·   ".join(tags), ds.SZ["body"], ds.C["amber"], bold=True, max_lines=1, slot="tags")
    stats = s.get("footer_stats") or []
    if stats:
        cv.rect(ds.MX + 0.4, 9.35, left_w, 0.01, fill="FFFFFF", alpha=15)
        w = left_w / 4
        for i, st in enumerate(stats[:4]):
            x = ds.MX + 0.4 + i * w
            cv.text(x, 9.65, w - 0.2, 0.3, st.get("label", ""), ds.SZ["label"], ds.C["muted_dark"], bold=True, spacing=0.2, max_lines=1, slot="footer_stats.label")
            cv.text(x, 9.98, w - 0.2, 0.45, st.get("value", ""), 20, ds.C["amber"] if i == 3 else ds.C["white"], bold=True, max_lines=1, slot="footer_stats.value")
    cv.notes(slide.get("notes"))

@register("statement")
def statement(cv, s, slide):
    cv.rect(ds.MX, 3.3, 0.06, 3.2, fill=cv.accent)
    cv.text(ds.MX + 0.5, 3.2, 16.5, 3.4, s.get("statement", ""), ds.SZ["statement"], cv.ink, bold=True, line_spacing=1.12, anchor="middle", max_lines=2, slot="statement")
    if s.get("sub"):
        cv.text(ds.MX + 0.5, 6.9, 16.5, 0.6, s["sub"], ds.SZ["lead"], cv.sub, max_lines=1, slot="sub")
    cv.page_no(slide["no"], cv.ctx.total); cv.notes(slide.get("notes"))

_TONE = {"accent": ds.C["accent"], "amber": ds.C["amber"], "teal": ds.C["teal"], "dark": ds.C["teal"]}

@register("trend_cards")
def trend_cards(cv, s, slide):
    cv.kicker(s.get("kicker", "")); cv.title(s.get("title", "")); cv.lead(s.get("lead", ""))
    if s.get("key_gap"):
        cv.card(16.1, 0.75, 2.75, 2.8); cv.label(16.4, 1.0, 2.2, "KEY GAP")
        cv.text(16.4, 1.4, 2.2, 2.0, s["key_gap"], ds.SZ["card_title"], cv.ink, bold=True, line_spacing=1.25, max_lines=4, slot="key_gap")
    cards = s.get("cards") or []
    n = max(1, len(cards)); w = ds.col_w(n); y, h = ds.BODY_Y, 3.45
    for i, c in enumerate(cards):
        x = ds.MX + i * (w + ds.GAP); tone = c.get("tone", ["accent", "amber", "teal"][i % 3])
        dark = tone == "dark"
        cv.card(x, y, w, h, style="dark" if dark else "plain", top_bar=_TONE[tone])
        ink, sub, mut = (ds.C["white"], ds.C["sub_dark"], ds.C["muted_dark"]) if dark else (cv.ink, cv.sub, cv.muted)
        cv.label(x + 0.4, y + 0.35, w - 0.8, c.get("label", ""), color=_TONE[tone] if not dark else ds.C["teal"])
        cv.text(x + 0.4, y + 0.75, w - 0.8, 0.5, c.get("headline", ""), ds.SZ["card_title"], ink, bold=True, max_lines=1, slot="cards.headline")
        cv.stat(x + 0.4, y + 1.3, w - 0.8, c.get("big", ""), c.get("unit", ""), color=ink)
        cv.text(x + 0.4, y + 2.25, w - 0.8, 0.7, c.get("desc", ""), ds.SZ["body"], sub, line_spacing=1.4, max_lines=2, slot="cards.desc")
        cv.text(x + 0.4, y + 3.0, w - 0.8, 0.3, c.get("source", ""), ds.SZ["source"], mut, max_lines=1, slot="cards.source")
    band = s.get("band")
    if band:
        by = y + h + 0.35; bh = ds.BODY_B - by
        cv.card(ds.MX, by, ds.CW, bh, style="accent")
        cv.label(ds.MX + 0.45, by + 0.4, 6, "SO WHAT", color="FFFFFF")
        cv.text(ds.MX + 0.45, by + 0.85, 8.2, bh - 1.1, band.get("so_what", ""), 27, ds.C["white"], bold=True, line_spacing=1.25, max_lines=2, slot="band.so_what")
        cv.label(ds.MX + 9.4, by + 0.4, 6, "WHY NOW", color="FFFFFF")
        cv.body_bullets(ds.MX + 9.4, by + 0.85, 7.8, bh - 1.0, band.get("why_now", []), size=ds.SZ["body"], color=ds.C["white"])
    cv.source_line(slide.get("source_line", "")); cv.page_no(slide["no"], cv.ctx.total); cv.notes(slide.get("notes"))
