# -*- coding: utf-8 -*-
import os, struct
from pathlib import Path
import pytest
from extractors import hwp

def _u16(s: str) -> bytes:
    return s.encode("utf-16-le")

def test_decode_para_text_skips_extended_control():
    # "안녕" + 확장 컨트롤(0x0B, 16바이트) + "세상" + 줄바꿈(13)
    payload = _u16("안녕") + struct.pack("<H", 11) + b"\x00" * 14 + _u16("세상") + struct.pack("<H", 13)
    assert hwp.decode_para_text(payload) == "안녕 세상\n"

def test_iter_records_parses_header_and_long_size():
    # tag=67, level=0, size=4 → header = 67 | (4<<20)
    hdr = struct.pack("<I", 67 | (4 << 20)) + _u16("ab")
    # long size: size field 0xFFF then explicit uint32
    hdr2 = struct.pack("<I", 67 | (0xFFF << 20)) + struct.pack("<I", 4) + _u16("cd")
    recs = list(hwp.iter_records(hdr + hdr2))
    assert [t for t, _ in recs] == [67, 67]
    assert hwp.decode_para_text(recs[1][1]) == "cd"

def test_sniff_image_ext():
    assert hwp.sniff_ext(b"\xff\xd8\xff\xe0" + b"0" * 10) == "jpg"
    assert hwp.sniff_ext(b"\x89PNG\r\n\x1a\n") == "png"
    assert hwp.sniff_ext(b"BM" + b"0" * 10) == "bmp"
    assert hwp.sniff_ext(b"\x00\x01\x02") is None

@pytest.mark.skipif(not os.environ.get("SEED_IR_TEST_HWP"), reason="실파일 경로 env 없음")
def test_real_hwp_extract(out_dir):
    res = hwp.extract(os.environ["SEED_IR_TEST_HWP"], out_dir)
    assert len(res["text"]) > 1000
    assert "사업계획서" in res["text"]
    assert len(res["images"]) >= 1
    assert all(Path(i["file"]).exists() for i in res["images"])
