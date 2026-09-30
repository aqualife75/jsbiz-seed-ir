import copy
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'plugins/seed-ir/skills/seed-ir/scripts'

def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + '.py'))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod

class VisualPlanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.v = load('visual_plan')
        self.deck = {'team_name': '수리온', 'slides': [{'id': 'REPAIR', 'blocks': [
            {'id': 'FLOW', 'type': 'steps', 'items': [{'title': '점검', 'text': '계획: 수리 접수'}]}]}],
            'views': {'master': {'slide_ids': ['REPAIR']}, 'pitch': {'slide_ids': ['REPAIR']}}}
        self.plan = {'schema_version': '1.0', 'slides': [{'slide_id': 'REPAIR',
            'evidence_ids': ['A7'], 'block_ids': ['FLOW'], 'visual_type': 'diagram',
            'source_strategy': 'native', 'asset_refs': [], 'disclosure': '계획',
            'claim_boundary': '접수 절차 설계이며 실제 고객 실적이 아니다',
            'status': 'ready', 'search_note': '접수 흐름 자체를 도식으로 설명한다; 외부 사진 불필요'}]}
    def check(self, plan=None, final=True):
        return self.v.validate(self.plan if plan is None else plan, self.deck, {'A7': {}}, self.root, required=True, final=final)
    def test_other_company_native_flow_and_old_project_compatibility(self):
        self.assertEqual([], self.check()['errors'])
        self.assertEqual([], self.v.validate(None, self.deck, {}, self.root, required=False, final=True)['errors'])
        self.assertTrue(self.v.validate(None, self.deck, {}, self.root, required=True, final=True)['errors'])
    def test_missing_slide_plan_unknown_evidence_and_wrong_display_block_fail(self):
        for field, value in [('evidence_ids', ['NO']), ('block_ids', ['NO']), ('visual_type', 'chart')]:
            plan = copy.deepcopy(self.plan); plan['slides'][0][field] = value
            self.assertTrue(self.check(plan)['errors'], field)
        self.assertTrue(self.check({'schema_version': '1.0', 'slides': []})['errors'])
    def test_unfinished_image_stays_a_draft(self):
        self.plan['slides'][0].update(status='missing', source_strategy='official')
        self.assertTrue(self.check()['errors'])
        self.assertTrue(self.check(final=False)['warnings'])
    def image_plan(self):
        path = self.root / 'mockup.png'; path.write_bytes(b'fixture image bytes')
        asset = {'path': 'mockup.png', 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'source': 'AI generated concept', 'rights': 'owned', 'origin': 'generated',
            'caption': 'AI 생성 제품 설계안 · 구현 미확인', 'claim_boundary': '실제 제품 구현을 입증하지 않는다'}
        self.deck['slides'][0]['blocks'] = [{'id': 'SCREEN', 'type': 'image', **asset}]
        self.plan['slides'][0].update(block_ids=['SCREEN'], visual_type='product_ui',
            source_strategy='generated', asset_refs=[asset], disclosure=asset['caption'])
        return asset
    def test_generated_asset_must_exist_match_bytes_rights_and_actual_caption(self):
        self.image_plan(); self.assertFalse(self.check()['errors'])
        (self.root / 'mockup.png').write_bytes(b'changed image')
        self.assertTrue(any('SHA256' in e for e in self.check()['errors']))
        self.image_plan(); self.deck['slides'][0]['blocks'][0]['caption'] = '우리 제품'
        self.assertTrue(any('실제 장표' in e for e in self.check()['errors']))
        self.image_plan(); self.plan['slides'][0]['asset_refs'][0]['rights'] = 'unknown'
        self.assertTrue(any('사용권' in e for e in self.check()['errors']))
    def test_orphan_asset_and_outside_path_rejected(self):
        self.image_plan(); self.plan['slides'][0]['asset_refs'][0]['path'] = '../private.png'
        self.assertTrue(any('내부' in e for e in self.check()['errors']))
        self.image_plan(); self.deck['slides'][0]['blocks'] = [{'id': 'SCREEN', 'type': 'text'}]
        self.assertTrue(any('연결되지' in e for e in self.check()['errors']))
    def test_supporting_asset_edits_invalidate_existing_fingerprints(self):
        h = load('harness'); h.initialize(self.root, '수리온')
        (self.root / 'icon.png').write_bytes(b'first')
        self.deck['slides'][0]['visual_brief'] = {'supporting_assets': [{'path': 'icon.png'}]}
        h.write_json(self.root / 'deck/deck.json', self.deck)
        before = h.fingerprint(self.root, 'story')
        (self.root / 'icon.png').write_bytes(b'changed')
        self.assertNotEqual(before, h.fingerprint(self.root, 'story'))

if __name__ == '__main__': unittest.main()
