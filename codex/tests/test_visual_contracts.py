import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'plugins/seed-ir/skills/seed-ir/scripts'


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class VisualContractTests(unittest.TestCase):
    def setUp(self):
        self.q = load('quality')
        self.h = load('harness')
        self.slide = {'id': 'S1', 'section': 'product', 'governing_message': '계획: 입력을 간단하게',
            'blocks': [
                {'id': 'B1', 'type': 'image', 'path': 'assets/screen.png', 'source': '가상 설계안',
                 'caption': '계획: 교육용 가상 화면', 'kind': 'plan', 'evidence_ids': ['E1']},
                {'id': 'B2', 'type': 'text', 'text': '계획: 사진 입력 뒤 결과 확인'}],
            'visual_brief': {'key_message': '계획: 입력을 간단하게', 'primary_block_id': 'B1',
                'reading_order': ['B1', 'B2'], 'layout_variant': 'product_hero',
                'visual_reason': '가상 설계 화면의 입력부를 확대하여 흐름을 설명한다'}}
        self.evidence = {'E1': {'status': 'confirmed', 'kind': 'internal'}}

    def check(self, slide=None, required=True, final=True):
        return self.q.validate_visual_brief(slide or self.slide, self.evidence,
                                             required=required, final=final)

    def test_complete_visual_brief_and_fictional_asset_are_valid(self):
        self.assertEqual([], self.check()['errors'])
        self.assertTrue(self.check()['complete'])

    def test_legacy_missing_is_optional_and_new_missing_stays_draft_until_design(self):
        self.slide.pop('visual_brief')
        self.assertFalse(self.check(required=False)['errors'])
        draft = self.check(final=False)
        self.assertTrue(draft['warnings'])
        self.assertFalse(draft['errors'])
        self.assertTrue(self.check()['errors'])

    def test_bad_primary_and_duplicate_omitted_or_unknown_reading_order_fail(self):
        for primary, order in [('NO', ['B1', 'B2']), ('B1', ['B1', 'B1']),
                               ('B1', ['B1']), ('B1', ['B1', 'NO']), ('B1', [1, {}])]:
            with self.subTest(primary=primary, order=order):
                slide = copy.deepcopy(self.slide)
                slide['visual_brief'].update(primary_block_id=primary, reading_order=order)
                self.assertTrue(self.check(slide, required=False, final=False)['errors'])

    def test_null_brief_is_malformed_not_legacy_missing(self):
        self.slide['visual_brief'] = None
        self.assertTrue(self.check(required=False, final=False)['errors'])

    def test_key_message_cannot_hide_excluded_funding_content(self):
        self.slide['visual_brief']['key_message'] = '계획: 투자 요청 금액 1억 원'
        self.assertTrue(self.q.contains_excluded_funding(self.slide))

    def test_variant_must_match_primary_and_product_cannot_pass_as_text_only(self):
        self.slide['visual_brief']['layout_variant'] = 'market_layers'
        self.assertTrue(any('formula' in e for e in self.check()['errors']))
        self.slide['visual_brief'].update(layout_variant='product_hero', primary_block_id='B2')
        self.assertTrue(any('product_hero' in e for e in self.check()['errors']))
        self.slide['blocks'].pop(0)
        self.slide['visual_brief'].update(layout_variant='evidence_focus', reading_order=['B2'])
        self.assertTrue(any('제품' in e for e in self.check()['errors']))

    def test_product_asset_must_have_provenance_and_valid_evidence(self):
        for field, value in [('source', ''), ('path', ''), ('evidence_ids', []),
                              ('evidence_ids', ['UNKNOWN'])]:
            with self.subTest(field=field, value=value):
                slide = copy.deepcopy(self.slide)
                slide['blocks'][0][field] = value
                self.assertTrue(self.check(slide)['errors'])

    def test_product_steps_can_use_nested_asset_and_inherited_evidence(self):
        asset = self.slide['blocks'][0]
        asset.pop('evidence_ids')
        self.slide['blocks'][0] = {'id': 'B1', 'type': 'steps', 'evidence_ids': ['E1'],
                                  'items': [{'title': '입력', 'asset': asset}]}
        self.assertFalse(self.check()['errors'])

    def test_visual_review_requires_observations_for_every_slide(self):
        checks = {key: 'pass' for key in self.q.VISUAL_REVIEW_CHECKS}
        receipt = {'reviewer': '검수자', 'rationale': '현재 PPTX 렌더를 직접 검토함',
            'checks': checks, 'visual_observations': [
                {'slide_id': 'S1', 'hierarchy': '제목 다음에 입력 화면이 보임',
                 'evidence_legibility': '확대한 입력 버튼과 출처를 읽을 수 있음'}],
            'composition_review': '제품 화면 중심 장표 다음 비교표로 전환하여 관계를 구분함'}
        self.assertFalse(self.q.validate_visual_review(receipt, ['S1'], 'pitch'))
        receipt['visual_observations'] = []
        self.assertTrue(self.q.validate_visual_review(receipt, ['S1'], 'pitch'))

    def test_new_project_enables_v14_but_preserves_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            self.h.initialize(project, '우리팀', input_dir='자료넣는곳')
            config = self.h.read_json(project / 'project.json')
            self.assertTrue(config['require_visual_briefs'])
            self.assertEqual('1.5.0', config['harness_version'])
            self.assertTrue(config['require_visual_plan'])
            self.assertEqual('1.2', config['schema_version'])

    def test_schema_optional_brief_contract_is_explicit(self):
        schema = json.loads((SCRIPTS.parent / 'schemas/deck.schema.json').read_text(encoding='utf-8-sig'))
        item = schema['properties']['slides']['items']
        self.assertNotIn('visual_brief', item['required'])
        self.assertEqual('#/$defs/visualBrief', item['properties']['visual_brief']['$ref'])
        self.assertEqual(5, len(schema['$defs']['visualBrief']['required']))


if __name__ == '__main__':
    unittest.main()
