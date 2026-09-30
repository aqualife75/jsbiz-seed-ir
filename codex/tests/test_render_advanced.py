"""The rich contract must keep evidence, view order and native visual objects."""
import importlib.util
import base64
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile
from xml.etree import ElementTree as ET

SCRIPT = Path(__file__).resolve().parents[1] / 'plugins/seed-ir/skills/seed-ir/scripts/render_deck.py'
spec = importlib.util.spec_from_file_location('render_advanced_tests', SCRIPT)
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)


class AdvancedContractTests(unittest.TestCase):
    def test_v12_section_labels_match_the_fourteen_part_curriculum(self):
        expected = {
            'cover': '표지', 'background': '문제 배경 및 최근 트렌드', 'problem': '문제 정의',
            'alternatives': '기존 대체재의 문제점', 'solution': '해결방안', 'product': '제품 및 서비스 소개',
            'traction': '초기 고객 반응', 'business_model': '수익 모델', 'market': '시장 규모',
            'go_to_market': '초기 시장 진입 전략', 'growth': '성장 전략', 'milestones': '마일스톤',
            'team': '팀 구성', 'vision': '비전',
        }
        for section, label in expected.items():
            self.assertEqual(render.SECTION_LABELS.get(section), label)

    def test_v12_milestone_roadmap_without_funding_renders_all_content(self):
        try:
            render.artifact_runtime()
            render.resolve_font({})
        except render.RenderError as error:
            self.skipTest(str(error))
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            for folder in ['deck', 'evidence', 'design']:
                (project / folder).mkdir()
            main = {'id': 'roadmap', 'type': 'roadmap', 'title': '검증 관문', 'kind': 'plan',
                    'evidence_ids': [], 'items': [
                        {'period': f'{index}분기', 'title': title, 'deliverables': [f'산출물 {index}', '결과 기록'],
                         'gate': f'진입 조건 {index}'}
                        for index, title in enumerate(['문제 검증', '제품 실험', '초기 도입', '반복 사용'], start=1)]}
            base = {'layout': 'milestone_roadmap', 'section': 'milestones',
                    'governing_message': '계획: 검증 관문을 통과하며 다음 단계로 진행합니다',
                    'governing_kind': 'plan', 'seconds': 15, 'speaker_notes': '가상의 검증 계획입니다.'}
            slides = [{**base, 'id': 'M1', 'blocks': [main]},
                      {**base, 'id': 'M2', 'blocks': [main, {'id': 'duration', 'type': 'metric',
                       'title': '기간', 'value': '12개월', 'detail': '교육용 계획 기간', 'kind': 'plan',
                       'evidence_ids': []}, {'id': 'scope', 'type': 'text',
                       'title': '계획의 기준', 'text': '실험 결과에 따라 일정과 다음 단계를 조정합니다.',
                       'kind': 'plan', 'evidence_ids': []}]}]
            deck = {'schema_version': '1.2', 'team_name': '가상 테스트', 'slides': slides,
                    'views': {'master': {'slide_ids': ['M1', 'M2']}, 'pitch': {'slide_ids': ['M2']}}}
            profile = json.loads((SCRIPT.parent.parent / 'references/design-profile.json').read_text('utf8'))
            for rel, value in [('deck/deck.json', deck), ('evidence/evidence.json', {'items': []}),
                               ('design/design-profile.json', profile)]:
                (project / rel).write_text(json.dumps(value, ensure_ascii=False), 'utf8')
            report = render.render_project(project, 'master')
            self.assertEqual(report['slide_count'], 2)
            prs = render.Presentation(project / 'output/master/seed-ir-draft.pptx')
            for number, slide in enumerate(prs.slides, start=1):
                visible = '\n'.join(shape.text for shape in slide.shapes if shape.has_text_frame)
                self.assertIn('마일스톤', visible)
                self.assertNotIn('투자 요청', visible)
                for index in range(1, 5):
                    self.assertIn(f'산출물 {index}', visible)
                    self.assertIn(f'진입 조건 {index}', visible)
                self.assertTrue((project / f'output/master/renders/slide-{number:02d}.png').is_file())
            self.assertIn('실험 결과에 따라', '\n'.join(shape.text for shape in prs.slides[1].shapes if shape.has_text_frame))

    def test_view_order_and_independent_master_content(self):
        deck = {'schema_version': '1.1', 'team_name': 'T', 'slides': [{'id': 'M1'}, {'id': 'M2'}, {'id': 'P1'}],
                'views': {'master': {'slide_ids': ['M1', 'M2']}, 'pitch': {'slide_ids': ['P1', 'M1']}}}
        self.assertEqual([s['id'] for s in render.select_view(deck, 'pitch')['slides']], ['P1', 'M1'])
        self.assertEqual(len(deck['slides']), 3)
        with self.assertRaisesRegex(render.RenderError, 'view'):
            render.select_view(deck, 'absent')

    def test_nested_evidence_is_included_in_citations(self):
        s = {'blocks': [{'type': 'steps', 'evidence_ids': ['E1'], 'items': [
            {'title': '한 단계', 'text': '개별 근거', 'evidence_ids': ['E2']}]}]}
        self.assertEqual(render.evidence_refs(s), ['E1', 'E2'])

    def test_nested_image_cannot_escape_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(render.RenderError):
                render.validate_rich_assets(Path(tmp), {'blocks': [{'items': [{'asset': {
                    'path': '../outside.png', 'caption': '제품', 'rights': 'owned', 'source': '팀', 'alt': '제품'}}]}]})

    def test_unresolved_or_duplicate_view_members_are_rejected(self):
        for ids in [['missing'], ['M1', 'M1']]:
            deck = {'slides': [{'id': 'M1'}], 'views': {'pitch': {'slide_ids': ids}}}
            with self.subTest(ids=ids), self.assertRaises(render.RenderError):
                render.select_view(deck, 'pitch')

    def test_native_crop_retains_original_media_and_target_ratio(self):
        spec = importlib.util.spec_from_file_location('crop_tests', SCRIPT.with_name('fix_native_image_crops.py'))
        crop = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(crop)
        png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jD1cAAAAASUVORK5CYII=')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); image = root/'fixture.png'; image.write_bytes(png)
            pptx = root/'fixture.pptx'; manifest = root/'crops.json'
            xml = '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><p:cSld><p:spTree><p:pic><p:blipFill><a:blip/><a:stretch/></p:blipFill><p:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="1" cy="1"/></a:xfrm></p:spPr></p:pic></p:spTree></p:cSld></p:sld>'
            with ZipFile(pptx, 'w') as z:
                z.writestr('ppt/slides/slide1.xml', xml)
                z.writestr('ppt/media/image1.png', png)
            manifest.write_text(json.dumps([{'slide':1,'image_index':0,'source':str(image),
                'crop':{'left':0.25,'top':0,'right':0.25,'bottom':0},'frame':[10,20,200,100]}]),'utf8')
            crop.repair(pptx,manifest)
            with ZipFile(pptx) as z:
                self.assertEqual(z.read('ppt/media/image1.png'),png)
                slide = ET.fromstring(z.read('ppt/slides/slide1.xml'))
                self.assertEqual(slide.find('.//a:srcRect',crop.NS).attrib,{'l':'25000','t':'0','r':'25000','b':'0'})
                ext = slide.find('.//a:xfrm/a:ext',crop.NS).attrib
                self.assertAlmostEqual(int(ext['cx'])/int(ext['cy']),0.5)

    def test_rich_chart_and_table_keep_native_values_after_export(self):
        try:
            node, module = render.artifact_runtime()
            font = render.resolve_font({})
        except render.RenderError as error:
            self.skipTest(str(error))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for folder in ('deck','evidence','design'): (root/folder).mkdir()
            common={'kind':'fact','evidence_ids':['E1']}
            blocks=[{**common,'id':'chart','type':'chart','title':'기능 검증용 가상 수치','chart_type':'bar','categories':['기존','실험'],'series':[{'name':'소요 시간','values':[30,10]}],'unit':'분','source':'가상 테스트'},
                    {**common,'id':'table','type':'table','title':'가상 측정 조건','columns':['항목','조건'],'rows':[['기간','1주'],['횟수','10회']]},
                    {**common,'id':'note','type':'text','title':'가상 테스트','text':'실제 사업 성과가 아닌 렌더링 기능 검증용 입력입니다.'}]
            s={'id':'S1','layout':'evidence_board','section':'traction','governing_message':'기능 검증용 가상 자료','governing_kind':'fact','governing_evidence_ids':['E1'],'seconds':30,'speaker_notes':'기능 검증용 가상 자료입니다.','blocks':blocks}
            deck={'schema_version':'1.1','team_name':'가상 테스트','slides':[s],'views':{'master':{'slide_ids':['S1']},'pitch':{'slide_ids':['S1']}}}
            evidence={'items':[{'id':'E1','claim':'기능 검증용 가상 자료','kind':'internal','status':'confirmed','source_id':'fixture','locator':'1쪽'}]}
            profile=json.loads((SCRIPT.parent.parent/'references/design-profile.json').read_text('utf8'))
            for rel,data in [('deck/deck.json',deck),('evidence/evidence.json',evidence),('design/design-profile.json',profile)]:
                (root/rel).write_text(json.dumps(data,ensure_ascii=False),'utf8')
            empty_home=root/'empty-home'; empty_home.mkdir()
            # Explicit supported runtime + no personal Codex skills/cache at HOME.
            with patch.object(render.Path,'home',return_value=empty_home), patch.dict(os.environ,
                    {'HOME':str(empty_home),'USERPROFILE':str(empty_home),'SEED_IR_NODE':str(node),
                     'SEED_IR_NODE_MODULES':str(module.parents[3])}):
                report=render.render_project(root,'master')
            self.assertEqual((report['editable_chart_count'],report['editable_table_count']),(1,1))
            self.assertEqual(report['pptx_render_review'],'not_performed')
            pptx=render.Presentation(str(root/'output/master/seed-ir-draft.pptx'))
            chart=next(x.chart for x in pptx.slides[0].shapes if x.has_chart)
            table=next(x.table for x in pptx.slides[0].shapes if x.has_table)
            self.assertEqual(list(chart.series[0].values),[30,10])
            self.assertEqual(table.cell(2,1).text,'10회')
            self.assertTrue((root/'output/master/renders/slide-01.png').is_file())
            with ZipFile(root/'output/master/seed-ir-draft.pptx') as package:
                self.assertTrue(any(name.endswith('.xlsx') for name in package.namelist()))
            self.assertTrue((root/'work/render/master-chart-data-snapshot.json').is_file())

            # A migrated v1.1 slide pool can still contain only legacy slides.
            s.pop('blocks')
            s['body']=[{'text':'이 문장의 고유 근거가 노트에 유지됩니다.','kind':'fact','evidence_ids':['E2']}]
            s['layout']='evidence'; s['visual']={'type':'none'}
            evidence['items'].append({'id':'E2','claim':'본문의 고유 근거','kind':'internal','status':'confirmed','source_id':'body-fixture','locator':'2쪽'})
            (root/'deck/deck.json').write_text(json.dumps(deck,ensure_ascii=False),'utf8')
            (root/'evidence/evidence.json').write_text(json.dumps(evidence,ensure_ascii=False),'utf8')
            migrated=render.render_project(root,'pitch')
            self.assertEqual(migrated['view'],'pitch')
            self.assertTrue((root/'output/pitch/seed-ir-draft.pptx').is_file())
            self.assertTrue((root/'output/master/seed-ir-draft.pptx').is_file())
            self.assertEqual((root/'output/pitch/seed-ir-draft.pptx').read_bytes(),(root/'output/seed-ir-draft.pptx').read_bytes())
            legacy=render.Presentation(str(root/'output/pitch/seed-ir-draft.pptx'))
            self.assertIn('E2',legacy.slides[0].notes_slide.notes_text_frame.text)


if __name__ == '__main__':
    unittest.main()
