#!/usr/bin/env python3
"""Prepare a learner project using stdlib only; this does not author a deck."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import uuid

SKILL_DIR = Path(__file__).resolve().parents[1]
MIN_PYTHON = (3, 11)
REQUIRED_MODULES = {'pptx': 'python-pptx', 'PIL': 'Pillow', 'fitz': 'PyMuPDF', 'olefile': 'olefile'}
PROBE_TIMEOUT = 45
INSTALL_TIMEOUT = 180
PROBE_PREFIX = 'SEED_IR_PROBE:'


class SetupError(ValueError):
    """A short, safe message suitable for a learner; raw errors go to the log."""


def is_redirect(path: Path) -> bool:
    return path.is_symlink() or bool(getattr(path, 'is_junction', lambda: False)())


def local_path(project: Path, relative: str, directory: bool = False) -> Path:
    fragment = Path(relative)
    if fragment.is_absolute() or not fragment.parts or '..' in fragment.parts:
        raise SetupError('프로젝트 폴더 안의 경로만 사용할 수 있습니다. Codex가 폴더 구성을 확인해야 합니다.')
    target = project / fragment
    cursor = project
    for index, part in enumerate(fragment.parts):
        cursor = cursor / part
        if is_redirect(cursor):
            raise SetupError('준비 폴더에 연결 경로가 있어 기존 자료를 보존하고 중단했습니다. Codex가 실제 폴더 위치를 확인해야 합니다.')
        needs_directory = index < len(fragment.parts) - 1 or directory
        if cursor.exists() and needs_directory and not cursor.is_dir():
            raise SetupError('준비에 필요한 폴더 이름으로 기존 파일이 있습니다. 덮어쓰지 않았으며 Codex의 확인이 필요합니다.')
    try:
        target.resolve().relative_to(project)
    except ValueError as error:
        raise SetupError('프로젝트 밖으로 연결되는 경로는 준비에 사용할 수 없습니다.') from error
    return target


def load_harness():
    spec = importlib.util.spec_from_file_location('seed_ir_prepare_harness', Path(__file__).with_name('harness.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError) as error:
        raise SetupError('기존 준비 기록이나 프로젝트 설정을 읽지 못했습니다. 덮어쓰지 않았으며 Codex가 해당 파일을 확인해야 합니다.') from error


def write_runtime(project: Path, report: dict):
    target = local_path(project, 'work/setup/runtime.json')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', prefix='.runtime-', suffix='.tmp',
                                         dir=target.parent, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(report, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        for attempt, delay in enumerate((0, .05, .1, .2, .4)):
            if delay:
                time.sleep(delay)
            try:
                temporary.replace(target)
                temporary = None
                break
            except PermissionError:
                if attempt == 4:
                    raise
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


class SetupLog:
    def __init__(self, path: Path):
        self.path = path

    def __call__(self, phase: str, **details):
        record = {'at': datetime.now(timezone.utc).isoformat(), 'phase': phase, **details}
        with self.path.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + '\n')


def run_logged(command: list[str], log: SetupLog, phase: str, timeout: int, cwd: Path | None = None) -> dict:
    started = time.monotonic()
    result = {'ok': False, 'returncode': None, 'stdout': '', 'stderr': ''}
    try:
        completed = subprocess.run(command, cwd=cwd, capture_output=True, text=True,
                                   encoding='utf-8', errors='replace', timeout=timeout)
        result.update(ok=completed.returncode == 0, returncode=completed.returncode,
                      stdout=completed.stdout, stderr=completed.stderr)
        if completed.returncode:
            result['reason'] = 'process_failed'
    except subprocess.TimeoutExpired as error:
        result.update(reason='timeout', stdout=error.stdout or '', stderr=error.stderr or '')
    except OSError as error:
        result.update(reason='start_failed', error_type=type(error).__name__, stderr=str(error))
    for channel in ['stdout', 'stderr']:
        if isinstance(result[channel], bytes):
            result[channel] = result[channel].decode('utf-8', errors='replace')
    result['elapsed_seconds'] = round(time.monotonic() - started, 3)
    if log is not None:
        log(phase, command=command, **result)
    return result


def probe_value(result: dict) -> dict | None:
    if not result['ok']:
        return None
    for line in reversed(result.get('stdout', '').splitlines()):
        if line.startswith(PROBE_PREFIX):
            try:
                value = json.loads(line[len(PROBE_PREFIX):])
                return value if isinstance(value, dict) else None
            except ValueError:
                return None
    return None


PYTHON_PROBE = r'''
import importlib,json,sys
checks={}
for name in ['pptx','PIL','fitz','olefile']:
    try:
        module=importlib.import_module(name)
        api={'pptx':'Presentation','PIL':'open','fitz':'open','olefile':'OleFileIO'}[name]
        api_module=importlib.import_module('PIL.Image') if name=='PIL' else module
        if not callable(getattr(api_module,api,None)):
            raise ImportError('required document API is unavailable')
        checks[name]={'ok':True,'version':str(getattr(module,'__version__',getattr(module,'VersionBind','unknown')))}
    except Exception as error:
        checks[name]={'ok':False,'error_type':type(error).__name__}
print('SEED_IR_PROBE:'+json.dumps({'version':list(sys.version_info[:3]),'prefix':sys.prefix,'executable':sys.executable,'modules':checks}))
'''


def supported_python(report: dict) -> bool:
    return tuple(report.get('version', [0, 0])[:2]) >= MIN_PYTHON


def probe_python(executable: str | Path, log: SetupLog) -> dict:
    result = run_logged([str(executable), '-I', '-c', PYTHON_PROBE], log, 'python_probe', PROBE_TIMEOUT)
    report = probe_value(result) or {'executable': str(executable), 'version': [], 'modules': {},
                                    'reason': result.get('reason', 'invalid_probe_output')}
    report['missing'] = [name for name in REQUIRED_MODULES if not report.get('modules', {}).get(name, {}).get('ok')]
    report['ready'] = supported_python(report) and not report['missing']
    return report


def venv_executable(directory: Path) -> Path:
    return directory / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def valid_venv_report(report: dict, directory: Path) -> bool:
    # Keep the venv executable path (including normal POSIX interpreter symlinks).
    # The child must prove that Python actually entered this environment.
    return bool(report.get('prefix')) and Path(report['prefix']).resolve() == directory.resolve()


def required_packages(project: Path, missing: list[str]) -> tuple[list[str], Path]:
    candidates = [local_path(project, 'requirements.txt'), SKILL_DIR / 'requirements.txt']
    requirements = next((path for path in candidates if path.is_file()), None)
    if requirements is None or is_redirect(requirements):
        raise SetupError('필요 패키지 목록을 찾지 못했습니다. Codex가 배포본의 requirements.txt를 확인해야 합니다.')
    selected = {}
    names = {name.casefold(): name for name in REQUIRED_MODULES.values()}
    try:
        for raw in requirements.read_text(encoding='utf-8-sig').splitlines():
            line = raw.partition('#')[0].strip()
            if not line:
                continue
            match = re.fullmatch(r'([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+!-]+)', line)
            if not match:
                raise SetupError('패키지 목록은 배포본의 고정 버전 형식이어야 합니다. Codex가 준비 파일을 확인해야 합니다.')
            canonical = names.get(match.group(1).casefold())
            if canonical:
                if canonical in selected:
                    raise SetupError('패키지 목록에 중복 항목이 있습니다. Codex가 배포 파일을 확인해야 합니다.')
                selected[canonical] = canonical + '==' + match.group(2)
        packages = [selected[REQUIRED_MODULES[name]] for name in missing]
    except (OSError, KeyError) as error:
        raise SetupError('부족한 패키지의 고정 버전 목록이 없습니다. Codex가 배포 파일을 확인해야 합니다.') from error
    return packages, requirements


def create_venv(executable: str | Path, directory: Path, log: SetupLog) -> dict:
    if directory.exists() or is_redirect(directory):
        raise SetupError('기존 .venv를 덮어쓰지 않았습니다. Codex가 프로젝트 실행 환경을 확인해야 합니다.')
    return run_logged([str(executable), '-I', '-m', 'venv', '--copies', str(directory)],
                      log, 'venv_create', INSTALL_TIMEOUT, directory.parent)


def install_packages(executable: str | Path, packages: list[str], project: Path, log: SetupLog) -> dict:
    directory = local_path(project, '.venv', directory=True)
    # Do not resolve the executable itself: a normal POSIX venv may symlink it.
    try:
        Path(executable).absolute().relative_to(directory)
    except ValueError as error:
        raise SetupError('패키지는 프로젝트 전용 실행 환경에만 준비할 수 있습니다.') from error
    command = [str(executable), '-I', '-m', 'pip', '--isolated', '--require-virtualenv', 'install', '--disable-pip-version-check',
               '--no-input', '--no-cache-dir', '--timeout', '20', '--retries', '1', *packages]
    return run_logged(command, log, 'pip_install', INSTALL_TIMEOUT, project)


NODE_PROBE = r'''
import {pathToFileURL} from 'node:url';
const module=await import(pathToFileURL(process.argv[1]).href);
const ready=typeof module.Presentation?.create==='function' && typeof module.PresentationFile?.importPptx==='function';
console.log('SEED_IR_PROBE:'+JSON.stringify({ready,version:process.version,module_imported:ready}));
if(!ready)process.exitCode=2;
'''


def node_candidates(project: Path, node: str | None, node_modules: str | None, prior: dict):
    nodes = [node, os.environ.get('SEED_IR_NODE'), os.environ.get('RUNTIME_NODE'), prior.get('node'), shutil.which('node')]
    parent = Path(sys.executable).parent.parent
    nodes += [parent / 'node/bin/node.exe', parent / 'node/bin/node']
    cache = Path.home() / '.cache/codex-runtimes'
    if cache.is_dir():
        try:
            for runtime in sorted(cache.iterdir()):
                nodes += [runtime / 'dependencies/node/bin/node.exe', runtime / 'dependencies/node/bin/node']
        except OSError:
            pass
    module_hints = [node_modules, os.environ.get('SEED_IR_NODE_MODULES'), os.environ.get('RUNTIME_NODE_MODULES'), prior.get('node_modules')]
    seen = set()
    for value in nodes:
        if not isinstance(value, (str, Path)) or not value:
            continue
        executable = Path(value).expanduser().absolute()
        if not executable.is_file():
            continue
        roots = module_hints + [executable.parent.parent / 'node_modules', executable.parent / 'node_modules', project / 'node_modules']
        for hint in roots:
            if not isinstance(hint, (str, Path)) or not hint:
                continue
            root = Path(hint).expanduser().absolute()
            module = root / '@oai/artifact-tool/dist/artifact_tool.mjs'
            key = (str(executable), str(module))
            if key not in seen and module.is_file():
                seen.add(key)
                yield executable, root, module


def probe_node_runtime(project: Path, node: str | None = None, node_modules: str | None = None,
                       prior: dict | None = None, log: SetupLog | None = None) -> dict:
    attempts = []
    for executable, root, module in node_candidates(project, node, node_modules, prior or {}):
        result = run_logged([str(executable), '--input-type=module', '-e', NODE_PROBE, str(module)],
                            log, 'node_import_probe', PROBE_TIMEOUT, project)
        value = probe_value(result)
        if value and value.get('ready') and value.get('module_imported'):
            return {**value, 'node': str(executable), 'node_modules': str(root), 'probe_scope': 'node execution and Artifact Tool module import'}
        attempts.append({'node': str(executable), 'node_modules': str(root),
                         'reason': result.get('reason', 'invalid_probe_output'), 'returncode': result['returncode']})
    return {'ready': False, 'node': None, 'node_modules': None, 'module_imported': False,
            'reason': 'import_failed' if attempts else 'runtime_not_found', 'attempts': attempts}


def prepare(project: Path | str, team: str, install_missing: bool = False,
            node: str | None = None, node_modules: str | None = None) -> dict:
    requested = Path(project).expanduser().absolute()
    if is_redirect(requested) or (requested.exists() and not requested.is_dir()):
        raise SetupError('프로젝트로 사용할 실제 폴더를 확인해야 합니다. 기존 파일은 변경하지 않았습니다.')
    project = requested.resolve()
    for relative in ['data/raw', 'deck', 'evidence', 'research', 'reviews', 'design', 'output',
                     'work/setup', '자료넣는곳', '결과물', '.venv']:
        local_path(project, relative, directory=True)
    for relative in ['project.json', 'state.json', 'deck/deck.json', 'deck/section-briefs.json',
                     'evidence/evidence.json', 'evidence/section-map.json', 'work/setup/runtime.json', '.venv/pyvenv.cfg']:
        local_path(project, relative)
    config_path = project / 'project.json'
    exists = config_path.exists()
    if exists:
        config = read_json(config_path)
        if not isinstance(config, dict):
            raise SetupError('기존 프로젝트 설정의 형식을 확인해야 합니다. 덮어쓰지 않았습니다.')
        input_dir = config.get('input_dir', 'input')
        if not isinstance(input_dir, str) or not input_dir:
            raise SetupError('기존 자료 폴더 설정을 Codex가 확인해야 합니다. 자료는 변경하지 않았습니다.')
        local_path(project, input_dir.replace('\\', '/'), directory=True)
        harness = load_harness()
        if callable(getattr(harness, 'input_directory', None)):
            try:
                input_dir = harness.input_directory(project, config).relative_to(project).as_posix()
            except (ValueError, TypeError, OSError) as error:
                raise SetupError('기존 자료 폴더가 내부 작업 폴더와 겹치거나 올바르지 않습니다. Codex가 설정을 확인해야 합니다.') from error
        local_path(project, input_dir, directory=True)
        project_status = 'resumed'
    else:
        for relative in ['state.json', 'data/raw', 'deck', 'evidence', 'research', 'reviews', 'design', 'output', 'work']:
            path = project / relative
            if path.exists() and (path.is_file() or any(path.iterdir())):
                raise SetupError('이전 작업의 일부가 있어 새 프로젝트로 덮어쓰지 않았습니다. Codex가 기존 프로젝트 상태를 확인해야 합니다.')
        project.mkdir(parents=True, exist_ok=True)
        input_dir = '자료넣는곳'
        load_harness().initialize(project, team.strip() or '우리팀', input_dir=input_dir)
        config = read_json(config_path)
        project_status = 'initialized'
    local_path(project, '결과물', directory=True).mkdir(exist_ok=True)
    setup = local_path(project, 'work/setup', directory=True)
    setup.mkdir(parents=True, exist_ok=True)
    previous_path = local_path(project, 'work/setup/runtime.json')
    prior = read_json(previous_path) if previous_path.exists() else {}
    if not isinstance(prior, dict):
        raise SetupError('기존 준비 기록의 형식을 Codex가 확인해야 합니다. 작업 자료는 보존했습니다.')
    log = SetupLog(setup / ('setup-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8] + '.log'))
    checks, needs = {}, []
    missing_state = [relative for relative in ['state.json', 'deck/deck.json', 'evidence/evidence.json'] if not (project / relative).is_file()]
    checks['project'] = {'ok': not missing_state, 'missing': missing_state}
    if missing_state:
        project_status = 'incomplete'
        needs.append({'kind': 'project_state', 'message': 'Codex가 일부만 남은 프로젝트 상태를 확인하고 기존 작업을 복구해야 합니다.'})
    current = probe_python(sys.executable, log)
    checks['current_python'] = current
    selected, selected_executable = current, Path(sys.executable)
    directory = project / '.venv'
    executable = venv_executable(directory)
    # Reject redirected venv directories, while permitting the standard POSIX
    # bin/python symlink after the child confirms sys.prefix.
    local_path(project, '.venv/' + executable.parent.name, directory=True)
    existing = None
    if directory.exists():
        if (directory / 'pyvenv.cfg').is_file() and executable.is_file():
            existing = probe_python(executable, log)
            if not valid_venv_report(existing, directory):
                existing.update(ready=False, reason='venv_prefix_mismatch')
        else:
            existing = {'ready': False, 'reason': 'incomplete_venv', 'missing': list(REQUIRED_MODULES)}
        checks['existing_venv'] = existing
        if existing.get('ready'):
            selected, selected_executable = existing, executable
    if not selected.get('ready') and install_missing:
        try:
            if not directory.exists():
                if not supported_python(current):
                    raise SetupError('Codex가 Python 3.11 이상의 제공 실행 환경을 찾아야 합니다.')
                creation = create_venv(sys.executable, directory, log)
                checks['venv_creation'] = {key: value for key, value in creation.items() if key not in {'stdout', 'stderr'}}
                if not creation['ok']:
                    raise SetupError('프로젝트 전용 실행 환경을 만들지 못했습니다. Codex가 준비 로그를 확인해야 합니다.')
                existing = probe_python(executable, log)
            if existing is None or not valid_venv_report(existing, directory) or not supported_python(existing):
                raise SetupError('기존 프로젝트 실행 환경이 불완전합니다. 덮어쓰지 않았으며 Codex의 확인이 필요합니다.')
            packages, requirements = required_packages(project, existing.get('missing', list(REQUIRED_MODULES)))
            checks['requirements'] = str(requirements)
            installation = install_packages(executable, packages, project, log) if packages else {'ok': True, 'skipped': True}
            checks['installation'] = {key: value for key, value in installation.items() if key not in {'stdout', 'stderr'}}
            if installation['ok']:
                selected = probe_python(executable, log)
                if not valid_venv_report(selected, directory):
                    selected.update(ready=False, reason='venv_prefix_mismatch')
                selected_executable = executable
            else:
                needs.append({'kind': 'package_installation', 'message': 'Codex가 패키지 다운로드 연결과 준비 로그를 확인한 뒤 환경 준비를 다시 진행해야 합니다.'})
        except SetupError as error:
            log('preparation_action_needed', message=str(error))
            needs.append({'kind': 'python_environment', 'message': str(error)})
    if not selected.get('ready'):
        needs.append({'kind': 'python_packages', 'modules': selected.get('missing', list(REQUIRED_MODULES)),
                      'message': 'Codex가 필요한 문서 처리 도구를 프로젝트 안에 준비해야 합니다.' if supported_python(selected)
                      else 'Codex가 Python 3.11 이상의 제공 실행 환경을 찾아야 합니다.'})
    checks['selected_python'] = selected
    node_report = probe_node_runtime(project, node=node, node_modules=node_modules, prior=prior, log=log)
    checks['node'] = node_report
    if not node_report.get('ready'):
        needs.append({'kind': 'node_runtime', 'message': 'Codex가 제공하는 Node.js와 @oai/artifact-tool 실행 환경의 경로를 확인해야 합니다.'})
    report = {'schema_version': 'seed-ir-preparation.v1', 'prepared_at': datetime.now(timezone.utc).isoformat(),
              'team_name': config.get('team_name', team), 'project_status': project_status,
              'python': str(selected_executable), 'node': node_report.get('node'), 'node_modules': node_report.get('node_modules'),
              'input_dir': input_dir, 'ready': bool(selected.get('ready') and node_report.get('ready') and not needs),
              'deck_authored': False, 'scope': '제작 환경 준비; 자료 분석과 AI 덱 작성은 다음 단계입니다.',
              'checks': checks, 'needs': needs, 'log': log.path.relative_to(project).as_posix(),
              'retry_request': '환경 준비를 다시 확인해줘.'}
    write_runtime(project, report)
    return report


def record_unexpected_failure(project: Path, team: str, error: Exception):
    """Best-effort private diagnostics; never follow an unsafe setup directory."""
    try:
        requested = project.expanduser().absolute()
        if is_redirect(requested) or not requested.is_dir():
            return
        root = requested.resolve()
        setup = local_path(root, 'work/setup', directory=True)
        local_path(root, 'work/setup/runtime.json')
        setup.mkdir(parents=True, exist_ok=True)
        log = SetupLog(setup / ('setup-error-' + uuid.uuid4().hex + '.log'))
        log('unexpected_failure', error_type=type(error).__name__, detail=str(error), traceback=traceback.format_exc())
        config_path = local_path(root, 'project.json')
        try:
            config = read_json(config_path) if config_path.is_file() else {}
            if not isinstance(config, dict):
                config = {}
        except SetupError:
            config = {}
        report = {'schema_version': 'seed-ir-preparation.v1', 'prepared_at': datetime.now(timezone.utc).isoformat(),
                  'team_name': config.get('team_name', team), 'project_status': 'action_needed', 'python': sys.executable,
                  'node': None, 'node_modules': None, 'input_dir': config.get('input_dir', 'input' if config_path.exists() else '자료넣는곳'), 'ready': False,
                  'deck_authored': False, 'checks': {'unexpected_failure': {'error_type': type(error).__name__}},
                  'needs': [{'kind': 'setup_failure', 'message': 'Codex가 준비 로그와 기존 프로젝트 상태를 확인해야 합니다.'}],
                  'log': log.path.relative_to(root).as_posix(), 'retry_request': '환경 준비를 다시 확인해줘.'}
        write_runtime(root, report)
    except Exception:
        # A redirected or locked work folder must not lead to fallback writes
        # outside the project or expose raw exception text on learner stdout.
        return


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Codex가 프로젝트 실행 환경을 준비합니다. 이 단계는 덱을 작성하지 않습니다.')
    parser.add_argument('--project', type=Path, default=Path('.'))
    parser.add_argument('--team', default='우리팀')
    parser.add_argument('--install-missing', action='store_true')
    parser.add_argument('--node')
    parser.add_argument('--node-modules')
    args = parser.parse_args(argv)
    try:
        report = prepare(args.project, args.team, args.install_missing, args.node, args.node_modules)
    except SetupError as error:
        print(str(error))
        print('Codex에게 “환경 준비를 다시 확인해줘”라고 말씀해 주세요.')
        return 2
    except Exception as error:
        # Do not expose a raw traceback, source paths or file contents to learners.
        record_unexpected_failure(args.project, args.team, error)
        print('환경 준비를 마치지 못했습니다. Codex가 준비 파일과 작업 폴더의 접근 상태를 확인해야 합니다.')
        print('Codex에게 “환경 준비를 다시 확인해줘”라고 말씀해 주세요.')
        return 2
    if report['ready']:
        print('제작 환경 준비가 끝났습니다. 자료 분석과 AI 덱 작성은 아직 시작하지 않았습니다.')
        print('Codex가 이어서 자료 분석과 AI 덱 작성을 진행합니다.')
        return 0
    print('준비가 아직 끝나지 않았습니다. ' + report['needs'][0]['message'])
    print('Codex에게 “환경 준비를 다시 확인해줘”라고 말씀해 주세요.')
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
