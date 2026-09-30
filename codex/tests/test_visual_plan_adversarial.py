"""Visual-plan failure cases: displayed evidence must outlive filled form fields."""
import copy
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'plugins/seed-ir/skills/seed-ir/scripts'


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class VisualPlanAdversarialTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)
        self.validator = load(SCRIPTS / 'visual_plan.py', 'visual_plan_adversarial')
        self.evidence = {'A7': {}, 'OTHER': {}}
        self.deck = {'slides': [{'id': 'CUSTOM', 'blocks': [
            {'id': 'FLOW', 'type': 'steps', 'evidence_ids': ['A7'],
             'items': [{'title': '접수', 'text': '서비스 접수 계획'}]}]}],
            'views': {'master': {'slide_ids': ['CUSTOM']}, 'pitch': {'slide_ids': ['CUSTOM']}}}
        self.plan = {'schema_version': '1.0', 'slides': [{
            'slide_id': 'CUSTOM', 'evidence_ids': ['A7'], 'block_ids': ['FLOW'],
            'visual_type': 'diagram', 'source_strategy': 'native', 'asset_refs': [],
            'disclosure': '계획', 'claim_boundary': '접수 흐름 설계이며 실적이 아니다',
            'status': 'ready', 'search_note': '사용자 제공 접수 절차를 도식으로 설명한다'}]}

    def validate(self):
        return self.validator.validate(self.plan, self.deck, self.evidence,
                                       self.project, required=True, final=True)

    def add_image(self):
        path = self.project / 'mockup.png'
        path.write_bytes(b'fixture image bytes')
        asset = {'path': 'mockup.png', 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                 'source': 'generated concept fixture', 'rights': 'owned', 'origin': 'generated',
                 'caption': 'AI 생성 제품 설계안', 'claim_boundary': '실제 제품 구현을 입증하지 않는다'}
        self.deck['slides'][0]['blocks'] = [{'id': 'SCREEN', 'type': 'image',
                                          'evidence_ids': ['A7'], **asset}]
        self.plan['slides'][0].update(block_ids=['SCREEN'], visual_type='product_ui',
            source_strategy='generated', disclosure='AI 생성 제품 설계안', asset_refs=[copy.deepcopy(asset)])
        return asset

    def test_malformed_enum_and_disclosure_fields_return_errors_without_crashing(self):
        baseline = copy.deepcopy(self.plan)
        for field, value in [('source_strategy', []), ('visual_type', {}),
                             ('status', []), ('disclosure', {'text': 'AI 생성'})]:
            with self.subTest(field=field):
                self.plan = copy.deepcopy(baseline)
                self.plan['slides'][0]['source_strategy'] = 'generated'
                self.plan['slides'][0][field] = value
                try:
                    result = self.validate()
                except (TypeError, ValueError, AttributeError) as error:
                    self.fail(f'{field}: validator crashed instead of reporting malformed input: {error}')
                self.assertTrue(result['errors'])

    def test_malformed_asset_fields_return_errors_without_crashing(self):
        self.add_image()
        baseline = copy.deepcopy(self.plan)
        for field, value in [('rights', []), ('origin', {}), ('caption', {'text': 'AI 생성'})]:
            with self.subTest(field=field):
                self.plan = copy.deepcopy(baseline)
                self.plan['slides'][0]['asset_refs'][0][field] = value
                try:
                    result = self.validate()
                except (TypeError, ValueError, AttributeError) as error:
                    self.fail(f'{field}: validator crashed instead of reporting malformed input: {error}')
                self.assertTrue(result['errors'])

    def test_mixed_cannot_mark_a_plain_text_only_slide_as_ready_visuals(self):
        self.deck['slides'][0]['blocks'] = [{'id': 'TEXT', 'type': 'text',
            'text': '한 문장만 있는 원고', 'evidence_ids': ['A7']}]
        self.plan['slides'][0].update(block_ids=['TEXT'], visual_type='mixed')
        self.assertTrue(self.validate()['errors'], 'mixed must reference actual visual content')

    def test_product_ui_cannot_resolve_its_image_only_from_unused_supporting_metadata(self):
        asset = self.add_image()
        self.deck['slides'][0]['blocks'] = [{'id': 'FLOW', 'type': 'steps',
            'items': [{'title': '입력', 'text': '화면 없는 절차 설명'}], 'evidence_ids': ['A7']}]
        self.deck['slides'][0]['visual_brief'] = {'supporting_assets': [asset]}
        self.plan['slides'][0]['block_ids'] = ['FLOW']
        self.assertTrue(self.validate()['errors'], 'a metadata-only image is not displayed product UI')

    def test_asset_must_belong_to_the_selected_visual_blocks(self):
        self.add_image()
        self.deck['slides'][0]['blocks'].append({'id': 'FLOW', 'type': 'steps',
            'items': [{'title': '입력', 'text': '화면 없는 절차 설명'}], 'evidence_ids': ['A7']})
        self.plan['slides'][0]['block_ids'] = ['FLOW']
        self.assertTrue(self.validate()['errors'], 'unrelated image elsewhere cannot fulfill FLOW image requirement')

    def test_native_strategy_cannot_omit_the_asset_it_declares_as_product_ui(self):
        self.add_image()
        self.plan['slides'][0].update(source_strategy='native', asset_refs=[])
        self.assertTrue(self.validate()['errors'], 'native cannot bypass image provenance and hash checks')

    def test_duplicate_evidence_ids_fail_as_required_by_schema(self):
        self.plan['slides'][0]['evidence_ids'] = ['A7', 'A7']
        self.assertTrue(self.validate()['errors'])

    def test_ai_product_claim_alone_is_not_a_generated_image_disclosure(self):
        self.add_image()
        claim = '실제 고객 데이터로 입증한 AI 성능'
        self.plan['slides'][0]['disclosure'] = claim
        self.plan['slides'][0]['asset_refs'][0]['caption'] = claim
        self.deck['slides'][0]['blocks'][0]['caption'] = claim
        self.assertTrue(self.validate()['errors'], 'AI describes a product, not necessarily a fabricated illustration')

    def test_invalid_filesystem_path_is_reported_instead_of_crashing(self):
        self.add_image()
        self.plan['slides'][0]['asset_refs'][0]['path'] = 'invalid\x00.png'
        try:
            result = self.validate()
        except (OSError, ValueError) as error:
            self.fail(f'invalid path crashed validator instead of a validation error: {error}')
        self.assertTrue(result['errors'])

    def test_publisher_enforces_required_visual_plan_before_creating_latest_pointer(self):
        fixtures = load(ROOT / 'tests/test_beginner_workspace.py', 'visual_plan_publication_fixtures')
        fixture = fixtures.BeginnerWorkspaceTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        publisher = fixture.seed_publication()
        config = fixture.h.read_json(fixture.project / 'project.json')
        config['require_visual_plan'] = True
        fixture.h.write_json(fixture.project / 'project.json', config)
        with self.assertRaisesRegex(ValueError, 'visual.plan|시각 자료'):
            publisher.publish(fixture.project)
        self.assertFalse((fixture.project / '결과물/결과보기.html').exists())

    def test_optional_but_present_invalid_plan_is_not_ignored_by_publisher(self):
        fixtures = load(ROOT / 'tests/test_beginner_workspace.py', 'visual_plan_legacy_publication_fixtures')
        fixture = fixtures.BeginnerWorkspaceTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        publisher = fixture.seed_publication()
        path = fixture.project / 'design/visual-plan.json'
        for value in ('null', '{invalid JSON', '{"schema_version":"1.0","slides":[]}'):
            with self.subTest(value=value):
                path.write_text(value, encoding='utf-8')
                with self.assertRaises(ValueError):
                    publisher.publish(fixture.project)
                self.assertFalse((fixture.project / '결과물/결과보기.html').exists())
        path.unlink()
        path.mkdir()
        with self.assertRaises(ValueError):
            publisher.publish(fixture.project)
        self.assertFalse((fixture.project / '결과물/결과보기.html').exists())

    def test_publisher_accepts_current_complete_plan_but_keeps_investor_revise_as_draft(self):
        fixtures = load(ROOT / 'tests/test_beginner_workspace.py', 'visual_plan_valid_publication_fixtures')
        fixture = fixtures.BeginnerWorkspaceTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        publisher = fixture.seed_visual_publication()
        h, project = fixture.h, fixture.project
        config = h.read_json(project / 'project.json')
        config['require_visual_plan'] = True
        h.write_json(project / 'project.json', config)
        deck = h.read_json(project / 'deck/deck.json')
        plans = []
        for slide in deck['slides']:
            block = slide['blocks'][0]
            row = {'slide_id': slide['id'], 'evidence_ids': ['E1'], 'block_ids': ['B1'],
                'visual_type': 'quote', 'source_strategy': 'native', 'asset_refs': [],
                'disclosure': '계획', 'claim_boundary': '사업 검증 전 계획',
                'status': 'ready', 'search_note': '원고의 계획을 직접 표시한 fixture'}
            if block['type'] == 'image':
                row.update(visual_type='product_ui', source_strategy='original', asset_refs=[{
                    'path': block['path'], 'sha256': h.sha(project / block['path']),
                    'source': block['source'], 'rights': block['rights'], 'origin': 'original',
                    'caption': block['caption'], 'claim_boundary': '기능 검증용 합성 파일'}])
            plans.append(row)
        h.write_json(project / 'design/visual-plan.json', {'schema_version': '1.0', 'slides': plans})
        result = publisher.publish(project)
        self.assertEqual(result['status'], 'draft')
        self.assertTrue((project / result['run_dir'] / '5분_발표본_보완초안.pptx').is_file())


if __name__ == '__main__':
    unittest.main()
