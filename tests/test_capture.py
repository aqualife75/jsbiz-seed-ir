# -*- coding: utf-8 -*-
import pytest
from PIL import Image
import capture_evidence as ce

def test_find_chrome_returns_path_or_none():
    p = ce.find_chrome()
    assert p is None or p.lower().endswith((".exe", "chrome", "chromium", "msedge", "google chrome"))

@pytest.mark.skipif(ce.find_chrome() is None, reason="Chrome/Edge 없음")
def test_capture_local_html(out_dir):
    html = out_dir / "a.html"; html.write_text("<html><body style='font-size:40px'>당뇨 조절률 32.4% (대한당뇨병학회 2024)</body></html>", encoding="utf-8")
    out = out_dir / "cap.png"
    ce.capture(html.resolve().as_uri(), out, width=1000, height=600, wait_ms=1500)
    im = Image.open(out); assert im.size[0] == 1000 and im.size[1] >= 500
    crop = out_dir / "crop.png"; ce.main([html.resolve().as_uri(), str(crop), "--size", "1000x600", "--crop", "0,0,500,200"])
    assert Image.open(crop).size == (500, 200)
