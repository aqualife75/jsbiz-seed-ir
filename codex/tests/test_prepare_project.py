"""Preparation preserves learner work and never installs into a global runtime."""
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import subprocess
import unittest
from contextlib import redirect_stdout
from unittest.mock import Mock, patch

SCRIPT = Path(__file__).resolve().parents[1] / 'plugins/seed-ir/skills/seed-ir/scripts/prepare_project.py'
spec = importlib.util.spec_from_file_location('prepare_project_tests', SCRIPT)
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)
REAL_NODE_PROBE = prepare.probe_node_runtime
REAL_LOAD_HARNESS = prepare.load_harness


def python_report(executable, missing=(), prefix=None):
    return {'ready': not missing, 'executable': str(executable), 'version': [3, 12, 1],
            'prefix': str(prefix or Path(executable).parent),
            'modules': {name: {'ok': name not in missing} for name in prepare.REQUIRED_MODULES},
            'missing': list(missing)}


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name) / '우리 팀'
        self.project.mkdir()
        (self.project / '자료넣는곳').mkdir()
        self.original = self.project / '자료넣는곳/기존 자료.txt'
        self.original.write_text('보존할 내용', 'utf8')
        self.harness = Mock()
        self.harness.initialize.side_effect = self.initialize
        self.harness.input_directory.side_effect = lambda project, config: project / config.get('input_dir', 'input')
        self.current = str(prepare.sys.executable)
        self.py = patch.object(prepare, 'probe_python', side_effect=lambda exe, log: python_report(exe)).start()
        self.node = patch.object(prepare, 'probe_node_runtime', return_value={
            'ready': True, 'node': '/bundled/node', 'node_modules': '/bundled/node_modules',
            'version': 'v22.0.0', 'module_imported': True}).start()
        self.loader = patch.object(prepare, 'load_harness', return_value=self.harness).start()
        self.addCleanup(patch.stopall)

    def initialize(self, project, team, input_dir):
        for folder in ['deck', 'evidence', 'work', input_dir]:
            (project / folder).mkdir(parents=True, exist_ok=True)
        for relative, value in [('project.json', {'team_name': team, 'input_dir': input_dir}),
                                ('state.json', {'checkpoints': {}}), ('deck/deck.json', {'slides': []}),
                                ('evidence/evidence.json', {'items': []})]:
            (project / relative).write_text(json.dumps(value, ensure_ascii=False), 'utf8')

    def test_first_setup_uses_korean_input_and_does_not_download_complete_runtime(self):
        with patch.object(prepare, 'create_venv') as create, patch.object(prepare, 'install_packages') as install:
            result = prepare.prepare(self.project, '새 팀', install_missing=True)
        self.assertTrue(result['ready'])
        self.harness.initialize.assert_called_once_with(self.project, '새 팀', input_dir='자료넣는곳')
        create.assert_not_called(); install.assert_not_called()
        self.assertEqual(self.original.read_text('utf8'), '보존할 내용')
        stored = json.loads((self.project / 'work/setup/runtime.json').read_text('utf8'))
        self.assertEqual(stored['input_dir'], '자료넣는곳')
        self.assertEqual(stored['python'], self.current)
        self.assertFalse(stored['deck_authored'])

    def test_repeat_is_resume_and_preserves_team_deck_and_user_files(self):
        prepare.prepare(self.project, '원래 팀')
        deck = self.project / 'deck/deck.json'
        deck.write_text('{"keep": "작업 중"}', 'utf8')
        state_before = (self.project / 'state.json').read_bytes()
        result = prepare.prepare(self.project, '덮어쓸 팀', install_missing=True)
        self.assertTrue(result['ready'])
        self.assertEqual(result['team_name'], '원래 팀')
        self.assertEqual(result['project_status'], 'resumed')
        self.assertEqual(self.harness.initialize.call_count, 1)
        self.assertEqual(deck.read_text('utf8'), '{"keep": "작업 중"}')
        self.assertEqual((self.project / 'state.json').read_bytes(), state_before)

    def test_partial_initialization_is_not_overwritten(self):
        (self.project / 'deck').mkdir()
        existing = self.project / 'deck/deck.json'
        existing.write_text('unfinished', 'utf8')
        with self.assertRaises(prepare.SetupError):
            prepare.prepare(self.project, '새 팀', install_missing=True)
        self.harness.initialize.assert_not_called()
        self.assertEqual(existing.read_text(), 'unfinished')
        self.assertFalse((self.project / 'project.json').exists())

    def make_venv(self):
        directory = self.project / '.venv'
        executable = prepare.venv_executable(directory)
        executable.parent.mkdir(parents=True)
        executable.write_text('stub', 'utf8')
        (directory / 'pyvenv.cfg').write_text('home = runtime', 'utf8')
        return directory, executable

    def test_existing_usable_project_venv_has_priority_and_no_download(self):
        directory, executable = self.make_venv()
        self.py.side_effect = lambda exe, log: python_report(exe, prefix=directory if str(exe) == str(executable) else None)
        with patch.object(prepare, 'create_venv') as create, patch.object(prepare, 'install_packages') as install:
            result = prepare.prepare(self.project, '우리 팀', install_missing=True)
        self.assertEqual(result['python'], str(executable))
        self.assertTrue(result['ready'])
        create.assert_not_called(); install.assert_not_called()

    def test_missing_dependency_without_install_flag_does_not_download(self):
        self.py.side_effect = lambda exe, log: python_report(exe, ['fitz'])
        with patch.object(prepare, 'create_venv') as create, patch.object(prepare, 'install_packages') as install:
            result = prepare.prepare(self.project, '우리 팀')
        self.assertFalse(result['ready'])
        self.assertTrue(result['needs'])
        create.assert_not_called(); install.assert_not_called()

    def test_failed_pip_is_recorded_and_never_targets_current_python(self):
        directory, executable = self.make_venv()
        (self.project / 'requirements.txt').write_text('PyMuPDF==1.27.2.3\n', 'utf8')
        self.py.side_effect = lambda exe, log: python_report(exe, ['fitz'], prefix=directory if str(exe) == str(executable) else None)
        with patch.object(prepare, 'install_packages', return_value={'ok': False, 'reason': 'timeout'}) as install:
            result = prepare.prepare(self.project, '우리 팀', install_missing=True)
        self.assertFalse(result['ready'])
        self.assertEqual(Path(install.call_args.args[0]), executable)
        self.assertNotEqual(str(install.call_args.args[0]), self.current)
        self.assertEqual(result['checks']['installation']['reason'], 'timeout')
        self.assertEqual(self.original.read_text('utf8'), '보존할 내용')
        self.assertTrue((self.project / 'work/setup/runtime.json').exists())

    def test_venv_path_file_is_not_overwritten(self):
        file = self.project / '.venv'
        file.write_text('unrelated work', 'utf8')
        with self.assertRaises(prepare.SetupError):
            prepare.prepare(self.project, '우리 팀', install_missing=True)
        self.assertEqual(file.read_text(), 'unrelated work')
        self.harness.initialize.assert_not_called()

    def test_redirected_work_or_venv_is_rejected_before_initialization(self):
        for relative in ['work', '.venv']:
            with self.subTest(relative=relative), patch.object(prepare, 'is_redirect', side_effect=lambda p: p == self.project / relative):
                with self.assertRaises(prepare.SetupError):
                    prepare.prepare(self.project, '우리 팀', install_missing=True)
        self.harness.initialize.assert_not_called()

    def test_node_import_failure_cannot_claim_ready(self):
        self.node.return_value = {'ready': False, 'node': '/existing/node', 'node_modules': '/existing/modules',
                                  'module_imported': False, 'reason': 'import_failed'}
        result = prepare.prepare(self.project, '우리 팀')
        self.assertFalse(result['ready'])
        self.assertFalse(result['checks']['node']['module_imported'])
        self.assertTrue(any(need['kind'] == 'node_runtime' for need in result['needs']))

    def test_requirements_fallback_selects_only_missing_known_packages(self):
        skill = self.project / 'skill'
        skill.mkdir()
        (skill / 'requirements.txt').write_text('python-pptx==1.0.2\nPillow==12.1.1\nPyMuPDF==1.27.2.3\nolefile==0.47\n', 'utf8')
        with patch.object(prepare, 'SKILL_DIR', skill):
            packages, path = prepare.required_packages(self.project, ['PIL', 'fitz'])
        self.assertEqual(packages, ['Pillow==12.1.1', 'PyMuPDF==1.27.2.3'])
        self.assertEqual(path, skill / 'requirements.txt')

    def test_requirement_options_cannot_redirect_install_outside_venv(self):
        (self.project / 'requirements.txt').write_text('Pillow @ https://example.invalid/pkg.whl\n', 'utf8')
        with self.assertRaises(prepare.SetupError):
            prepare.required_packages(self.project, ['PIL'])

    def test_successful_install_reprobes_project_venv(self):
        directory, executable = self.make_venv()
        (self.project / 'requirements.txt').write_text('Pillow==12.1.1\n', 'utf8')
        installed = []
        self.py.side_effect = lambda exe, log: python_report(exe, [] if installed else ['PIL'], prefix=directory if str(exe) == str(executable) else None)
        def install(*args):
            installed.append(args)
            return {'ok': True}
        with patch.object(prepare, 'install_packages', side_effect=install):
            result = prepare.prepare(self.project, '우리 팀', install_missing=True)
        self.assertTrue(result['ready'])
        self.assertEqual(result['python'], str(executable))
        self.assertEqual(installed[0][1], ['Pillow==12.1.1'])

    def test_pip_timeout_has_bounded_private_log_and_virtualenv_requirement(self):
        _, executable = self.make_venv()
        path = self.project / 'pip.log'
        error = subprocess.TimeoutExpired(['pip'], timeout=prepare.INSTALL_TIMEOUT, output=b'progress', stderr=b'network stalled')
        with patch.object(prepare.subprocess, 'run', side_effect=error) as run:
            result = prepare.install_packages(executable, ['Pillow==12.1.1'], self.project, prepare.SetupLog(path))
        self.assertFalse(result['ok'])
        self.assertEqual(result['reason'], 'timeout')
        self.assertEqual(run.call_args.kwargs['timeout'], prepare.INSTALL_TIMEOUT)
        self.assertIn('--require-virtualenv', run.call_args.args[0])
        self.assertIn('--isolated', run.call_args.args[0])
        self.assertIn('network stalled', path.read_text('utf8'))

    def test_node_probe_requires_successful_process_and_valid_module_exports(self):
        candidate = [(Path('/node'), Path('/modules'), Path('/modules/@oai/artifact-tool/dist/artifact_tool.mjs'))]
        log = prepare.SetupLog(self.project / 'node.log')
        with patch.object(prepare, 'node_candidates', return_value=iter(candidate)), \
             patch.object(prepare.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, '', '')):
            result = REAL_NODE_PROBE(self.project, log=log)
        self.assertFalse(result['ready'])
        self.assertFalse(result['module_imported'])
        with patch.object(prepare, 'node_candidates', return_value=iter(candidate)), \
             patch.object(prepare.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'SEED_IR_PROBE:{"ready":true,"module_imported":true,"version":"v22"}\n', '')):
            result = REAL_NODE_PROBE(self.project, log=log)
        self.assertTrue(result['ready'])
        self.assertTrue(result['module_imported'])

    def test_unexpected_exception_has_safe_stdout_and_private_diagnostics(self):
        self.initialize(self.project, '우리 팀', '자료넣는곳')
        visible = io.StringIO()
        with patch.object(prepare, 'prepare', side_effect=RuntimeError('private internal detail')), redirect_stdout(visible):
            code = prepare.main(['--project', str(self.project), '--team', '우리 팀'])
        self.assertEqual(code, 2)
        self.assertNotIn('private internal detail', visible.getvalue())
        record = json.loads((self.project / 'work/setup/runtime.json').read_text('utf8'))
        self.assertFalse(record['ready'])
        self.assertIn('private internal detail', (self.project / record['log']).read_text('utf8'))

    def test_legacy_input_default_remains_input_even_when_folder_is_absent(self):
        self.initialize(self.project, '기존 팀', '자료넣는곳')
        config = self.project / 'project.json'
        config.write_text('{"team_name":"기존 팀"}', 'utf8')
        result = prepare.prepare(self.project, '다른 팀')
        self.assertEqual(result['input_dir'], 'input')
        self.harness.input_directory.assert_called_once()
        self.assertEqual(config.read_text('utf8'), '{"team_name":"기존 팀"}')

    def test_real_harness_initialization_uses_requested_input_directory(self):
        with patch.object(prepare, 'load_harness', return_value=REAL_LOAD_HARNESS()):
            result = prepare.prepare(self.project, '실제 초기화 테스트')
        self.assertTrue(result['ready'])
        config = json.loads((self.project / 'project.json').read_text('utf8'))
        self.assertEqual(config['input_dir'], '자료넣는곳')
        self.assertTrue((self.project / 'deck/section-briefs.json').is_file())
        self.assertFalse(result['deck_authored'])

    def test_venv_interpreter_must_prove_project_prefix_before_pip(self):
        directory, executable = self.make_venv()
        self.py.side_effect = lambda exe, log: python_report(exe, ['fitz'], prefix=directory.parent)
        with patch.object(prepare, 'install_packages') as install:
            result = prepare.prepare(self.project, '우리 팀', install_missing=True)
        self.assertFalse(result['ready'])
        self.assertEqual(result['checks']['existing_venv']['reason'], 'venv_prefix_mismatch')
        install.assert_not_called()

    def test_incomplete_venv_keeps_unrelated_work_and_does_not_recreate(self):
        directory = self.project / '.venv'
        directory.mkdir()
        note = directory / 'keep.txt'
        note.write_text('keep', 'utf8')
        self.py.side_effect = lambda exe, log: python_report(exe, ['fitz'])
        with patch.object(prepare, 'create_venv') as create, patch.object(prepare, 'install_packages') as install:
            result = prepare.prepare(self.project, '우리 팀', install_missing=True)
        self.assertFalse(result['ready'])
        self.assertEqual(note.read_text('utf8'), 'keep')
        create.assert_not_called(); install.assert_not_called()

    def test_current_python_below_minimum_does_not_create_wrong_version_venv(self):
        report = python_report(self.current)
        report.update(version=[3, 10, 9], ready=False)
        self.py.return_value = report
        self.py.side_effect = None
        with patch.object(prepare, 'create_venv') as create:
            result = prepare.prepare(self.project, '우리 팀', install_missing=True)
        self.assertFalse(result['ready'])
        create.assert_not_called()
        self.assertTrue(any('3.11' in need['message'] for need in result['needs']))


if __name__ == '__main__':
    unittest.main()
