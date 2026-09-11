# -*- coding: utf-8 -*-
from PIL import Image
import design_system as ds
import prep_image as pi

def test_tokens_match_spec():
    assert (ds.CANVAS_W, ds.CANVAS_H) == (20.0, 11.25) and ds.FONT == "Pretendard"
    assert ds.BG == {"dark": "10141B", "cream": "F5F2EB"}
    assert ds.accent("cream") == "E0492E" and ds.accent("dark") == "FF6A4D"
    assert ds.ink("dark") == "FFFFFF" and ds.ink("cream") == "10141B"
    assert abs(ds.col_w(3) - 5.75) < 1e-6 and abs(ds.col_w(4) - 4.25) < 1e-6

def test_fit_cover_and_darken(out_dir):
    src = out_dir / "s.jpg"; Image.new("RGB", (800, 300), (200, 200, 200)).save(src)
    dst = out_dir / "d.png"; pi.fit_cover(src, dst, 400, 400)
    im = Image.open(dst); assert im.size == (400, 400)
    dk = out_dir / "k.png"; pi.darken(dst, dk, 0.6)
    px = Image.open(dk).convert("RGB").getpixel((10, 10))
    assert px[0] < 120  # 어두워짐

def test_round_and_crop_and_bmp(out_dir):
    src = out_dir / "b.bmp"; Image.new("RGB", (100, 60), (1, 2, 3)).save(src)
    png = out_dir / "b.png"; pi.to_png(src, png); assert Image.open(png).format == "PNG"
    rc = out_dir / "r.png"; pi.round_corners(png, rc, 20); assert Image.open(rc).mode == "RGBA"
    cr = out_dir / "c.png"; pi.crop(png, cr, (10, 10, 50, 40)); assert Image.open(cr).size == (40, 30)
