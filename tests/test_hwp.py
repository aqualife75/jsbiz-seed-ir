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

def test_decode_para_text_surrogate_pairs():
    # "가" + U+1F600(😀)의 서로게이트 쌍 + 짝없는 상위 서로게이트(0xD83D) + "나"
    payload = (
        _u16("가")
        + struct.pack("<H", 0xD83D) + struct.pack("<H", 0xDE00)
        + struct.pack("<H", 0xD83D)
        + _u16("나")
    )
    assert hwp.decode_para_text(payload) == "가\U0001F600나"

def test_hwp_text_prvtext_fallback(monkeypatch):
    class _FakeStream:
        def __init__(self, data: bytes):
            self._data = data
        def read(self):
            return self._data

    class _FakeOleFileIO:
        def __init__(self, path):
            pass
        def openstream(self, name):
            if name == "FileHeader":
                data = bytearray(40)
                data[36] = 0  # 압축 플래그 off
                return _FakeStream(bytes(data))
            if name == "PrvText":
                return _FakeStream("미리보기 텍스트".encode("utf-16-le"))
            raise FileNotFoundError(name)
        def listdir(self):
            return []
        def exists(self, name):
            return name == "PrvText"
        def close(self):
            pass

    monkeypatch.setattr(hwp.olefile, "OleFileIO", _FakeOleFileIO)
    assert hwp.hwp_text("dummy.hwp") == "미리보기 텍스트"

@pytest.mark.skipif(not os.environ.get("SEED_IR_TEST_HWP"), reason="실파일 경로 env 없음")
def test_real_hwp_extract(out_dir):
    res = hwp.extract(os.environ["SEED_IR_TEST_HWP"], out_dir)
    assert len(res["text"]) > 1000
    assert "사업계획서" in res["text"]
    assert len(res["images"]) >= 1
    assert all(Path(i["file"]).exists() for i in res["images"])
