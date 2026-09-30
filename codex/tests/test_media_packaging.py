"""Focused safety checks using only Python's standard library."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

SCRIPT = Path(__file__).resolve().parents[1] / 'plugins/seed-ir/skills/seed-ir/scripts/deduplicate_pptx_media.py'
spec = importlib.util.spec_from_file_location('seed_ir_media_packaging', SCRIPT)
media = importlib.util.module_from_spec(spec)
spec.loader.exec_module(media)
deduplicate_pptx_media = media.deduplicate_pptx_media
validate_relationships = media.validate_relationships
REL = 'http://schemas.openxmlformats.org/package/2006/relationships'
CT = 'http://schemas.openxmlformats.org/package/2006/content-types'


def members(path):
    with zipfile.ZipFile(path) as z:
        return {n: z.read(n) for n in z.namelist()}


class DedupTests(unittest.TestCase):
    def fixture(self, path, broken=False):
        data = {
            '[Content_Types].xml': f'''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="{CT}">
 <Default Extension="png" ContentType="image/png"/>
 <Override PartName="/ppt/media/b%20copy.png" ContentType="image/png"/>
 <Override PartName="/ppt/presentation.xml" ContentType="test/presentation"/>
</Types>'''.encode(),
            '_rels/.rels': f'''<Relationships xmlns="{REL}"><Relationship Id="r1" Type="presentation" Target="ppt/presentation.xml"/><Relationship Id="r2" Type="image" Target="/ppt/media/b%20copy.png#example"/></Relationships>'''.encode(),
            'ppt/presentation.xml': b'<presentation/>',
            'ppt/slides/slide1.xml': b'<slide><!-- Preserve precisely --></slide>',
            'ppt/slides/_rels/slide1.xml.rels': f'''<?xml version="1.0"?><r:Relationships xmlns:r="{REL}"><r:Relationship Id='x1' Type='image' Target='../media/b%20copy.png?source=1&amp;keep=2#part'/><r:Relationship Id='x2' Type='hyperlink' Target='https://example.test/ppt/media/b%20copy.png' TargetMode='External'/><r:Relationship Id='x3' Type='image' Target='../media/a.png'/></r:Relationships>'''.encode(),
            'ppt/media/a.png': b'original image bytes\x00\xff',
            'ppt/media/b copy.png': b'original image bytes\x00\xff',
            'ppt/media/c.jpg': b'original image bytes\x00\xff',
            'ppt/media/d.png': b'other image bytes',
            'customXml/item1.xml': b'<arbitrary>unchanged payload</arbitrary>',
        }
        if broken:
            data['ppt/slides/_rels/slide1.xml.rels'] = data['ppt/slides/_rels/slide1.xml.rels'].replace(b'../media/a.png', b'../media/missing.png')
        with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
            z.comment = b'preserve archive comment'
            for name, payload in data.items():
                z.writestr(name, payload)
        return data

    def test_uri_rewrite_exact_preservation_and_idempotence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'fixture.pptx'
            before = self.fixture(path)
            report = deduplicate_pptx_media(path)
            after = members(path)
            self.assertEqual(report['media_count_before'], 4)
            self.assertEqual(report['media_count_after'], 3)
            self.assertEqual(report['rewritten_relationships'], 2)
            self.assertEqual(report['removed_content_type_overrides'], 1)
            self.assertNotIn('ppt/media/b copy.png', after)
            for name in ['ppt/media/a.png', 'ppt/media/c.jpg', 'ppt/media/d.png', 'ppt/slides/slide1.xml', 'customXml/item1.xml']:
                self.assertEqual(before[name], after[name])
            self.assertEqual(after['_rels/.rels'], before['_rels/.rels'].replace(b'/ppt/media/b%20copy.png#example', b'ppt/media/a.png#example'))
            self.assertEqual(after['ppt/slides/_rels/slide1.xml.rels'], before['ppt/slides/_rels/slide1.xml.rels'].replace(b"Target='../media/b%20copy.png?source=1&amp;keep=2#part'", b"Target='../media/a.png?source=1&amp;keep=2#part'"))
            validate_relationships(after)
            archive_bytes = path.read_bytes()
            self.assertFalse(deduplicate_pptx_media(path)['changed'])
            self.assertEqual(path.read_bytes(), archive_bytes)

    def test_invalid_relationship_leaves_original_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'broken.pptx'
            self.fixture(path, broken=True)
            before = path.read_bytes()
            with self.assertRaises(ValueError):
                deduplicate_pptx_media(path)
            self.assertEqual(path.read_bytes(), before)

    def test_failed_atomic_replace_preserves_input(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fixture.pptx'
            self.fixture(path)
            before = path.read_bytes()
            with patch.object(media.os, 'replace', side_effect=PermissionError('locked')):
                with self.assertRaises(PermissionError):
                    deduplicate_pptx_media(path)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_transient_windows_lock_retries_only_atomic_replace(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fixture.pptx'
            self.fixture(path)
            original_replace = media.os.replace
            calls = []
            def briefly_locked(source, destination):
                calls.append((source, destination))
                if len(calls) == 1:
                    error = PermissionError('simulated Windows sharing lock')
                    error.winerror = 32
                    raise error
                return original_replace(source, destination)
            with patch.object(media.os, 'replace', side_effect=briefly_locked), \
                    patch.object(media.time, 'sleep') as sleep:
                report = deduplicate_pptx_media(path)
            self.assertEqual(report['atomic_replace_attempts'], 2)
            self.assertEqual(len(calls), 2)
            sleep.assert_called_once_with(.2)
            validate_relationships(members(path))

    def test_concurrent_change_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fixture.pptx'
            self.fixture(path)
            changed = b'concurrent user save'
            original_chmod = media.os.chmod
            def changed_before_replace(target, mode):
                original_chmod(target, mode)
                path.write_bytes(changed)
            with patch.object(media.os, 'chmod', side_effect=changed_before_replace):
                with self.assertRaisesRegex(RuntimeError, 'Input changed before replacement'):
                    deduplicate_pptx_media(path)
            self.assertEqual(path.read_bytes(), changed)
            self.assertEqual(list(Path(directory).iterdir()), [path])


if __name__ == '__main__':
    unittest.main()
