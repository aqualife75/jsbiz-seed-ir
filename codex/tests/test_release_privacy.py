"""Release safeguards exercise fictional sentinels, never private team data."""
import base64
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('guarded_release',ROOT/'build_release.py')
release=importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class PrivacyReleaseTests(unittest.TestCase):
    def test_nested_slide_notes_are_inspected(self):
        private='sentinelsecret'
        digest=hashlib.sha256(private.encode()).hexdigest()
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w') as archive:
            archive.writestr('ppt/notesSlides/notesSlide1.xml',f'<note>{private}</note>')
        with patch.object(release,'PRIVATE_TOKEN_DIGESTS',{digest}):
            with self.assertRaisesRegex(ValueError,'Private identifier'):
                release.audit_payload(stream.getvalue(),'sample.pptx')

    def test_split_xml_runs_and_escaped_json_are_inspected(self):
        private='sentinelsecret'
        digest=hashlib.sha256(private.encode()).hexdigest()
        with patch.object(release,'PRIVATE_TOKEN_DIGESTS',{digest}):
            for raw in [b'<p><t>sentinel</t><t>secret</t></p>',br'{"team":"sentinel\u0073ecret"}']:
                with self.assertRaisesRegex(ValueError,'Private identifier'):
                    release.audit_payload(raw,'metadata')

    def test_embedded_html_image_digest_is_checked(self):
        private=b'private-test-bitmap'
        digest=hashlib.sha256(private).hexdigest()
        html=b'<img src="data:image/png;base64,'+base64.b64encode(private)+b'">'
        with patch.object(release,'PRIVATE_FILE_DIGESTS',{digest}):
            with self.assertRaisesRegex(ValueError,'Private asset'):
                release.audit_payload(html,'viewer.html')

    def test_manifest_rejects_path_escape_and_changed_binary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'examples').mkdir()
            manifest=root/'examples/sample-assets.json'
            manifest.write_text(json.dumps({'sample_id':'glucopic-fictional','assets':[
                {'path':'examples/../private.png','sha256':'0'*64}]}),'utf-8')
            with patch.object(release,'ROOT',root):
                with self.assertRaisesRegex(ValueError,'Invalid'):
                    release.approved_sample_files()
                binary=root/'examples/sample.png';binary.write_bytes(b'fictional-image')
                manifest.write_text(json.dumps({'sample_id':'glucopic-fictional','assets':[
                    {'path':'examples/sample.png','sha256':'0'*64}]}),'utf-8')
                with self.assertRaisesRegex(ValueError,'Unapproved or changed'):
                    release.checked_files()
                data=json.loads(manifest.read_text('utf-8'))
                data['assets'][0]['sha256']=hashlib.sha256(binary.read_bytes()).hexdigest()
                manifest.write_text(json.dumps(data),'utf-8')
                self.assertIn(binary,release.checked_files())

    def test_public_sample_passes_and_personal_path_fails(self):
        release.audit_payload('글루코픽 교육용 AI 가상 사례'.encode(),'approved.md')
        with self.assertRaisesRegex(ValueError,'Private absolute path'):
            release.audit_payload('/'.join(['C:','Users','example','private.md']).encode(),'notes.txt')

    def test_utf16_xml_and_compound_identifiers_are_inspected(self):
        private='sentinelsecret'
        digest=hashlib.sha256(private.encode()).hexdigest()
        with patch.object(release,'PRIVATE_TOKEN_DIGESTS',{digest}), patch.object(release,'PRIVATE_TOKEN_LENGTHS',{len(private)}):
            for raw in [f'<note>{private}</note>'.encode('utf-16'),
                        f'{private}Deck {private}사업계획서'.encode()]:
                with self.assertRaisesRegex(ValueError,'Private identifier'):
                    release.audit_payload(raw,'notes.xml')
            with self.assertRaisesRegex(ValueError,'Undecodable text'):
                release.audit_payload(b'\x81\x82invalid','notes.xml')

    def test_nested_sample_text_is_never_selected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); nested=root/'examples/unapproved-team';nested.mkdir(parents=True)
            (root/'examples/sample-assets.json').write_text(json.dumps({'sample_id':'glucopic-fictional','assets':[]}), 'utf-8')
            (nested/'demo-input.md').write_text('Unapproved client material', 'utf-8')
            with patch.object(release,'ROOT',root):
                with self.assertRaisesRegex(ValueError,'Unapproved example file'):
                    release.checked_files()


if __name__=='__main__': unittest.main()
