"""Visual dispatch and real native package preservation, independent of sample content."""
import base64
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from xml.etree import ElementTree as ET
from zipfile import ZipFile

SCRIPTS = Path(__file__).resolve().parents[1] / 'plugins/seed-ir/skills/seed-ir/scripts'
spec = importlib.util.spec_from_file_location('visual_renderer_launcher', SCRIPTS / 'render_deck.py')
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


def brief(variant, primary, ids):
    return {'layout_variant': variant, 'primary_block_id': primary,
            'reading_order': ids, 'key_message': '교육용 가상 렌더 검증',
            'visual_reason': '주요 근거와 보조 설명을 크기와 위치로 구분합니다.'}


class VisualRendererTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.node, cls.module = launcher.artifact_runtime()
        except launcher.RenderError as exc:
            raise unittest.SkipTest(str(exc))

    def run_node(self, source):
        result = subprocess.run([str(self.node), '--input-type=module', '-e', source],
                                capture_output=True, text=True, encoding='utf8')
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_content_aware_dispatch_keeps_all_ids_and_primary_area(self):
        helper = (SCRIPTS / 'visual_composition.mjs').as_uri()
        result = self.run_node(f"""
            import {{planVisualComposition}} from {json.dumps(helper)};
            const blocks = [{{id:'hero',type:'image'}}, {{id:'scope',type:'text',text:'One supplied detail.'}}, {{id:'limit',type:'text',text:'Another complete detail.'}}];
            const slide = {{id:'P1',layout:'product_journey',visual_brief:{json.dumps(brief('product_hero', 'hero', ['scope', 'hero', 'limit']))}}};
            const plan = planVisualComposition(slide,blocks);
            console.log(JSON.stringify({{plan,legacy:planVisualComposition({{id:'L1'}},blocks)}}));
        """)
        plan = result['plan']
        self.assertIsNone(result['legacy'])
        self.assertEqual(plan['reading_order'], ['scope', 'hero', 'limit'])
        self.assertCountEqual([p['block_id'] for p in plan['placements']], ['hero', 'scope', 'limit'])
        primary = next(p for p in plan['placements'] if p['role'] == 'primary')
        self.assertTrue(all(primary['w'] * primary['h'] > p['w'] * p['h'] * 2
                            for p in plan['placements'] if p['role'] == 'support'))
        self.assertEqual(plan['layout_variant'], 'product_hero')

    def test_missing_asset_and_incomplete_reading_order_fail(self):
        helper = (SCRIPTS / 'visual_composition.mjs').as_uri()
        result = self.run_node(f"""
            import {{planVisualComposition}} from {json.dumps(helper)};
            const bad = [
              {{id:'A',visual_brief:{{layout_variant:'product_hero',primary_block_id:'a',reading_order:['a']}}}},
              {{id:'B',visual_brief:{{layout_variant:'evidence_focus',primary_block_id:'a',reading_order:['a','a']}}}}
            ];
            console.log(JSON.stringify(bad.map(s=>{{try{{planVisualComposition(s,[{{id:'a',type:'text',text:'Complete content'}}]);return null;}}catch(e){{return e.message;}}}})));
        """)
        self.assertIn('source image', result[0])
        self.assertIn('every block ID exactly once', result[1])

    def test_quantitative_axis_has_readable_intervals_and_label_headroom(self):
        helper = (SCRIPTS / 'visual_composition.mjs').as_uri()
        result = self.run_node(f"""
            import {{readableValueAxis}} from {json.dumps(helper)};
            console.log(JSON.stringify([readableValueAxis([20000,4000,2400,1680,1000]), readableValueAxis([1.2,1.608,1.788])]));
        """)
        self.assertEqual(result[0], {'min': 0, 'max': 25000, 'majorUnit': 5000, 'numberFormatCode': '#,##0'})
        self.assertEqual(result[1]['majorUnit'], .5)
        self.assertEqual(result[1]['numberFormatCode'], '#,##0.0')
        self.assertGreater(result[1]['max'], 1.788)

    def test_portrait_product_and_cover_preserve_height_without_empty_wide_frames(self):
        helper = (SCRIPTS / 'visual_composition.mjs').as_uri()
        result = self.run_node(f"""
            import {{planVisualComposition}} from {json.dumps(helper)};
            const blocks = [{{id:'text',type:'text',text:'Main value proposition'}},{{id:'image',type:'image'}},{{id:'disclosure',type:'text',text:'Educational assumption.'}}];
            const product = {{id:'P',visual_brief:{json.dumps(brief('product_hero', 'image', ['image', 'text', 'disclosure']))}}};
            const cover = {{id:'C',visual_brief:{json.dumps(brief('cover_focus', 'text', ['text', 'image', 'disclosure']))}}};
            console.log(JSON.stringify({{portrait:planVisualComposition(product,blocks,{{block_image_aspects:{{image:.6}}}}),landscape:planVisualComposition(product,blocks,{{block_image_aspects:{{image:1.7}}}}),cover:planVisualComposition(cover,blocks)}}));
        """)
        portrait = next(p for p in result['portrait']['placements'] if p['block_id'] == 'image')
        landscape = next(p for p in result['landscape']['placements'] if p['block_id'] == 'image')
        self.assertLess(portrait['w'], landscape['w'] * .7)
        self.assertEqual(portrait['h'], landscape['h'])
        cover = {p['block_id']: p for p in result['cover']['placements']}
        self.assertEqual(cover['text']['x'], cover['disclosure']['x'])
        self.assertGreater(cover['disclosure']['y'], cover['text']['y'])
        self.assertGreater(cover['image']['h'], cover['text']['h'])

    def test_product_market_comparison_and_legacy_export_complete_native_content(self):
        font = launcher.resolve_font({})
        profile = json.loads((SCRIPTS.parent / 'references/design-profile.json').read_text('utf8'))
        common = {'kind': 'assumption', 'evidence_ids': []}
        asset = {**common, 'id': 'hero', 'type': 'image', 'title': '가상 제품 화면',
                 'path': 'fixture.png', 'caption': '가상 화면 캡션 보존', 'source': '렌더 기능 테스트',
                 'rights': 'owned', 'alt': '기능 검증용 원본 비트맵'}
        note = {**common, 'id': 'note', 'type': 'text', 'title': '범위', 'text': '모든 설명을 보존합니다.'}
        table = {**common, 'id': 'comparison', 'type': 'table', 'title': '같은 조건의 비교',
                 'columns': ['기준', '기존', '계획'], 'rows': [['입력', '수동', '사진'], ['확인', '분리', '한 화면']]}
        formula = {**common, 'id': 'market', 'type': 'formula', 'title': '세 단계 계산',
                   'items': [{'label': label, 'formula': formula, 'result': result, 'basis': basis}
                             for label, formula, result, basis in [
                                 ('TAM 예시', '100 × 10', '1,000원', '전체 조건 가정'),
                                 ('SAM 예시', '50 × 10', '500원', '대상 조건 가정'),
                                 ('SOM 예시', '10 × 10', '100원', '목표 조건 가정')]]}
        chart = {**common, 'id': 'chart', 'type': 'chart', 'title': '가상 입력값', 'chart_type': 'bar',
                 'categories': ['A', 'B'], 'series': [{'name': '교육용 가정', 'values': [30, 10]}],
                 'unit': '분', 'source': '교육용 가상 데이터'}
        slides = []
        for sid, variant, main, support in [('P', 'product_hero', asset, note),
                                            ('M', 'market_layers', formula, note),
                                            ('C', 'comparison_focus', table, note),
                                            ('E', 'evidence_focus', chart, note)]:
            slides.append({'id': sid, 'layout': 'evidence_board', 'section': 'product',
                           'governing_message': '교육용 가상 자료의 모든 내용을 보존합니다',
                           'governing_kind': 'assumption', 'speaker_notes': '사용자 발표 노트 보존',
                           'blocks': [main, support], 'visual_brief': brief(variant, main['id'], [main['id'], 'note'])})
        slides.append({'id': 'L', 'layout': 'evidence', 'section': 'problem',
                       'governing_message': '레거시 본문을 보존합니다', 'governing_kind': 'assumption',
                       'body': [{**common, 'text': '레거시 고유 문장 보존'}], 'speaker_notes': '이전 원고 보존'})
        with tempfile.TemporaryDirectory(prefix='seed-ir-visual-fixture-') as tmp:
            root = Path(tmp)
            (root / 'fixture.png').write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jD1cAAAAASUVORK5CYII='))
            request = {'deck': {'view': 'master', 'slides': slides}, 'profile': profile,
                       'font': font, 'sources': {}, 'project': str(root), 'section_labels': {},
                       'chart_snapshot_helper': str(SCRIPTS / 'materialize_chart_workbooks.py')}
            input_path = root / 'input.json'
            input_path.write_text(json.dumps(request, ensure_ascii=False), 'utf8')
            result = subprocess.run([str(self.node), str(SCRIPTS / 'render_rich.mjs'), str(input_path),
                                     str(root / 'output'), str(self.module), sys.executable],
                                    capture_output=True, text=True, encoding='utf8')
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads((root / 'output/rich-render-report.json').read_text('utf8'))
            self.assertEqual([p['layout_variant'] for p in report['compositions']],
                             ['product_hero', 'market_layers', 'comparison_focus', 'evidence_focus', 'legacy'])
            self.assertTrue(report['font_registration']['registered'])
            self.assertEqual(report['native_table_owner_slides'], [3])
            self.assertEqual(report['native_chart_owner_slides'], [4])
            self.assertEqual(len(report['coverage']), 9)
            with ZipFile(root / 'output/seed-ir-draft.pptx') as package:
                names = package.namelist()
                texts = '\n'.join(''.join(ET.fromstring(package.read(name)).itertext())
                                  for name in names if name.startswith('ppt/slides/slide') and name.endswith('.xml'))
                for expected in ['가상 화면 캡션 보존', '모든 설명을 보존합니다.', '전체 조건 가정',
                                 '대상 조건 가정', '목표 조건 가정', '기존', '수동', '레거시 고유 문장 보존']:
                    self.assertIn(expected, texts)
                chart_parts = [name for name in names if '/charts/' in name and name.endswith('.xml') and '/_rels/' not in name]
                self.assertEqual(len(chart_parts), 1)
                chart_xml = ET.fromstring(package.read(chart_parts[0]))
                self.assertTrue(chart_xml.tag.endswith('}chartSpace'))
                ns = {'c': 'http://schemas.openxmlformats.org/drawingml/2006/chart'}
                self.assertEqual([node.text for node in chart_xml.findall('.//c:val/c:numRef/c:numCache/c:pt/c:v', ns)], ['30', '10'])
                self.assertEqual(chart_xml.find('.//c:catAx/c:scaling/c:orientation', ns).get('val'), 'maxMin')
                self.assertEqual(chart_xml.find('.//c:valAx/c:majorUnit', ns).get('val'), '10')
                self.assertEqual(chart_xml.find('.//c:valAx/c:crosses', ns).get('val'), 'max')
                self.assertEqual(chart_xml.find('.//c:valAx/c:tickLblPos', ns).get('val'), 'low')
                self.assertTrue(any(name.endswith('.xlsx') for name in names))
                notes = ''.join(package.read(name).decode('utf8') for name in names if name.startswith('ppt/notesSlides/notesSlide') and name.endswith('.xml'))
                self.assertIn('사용자 발표 노트 보존', notes)
            self.assertEqual(len(list((root / 'output/renders').glob('*.png'))), 5)


if __name__ == '__main__':
    unittest.main()
