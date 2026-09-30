"""Behavioral tests for the portable document ingestion CLI."""
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile
import zlib

SCRIPT = Path(__file__).resolve().parents[1] / "plugins/seed-ir/skills/seed-ir/scripts/ingest.py"
PNG = bytes.fromhex("89504e470d0a1a0a") + b"fixture-image"


class IngestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.inputs = self.base / "inputs"
        self.inputs.mkdir()
        self.out = self.base / "out"

    def archive(self, name, members):
        target = self.inputs / name
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
            for path, data in members.items():
                archive.writestr(path, data)
        return target

    def run_ingest(self, target=None, output=None, success=True):
        result = subprocess.run([sys.executable, str(SCRIPT), "--input", str(target or self.inputs),
                                 "--output", str(output or self.out)], capture_output=True, text=True)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def read(self, name):
        return json.loads((self.out / (name + ".json")).read_text(encoding="utf-8"))

    def test_duplicate_identity_and_private_stdout(self):
        for name in ["a.txt", "b.txt"]:
            (self.inputs / name).write_text("PRIVATE_REVENUE_123", encoding="utf-8")
        result = self.run_ingest()
        files = self.read("inventory")["files"]
        self.assertEqual(len(files), 2)
        self.assertEqual(files[0]["source_id"], files[1]["source_id"])
        self.assertEqual(files[1]["status"], "duplicate")
        self.assertEqual(files[1]["duplicate_of"], "a.txt")
        self.assertEqual(len(self.read("documents")["segments"]), 1)
        self.assertNotIn("PRIVATE_REVENUE_123", result.stdout + result.stderr)

    def test_pptx_text_and_slide_image_relation(self):
        self.archive("deck.pptx", {
            "ppt/slides/slide2.xml": '<p:sld xmlns:p="urn:p" xmlns:a="urn:a" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><a:p><a:r><a:t>고객 검증</a:t></a:r></a:p><a:blip r:embed="rId1"/></p:sld>',
            "ppt/slides/_rels/slide2.xml.rels": '<Relationships><Relationship Id="rId1" Target="../media/image1.png" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"/></Relationships>',
            "ppt/media/image1.png": PNG})
        self.run_ingest()
        segment = self.read("documents")["segments"][0]
        self.assertEqual(segment["text"], "고객 검증")
        self.assertIn("slide2", segment["locator"])
        asset = self.read("assets")["assets"][0]
        self.assertIn("slide2", asset["locator"])
        self.assertEqual((self.out / asset["path"]).read_bytes(), PNG)
        self.assertEqual(asset["source_id"], segment["source_id"])

    def test_docx_and_xlsx_preserve_locations_and_formula_cache(self):
        self.archive("document.docx", {"word/document.xml": '<w:document xmlns:w="urn:w"><w:p><w:r><w:t>팀 역량</w:t></w:r></w:p></w:document>'})
        self.archive("metrics.xlsx", {
            "xl/sharedStrings.xml": '<sst><si><t>매출</t></si></sst>',
            "xl/worksheets/sheet1.xml": '<worksheet><sheetData><row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1"><f>10*2</f><v>20</v></c></row></sheetData></worksheet>'})
        self.run_ingest()
        segments = self.read("documents")["segments"]
        self.assertTrue(any(s["text"] == "팀 역량" and "paragraph" in s["locator"] for s in segments))
        self.assertTrue(any("매출" in s["text"] and "A1" in s["locator"] for s in segments))
        self.assertTrue(any("20" in s["text"] and "10*2" in s["text"] for s in segments))

    def test_hwpx_manifest_maps_image_to_section(self):
        self.archive("document.hwpx", {
            "Contents/content.hpf": '<opf:package xmlns:opf="urn:opf"><opf:manifest><opf:item id="image1" href="BinData/image1.png" media-type="image/png"/></opf:manifest></opf:package>',
            "Contents/section0.xml": '<hs:sec xmlns:hs="urn:hs" xmlns:hp="urn:hp" xmlns:hc="urn:hc"><hp:p><hp:run><hp:t>시제품</hp:t></hp:run></hp:p><hc:img binaryItemIDRef="image1"/></hs:sec>',
            "BinData/image1.png": PNG})
        self.run_ingest()
        self.assertEqual(self.read("documents")["segments"][0]["text"], "시제품")
        self.assertIn("section0", self.read("assets")["assets"][0]["locator"])

    def test_failure_isolation_and_unsupported_listing(self):
        (self.inputs / "good.txt").write_text("valid", encoding="utf-8")
        (self.inputs / "broken.pptx").write_bytes(b"not-a-zip")
        (self.inputs / "unknown.xyz").write_bytes(b"unknown")
        self.run_ingest()
        states = {f["source_file"]: f["status"] for f in self.read("inventory")["files"]}
        self.assertEqual(states, {"broken.pptx": "error", "good.txt": "ok", "unknown.xyz": "unsupported"})

    def test_zip_traversal_and_xml_entities_rejected(self):
        self.archive("unsafe.pptx", {"../escaped.png": PNG, "ppt/slides/slide1.xml": "<sld/>"})
        self.archive("entity.docx", {"word/document.xml": '<!DOCTYPE x [<!ENTITY a "secret">]><document>&a;</document>'})
        self.run_ingest()
        self.assertTrue(all(f["status"] == "error" for f in self.read("inventory")["files"]))
        self.assertFalse((self.base / "escaped.png").exists())

    def test_output_nested_under_input_is_rejected(self):
        result = self.run_ingest(output=self.inputs / "output", success=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("outside the input", result.stderr)
        self.assertFalse((self.inputs / "output").exists())

    def test_zip_bomb_and_utf16_entities_are_rejected(self):
        self.archive("bomb.pptx", {"ppt/slides/slide1.xml": b"x" * 2000000})
        self.archive("entity.docx", {"word/document.xml": '<!DOCTYPE x [<!ENTITY a "secret">]><document>&a;</document>'.encode("utf-16")})
        self.run_ingest()
        self.assertTrue(all(f["status"] == "error" for f in self.read("inventory")["files"]))

    @unittest.skipUnless(importlib.util.find_spec("fitz"), "optional pymupdf not installed")
    def test_pdf_page_text_and_blank_page_ocr_queue(self):
        import fitz
        with fitz.open() as document:
            document.new_page().insert_text((30, 30), "Validation evidence")
            document.new_page()
            document.save(self.inputs / "evidence.pdf")
        self.run_ingest()
        data = self.read("documents")
        self.assertEqual(data["segments"][0]["locator"], "page=1")
        self.assertIn("Validation evidence", data["segments"][0]["text"])
        self.assertEqual(data["ocr_queue"][0]["locator"], "page=2#ocr-raster")

    def test_image_is_queued_for_visual_review(self):
        (self.inputs / "photo.png").write_bytes(PNG)
        self.run_ingest()
        self.assertEqual(self.read("assets")["assets"][0]["status"], "visual_review_pending")
        self.assertEqual(self.read("documents")["segments"], [])
        self.assertEqual(len(self.read("documents")["ocr_queue"]), 1)

    def test_hwp_records_control_codes_and_decompression_bound(self):
        self.assertTrue(SCRIPT.is_file(), "ingestion runtime is not implemented")
        spec = importlib.util.spec_from_file_location("ingest", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        payload = "앞".encode("utf-16le") + struct.pack("<8H", 2, 0x4141, 0, 0, 0, 0, 0, 2) + "뒤".encode("utf-16le")
        record = struct.pack("<I", 67 | (len(payload) << 20)) + payload
        self.assertEqual(list(module.hwp_paragraphs(record)), [(1, "앞뒤")])
        compressed = zlib.compressobj(wbits=-15)
        blob = compressed.compress(b"A" * 1000) + compressed.flush()
        with self.assertRaises(ValueError):
            module.inflate_bounded(blob, limit=100)
        # HWP BinData may be uncompressed PNG even when document compression is on.
        with self.assertRaises(ValueError):
            module.inflate_bounded(PNG)


if __name__ == "__main__":
    unittest.main()
