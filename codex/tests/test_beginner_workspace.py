import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile


SCRIPTS = Path(__file__).resolve().parents[1] / 'plugins/seed-ir/skills/seed-ir/scripts'


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BeginnerWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)
        self.h = load('harness')

    def seed_input(self, folder='자료넣는곳'):
        h, p = self.h, self.project
        h.initialize(p, '우리 팀', input_dir=folder)
        source = h.input_directory(p) / '팀 소개.txt'
        source.write_text('검증할 사업 아이디어', encoding='utf-8')
        h.write_json(p / 'data/raw/inventory.json', {'files': [{
            'source_id': 'SRC1', 'source_file': source.name, 'status': 'ok', 'sha256': h.sha(source)}]})
        h.write_json(p / 'data/raw/documents.json', {'segments': [{
            'source_id': 'SRC1', 'locator': 'line 1', 'text': source.read_text(encoding='utf-8')}]})
        h.write_json(p / 'data/raw/assets.json', {'assets': []})
        return source

    def test_legacy_default_and_missing_config_field(self):
        self.h.initialize(self.project, '기존 팀')
        self.assertEqual(self.project / 'input', self.h.input_directory(self.project))
        config = self.h.read_json(self.project / 'project.json')
        config.pop('input_dir', None)
        self.h.write_json(self.project / 'project.json', config)
        self.assertEqual(self.project / 'input', self.h.input_directory(self.project))

    def test_korean_input_passes_intake_without_creating_legacy_input(self):
        self.seed_input()
        result = self.h.check(self.project, 'intake')
        self.assertTrue(result['passed'], result['errors'])
        self.assertFalse((self.project / 'input').exists())

    def test_added_changed_deleted_files_invalidate_checkpoint(self):
        source = self.seed_input()
        self.h.record(self.project, 'intake')
        baseline = self.h.fingerprint(self.project, 'intake')
        extra = source.with_name('추가.txt')
        extra.write_text('새 자료', encoding='utf-8')
        self.assertNotEqual(baseline, self.h.fingerprint(self.project, 'intake'))
        self.assertEqual('stale', self.h.status(self.project)['stages']['intake'])
        self.assertFalse(self.h.check(self.project, 'intake')['passed'])
        extra.unlink()
        source.write_text('바뀐 자료', encoding='utf-8')
        self.assertNotEqual(baseline, self.h.fingerprint(self.project, 'intake'))
        self.assertFalse(self.h.check(self.project, 'intake')['passed'])
        source.unlink()
        self.assertNotEqual(baseline, self.h.fingerprint(self.project, 'intake'))
        self.assertFalse(self.h.check(self.project, 'intake')['passed'])

    def test_changing_input_folder_invalidates_checkpoint(self):
        self.seed_input()
        self.h.record(self.project, 'intake')
        config = self.h.read_json(self.project / 'project.json')
        config['input_dir'] = '다른자료'
        self.h.write_json(self.project / 'project.json', config)
        (self.project / '다른자료').mkdir()
        self.assertEqual('stale', self.h.status(self.project)['stages']['intake'])

    def test_input_path_safety_and_normalization(self):
        bad = ['', '.', '..', '../outside', '/outside', 'C:\\outside', 'work',
               'data/raw', 'output', '결과물', '.agents/자료', '.venv', 'deck', 'reviews',
               'research', 'design', 'evidence', 'node_modules', 42]
        for value in bad:
            with self.subTest(value=value), self.assertRaises((TypeError, ValueError)):
                self.h.input_directory(self.project, {'input_dir': value})
        self.assertEqual(self.project / '우리팀/자료',
                         self.h.input_directory(self.project, {'input_dir': '우리팀\\자료'}))

    def test_input_symlink_outside_or_into_internal_is_rejected(self):
        for name, destination in [('외부', self.project.parent), ('내부', self.project / 'output')]:
            destination.mkdir(exist_ok=True)
            link = self.project / name
            try:
                link.symlink_to(destination, target_is_directory=True)
            except OSError:
                self.skipTest('symbolic links unavailable')
            with self.assertRaises(ValueError):
                self.h.input_directory(self.project, {'input_dir': name})

    def test_input_file_symlink_cannot_read_internal_artifacts(self):
        self.seed_input()
        target = self.project / 'output/private.txt'
        target.write_text('internal', encoding='utf-8')
        link = self.project / '자료넣는곳/링크.txt'
        try:
            link.symlink_to(target)
        except OSError:
            self.skipTest('symbolic links unavailable')
        with self.assertRaises(ValueError):
            self.h.fingerprint(self.project, 'intake')

    def seed_publication(self):
        source = self.seed_input()
        h, p = self.h, self.project
        # Default fixture preserves legacy v1.2 publication compatibility.
        config = h.read_json(p / 'project.json')
        config['require_visual_briefs'] = False
        config['require_visual_plan'] = False
        h.write_json(p / 'project.json', config)
        deck = h.read_json(p / 'deck/deck.json')
        for slide in deck['slides']:
            slide.update(governing_message='계획: 사용자 문제를 검증합니다', governing_kind='plan',
                         speaker_notes='계획의 가정을 설명합니다.')
        h.write_json(p / 'deck/deck.json', deck)
        h.write_json(p / 'evidence/evidence.json', {'items': [{
            'id': 'E1', 'claim': '자료에 제시된 사업 아이디어', 'kind': 'internal', 'status': 'confirmed',
            'source_id': 'SRC1', 'locator': 'line 1'}]})
        common = {'reviewer': '검토자', 'rationale': '현재 자료를 대조했습니다.', 'verdict': 'pass',
                  'deck_sha256': h.sha(p / 'deck/deck.json'),
                  'evidence_sha256': h.sha(p / 'evidence/evidence.json'),
                  'source_documents_sha256': h.sha(p / 'data/raw/documents.json'), 'findings': []}
        investor = dict(common, verdict='revise', briefs_sha256=h.sha(p / 'deck/section-briefs.json'))
        h.write_json(p / 'reviews/investor.json', investor)
        visual = dict(common, views={})
        for view in ('master', 'pitch'):
            target = p / f'output/{view}/seed-ir-draft.pptx'
            target.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(target, 'w') as archive:
                archive.writestr('ppt/presentation.xml', '<presentation/>')
                for i in range(len(deck['views'][view]['slide_ids'])):
                    archive.writestr(f'ppt/slides/slide{i + 1}.xml', '<slide/>')
            image_dir = target.parent / 'renders'
            image_dir.mkdir()
            images = []
            for i in range(len(deck['views'][view]['slide_ids'])):
                image = image_dir / f'{i + 1}.png'
                image.write_bytes(b'\x89PNG\r\n\x1a\n' + b'fixture')
                images.append(image.relative_to(p).as_posix())
            receipt = {'verdict': 'pass', 'pptx_sha256': h.sha(target), 'render_method': 'artifact-tool',
                       'slides_reviewed': deck['views'][view]['slide_ids'], 'render_files': images,
                       'render_sha256': {rel: h.sha(p / rel) for rel in images},
                       'checks': {key: 'pass' for key in (
                           'text_overflow', 'font_substitution', 'contrast', 'chart_labels', 'image_crops')}}
            if view == 'pitch':
                (p / 'output/seed-ir-draft.pptx').write_bytes(target.read_bytes())
                visual.update(receipt)
            else:
                visual['views'][view] = receipt
        h.write_json(p / 'reviews/visual.json', visual)
        h.write_json(p / 'reviews/pitch.json', dict(common, pptx_sha256=visual['pptx_sha256'],
                     method='estimated', duration_seconds=285, estimation_basis='말하기 속도와 장표 전환시간'))
        (p / 'output/pitch-script.md').write_text('옛 대본: 가져오면 안 됩니다.', encoding='utf-8')
        (p / 'output/seed-ir-final.pptx').write_bytes(b'STALE FINAL')
        return load('publish_results')

    def test_publisher_labels_draft_and_ignores_old_final_and_stale_script(self):
        publisher = self.seed_publication()
        result = publisher.publish(self.project)
        self.assertEqual('draft', result['status'])
        folder = self.project / result['run_dir']
        self.assertTrue((folder / '결과보기.html').is_file())
        deck = folder / '5분_발표본_보완초안.pptx'
        self.assertEqual((self.project / 'output/seed-ir-draft.pptx').read_bytes(), deck.read_bytes())
        script = (folder / '5분_발표대본.md').read_text(encoding='utf-8')
        self.assertIn('계획의 가정을 설명합니다', script)
        self.assertNotIn('옛 대본', script)
        second = publisher.publish(self.project)
        self.assertNotEqual(result['run_dir'], second['run_dir'])
        self.assertTrue(folder.exists())

    def seed_visual_publication(self):
        publisher = self.seed_publication()
        h, p = self.h, self.project
        config = h.read_json(p / 'project.json')
        config['require_visual_briefs'] = True
        h.write_json(p / 'project.json', config)
        deck = h.read_json(p / 'deck/deck.json')
        for slide in deck['slides']:
            slide['layout'] = 'cover'
            slide['blocks'] = [{'id': 'B1', 'type': 'text', 'title': '계획',
                'kind': 'plan', 'evidence_ids': [], 'text': '계획: 추가 확인'}]
            slide['visual_brief'] = {'key_message': slide['governing_message'],
                'primary_block_id': 'B1', 'reading_order': ['B1'], 'layout_variant': 'cover_focus',
                'visual_reason': 'Synthetic contract fixture only'}
            if slide['section'] == 'product':
                slide['blocks'][0] = {'id': 'B1', 'type': 'image', 'title': '계획: 제품 화면',
                    'kind': 'plan', 'evidence_ids': ['E1'], 'path': 'output/master/renders/1.png',
                    'caption': '계획: 가상 제품 화면', 'source': 'Synthetic test fixture only',
                    'rights': 'owned', 'alt': '계획: 제품 화면'}
                slide['visual_brief']['layout_variant'] = 'product_hero'
        h.write_json(p / 'deck/deck.json', deck)
        for name in ('investor', 'pitch', 'visual'):
            path = p / f'reviews/{name}.json'
            receipt = h.read_json(path)
            receipt['deck_sha256'] = h.sha(p / 'deck/deck.json')
            if name == 'visual':
                for view in ('master', 'pitch'):
                    review = receipt['views']['master'] if view == 'master' else receipt
                    review.update(reviewer='Synthetic fixture', rationale='Not a human design review',
                        checks={key: 'pass' for key in h.quality.VISUAL_REVIEW_CHECKS},
                        visual_observations=[{'slide_id': sid, 'hierarchy': 'Synthetic fixture observation',
                            'evidence_legibility': 'Synthetic fixture observation'}
                            for sid in deck['views'][view]['slide_ids']],
                        composition_review='Synthetic receipt validation fixture only')
            h.write_json(path, receipt)
        return publisher

    def test_locked_staging_directory_falls_back_to_verified_snapshot_copies(self):
        publisher = self.seed_publication()
        first = publisher.publish(self.project)
        original_rename = Path.rename
        def locked_staging(path, destination):
            if path.name.startswith('.준비중-'):
                raise PermissionError('simulated sync directory lock')
            return original_rename(path, destination)
        with patch.object(Path, 'rename', new=locked_staging):
            second = publisher.publish(self.project)
        self.assertNotEqual(first['run_dir'], second['run_dir'])
        folder = self.project / second['run_dir']
        self.assertEqual((folder / '5분_발표본_보완초안.pptx').read_bytes(),
                         (self.project / 'output/seed-ir-draft.pptx').read_bytes())
        self.assertEqual((folder / '상세본_보완초안.pptx').read_bytes(),
                         (self.project / 'output/master/seed-ir-draft.pptx').read_bytes())
        landing = (self.project / '결과물/결과보기.html').read_text('utf-8')
        self.assertIn(folder.name, landing)
        self.assertTrue((self.project / 'work/publications' / (folder.name + '.json')).is_file())

    def test_failed_or_corrupt_sync_copy_never_changes_latest_publication(self):
        publisher = self.seed_publication()
        publisher.publish(self.project)
        landing = self.project / '결과물/결과보기.html'
        previous = landing.read_bytes()
        manifests = set((self.project / 'work/publications').iterdir())
        original_rename, original_write = Path.rename, Path.write_bytes
        def locked_staging(path, destination):
            if path.name.startswith('.준비중-'):
                raise PermissionError('simulated sync directory lock')
            return original_rename(path, destination)
        for failure in ('io', 'corruption'):
            def failed_copy(path, value):
                if (path.parent.parent == landing.parent
                        and not path.parent.name.startswith('.')
                        and path.name == '5분_발표대본.md'):
                    if failure == 'io':
                        raise OSError('simulated partial copy failure')
                    return original_write(path, b'corrupted copy')
                return original_write(path, value)
            with self.subTest(failure=failure), \
                    patch.object(Path, 'rename', new=locked_staging), \
                    patch.object(Path, 'write_bytes', new=failed_copy):
                with self.assertRaises((OSError, ValueError)):
                    publisher.publish(self.project)
            self.assertEqual(landing.read_bytes(), previous)
            self.assertEqual(set((self.project / 'work/publications').iterdir()), manifests)

    def test_strict_visual_publication_accepts_complete_contract(self):
        publisher = self.seed_visual_publication()
        result = publisher.publish(self.project)
        self.assertEqual('draft', result['status'])

    def test_strict_visual_publication_rejects_missing_brief_before_creating_results(self):
        publisher = self.seed_publication()
        config = self.h.read_json(self.project / 'project.json')
        config['require_visual_briefs'] = True
        self.h.write_json(self.project / 'project.json', config)
        with self.assertRaisesRegex(ValueError, 'visual_brief'):
            publisher.publish(self.project)
        self.assertFalse((self.project / '결과물/결과보기.html').exists())

    def test_strict_visual_publication_rejects_missing_human_observations(self):
        publisher = self.seed_visual_publication()
        path = self.project / 'reviews/visual.json'
        receipt = self.h.read_json(path)
        receipt['views']['master']['visual_observations'] = []
        self.h.write_json(path, receipt)
        with self.assertRaisesRegex(ValueError, 'visual_observations'):
            publisher.publish(self.project)
        self.assertFalse((self.project / '결과물/결과보기.html').exists())

    def test_publisher_questions_are_human_readable_without_claim_objects(self):
        publisher = self.seed_publication()
        briefs_path = self.project / 'deck/section-briefs.json'
        briefs = self.h.read_json(briefs_path)
        question = briefs['sections'][0]['questions'][0]
        question['answer'] = {'text': '계획: 고객의 문제를 해결합니다', 'kind': 'plan', 'evidence_ids': []}
        question['argument'] = [{'text': '계획: 인터뷰로 검증할 내용입니다', 'kind': 'plan', 'evidence_ids': []}]
        self.h.write_json(briefs_path, briefs)
        investor_path = self.project / 'reviews/investor.json'
        investor = self.h.read_json(investor_path)
        investor['briefs_sha256'] = self.h.sha(briefs_path)
        self.h.write_json(investor_path, investor)
        result = publisher.publish(self.project)
        text = (self.project / result['run_dir'] / '예상질문과_답변.md').read_text(encoding='utf-8')
        self.assertIn('계획: 고객의 문제를 해결합니다', text)
        self.assertIn('계획: 인터뷰로 검증할 내용입니다', text)
        self.assertNotIn('evidence_ids', text)
        self.assertNotIn("'kind'", text)

    def test_publisher_refuses_changed_deck_pptx_render_input_or_missing_review(self):
        publisher = self.seed_publication()
        for relative in ('deck/deck.json', 'output/seed-ir-draft.pptx',
                         'output/master/renders/1.png', '자료넣는곳/팀 소개.txt', 'reviews/investor.json'):
            with self.subTest(relative=relative):
                path = self.project / relative
                original = path.read_bytes()
                if relative == 'reviews/investor.json':
                    path.unlink()
                else:
                    path.write_bytes(original + b' ')
                with self.assertRaises((ValueError, FileNotFoundError)):
                    publisher.publish(self.project)
                path.write_bytes(original)
        self.assertFalse((self.project / '결과물/결과보기.html').exists())

    def test_publisher_refuses_missing_render_hashes_and_unsafe_destination(self):
        publisher = self.seed_publication()
        for destination in ('../outside', '자료넣는곳', 'work/results', 'output', '.'):
            with self.subTest(destination=destination), self.assertRaises(ValueError):
                publisher.publish(self.project, output_dir=destination)
        path = self.project / 'reviews/visual.json'
        receipt = self.h.read_json(path)
        receipt.pop('render_sha256')
        self.h.write_json(path, receipt)
        with self.assertRaisesRegex(ValueError, '렌더.*지문|render_sha256'):
            publisher.publish(self.project)

    def test_publisher_final_label_requires_live_final_gate(self):
        publisher = self.seed_publication()
        original = publisher.h.check
        def check(project, stage):
            if stage == 'final':
                return {'stage': stage, 'passed': True, 'errors': [], 'warnings': []}
            return original(project, stage)
        with patch.object(publisher.h, 'check', side_effect=check):
            result = publisher.publish(self.project)
        self.assertEqual('final', result['status'])
        self.assertTrue((self.project / result['run_dir'] / '5분_발표본_최종.pptx').is_file())


if __name__ == '__main__':
    unittest.main()
