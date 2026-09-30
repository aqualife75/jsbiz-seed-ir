import importlib.util
from pathlib import Path
import tempfile
import unittest
import json

ROOT=Path(__file__).resolve().parents[1]

class InstallTests(unittest.TestCase):
    def load(self):
        script=ROOT/'install.py'
        self.assertTrue(script.exists(), 'installer not implemented')
        spec=importlib.util.spec_from_file_location('installer',script)
        m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        return m

    def test_project_local_install(self):
        m=self.load()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'교육생 팀'
            m.install(p,'가상팀',False)
            self.assertTrue((p/'.agents/skills/seed-ir/SKILL.md').exists())
            self.assertTrue((p/'project.json').exists())
            self.assertTrue((p/'AGENTS.md').exists())
            self.assertTrue(list((p/'.codex/agents').glob('*.toml')))
            deck=json.loads((p/'deck/deck.json').read_text(encoding='utf-8'))
            self.assertEqual('1.2',deck['schema_version'])
            self.assertEqual(18,len(deck['slides']))
            self.assertEqual(300,sum(s['seconds'] for s in deck['slides']))
            self.assertEqual(14,len({s['section'] for s in deck['slides']}))

    def test_refuses_conflict_before_any_mutation(self):
        m=self.load()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'AGENTS.md').write_text('Keep me',encoding='utf-8')
            with self.assertRaises(FileExistsError): m.install(p,'test',False)
            self.assertEqual((p/'AGENTS.md').read_text(),'Keep me')
            self.assertFalse((p/'.agents').exists())

    def test_refuses_install_into_package(self):
        m=self.load()
        with self.assertRaises(ValueError): m.install(ROOT/'bad-target','test',False)

    def test_parent_file_conflict_does_not_partially_install(self):
        m=self.load()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'data').write_text('keep',encoding='utf-8')
            with self.assertRaises(FileExistsError): m.install(p,'test',False)
            self.assertFalse((p/'AGENTS.md').exists())
            self.assertFalse((p/'.agents').exists())

    def test_preserves_existing_question_briefs_before_installing(self):
        m=self.load()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'deck').mkdir()
            existing=p/'deck/section-briefs.json'; existing.write_text('{"keep": true}')
            with self.assertRaises(FileExistsError): m.install(p,'test',False)
            self.assertEqual(existing.read_text(),'{"keep": true}')
            self.assertFalse((p/'AGENTS.md').exists())

    def test_installs_rich_engine_and_question_contract(self):
        m=self.load()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'v11'
            m.install(p,'test',False)
            self.assertTrue((p/'.agents/skills/seed-ir/scripts/render_rich.mjs').is_file())
            self.assertTrue((p/'deck/section-briefs.json').is_file())

if __name__=='__main__': unittest.main()
