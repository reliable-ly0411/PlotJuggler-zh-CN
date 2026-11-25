#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Disposable hosted-Windows linked mutation for one MainWindow regression.

Only this CI source checkout is changed, then restored byte-for-byte and its
normal GUI runner rebuilt. An incomplete sentinel prevents later packaging.
Never run on the user's VM. This is a negative control, not a production build.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import xml.etree.ElementTree as ET

CASE_CLASS = 'MainWindowCustomWidgetTest'
CASE_NAME = 'WindowCloseClearsAnOrphanRecordInsideTheSurvivingFixtureRoot'
CASE = CASE_CLASS + '.' + CASE_NAME
FAILURE = 'clean-exit clear must remove an unowned record'


class MutationError(Exception):
    pass


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as source:
        for data in iter(lambda: source.read(1024 * 1024), b''):
            value.update(data)
    return value.hexdigest()


def mutant(original):
    lf = b'void ActiveWidgetsMarker::clear() {\n  live_.clear();\n  QFile::remove(path_);\n}'
    crlf = lf.replace(b'\n', b'\r\n')
    hits = [(needle, original.count(needle)) for needle in (lf, crlf)]
    chosen = [needle for needle, count in hits if count == 1]
    if len(chosen) != 1 or sum(count for _, count in hits) != 1:
        raise MutationError('cannot identify exactly one original marker-clear body')
    old = chosen[0]
    replacement = old.replace(b'QFile::remove(path_);', b'/* test-only mutation: preserve marker */')
    return original.replace(old, replacement, 1)


def check_case(xml_file, returncode, *, mutated):
    document = ET.parse(xml_file).getroot()
    cases = list(document.iter('testcase'))
    if len(cases) != 1 or cases[0].get('name') != CASE_NAME or cases[0].get('classname') != CASE_CLASS:
        raise MutationError('GTest did not report precisely the intended MainWindow case')
    case = cases[0]
    if case.get('status') != 'run' or case.find('skipped') is not None or list(document.iter('error')):
        raise MutationError('MainWindow case was not actually run')
    failures = case.findall('failure')
    if mutated:
        if returncode != 1 or len(failures) != 1:
            raise MutationError('mutant must produce exactly one genuine failing assertion')
        detail = (failures[0].get('message', '') + ' ' + ''.join(failures[0].itertext()))
        if (FAILURE not in detail or 'QFile::exists(marker_path_)' not in detail or
                'Actual: true' not in detail or 'Expected: false' not in detail):
            raise MutationError('mutant failed for a reason other than the surviving marker assertion')
    elif returncode != 0 or failures or list(document.iter('error')):
        raise MutationError('restored original MainWindow regression did not pass')


def require_same_ci_identity(actual, expected):
    """Compare reported token attributes, without claiming identical privileges."""
    if (not isinstance(actual, dict) or not isinstance(expected, dict) or
            not isinstance(actual.get('sid'), str) or not isinstance(expected.get('sid'), str) or
            actual['sid'].casefold() != expected['sid'].casefold() or
            any(type(actual.get(key)) is not int or type(expected.get(key)) is not int
                for key in ('session', 'integrity_rid')) or
            any(not isinstance(actual.get(key), str) or not isinstance(expected.get(key), str)
                for key in ('auth_luid', 'elevation_type')) or
            any(actual.get(key) != expected.get(key) for key in
                ('session', 'integrity_rid', 'auth_luid', 'elevation_type')) or
            type(actual.get('pid')) is not int or actual['pid'] <= 0):
        raise MutationError('actual CI process token attributes differ from the Qt probe context')


def validate_probe_identity(proof, actual):
    observed = {'pid': proof.get('pid'), 'sid': proof.get('user_sid'), 'session': proof.get('session'),
                'integrity_rid': proof.get('integrity_rid'), 'auth_luid': proof.get('auth_luid'),
                'elevation_type': proof.get('elevation_type')}
    require_same_ci_identity(observed, actual)


def load_token_reader():
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location('native_mutation_token_reader', Path(__file__).with_name('run_native_test_bundle.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_recorded(command, cwd, environment, output, phase, expected_identity, token_reader):
    stdout = output / (phase + '.stdout.bin')
    stderr = output / (phase + '.stderr.bin')
    argv = [str(x) for x in command]
    with stdout.open('xb') as out, stderr.open('xb') as err:
        with subprocess.Popen(argv, cwd=cwd, env=environment, stdin=subprocess.DEVNULL, stdout=out, stderr=err) as child:
            try:
                identity = token_reader.process_identity(int(child._handle), child.pid)
                require_same_ci_identity(identity, expected_identity)
            except Exception as exc:
                try:
                    child.terminate()
                except OSError:
                    pass
                child.wait()
                (output / (phase + '.process.json')).write_text(json.dumps({'argv': argv, 'cwd': str(cwd),
                    'exit_code': child.returncode, 'identity_status': 'unverified', 'outcome': 'uncertain'}) + '\n', encoding='utf-8')
                raise MutationError('child CI token was not verified; execution outcome may be uncertain') from exc
            code = child.wait()
    result = {'argv': argv, 'cwd': str(cwd), 'exit_code': code, 'identity': identity,
              'stdout_sha256': digest(stdout), 'stderr_sha256': digest(stderr)}
    (output / (phase + '.process.json')).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return result, stdout.read_bytes() + stderr.read_bytes()


def require_incremental_build(result, output):
    text = output.decode('utf-8', 'replace').casefold()
    if result['exit_code'] != 0 or not all(x in text for x in (
            'activewidgetsmarker.cpp.obj', 'pj_runtime.lib', 'pj_app_gui_tests.exe')):
        raise MutationError('incremental build did not compile the mutated/restored TU and relink its actual GUI runner')


def git(source, *args):
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith('GIT_')}
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='NUL', GIT_OPTIONAL_LOCKS='0',
               GIT_CONFIG_COUNT='1', GIT_CONFIG_KEY_0='core.fsmonitor', GIT_CONFIG_VALUE_0='false')
    result = subprocess.run(['git', '-C', str(source), *args], capture_output=True, env=env, check=False)
    if result.returncode:
        raise MutationError('cannot verify source Git identity')
    return result.stdout.decode('utf-8').strip()


def execute(root, output, source_sha, source_tree, qt_evidence, qt_core):
    if (sys.platform != 'win32' or os.environ.get('GITHUB_ACTIONS') != 'true' or
            os.environ.get('RUNNER_ENVIRONMENT') != 'github-hosted'):
        raise MutationError('this linked mutation runs only on a disposable GitHub-hosted Windows runner')
    root = root.resolve(strict=True)
    source, build = root / 's', root / 'b'
    marker = source / 'pj_runtime/src/ActiveWidgetsMarker.cpp'
    cmake = root / 't/cmake/bin/cmake.exe'
    runner = build / 'pj_app/RelWithDebInfo/pj_app_gui_tests.exe'
    qt_core = qt_core.resolve(strict=True)
    if (not qt_core.is_relative_to((root / 'q').resolve(strict=True)) or
            output.absolute() != build / 'native-kit/marker-mutation-evidence' or
            qt_evidence.absolute() != build / 'native-kit/ci-temp-probe-evidence/before-marker-mutation.stdout.bin'):
        raise MutationError('mutation inputs and evidence must stay in their exact owned CI directories')
    for path in (marker, cmake, runner, qt_core):
        info = path.lstat()
        if (not stat.S_ISREG(info.st_mode) or path.is_symlink() or info.st_nlink != 1 or
                getattr(info, 'st_file_attributes', 0) & 0x400):
            raise MutationError('mutation input must be one unlinked ordinary file: ' + str(path))
    if git(source, 'rev-parse', 'HEAD') != source_sha or git(source, 'rev-parse', 'HEAD^{tree}') != source_tree or git(source, 'status', '--porcelain=v1', '--untracked-files=all', '--ignore-submodules=none'):
        raise MutationError('mutation requires a clean checkout of the exact source commit and tree')
    proof = json.loads(qt_evidence.read_text(encoding='utf-8'))
    token_reader = load_token_reader()
    try:
        actual_identity = token_reader.current_identity()  # No impersonation; CI session 0 is allowed.
    except Exception as exc:
        raise MutationError('cannot read the current CI process token') from exc
    validate_probe_identity(proof, actual_identity)
    if (proof.get('scope') != 'disposable-windows-ci-only' or proof.get('qt_version') != '6.12.0' or
            Path(proof.get('qt_core', '')).resolve(strict=True) != qt_core.resolve(strict=True) or
            Path(proof.get('qt_temp', '')).resolve(strict=True) != Path(os.environ.get('TEMP', '')).resolve(strict=True) or
            os.environ.get('TEMP') != os.environ.get('TMP')):
        raise MutationError('same-token CI Qt temporary-path preflight is missing or differs')
    original = marker.read_bytes(); altered = mutant(original); original_sha = digest(marker)
    baseline_runner_sha = digest(runner)
    output.mkdir(parents=False, exist_ok=False)
    incomplete = output / 'INCOMPLETE'
    incomplete.write_text('Mutation or original rebuild has not been fully verified. Do not stage this build.\n', encoding='utf-8')
    build_cmd = [cmake, '--build', build, '--config', 'RelWithDebInfo', '--target', 'pj_app_gui_tests', '--parallel', '2']
    env = dict(os.environ)
    changed = False
    try:
        changed = True
        marker.write_bytes(altered)
        if digest(marker) == original_sha:
            raise MutationError('mutation did not change the source bytes')
        mutant_source_sha = digest(marker)
        result, log = run_recorded(build_cmd, root, env, output, 'mutant-build', actual_identity, token_reader)
        require_incremental_build(result, log)
        mutant_runner_sha = digest(runner)
        if mutant_runner_sha == baseline_runner_sha:
            raise MutationError('mutant linked runner did not change')
        report = output / 'mutant.xml'
        cmd = [runner, '--gtest_filter=' + CASE, '--gtest_color=no', '--gtest_output=xml:' + str(report)]
        result, _ = run_recorded(cmd, build / 'pj_app', env, output, 'mutant-test', actual_identity, token_reader)
        check_case(report, result['exit_code'], mutated=True)
    finally:
        if changed:
            marker.write_bytes(original)
            if digest(marker) != original_sha:
                raise MutationError('failed to restore the exact original source bytes')
    result, log = run_recorded(build_cmd, root, env, output, 'original-build', actual_identity, token_reader)
    require_incremental_build(result, log)
    restored_runner_sha = digest(runner)
    if restored_runner_sha == mutant_runner_sha:
        raise MutationError('restored GUI runner is still the mutant')
    report = output / 'original.xml'
    cmd = [runner, '--gtest_filter=' + CASE, '--gtest_color=no', '--gtest_output=xml:' + str(report)]
    result, _ = run_recorded(cmd, build / 'pj_app', env, output, 'original-test', actual_identity, token_reader)
    check_case(report, result['exit_code'], mutated=False)
    if digest(marker) != original_sha or git(source, 'status', '--porcelain=v1', '--untracked-files=all', '--ignore-submodules=none'):
        raise MutationError('source checkout was not restored cleanly after mutation')
    receipt = {'schema': 1, 'complete': True, 'scope': 'disposable-windows-ci-only',
               'source_sha': source_sha, 'source_tree': source_tree, 'case': CASE, 'ci_identity': actual_identity,
               'original_source_sha256': original_sha, 'mutated_source_sha256': mutant_source_sha,
               'baseline_runner_sha256': baseline_runner_sha, 'mutant_runner_sha256': mutant_runner_sha,
               'restored_runner_sha256': restored_runner_sha, 'qt_preflight_sha256': digest(qt_evidence)}
    (output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    incomplete.unlink()  # This script created this exact sentinel; no sweep or prefix deletion.
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'output', 'source-sha', 'source-tree', 'qt-evidence', 'qt-core'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    try:
        if len(args.source_sha) != 40 or len(args.source_tree) != 40 or any(c not in '0123456789abcdef' for c in args.source_sha + args.source_tree):
            raise MutationError('source identity must be full lowercase Git hashes')
        execute(Path(args.root), Path(args.output), args.source_sha, args.source_tree, Path(args.qt_evidence), Path(args.qt_core))
        return 0
    except (OSError, ValueError, MutationError, ET.ParseError) as exc:
        print('linked marker mutation failed: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
