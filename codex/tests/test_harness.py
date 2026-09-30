import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
import base64
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'plugins/seed-ir/skills/seed-ir/scripts/harness.py'


class HarnessTests(unittest.TestCase):
    def load(self):
        self.assertTrue(SCRIPT.exists(), 'harness runtime is not implemented')
        spec = importlib.util.spec_from_file_location('harness', SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def seed_draft(self, h, p):
        h.initialize(p, '검증용 초안')
        (p/'input/base.txt').write_text('테스트 자료', encoding='utf-8')
        h.write_json(p/'data/raw/inventory.json', {'files':[{'source_id':'SRC','status':'ok',
            'source_file':'base.txt','sha256':h.sha(p/'input/base.txt')}]})
        h.write_json(p/'data/raw/documents.json', {'segments':[{'source_id':'SRC','locator':'line1','text':'테스트 자료'}]})
        h.write_json(p/'data/raw/assets.json', {'assets':[]})
        h.write_json(p/'evidence/evidence.json', {'items':[{'id':'E1','claim':'테스트 자료',
            'kind':'internal','status':'confirmed','source_id':'SRC','locator':'line1'}]})
        deck=h.read_json(p/'deck/deck.json')
        for slide in deck['slides']:
            slide.update(governing_message='계획: 추가 검증', governing_kind='plan',
                         speaker_notes='계획의 한계를 설명합니다.')
        h.write_json(p/'deck/deck.json', deck)
        return deck

    def test_v11_draft_briefs_are_disclosed_but_final_requires_completion(self):
        h=self.load()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); self.seed_draft(h,p)
            draft=h.check(p,'story')
            self.assertTrue(draft['passed'], draft['errors'])
            self.assertTrue(draft['warnings'])
            self.assertFalse(draft['semantic_complete'])
            final=h.check(p,'final')
            self.assertTrue(any('answer' in e or 'coverage' in e for e in final['errors']))

    def test_master_can_expand_in_section_and_pitch_uses_its_own_time(self):
        h=self.load()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); deck=self.seed_draft(h,p)
            for i in range(4):
                slide=dict(deck['slides'][1], id=f'M{i}', seconds=200)
                deck['slides'].append(slide)
                deck['views']['master']['slide_ids'].insert(2+i,slide['id'])
            h.write_json(p/'deck/deck.json',deck)
            self.assertTrue(h.check(p,'story')['passed'])
            deck['views']['pitch']['slide_ids'].insert(2,'M0')
            h.write_json(p/'deck/deck.json',deck)
            self.assertTrue(any('발표시간 초과' in e for e in h.check(p,'story')['errors']))

    def test_blocks_without_legacy_body_still_validate_nested_facts(self):
        h=self.load()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); deck=self.seed_draft(h,p)
            slide=deck['slides'][0]; slide.pop('body')
            slide['blocks']=[{'id':'B1','type':'text','title':'계획의 근거','kind':'fact',
                'evidence_ids':['MISSING'],'text':'확인되지 않은 성과'}]
            h.write_json(p/'deck/deck.json',deck)
            self.assertTrue(any('MISSING' in e for e in h.check(p,'story')['errors']))

    def legacy_project(self, h, p, version):
        deck=self.seed_draft(h,p)
        curriculum=h.quality.load_curriculum(version)
        slides=[]
        for index,topic in enumerate(curriculum['topics']):
            slide=dict(deck['slides'][0],id=f'L{index:02}',section=topic['id'],
                       section_ids=[topic['id']],seconds=20)
            if topic['id']=='milestones':slide['governing_message']='계획: 투자 요청 금액과 사용 계획'
            slides.append(slide)
        deck.update(schema_version=version,slides=slides)
        if version=='1.0':deck.pop('views')
        else:deck['views']={v:{'slide_ids':[s['id'] for s in slides]} for v in ('master','pitch')}
        h.write_json(p/'deck/deck.json',deck)
        h.write_json(p/'deck/section-briefs.json',h.quality.initial_briefs(curriculum))
        h.write_json(p/'evidence/section-map.json',{'schema_version':version,'sections':[
            {'section':t['id'],'evidence_ids':[],'asset_ids':[],'missing_data':['검증 필요']} for t in curriculum['topics']]})
        config=h.read_json(p/'project.json');config['schema_version']=version
        h.write_json(p/'project.json',config)
        return deck

    def test_legacy_migration_preserves_originals_and_creates_unresolved_v12(self):
        h=self.load()
        for version in ('1.0','1.1'):
            with self.subTest(version=version),tempfile.TemporaryDirectory() as d:
                p=Path(d);self.legacy_project(h,p,version)
                originals={rel:(p/rel).read_bytes() for rel in ('deck/deck.json','deck/section-briefs.json',
                    'evidence/section-map.json','project.json','input/base.txt','evidence/evidence.json')}
                result=h.migrate(p)
                self.assertTrue(result['migrated'])
                for rel,backup in result['backups'].items():self.assertEqual(originals[rel],(p/backup).read_bytes())
                for rel in ('input/base.txt','evidence/evidence.json'):self.assertEqual(originals[rel],(p/rel).read_bytes())
                migrated=h.read_json(p/'deck/deck.json')
                self.assertEqual('1.2',migrated['schema_version'])
                self.assertEqual(18,len(migrated['slides']))
                self.assertEqual(300,sum(s['seconds'] for s in migrated['slides']))
                self.assertTrue(all(not s['governing_message'] for s in migrated['slides']))
                briefs=h.read_json(p/'deck/section-briefs.json')
                self.assertEqual(14,len(briefs['sections']))
                self.assertTrue(all(q['status']=='missing' for s in briefs['sections'] for q in s['questions']))
                current=(p/'deck/deck.json').read_bytes()
                self.assertFalse(h.migrate(p)['migrated'])
                self.assertEqual(current,(p/'deck/deck.json').read_bytes())

    def test_migration_backup_collision_does_not_mutate_canonical_files(self):
        h=self.load()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);self.legacy_project(h,p,'1.1')
            original=(p/'deck/deck.json').read_bytes();config=(p/'project.json').read_bytes()
            (p/'deck/deck.pre-v1.2.v1.1.json').write_text('existing backup',encoding='utf-8')
            with self.assertRaises(FileExistsError):h.migrate(p)
            self.assertEqual(original,(p/'deck/deck.json').read_bytes())
            self.assertEqual(config,(p/'project.json').read_bytes())

    def test_v11_draft_is_readable_under_legacy_section_contract(self):
        h=self.load()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);self.legacy_project(h,p,'1.1')
            report=h.check(p,'story')
            self.assertTrue(report['passed'],report['errors'])
            self.assertTrue(any('v1.2' in w for w in report['warnings']))

    def test_v12_story_enforces_both_view_minimums_and_forbids_funding_subject(self):
        h=self.load()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);deck=self.seed_draft(h,p)
            self.assertTrue(h.check(p,'story')['passed'])
            ids=deck['views']['pitch']['slide_ids'];removed=ids.pop(3)
            h.write_json(p/'deck/deck.json',deck)
            self.assertTrue(any('problem' in e and '최소' in e for e in h.check(p,'story')['errors']))
            ids.insert(3,removed)
            deck['slides'][-3]['governing_message']='계획: 투자 요청 금액 1억원'
            h.write_json(p/'deck/deck.json',deck)
            self.assertTrue(any('투자' in e for e in h.check(p,'story')['errors']))

    def test_v12_pitch_compression_requires_every_source_to_share_section(self):
        h=self.load()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);deck=self.seed_draft(h,p)
            problems=[s for s in deck['slides'] if s['section']=='problem']
            alternative=next(s for s in deck['slides'] if s['section']=='alternatives')
            compressed=dict(problems[0],id='P03',source_slide_ids=[s['id'] for s in problems])
            deck['slides'].append(compressed)
            ids=deck['views']['pitch']['slide_ids'];ids[ids.index(problems[0]['id'])]='P03'
            h.write_json(p/'deck/deck.json',deck)
            self.assertTrue(h.check(p,'story')['passed'])
            compressed['source_slide_ids'].append(alternative['id'])
            h.write_json(p/'deck/deck.json',deck)
            errors=h.check(p,'story')['errors']
            self.assertTrue(any('P03' in e and '목차' in e for e in errors),errors)

    def test_nested_block_asset_keeps_project_path_boundary(self):
        h=self.load()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); deck=self.seed_draft(h,p)
            deck['slides'][0]['blocks']=[{'id':'B1','type':'steps','title':'계획: 제품 흐름',
                'kind':'plan','evidence_ids':[],'items':[
                    {'title':'1','text':'계획: 입력','asset':{'path':'../private.png','caption':'계획: 화면',
                        'source':'팀 자료','rights':'owned','alt':'입력'}},
                    {'title':'2','text':'계획: 분석'}]}]
            h.write_json(p/'deck/deck.json',deck)
            self.assertTrue(any('프로젝트 밖' in e for e in h.check(p,'story')['errors']))

    def test_compressed_pitch_cannot_cite_unrelated_master_section(self):
        h=self.load()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); deck=self.seed_draft(h,p)
            compressed=dict(deck['slides'][6],id='P-MARKET',source_slide_ids=['S01'])
            deck['slides'].append(compressed)
            deck['views']['pitch']['slide_ids'][6]='P-MARKET'
            h.write_json(p/'deck/deck.json',deck)
            self.assertTrue(any('목차 연결' in e for e in h.check(p,'story')['errors']))

    def test_init_preserves_existing_project(self):
        h = self.load()
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            h.initialize(p, '테스트팀')
            original = (p / 'project.json').read_bytes()
            with self.assertRaises(FileExistsError):
                h.initialize(p, '다른 팀')
            self.assertEqual(original, (p / 'project.json').read_bytes())

    def test_empty_project_cannot_pass_final(self):
        h = self.load()
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            h.initialize(p, '테스트팀')
            report = h.check(p, 'final')
            self.assertFalse(report['passed'])
            self.assertGreater(len(report['errors']), 0)

    def test_claim_cannot_reference_unverified_or_external_internal_metric(self):
        h = self.load()
        evidence = {'E1': {'id':'E1','kind':'external','status':'confirmed'}}
        errors = h.validate_claim({'text':'당사 유료고객 30명','kind':'fact','evidence_ids':['E1'],'scope':'company'}, evidence, 'slide 1')
        self.assertTrue(any('internal' in e for e in errors))
        evidence['E1']['status'] = 'unverified'
        self.assertTrue(h.validate_claim({'text':'시장 20%','kind':'fact','evidence_ids':['E1']}, evidence, 'slide 1'))

    def test_assumption_must_be_labeled(self):
        h = self.load()
        self.assertTrue(h.validate_claim({'text':'연매출 5억','kind':'assumption','evidence_ids':[]}, {}, 'slide 1'))
        self.assertFalse(h.validate_claim({'text':'[가정] 연매출 5억','kind':'assumption','evidence_ids':[]}, {}, 'slide 1'))

    def test_changed_artifact_invalidates_checkpoint(self):
        h = self.load()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); h.initialize(p, '테스트팀')
            (p/'input/base.txt').write_text('test',encoding='utf-8')
            h.write_json(p/'data/raw/inventory.json', {'files':[{'source_id':'S1','status':'ok','source_file':'base.txt','sha256':h.sha(p/'input/base.txt')}]})
            h.write_json(p/'data/raw/documents.json', {'segments':[{'source_id':'S1','locator':'p1','text':'test'}]})
            h.write_json(p/'data/raw/assets.json', {'assets':[]})
            h.record(p, 'intake')
            self.assertEqual(h.status(p)['stages']['intake'], 'passed')
            (p/'input/new.txt').write_text('changed', encoding='utf-8')
            self.assertEqual(h.status(p)['stages']['intake'], 'stale')
            self.assertFalse(h.check(p,'intake')['passed'])
            with self.assertRaises(ValueError): h.record(p,'intake')

    def test_corrupt_json_is_actionable_failure(self):
        h=self.load()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); h.initialize(p,'test')
            (p/'evidence/evidence.json').write_text('{',encoding='utf-8')
            r=h.check(p,'evidence')
            self.assertFalse(r['passed'])
            self.assertTrue(any('JSON' in e for e in r['errors']))

    def test_referenced_images_outside_standard_folders_invalidate_story(self):
        h=self.load()
        for placement in ('legacy','image_block','nested_step_asset'):
            with self.subTest(placement=placement), tempfile.TemporaryDirectory() as d:
                p=Path(d); deck=self.seed_draft(h,p)
                (p/'assets').mkdir(); image=p/'assets/product.png'; image.write_bytes(b'first image')
                asset={'path':'assets/product.png','caption':'계획: 제품 화면',
                       'source':'synthetic fixture','rights':'owned','alt':'제품 화면'}
                if placement=='legacy': deck['slides'][0]['assets']=[asset]
                elif placement=='image_block':
                    deck['slides'][0]['blocks']=[dict(asset,id='B1',type='image',title='제품',kind='plan',evidence_ids=[])]
                else:
                    deck['slides'][0]['blocks']=[{'id':'B1','type':'steps','title':'제품 흐름','kind':'plan','evidence_ids':[],
                        'items':[{'title':'입력','text':'계획: 사진 입력','asset':asset},
                                 {'title':'결과','text':'계획: 결과 확인'}]}]
                h.write_json(p/'deck/deck.json',deck)
                for stage in ('intake','evidence','story'):h.record(p,stage)
                self.assertEqual('passed',h.status(p)['stages']['story'])
                image.write_bytes(b'changed image')
                self.assertEqual('stale',h.status(p)['stages']['story'])

    def test_image_fingerprint_rejects_project_escape(self):
        h=self.load()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'project';deck=self.seed_draft(h,p)
            (p.parent/'private.png').write_bytes(b'private image')
            deck['slides'][0]['assets']=[{'path':'../private.png','caption':'test','source':'test','rights':'owned','alt':'test'}]
            h.write_json(p/'deck/deck.json',deck)
            with self.assertRaisesRegex(ValueError,'프로젝트 밖'):h.fingerprint(p,'story')

    def test_old_investor_receipt_cannot_be_rerecorded_after_evidence_or_source_change(self):
        h=self.load()
        for changed,field in [('evidence/evidence.json','evidence_sha256'),
                              ('data/raw/documents.json','source_documents_sha256')]:
            with self.subTest(changed=changed),tempfile.TemporaryDirectory() as d:
                p=Path(d);self.seed_draft(h,p)
                config=h.read_json(p/'project.json');config['research_required']=False;h.write_json(p/'project.json',config)
                briefs=h.read_json(p/'deck/section-briefs.json')
                receipt={'deck_sha256':h.sha(p/'deck/deck.json'),'briefs_sha256':h.sha(p/'deck/section-briefs.json'),
                    'evidence_sha256':h.sha(p/'evidence/evidence.json'),
                    'source_documents_sha256':h.sha(p/'data/raw/documents.json'),
                    'reviewer':'synthetic fixture','rationale':'synthetic fixture','verdict':'pass','findings':[],
                    'question_verdicts':[{'question_id':q['question_id'],'verdict':'pass','rationale':'synthetic fixture'}
                        for section in briefs['sections'] for q in section['questions']]}
                h.write_json(p/'reviews/investor.json',receipt)
                for stage in h.STAGES[:5]:h.record(p,stage)
                data=h.read_json(p/changed)
                if changed.startswith('evidence'):data['items'][0]['claim']='수정된 원문 근거'
                else:data['segments'][0]['text']='추출 문장 정정'
                h.write_json(p/changed,data)
                for stage in h.STAGES[:4]:h.record(p,stage)
                with self.assertRaisesRegex(ValueError,field):h.record(p,'review')

    def test_write_json_retries_transient_permission_error_without_losing_previous_file(self):
        h=self.load()
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'state.json';h.write_json(path,{'version':'old'})
            original_replace=Path.replace;attempts=[]
            def temporarily_locked(source,target):
                attempts.append(source)
                if len(attempts)<3:raise PermissionError('temporary sync lock')
                return original_replace(source,target)
            with patch.object(Path,'replace',temporarily_locked):
                h.write_json(path,{'version':'new'})
            self.assertEqual({'version':'new'},h.read_json(path))
            self.assertEqual(3,len(attempts))

    def test_write_json_persistent_permission_error_is_bounded_and_preserves_old_file(self):
        h=self.load()
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'state.json';h.write_json(path,{'version':'old'})
            attempts=[]
            def locked(source,target):
                attempts.append(source);raise PermissionError('persistent lock')
            with patch.object(Path,'replace',locked):
                with self.assertRaises(PermissionError):h.write_json(path,{'version':'new'})
            self.assertEqual({'version':'old'},h.read_json(path))
            self.assertLessEqual(len(attempts),5)
            self.assertGreater(len(attempts),1)

    def test_full_gate_tracks_evidence_revisions_and_finalizes_identical_pptx(self):
        h=self.load()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); h.initialize(p,'synthetic test only')
            # This fixture exercises legacy v1.2 receipts without later visual contracts.
            config=h.read_json(p/'project.json');config['require_visual_briefs']=False;config['require_visual_plan']=False
            h.write_json(p/'project.json',config)
            (p/'input/fixture.txt').write_text('synthetic example',encoding='utf-8')
            h.write_json(p/'data/raw/inventory.json', {'files':[{'source_id':'SRC','status':'ok','source_file':'fixture.txt','sha256':h.sha(p/'input/fixture.txt')}]})
            h.write_json(p/'data/raw/documents.json', {'segments':[{'source_id':'SRC','locator':'line1','text':'synthetic example'}]})
            h.write_json(p/'data/raw/assets.json', {'assets':[]})
            h.record(p,'intake')
            ledger={'items':[{'id':'E1','claim':'synthetic example','kind':'internal','status':'confirmed','source_id':'SRC','locator':'line1'}]}
            h.write_json(p/'evidence/evidence.json',ledger); h.record(p,'evidence')
            deck=h.read_json(p/'deck/deck.json')
            for s in deck['slides']:
                s.update(governing_message='예시 데이터',governing_evidence_ids=['E1'],speaker_notes='예시 발표 대본')
            briefs=h.read_json(p/'deck/section-briefs.json')
            for section in briefs['sections']:
                for q in section['questions']:
                    claim={'text':'synthetic claim for state transition test only','kind':'fact','evidence_ids':['E1']}
                    q.update(status='answered',answer=claim,argument=[claim],evidence_ids=['E1'],missing=[])
                    for row in q['coverage']: row['claim']=claim
            h.write_json(p/'deck/section-briefs.json',briefs)
            h.write_json(p/'deck/deck.json',deck); h.record(p,'story')
            h.write_json(p/'research/search-log.json',{'scope':'synthetic unit test only','limitations':'No real search performed',
                'queries':[{'query':'test fixture','engine':'synthetic','accessed_at':'2026-09-11','selected_urls':[]}], 'gaps':[]})
            h.record(p,'research')
            review={'deck_sha256':h.sha(p/'deck/deck.json'),'verdict':'pass','findings':[],
                    'reviewer':'synthetic test fixture','rationale':'test fixture only',
                    'briefs_sha256':h.sha(p/'deck/section-briefs.json'),
                    'evidence_sha256':h.sha(p/'evidence/evidence.json'),
                    'source_documents_sha256':h.sha(p/'data/raw/documents.json'),
                    'question_verdicts':[{'question_id':q['question_id'],'verdict':'pass','rationale':'synthetic fixture only'}
                        for section in briefs['sections'] for q in section['questions']]}
            h.write_json(p/'reviews/investor.json',review); h.record(p,'review')
            with zipfile.ZipFile(p/'output/seed-ir-draft.pptx','w') as z:
                z.writestr('ppt/presentation.xml','<presentation/>')
                for i in range(len(deck['slides'])): z.writestr(f'ppt/slides/slide{i+1}.xml','<slide/>')
            h.write_json(p/'design/design-profile.json',{'test_fixture':True})
            (p/'output/renders').mkdir()
            render_files=[]
            png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')
            for i in range(len(deck['slides'])):
                rel=f'output/renders/slide{i+1}.png'; (p/rel).write_bytes(png); render_files.append(rel)
            visual=dict(review,pptx_sha256=h.sha(p/'output/seed-ir-draft.pptx'),render_method='artifact-tool',
                        render_files=render_files,slides_reviewed=[s['id'] for s in deck['slides']],
                        checks={k:'pass' for k in ['text_overflow','font_substitution','contrast','chart_labels','image_crops']})
            (p/'output/master').mkdir()
            (p/'output/master/seed-ir-draft.pptx').write_bytes((p/'output/seed-ir-draft.pptx').read_bytes())
            visual['views']={'master':{k:visual[k] for k in ['verdict','pptx_sha256','render_method','render_files','slides_reviewed','checks']}}
            h.write_json(p/'reviews/visual.json',visual); h.record(p,'design')
            (p/'output/pitch-script.md').write_text('synthetic test script',encoding='utf-8')
            h.write_json(p/'reviews/pitch.json',dict(review,pptx_sha256=h.sha(p/'output/seed-ir-draft.pptx'),
                duration_seconds=290,method='estimated',estimation_basis='synthetic test'))
            h.record(p,'pitch')
            self.assertTrue(h.check(p,'final')['passed'],h.check(p,'final')['errors'])
            h.finalize(p)
            self.assertEqual((p/'output/seed-ir-draft.pptx').read_bytes(),(p/'output/seed-ir-final.pptx').read_bytes())
            self.assertTrue((p/'output/master/seed-ir-final.pptx').exists())
            original_evidence=(p/'evidence/evidence.json').read_bytes()
            ledger['items'][0]['claim']='changed synthetic evidence';h.write_json(p/'evidence/evidence.json',ledger)
            review['evidence_sha256']=h.sha(p/'evidence/evidence.json');h.write_json(p/'reviews/investor.json',review)
            self.assertTrue(any('reviews/visual.json: evidence_sha256' in e for e in h.check(p,'design')['errors']))
            (p/'evidence/evidence.json').write_bytes(original_evidence)
            review['evidence_sha256']=h.sha(p/'evidence/evidence.json');h.write_json(p/'reviews/investor.json',review)
            master=(p/'output/master/seed-ir-draft.pptx').read_bytes()
            (p/'output/master/seed-ir-draft.pptx').write_bytes(b'changed')
            self.assertFalse(h.check(p,'final')['passed'])
            (p/'output/master/seed-ir-draft.pptx').write_bytes(master)
            ledger['items'][0]['status']='contradicted'; h.write_json(p/'evidence/evidence.json',ledger)
            self.assertFalse(h.check(p,'final')['passed'])
            with self.assertRaises(ValueError): h.finalize(p)

    def test_modified_source_must_be_reextracted_before_rerecord(self):
        h=self.load()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); h.initialize(p,'test')
            source=p/'input/revenue.txt'; source.write_text('10',encoding='utf-8')
            h.write_json(p/'data/raw/inventory.json',{'files':[{'source_id':'SRC','source_file':'revenue.txt','sha256':h.sha(source),'status':'ok'}]})
            h.write_json(p/'data/raw/documents.json',{'segments':[{'source_id':'SRC','locator':'line1','text':'10'}]})
            h.write_json(p/'data/raw/assets.json',{'assets':[]})
            h.record(p,'intake'); source.write_text('0',encoding='utf-8')
            self.assertFalse(h.check(p,'intake')['passed'])
            with self.assertRaises(ValueError): h.record(p,'intake')

    def test_wrong_nested_json_type_reports_failure(self):
        h=self.load()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); h.initialize(p,'test')
            h.write_json(p/'data/raw/inventory.json',{'files':['not-an-object']})
            report=h.check(p,'intake')
            self.assertFalse(report['passed'])

    def test_missing_source_ids_cannot_confirm_internal_evidence(self):
        h=self.load()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); h.initialize(p,'test')
            h.write_json(p/'data/raw/inventory.json',{'files':[{'status':'ok'}]})
            h.write_json(p/'data/raw/documents.json',{'segments':[{'text':'fiction'}]})
            h.write_json(p/'data/raw/assets.json',{'assets':[]})
            h.write_json(p/'evidence/evidence.json',{'items':[{'id':'E1','claim':'fiction','kind':'internal','status':'confirmed','locator':'fake'}]})
            self.assertFalse(h.check(p,'evidence')['passed'])


if __name__ == '__main__':
    unittest.main()
