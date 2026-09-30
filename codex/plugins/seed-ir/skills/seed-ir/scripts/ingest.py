#!/usr/bin/env python3
"""Local, provenance-preserving extraction. No OCR, network, or document execution.

Python 3.11+. Optional: pymupdf for PDF; olefile for HWP5 fallback.
Installed @ohah/hwpjs is preferred for HWP; it is never downloaded automatically.
"""
import argparse
from collections import Counter
import hashlib
import json
import mimetypes
from pathlib import Path, PurePosixPath
import posixpath
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
import zlib

MAX_FILE = 256 * 1024 * 1024
MAX_MEMBER = 64 * 1024 * 1024
MAX_ARCHIVE = 512 * 1024 * 1024
IMAGES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff", ".svg", ".emf", ".wmf"}
OFFICE = {".pptx", ".docx", ".xlsx", ".hwpx"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def local(tag):
    return tag.rsplit("}", 1)[-1]


def natural(value):
    return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", value)]


def xml(data):
    # Null removal also recognizes declarations in UTF-16/UTF-32 XML.
    declarations = data.replace(b"\0", b"").upper()
    if b"<!DOCTYPE" in declarations or b"<!ENTITY" in declarations:
        raise ValueError("XML DTD/entity declarations are not supported")
    return ET.fromstring(data)


def inflate_bounded(data, limit=MAX_MEMBER):
    decoder = zlib.decompressobj(-15)
    try:
        result = decoder.decompress(data, limit + 1)
    except zlib.error:
        raise ValueError("Invalid HWP compressed stream (possibly stored uncompressed)") from None
    if len(result) > limit or decoder.unconsumed_tail:
        raise ValueError("HWP decompression exceeds safety limit")
    if not decoder.eof:
        raise ValueError("Truncated HWP compressed stream")
    return result


def hwp_paragraphs(data):
    """HWP5 records; locators identify records, never inferred page numbers."""
    offset, paragraph = 0, 0
    inline_controls = {1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23}
    while offset < len(data):
        if offset + 4 > len(data):
            raise ValueError("Truncated HWP record header")
        header = struct.unpack_from("<I", data, offset)[0]
        offset += 4
        tag, size = header & 1023, header >> 20
        if size == 4095:
            if offset + 4 > len(data):
                raise ValueError("Truncated HWP extended record")
            size = struct.unpack_from("<I", data, offset)[0]
            offset += 4
        if size > MAX_MEMBER or offset + size > len(data):
            raise ValueError("Invalid HWP record length")
        payload = data[offset:offset + size]
        offset += size
        if tag != 67:
            continue
        paragraph += 1
        clean = bytearray()
        cursor = 0
        while cursor + 2 <= len(payload):
            char = struct.unpack_from("<H", payload, cursor)[0]
            if char in inline_controls:
                if char == 9:
                    clean.extend(b"\t\0")
                cursor += 16
            else:
                if char >= 32 or char in (10, 13):
                    clean.extend(payload[cursor:cursor + 2])
                cursor += 2
        text = clean.decode("utf-16le", errors="replace").strip()
        if text:
            yield paragraph, text


def image_extension(data, hint):
    for magic, extension in [(b"\x89PNG\r\n\x1a\n", ".png"), (b"\xff\xd8\xff", ".jpg"),
                             (b"GIF8", ".gif"), (b"BM", ".bmp"), (b"II*\0", ".tif"), (b"MM\0*", ".tif")]:
        if data.startswith(magic):
            return extension
    return hint.lower() if hint.lower() in IMAGES else ".bin"


class Extractor:
    def __init__(self, output, entry):
        self.output, self.entry = output, entry
        self.segments, self.assets, self.queue = [], [], []
        self.asset_bytes = 0

    def warn(self, message):
        if message not in self.entry["warnings"]:
            self.entry["warnings"].append(message)

    def segment(self, locator, text):
        text = text.strip()
        if text:
            self.segments.append({"segment_id": "seg_" + digest((self.entry["source_id"] + locator + text).encode())[:24],
                                  "source_id": self.entry["source_id"], "source_file": self.entry["source_file"],
                                  "locator": locator, "text": text})

    def asset(self, locator, data, hint, review=False):
        self.asset_bytes += len(data)
        if len(data) > MAX_MEMBER or self.asset_bytes > MAX_ARCHIVE:
            raise ValueError("Extracted assets exceed safety limit")
        sha = digest(data)
        extension = image_extension(data, hint)
        relative = "assets/" + sha + extension
        path = self.output / relative
        if not path.exists():
            path.write_bytes(data)
        item = {"asset_id": "ast_" + digest((self.entry["source_id"] + locator + sha).encode())[:24],
                "source_id": self.entry["source_id"], "source_file": self.entry["source_file"], "locator": locator,
                "path": relative, "sha256": sha, "mime": mimetypes.guess_type("image" + extension)[0] or "application/octet-stream",
                "status": "visual_review_pending" if review else "extracted"}
        self.assets.append(item)
        if review:
            self.queue.append({key: item[key] for key in ("asset_id", "source_id", "source_file", "locator")}
                              | {"reason": "Visual inspection/OCR required; no text has been inferred"})
        return item

    def office(self, path):
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            if len(infos) > 10000 or sum(i.file_size for i in infos) > MAX_ARCHIVE:
                raise ValueError("ZIP archive exceeds safety limit")
            for info in infos:
                member = PurePosixPath(info.filename)
                if member.is_absolute() or ".." in member.parts or "\\" in info.filename or ":" in info.filename:
                    raise ValueError("Unsafe ZIP member path")
                if info.file_size > MAX_MEMBER or info.file_size / max(info.compress_size, 1) > 1000:
                    raise ValueError("ZIP member exceeds size/ratio limit")
                if info.flag_bits & 1:
                    raise ValueError("Encrypted ZIP members are unsupported")
            names = set(archive.namelist())
            if len(names) != len(infos):
                raise ValueError("Duplicate ZIP member names are unsupported")

            def read_xml(name):
                return xml(archive.read(name))

            def relationships(part):
                relpath = posixpath.join(posixpath.dirname(part), "_rels", posixpath.basename(part) + ".rels")
                result = {}
                if relpath in names:
                    for relation in read_xml(relpath):
                        if relation.get("TargetMode") == "External":
                            self.warn("External Office relationships were not fetched")
                            continue
                        target = relation.get("Target", "")
                        resolved = posixpath.normpath(posixpath.join(posixpath.dirname(part), target))
                        if resolved.startswith("../") or "\\" in target or ":" in target:
                            self.warn("Unsafe Office relationship was ignored")
                            continue
                        # OOXML targets may be package-root absolute.
                        resolved = resolved.lstrip("/")
                        if resolved in names:
                            result[relation.get("Id")] = resolved
                return result

            media = {n for n in names if ("/media/" in n or n.startswith("BinData/")) and not n.endswith("/")}
            manifest = {}
            if "Contents/content.hpf" in names:
                for item in read_xml("Contents/content.hpf").iter():
                    if local(item.tag) == "item":
                        target = item.get("href", "").lstrip("/")
                        if target not in names:
                            target = posixpath.normpath("Contents/" + target)
                        if target in names:
                            manifest[item.get("id")] = target
            shared = []
            if "xl/sharedStrings.xml" in names:
                shared = ["".join(t.text or "" for t in si.iter() if local(t.tag) == "t") for si in read_xml("xl/sharedStrings.xml")]
            patterns = {".pptx": r"ppt/(slides/slide\d+|notesSlides/notesSlide\d+)\.xml$",
                        ".docx": r"word/(document|header\d+|footer\d+|footnotes|endnotes)\.xml$",
                        ".xlsx": r"xl/worksheets/sheet\d+\.xml$", ".hwpx": r"Contents/section\d+\.xml$"}
            parts = sorted([n for n in names if re.match(patterns[path.suffix.lower()], n)], key=natural)
            if not parts:
                raise ValueError("No supported document content parts found")
            if path.suffix.lower() in {".docx", ".hwpx"}:
                self.warn("Locators identify XML parts/paragraphs; pagination and layout require rendered review")
            used = set()
            for part in parts:
                tree, rels = read_xml(part), relationships(part)
                if path.suffix.lower() == ".xlsx":
                    for cell in (e for e in tree.iter() if local(e.tag) == "c"):
                        value = next((e.text or "" for e in cell if local(e.tag) == "v"), "")
                        formula = next((e.text or "" for e in cell if local(e.tag) == "f"), "")
                        if cell.get("t") == "s":
                            value = shared[int(value)] if value.isdigit() and int(value) < len(shared) else "[unresolved shared string]"
                        elif cell.get("t") == "inlineStr":
                            value = "".join(e.text or "" for e in cell.iter() if local(e.tag) == "t")
                        if formula:
                            value += " [formula=" + formula + "; cached value, not recalculated]"
                            self.warn("Spreadsheet formulas use saved cached values; recalculation/units must be verified")
                        self.segment(part + "#cell=" + cell.get("r", "unknown"), value)
                else:
                    for index, paragraph in enumerate((e for e in tree.iter() if local(e.tag) == "p"), 1):
                        def own_text(element):
                            for child in element:
                                if local(child.tag) == "p":
                                    continue
                                if local(child.tag) == "t":
                                    yield child.text or ""
                                else:
                                    yield from own_text(child)
                        self.segment(part + "#paragraph=" + str(index), "".join(own_text(paragraph)))

                def map_images(root, relations, context, depth=0):
                    for index, node in enumerate(root.iter(), 1):
                        for key, value in node.attrib.items():
                            target = manifest.get(value) if local(key) == "binaryItemIDRef" else relations.get(value) if local(key) in {"embed", "id"} else None
                            if target in media:
                                self.asset(context + "#node=" + str(index) + ":" + target, archive.read(target), Path(target).suffix)
                                used.add(target)
                            elif target and target.startswith("xl/drawings/") and target.endswith(".xml") and depth == 0:
                                map_images(read_xml(target), relationships(target), context + "/" + target, depth + 1)
                map_images(tree, rels, part)
            for target in sorted(media - used):
                self.asset("embedded:" + target + "#location-unmapped", archive.read(target), Path(target).suffix)
                self.warn("Some embedded assets have no mapped paragraph/slide; inspect their source document")

    def pdf(self, path):
        try:
            import fitz
        except ImportError:
            raise ValueError("PDF extraction requires optional dependency: pymupdf") from None
        with fitz.open(path) as document:
            if document.needs_pass:
                raise ValueError("Password-protected PDF is unsupported")
            if len(document) > 2000:
                raise ValueError("PDF exceeds 2000 page safety limit")
            for index, page in enumerate(document, 1):
                locator = "page=" + str(index)
                text = page.get_text("text")
                self.segment(locator, text)
                for number, image in enumerate(page.get_images(full=True), 1):
                    try:
                        item = document.extract_image(image[0])
                        if item:
                            self.asset(locator + "#image=" + str(number), item["image"], "." + item["ext"])
                    except Exception:
                        self.warn("One or more PDF images could not be extracted")
                if not text.strip():
                    # Bounded rasterization, then human/vision OCR; never invent text.
                    scale = min(1.5, 2000 / max(page.rect.width, page.rect.height, 1))
                    pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                    self.asset(locator + "#ocr-raster", pixmap.tobytes("png"), ".png", review=True)
                    self.warn("Textless PDF pages are queued for OCR/visual review")

    def hwp(self, path):
        command = shutil.which("hwpjs")
        command_args = [command] if command else None
        if command and Path(command).suffix.lower() in {".cmd", ".bat", ".ps1"}:
            # Avoid command-shell execution of arbitrary document filenames.
            package = Path(command).parent / "node_modules/@ohah/hwpjs/package.json"
            command_args = None
            if package.is_file() and shutil.which("node"):
                try:
                    metadata = json.loads(package.read_text(encoding="utf-8"))
                    entry = metadata.get("bin", {})
                    entry = entry.get("hwpjs") if isinstance(entry, dict) else entry
                    script = (package.parent / entry).resolve() if entry else None
                    if script and script.is_relative_to(package.parent.resolve()) and script.is_file():
                        command_args = [shutil.which("node"), str(script)]
                except (ValueError, OSError, TypeError):
                    pass
        if command_args:
            try:
                with tempfile.TemporaryDirectory(prefix="hwp-convert-", dir=self.output) as temp:
                    temp = Path(temp)
                    converted = temp / "document.md"
                    images = temp / "images"
                    result = subprocess.run(command_args + ["to-markdown", str(path), "-o", str(converted), "--images-dir", str(images)],
                                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=90, shell=False)
                    if result.returncode == 0 and converted.is_file() and converted.stat().st_size <= MAX_MEMBER:
                        self.segment("hwpjs:markdown#document", converted.read_text(encoding="utf-8"))
                        if images.is_dir():
                            for image in sorted(images.rglob("*")):
                                if image.is_file() and image.resolve().is_relative_to(images.resolve()) and image.stat().st_size <= MAX_MEMBER:
                                    self.asset("hwpjs:embedded#" + image.name, image.read_bytes(), image.suffix)
                        if self.segments:
                            self.warn("hwpjs conversion has no verified page locators; inspect original layout and table relationships")
                            return
                self.warn("Installed hwpjs conversion failed; using HWP5 fallback")
            except (OSError, subprocess.TimeoutExpired):
                self.warn("Installed hwpjs unavailable/timed out; using HWP5 fallback")
        self.hwp5(path)

    def hwp5(self, path):
        try:
            import olefile
        except ImportError:
            raise ValueError("HWP fallback requires optional dependency: olefile (or install @ohah/hwpjs)") from None
        with olefile.OleFileIO(str(path)) as document:
            if not document.exists("FileHeader"):
                raise ValueError("Not an HWP5 document; legacy HWP3 is unsupported")
            header = document.openstream("FileHeader").read(256)
            if len(header) < 40 or not header.startswith(b"HWP Document File") or header[35] != 5:
                raise ValueError("Unsupported or invalid HWP version")
            flags = struct.unpack_from("<I", header, 36)[0]
            if flags & 2:
                raise ValueError("Password-protected HWP is unsupported")
            if flags & 4:
                raise ValueError("Distribution-protected HWP ViewText is unsupported; provide PDF/HWPX export")
            if flags & (1 << 4):
                self.warn("HWP scripts are present and were not executed")
            self.warn("HWP5 fallback: section/paragraph locators only; page numbers, table structure, and image placement require visual review")
            streams = document.listdir()
            if len(streams) > 10000 or sum(document.get_size(s) for s in streams) > MAX_ARCHIVE:
                raise ValueError("HWP streams exceed safety limit")
            for stream in sorted(streams, key=lambda s: natural("/".join(s))):
                name = "/".join(stream)
                if document.get_size(stream) > MAX_MEMBER:
                    raise ValueError("HWP stream exceeds safety limit")
                if name.startswith("BodyText/Section"):
                    data = document.openstream(stream).read(MAX_MEMBER + 1)
                    if flags & 1:
                        data = inflate_bounded(data)
                    for number, text in hwp_paragraphs(data):
                        self.segment(name + "#paragraph=" + str(number), text)
                elif name.startswith("BinData/"):
                    data = document.openstream(stream).read(MAX_MEMBER + 1)
                    if flags & 1:
                        try:
                            data = inflate_bounded(data)
                        except ValueError:
                            # BinData compression may be individually disabled.
                            if image_extension(data, "") == ".bin":
                                self.warn("A BinData item could not be decompressed; raw bytes retained for inspection")
                    self.asset(name + "#placement-unmapped", data, Path(name).suffix)
            if not self.segments:
                self.warn("No HWP paragraph text extracted; use a rendered PDF for OCR/visual review")

    def extract(self, path):
        extension = path.suffix.lower()
        if extension in OFFICE:
            self.office(path)
        elif extension == ".pdf":
            self.pdf(path)
        elif extension == ".hwp":
            self.hwp(path)
        elif extension in {".txt", ".md", ".csv", ".tsv", ".json"}:
            data = path.read_bytes()
            text = None
            for encoding in ("utf-8-sig", "utf-16" if data.startswith((b"\xff\xfe", b"\xfe\xff")) else "cp949"):
                try:
                    text = data.decode(encoding)
                    break
                except UnicodeError:
                    continue
            if text is None:
                raise ValueError("Text encoding unsupported; save as UTF-8")
            for index, line in enumerate(text.splitlines(), 1):
                self.segment("line=" + str(index), line)
        elif extension in IMAGES:
            self.asset("image:original", path.read_bytes(), extension, review=True)
            self.warn("Image text/data requires visual review; OCR has not been performed")
        else:
            self.entry["status"] = "unsupported"
            self.warn("Unsupported file format; export to PDF, Office XML, or UTF-8 text")


def ingest(input_path, output):
    input_path, output = Path(input_path).resolve(), Path(output).resolve()
    if not input_path.exists():
        raise ValueError("Input path does not exist")
    if output == input_path or (input_path.is_dir() and output.is_relative_to(input_path)):
        raise ValueError("Output must be outside the input directory to prevent recursive ingestion")
    output.mkdir(parents=True, exist_ok=True)
    (output / "assets").mkdir(exist_ok=True)
    candidates = sorted(input_path.rglob("*") if input_path.is_dir() else [input_path], key=lambda p: str(p).casefold())
    files, segments, assets, queue, seen = [], [], [], [], {}
    for path in candidates:
        if not path.is_file():
            continue
        source_file = path.relative_to(input_path).as_posix() if input_path.is_dir() else path.name
        entry = {"source_id": None, "source_file": source_file, "sha256": None, "size_bytes": None,
                 "format": path.suffix.lower().lstrip("."), "status": "ok", "warnings": [], "segment_count": 0, "asset_count": 0}
        files.append(entry)
        try:
            if input_path.is_dir() and not path.resolve().is_relative_to(input_path):
                raise ValueError("Symlink/reparse target outside input directory was not read")
            entry["size_bytes"] = path.stat().st_size
            if entry["size_bytes"] > MAX_FILE:
                raise ValueError("Input file exceeds 256 MiB safety limit")
            with path.open("rb") as source:
                sha = hashlib.file_digest(source, "sha256").hexdigest()
            entry.update(sha256=sha, source_id="src_" + sha)
            if sha in seen:
                entry.update(status="duplicate", duplicate_of=seen[sha])
                continue
            extractor = Extractor(output, entry)
            extractor.extract(path)
            segments.extend(extractor.segments)
            assets.extend(extractor.assets)
            queue.extend(extractor.queue)
            entry.update(segment_count=len(extractor.segments), asset_count=len(extractor.assets))
            if entry["status"] == "ok" and entry["warnings"]:
                entry["status"] = "partial"
            seen[sha] = source_file
        except Exception as exc:
            entry["status"] = "error"
            # Parser diagnostics contain no extracted document content.
            reason = str(exc) if isinstance(exc, (ValueError, OSError, zipfile.BadZipFile, ET.ParseError)) else type(exc).__name__
            entry["warnings"].append(reason[:400])
    counts = dict(Counter(f["status"] for f in files))
    summary = {"files": len(files), "segments": len(segments), "assets": len(assets), "ocr_pending": len(queue), "statuses": counts}
    outputs = {"inventory": {"schema_version": "1.0", "files": files, "summary": summary},
               "documents": {"schema_version": "1.0", "segments": segments, "ocr_queue": queue},
               "assets": {"schema_version": "1.0", "assets": assets}}
    for name, data in outputs.items():
        temporary = output / (name + ".json.tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(output / (name + ".json"))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Source file or recursive folder")
    parser.add_argument("--output", required=True, help="Extraction directory outside the source folder")
    args = parser.parse_args()
    try:
        summary = ingest(args.input, args.output)
    except (OSError, ValueError) as exc:
        parser.exit(2, "ingest: " + str(exc) + "\n")
    print(json.dumps(summary))
    # Per-file failures are intentionally isolated; inventory statuses are the gate.
    return 0


if __name__ == "__main__":
    sys.exit(main())
