"""The learner distribution must open as a project without an installation step."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('release_builder',ROOT/'build_release.py')
release=importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseTests(unittest.TestCase):
    def test_ready_project_contains_startup_and_empty_input_not_installer(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            target=release.build_learner(Path(tmp))
            prefix=release.LEARNER_ROOT+'/'
            with zipfile.ZipFile(target) as archive:
                names=archive.namelist()
                self.assertEqual(len(names),len(set(names)))
                self.assertTrue(all(n.startswith(prefix) for n in names))
                self.assertEqual(archive.read(prefix+'AGENTS.md'),(ROOT/'learner-template/AGENTS.md').read_bytes())
                self.assertEqual(archive.read(prefix+'.agents/skills/seed-ir/requirements.txt'),(ROOT/'requirements.txt').read_bytes())
                self.assertEqual(len([n for n in names if n.startswith(prefix+'.codex/agents/')]),7)
                for rel in ['자료넣는곳/','결과물/']:
                    self.assertTrue(archive.getinfo(prefix+rel).is_dir())
                    self.assertEqual([n for n in names if n.startswith(prefix+rel)],[prefix+rel])
                for rel in ['project.json','state.json','install.py','install-windows.cmd','input/',
                            '.venv/','work/','output/','examples/make_demo.py',
                            'docs/v1.1-implementation-plan.md','docs/plans/']:
                    self.assertFalse(any(n==prefix+rel or (rel.endswith('/') and n.startswith(prefix+rel)) for n in names),rel)
                for name in names:
                    self.assertNotIn('..',Path(name).parts)
                    release.audit_text(name,'archive member')
                self.assertEqual(len([n for n in names if n.endswith('.pptx')]),2)
                manifest=json.loads(archive.read(prefix+'FILE-MANIFEST.json'))
                for name,digest in manifest.items():
                    self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(),digest,name)
                self.assertIsNone(archive.testzip())

    def test_legacy_developer_layout_and_reproducible_learner_archive(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            out=Path(tmp)
            learner=release.build_learner(out)
            before=hashlib.sha256(learner.read_bytes()).hexdigest()
            self.assertEqual(before,hashlib.sha256(release.build_learner(out).read_bytes()).hexdigest())
            developer=release.build(out)
            with zipfile.ZipFile(developer) as archive:
                self.assertIn('seed-ir-harness/install.py',archive.namelist())
                self.assertIn('seed-ir-harness/plugins/seed-ir/skills/seed-ir/SKILL.md',archive.namelist())
                self.assertIn('seed-ir-harness/tests/test_release.py',archive.namelist())


if __name__=='__main__': unittest.main()
