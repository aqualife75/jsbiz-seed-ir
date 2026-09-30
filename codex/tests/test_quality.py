"""Regression coverage for semantic completeness, disclosure, and deck views."""
import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'plugins/seed-ir/skills/seed-ir/scripts'


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class QualityTests(unittest.TestCase):
    def setUp(self):
        self.q = load('quality')
        self.h = load('harness')
        self.curriculum = self.q.load_curriculum()
        self.evidence = {'E1': {'kind': 'internal', 'status': 'confirmed'}}

    def claim(self, text='테스트용 확인된 정보'):
        return {'text': text, 'kind': 'fact', 'evidence_ids': ['E1']}

    def complete_briefs(self):
        briefs = self.q.initial_briefs(self.curriculum)
        for section in briefs['sections']:
            for question in section['questions']:
                question.update(status='answered', answer=self.claim(), argument=[self.claim()],
                                evidence_ids=['E1'], missing=[])
                for coverage in question['coverage']:
                    coverage['claim'] = self.claim()
        return briefs

    def check(self, briefs, final=False):
        return self.q.validate_briefs(briefs, self.curriculum, self.evidence, [],
                                      self.h.validate_claim, final=final)

    def test_evidence_id_alone_does_not_complete_required_questions(self):
        briefs = self.q.initial_briefs(self.curriculum)
        for section in briefs['sections']:
            for question in section['questions']:
                question.update(evidence_ids=['E1'], status='answered', missing=[])
        result = self.check(briefs, final=True)
        self.assertFalse(result['complete'])
        self.assertTrue(result['errors'])
        self.assertTrue(any('answer' in e or '답변' in e for e in result['errors']))

    def test_explicit_missing_data_is_an_honest_draft_but_blocks_final(self):
        briefs = self.q.initial_briefs(self.curriculum)
        draft = self.check(briefs)
        self.assertEqual([], draft['errors'])
        self.assertTrue(draft['warnings'])
        self.assertFalse(draft['complete'])
        self.assertTrue(self.check(briefs, final=True)['errors'])

    def test_answer_cannot_omit_required_data_coverage(self):
        briefs = self.complete_briefs()
        self.assertTrue(self.check(briefs, final=True)['complete'])
        team = next(x for x in briefs['sections'] if x['section'] == 'team')
        team['questions'][0]['coverage'] = []
        result = self.check(briefs, final=True)
        self.assertFalse(result['complete'])
        self.assertTrue(any('team.q1' in e and 'coverage' in e for e in result['errors']))

    def test_assumption_disguised_as_fact_fails_even_in_draft_brief(self):
        briefs = self.complete_briefs()
        self.evidence['E1']['status'] = 'unverified'
        self.assertTrue(self.check(briefs)['errors'])

    def test_unknown_question_and_visual_reference_cannot_pass(self):
        briefs = self.complete_briefs()
        question = briefs['sections'][0]['questions'][0]
        question['visual_refs'] = [{'slide_id': 'MISSING', 'block_id': 'B1'}]
        self.assertTrue(self.check(briefs)['errors'])
        question['visual_refs'] = []
        question['question_id'] = 'invented.q1'
        self.assertTrue(self.check(briefs)['errors'])

    def test_master_and_pitch_have_independent_order_without_slide_count_cap(self):
        slides = [{'id': f'S{i}', 'seconds': 10} for i in range(16)]
        deck = {'schema_version': '1.1', 'slides': slides,
                'views': {'master': {'slide_ids': [s['id'] for s in slides]},
                          'pitch': {'slide_ids': ['S3', 'S1'], 'target_seconds': 300}}}
        self.assertEqual(16, len(self.q.select_slides(deck, 'master')))
        self.assertEqual(['S3', 'S1'], [s['id'] for s in self.q.select_slides(deck, 'pitch')])
        deck['views']['pitch']['slide_ids'].append('unknown')
        with self.assertRaises(ValueError): self.q.select_slides(deck, 'pitch')

    def test_v1_deck_remains_readable_without_silent_completeness_upgrade(self):
        legacy = {'schema_version': '1.0', 'slides': [{'id': 'S1'}]}
        self.assertEqual(legacy['slides'], self.q.select_slides(legacy, 'master'))
        self.assertEqual(legacy['slides'], self.q.select_slides(legacy, 'pitch'))

    def v12_deck(self):
        slides=[]
        for topic in self.curriculum['topics']:
            for part in range(topic['min_slides']):
                slides.append({'id':f"{topic['id']}-{part}",'section':topic['id'],
                               'section_ids':[topic['id']],'governing_message':'계획: 원문으로 검증',
                               'speaker_notes':'계획의 확인 범위를 설명합니다.'})
        ids=[s['id'] for s in slides]
        return {'schema_version':'1.2','slides':slides,
                'views':{'master':{'slide_ids':ids.copy()},'pitch':{'slide_ids':ids.copy(),'target_seconds':300}}}

    def test_v12_requires_section_minima_in_each_view(self):
        deck=self.v12_deck()
        self.assertEqual([],self.q.validate_view_contract(deck,'master'))
        self.assertEqual([],self.q.validate_view_contract(deck,'pitch'))
        deck['views']['pitch']['slide_ids'].remove('product-1')
        self.assertEqual([],self.q.validate_view_contract(deck,'master'))
        self.assertTrue(any('product' in e and '2' in e for e in self.q.validate_view_contract(deck,'pitch')))

    def test_v12_enforces_order_and_rejects_composite_counting(self):
        deck=self.v12_deck();ids=deck['views']['master']['slide_ids'];ids[1],ids[2]=ids[2],ids[1]
        self.assertTrue(any('순서' in e for e in self.q.validate_view_contract(deck,'master')))
        deck=self.v12_deck();deck['slides'][2]['section_ids']=['problem','alternatives']
        self.assertTrue(any('독립' in e for e in self.q.validate_view_contract(deck,'pitch')))
        deck=self.v12_deck();next(s for s in deck['slides'] if s['id']=='problem-1')['appendix']=True
        self.assertTrue(any('problem' in e for e in self.q.validate_view_contract(deck,'pitch')))

    def test_v12_omits_funding_questions_and_blocks_fundraising_content(self):
        forbidden=('투자 요청','요청 금액','자금 조달','투자금','필요 자금')
        for topic in self.curriculum['topics']:
            content=' '.join(topic['required_data']+topic['investor_questions'])
            self.assertFalse(any(word in content for word in forbidden),topic['id'])
        deck=self.v12_deck();deck['slides'][-3]['speaker_notes']='투자 요청 3억원으로 실행합니다.'
        self.assertTrue(any('투자' in e for e in self.q.validate_view_contract(deck,'pitch')))
        deck['schema_version']='1.1'
        self.assertEqual([],self.q.validate_view_contract(deck,'pitch'))

    def test_legacy_curriculum_keeps_old_question_contract(self):
        legacy=self.q.load_curriculum('1.1')
        self.assertEqual(12,len(legacy['topics']))
        self.assertEqual(19,sum(len(t['question_contracts']) for t in legacy['topics']))
        self.assertIn('competition',[t['id'] for t in legacy['topics']])

    def test_v12_rejects_funding_aliases_in_nested_visible_content(self):
        for phrase in ('투자금 3억원','Seed 요청액 3억원','요청금액 3억원',
                       'Seed 요청 3억원','자금 사용 계획','자금 조달 계획','조달계획'):
            with self.subTest(phrase=phrase):
                deck=self.v12_deck()
                deck['slides'][-3]['blocks']=[{'type':'roadmap','items':[{'gate':'계획: '+phrase}]}]
                self.assertTrue(any('투자' in e for e in self.q.validate_view_contract(deck,'pitch')))

    def test_v12_allows_customer_prices_unit_costs_and_business_milestones(self):
        deck=self.v12_deck()
        deck['slides'][-3]['blocks']=[{'type':'roadmap','items':[
            {'title':'계획: 판매가격 월 10만원','gate':'계획: 단위원가 3만원과 구매전환율 검증'},
            {'title':'계획: 제품 검증','gate':'계획: 고객 10곳의 재구매 여부 확인'}]}]
        self.assertEqual([],self.q.validate_view_contract(deck,'pitch'))

    def test_v12_rejects_capital_use_without_plan_suffix(self):
        deck=self.v12_deck()
        deck['slides'][-3]['speaker_notes']='가정: 자금 사용: 개발 1억원, 운영 5천만원.'
        self.assertTrue(any('투자' in e for e in self.q.validate_view_contract(deck,'pitch')))
        deck=self.v12_deck()
        deck['slides'][-3]['blocks']=[{'type':'table','columns':['계획'],
                                     'rows':[['투자\n요청 3억원']]}]
        self.assertTrue(any('투자' in e for e in self.q.validate_view_contract(deck,'pitch')))

    def test_v12_brief_excludes_funding_in_question_and_all_claim_slots(self):
        for field in ('question','answer','argument','coverage'):
            with self.subTest(field=field):
                briefs=self.complete_briefs()
                question=next(s for s in briefs['sections'] if s['section']=='milestones')['questions'][0]
                if field=='question':question[field]='성장 단계에 필요한 투자금은 얼마인가'
                elif field=='answer':question[field]=self.claim('투자 요청 3억원입니다')
                elif field=='argument':question[field]=[self.claim('자금 사용: 개발 1억원')]
                else:question[field][0]['claim']=self.claim('투자금은 개발과 운영에 사용합니다')
                errors=self.check(briefs)['errors']
                self.assertTrue(any('milestones.q1' in e and '투자' in e for e in errors),errors)

    def test_v12_brief_still_allows_customer_prices_and_unit_costs(self):
        briefs=self.complete_briefs()
        question=next(s for s in briefs['sections'] if s['section']=='business_model')['questions'][0]
        question['answer']=self.claim('판매가격은 매장당 월 10만원입니다')
        question['argument']=[self.claim('단위원가 3만원과 구매전환율을 확인했습니다')]
        self.assertEqual([],self.check(briefs)['errors'])

    def test_nested_block_claim_cannot_escape_evidence_validation(self):
        block = {'id': 'B1', 'type': 'team', 'title': '팀의 실행 역량',
                 'kind': 'plan', 'evidence_ids': [], 'items': [
                     {'name': '대표', 'role': '개발', 'proof': '당사 유료고객 100명',
                      'contribution': '영업', 'kind': 'fact', 'evidence_ids': ['EXT']},
                     {'name': '팀원', 'role': '운영', 'proof': '계획: 역량 확인',
                      'contribution': '계획: 현장 실험'}]}
        evidence = {'EXT': {'kind': 'external', 'status': 'confirmed'}}
        result = self.q.validate_blocks({'id': 'S1', 'blocks': [block]}, evidence,
                                         self.h.validate_claim)
        self.assertTrue(any('internal' in e for e in result))

    def test_table_and_chart_shape_errors_are_actionable(self):
        table = {'id': 'B1', 'type': 'table', 'title': '가정: 비교표', 'kind': 'assumption',
                 'evidence_ids': [], 'columns': ['기준', '자사'], 'rows': [['시간']]}
        result = self.q.validate_blocks({'id': 'S1', 'blocks': [table]}, {}, self.h.validate_claim)
        self.assertTrue(any('열' in e or 'columns' in e for e in result))
        chart = dict(table, type='chart', chart_type='bar', categories=['A', 'B'],
                     series=[{'name': '가정: 매출', 'values': [1]}], unit='억원', source='가정')
        self.assertTrue(self.q.validate_blocks({'id': 'S1', 'blocks': [chart]}, {}, self.h.validate_claim))

    def test_semantic_layout_requires_its_actual_visual_content(self):
        text={'id':'B1','type':'text','title':'계획','kind':'plan','evidence_ids':[],'text':'계획: 원고 작성'}
        result=self.q.validate_blocks({'id':'S1','layout':'competition_matrix','blocks':[text]}, {}, self.h.validate_claim)
        self.assertTrue(any('table' in e for e in result))
        steps={'id':'B2','type':'steps','title':'계획','kind':'plan','evidence_ids':[],
               'items':[{'title':str(i),'text':'계획: 단계를 설명합니다'} for i in range(5)]}
        result=self.q.validate_blocks({'id':'S1','layout':'product_journey','blocks':[steps,text]}, {}, self.h.validate_claim)
        self.assertTrue(any('4' in e for e in result))

    def test_milestone_roadmap_accepts_business_gates_with_optional_support(self):
        roadmap={'id':'R','type':'roadmap','title':'계획: 사업 검증','kind':'plan','evidence_ids':[],
                 'items':[{'period':'1단계','title':'제품 검증','deliverables':['시제품'], 'gate':'사용성 확인'},
                          {'period':'2단계','title':'시장 검증','deliverables':['고객 실험'], 'gate':'반복 사용 확인'}]}
        text={'id':'T','type':'text','title':'계획','kind':'plan','evidence_ids':[],'text':'계획: 단계별 검증'}
        metric={'id':'M','type':'metric','title':'계획','kind':'plan','evidence_ids':[],'value':'10곳','detail':'계획: 초기 실험'}
        slide={'id':'S1','layout':'milestone_roadmap','blocks':[roadmap]}
        self.assertEqual([],self.q.validate_blocks(slide,{},self.h.validate_claim))
        slide['blocks']=[roadmap,text,metric]
        self.assertEqual([],self.q.validate_blocks(slide,{},self.h.validate_claim))
        slide['blocks'].append(dict(text,id='T2'))
        self.assertTrue(any('최대 2개' in e for e in self.q.validate_blocks(slide,{},self.h.validate_claim)))
        slide['blocks']=[roadmap,dict(roadmap,id='R2')]
        self.assertTrue(any('정확히 1개' in e for e in self.q.validate_blocks(slide,{},self.h.validate_claim)))


if __name__ == '__main__':
    unittest.main()
