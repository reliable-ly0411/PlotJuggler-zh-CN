#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Run a verified same-root native test kit in the approved Windows session.

CTest remains the test executor. Its own stdout/stderr are stored as raw bytes;
CTest combines each child test's stdout/stderr. This launcher does not claim to
recover the original child streams. A separate host safety review is required
before invoking it, especially for shared Qt and application state.
"""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import stat
import sys
import uuid
import xml.etree.ElementTree as ET

# Neither this launcher nor its loaded audit modules should create bytecode in
# the immutable source tree before the kit snapshot is verified.
sys.dont_write_bytecode = True

spec = importlib.util.spec_from_file_location('native_bundle_audit', Path(__file__).with_name('native_bundle_audit.py'))
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
review_spec = importlib.util.spec_from_file_location('native_test_review', Path(__file__).with_name('native_test_review.py'))
review = importlib.util.module_from_spec(review_spec)
review_spec.loader.exec_module(review)


class LauncherError(Exception):
    """An identity, input or test-execution condition could not be proven."""


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def root_path(root, relative, *, file=False, directory=False):
    """Resolve a declared existing input without accepting an external path."""
    audit.check_windows_relative(relative, str(root))
    candidate = Path(root).joinpath(*relative.split('/'))
    resolved = candidate.resolve(strict=True)
    if not resolved.is_relative_to(Path(root).resolve(strict=True)):
        raise LauncherError('a declared path leaves the verified kit root')
    if file and not resolved.is_file() or directory and not resolved.is_dir():
        raise LauncherError('a declared input has the wrong type')
    return resolved


def check_driver_import_paths(root, system_path=None):
    """Verify the pinned embedded Python's actual isolated import path."""
    root = Path(root).resolve(strict=True)
    python_dir = root / 't/python'
    pth = python_dir / 'python312._pth'
    expected = [python_dir / 'python312.zip', python_dir, root / 's', root / 's/scripts',
                root / 's/tests', root / 's/packaging/localization']
    if not pth.is_file():
        raise LauncherError('the authenticated embedded Python path file is missing')
    def normalize(path):
        return os.path.normcase(os.path.normpath(str(Path(path).resolve(strict=True))))
    declared = []
    for line in pth.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('import '):
            raise LauncherError('embedded Python path file may not execute site imports')
        path = Path(line)
        declared.append(normalize(path if path.is_absolute() else python_dir / path))
    expected_paths = [normalize(path) for path in expected]
    actual_paths = [normalize(path) for path in (sys.path if system_path is None else system_path)]
    if declared != expected_paths or actual_paths != expected_paths:
        raise LauncherError('embedded Python declared or actual import paths differ from the same-root allowlist')


def process_identity(process_handle, pid):
    """Read the exact Windows primary-token SID, session and integrity RID."""
    if sys.platform != 'win32':
        raise LauncherError('Windows process-token identity is unavailable')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    advapi = ctypes.WinDLL('advapi32', use_last_error=True)
    kernel.ProcessIdToSessionId.argtypes = [wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    kernel.ProcessIdToSessionId.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [wintypes.HLOCAL]
    kernel.LocalFree.restype = wintypes.HLOCAL
    advapi.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    advapi.OpenProcessToken.restype = wintypes.BOOL
    advapi.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID,
                                           wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    advapi.GetTokenInformation.restype = wintypes.BOOL
    advapi.ConvertSidToStringSidW.argtypes = [wintypes.LPVOID, ctypes.POINTER(wintypes.LPWSTR)]
    advapi.ConvertSidToStringSidW.restype = wintypes.BOOL
    advapi.GetSidSubAuthorityCount.argtypes = [wintypes.LPVOID]
    advapi.GetSidSubAuthorityCount.restype = ctypes.POINTER(ctypes.c_ubyte)
    advapi.GetSidSubAuthority.argtypes = [wintypes.LPVOID, wintypes.DWORD]
    advapi.GetSidSubAuthority.restype = ctypes.POINTER(wintypes.DWORD)

    class SidAndAttributes(ctypes.Structure):
        _fields_ = [('sid', wintypes.LPVOID), ('attributes', wintypes.DWORD)]

    class Luid(ctypes.Structure):
        _fields_ = [('low', wintypes.DWORD), ('high', wintypes.LONG)]

    class TokenStatistics(ctypes.Structure):
        _fields_ = [('token_id', Luid), ('authentication_id', Luid), ('expiration_time', ctypes.c_longlong),
                    ('token_type', ctypes.c_int), ('impersonation_level', ctypes.c_int),
                    ('dynamic_charged', wintypes.DWORD), ('dynamic_available', wintypes.DWORD),
                    ('group_count', wintypes.DWORD), ('privilege_count', wintypes.DWORD), ('modified_id', Luid)]

    def read_token(token, kind):
        needed = wintypes.DWORD()
        advapi.GetTokenInformation(token, kind, None, 0, ctypes.byref(needed))
        if ctypes.get_last_error() != 122 or not needed.value:  # ERROR_INSUFFICIENT_BUFFER
            raise LauncherError('cannot size the process token information')
        buffer = ctypes.create_string_buffer(needed.value)
        if not advapi.GetTokenInformation(token, kind, buffer, needed.value, ctypes.byref(needed)):
            raise LauncherError('cannot read the process token information')
        return buffer

    session = wintypes.DWORD()
    if not kernel.ProcessIdToSessionId(pid, ctypes.byref(session)):
        raise LauncherError('cannot read process session')
    token = wintypes.HANDLE()
    if not advapi.OpenProcessToken(process_handle, 0x0008, ctypes.byref(token)):
        raise LauncherError('cannot open process token')
    try:
        user_buffer = read_token(token, 1)  # TokenUser
        integrity_buffer = read_token(token, 25)  # TokenIntegrityLevel
        statistics_buffer = read_token(token, 10)  # TokenStatistics
        elevation_buffer = read_token(token, 18)  # TokenElevationType
        user = ctypes.cast(user_buffer, ctypes.POINTER(SidAndAttributes)).contents
        label = ctypes.cast(integrity_buffer, ctypes.POINTER(SidAndAttributes)).contents
        sid_text = wintypes.LPWSTR()
        if not advapi.ConvertSidToStringSidW(user.sid, ctypes.byref(sid_text)):
            raise LauncherError('cannot render process SID')
        try:
            sid = sid_text.value
        finally:
            kernel.LocalFree(ctypes.cast(sid_text, wintypes.HLOCAL))
        count_ptr = advapi.GetSidSubAuthorityCount(label.sid)
        if not count_ptr or not count_ptr.contents.value:
            raise LauncherError('invalid process integrity SID')
        rid_ptr = advapi.GetSidSubAuthority(label.sid, count_ptr.contents.value - 1)
        if not rid_ptr:
            raise LauncherError('cannot read process integrity RID')
        stats = ctypes.cast(statistics_buffer, ctypes.POINTER(TokenStatistics)).contents
        elevation_value = ctypes.cast(elevation_buffer, ctypes.POINTER(ctypes.c_int)).contents.value
        elevation = {1: 'default', 2: 'full', 3: 'limited'}.get(elevation_value)
        if elevation is None:
            raise LauncherError('unknown process token elevation type')
        auth_luid = f'{stats.authentication_id.high & 0xffffffff:08x}:{stats.authentication_id.low:08x}'
        return {'pid': int(pid), 'session': int(session.value), 'sid': sid, 'integrity_rid': int(rid_ptr.contents.value),
                'auth_luid': auth_luid, 'elevation_type': elevation}
    finally:
        kernel.CloseHandle(token)


def current_identity():
    if sys.platform != 'win32':
        raise LauncherError('this launcher requires Windows')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    advapi = ctypes.WinDLL('advapi32', use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.GetCurrentThread.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    advapi.OpenThreadToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.BOOL, ctypes.POINTER(wintypes.HANDLE)]
    advapi.OpenThreadToken.restype = wintypes.BOOL
    token = wintypes.HANDLE()
    if advapi.OpenThreadToken(kernel.GetCurrentThread(), 0x0008, True, ctypes.byref(token)):
        kernel.CloseHandle(token)
        raise LauncherError('launcher thread is impersonating another identity')
    if ctypes.get_last_error() != 1008:  # ERROR_NO_TOKEN
        raise LauncherError('cannot establish whether the launcher thread is impersonating')
    return process_identity(kernel.GetCurrentProcess(), os.getpid())


def require_identity(actual, expected):
    if (not isinstance(actual, dict) or not isinstance(expected, dict) or
            any(type(actual.get(key)) is not int or type(expected.get(key)) is not int
                for key in ('session', 'integrity_rid')) or
            not isinstance(actual.get('sid'), str) or not isinstance(expected.get('sid'), str) or
            actual['session'] == 0 or actual['sid'].upper() in {'S-1-5-18', 'S-1-5-19', 'S-1-5-20'} or
            actual['session'] != expected['session'] or actual['sid'].upper() != expected['sid'].upper() or
            actual['integrity_rid'] != expected['integrity_rid'] or
            any(actual.get(key) != expected[key] for key in ('auth_luid', 'elevation_type') if key in expected)):
        raise LauncherError('actual process SID, session or integrity does not match the approved interactive token')


def same_discovery(expected, actual):
    """Compare the complete ordered case list, command and CTest properties."""
    def projection(doc):
        if not isinstance(doc, dict) or doc.get('kind') != 'ctestInfo' or not isinstance(doc.get('tests'), list):
            raise LauncherError('invalid CTest discovery document')
        records = []
        names = set()
        for test in doc['tests']:
            if (not isinstance(test, dict) or not isinstance(test.get('name'), str) or
                    test['name'] in names or not isinstance(test.get('command'), list) or
                    not test['command'] or not isinstance(test.get('properties'), list)):
                raise LauncherError('missing, duplicate or malformed CTest registration')
            names.add(test['name'])
            records.append({key: test.get(key) for key in ('name', 'config', 'command', 'properties')})
        return records
    if not projection(expected) or projection(expected) != projection(actual):
        raise LauncherError('target CTest registrations differ from the verified build')


def generated_ctest_outputs(suites, full_docs=None, prepared=None, logical_root=None, root=None):
    """Exact CTest bookkeeping plus the selected, reviewed QtTest text file."""
    files, directories = set(), set()
    for suite in suites:
        tree = suite['tree'].rstrip('/')
        temporary = tree + '/Testing/Temporary'
        directories.update((tree + '/Testing', temporary))
        files.update(temporary + '/' + name for name in ('LastTest.log', 'LastTestsFailed.log',
                     'LastTestsDisabled.log', 'CTestCostData.txt', 'CTestCheckpoint.txt'))
        if full_docs is None or prepared is None:
            continue
        name = 'pj_bundled_translations_test'
        if name not in prepared[suite['id']]['selected']:
            continue
        if suite['id'] not in ('main', 'i18n') or logical_root is None or root is None:
            raise LauncherError('bundled QtTest output is only approved in its actual main or i18n tree')
        test = review.indexed(full_docs[suite['id']])[name][0]
        absolute = audit.bundled_qttest_output(test, logical_root)
        relative = audit.to_relative(absolute, logical_root)
        target = temporary + '/bundled-translations.txt'
        if relative.casefold() != target.casefold():
            raise LauncherError('bundled QtTest output does not belong to its selected suite tree')
        contract_path = suite.get('allowed_outputs')
        if not isinstance(contract_path, str):
            raise LauncherError('selected bundled QtTest requires an immutable per-case output contract')
        contract = audit.read_json(root_path(root, contract_path, file=True))
        declared = contract.get(name) if isinstance(contract, dict) else None
        if (not isinstance(declared, list) or len(declared) != 1 or not isinstance(declared[0], str) or
                audit.to_relative(declared[0], logical_root).casefold() != target.casefold()):
            raise LauncherError('bundled QtTest output contract does not name the exact selected output')
        files.add(target)
    return {'files': files, 'directories': directories}


def check_immutable(root, manifest, generated=None, manifest_path=None):
    """Re-inventory the entire kit, allowing only exact owned CTest outputs.

    This catches cross-suite additions, not same-suite loader contamination;
    the latter still requires source/fixture review before that group runs.
    """
    logical = manifest['logical_root']
    internal = manifest_path is not None and Path(manifest_path).absolute() == root / '_bundle/manifest.json'
    snapshot = audit.inventory(root, logical, exclude_manifest=internal, ignore_owned_runs=True)
    generated = generated or {'files': set(), 'directories': set()}
    allowed_files, allowed_dirs = generated['files'], generated['directories']
    expected = manifest['files']
    expected_names = {entry['path'] for entry in expected}
    if expected_names & allowed_files:
        raise LauncherError('a mutable CTest output was incorrectly included as an immutable input')
    extra_files = [entry for entry in snapshot['files'] if entry['path'] not in expected_names]
    if any(entry['path'] not in allowed_files for entry in extra_files):
        raise LauncherError('an unapproved file was added to the kit: ' +
                            next(entry['path'] for entry in extra_files if entry['path'] not in allowed_files))
    protected_files = [entry for entry in snapshot['files'] if entry['path'] in expected_names]
    if protected_files != expected:
        raise LauncherError('an immutable manifest input changed or disappeared')
    expected_dirs = set(manifest['directories'])
    actual_dirs = set(snapshot['directories'])
    if not expected_dirs <= actual_dirs or not (actual_dirs - expected_dirs) <= allowed_dirs:
        raise LauncherError('the payload directory set changed outside exact CTest bookkeeping directories')
    return {'owned_generated_files': [entry['path'] for entry in extra_files],
            'owned_generated_directories': sorted(actual_dirs - expected_dirs)}


def restore_verified_mtimes(root, manifest):
    """Restore only authenticated original file timestamps after byte verification."""
    changed = []
    for entry in manifest['files']:
        path = root_path(root, entry['path'], file=True)
        info = path.stat()
        original = entry['mtime_ns']
        if info.st_mtime_ns != original:
            os.utime(path, ns=(info.st_atime_ns, original))
            if path.stat().st_mtime_ns != original:
                raise LauncherError('could not restore the authenticated file timestamp: ' + entry['path'])
            changed.append({'path': entry['path'], 'extracted_mtime_ns': info.st_mtime_ns,
                            'original_mtime_ns': original})
    return changed


def validate_plan(plan, source_sha, source_tree, config):
    if not isinstance(plan, dict) or plan.get('schema') != 1 or plan.get('source_sha') != source_sha or \
            plan.get('source_tree') != source_tree or plan.get('configuration') != config:
        raise LauncherError('run plan source or configuration differs from the verified kit')
    paths, suites = plan.get('paths'), plan.get('suites')
    if not isinstance(paths, dict) or not isinstance(suites, list) or not suites:
        raise LauncherError('run plan paths or suites are missing')
    for name in ('python', 'ctest', 'probe', 'qt', 'fonts', 'feedback'):
        if not isinstance(paths.get(name), str) or not paths[name]:
            raise LauncherError('run plan is missing path: ' + name)
    runtime = plan.get('runtime_dirs')
    if not isinstance(runtime, list) or not runtime or any(not isinstance(x, str) or not x for x in runtime):
        raise LauncherError('run plan must identify runtime DLL directories')
    ids = []
    for suite in suites:
        if not isinstance(suite, dict) or not isinstance(suite.get('id'), str) or \
                not suite['id'].replace('-', '').isalnum() or suite.get('kind') not in ('ctest', 'csv'):
            raise LauncherError('invalid suite record')
        if not all(isinstance(suite.get(k), str) for k in ('tree', 'discovery', 'full_discovery')):
            raise LauncherError('each suite needs a test tree, selected and complete discovery files')
        if suite['id'] in ('main', 'i18n', 'csv-runtime') and not isinstance(suite.get('build_identity'), str):
            raise LauncherError('main, i18n and CSV each need a captured build identity')
        if suite.get('platform') not in (None, 'windows'):
            raise LauncherError('unknown Qt platform override')
        if suite['id'] == 'file-dialog':
            if suite.get('platform') != 'windows' or not suite.get('pattern'):
                raise LauncherError('native file-dialog repetition requires its explicit selection and platform')
        elif suite.get('platform') is not None:
            raise LauncherError('the Qt platform may be overridden only for the file-dialog repetition')
        if suite['id'] in ('main', 'i18n') and suite.get('pattern') is not None:
            raise LauncherError('main and i18n must include every registered test')
        if suite['id'] == 'csv-runtime' and suite.get('pattern') != '^CsvRuntimeFileLoader_':
            raise LauncherError('CSV runtime needs its explicit three-language selection')
        if suite.get('pattern') is not None and not isinstance(suite['pattern'], str):
            raise LauncherError('invalid CTest selection regex')
        if suite['kind'] == 'csv' and not all(isinstance(suite.get(k), str) for k in ('prefix', 'identity')):
            raise LauncherError('CSV suite needs its staged plugin prefix and prebuilt identity')
        ids.append(suite['id'])
    if len(ids) != len(set(ids)) or not {'main', 'i18n', 'file-dialog', 'csv-runtime'}.issubset(ids):
        raise LauncherError('main, i18n, file-dialog and CSV runtime suite identities are required')
    kinds = {item['id']: item['kind'] for item in suites}
    if any(kinds[x] != 'ctest' for x in ('main', 'i18n', 'file-dialog')) or kinds['csv-runtime'] != 'csv':
        raise LauncherError('required suite types do not match their coverage contracts')
    by_id = {item['id']: item for item in suites}
    if (by_id['main']['tree'].casefold() == by_id['i18n']['tree'].casefold() or
            by_id['main']['full_discovery'].casefold() == by_id['i18n']['full_discovery'].casefold() or
            by_id['main']['build_identity'].casefold() == by_id['i18n']['build_identity'].casefold()):
        raise LauncherError('main and standalone i18n must have separate builds, discovery and identities')
    if (by_id['file-dialog']['tree'].casefold() != by_id['main']['tree'].casefold() or
            by_id['file-dialog']['full_discovery'].casefold() != by_id['main']['full_discovery'].casefold()):
        raise LauncherError('file-dialog repetition must use the main build and full discovery')
    csv, main = by_id['csv-runtime'], by_id['main']
    if csv['tree'].casefold() == main['tree'].casefold():
        if (csv['full_discovery'].casefold() != main['full_discovery'].casefold() or
                csv['build_identity'].casefold() != main['build_identity'].casefold()):
            raise LauncherError('CSV repetition on the main tree must use its exact discovery and identity')
    elif (csv['tree'].casefold() == by_id['i18n']['tree'].casefold() or
          csv['full_discovery'].casefold() in (main['full_discovery'].casefold(), by_id['i18n']['full_discovery'].casefold()) or
          csv['build_identity'].casefold() in (main['build_identity'].casefold(), by_id['i18n']['build_identity'].casefold())):
        raise LauncherError('an independent CSV tree needs its own full discovery and build identity')
    return paths, runtime, suites


def validate_plan_bindings(paths, runtime_dirs, suites, manifest):
    """Prevent a plan from executing or loading unmanifested run-output files."""
    files = {x['path'].casefold() for x in manifest['files']}
    directories = {x.casefold() for x in manifest['directories']}
    inputs = list(paths.values()) + list(runtime_dirs)
    for suite in suites:
        inputs.extend(suite[key] for key in ('tree', 'discovery', 'full_discovery', 'build_identity', 'prefix', 'identity', 'allowed_outputs')
                      if isinstance(suite.get(key), str))
    if any(path.casefold() == 'r' or path.casefold().startswith('r/') for path in inputs):
        raise LauncherError('owned run outputs cannot be used as immutable test inputs')
    for key in ('python', 'ctest', 'probe'):
        if paths[key].casefold() not in files:
            raise LauncherError('run plan executable is absent from the verified manifest: ' + key)
    app_keys = ('app_guard_probe', 'app_guard_validation', 'application')
    if any(key in paths for key in app_keys):
        if any(not isinstance(paths.get(key), str) or paths[key].casefold() not in files for key in app_keys):
            raise LauncherError('optional real-App guard inputs must all be immutable manifest files')
    for key in ('qt', 'fonts', 'feedback'):
        if paths[key].casefold() not in directories:
            raise LauncherError('run plan directory is absent from the verified manifest: ' + key)
    if (paths['qt'].rstrip('/') + '/bin/Qt6Core.dll').casefold() not in files:
        raise LauncherError('Qt Core runtime is absent from the verified manifest')
    driver_directory = str(PurePosixPath(paths['python']).parent).casefold().rstrip('/')
    for path in runtime_dirs:
        if path.casefold() not in directories:
            raise LauncherError('a runtime DLL directory is not an immutable manifest directory')
        if path.casefold() == driver_directory or path.casefold().startswith(driver_directory + '/'):
            raise LauncherError('the isolated driver Python directory cannot be a test DLL search path')
    for suite in suites:
        if (suite['tree'].casefold() not in directories or suite['discovery'].casefold() not in files or
                suite['full_discovery'].casefold() not in files):
            raise LauncherError('a suite tree or discovery file is absent from the verified manifest')
        if suite['kind'] == 'csv' and (suite['prefix'].casefold() not in directories or suite['identity'].casefold() not in files):
            raise LauncherError('CSV prefix or prebuilt identity is not bound by the manifest')
        if suite['id'] in ('main', 'i18n', 'csv-runtime') and suite['build_identity'].casefold() not in files:
            raise LauncherError('build identity is absent from the verified manifest')
        allowed = suite.get('allowed_outputs')
        if allowed is not None and (not isinstance(allowed, str) or allowed.casefold() not in files):
            raise LauncherError('suite output exception list is not bound by the manifest')


def load_source_module(root, relative, module_name):
    """Load a source module only after its bytes are covered by the manifest."""
    path = root_path(root, relative, file=True)
    source_spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(source_spec)
    source_spec.loader.exec_module(module)
    return module


def check_build_identity(root, suite, source_sha, source_tree, config, main_tree):
    if suite['id'] not in ('main', 'i18n', 'csv-runtime'):
        return
    record = audit.read_json(root_path(root, suite['build_identity'], file=True))
    role = 'main' if suite['id'] == 'csv-runtime' and suite['tree'].casefold() == main_tree.casefold() else suite['id']
    expected = {'schema': 1, 'role': role, 'source_sha': source_sha, 'source_tree': source_tree,
                'configuration': config, 'source_dir': 's/pj_app/tests/i18n' if suite['id'] == 'i18n' else 's',
                'build_tree': suite['tree'], 'native_bundle_mode': True}
    if (not isinstance(record, dict) or record.get('native_bundle_mode') is not True or
            any(record.get(k) != v for k, v in expected.items())):
        raise LauncherError('independent build identity does not match its source and test tree: ' + suite['id'])
    if not audit.HEX64.fullmatch(str(record.get('cmake_cache_sha256', ''))):
        raise LauncherError('build identity is missing the original CI CMakeCache SHA-256')


def check_suite_contract(root, suite, baseline):
    names = [test.get('name') for test in baseline.get('tests', [])]
    if suite['id'] == 'main' and 'RuntimeCatalogLanguageTest' not in names:
        raise LauncherError('the new runtime catalog language regression is not registered')
    if suite['id'] == 'file-dialog':
        module = load_source_module(root, 's/packaging/localization/audit_file_dialog_results.py', 'file_dialog_gate')
        if len(names) != len(set(names)) or set(names) != module.CASES:
            raise LauncherError('native file-dialog selection differs from its source contract')
    if suite['id'] == 'csv-runtime':
        module = load_source_module(root, 's/packaging/localization/run_csv_runtime_acceptance.py', 'csv_runtime_gate')
        if len(names) != len(set(names)) or set(names) != module.EXPECTED:
            raise LauncherError('CSV runtime selection differs from its source contract')


def write_json_new(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as output:
        json.dump(value, output, indent=2, ensure_ascii=False, sort_keys=True)
        output.write('\n')


def run_process(argv, cwd, environment, stdout_file, stderr_file, expected, timeout):
    """Record CTest's own streams and verify the child process primary token."""
    started = datetime.now(timezone.utc).isoformat()
    with Path(stdout_file).open('xb') as stdout, Path(stderr_file).open('xb') as stderr:
        proc = subprocess.Popen([str(x) for x in argv], cwd=str(cwd), env=environment,
                                stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr)
        try:
            identity = process_identity(int(proc._handle), proc.pid)  # Popen owns this exact process handle.
            require_identity(identity, expected)
        except Exception:
            # This handle belongs only to the just-created process. Its outcome
            # may be uncertain if it started work before a token mismatch was seen.
            proc.terminate()
            raise LauncherError('child token could not be verified; process outcome may be uncertain') from None
        try:
            code = proc.wait(timeout=timeout)
            pending = False
        except subprocess.TimeoutExpired:
            # Do not kill an unverified descendant process tree. The caller must
            # treat this as a live-process blocker and retain the logs.
            code, pending = None, True
    return {'argv': [str(x) for x in argv], 'cwd': str(cwd), 'identity': identity,
            'started_utc': started, 'exit_code': code, 'still_running': pending,
            'stdout_sha256': None if pending else sha256(stdout_file),
            'stderr_sha256': None if pending else sha256(stderr_file)}


def checked_system_powershell(windows, expected):
    if not audit.HEX64.fullmatch(expected):
        raise LauncherError('Windows PowerShell identity must be a full SHA-256')
    shell = windows / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    for part in (shell, *shell.parents):
        info = part.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise LauncherError('Windows PowerShell path contains a link or reparse point')
        if part == windows:
            break
    info = shell.lstat()
    if not stat.S_ISREG(info.st_mode) or sha256(shell) != expected:
        raise LauncherError('independently reviewed Windows PowerShell does not match the host file')
    return shell


def test_runtime_search_path(windows, qt, ctest, dll_dirs, system_tools, python):
    """Do not expose the driver Python DLLs to native test processes via PATH.

    The verified driver and test scripts use an absolute executable path; the
    driver's own application directory remains available to Windows. Actual
    subprocess commands and per-executable PE closure must still be verified.
    """
    python_directory = Path(python).parent.resolve(strict=True)
    directories = [*(Path(x) for x in system_tools), Path(qt) / 'bin', Path(ctest).parent,
                   *(Path(x) for x in dll_dirs), Path(windows) / 'System32', Path(windows)]
    for directory in directories:
        resolved = directory.resolve(strict=True)
        if resolved == python_directory or python_directory in resolved.parents:
            raise LauncherError('test PATH must not include the driver Python directory')
    return os.pathsep.join(str(item) for item in directories)


def clean_environment(root, run_root, plan_paths, runtime_dirs, create=True, powershell_sha256=None):
    """Construct only the variables needed by this test process tree."""
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetWindowsDirectoryW.argtypes = [wintypes.LPWSTR, wintypes.UINT]
    kernel.GetWindowsDirectoryW.restype = wintypes.UINT
    buffer = ctypes.create_unicode_buffer(32768)
    length = kernel.GetWindowsDirectoryW(buffer, len(buffer))
    if not length or length >= len(buffer):
        raise LauncherError('cannot identify the Windows system directory')
    windows = Path(buffer.value)
    qt = root_path(root, plan_paths['qt'], directory=True)
    python = root_path(root, plan_paths['python'], file=True)
    ctest = root_path(root, plan_paths['ctest'], file=True)
    fonts = root_path(root, plan_paths['fonts'], directory=True)
    feedback = root_path(root, plan_paths['feedback'], directory=True)
    dll_dirs = [root_path(root, item, directory=True) for item in runtime_dirs]
    system_tools = []
    if powershell_sha256 is not None:
        shell = checked_system_powershell(windows, powershell_sha256)
        if (windows / 'System32/pwsh.exe').exists() or (windows / 'pwsh.exe').exists():
            raise LauncherError('an unreviewed PowerShell executable could shadow the approved system tool')
        system_tools.append(str(shell.parent))
    temp = run_root / 'tmp'
    profile = run_root / 'profile'
    roaming, local = profile / 'roaming', profile / 'local'
    screenshots = run_root / 'screenshots'
    app_guard = run_root / 'app-guard'
    if create:
        for directory in (temp, profile, roaming, local, screenshots, app_guard):
            directory.mkdir()
    for directory in (temp, profile, roaming, local, screenshots, app_guard):
        info = directory.lstat()
        if not directory.is_dir() or stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise LauncherError('run environment contains a linked or missing directory')
    path = test_runtime_search_path(windows, qt, ctest, dll_dirs, system_tools, python)
    env = {'SystemRoot': str(windows), 'WINDIR': str(windows), 'PATH': path,
           'TEMP': str(temp), 'TMP': str(temp), 'USERPROFILE': str(profile),
           'APPDATA': str(roaming), 'LOCALAPPDATA': str(local),
           'QT_QPA_FONTDIR': str(fonts), 'PJ_GUI_ACCEPTANCE_DIR': str(screenshots),
           'PJ_FEEDBACK_PLUGIN_DIR': str(feedback),
           'PJ_APBIN_TEST_DIR': str(feedback / 'ardupilot-dataflash'),
           'PJ_DISABLE_TELEMETRY': '1', 'PJ_REQUIRE_GPU_TESTS': '1',
           'PYTHONDONTWRITEBYTECODE': '1'}
    return env, qt, python, ctest


def driver_probe_command(root, manifest, python, manifest_path, manifest_sha256):
    """Use only the source-bound driver identity probe and absolute Python."""
    relative = 's/scripts/windows/native_driver_python_probe.py'
    if relative.casefold() not in {item['path'].casefold() for item in manifest['files']}:
        raise LauncherError('the driver identity probe is not bound by the manifest')
    script = root_path(root, relative, file=True)
    return [str(python), '-I', '-B', str(script), '--root', str(root), '--manifest', str(manifest_path),
            '--manifest-sha256', manifest_sha256]


def validate_driver_probe(evidence, manifest, root, manifest_sha256, process):
    """Bind actual child PID, version and loaded files to the immutable kit."""
    if (not isinstance(evidence, dict) or type(evidence.get('schema')) is not int or evidence['schema'] != 1 or
            evidence.get('scope') != 'isolated-driver-python' or
            evidence.get('manifest_sha256') != manifest_sha256 or type(evidence.get('pid')) is not int or
            not isinstance(process, dict) or not isinstance(process.get('identity'), dict) or
            type(process['identity'].get('pid')) is not int or
            evidence['pid'] != process['identity'].get('pid')):
        raise LauncherError('driver identity evidence does not match the actual child')
    tools = [x for x in manifest['provenance']['tools'] if isinstance(x, dict) and x.get('name') == 'python']
    if len(tools) != 1 or evidence.get('version') != tools[0].get('version'):
        raise LauncherError('driver Python version differs from the authenticated tool')
    if (not isinstance(evidence.get('prefix'), str) or
            Path(evidence['prefix']).resolve(strict=True) != (Path(root) / 't/python').resolve(strict=True)):
        raise LauncherError('driver Python prefix is outside its authenticated distribution')
    files = {x['path'].casefold(): x for x in manifest['files']}
    def check(row):
        if (not isinstance(row, dict) or not isinstance(row.get('path'), str) or
                row['path'].casefold() not in files or files[row['path'].casefold()]['path'] != row['path'] or
                row.get('sha256') != files[row['path'].casefold()]['sha256']):
            raise LauncherError('driver loaded file is not bound by the manifest')
        return row['path']
    if (check(evidence.get('executable')) != 't/python/python.exe' or
            check(evidence.get('stdlib')) != 't/python/python312.zip' or
            check(evidence.get('tool_pins')) != 's/.github/windows-native-kit/tool-pins.json'):
        raise LauncherError('driver executable, stdlib or tool pins differ')
    modules, dlls = evidence.get('modules'), evidence.get('loaded_dlls')
    if not isinstance(modules, list) or not isinstance(dlls, list):
        raise LauncherError('driver module evidence is missing')
    if len(modules) != 3 or {check(x) for x in modules} != {
            't/python/_ctypes.pyd', 't/python/_ssl.pyd', 't/python/_sqlite3.pyd'}:
        raise LauncherError('driver native extension evidence is incomplete')
    loaded_paths = [check(x) for x in dlls]
    if any(not path.startswith('t/python/') for path in loaded_paths):
        raise LauncherError('driver native library was loaded outside its official distribution')
    loaded = [path.rsplit('/', 1)[-1] for path in loaded_paths]
    patterns = (r'python312\.dll', r'libcrypto[^/]*\.dll', r'libssl[^/]*\.dll',
                r'libffi[^/]*\.dll', r'sqlite3\.dll')
    if len(loaded) != len(patterns) or any(sum(bool(re.fullmatch(p, x, re.I)) for x in loaded) != 1 for p in patterns):
        raise LauncherError('driver native library evidence is incomplete or ambiguous')
    return evidence


def load_context(args, *, restore):
    if sys.platform != 'win32':
        raise LauncherError('this launcher requires Windows')
    root = Path(args.root).absolute()
    expected = {'session': args.session, 'sid': args.sid, 'integrity_rid': args.integrity,
                'auth_luid': args.auth_luid, 'elevation_type': args.elevation_type}
    require_identity(current_identity(), expected)
    manifest_path = Path(args.manifest).absolute()
    audit.verify_manifest(root, manifest_path, False, args.manifest_sha256, args.expected_root,
                          args.source_sha, args.source_tree, args.config, allow_owned_runs=True)
    manifest = audit.read_json(manifest_path)
    restored = restore_verified_mtimes(root, manifest) if restore else []
    audit.verify_manifest(root, manifest_path, True, args.manifest_sha256, args.expected_root,
                          args.source_sha, args.source_tree, args.config, allow_owned_runs=True)
    plan_path = root_path(root, args.plan, file=True)
    relative_plan = plan_path.relative_to(root.resolve()).as_posix().casefold()
    if relative_plan not in {entry['path'].casefold() for entry in manifest['files']}:
        raise LauncherError('run plan is not bound by the verified manifest')
    plan = audit.read_json(plan_path)
    paths, runtime_dirs, suites = validate_plan(plan, args.source_sha, args.source_tree, args.config)
    if plan.get('qt_version') != manifest['provenance']['qt']:
        raise LauncherError('run plan Qt version differs from the verified manifest')
    validate_plan_bindings(paths, runtime_dirs, suites, manifest)
    driver = root_path(root, paths['python'], file=True)
    if Path(sys.executable).resolve() != driver or not sys.flags.isolated or not sys.flags.dont_write_bytecode:
        raise LauncherError('launcher must use the verified driver Python with -I -B')
    check_driver_import_paths(root)
    return root, expected, manifest, plan_path, plan, paths, runtime_dirs, suites, restored


def preflight(args):
    """Only an immutable QtCore identity/temp probe runs before review."""
    root, expected, manifest, plan_path, plan, paths, runtime_dirs, _, restored = load_context(args, restore=True)
    run_parent = root_path(root, 'r', directory=True)
    run_root = run_parent / ('run-' + uuid.uuid4().hex)
    run_root.mkdir()
    write_json_new(run_root / 'run-identity.json', {'schema': 1, 'source_sha': args.source_sha,
                   'source_tree': args.source_tree, 'configuration': args.config, 'run_root': str(run_root),
                   'status': 'preflight-started'})
    print(json.dumps({'run_root': str(run_root), 'status': 'preflight-started'}, ensure_ascii=False), flush=True)
    write_json_new(run_root / 'restored-mtimes.json', restored)
    env, qt, _, _ = clean_environment(root, run_root, paths, runtime_dirs, powershell_sha256=args.windows_powershell_sha256)
    probe = root_path(root, paths['probe'], file=True)
    qt_core = (qt / 'bin/Qt6Core.dll').resolve(strict=True)
    probe_cmd = [probe, '--run-root', run_root, '--temp', run_root / 'tmp', '--session', str(args.session),
                 '--sid', args.sid, '--integrity', str(args.integrity), '--qt', plan['qt_version'], '--qt-core', qt_core]
    write_json_new(run_root / 'environment.json', env)
    probe_result = run_process(probe_cmd, root, env, run_root / 'probe.stdout.bin', run_root / 'probe.stderr.bin',
                               expected, 120)
    write_json_new(run_root / 'probe-process.json', probe_result)
    if probe_result['still_running'] or probe_result['exit_code'] != 0:
        raise LauncherError('Qt temp/identity probe failed or remains running; no CTest suite was started')
    probe_evidence = json.loads((run_root / 'probe.stdout.bin').read_text(encoding='utf-8'))
    if (probe_evidence.get('session') != args.session or probe_evidence.get('user_sid', '').upper() != args.sid.upper() or
            probe_evidence.get('integrity_rid') != args.integrity):
        raise LauncherError('Qt probe evidence differs from the approved interactive identity')
    check_immutable(root, manifest, manifest_path=args.manifest)
    driver_cmd = driver_probe_command(root, manifest, root_path(root, paths['python'], file=True),
                                      args.manifest, args.manifest_sha256)
    write_json_new(run_root / 'driver-python-started.json', {'argv': driver_cmd, 'cwd': str(root),
                   'outcome': 'uncertain until driver-python-process.json exists'})
    driver_result = run_process(driver_cmd, root, env, run_root / 'driver-python.stdout.bin',
                                run_root / 'driver-python.stderr.bin', expected, 120)
    write_json_new(run_root / 'driver-python-process.json', driver_result)
    if (driver_result.get('still_running') is not False or type(driver_result.get('exit_code')) is not int or
            driver_result['exit_code'] != 0):
        raise LauncherError('driver Python identity probe failed or remains running; no CTest suite was started')
    driver_evidence = json.loads((run_root / 'driver-python.stdout.bin').read_text(encoding='utf-8'))
    validate_driver_probe(driver_evidence, manifest, root, args.manifest_sha256, driver_result)
    check_immutable(root, manifest, manifest_path=args.manifest)
    result = {'schema': 1, 'run_root': str(run_root), 'source_sha': args.source_sha, 'source_tree': args.source_tree,
              'configuration': args.config, 'manifest_sha256': args.manifest_sha256, 'identity': expected,
              'windows_powershell_sha256': args.windows_powershell_sha256,
              'plan_sha256': sha256(plan_path), 'probe_sha256': sha256(run_root / 'probe.stdout.bin'),
              'probe_process_sha256': sha256(run_root / 'probe-process.json'),
              'probe_stderr_sha256': sha256(run_root / 'probe.stderr.bin'),
              'driver_python_sha256': sha256(run_root / 'driver-python.stdout.bin'),
              'driver_python_process_sha256': sha256(run_root / 'driver-python-process.json'),
              'driver_python_stderr_sha256': sha256(run_root / 'driver-python.stderr.bin'),
              'environment_sha256': sha256(run_root / 'environment.json')}
    write_json_new(run_root / 'preflight.json', result)
    return run_root, result


def selected_document(full, names):
    return {'kind': 'ctestInfo', 'tests': [test for test in full['tests'] if test['name'] in names]}


def audit_selected_discovery(root, logical_root, suite, baseline_path, selected, output, config):
    """Audit only closed selected cases, preserving full-tree partition elsewhere."""
    allowed_path = None
    if suite.get('allowed_outputs'):
        original = audit.read_json(root_path(root, suite['allowed_outputs'], file=True))
        if not isinstance(original, dict):
            raise LauncherError('suite allowed-output evidence is invalid')
        filtered = {name: value for name, value in original.items() if name in selected}
        if filtered:
            allowed_path = output / 'selected-allowed-outputs.json'
            write_json_new(allowed_path, filtered)
    return audit.audit_discovery(root, logical_root, baseline_path, allowed_path, config)


def block_unclosed_real_app_cases(full_docs, decisions, guard_ready=False, reason=None):
    """Do not mistake a review label or private profile for a marker guard."""
    expected = {'ArduPilotLayoutRestoreTest': 'check_ardupilot_layout.py',
                'WindowsApplicationContract': 'verify_windows_application.py'}
    for suite, doc in full_docs.items():
        for case in doc['tests']:
            name = case['name']
            command = case.get('command', [])
            matched = {case_name for case_name, script in expected.items()
                       if any(script in str(arg).casefold() for arg in command)}
            mismatched = (name in expected and matched != {name}) or (matched and matched != {name})
            real_app_case = name in expected or bool(matched)
            if mismatched or (not guard_ready and real_app_case):
                item = dict(decisions[suite][name])
                item['status'] = 'safety_unreviewed'
                item['reason'] = ('real-App CTest name and guarded source script identity do not match' if mismatched else
                                  reason or ('real application marker and active-process preconditions have no verified '
                                             'runtime guard in this launcher; no application process was started'))
                decisions[suite][name] = item


def checked_app_guard(root, paths, manifest, source_sha, source_tree, config):
    """Bind the seven real probe tests to the authenticated Windows CI build.

    A self-filled result, process exit or same-named JUnit cases alone is not
    evidence. The producer's authenticated workflow and immutable manifest are
    the trust root; this does not claim to attest a malicious CI provider.
    """
    keys = ('app_guard_probe', 'app_guard_validation', 'application')
    if not all(isinstance(paths.get(key), str) for key in keys):
        return False, 'real-App guard, application or Windows validation evidence is absent'
    try:
        files = {entry['path'].casefold() for entry in manifest['files']}
        def evidence(relative):
            if not isinstance(relative, str) or relative.casefold() not in files:
                raise LauncherError('guard evidence is not an immutable manifest file: ' + str(relative))
            return root_path(root, relative, file=True)
        root = Path(root).resolve(strict=True)
        probe, app = evidence(paths['app_guard_probe']), evidence(paths['application'])
        qt = root_path(root, paths['qt'], directory=True) / 'bin/Qt6Core.dll'
        ctest = evidence(paths['ctest'])
        cmake = evidence(str(Path(paths['ctest']).parent.as_posix() + '/cmake.exe'))
        tree = root_path(root, 'b/app-marker-probe', directory=True)
        source = root_path(root, 's/scripts/windows/native_app_marker_probe', directory=True)
        outdir = tree / config
        expected_files = {'probe': outdir / 'native_app_marker_probe.exe',
                          'policy_test': outdir / 'marker_probe_policy_test.exe',
                          'windows_test': outdir / 'marker_probe_windows_tests.exe',
                          'process_fixture': outdir / 'plotjuggler_marker_test_fixture.exe'}
        if probe != expected_files['probe'].resolve(strict=True):
            raise LauncherError('guard probe is not from its dedicated CI build tree')
        for exe in expected_files.values():
            evidence(exe.relative_to(root).as_posix())
        for rel in ('CMakeLists.txt', 'main.cpp', 'policy.cpp', 'policy.h', 'tests/policy_test.cpp',
                    'tests/windows_probe_test.cpp', 'tests/known_process_fixture.cpp'):
            evidence((source / rel).relative_to(root).as_posix())
        record = audit.read_json(evidence(paths['app_guard_validation']))
        expected = {'schema': 2, 'source_sha': source_sha, 'source_tree': source_tree, 'configuration': config,
                    'platform': 'windows', 'runner_environment': 'github-hosted',
                    'probe_sha256': sha256(probe), 'qt_core_sha256': sha256(qt), 'application_sha256': sha256(app)}
        if not isinstance(record, dict) or any(record.get(k) != v for k, v in expected.items()):
            raise LauncherError('guard validation does not match the actual CI source, probe, Qt and application')
        identity = audit.read_json(evidence(record.get('build_identity')))
        expected_identity = {'schema': 1, 'role': 'app-marker-probe', 'source_sha': source_sha,
                             'source_tree': source_tree, 'configuration': config,
                             'source_dir': 's/scripts/windows/native_app_marker_probe',
                             'build_tree': 'b/app-marker-probe', 'qt_core_sha256': sha256(qt)}
        if (not isinstance(identity, dict) or any(identity.get(k) != v for k, v in expected_identity.items()) or
                not audit.HEX64.fullmatch(str(identity.get('cmake_cache_sha256', ''))) or
                identity.get('executables_sha256') != {name: sha256(path) for name, path in expected_files.items()}):
            raise LauncherError('guard build identity is not bound to the dedicated source, tree, Qt and executables')

        def process(phase, expected_argv=None):
            process_file = evidence(record.get(phase + '_process'))
            stdout = evidence(record.get(phase + '_stdout'))
            stderr = evidence(record.get(phase + '_stderr'))
            item = audit.read_json(process_file)
            if (not isinstance(item, dict) or item.get('exit_code') != 0 or item.get('still_running') is not False or
                    item.get('stdout_sha256') != sha256(stdout) or item.get('stderr_sha256') != sha256(stderr) or
                    not isinstance(item.get('argv'), list) or not all(isinstance(x, str) for x in item['argv']) or
                    Path(item.get('cwd', '')).resolve(strict=True) != root):
                raise LauncherError('guard ' + phase + ' process or raw outputs are incomplete')
            if expected_argv is not None and item['argv'] != [str(x) for x in expected_argv]:
                raise LauncherError('guard ' + phase + ' argv differs from its required unfiltered command')
            return item, stdout
        configure, _ = process('configure')
        args = configure['argv']
        if (len(args) < 9 or args[0] != str(cmake) or args.count('-S') != 1 or args.count('-B') != 1 or
                args[args.index('-S') + 1] != str(source) or args[args.index('-B') + 1] != str(tree) or
                args.count('-G') != 1 or args[args.index('-G') + 1] != 'Ninja Multi-Config' or
                ('-DCMAKE_PREFIX_PATH=' + str(qt.parent.parent)) not in args):
            raise LauncherError('guard configure command is not the dedicated same-source/Qt build')
        process('build', [cmake, '--build', tree, '--config', config])
        discovery_process, discovery = process('discovery', [ctest, '--test-dir', tree, '-C', config, '--show-only=json-v1'])
        junit = evidence(record.get('junit'))
        process('execution', [ctest, '--test-dir', tree, '-C', config, '--no-tests=error', '--verbose',
                              '--test-output-size-passed', '1073741824', '--test-output-size-failed', '1073741824',
                              '--output-junit', junit])
        discovered = review.indexed(audit.read_json(discovery))
        cases = {'marker_probe_policy': [str(expected_files['policy_test'])]}
        for suffix in ('identity', 'marker_paths', 'access_denied', 'processes', 'qt', 'cli'):
            cases['marker_probe_windows_' + suffix] = [str(expected_files['windows_test']), suffix]
        if set(discovered) != set(cases):
            raise LauncherError('Windows probe discovery differs from all seven exact registrations')
        for name, expected_command in cases.items():
            case, props = discovered[name]
            actual_command = case.get('command')
            if (not isinstance(actual_command, list) or not actual_command or
                    Path(actual_command[0]).resolve(strict=True) != Path(expected_command[0]).resolve(strict=True) or
                    actual_command[1:] != expected_command[1:] or props.get('DISABLED', False) or
                    any(key in props for key in ('ENVIRONMENT', 'ENVIRONMENT_MODIFICATION', 'WILL_FAIL')) or
                    Path(props.get('WORKING_DIRECTORY', '')).resolve(strict=True) != tree):
                raise LauncherError('Windows probe case is not bound to its actual test executable and working directory: ' + name)
        result = audit.audit_results(discovery, junit)
        if not result['complete_without_skips_or_failures']:
            raise LauncherError('Windows probe validation contains failures, skips or removed output')
        return True, 'real Windows probe validation is bound to the authenticated CI build and test commands'
    except (OSError, ValueError, IndexError, KeyError, TypeError, audit.AuditError, review.ReviewError, LauncherError, ET.ParseError) as exc:
        return False, 'real-App probe validation is incomplete: ' + str(exc)

def app_guard_environment(root, run_root, paths, expected, qt_version):
    probe = root_path(root, paths['app_guard_probe'], file=True)
    app = root_path(root, paths['application'], file=True)
    qt = root_path(root, paths['qt'], directory=True) / 'bin/Qt6Core.dll'
    values = {'GUARD_REQUIRED': '1', 'PROBE': str(probe), 'PROBE_SHA256': sha256(probe),
              'QT_CORE': str(qt), 'QT_CORE_SHA256': sha256(qt), 'QT_VERSION': qt_version,
              'EXECUTABLE': str(app), 'EXECUTABLE_SHA256': sha256(app), 'RUN_ROOT': str(run_root),
              'SID': expected['sid'], 'SESSION': str(expected['session']), 'INTEGRITY_RID': str(expected['integrity_rid']),
              'AUTH_LUID': expected['auth_luid'], 'ELEVATION_TYPE': expected['elevation_type']}
    return {'PJ_NATIVE_APP_' + name: value for name, value in values.items()}


def block_guard_environment_overrides(full_docs, decisions):
    reserved = {'TEMP', 'TMP', 'PATH', 'QT_PLUGIN_PATH', 'PYTHONDONTWRITEBYTECODE'}
    for suite, doc in full_docs.items():
        for case in doc['tests']:
            if case['name'] not in ('ArduPilotLayoutRestoreTest', 'WindowsApplicationContract'):
                continue
            props = review.properties(case)
            values = []
            for field in ('ENVIRONMENT', 'ENVIRONMENT_MODIFICATION'):
                if field in props:
                    values.extend(review.as_names(props[field]))
            for value in values:
                key = re.split(r'[=:]', value, maxsplit=1)[0].upper()
                if key in reserved or key.startswith('PJ_NATIVE_APP_'):
                    item = dict(decisions[suite][case['name']])
                    item['status'] = 'safety_unreviewed'
                    item['reason'] = 'CTest property can override a verified real-App guard environment variable: ' + key
                    decisions[suite][case['name']] = item


def audit_app_guard_receipts(root, run_root, suite_env, selected, previous):
    """Report real-App calls and distinguish a missing module observation."""
    relevant = set(selected) & {'ArduPilotLayoutRestoreTest', 'WindowsApplicationContract'}
    if not relevant:
        return {}, []
    helper = load_source_module(root, 's/scripts/windows/native_app_launch_guard.py', 'native_app_guard_result')
    try:
        values = helper.settings(suite_env)
    except Exception as exc:
        raise LauncherError('real-App guard binding is invalid: ' + str(exc)) from exc
    if values is None:
        raise LauncherError('real-App cases ran without the required per-launch guard')
    evidence_root = run_root / 'app-guard'
    new = [path for path in evidence_root.iterdir() if path.name not in previous]
    records = {name: [] for name in relevant}
    issues = []
    for directory in new:
        info = directory.lstat()
        if (not directory.is_dir() or stat.S_ISLNK(info.st_mode) or
                getattr(info, 'st_file_attributes', 0) & 0x400 or not re.fullmatch(r'launch-[0-9a-f]{32}', directory.name)):
            raise LauncherError('unexpected real-App guard evidence entry')
        call = audit.read_json(directory / 'app-argv.json')
        case = call.get('case')
        if case not in records:
            raise LauncherError('real-App guard recorded an unexpected case')
        guard_status = audit.read_json(directory / 'guard-status.json')
        if (not isinstance(guard_status, dict) or guard_status.get('status') != 'completed' or
                guard_status.get('lock_retained') is not False):
            issues.append(case + ': guarded launch lock release was not confirmed for ' + directory.name)
        argv = call.get('argv')
        if (not isinstance(argv, list) or not argv or not all(isinstance(x, str) for x in argv) or
                Path(argv[0]).resolve(strict=True) != Path(values['EXECUTABLE']).resolve(strict=True) or
                argv.count('--profile-dir') != 1 or argv.index('--profile-dir') + 1 >= len(argv) or
                not Path(argv[argv.index('--profile-dir') + 1]).resolve().is_relative_to((run_root / 'tmp').resolve(strict=True))):
            raise LauncherError('real-App recorded argv or profile is invalid')
        snapshots = {}
        for phase in ('before', 'after'):
            process = audit.read_json(directory / (phase + '.process.json'))
            if process.get('exit_code') != 0 or process.get('argv') != helper.probe_command(values):
                raise LauncherError('real-App ' + phase + ' guard did not complete cleanly')
            try:
                snapshots[phase] = helper.validate_snapshot((directory / (phase + '.stdout.bin')).read_bytes(), values)
            except Exception as exc:
                raise LauncherError('real-App ' + phase + ' snapshot is invalid: ' + str(exc)) from exc
        child = audit.read_json(directory / 'app-process.json')
        start_record = audit.read_json(directory / 'app-start.json')
        if (start_record.get('argv') != argv or not isinstance(start_record.get('cwd'), str) or
                not Path(start_record['cwd']).resolve(strict=True).is_relative_to(root.resolve(strict=True))):
            raise LauncherError('real-App process argv or working directory evidence differs')
        child_expected = {'sid': values['SID'], 'session': int(values['SESSION']),
                          'integrity_rid': int(values['INTEGRITY_RID']), 'auth_luid': values['AUTH_LUID'],
                          'elevation_type': values['ELEVATION_TYPE']}
        if child.get('identity_status') == 'not_observed_process_exited' and child.get('identity') is None:
            issues.append(case + ': actual App token was not observed for ' + directory.name)
        elif child.get('identity_status') == 'observed':
            require_identity(child.get('identity', {}), child_expected)
        else:
            raise LauncherError('real-App child identity evidence is malformed')
        exit_record = audit.read_json(directory / 'app-exit.json')
        if not isinstance(exit_record.get('exit_code'), int):
            raise LauncherError('real-App exit status is uncertain')
        times = [snapshots['before']['completed_at_utc'], start_record.get('started_utc'),
                 exit_record.get('completed_utc'), snapshots['after']['checked_at_utc']]
        try:
            times = [datetime.fromisoformat(value.replace('Z', '+00:00')) for value in times]
        except (AttributeError, TypeError, ValueError) as exc:
            raise LauncherError('real-App snapshot timing is invalid') from exc
        if any(value.utcoffset() != timezone.utc.utcoffset(value) for value in times) or times != sorted(times):
            raise LauncherError('real-App before, execution and after evidence is out of order')
        qt_evidence = child.get('qt_core', {})
        if qt_evidence.get('status') != 'observed':
            issues.append(case + ': actual QtCore module path was not observed for ' + directory.name)
        elif os.path.normcase(os.path.normpath(qt_evidence.get('path', ''))) != os.path.normcase(os.path.normpath(values['QT_CORE'])):
            raise LauncherError('real-App loaded an unexpected QtCore module')
        records[case].append({'directory': directory.name, 'argv': call.get('argv'), 'qt_core': qt_evidence,
                              'exit_code': exit_record['exit_code']})
    for case, expected_count in (('ArduPilotLayoutRestoreTest', 3), ('WindowsApplicationContract', 2)):
        if case in relevant and len(records[case]) != expected_count:
            issues.append(case + ': incomplete per-launch guard evidence')
    if 'ArduPilotLayoutRestoreTest' in records and len(records['ArduPilotLayoutRestoreTest']) == 3:
        languages = []
        for item in records['ArduPilotLayoutRestoreTest']:
            args = item['argv']
            if args.count('--language') != 1 or args.index('--language') + 1 >= len(args):
                raise LauncherError('real-App layout language argv is incomplete')
            languages.append(args[args.index('--language') + 1])
        if set(languages) != {'zh_CN', 'zh_TW', 'en_US'}:
            raise LauncherError('real-App layout languages do not match the source contract')
    if 'WindowsApplicationContract' in records and len(records['WindowsApplicationContract']) == 2:
        if {item['argv'][-1] for item in records['WindowsApplicationContract']} != {'--version', '--help'}:
            raise LauncherError('real-App CLI options do not match the source contract')
    return records, issues


def selection_plan(suites, full_docs, selected_docs, decisions, mode, discovery_reviews=None):
    """Determine every group before launching any discovery process."""
    prepared = {}
    for suite in suites:
        name = suite['id']
        full, baseline = full_docs[name], selected_docs[name]
        full_index = review.indexed(full)
        desired = set(review.indexed(baseline))
        if name in ('main', 'i18n'):
            # No saved regex is permitted for either full tree, and neither
            # may use a silently filtered baseline to hide registrations.
            same_discovery(full, baseline)
        if not desired <= set(full_index):
            raise LauncherError('suite selection is not a subset of the complete source tree: ' + name)
        same_discovery(selected_document(full, desired), baseline)
        discovery = (discovery_reviews or {}).get(name, {'status': 'approved'})
        if discovery['status'] != 'approved':
            if mode == 'full':
                raise LauncherError('full mode requires independently approved discovery: ' + name)
            prepared[name] = {'selected': set(), 'desired': desired,
                              'unrun': [{'case': case, 'status': discovery['status'], 'reason': discovery['reason'],
                                         'evidence': [item['path'] for item in discovery['evidence']],
                                         'group': 'discovery'} for case in sorted(desired)]}
            continue
        if mode == 'full':
            selected, unrun = review.approved_selection(full, decisions[name], mode, desired)
        else:
            selected = set()
            unrun = [{'case': case, **decisions[name][case]} for case in sorted(desired)
                     if decisions[name][case]['status'] != 'approved']
            groups = {}
            for case in sorted(desired):
                decision = decisions[name][case]
                if decision['status'] == 'approved':
                    groups.setdefault(decision['group'], set()).add(case)
            for members in groups.values():
                try:
                    closed, _ = review.approved_selection(full, decisions[name], mode, members)
                    selected.update(closed)
                except review.ReviewError as exc:
                    # An unclosed group is omitted without blocking unrelated
                    # reviewed groups, even when they share a CTest tree.
                    unrun.extend({'case': case, 'status': 'safety_unreviewed',
                                  'reason': 'group dependency/fixture closure refused: ' + str(exc),
                                  'evidence': decisions[name][case]['evidence'],
                                  'group': decisions[name][case]['group']} for case in sorted(members))
            # A case may be independently necessary for a different safe
            # group; never simultaneously report it as both selected/unrun.
            unrun = [entry for entry in unrun if entry['case'] not in selected]
        if suite['kind'] == 'csv' and selected and selected != desired:
            if mode == 'full':
                raise LauncherError('CSV runtime gate cannot omit or add cases')
            unrun = [{'case': case, 'status': 'condition_missing',
                      'reason': 'CSV prebuilt gate requires all three original language cases with no extra fixture cases',
                      'evidence': decisions[name][case]['evidence'], 'group': decisions[name][case]['group']}
                     for case in sorted(desired)]
            selected = set()
        prepared[name] = {'selected': selected, 'unrun': unrun, 'desired': desired}
    return prepared


def checked_run_root(root, value):
    parent = root_path(root, 'r', directory=True)
    candidate = Path(value).absolute()
    if candidate.parent != parent or not candidate.name.startswith('run-') or len(candidate.name) != 36:
        raise LauncherError('run root must be a fresh direct child of the kit run directory')
    info = candidate.lstat()
    if not candidate.is_dir() or stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
        raise LauncherError('run root is not an ordinary directory')
    return candidate



def prepare_owned_suite_outputs(root, run_root, suite, selected, discovery, env):
    """Create fresh, suite-local outputs and reject CTest overrides before discovery."""
    root, run_root = Path(root).absolute(), Path(run_root).absolute()
    name = suite['id']
    if not re.fullmatch(r'(?:run|ci)-[0-9a-f]{32}', run_root.name) or run_root.parent != root / 'r':
        raise LauncherError('owned output run is outside this kit')
    output = run_root / name
    if not isinstance(name, str) or not name.replace('-', '').isalnum():
        raise LauncherError('invalid native output suite')
    if name not in ('main', 'i18n') and any(case.startswith('AppProfile.') for case in selected):
        raise LauncherError('AppProfile requires its main or i18n owned output suite')
    for path in (root, root / 'r', run_root, run_root / 'tmp', output):
        info = path.lstat()
        if (not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode) or
                getattr(info, 'st_file_attributes', 0) & 0x400 or path.resolve(strict=True) != path):
            raise LauncherError('linked or noncanonical owned output directory: ' + str(path))
        audit.check_no_named_streams(path, True)
    if any(os.path.normcase(os.path.normpath(env.get(key, ''))) != os.path.normcase(os.path.normpath(str(run_root / 'tmp')))
           for key in ('TEMP', 'TMP')):
        raise LauncherError('suite temporary directory differs from the probed run')
    if 'PJ_UPDATE_POINTCLOUD_GOLDENS' in {key.upper() for key in env}:
        raise LauncherError('golden updates are forbidden in the test kit')
    indexed = review.indexed(discovery)
    if not set(selected) <= set(indexed):
        raise LauncherError('owned output selection differs from discovery')
    for case_name in selected:
        _, props = indexed[case_name]
        forbidden = {'PJ_NATIVE_OUTPUT_ROOT', 'PJ_CSV_DIAGNOSTIC_DIR',
                     'PJ_POINTCLOUD_GOLDEN_OUT', 'PJ_UPDATE_POINTCLOUD_GOLDENS',
                     'PATH', 'PYTHONHOME', 'PYTHONPATH', 'PYTHONEXECUTABLE', 'PYTHONUSERBASE'}
        if case_name.startswith('AppProfile.'):
            forbidden |= {'TEMP', 'TMP', 'TMPDIR', 'XDG_CACHE_HOME'}
        for prop in ('ENVIRONMENT', 'ENVIRONMENT_MODIFICATION'):
            if prop not in props:
                continue
            for value in review.as_names(props[prop]):
                for assignment in value.split(';'):
                    key = re.split(r'[=:]', assignment, maxsplit=1)[0].upper()
                    if key in forbidden:
                        raise LauncherError('CTest may override an owned output variable: ' + case_name + ': ' + key)
    for leaf in ('csv-diagnostics', 'profile-tests', 'pointcloud-golden'):
        (output / leaf).mkdir()  # no preexisting or reused output
    result = dict(env)
    result.update(PJ_NATIVE_OUTPUT_ROOT=str(output), PJ_CSV_DIAGNOSTIC_DIR=str(output / 'csv-diagnostics'),
                  PJ_POINTCLOUD_GOLDEN_OUT=str(output / 'pointcloud-golden'))
    return result


def inventory_owned_suite_outputs(output, selected, require_complete):
    """Keep and hash actual outputs; never clean up links or failure artifacts."""
    output = Path(output)
    csv_dir, golden_dir, profile_dir = (output / x for x in ('csv-diagnostics', 'pointcloud-golden', 'profile-tests'))
    expected_csv = {name.removeprefix('CsvRuntimeFileLoader_') + '.json' for name in selected
                    if name in {'CsvRuntimeFileLoader_en_US', 'CsvRuntimeFileLoader_zh_CN', 'CsvRuntimeFileLoader_zh_TW'}}
    result = {'schema': 1, 'csv': [], 'pointcloud': [], 'profile': [], 'missing_csv': []}
    for directory, kind in ((csv_dir, 'csv'), (golden_dir, 'pointcloud')):
        audit.check_no_named_streams(directory, True)
        for path in sorted(directory.iterdir()):
            audit.regular_file(path); audit.check_no_named_streams(path, False)
            if kind == 'csv':
                if path.name not in expected_csv:
                    raise LauncherError('unexpected CSV diagnostic output: ' + path.name)
                try:
                    document = json.loads(path.read_text(encoding='utf-8'))
                    records = document['records']
                    matches = [x for x in records if isinstance(x, dict) and x.get('id') == 'data-source-load-failed']
                    if (not isinstance(document, dict) or type(document.get('version')) is not int or document.get('version') != 1 or not isinstance(records, list) or
                            len(matches) != 1 or matches[0].get('level') != 'error' or
                            not isinstance(matches[0].get('message'), str) or not matches[0]['message']):
                        raise ValueError('unexpected diagnostic content')
                except (KeyError, ValueError, TypeError, UnicodeError) as exc:
                    raise LauncherError('invalid CSV diagnostic output: ' + path.name) from exc
            elif not (path.name.endswith('_actual.png') or path.name.endswith('_diff.png')):
                raise LauncherError('unexpected pointcloud failure output: ' + path.name)
            result[kind].append({'path': path.name, 'sha256': sha256(path), 'bytes': path.stat().st_size})
    result['missing_csv'] = sorted(expected_csv - {x['path'] for x in result['csv']})
    # Fixtures deliberately contain symlinks/junctions. Record but never follow
    # them, and require their targets to remain within this fresh output tree.
    stack = [profile_dir]
    while stack:
        directory = stack.pop()
        audit.check_no_named_streams(directory, True)
        for path in sorted(directory.iterdir()):
            info = path.lstat(); rel = path.relative_to(profile_dir).as_posix()
            linked = stat.S_ISLNK(info.st_mode) or bool(getattr(info, 'st_file_attributes', 0) & 0x400)
            if linked:
                target = path.resolve(strict=True)
                if not target.is_relative_to(profile_dir.resolve(strict=True)):
                    raise LauncherError('profile fixture link leaves its owned output tree: ' + rel)
                result['profile'].append({'path': rel, 'type': 'link', 'target': str(target)})
            elif stat.S_ISDIR(info.st_mode):
                stack.append(path); result['profile'].append({'path': rel, 'type': 'directory'})
            else:
                audit.regular_file(path); audit.check_no_named_streams(path, False)
                result['profile'].append({'path': rel, 'type': 'file', 'sha256': sha256(path), 'bytes': info.st_size})
    if require_complete and result['missing_csv']:
        raise LauncherError('missing CSV diagnostic outputs: ' + ', '.join(result['missing_csv']))
    return result

def initialize_execution_plan(run_root, suites, prepared, full_docs, mode):
    """Durably record every selected and omitted case before any discovery."""
    progress = {}
    main_names = set(review.indexed(full_docs['main']))
    main_tree = next(item['tree'] for item in suites if item['id'] == 'main')
    for suite in suites:
        name = suite['id']
        output = run_root / name
        output.mkdir()
        selected = sorted(prepared[name]['selected'])
        unrun = prepared[name]['unrun']
        overlap = sorted(prepared[name]['desired'] & main_names) if name in ('file-dialog', 'csv-runtime') else []
        repeat = ('main' if name == 'file-dialog' or
                  (name == 'csv-runtime' and suite['tree'].casefold() == main_tree.casefold()) else None)
        progress[name] = {'phase': 'not_started' if selected else 'not_run', 'selected': selected,
                          'unrun': unrun, 'overlapping_main_case_names': overlap, 'repeat_of': repeat}
        write_json_new(output / 'selection.json', {'mode': mode, **progress[name]})
    write_json_new(run_root / 'execution-plan.json', {'schema': 1, 'mode': mode, 'suites': progress})
    return progress


def incomplete_receipt(progress):
    result = {}
    for name, value in progress.items():
        row = dict(value)
        phase = row['phase']
        if phase in ('discovery_started', 'discovery_still_running'):
            row['case_status'] = 'discovery_outcome_uncertain'
        elif phase in ('execution_started', 'execution_still_running'):
            row['case_status'] = 'execution_outcome_uncertain'
        elif phase in ('execution_finished', 'incomplete_result'):
            row['case_status'] = 'process_exited_but_case_outcomes_unverified'
        elif phase == 'completed':
            row['case_status'] = 'see_suite_coverage'
        else:
            row['case_status'] = 'not_started'
        result[name] = row
    return {'schema': 1, 'status': 'incomplete', 'suites': result}


def mark_process_start(output, phase, argv, cwd):
    if phase not in ('discovery', 'execution'):
        raise LauncherError('unknown process phase')
    write_json_new(Path(output) / (phase + '-started.json'),
                   {'phase': phase, 'argv': [str(x) for x in argv], 'cwd': str(cwd),
                    'started_utc': datetime.now(timezone.utc).isoformat(),
                    'outcome': 'uncertain until corresponding process receipt exists'})


def execute(args):
    root, expected, manifest, plan_path, plan, paths, runtime_dirs, suites, _ = load_context(args, restore=False)
    if not args.run_root or not args.review or not args.review_sha256:
        raise LauncherError('execution requires the preflight run root and independently hashed review')
    run_root = checked_run_root(root, args.run_root)
    # Exclusive marker prevents two simultaneous or repeated executions in a
    # reviewed run root. A failed attempt remains visible and is not retried.
    marker = run_root / 'execution-started.json'
    preflight_path = run_root / 'preflight.json'
    state = audit.read_json(preflight_path)
    expected_state = {'schema': 1, 'run_root': str(run_root), 'source_sha': args.source_sha,
                      'source_tree': args.source_tree, 'configuration': args.config,
                      'manifest_sha256': args.manifest_sha256, 'identity': expected, 'plan_sha256': sha256(plan_path),
                      'windows_powershell_sha256': args.windows_powershell_sha256}
    if any(state.get(key) != value for key, value in expected_state.items()):
        raise LauncherError('preflight source, plan, token or run root no longer matches')
    for key, filename in (('probe_sha256', 'probe.stdout.bin'), ('probe_process_sha256', 'probe-process.json'),
                          ('probe_stderr_sha256', 'probe.stderr.bin'), ('environment_sha256', 'environment.json'),
                          ('driver_python_sha256', 'driver-python.stdout.bin'),
                          ('driver_python_process_sha256', 'driver-python-process.json'),
                          ('driver_python_stderr_sha256', 'driver-python.stderr.bin')):
        if sha256(run_root / filename) != state.get(key):
            raise LauncherError('preflight evidence changed: ' + filename)
    process = audit.read_json(run_root / 'probe-process.json')
    if process.get('still_running') or process.get('exit_code') != 0:
        raise LauncherError('preflight Qt probe did not finish successfully')
    require_identity(process.get('identity', {}), expected)
    driver_process = audit.read_json(run_root / 'driver-python-process.json')
    if (driver_process.get('still_running') is not False or type(driver_process.get('exit_code')) is not int or
            driver_process['exit_code'] != 0):
        raise LauncherError('preflight driver Python probe did not finish successfully')
    require_identity(driver_process.get('identity', {}), expected)
    validate_driver_probe(audit.read_json(run_root / 'driver-python.stdout.bin'), manifest, root,
                          args.manifest_sha256, driver_process)
    env, qt, python, ctest = clean_environment(root, run_root, paths, runtime_dirs, create=False,
                                               powershell_sha256=args.windows_powershell_sha256)
    if env != audit.read_json(run_root / 'environment.json'):
        raise LauncherError('preflight environment no longer matches the verified plan')
    review_path = Path(args.review).absolute()
    if review_path.parent != run_root:
        raise LauncherError('review must be stored directly in its own run root')
    review.verify_evidence(run_root, [{'path': review_path.name, 'sha256': args.review_sha256}])
    full_docs, selected_docs = {}, {}
    for suite in suites:
        name = suite['id']
        check_build_identity(root, suite, args.source_sha, args.source_tree, args.config,
                             next(item['tree'] for item in suites if item['id'] == 'main'))
        full_path = root_path(root, suite['full_discovery'], file=True)
        selected_path = root_path(root, suite['discovery'], file=True)
        full_docs[name] = audit.read_json(full_path)
        selected_docs[name] = audit.read_json(selected_path)
        check_suite_contract(root, suite, selected_docs[name])
    review_record = audit.read_json(review_path)
    decisions = review.validate_review(review_record, run_root, expected, args.source_sha,
                                       args.source_tree, args.manifest_sha256, state['probe_sha256'],
                                       sha256(preflight_path), full_docs, allow_unreviewed_discovery=args.mode != 'full')
    guard_ready, guard_reason = checked_app_guard(root, paths, manifest, args.source_sha, args.source_tree, args.config)
    block_unclosed_real_app_cases(full_docs, decisions, guard_ready, guard_reason)
    block_guard_environment_overrides(full_docs, decisions)
    discovery_reviews = {item['id']: item['discovery'] for item in review_record['suites']}
    prepared = selection_plan(suites, full_docs, selected_docs, decisions, args.mode, discovery_reviews)
    check_immutable(root, manifest, manifest_path=args.manifest)
    generated = generated_ctest_outputs(suites, full_docs, prepared, manifest['logical_root'], root)
    write_json_new(marker, {'schema': 1, 'mode': args.mode, 'review_sha256': args.review_sha256,
                            'preflight_sha256': sha256(preflight_path)})
    progress = initialize_execution_plan(run_root, suites, prepared, full_docs, args.mode)
    finished = False
    try:
        summary = []
        for suite in suites:
            name = suite['id']
            output = run_root / name
            check_immutable(root, manifest, generated, args.manifest)
            selected = prepared[name]['selected']
            unrun = prepared[name]['unrun']
            if not selected:
                summary.append({'suite': name, 'status': 'not_run', 'reason': 'no closed reviewed group', 'unrun': len(unrun),
                                'repeat_of': progress[name]['repeat_of'], 'overlapping_main_case_names': progress[name]['overlapping_main_case_names']})
                continue
            tree = root_path(root, suite['tree'], directory=True)
            suite_env = prepare_owned_suite_outputs(root, run_root, suite, selected, full_docs[name], env)
            if guard_ready:
                suite_env.update(app_guard_environment(root, run_root, paths, expected, plan['qt_version']))
            if suite.get('platform') == 'windows':
                suite_env['QT_QPA_PLATFORM'] = 'windows'
            write_json_new(output / 'environment.json', suite_env)
            # --tests-from-file is explicit and does not itself close DEPENDS.
            # Selection was closed from the complete tree above, then checked
            # against the actual CTest discovery before executing the suite.
            selection_file = output / 'selected.txt'
            with selection_file.open('x', encoding='utf-8', newline='\n') as target:
                for case in sorted(selected):
                    target.write(case + '\n')
            selection = ['--tests-from-file', selection_file]
            selected_baseline = selected_document(full_docs[name], selected)
            baseline_path = output / 'selected-discovery.json'
            write_json_new(baseline_path, selected_baseline)
            audit_selected_discovery(root, args.expected_root, suite, baseline_path, selected, output, args.config)
            discovery_cmd = [ctest, '--test-dir', tree, '-C', args.config, '--show-only=json-v1', *selection]
            mark_process_start(output, 'discovery', discovery_cmd, root)
            progress[name]['phase'] = 'discovery_started'
            result = run_process(discovery_cmd, root, suite_env, output / 'discovery.stdout.bin',
                                 output / 'discovery.stderr.bin', expected, 1800)
            write_json_new(output / 'discovery-process.json', result)
            progress[name]['phase'] = 'discovery_still_running' if result['still_running'] else 'discovery_finished'
            if result['still_running'] or result['exit_code'] != 0:
                raise LauncherError('CTest discovery failed or remains running: ' + name)
            actual = json.loads((output / 'discovery.stdout.bin').read_text(encoding='utf-8'))
            same_discovery(selected_baseline, actual)
            check_immutable(root, manifest, generated, args.manifest)
            report = output / 'junit.xml'
            if suite['kind'] == 'ctest':
                command = [ctest, '--test-dir', tree, '-C', args.config, '--no-tests=error', '--verbose',
                           '--test-output-size-passed', '1073741824', '--test-output-size-failed', '1073741824',
                           '--output-log', output / 'ctest.log', '--output-junit', report, *selection]
            else:
                script = root_path(root, 's/packaging/localization/run_csv_runtime_acceptance.py', file=True)
                prefix = root_path(root, suite['prefix'], directory=True)
                identity = root_path(root, suite['identity'], file=True)
                command = [python, '-I', '-B', script, '--build', tree, '--prefix', prefix,
                           '--prebuilt-identity', identity, '--source-sha', args.source_sha,
                           '--source-tree', args.source_tree, '--kit-root', root, '--qt-dir', qt,
                           '--ctest', ctest, '--manifest', args.manifest, '--manifest-sha256', args.manifest_sha256,
                           '--report', report]
            guard_before = {path.name for path in (run_root / 'app-guard').iterdir()}
            mark_process_start(output, 'execution', command, root)
            progress[name]['phase'] = 'execution_started'
            result = run_process(command, root, suite_env, output / 'stdout.bin', output / 'stderr.bin', expected, args.timeout)
            write_json_new(output / 'process.json', result)
            progress[name]['phase'] = 'execution_still_running' if result['still_running'] else 'execution_finished'
            if result['still_running']:
                raise LauncherError('suite exceeded its outer timeout and may still be running: ' + name)
            write_json_new(output / 'owned-output-inventory.json',
                           inventory_owned_suite_outputs(output, selected, result['exit_code'] == 0))
            inventory_receipt = check_immutable(root, manifest, generated, args.manifest)
            write_json_new(output / 'post-suite-inventory.json', inventory_receipt)
            last_log = tree / 'Testing/Temporary/LastTest.log'
            if last_log.is_file():
                shutil.copyfile(last_log, output / 'LastTest.log')
            try:
                if not report.is_file():
                    raise LauncherError('suite did not produce JUnit evidence')
                coverage = audit.audit_results(baseline_path, report)
                gate_errors = []
                if guard_ready:
                    app_issues = []
                    try:
                        app_records, app_issues = audit_app_guard_receipts(root, run_root, suite_env, selected, guard_before)
                        if app_records:
                            write_json_new(output / 'app-guard-audit.json', {'cases': app_records, 'issues': app_issues})
                        gate_errors.extend(app_issues)
                    except (LauncherError, OSError, ValueError, KeyError, TypeError) as exc:
                        app_issues.append('real-App guard evidence incomplete: ' + str(exc))
                        gate_errors.extend(app_issues)
                    for case_result in coverage['case_results']:
                        if case_result['test'] in ('ArduPilotLayoutRestoreTest', 'WindowsApplicationContract'):
                            case_result['app_guard_coverage'] = ('unverified' if any(
                                issue.startswith(case_result['test'] + ':') or issue.startswith('real-App guard evidence')
                                for issue in app_issues) else 'verified')
                try:
                    if name == 'file-dialog':
                        if selected != prepared[name]['desired']:
                            gate_errors.append('full native file-dialog gate was not run')
                        else:
                            dialog_gate = load_source_module(root, 's/packaging/localization/audit_file_dialog_results.py', 'file_dialog_result_gate')
                            write_json_new(output / 'file-dialog-audit.json', {'cases': dialog_gate.audit(report)})
                    if name == 'main':
                        feedback_gate = load_source_module(root, 's/packaging/localization/audit_feedback_results.py', 'feedback_result_gate')
                        if not feedback_gate.EXPECTED <= selected:
                            gate_errors.append('full APBIN/FFT feedback gate was not run')
                        else:
                            write_json_new(output / 'feedback-audit.json', {
                                'cases': feedback_gate.audit_cases(ET.parse(report).getroot(), allow_other_cases=True),
                                'screenshots': feedback_gate.audit_images(Path(env['PJ_GUI_ACCEPTANCE_DIR']))})
                except (ValueError, OSError, ET.ParseError) as exc:
                    gate_errors.append(str(exc))
                write_json_new(output / 'coverage.json', coverage)
                progress[name]['phase'] = 'completed'
                summary.append({'suite': name, 'status': 'completed', 'kind': suite['kind'], 'test_count': coverage['test_count'],
                                'exit_code': result['exit_code'], 'failures': len(coverage['failures']),
                                'top_level_skips': len(coverage['top_level_skips']), 'nested_skips': len(coverage['nested_skips']),
                                'truncated_outputs': len(coverage['truncated_outputs']), 'gate_errors': gate_errors, 'unrun': len(unrun),
                                'repeat_of': progress[name]['repeat_of'], 'overlapping_main_case_names': progress[name]['overlapping_main_case_names']})
            except (LauncherError, audit.AuditError, OSError, ValueError, ET.ParseError) as exc:
                progress[name]['phase'] = 'incomplete_result'
                summary.append({'suite': name, 'status': 'incomplete', 'kind': suite['kind'], 'test_count': 0,
                                'exit_code': result['exit_code'], 'failures': 1, 'top_level_skips': 0,
                                'nested_skips': 0, 'truncated_outputs': 0, 'gate_errors': [str(exc)], 'unrun': len(unrun),
                                'repeat_of': progress[name]['repeat_of'], 'overlapping_main_case_names': progress[name]['overlapping_main_case_names']})
        check_immutable(root, manifest, generated, args.manifest)
        write_json_new(run_root / 'summary.json', {'schema': 1, 'mode': args.mode, 'source_sha': args.source_sha,
                       'source_tree': args.source_tree, 'configuration': args.config, 'suites': summary})
        finished = True
        return run_root, summary
    finally:
        if not finished:
            write_json_new(run_root / 'incomplete.json', incomplete_receipt(progress))



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'manifest', 'manifest-sha256', 'expected-root', 'source-sha', 'source-tree', 'config', 'plan', 'sid'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--session', type=int, required=True)
    parser.add_argument('--integrity', type=int, required=True)
    parser.add_argument('--auth-luid', required=True, help='independently verified logon AuthenticationId')
    parser.add_argument('--elevation-type', choices=('default', 'full', 'limited'), required=True)
    parser.add_argument('--timeout', type=int, default=21600)
    parser.add_argument('--mode', choices=('preflight', 'full', 'reviewed-subset'), default='preflight')
    parser.add_argument('--run-root')
    parser.add_argument('--review')
    parser.add_argument('--review-sha256')
    parser.add_argument('--windows-powershell-sha256', help='independently reviewed host system PowerShell SHA-256')
    args = parser.parse_args()
    try:
        if args.session <= 0 or args.integrity <= 0 or args.timeout <= 0:
            raise LauncherError('session, integrity and timeout must be positive')
        if not re.fullmatch(r'[0-9a-f]{8}:[0-9a-f]{8}', args.auth_luid):
            raise LauncherError('AuthenticationId must be the independently verified lower-case high:low LUID')
        if args.mode == 'preflight':
            if args.run_root or args.review or args.review_sha256:
                raise LauncherError('preflight creates its own new run root and does not accept a review')
            run_root, result = preflight(args)
            print(json.dumps({'run_root': str(run_root), 'status': 'awaiting-independent-review',
                              'preflight_sha256': sha256(run_root / 'preflight.json'),
                              'probe_sha256': result['probe_sha256']}, ensure_ascii=False))
            return 0
        run_root, summary = execute(args)
        print(json.dumps({'run_root': str(run_root), 'suites': summary}, ensure_ascii=False))
        return 2 if any(x['status'] != 'completed' or x['exit_code'] != 0 or x['failures'] or x['top_level_skips'] or
                        x['nested_skips'] or x['truncated_outputs'] or x['gate_errors'] or x['unrun'] for x in summary) else 0
    except (LauncherError, review.ReviewError, audit.AuditError, OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f'native test launcher stopped: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
