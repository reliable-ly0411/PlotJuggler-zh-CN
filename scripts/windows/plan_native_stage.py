#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Inventory exact same-root files and stage only source-reviewed closure.

The initial output is only a candidate, not approval to execute or upload.
Optional packaging requires the exact source-reviewed closure verifier,
independent file/source checks, PE resolution and recorded producer controls.
Actual selected groups still have to run before upload and on a clean host;
static imports or source analysis alone do not prove runtime behavior.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import ntpath
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import shutil
import stat
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

HERE = Path(__file__).resolve().parent
FFT_SOURCE_COMMIT = '2bc991cae2dba7f9f1468dbf8dd72d89797699bc'
FFT_LICENSE_SHA256 = '3701f21353125c50abb10b6a440148a00e41a43a10da994f6d240264030dfe2b'
PRODUCER_EVIDENCE_FILES = (
    ['native-kit/conan-evidence/' + phase + suffix for phase in ('remotes', 'install')
     for suffix in ('.process.json', '.stdout.bin', '.stderr.bin')] +
    ['native-kit/codemodel/process/' + phase + suffix for phase in ('configure', 'build')
     for suffix in ('.process.json', '.stdout.bin', '.stderr.bin')] +
    ['native-kit/bootstrap-selftest-evidence/' + name for name in ('process.json', 'stdout.bin', 'stderr.bin',
     'python-origin.process.json', 'python-origin.stdout.bin', 'python-origin.stderr.bin')] +
    ['native-kit/ci-temp-probe-evidence/' + phase + suffix
     for phase in ('before-plugin-preflight', 'before-marker-mutation', 'before-main-discovery')
     for suffix in ('.json', '.stdout.bin', '.stderr.bin')] +
    ['native-kit/registry-smoke-build/' + name for name in ('configure.log', 'build.log', 'producer-identity.json')] +
    ['native-kit/registry-smoke-evidence/' + name for name in
     ('receipt.json', 'normal.stdout.bin', 'normal.stderr.bin', 'injected.stdout.bin', 'injected.stderr.bin')] +
    ['registry-smoke/RelWithDebInfo/registry_fixture_smoke.exe'] +
    ['native-kit/marker-mutation-evidence/' + phase + suffix
     for phase in ('mutant-build', 'mutant-test', 'original-build', 'original-test')
     for suffix in ('.stdout.bin', '.stderr.bin', '.process.json')] +
    ['native-kit/marker-mutation-evidence/' + name for name in ('receipt.json', 'mutant.xml', 'original.xml')]
)


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


audit = load_module('native_stage_audit', 'native_bundle_audit.py')
source_helper = load_module('native_stage_source', 'prepare_native_source.py')
tools_helper = load_module('native_stage_tools', 'prepare_native_tools.py')
pe_helper = load_module('native_stage_pe', 'native_pe_closure.py')


class PlanError(Exception):
    """Input identity or a candidate file cannot be established safely."""


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_new(path, value):
    path = Path(path)
    if not path.parent.is_dir():
        raise PlanError('output parent does not exist: ' + str(path.parent))
    with path.open('x', encoding='utf-8', newline='\n') as output:
        json.dump(value, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write('\n')


def archive_captured_stage(staging, logical_root, archive, manifest_sha256):
    """Stream a captured stage into one new ZIP and check every archived byte.

    No trust decision is made here. The caller must establish dependency and
    execution closure before staging; the clean Windows bootstrap separately
    authenticates and extracts these bytes without executing any kit code.
    """
    staging, archive = Path(staging).absolute(), Path(archive).absolute()
    logical_root = audit.windows_root(logical_root)
    manifest_path = staging / '_bundle' / 'manifest.json'
    if not audit.HEX64.fullmatch(str(manifest_sha256)) or digest(manifest_path) != manifest_sha256:
        raise PlanError('captured manifest SHA-256 differs')
    manifest = read_json(manifest_path)
    if (manifest.get('schema') != 1 or manifest.get('logical_root') != logical_root or
            not isinstance(manifest.get('files'), list) or not isinstance(manifest.get('directories'), list)):
        raise PlanError('captured manifest identity is invalid')
    audit.check_provenance(manifest.get('provenance'))
    if (manifest['provenance']['source_sha'][:12] != logical_root[-12:] or
            audit.inventory(staging, logical_root, exclude_manifest=True) !=
            {'files': manifest['files'], 'directories': manifest['directories']}):
        raise PlanError('staged files or directories differ from the captured manifest')
    records = manifest['files']
    directories = manifest['directories']
    total = sum(item['bytes'] for item in records)
    if (len(records) + len(directories) + 1 > 100000 or total > 32 * 1024**3 or
            manifest_path.stat().st_size > 32 * 1024**2 or
            any(item['bytes'] > 8 * 1024**3 or item['mtime_ns'] % 100 for item in records)):
        raise PlanError('captured stage exceeds bootstrap size, count, or timestamp bounds')
    if archive.exists() or not archive.parent.is_dir() or staging in archive.parents:
        raise PlanError('archive must be a new file outside the captured stage')
    audit.check_root(archive.parent, logical_root)
    # Conservatively reserve for worst-case DEFLATE expansion as well as long
    # ZIP headers and central records; do not assume the compression ratio.
    names = list(directories) + [item['path'] for item in records] + ['_bundle/manifest.json']
    expanded = total + manifest_path.stat().st_size
    upper = expanded + (expanded >> 12) + (expanded >> 14) + (expanded >> 25) + \
        sum(2 * len(x.encode('utf-8')) + 1024 for x in names) + 65536
    if upper > 16 * 1024**3:
        raise PlanError('conservative ZIP upper bound exceeds the bootstrap limit')
    if shutil.disk_usage(archive.parent).free < upper + 2 * 1024**3:
        raise PlanError('insufficient free space for the archive and two-GiB reserve')
    expected = {item['path']: (item['bytes'], item['sha256']) for item in records}
    expected['_bundle/manifest.json'] = (manifest_path.stat().st_size, manifest_sha256)
    try:
        with archive.open('xb') as output, zipfile.ZipFile(output, 'w', allowZip64=True) as target:
            for relative in directories:
                info = zipfile.ZipInfo(relative + '/', date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system, info.external_attr = 0, 0x10
                target.writestr(info, b'', compress_type=zipfile.ZIP_STORED)
            for relative in sorted(expected, key=str.casefold):
                info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system, info.external_attr = 0, 0x20
                info.compress_type, info._compresslevel = zipfile.ZIP_DEFLATED, 6
                source = staging.joinpath(*relative.split('/'))
                with source.open('rb') as src, target.open(info, 'w', force_zip64=expected[relative][0] >= 2**31) as dst:
                    shutil.copyfileobj(src, dst, 1024 * 1024)
        if archive.stat().st_size > 16 * 1024**3:
            raise PlanError('ZIP exceeds the bootstrap archive limit')
        with zipfile.ZipFile(archive) as result:
            entries = result.infolist()
            wanted = {x + '/' for x in directories} | set(expected)
            if (result.comment or len(entries) != len(wanted) or
                    {x.filename for x in entries} != wanted or len({x.filename.casefold() for x in entries}) != len(entries)):
                raise PlanError('ZIP entry set differs from the captured manifest')
            for info in entries:
                if info.is_dir():
                    if info.file_size:
                        raise PlanError('ZIP directory is not empty')
                    continue
                value = hashlib.sha256()
                size = 0
                with result.open(info) as src:
                    for chunk in iter(lambda: src.read(1024 * 1024), b''):
                        size += len(chunk)
                        value.update(chunk)
                if (size, value.hexdigest()) != expected[info.filename]:
                    raise PlanError('ZIP member differs from captured bytes: ' + info.filename)
        if (audit.inventory(staging, logical_root, exclude_manifest=True) !=
                {'files': records, 'directories': directories} or digest(manifest_path) != manifest_sha256):
            raise PlanError('captured stage changed while ZIP was created')
        return {'archive_sha256': digest(archive), 'manifest_sha256': manifest_sha256,
                'archive_bytes': archive.stat().st_size, 'expanded_bytes': total + manifest_path.stat().st_size,
                'files': len(records), 'directories': len(directories)}
    except BaseException:
        # The archive is never an admissible artifact after any failure.
        try:
            archive.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def run_reviewed_verifier(verifier, root, source, candidate, report, reviewed, output):
    return subprocess.run([sys.executable, '-I', '-B', str(verifier), '--root', str(root),
                           '--candidate-plan', str(candidate), '--candidate-report', str(report),
                           '--reviewed-policy', str(reviewed), '--output-dir', str(output)],
                          cwd=source, check=False).returncode


def load_reviewed_verifier(path):
    spec = importlib.util.spec_from_file_location('native_reviewed_closure', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def selected_pe_plan(plan, runtime_dirs, selected, full_docs, logical_root, reviewed_files):
    """Restrict PE closure to selected processes and visible/reviewed modules.

    Non-selected standalone executables do not cause a subset run to fail.
    The next step resolves imports against all visible providers without
    recursively auditing unrelated DLLs. The independently reviewed source
    inventory supplies this list; it is not described as an observed trace.
    """
    if not isinstance(reviewed_files, list) or not reviewed_files or any(not isinstance(x, str) for x in reviewed_files):
        raise PlanError('closure needs explicitly reviewed PE files')
    entries = {}
    for item in plan['files']:
        target = item['destination']
        if PurePosixPath(target).suffix.casefold() not in ('.exe', '.dll', '.pyd'):
            continue
        key = target.casefold()
        if key in entries:
            raise PlanError('duplicate PE staging path')
        entries[key] = item
    chosen = set()
    for target in reviewed_files:
        safe_relative(target, logical_root)
        if target.casefold() not in entries or target.casefold() in chosen:
            raise PlanError('reviewed PE is missing from the plan or duplicated: ' + target)
        chosen.add(target.casefold())
    for fixed in ('t/python/python.exe', 't/python/python3.dll', 't/python/python312.dll', 't/cmake/bin/ctest.exe',
                  'b/ci-temp-probe/relwithdebinfo/pj_native_ci_temp_probe.exe',
                  'i/temp-probe/relwithdebinfo/pj_native_temp_probe.exe'):
        if fixed not in entries:
            raise PlanError('verified CI driver PE is absent from the staging plan: ' + fixed)
        chosen.add(fixed)
    # The driver dynamically imports standard extension modules. Seed every
    # authenticated top-level embedded-Python DLL and PYD for ordinary and
    # delay-import closure; this does not claim every runtime branch was run.
    for key in entries:
        path = PurePosixPath(key)
        if path.parent.as_posix() == 't/python' and path.suffix in ('.dll', '.pyd'):
            chosen.add(key)
    for suite, name in selected:
        tests = [test for test in full_docs[suite]['tests'] if test.get('name') == name]
        if len(tests) != 1 or not isinstance(tests[0].get('command'), list) or not tests[0]['command']:
            raise PlanError('selected test has no unique executable: ' + suite + '/' + name)
        try:
            target = audit.to_relative(tests[0]['command'][0], logical_root)
        except audit.AuditError as exc:
            raise PlanError('selected executable is outside the same-root plan: ' + suite + '/' + name) from exc
        if target.casefold() not in entries or PurePosixPath(target).suffix.casefold() != '.exe':
            raise PlanError('selected test executable is missing from the PE plan: ' + target)
        chosen.add(target.casefold())
    return {'origins': plan['origins'], 'files': [entries[key] for key in sorted(chosen)]}


def resolve_selected_pe_plan(plan, seeds, runtime_dirs, system_dlls):
    """Resolve just reachable static imports, checking all visible providers."""
    directories = {x.casefold().rstrip('/') for x in runtime_dirs}
    system = {name.casefold() for name in system_dlls}
    available = {}
    for item in plan['files']:
        path = PurePosixPath(item['destination'])
        if path.suffix.casefold() == '.dll':
            available.setdefault(path.name.casefold(), []).append(item)
    selected = {item['destination'].casefold(): item for item in seeds['files']}
    queue = list(selected)
    while queue:
        key = queue.pop()
        item = selected[key]
        target = PurePosixPath(item['destination'])
        source = regular_under(plan['origins'][item['origin']]['root'], item['source'])
        if digest(source) != item['sha256']:
            raise PlanError('selected PE bytes changed: ' + item['destination'])
        try:
            imports = pe_helper.imports(source)
        except (pe_helper.PEError, OSError, ValueError) as exc:
            raise PlanError('cannot parse selected PE: ' + item['destination'] + ': ' + str(exc)) from exc
        for kind in ('normal', 'delay'):
            for name in imports[kind]:
                candidates = [x for x in available.get(name.casefold(), [])
                              if str(PurePosixPath(x['destination']).parent).casefold() in directories or
                              (target.suffix.casefold() == '.exe' and
                               PurePosixPath(x['destination']).parent.as_posix().casefold() == target.parent.as_posix().casefold())]
                if name.casefold() in system:
                    if candidates:
                        raise PlanError('host and visible bundled DLL collide: ' + name)
                    continue
                if not candidates:
                    raise PlanError(f'unresolved selected {kind} import {name} in {item["destination"]}')
                if len({x['sha256'] for x in candidates}) != 1:
                    raise PlanError('different visible DLLs collide for selected import: ' + name)
                for provider in candidates:
                    provider_key = provider['destination'].casefold()
                    if provider_key not in selected:
                        selected[provider_key] = provider
                        queue.append(provider_key)
    return {'origins': plan['origins'], 'files': [selected[key] for key in sorted(selected)]}


def validate_dynamic_inventory(plan, inventory, selected, full_docs, logical_root, source_sha, source_tree):
    """Bind source-reviewed dynamic inputs to real selected cases and file bytes."""
    if (not isinstance(inventory, dict) or any(inventory.get(k) != v for k, v in {
            'schema': 1, 'basis': 'source-analysis', 'source_sha': source_sha, 'source_tree': source_tree,
            'configuration': 'RelWithDebInfo'}.items()) or not isinstance(inventory.get('scopes'), list)):
        raise PlanError('dynamic inventory is not exact-source source-analysis evidence')
    files = {item['destination'].casefold(): item for item in plan['files']}
    covered, pe_files = set(), {}
    def file_value(value, *, source=False, role=False):
        keys = {'path', 'sha256'} | ({'role'} if role else set())
        if (not isinstance(value, dict) or set(value) != keys or not isinstance(value.get('path'), str) or
                not audit.HEX64.fullmatch(str(value.get('sha256', ''))) or
                (role and (not isinstance(value['role'], str) or not value['role'].strip()))):
            raise PlanError('dynamic inventory has an invalid explicit file identity')
        relative = safe_relative(value['path'], logical_root)
        item = files.get(relative.casefold())
        if (item is None or item['destination'] != relative or item['sha256'] != value['sha256'] or
                (source and not relative.startswith('s/'))):
            raise PlanError('dynamic inventory file is not an exact staged source or runtime identity: ' + relative)
        real = regular_under(plan['origins'][item['origin']]['root'], item['source'])
        if digest(real) != value['sha256']:
            raise PlanError('dynamic inventory file bytes changed: ' + relative)
        if PurePosixPath(relative).suffix.casefold() in ('.exe', '.dll', '.pyd'):
            pe_files[relative.casefold()] = relative
        return relative
    for scope in inventory['scopes']:
        if (not isinstance(scope, dict) or set(scope) != {'suite', 'cases', 'runner', 'source_files',
                'dynamic_files', 'subprocesses', 'reason'} or not isinstance(scope['suite'], str) or
                not isinstance(scope['cases'], list) or not scope['cases'] or
                not isinstance(scope['reason'], str) or not scope['reason'].strip()):
            raise PlanError('dynamic inventory scope is incomplete')
        runner = file_value(scope['runner'])
        if (not isinstance(scope['source_files'], list) or not scope['source_files'] or
                not isinstance(scope['dynamic_files'], list) or not isinstance(scope['subprocesses'], list)):
            raise PlanError('each dynamic scope requires source evidence and explicit runtime/subprocess lists')
        for value in scope['source_files']:
            file_value(value, source=True)
        for value in scope['dynamic_files']:
            file_value(value, role=True)
        for value in scope['subprocesses']:
            file_value(value)
        for case in scope['cases']:
            key = (scope['suite'], case)
            if not isinstance(case, str) or key not in selected or key in covered:
                raise PlanError('dynamic inventory has an unselected or duplicate case')
            tests = [test for test in full_docs[scope['suite']]['tests'] if test.get('name') == case]
            if len(tests) != 1 or not tests[0].get('command'):
                raise PlanError('dynamic inventory case is absent from actual discovery')
            try:
                actual_runner = audit.to_relative(tests[0]['command'][0], logical_root)
            except audit.AuditError as exc:
                raise PlanError('dynamic inventory runner leaves the same root') from exc
            if actual_runner.casefold() != runner.casefold():
                raise PlanError('dynamic inventory runner differs from actual discovery')
            covered.add(key)
    if covered != selected:
        raise PlanError('dynamic inventory does not cover every selected case')
    return [pe_files[key] for key in sorted(pe_files)]


def ci_pe_search_directories(run_paths, runtime_dirs, reviewed, logical_root):
    """Use only the same-root directories actually placed in hosted CI PATH."""
    extra_dirs = reviewed.get('loader_extra_dirs', [])
    if not isinstance(extra_dirs, list) or extra_dirs:
        raise PlanError('loader-specific directories are not part of the hosted CI PATH')
    base_dirs = [run_paths['qt'].rstrip('/') + '/bin',
                 str(PurePosixPath(run_paths['ctest']).parent), *runtime_dirs]
    result, seen = [], set()
    for item in base_dirs:
        item = safe_relative(item, logical_root)
        if item.casefold() not in seen:
            seen.add(item.casefold()); result.append(item)
    return result


def package_candidate(root, logical_root, source_sha, source_tree, candidate_path, report_path, staging, archive):
    """Run the source-reviewed closure verifier, then stage and capture its inputs.

    The verifier and its policy are deliberately required from the exact clean
    source tree. Its reviewed rules fix the verifier hash, named system DLLs
    and case-selection logic; a CI variable or lone 'approved' flag cannot
    supply that review. The verifier must independently check Qt/Conan origins,
    licenses, host modules and a source-reviewed dynamic dependency inventory.
    Missing implementation or evidence remains a specific hard failure.
    """
    root, staging, archive = Path(root).absolute(), Path(staging).absolute(), Path(archive).absolute()
    logical_root = audit.windows_root(logical_root)
    if not audit.HEX40.fullmatch(str(source_sha)) or not audit.HEX40.fullmatch(str(source_tree)) or source_sha[:12] != logical_root[-12:]:
        raise PlanError('packaging needs a full source identity matching the same-root path')
    audit.check_root(root, logical_root, require_exact=True)
    source = root / 's'
    candidate_path, report_path = Path(candidate_path).absolute(), Path(report_path).absolute()
    generated = verified_source_state(root, logical_root, source_sha, source_tree)
    policy_rel = '.github/windows-native-kit/ci-closure-policy.json'
    verifier_rel = 'scripts/windows/verify_native_ci_closure.py'
    for relative in (policy_rel, verifier_rel, 'scripts/windows/run_native_ci_verification.py'):
        if not (source / relative).is_file():
            raise PlanError('source-reviewed closure input is missing: s/' + relative)
        try:
            git(source, 'ls-files', '--error-unmatch', '--', relative)
        except PlanError as exc:
            raise PlanError('closure input must be tracked by the exact source commit: s/' + relative) from exc
    reviewed_path, verifier_path = source / policy_rel, source / verifier_rel
    reviewed = read_json(reviewed_path)
    if (not isinstance(reviewed, dict) or reviewed.get('schema') != 2 or
            not audit.HEX64.fullmatch(str(reviewed.get('verifier_sha256', ''))) or
            digest(verifier_path) != reviewed['verifier_sha256']):
        raise PlanError('source-reviewed closure policy does not pin the actual verifier')
    verifier = load_reviewed_verifier(verifier_path)
    plan, report = read_json(candidate_path), read_json(report_path)
    if (not isinstance(plan, dict) or not isinstance(plan.get('files'), list) or
            not isinstance(plan.get('origins'), dict) or not isinstance(plan.get('directories'), list) or
            not isinstance(report, dict) or report.get('source_sha') != source_sha or
            report.get('source_tree') != source_tree or report.get('logical_root') != logical_root or
            report.get('configuration') != 'RelWithDebInfo'):
        raise PlanError('candidate plan and report do not match the exact source and root')
    planned_paths = {item['destination'].casefold() for item in plan['files']}
    missing_producer = ['b/' + item for item in PRODUCER_EVIDENCE_FILES if ('b/' + item).casefold() not in planned_paths]
    if missing_producer or (root / 'b/native-kit/marker-mutation-evidence/INCOMPLETE').exists():
        raise PlanError('required producer evidence is missing or mutation remains incomplete: ' + ', '.join(missing_producer))
    if 's/scripts/windows/native_marker_mutation.py' not in planned_paths:
        raise PlanError('the exact linked mutation controller is absent from the candidate')
    mutation = read_json(regular_under(root, 'b/native-kit/marker-mutation-evidence/receipt.json'))
    marker_file = regular_under(source, 'pj_runtime/src/ActiveWidgetsMarker.cpp')
    runner_file = regular_under(root, 'b/pj_app/RelWithDebInfo/pj_app_gui_tests.exe')
    temp_file = regular_under(root, 'b/native-kit/ci-temp-probe-evidence/before-marker-mutation.stdout.bin')
    if (not isinstance(mutation, dict) or mutation.get('schema') != 1 or mutation.get('complete') is not True or
            mutation.get('scope') != 'disposable-windows-ci-only' or mutation.get('source_sha') != source_sha or
            mutation.get('source_tree') != source_tree or
            mutation.get('case') != 'MainWindowCustomWidgetTest.WindowCloseClearsAnOrphanRecordInsideTheSurvivingFixtureRoot' or
            any(not audit.HEX64.fullmatch(str(mutation.get(key, ''))) for key in
                ('original_source_sha256', 'mutated_source_sha256', 'baseline_runner_sha256', 'mutant_runner_sha256',
                 'restored_runner_sha256', 'qt_preflight_sha256')) or
            mutation.get('original_source_sha256') != digest(marker_file) or
            mutation.get('restored_runner_sha256') != digest(runner_file) or mutation.get('qt_preflight_sha256') != digest(temp_file) or
            mutation.get('mutated_source_sha256') == mutation.get('original_source_sha256') or
            mutation.get('mutant_runner_sha256') == mutation.get('restored_runner_sha256')):
        raise PlanError('linked mutation receipt does not match the restored source, runner and real Qt preflight')
    tracked = []
    for row in git(source, 'ls-files', '--recurse-submodules', '--stage', '-z', binary=True).split(b'\0'):
        if not row:
            continue
        header, raw_path = row.split(b'\t', 1)
        mode, _, stage = header.decode('ascii').split()
        if mode not in ('100644', '100755') or stage != '0':
            raise PlanError('tracked source is not an ordinary resolved file')
        tracked.append(raw_path.decode('utf-8', errors='strict'))
    try:
        verifier.source_paths_match(tracked, [x['destination'] for x in plan['files']],
                                    verifier.SYNTHETIC_MEDIA_PATHS if generated else ())
    except verifier.ClosureError as exc:
        raise PlanError('source stage does not match the exact clean recursive Git inventory: ' + str(exc)) from exc
    output = root / 'b/native-kit/closure-evidence'
    if output.exists():
        raise PlanError('closure evidence output must be new')
    output.mkdir()
    candidate_sha, report_sha, reviewed_sha, verifier_sha = (digest(candidate_path), digest(report_path),
                                                               digest(reviewed_path), digest(verifier_path))
    code = run_reviewed_verifier(verifier_path, root, source, candidate_path, report_path, reviewed_path, output)
    if code != 0:
        raise PlanError('source-reviewed closure verifier failed with exit code ' + str(code))
    if (digest(candidate_path), digest(report_path), digest(reviewed_path), digest(verifier_path)) != \
            (candidate_sha, report_sha, reviewed_sha, verifier_sha):
        raise PlanError('candidate, report, reviewed policy or verifier changed during closure verification')
    receipt_path, ci_policy_path, provenance_path = (output / 'receipt.json', output / 'ci-policy.json', output / 'provenance.json')
    receipt, ci_policy, provenance = (read_json(p) for p in (receipt_path, ci_policy_path, provenance_path))
    expected = {'schema': 1, 'source_sha': source_sha, 'source_tree': source_tree,
                'configuration': 'RelWithDebInfo', 'candidate_plan_sha256': candidate_sha,
                'candidate_report_sha256': report_sha, 'reviewed_policy_sha256': reviewed_sha,
                'verifier_sha256': verifier_sha}
    if not isinstance(receipt, dict) or any(receipt.get(k) != v for k, v in expected.items()):
        raise PlanError('closure receipt is not bound to the actual source, candidate and reviewed verifier')
    if (not isinstance(ci_policy, dict) or
            any(ci_policy.get(k) != v for k, v in {'schema': 1, 'scope': 'github-hosted-windows-ci',
                'source_sha': source_sha, 'source_tree': source_tree, 'configuration': 'RelWithDebInfo'}.items())):
        raise PlanError('derived CI case policy differs from the exact source and scope')
    evidence = receipt.get('evidence')
    required_kinds = {'qt-origin-extraction', 'conan-origin-license', 'host-system-resolution',
                      'dynamic-dependency-inventory', 'case-source-review', 'private-registry-lifecycle', 'ci-temp-safety',
                      'linked-marker-mutation', 'bootstrap-adversarial', 'candidate-input'}
    if not isinstance(evidence, list) or not evidence or not required_kinds <= {x.get('kind') for x in evidence if isinstance(x, dict)}:
        raise PlanError('closure receipt lacks Qt, Conan, host, dynamic inventory, source review, registry, CI temp, mutation or bootstrap evidence')
    added, seen = [], set()
    for item in evidence:
        if (not isinstance(item, dict) or item.get('kind') not in required_kinds or not isinstance(item.get('path'), str) or
                not item['path'].startswith('b/native-kit/closure-evidence/') or
                not audit.HEX64.fullmatch(str(item.get('sha256', ''))) or
                item['path'].casefold() in seen):
            raise PlanError('closure evidence needs unique exact same-root paths and SHA-256 hashes')
        seen.add(item['path'].casefold())
        relative = safe_relative(item['path'], logical_root)
        path = regular_under(root, relative)
        if not path.stat().st_size or digest(path) != item['sha256']:
            raise PlanError('closure evidence is empty or changed: ' + relative)
        if item['kind'] == 'dynamic-dependency-inventory' and not relative.casefold().endswith('.json'):
            raise PlanError('dynamic dependency inventory must be a source-analysis JSON document')
        added.append(relative)
    input_records = {item['path']: item['sha256'] for item in evidence if item['kind'] == 'candidate-input'}
    if input_records != {'b/native-kit/closure-evidence/candidate-plan.json': candidate_sha,
                         'b/native-kit/closure-evidence/candidate-report.json': report_sha}:
        raise PlanError('clean verification requires the exact original candidate plan and report bytes')
    for path in (receipt_path, ci_policy_path, provenance_path):
        relative = path.relative_to(root).as_posix()
        regular_under(root, relative)
        if relative.casefold() in seen:
            raise PlanError('closure output may not list its control files as raw evidence')
        seen.add(relative.casefold()); added.append(relative)
    for relative in added:
        entry = {'origin': 'main-build', 'source': relative[2:], 'destination': relative,
                 'sha256': digest(regular_under(root, relative))}
        if any(x['destination'].casefold() == relative.casefold() for x in plan['files']):
            raise PlanError('closure evidence collides with an existing plan file')
        plan['files'].append(entry)
    plan['files'].sort(key=lambda x: x['destination'].casefold())
    audit.check_provenance(provenance)
    if (provenance['source_sha'] != source_sha or provenance['source_tree'] != source_tree or
            provenance['configuration'] != 'RelWithDebInfo' or
            provenance['workflow_sha'] != os.environ.get('GITHUB_WORKFLOW_SHA') or
            provenance['conan_lock_sha256'] != digest(source / 'conan.lock') or
            provenance['conan_graph_sha256'] != digest(root / 'b/conan-install-graph.json')):
        raise PlanError('generated provenance differs from the actual workflow, source, Conan lock or installed graph')
    pin_document = read_json(regular_under(source, '.github/windows-native-kit/tool-pins.json'))
    pins = {item['name']: item for item in pin_document['artifacts']}
    tools = {item['name']: item for item in provenance['tools']}
    for name, pin_name in (('cmake', 'cmake'), ('ctest', 'cmake'), ('python', 'python'),
                           ('7z', '7z-extra'), ('ifw', 'ifw')):
        pin, tool = pins[pin_name], tools[name]
        if any(tool[field] != value for field, value in (('sha256', pin['sha256']),
                                                          ('version', pin['version']), ('origin', pin['url']))):
            raise PlanError('provenance differs from the actual source-pinned tool distribution: ' + name)
    # Recompute the complete case partition from reviewed source rules and
    # actual discovery; never trust a producer-written approved flag alone.
    ci = load_module('native_stage_ci_contract', 'run_native_ci_verification.py')
    launcher = load_module('native_stage_launcher_package', 'run_native_test_bundle.py')
    run_plan = read_json(root / 'b/native-kit/run-plan.json')
    run_paths, runtime_dirs, suites = launcher.validate_plan(run_plan, source_sha, source_tree, 'RelWithDebInfo')
    full_docs = {suite['id']: read_json(regular_under(root, suite['full_discovery'])) for suite in suites}
    selected_docs = {suite['id']: read_json(regular_under(root, suite['discovery'])) for suite in suites}
    manifest_stub = {'files': [{'path': item['destination']} for item in plan['files']]}
    try:
        derived_policy = verifier.derive_partition(reviewed, full_docs, source_sha, source_tree, logical_root,
                                                   [item['destination'] for item in plan['files']], report.get('coverage'))
        if ci_policy != derived_policy:
            raise PlanError('CI policy differs from deterministic source-reviewed case partition')
        decisions = ci.validate_policy(ci_policy, full_docs, source_sha, source_tree, 'RelWithDebInfo', manifest_stub)
        prepared = launcher.selection_plan(suites, full_docs, selected_docs, decisions, 'reviewed-subset')
    except (ci.CIError, launcher.LauncherError, ci.review.ReviewError, verifier.ClosureError) as exc:
        raise PlanError('CI policy or CTest selection does not close: ' + str(exc)) from exc
    approved = {(suite, case) for suite, items in decisions.items() for case, decision in items.items()
                if decision['status'] == 'approved'}
    actual = {(suite, case) for suite, result in prepared.items() for case in result['selected']}
    if not actual or not approved <= actual:
        raise PlanError('source-reviewed CI case groups are empty or not fully closed over CTest dependencies')
    for kind in ('case-source-review',):
        covered = set()
        for item in evidence:
            if item['kind'] != kind:
                continue
            cases = item.get('cases')
            if not isinstance(cases, list) or not cases:
                raise PlanError(kind + ' must identify the exact reviewed suite and cases')
            for case in cases:
                if (not isinstance(case, dict) or set(case) != {'suite', 'case'} or
                        not isinstance(case['suite'], str) or not isinstance(case['case'], str)):
                    raise PlanError('invalid suite/case binding in ' + kind)
                covered.add((case['suite'], case['case']))
        if not actual <= covered or not covered <= actual:
            raise PlanError(kind + ' does not cover exactly the selected CTest cases')
    inventories = [item for item in evidence if item['kind'] == 'dynamic-dependency-inventory']
    if len(inventories) != 1:
        raise PlanError('exactly one source-reviewed dynamic dependency inventory is required')
    inventory = read_json(regular_under(root, inventories[0]['path']))
    try:
        derived_inventory = verifier.derive_dynamic_inventory(reviewed, ci_policy, plan, full_docs, logical_root)
        verifier.verify_dynamic_inventory(inventory, derived_inventory)
    except verifier.ClosureError as exc:
        raise PlanError('dynamic inventory differs from the source-reviewed runtime rules: ' + str(exc)) from exc
    reviewed_pe_files = validate_dynamic_inventory(plan, inventory, actual, full_docs, logical_root, source_sha, source_tree)
    # A missing fixture, real application guard or other known condition must
    # not become approved merely through a policy record.
    for case in report.get('coverage', []):
        if case.get('status') == 'condition_missing' and case.get('case') and \
                any((suite == case.get('suite') or (suite in ('file-dialog', 'csv-runtime') and case.get('suite') == 'main'))
                    and name == case['case'] for suite, name in actual):
            raise PlanError('reviewed CI selection requires an unavailable condition: ' + case['case'])
    deferred = {'dynamic-dependencies-unreviewed', 'provenance-unverified', 'runtime-closure-unverified',
                'clean-job-unverified', 'source-selection-unreviewed', 'pe-import-needs-resolution',
                'unreadable-pe', 'conflicting-dll-basename'}
    blockers = []
    for item in report.get('blockers', []):
        if item.get('code') in deferred:
            continue
        if item.get('case') and not any(name == item['case'] and
                (suite == item.get('suite') or (suite in ('file-dialog', 'csv-runtime') and item.get('suite') == 'main'))
                for suite, name in actual):
            continue
        blockers.append(item)
    if blockers:
        raise PlanError('unresolved selected/global candidate inputs: ' + json.dumps(blockers, ensure_ascii=False))
    static_dirs = receipt.get('runtime_dirs')
    # Match the launcher's actual PATH. The driver's own application directory
    # is searched for that process, but is never placed in test-process PATH.
    expected_dirs = ci_pe_search_directories(run_paths, runtime_dirs, reviewed, logical_root)
    if (not isinstance(static_dirs, list) or any(not isinstance(x, str) for x in static_dirs) or
            [x.casefold() for x in static_dirs] != [x.casefold() for x in expected_dirs]):
        raise PlanError('closure runtime directories differ from the actual CI PATH and reviewed loader additions')
    # Recompute per-process AMD64 normal/delay closure using the exact pinned
    # source verifier and this host's System32-only resolver. Do not treat a
    # policy DLL name list or a global union of DLLs as loader evidence.
    try:
        manifest_files = [{'path': row['destination'], 'sha256': row['sha256']} for row in plan['files']]
        pair = verifier.derive_verified_python_pair(root, manifest_files, source_sha, source_tree, logical_root)
        processes = verifier.derive_pe_processes(suites, prepared, full_docs, inventory, manifest_files, logical_root)
        pe = verifier.resolve_candidate_pe_imports(
            plan, processes, static_dirs, os.environ.get('SystemRoot', ''),
            lambda name: verifier.windows_system_resolver(name, allow_not_found=True), python_pair=pair)
        host = [item for item in evidence if item['kind'] == 'host-system-resolution']
        if len(host) != 1:
            raise PlanError('a unique producer System32 import receipt is required')
        recorded = read_json(regular_under(root, host[0]['path']))
        if recorded != {'schema': 1, 'scope': pe['scope'], 'system_imports': pe['system_imports'],
                        'legacy_checks': pe['legacy_checks']}:
            raise PlanError('producer System32 imports differ from independent per-process resolution')
    except (verifier.ClosureError, pe_helper.PEError) as exc:
        raise PlanError('actual per-process PE static closure failed: ' + str(exc)) from exc
    estimated = sum(regular_under(plan['origins'][item['origin']]['root'], item['source']).stat().st_size
                    for item in plan['files'])
    if shutil.disk_usage(staging.parent).free < 2 * estimated + 2 * 1024**3 + 64 * 1024**2:
        raise PlanError('insufficient space for stage, conservative ZIP bound and two-GiB reserve')
    staged_plan = output / 'stage-plan.json'
    write_new(staged_plan, plan)
    audit.stage_allowlisted(staged_plan, staging, logical_root)
    capture = audit.create_manifest(staging, logical_root, provenance_path, staging / '_bundle/manifest.json')
    result = archive_captured_stage(staging, logical_root, archive, capture['manifest_sha256'])
    result.update({'schema': 1, 'status': 'staged-awaiting-independent-ci', 'source_sha': source_sha,
                   'source_tree': source_tree, 'configuration': 'RelWithDebInfo',
                   'ci_policy': 'b/native-kit/closure-evidence/ci-policy.json'})
    return result


def safe_relative(value, logical_root):
    if not isinstance(value, str):
        raise PlanError('relative file path must be a string')
    try:
        audit.check_windows_relative(value, logical_root)
    except audit.AuditError as exc:
        raise PlanError(str(exc)) from exc
    return value


def safe_conan_manifest_name(value):
    """Validate metadata names without admitting build-only files to staging.

    Conan manifests legitimately list static libraries and other build inputs.
    Such names are only parsed here. Selected files still pass the stricter
    payload allowlist and are independently hashed before they are copied.
    """
    if not isinstance(value, str) or not value or value.startswith('/') or '\\' in value:
        raise PlanError('invalid Conan package manifest path')
    for part in value.split('/'):
        if (part in ('', '.', '..') or part.endswith(('.', ' ')) or
                any(ord(ch) < 32 or ch in '<>:"|?*' for ch in part) or
                audit.is_reserved_component(part) or len(part.encode('utf-16-le')) // 2 > 255):
            raise PlanError('unsafe Conan package manifest path: ' + value)
    return value


def regular_under(root, relative):
    """Reject links anywhere beneath the root, including Windows junctions."""
    root = Path(root).absolute()
    path = root.joinpath(*relative.split('/'))
    for candidate in (path, *path.parents):
        info = candidate.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise PlanError('candidate has a link or reparse point: ' + relative)
        if candidate == root:
            break
    else:
        raise PlanError('candidate is outside its origin')
    if not path.is_file():
        raise PlanError('candidate is not a regular file: ' + relative)
    return path


def read_codemodel_json(path):
    """Read bounded CMake replies and reject ambiguous duplicate JSON keys."""
    if Path(path).stat().st_size > 64 * 1024 * 1024:
        raise PlanError('CMake File API JSON exceeds the size limit')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise PlanError('duplicate CMake File API JSON key: ' + key)
            result[key] = value
        return result
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=unique)
    except (ValueError, UnicodeError) as exc:
        raise PlanError('invalid CMake File API JSON: ' + str(path)) from exc


def inspect_codemodel(root, logical_root, reply_relative):
    """Select only the reviewed real targets from one original CMake reply.

    This determines candidate bytes; it does not prove that a target was
    compiled, loaded or run. Independent closure verification remains required.
    """
    root = Path(root).absolute()
    logical_root = audit.windows_root(logical_root)
    safe_relative(reply_relative, logical_root)
    reply = root.joinpath(*reply_relative.split('/'))
    audit.check_root(reply, logical_root)
    indexes = [path.name for path in reply.iterdir() if re.fullmatch(r'index-[A-Za-z0-9_.-]+\.json', path.name)]
    if len(indexes) != 1:
        raise PlanError('CMake File API requires exactly one original index')
    def read_named(name, pattern):
        if not isinstance(name, str) or not re.fullmatch(pattern, name):
            raise PlanError('unsafe or malformed CMake File API reply filename')
        rel = safe_relative(reply_relative + '/' + name, logical_root)
        path = regular_under(root, rel)
        audit.regular_file(path)
        audit.check_no_named_streams(path, False)
        return read_codemodel_json(path), rel
    index, index_path = read_named(indexes[0], r'index-[A-Za-z0-9_.-]+\.json')
    if not isinstance(index, dict):
        raise PlanError('malformed CMake File API index')
    cmake, reply_block = index.get('cmake'), index.get('reply')
    if not isinstance(cmake, dict) or not isinstance(reply_block, dict):
        raise PlanError('malformed CMake File API generator or reply block')
    generator, response = cmake.get('generator'), reply_block.get('codemodel-v2')
    if (not isinstance(generator, dict) or generator.get('name') != 'Ninja Multi-Config' or
            generator.get('multiConfig') is not True or not isinstance(response, dict) or
            response.get('kind') != 'codemodel' or not isinstance(response.get('version'), dict) or
            response['version'].get('major') != 2):
        raise PlanError('CMake File API requires the Ninja Multi-Config codemodel-v2 reply')
    model, model_path = read_named(response.get('jsonFile'), r'codemodel-v2-[A-Za-z0-9_.-]+\.json')
    if (not isinstance(model, dict) or model.get('kind') != 'codemodel' or
            not isinstance(model.get('version'), dict) or model['version'].get('major') != 2):
        raise PlanError('invalid CMake File API codemodel')
    paths = model.get('paths', {})
    for key, expected in (('source', 's'), ('build', 'b')):
        value = paths.get(key) if isinstance(paths, dict) else None
        if not isinstance(value, str) or not ntpath.isabs(value) or \
                ntpath.normcase(ntpath.normpath(value)) != ntpath.normcase(ntpath.join(logical_root, expected)):
            raise PlanError('CMake File API source or build root differs')
    configs = model.get('configurations')
    if not isinstance(configs, list):
        raise PlanError('CMake File API configurations are missing')
    matches = [x for x in configs if isinstance(x, dict) and x.get('name') == 'RelWithDebInfo']
    if len(matches) != 1 or not isinstance(matches[0].get('targets'), list):
        raise PlanError('CMake File API requires exactly one RelWithDebInfo configuration')
    refs = {}
    for ref in matches[0]['targets']:
        if not isinstance(ref, dict) or not isinstance(ref.get('name'), str) or not isinstance(ref.get('id'), str):
            raise PlanError('malformed CMake File API target reference')
        if ref['name'] in refs:
            raise PlanError('duplicate CMake File API target name: ' + ref['name'])
        refs[ref['name']] = ref
    verifier = load_module('native_stage_codemodel_contract', 'verify_native_ci_closure.py')
    rules = verifier.CODEMODEL_RULES
    if set(rules) != {'runtime-catalog-language', 'extension-manager'}:
        raise PlanError('unexpected reviewed CMake File API rule set')
    runners = {rule['target']: rule['runner'] for rule in rules.values()}
    plugins = {target for rule in rules.values() for target in rule['definitions'].values()}
    if len(runners) != 2 or sum(len(rule['definitions']) for rule in rules.values()) != 15 or len(plugins) != 14:
        raise PlanError('unexpected reviewed CMake File API target count')
    needed = set(runners) | plugins
    if set(runners) & plugins:
        raise PlanError('reviewed CMake File API runner and plugin targets overlap')
    reply_files = [index_path, model_path]
    targets, missing, artifact_paths = [], [], set()
    for name in sorted(needed):
        if name not in refs:
            missing.append({'target': name, 'reason': 'target is absent from the actual RelWithDebInfo codemodel'})
            continue
        ref = refs[name]
        try:
            obj, rel = read_named(ref.get('jsonFile'), r'target-[A-Za-z0-9_.+-]+\.json')
        except FileNotFoundError:
            missing.append({'target': name, 'reason': 'the referenced target reply JSON is missing'})
            continue
        expected_type = 'EXECUTABLE' if name in runners else 'SHARED_LIBRARY'
        if (not isinstance(obj, dict) or obj.get('name') != name or obj.get('id') != ref['id'] or
                obj.get('type') != expected_type):
            raise PlanError('CMake File API target identity differs: ' + name)
        if rel.casefold() in {x.casefold() for x in reply_files}:
            raise PlanError('CMake File API target reply is duplicated: ' + rel)
        reply_files.append(rel)
        suffix = '.exe' if name in runners else '.dll'
        artifacts = obj.get('artifacts')
        if not isinstance(artifacts, list):
            raise PlanError('CMake File API target artifacts are missing: ' + name)
        chosen = []
        for entry in artifacts:
            if not isinstance(entry, dict) or not isinstance(entry.get('path'), str):
                raise PlanError('invalid CMake File API artifact: ' + name)
            value = entry['path']
            if not value.casefold().endswith(suffix):
                continue
            if ntpath.isabs(value):
                full = value
            elif ntpath.splitdrive(value)[0] or value.startswith(('/', '\\')):
                raise PlanError('ambiguous CMake File API artifact path')
            else:
                full = ntpath.join(logical_root, 'b', value)
            # Reject traversal even if normalization would return under b/.
            parts = full.replace('\\', '/').split('/')
            if any(part in ('', '.', '..') or part.endswith((' ', '.')) for part in parts[1:]):
                raise PlanError('noncanonical CMake File API artifact path')
            relative = audit.to_relative(full, logical_root)
            safe_relative(relative, logical_root)
            if not relative.casefold().startswith('b/'):
                raise PlanError('CMake File API artifact leaves the main build tree')
            chosen.append(relative)
        if len(chosen) != 1:
            raise PlanError('CMake File API needs exactly one executable or DLL: ' + name)
        path = chosen[0]
        if name in runners and path.casefold() != runners[name].casefold():
            raise PlanError('CMake File API runner differs from the reviewed target: ' + name)
        if path.casefold() in artifact_paths:
            raise PlanError('CMake File API targets share an artifact: ' + path)
        artifact_paths.add(path.casefold())
        try:
            actual = regular_under(root, path)
        except FileNotFoundError:
            missing.append({'target': name, 'reason': 'the actual artifact is missing: ' + path})
            continue
        audit.regular_file(actual)
        audit.check_no_named_streams(actual, False)
        targets.append({'target': name, 'type': expected_type, 'path': path, 'sha256': digest(actual),
                        'json_file': ref['jsonFile']})
    # Preserve every reviewed macro separately even when two rules reuse one
    # target; this is a candidate mapping, not proof of compilation or loading.
    by_target = {item['target']: item for item in targets}
    missing_by_target = {item['target']: item['reason'] for item in missing}
    bindings = []
    rule_coverage = []
    for rule_name in sorted(rules):
        rule = rules[rule_name]
        required = {rule['target'], *rule['definitions'].values()}
        problems = [{'target': name, 'reason': missing_by_target[name]} for name in sorted(required) if name in missing_by_target]
        rule_coverage.append({'rule': rule_name, 'status': 'condition_missing' if problems else 'available', 'missing': problems})
        for macro, target in sorted(rule['definitions'].items()):
            row = {'rule': rule_name, 'definition': macro, 'target': target}
            if target in by_target:
                row.update(status='candidate-present', path=by_target[target]['path'], sha256=by_target[target]['sha256'])
            else:
                row.update(status='condition_missing', reason=missing_by_target[target])
            bindings.append(row)
    return {'index': index_path, 'reply_files': [{'path': x, 'sha256': digest(regular_under(root, x))}
                                                  for x in reply_files], 'targets': targets, 'bindings': bindings,
            'rule_coverage': rule_coverage}


def capture_codemodel(root, logical_root, source_sha, source_tree):
    """Retain raw query/reply bytes after the actual initial configure/build."""
    root = Path(root).absolute()
    logical_root = audit.windows_root(logical_root)
    if not audit.HEX40.fullmatch(source_sha) or not audit.HEX40.fullmatch(source_tree) or source_sha[:12] != logical_root[-12:]:
        raise PlanError('CMake File API capture source identity differs')
    audit.check_root(root, logical_root, require_exact=True)
    source = root / 's'
    # Main File API capture happens before media import and still requires a
    # genuinely clean source, even though the media job digest is available.
    verified_source_state(root, logical_root, source_sha, source_tree, allow_initial_clean=True)
    query = regular_under(root, 'b/.cmake/api/v1/query/codemodel-v2')
    if audit.regular_file(query).st_size != 0:
        raise PlanError('CMake File API original codemodel-v2 query is not empty')
    audit.check_no_named_streams(query, False)
    original = inspect_codemodel(root, logical_root, 'b/.cmake/api/v1/reply')
    output = root / 'b/native-kit/codemodel'
    audit.check_root(output, logical_root)
    if (output / 'query').exists() or (output / 'reply').exists():
        raise PlanError('refusing to reuse CMake File API retained evidence')
    (output / 'query').mkdir()
    (output / 'reply').mkdir()
    def copy_new(source_path, dest_path, expected):
        before = audit.regular_file(source_path)
        with source_path.open('rb') as src, dest_path.open('xb') as dst:
            shutil.copyfileobj(src, dst, 1024 * 1024)
        after = audit.regular_file(source_path)
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns) or \
                digest(source_path) != expected or digest(dest_path) != expected:
            raise PlanError('CMake File API reply changed while copying')
    copy_new(query, output / 'query/codemodel-v2', hashlib.sha256(b'').hexdigest())
    for item in original['reply_files']:
        source_path = regular_under(root, item['path'])
        copy_new(source_path, output / 'reply' / source_path.name, item['sha256'])
    retained = inspect_codemodel(root, logical_root, 'b/native-kit/codemodel/reply')
    if original['targets'] != retained['targets'] or original['bindings'] != retained['bindings'] or \
            original['rule_coverage'] != retained['rule_coverage'] or \
            [x['sha256'] for x in original['reply_files']] != [x['sha256'] for x in retained['reply_files']]:
        raise PlanError('retained CMake File API reply differs from the original')
    return {'schema': 1, 'source_sha': source_sha, 'source_tree': source_tree, 'configuration': 'RelWithDebInfo',
            'query': {'path': 'b/native-kit/codemodel/query/codemodel-v2', 'sha256': hashlib.sha256(b'').hexdigest()},
            **retained}


def select_codemodel_rules(root, logical_root, source_sha, source_tree, candidate_path, report_path, policy_path):
    """Compute actual source-reviewed/fixture-closed rules, never infer execution."""
    root = Path(root).absolute(); logical_root = audit.windows_root(logical_root)
    if (not audit.HEX40.fullmatch(source_sha) or not audit.HEX40.fullmatch(source_tree) or
            source_sha[:12] != logical_root[-12:]):
        raise PlanError('CMake rule selection needs the exact source identity')
    audit.check_root(root, logical_root, require_exact=True)
    expected_paths = ((candidate_path, 'b/native-kit/stage-candidate.json'),
                      (report_path, 'b/native-kit/stage-gaps.json'),
                      (policy_path, 's/.github/windows-native-kit/ci-closure-policy.json'))
    for value, relative in expected_paths:
        if Path(value).absolute() != root.joinpath(*relative.split('/')):
            raise PlanError('CMake rule selection input is not at its exact same-root path')
        regular_under(root, relative)
    source = root / 's'
    verified_source_state(root, logical_root, source_sha, source_tree)
    candidate, report, policy = map(read_json, (candidate_path, report_path, policy_path))
    verifier_path = regular_under(source, 'scripts/windows/verify_native_ci_closure.py')
    if (not isinstance(policy, dict) or policy.get('schema') != 2 or policy.get('verifier_sha256') != digest(verifier_path) or
            not isinstance(candidate, dict) or not isinstance(candidate.get('files'), list) or
            not isinstance(report, dict) or report.get('source_sha') != source_sha or report.get('source_tree') != source_tree or
            report.get('logical_root') != logical_root or report.get('configuration') != 'RelWithDebInfo'):
        raise PlanError('CMake rule selection candidate, report or reviewed verifier identity differs')
    verifier = load_reviewed_verifier(verifier_path)
    launcher = load_module('native_stage_codemodel_selection_launcher', 'run_native_test_bundle.py')
    ci = load_module('native_stage_codemodel_selection_ci', 'run_native_ci_verification.py')
    run_plan = read_json(regular_under(root, 'b/native-kit/run-plan.json'))
    _paths, _runtime_dirs, suites = launcher.validate_plan(run_plan, source_sha, source_tree, 'RelWithDebInfo')
    full = {item['id']: read_json(regular_under(root, item['full_discovery'])) for item in suites}
    selected_docs = {item['id']: read_json(regular_under(root, item['discovery'])) for item in suites}
    destinations = [item['destination'] for item in candidate['files']]
    try:
        partition = verifier.derive_partition(policy, full, source_sha, source_tree, logical_root,
                                              destinations, report.get('coverage'))
        decisions = ci.validate_policy(partition, full, source_sha, source_tree, 'RelWithDebInfo',
                                       {'files': [{'path': value} for value in destinations]})
        prepared = launcher.selection_plan(suites, full, selected_docs, decisions, 'reviewed-subset')
        ci.validate_ci_selection(prepared, decisions)
    except (verifier.ClosureError, ci.CIError, ci.review.ReviewError, launcher.review.ReviewError, launcher.LauncherError) as exc:
        raise PlanError('source-reviewed CMake rule selection does not close: ' + str(exc)) from exc
    cases = {name: [] for name in verifier.CODEMODEL_RULES}
    for suite, item in prepared.items():
        index = launcher.review.indexed(full[suite])
        for case in sorted(item['selected']):
            command = index[case][0].get('command')
            if not isinstance(command, list) or not command:
                raise PlanError('selected CTest case lacks its real runner: ' + case)
            try:
                runner = audit.to_relative(command[0], logical_root)
            except audit.AuditError as exc:
                raise PlanError('selected CTest runner is not same-root: ' + case) from exc
            for name, rule in verifier.CODEMODEL_RULES.items():
                if runner.casefold() == rule['runner'].casefold():
                    cases[name].append({'suite': suite, 'case': case})
    capture = read_codemodel_json(regular_under(root, 'b/native-kit/codemodel/capture.json'))
    if (not isinstance(capture, dict) or capture.get('source_sha') != source_sha or capture.get('source_tree') != source_tree or
            not isinstance(capture.get('rule_coverage'), list)):
        raise PlanError('CMake selection has no source-bound actual capture')
    status = {item['rule']: item for item in capture['rule_coverage'] if isinstance(item, dict) and 'rule' in item}
    if set(status) != set(cases):
        raise PlanError('CMake selection capture has an incomplete rule partition')
    records = []
    for name in sorted(cases):
        if cases[name] and status[name].get('status') != 'available':
            raise PlanError('a selected CMake rule has missing target inputs: ' + name)
        records.append({'rule': name, 'status': 'selected' if cases[name] else 'not_selected',
                        'cases': cases[name], 'target_condition': status[name]})
    return {'schema': 1, 'source_sha': source_sha, 'source_tree': source_tree,
            'basis': 'source-reviewed-planned-selection', 'rules': records}


def embedded_python_archive_members(archive_path, logical_root):
    """Enumerate exact top-level runtime members from the authenticated ZIP.

    The caller must already have checked the source-reviewed archive digest.
    Selection does not infer DLL names from the host or from another package.
    """
    required = {'python.exe', 'python3.dll', 'python312.dll', 'python312.zip', 'python312._pth', 'LICENSE.txt'}
    selected, folded = {}, set()
    with zipfile.ZipFile(archive_path) as archive:
        for info in archive.infolist():
            name = info.filename
            if '\\' in name:
                raise PlanError('Python ZIP member uses an ambiguous separator')
            if '/' in name or info.is_dir():
                continue
            if name not in required and PurePosixPath(name).suffix.casefold() not in {'.dll', '.pyd'}:
                continue
            safe_relative('t/python/' + name, logical_root)
            if name.casefold() in folded:
                raise PlanError('case-colliding Python ZIP runtime member: ' + name)
            if stat.S_ISLNK(info.external_attr >> 16) or info.flag_bits & 1:
                raise PlanError('linked or encrypted Python ZIP runtime member: ' + name)
            folded.add(name.casefold()); selected[name] = info
    if not required <= set(selected):
        raise PlanError('official Python ZIP lacks required runtime members: ' + ', '.join(sorted(required - set(selected))))
    return sorted(selected, key=str.casefold)


def verified_source_state(root, logical_root, source_sha, source_tree, *, allow_initial_clean=False):
    """Require clean tracked bytes and at most the exact authenticated media set."""
    root = Path(root).absolute(); source = root / 's'
    logical_root = audit.windows_root(logical_root)
    if (not audit.HEX40.fullmatch(source_sha) or not audit.HEX40.fullmatch(source_tree) or
            source_sha[:12] != logical_root[-12:]):
        raise PlanError('source state needs the exact full commit and tree identity')
    audit.check_root(root, logical_root, require_exact=True)
    if git(source, 'rev-parse', 'HEAD') != source_sha or git(source, 'rev-parse', 'HEAD^{tree}') != source_tree:
        raise PlanError('source checkout commit or tree differs')
    receipt = root / 'b/native-kit/media-fixtures/generation-receipt.json'
    expected = os.environ.get('PJ_MEDIA_MANIFEST_SHA256', '')
    if not receipt.is_file():
        if expected and not allow_initial_clean:
            raise PlanError('trusted media job was supplied but its generated-fixture receipt is missing')
        if git(source, 'status', '--porcelain=v1', '--untracked-files=all', '--ignore-submodules=none'):
            raise PlanError('source checkout is not clean')
        return None
    if not audit.HEX64.fullmatch(expected):
        raise PlanError('an independent media-generation job digest is required')
    verifier = load_reviewed_verifier(regular_under(source, 'scripts/windows/verify_native_ci_closure.py'))
    try:
        result = verifier.verify_generated_media(root, source_sha, source_tree, expected)
        raw = git(source, 'status', '--porcelain=v1', '-z', '--untracked-files=all',
                  '--ignore-submodules=none', binary=True).decode('utf-8', errors='strict')
        verifier.verify_generated_source_status(raw)
    except verifier.ClosureError as exc:
        raise PlanError('generated source fixtures failed independent identity or exact Git status: ' + str(exc)) from exc
    return result


def import_generated_media(root, logical_root, source_sha, source_tree, input_dir, expected_sha):
    """Import only the four authenticated CI fixtures into an initially clean clone."""
    root = Path(root).absolute(); source = root / 's'; input_dir = Path(input_dir).absolute()
    logical_root = audit.windows_root(logical_root)
    if (not audit.HEX40.fullmatch(source_sha) or not audit.HEX40.fullmatch(source_tree) or
            not audit.HEX64.fullmatch(expected_sha) or source_sha[:12] != logical_root[-12:] or
            os.environ.get('PJ_MEDIA_MANIFEST_SHA256') != expected_sha or
            os.environ.get('PJ_MEDIA_SOURCE_SHA') != source_sha or os.environ.get('PJ_MEDIA_SOURCE_TREE') != source_tree):
        raise PlanError('media job digest or exact source identity is missing or mismatched')
    audit.check_root(root, logical_root, require_exact=True)
    audit.check_root(input_dir, logical_root)
    if (git(source, 'rev-parse', 'HEAD') != source_sha or git(source, 'rev-parse', 'HEAD^{tree}') != source_tree or
            git(source, 'status', '--porcelain=v1', '--untracked-files=all', '--ignore-submodules=none')):
        raise PlanError('fixture import requires an initially clean exact source checkout')
    verifier = load_reviewed_verifier(regular_under(source, 'scripts/windows/verify_native_ci_closure.py'))
    names, relative_paths = verifier.SYNTHETIC_MEDIA_NAMES, verifier.SYNTHETIC_MEDIA_PATHS
    expected_names = ('test_480p.mp4', 'test_1080p_bframes.mp4', 'test_images.mcap', 'potato.mcap')
    if tuple(names) != expected_names or tuple(relative_paths) != tuple('s/pj_scene2D/testdata/' + x for x in expected_names):
        raise PlanError('source-reviewed generated media list differs from the four fixed paths')
    manifest_path = regular_under(input_dir, 'manifest.json')
    audit.regular_file(manifest_path); audit.check_no_named_streams(manifest_path, False)
    if digest(manifest_path) != expected_sha:
        raise PlanError('downloaded media manifest differs from the independent generation-job output')
    generator_path = regular_under(source, 'scripts/native-fixtures/generate_media_fixtures.py')
    if not __debug__:
        raise PlanError('media import forbids optimized Python assertions')
    spec = importlib.util.spec_from_file_location('native_generated_media_source', generator_path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    try:
        manifest = module.verify_manifest(input_dir, expected_sha)
    except (AssertionError, OSError, ValueError, KeyError, TypeError) as exc:
        raise PlanError('downloaded media bytes or semantic records failed verification: ' + str(exc)) from exc
    source_names = ('generate_media_fixtures.py', 'mcap_fixture_generator.cpp', 'mcap-source-lock.json')
    hashes = manifest.get('generator_sources')
    if not isinstance(hashes, dict) or set(hashes) != set(source_names):
        raise PlanError('media generator source identities are incomplete')
    for name in source_names:
        path = regular_under(source, 'scripts/native-fixtures/' + name)
        if digest(path) != hashes[name]:
            raise PlanError('media generator source differs from the trusted checkout: ' + name)
        git(source, 'ls-files', '--error-unmatch', '--', 'scripts/native-fixtures/' + name)
    total = 0
    for name in names:
        entry = manifest.get('files', {}).get(name)
        if (not isinstance(entry, dict) or set(entry) != {'bytes', 'sha256'} or type(entry['bytes']) is not int or
                not 0 < entry['bytes'] <= 512 * 1024**2 or not audit.HEX64.fullmatch(str(entry['sha256']))):
            raise PlanError('generated media manifest has an invalid file identity: ' + name)
        actual = regular_under(input_dir, name)
        info = audit.regular_file(actual); audit.check_no_named_streams(actual, False)
        if info.st_size != entry['bytes'] or digest(actual) != entry['sha256']:
            raise PlanError('generated media input bytes differ before copy: ' + name)
        total += info.st_size
    if total > 1024**3:
        raise PlanError('generated media inputs exceed the one-GiB import bound')
    lock = read_json(regular_under(source, 'scripts/native-fixtures/mcap-source-lock.json'))
    license_path = regular_under(input_dir, 'evidence/MCAP-LICENSE')
    audit.regular_file(license_path); audit.check_no_named_streams(license_path, False)
    if manifest.get('mcap_source') != lock or digest(license_path) != lock.get('license_sha256'):
        raise PlanError('media MCAP source or upstream license differs from the reviewed lock')
    for relative in relative_paths:
        tracked = git(source, 'ls-files', '-z', '--', relative[2:], binary=True)
        if tracked:
            raise PlanError('refusing to replace a Git-tracked media fixture: ' + relative)
        path = root.joinpath(*relative.split('/'))
        if path.exists() or path.is_symlink():
            raise PlanError('refusing to replace an existing media fixture: ' + relative)
    destination = source / 'pj_scene2D/testdata'
    audit.check_root(destination.parent, logical_root)
    if not destination.exists():
        destination.mkdir()
    audit.check_root(destination, logical_root)
    audit.check_no_named_streams(destination, True)
    control = root / 'b/native-kit/media-fixtures'
    if control.exists() or control.is_symlink():
        raise PlanError('refusing to reuse generated-media evidence directory')
    audit.check_root(control.parent, logical_root)
    control.mkdir()
    def copy_checked(source_path, target, expected_size, expected_hash):
        source_path = Path(source_path)
        before = audit.regular_file(source_path); audit.check_no_named_streams(source_path, False)
        with source_path.open('rb') as reader, target.open('xb') as writer:
            shutil.copyfileobj(reader, writer, 1024 * 1024)
        after = audit.regular_file(source_path)
        if ((before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns) or
                before.st_size != expected_size or digest(source_path) != expected_hash or
                digest(target) != expected_hash or target.stat().st_size != expected_size):
            raise PlanError('generated media input changed during exclusive copy: ' + target.name)
    copy_checked(manifest_path, control / 'manifest.json', manifest_path.stat().st_size, expected_sha)
    copy_checked(license_path, control / 'MCAP-LICENSE', license_path.stat().st_size, lock['license_sha256'])
    files = {}
    for name, relative in zip(names, relative_paths):
        entry = manifest['files'][name]
        copy_checked(regular_under(input_dir, name), root.joinpath(*relative.split('/')), entry['bytes'], entry['sha256'])
        files[relative] = {'bytes': entry['bytes'], 'sha256': entry['sha256']}
    receipt = {'schema': 1, 'source_sha': source_sha, 'source_tree': source_tree,
               'manifest_sha256': expected_sha, 'files': files}
    write_new(control / 'generation-receipt.json', receipt)
    verified_source_state(root, logical_root, source_sha, source_tree)
    return receipt


def git_environment():
    """Read the verified clone without inherited Git configuration or hooks."""
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith('GIT_')}
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull, GIT_ATTR_NOSYSTEM='1',
               GIT_TERMINAL_PROMPT='0', GIT_CONFIG_COUNT='1',
               GIT_CONFIG_KEY_0='core.fsmonitor', GIT_CONFIG_VALUE_0='false')
    return env


def git(source, *args, binary=False):
    result = subprocess.run(['git', '-C', str(source), *map(str, args)],
                            env=git_environment(), capture_output=True)
    if result.returncode:
        raise PlanError('git failed while inspecting the clean source: ' + str(args[0]))
    return result.stdout if binary else result.stdout.decode('utf-8', errors='strict').strip()


def cache_values(raw):
    """Read unique CMake cache entries without executing CMake code."""
    result = {}
    for line in raw.splitlines():
        if not line or line.startswith(('#', '//')):
            continue
        match = re.fullmatch(r'([^:=]+):([^=]+)=(.*)', line)
        if not match:
            raise PlanError('malformed CMakeCache entry')
        key, _kind, value = match.groups()
        if key in result:
            raise PlanError('duplicate CMakeCache entry: ' + key)
        result[key] = value
    return result


def validate_build_cache(values, logical_root, role, qt_version):
    """Bind each configured CMake tree to the exact source and test tools."""
    if role not in ('main', 'i18n') or not re.fullmatch(r'\d+\.\d+\.\d+', qt_version):
        raise PlanError('invalid build role or Qt version')
    if values.get('PJ_NATIVE_BUNDLE_MODE') != 'ON':
        raise PlanError('native-owned output mode must be enabled in each CMake cache')
    source = 's' if role == 'main' else 's/pj_app/tests/i18n'
    build = 'b' if role == 'main' else 'i'
    def absolute(relative):
        return ntpath.normcase(ntpath.normpath(ntpath.join(logical_root, *relative.split('/'))))
    def equal_path(key, expected):
        actual = values.get(key, '')
        if not ntpath.isabs(actual) or ntpath.normcase(ntpath.normpath(actual)) != absolute(expected):
            raise PlanError('CMakeCache path differs for ' + key)
    equal_path('CMAKE_HOME_DIRECTORY', source)
    equal_path('CMAKE_CACHEFILE_DIR', build)
    equal_path('CMAKE_COMMAND', 't/cmake/bin/cmake.exe')
    equal_path('CMAKE_MAKE_PROGRAM', 't/builder/Scripts/ninja.exe')
    equal_path('Python3_EXECUTABLE', 't/python/python.exe')
    equal_path('PJ_TEST_PYTHON', 't/python/python.exe')
    qt = f'q/{qt_version}/msvc2022_64'
    if absolute(qt) not in {ntpath.normcase(ntpath.normpath(x)) for x in values.get('CMAKE_PREFIX_PATH', '').split(';') if x}:
        raise PlanError('CMakeCache prefix does not contain the pinned same-root Qt')
    equal_path('PJ_IFW_TEST_ARCHIVE', 't/ifw/ifw.7z')
    equal_path('PJ_IFW_TEST_EXTRACTOR', 't/7z/7za.exe')
    if not audit.HEX64.fullmatch(values.get('PJ_IFW_TEST_EXTRACTOR_SHA256', '').lower()):
        raise PlanError('CMakeCache extractor hash is missing')
    if values.get('CMAKE_GENERATOR') != 'Ninja Multi-Config' or \
            'RelWithDebInfo' not in values.get('CMAKE_CONFIGURATION_TYPES', '').split(';'):
        raise PlanError('CMakeCache generator or configuration differs')
    if values.get('CMAKE_PROJECT_NAME') != ('plotjuggler4' if role == 'main' else 'plotjuggler4_i18n_tests'):
        raise PlanError('CMakeCache project role differs')
    if role == 'main':
        equal_path('CMAKE_TOOLCHAIN_FILE', 'b/conan_toolchain.cmake')
        if values.get('PJ_BUILD_TESTS') != 'ON' or values.get('PJ_PLUGIN_FEEDBACK_ACCEPTANCE') != 'ON':
            raise PlanError('main tree is missing required native test options')
        try:
            csv = audit.to_relative(values.get('PJ_CSV_RUNTIME_PLUGIN', ''), logical_root)
        except (audit.AuditError, ValueError) as exc:
            raise PlanError('CSV runtime plugin must use the exact same root') from exc
        csv_prefix = 'b/csv-prefix/lib/plotjuggler/plugins/csv-loader/'
        if not csv.casefold().startswith(csv_prefix.casefold()) or not csv.casefold().endswith('.dll'):
            raise PlanError('CMakeCache CSV plugin is not the staged native plugin')
    elif values.get('CMAKE_TOOLCHAIN_FILE'):
        raise PlanError('standalone i18n must not reuse the main Conan toolchain')
    compiler = values.get('CMAKE_CXX_COMPILER', '')
    if not ntpath.isabs(compiler) or ntpath.basename(compiler).casefold() != 'cl.exe':
        raise PlanError('CMakeCache does not identify the Windows MSVC compiler')
    result = {'source_dir': source, 'build_tree': build, 'qt': qt, 'compiler': compiler}
    if role == 'main':
        result['csv_plugin'] = csv
    return result


def compiler_context(root, logical_root, source_sha, source_tree, role):
    """Bind compiler evidence to one exact source and independent build role."""
    root = Path(root).absolute()
    logical_root = audit.windows_root(logical_root)
    audit.check_root(root, logical_root, require_exact=True)
    if (role not in ('main', 'i18n') or not audit.HEX40.fullmatch(source_sha) or
            not audit.HEX40.fullmatch(source_tree) or source_sha[:12] != logical_root[-12:]):
        raise PlanError('invalid compiler evidence source or role')
    build = 'b' if role == 'main' else 'i'
    return root, {'schema': 1, 'role': role, 'source_sha': source_sha, 'source_tree': source_tree,
                  'logical_root': logical_root, 'build_tree': build,
                  'source_dir': 's' if role == 'main' else 's/pj_app/tests/i18n'}


def compiler_path_key(value):
    """Require a local, absolute cl.exe path, never a search name or device path."""
    if (not isinstance(value, str) or not re.match(r'^[A-Za-z]:[\\/]', value) or
            ntpath.basename(value).casefold() != 'cl.exe' or
            any(x in ('', '.', '..') for x in re.split(r'[\\/]', value[3:])) or
            any(ord(x) < 32 or x in '<>"|?*;' for x in value) or ':' in value[2:]):
        raise PlanError('compiler must be an absolute local cl.exe path')
    return ntpath.normcase(ntpath.normpath(value))


def actual_compiler_identity(value):
    """Hash the real activated compiler without executing it or CMake code."""
    if os.name != 'nt':
        raise PlanError('compiler identity requires the actual Windows runner')
    compiler_path_key(value)
    path = Path(value)
    audit.check_root(path.parent, str(path.parent))
    before = path.lstat()
    if (not stat.S_ISREG(before.st_mode) or stat.S_ISLNK(before.st_mode) or
            getattr(before, 'st_file_attributes', 0) & 0x400):
        raise PlanError('compiler is not a real regular file')
    audit.check_no_named_streams(path, False)
    canonical = str(path.resolve(strict=True))
    if compiler_path_key(canonical) != compiler_path_key(value):
        raise PlanError('compiler path is not canonical')
    sha256 = digest(path)
    after = path.lstat()
    if ((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) !=
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) or
            stat.S_ISLNK(after.st_mode) or getattr(after, 'st_file_attributes', 0) & 0x400):
        raise PlanError('compiler changed while hashing')
    return {'path': canonical, 'sha256': sha256}


def activated_compiler_path():
    """Reject PATH/CWD shadowing outside the activated x64 MSVC toolset."""
    toolset = os.environ.get('VCToolsInstallDir', '')
    version = os.environ.get('VCToolsVersion', '')
    host = os.environ.get('VSCMD_ARG_HOST_ARCH', '')
    if (os.environ.get('VSCMD_ARG_TGT_ARCH') != 'x64' or host not in ('x64', 'x86') or
            not re.fullmatch(r'14\.4[0-9][0-9.]*', version) or
            ntpath.basename(toolset.rstrip('\\/')) != version):
        raise PlanError('activated x64 MSVC toolset identity is missing or inconsistent')
    expected = ntpath.join(toolset, 'bin', 'Host' + host, 'x64', 'cl.exe')
    found = shutil.which('cl.exe')
    if not found or compiler_path_key(found) != compiler_path_key(expected):
        raise PlanError('cl.exe resolves outside the activated MSVC toolset')
    return expected


def prepare_compiler_query(root, logical_root, source_sha, source_tree, role):
    """Create a fresh nonce query and freeze the activated compiler before configure."""
    root, context = compiler_context(root, logical_root, source_sha, source_tree, role)
    verified_source_state(root, logical_root, source_sha, source_tree, allow_initial_clean=True)
    identity = actual_compiler_identity(activated_compiler_path())
    build = context['build_tree']
    tree = root / build
    tree.mkdir(exist_ok=True)
    audit.check_root(tree, logical_root)
    if (tree / 'CMakeCache.txt').exists() or (tree / '.cmake/api').exists():
        raise PlanError('compiler query requires a new unconfigured CMake tree')
    base = tree / 'native-kit/compiler'
    base.parent.mkdir(exist_ok=True)
    audit.check_root(base.parent, logical_root)
    base.mkdir()
    client = 'client-native-compiler-' + role + '-' + secrets.token_hex(16)
    query = tree / '.cmake/api/v1/query' / client / 'toolchains-v1'
    # Check an existing .cmake parent before creating any descendants.
    if (tree / '.cmake').exists():
        audit.check_root(tree / '.cmake', logical_root)
    query.parent.mkdir(parents=True)
    audit.check_root(query.parent, logical_root)
    with query.open('xb'):
        pass
    if role == 'main':
        with (query.parent.parent / 'codemodel-v2').open('xb'):
            pass
    return {**context, 'compiler': identity, 'client': client,
            'query': {'path': query.relative_to(root).as_posix(), 'sha256': hashlib.sha256(b'').hexdigest()}}


def read_compiler_expectation(root, context, expected_sha256):
    """Validate the preconfigure record against a digest held by the caller."""
    base = context['build_tree'] + '/native-kit/compiler'
    path = regular_under(root, base + '/expected.json')
    if not audit.HEX64.fullmatch(str(expected_sha256)) or digest(path) != expected_sha256:
        raise PlanError('preconfigure compiler expectation changed')
    record = read_codemodel_json(path)
    if not isinstance(record, dict) or any(record.get(k) != v for k, v in context.items()):
        raise PlanError('compiler expectation source or role differs')
    client = record.get('client')
    if not isinstance(client, str) or not re.fullmatch('client-native-compiler-' + context['role'] + r'-[0-9a-f]{32}', client):
        raise PlanError('invalid compiler query freshness token')
    expected_query = {'path': context['build_tree'] + '/.cmake/api/v1/query/' + client + '/toolchains-v1',
                      'sha256': hashlib.sha256(b'').hexdigest()}
    compiler = record.get('compiler')
    if (record.get('query') != expected_query or not isinstance(compiler, dict) or
            set(compiler) != {'path', 'sha256'} or not audit.HEX64.fullmatch(str(compiler.get('sha256')))):
        raise PlanError('malformed preconfigure compiler identity or query')
    compiler_path_key(compiler.get('path'))
    return record


def inspect_compiler_reply(root, logical_root, expectation, reply_relative, query_relative):
    """Read only nonce-bound toolchains-v1 JSON; never execute generated .cmake."""
    query = regular_under(root, safe_relative(query_relative, logical_root))
    if audit.regular_file(query).st_size or digest(query) != expectation['query']['sha256']:
        raise PlanError('compiler File API query changed')
    audit.check_no_named_streams(query, False)
    reply = Path(root) / safe_relative(reply_relative, logical_root)
    audit.check_root(reply, logical_root)
    indexes = [p.name for p in reply.iterdir() if p.name.startswith('index-')]
    if len(indexes) != 1:
        raise PlanError('compiler File API requires exactly one fresh index')
    def read_named(name, pattern):
        if not isinstance(name, str) or not re.fullmatch(pattern, name):
            raise PlanError('unsafe compiler File API reply filename')
        relative = safe_relative(reply_relative + '/' + name, logical_root)
        path = regular_under(root, relative)
        audit.regular_file(path)
        audit.check_no_named_streams(path, False)
        return read_codemodel_json(path), {'path': relative, 'sha256': digest(path)}
    index, index_file = read_named(indexes[0], r'index-[A-Za-z0-9_.-]+\.json')
    if not isinstance(index, dict):
        raise PlanError('malformed compiler File API index')
    cmake, replies, objects = index.get('cmake'), index.get('reply'), index.get('objects')
    if (not isinstance(cmake, dict) or cmake.get('generator') != {'name': 'Ninja Multi-Config', 'multiConfig': True} or
            not isinstance(replies, dict) or not isinstance(objects, list)):
        raise PlanError('compiler File API generator or index differs')
    clients = [key for key in replies if key.startswith('client-native-compiler-')]
    response = replies.get(expectation['client'])
    if clients != [expectation['client']] or not isinstance(response, dict) or set(response) != {'toolchains-v1'}:
        raise PlanError('stale or ambiguous compiler File API client')
    response = response['toolchains-v1']
    if (not isinstance(response, dict) or set(response) != {'kind', 'version', 'jsonFile'} or
            response.get('kind') != 'toolchains' or response.get('version') != {'major': 1, 'minor': 0} or
            [obj for obj in objects if isinstance(obj, dict) and obj.get('kind') == 'toolchains'] != [response]):
        raise PlanError('compiler toolchains reply is not uniquely bound to its index')
    model, model_file = read_named(response['jsonFile'], r'toolchains-v1-[A-Za-z0-9_.-]+\.json')
    if (not isinstance(model, dict) or model.get('kind') != 'toolchains' or
            model.get('version') != {'major': 1, 'minor': 0} or not isinstance(model.get('toolchains'), list) or
            any(not isinstance(item, dict) or not isinstance(item.get('language'), str) for item in model['toolchains'])):
        raise PlanError('malformed compiler toolchains object')
    cxx = [item for item in model['toolchains'] if item['language'] == 'CXX']
    if len(cxx) != 1 or not isinstance(cxx[0].get('compiler'), dict) or cxx[0]['compiler'].get('id') != 'MSVC':
        raise PlanError('toolchains must identify exactly one actual MSVC CXX compiler')
    if compiler_path_key(cxx[0]['compiler'].get('path')) != compiler_path_key(expectation['compiler']['path']):
        raise PlanError('actual CXX compiler differs from the preconfigure expectation')
    return [{'path': query_relative, 'sha256': digest(query)}, index_file, model_file]


def capture_compiler_evidence(root, logical_root, source_sha, source_tree, role, qt_version, expected_sha256, phase):
    """Preflight before build, then snapshot final evidence after all build work."""
    if phase not in ('preflight', 'final'):
        raise PlanError('invalid compiler evidence phase')
    root, context = compiler_context(root, logical_root, source_sha, source_tree, role)
    verified_source_state(root, logical_root, source_sha, source_tree, allow_initial_clean=phase == 'preflight')
    expected = read_compiler_expectation(root, context, expected_sha256)
    if actual_compiler_identity(expected['compiler']['path']) != expected['compiler']:
        raise PlanError('preconfigure compiler bytes changed')
    build = context['build_tree']
    cache = regular_under(root, build + '/CMakeCache.txt')
    fields = validate_build_cache(cache_values(cache.read_text(encoding='utf-8')), logical_root, role, qt_version)
    if compiler_path_key(fields['compiler']) != compiler_path_key(expected['compiler']['path']):
        raise PlanError('cached compiler differs from the preconfigure expectation')
    original = inspect_compiler_reply(root, logical_root, expected, build + '/.cmake/api/v1/reply', expected['query']['path'])
    base = build + '/native-kit/compiler/' + phase
    output = root / base
    output.mkdir()
    (output / 'reply').mkdir()
    files = []
    for number, row in enumerate(original):
        destination = base + ('/toolchains-v1' if number == 0 else '/reply/' + Path(row['path']).name)
        source = regular_under(root, row['path'])
        target = root / destination
        with source.open('rb') as src, target.open('xb') as dst:
            shutil.copyfileobj(src, dst)
        if digest(source) != row['sha256'] or digest(target) != row['sha256']:
            raise PlanError('compiler evidence changed while retaining bytes')
        files.append({'path': destination, 'sha256': row['sha256']})
    if inspect_compiler_reply(root, logical_root, expected, base + '/reply', base + '/toolchains-v1') != files:
        raise PlanError('retained compiler evidence differs')
    return {**context, 'phase': phase, 'expected_sha256': expected_sha256,
            'cmake_cache_sha256': digest(cache), 'files': files, 'original_files': original}


def verify_compiler_evidence(root, logical_root, source_sha, source_tree, role, expected_sha256, receipt_sha256, phase,
                             live=False):
    """Revalidate retained bytes; only the producer can also inspect live inputs."""
    if phase not in ('preflight', 'final'):
        raise PlanError('invalid compiler evidence phase')
    root, context = compiler_context(root, logical_root, source_sha, source_tree, role)
    expected = read_compiler_expectation(root, context, expected_sha256)
    base = context['build_tree'] + '/native-kit/compiler/' + phase
    receipt_path = regular_under(root, base + '.json')
    if not audit.HEX64.fullmatch(str(receipt_sha256)) or digest(receipt_path) != receipt_sha256:
        raise PlanError('compiler evidence receipt changed')
    record = read_codemodel_json(receipt_path)
    if (not isinstance(record, dict) or any(record.get(k) != v for k, v in context.items()) or
            record.get('phase') != phase or record.get('expected_sha256') != expected_sha256 or
            not audit.HEX64.fullmatch(str(record.get('cmake_cache_sha256')))):
        raise PlanError('compiler evidence source, role or phase differs')
    files = inspect_compiler_reply(root, logical_root, expected, base + '/reply', base + '/toolchains-v1')
    if record.get('files') != files:
        raise PlanError('retained compiler evidence hashes differ')
    original = [{'path': expected['query']['path'], 'sha256': files[0]['sha256']}] + [
        {'path': context['build_tree'] + '/.cmake/api/v1/reply/' + Path(row['path']).name, 'sha256': row['sha256']}
        for row in files[1:]]
    if record.get('original_files') != original:
        raise PlanError('compiler evidence original paths differ')
    if live:
        if (actual_compiler_identity(expected['compiler']['path']) != expected['compiler'] or
                digest(regular_under(root, context['build_tree'] + '/CMakeCache.txt')) != record['cmake_cache_sha256'] or
                inspect_compiler_reply(root, logical_root, expected, context['build_tree'] + '/.cmake/api/v1/reply',
                                       expected['query']['path']) != original):
            raise PlanError('live compiler evidence changed after capture')
    return expected, [context['build_tree'] + '/native-kit/compiler/expected.json', base + '.json'] + [x['path'] for x in files]


def capture_build_identity(root, logical_root, source_sha, source_tree, role, qt_version, windows_sdk, msvc,
                           expected_sha256, preflight_sha256):
    """Read and hash real Windows configure inputs, never package CMakeCache."""
    if os.name != 'nt':
        raise PlanError('build identity capture requires the actual Windows runner')
    root = Path(root).absolute()
    logical_root = audit.windows_root(logical_root)
    audit.check_root(root, logical_root, require_exact=True)
    if not audit.HEX40.fullmatch(source_sha) or not audit.HEX40.fullmatch(source_tree) or source_sha[:12] != logical_root[-12:]:
        raise PlanError('invalid source identity for build capture')
    source = root / 's'
    verified_source_state(root, logical_root, source_sha, source_tree)
    if not re.fullmatch(r'[0-9.\\]+', windows_sdk or '') or not re.fullmatch(r'14\.4[0-9][0-9.]*', msvc or ''):
        raise PlanError('missing or invalid Windows SDK or MSVC toolset version')
    cache_rel = ('b' if role == 'main' else 'i') + '/CMakeCache.txt'
    cache = regular_under(root, cache_rel)
    data = cache.read_bytes()
    fields = validate_build_cache(cache_values(data.decode('utf-8')), logical_root, role, qt_version)
    cache_digest = hashlib.sha256(data).hexdigest()
    tools = {}
    for name, relative in (('cmake', 't/cmake/bin/cmake.exe'), ('python', 't/python/python.exe'),
                           ('ninja', 't/builder/Scripts/ninja.exe'), ('qt_core', fields['qt'] + '/bin/Qt6Core.dll'),
                           ('ifw', 't/ifw/ifw.7z'), ('extractor', 't/7z/7za.exe')):
        path = regular_under(root, relative)
        tools[name] = {'path': relative, 'sha256': digest(path)}
    if tools['extractor']['sha256'] != cache_values(data.decode('utf-8'))['PJ_IFW_TEST_EXTRACTOR_SHA256'].lower():
        raise PlanError('configured IFW extractor hash differs from its actual bytes')
    if role == 'main':
        plugin = regular_under(root, fields['csv_plugin'])
        spec = importlib.util.spec_from_file_location('native_csv_identity', source / 'packaging/localization/run_csv_runtime_acceptance.py')
        csv_gate = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(csv_gate)
        staged = csv_gate.staged_csv(root / 'b/csv-prefix')
        if os.path.normcase(os.path.normpath(str(staged))) != os.path.normcase(os.path.normpath(str(plugin))):
            raise PlanError('configured CSV plugin differs from the verified staged DLL')
        tools['csv_plugin'] = {'path': fields['csv_plugin'], 'sha256': digest(plugin)}
    expected, _ = verify_compiler_evidence(root, logical_root, source_sha, source_tree, role,
                                           expected_sha256, preflight_sha256, 'preflight')
    final = capture_compiler_evidence(root, logical_root, source_sha, source_tree, role, qt_version,
                                      expected_sha256, 'final')
    final_path = root / fields['build_tree'] / 'native-kit/compiler/final.json'
    write_new(final_path, final)
    return {'schema': 1, 'role': role, 'source_sha': source_sha, 'source_tree': source_tree,
            'configuration': 'RelWithDebInfo', 'source_dir': fields['source_dir'], 'build_tree': fields['build_tree'],
            'native_bundle_mode': True, 'cmake_cache_sha256': cache_digest, 'generator': 'Ninja Multi-Config', 'qt_version': qt_version,
            'windows_sdk': windows_sdk, 'msvc_toolset': msvc,
            'compiler': expected['compiler'], 'tools': tools,
            'compiler_evidence': {'expected_sha256': expected_sha256, 'preflight_sha256': preflight_sha256,
                                  'final_sha256': digest(final_path)}}


class Candidate:
    """Collect an explicit list of file bytes and report every unresolved case."""

    def __init__(self, root, logical_root, source_sha, source_tree, declarations=None):
        self.root = Path(root).absolute()
        self.logical_root = audit.windows_root(logical_root)
        if not audit.HEX40.fullmatch(source_sha) or not audit.HEX40.fullmatch(source_tree):
            raise PlanError('full source commit and tree IDs are required')
        if source_sha[:12] != self.logical_root[-12:]:
            raise PlanError('source commit prefix does not match logical root')
        self.source_sha, self.source_tree = source_sha, source_tree
        self.source = self.root / 's'
        try:
            audit.check_root(self.root, self.logical_root, require_exact=True)
        except (audit.AuditError, OSError) as exc:
            raise PlanError(str(exc)) from exc
        if not self.source.is_dir():
            raise PlanError('same-root source directory is missing')
        self.generated_media = verified_source_state(self.root, self.logical_root, source_sha, source_tree)
        status = git(self.source, 'submodule', 'status', '--recursive')
        if any(line[:1] in ('-', '+', 'U') for line in status.splitlines()):
            raise PlanError('source has an uninitialized, divergent or conflicted submodule')
        try:
            self.modules = source_helper.module_map(self.source, env=git_environment())
        except (source_helper.SourceError, OSError, UnicodeError) as exc:
            raise PlanError('cannot establish recursive submodule identities: ' + str(exc)) from exc
        self.origins = {
            'project': {'root': str(self.source), 'description': 'Tracked PlotJuggler source',
                        'revision': source_sha, 'license_files': ['s/LICENSE']},
            'main-build': {'root': str(self.root / 'b'), 'description': 'Main test build from exact source',
                           'revision': source_sha, 'license_files': ['s/LICENSE']},
            'i18n-build': {'root': str(self.root / 'i'), 'description': 'Standalone language build from exact source',
                           'revision': source_sha, 'license_files': ['s/LICENSE']},
        }
        self.origin_prefixes = {'project': 's', 'main-build': 'b', 'i18n-build': 'i'}
        for index, item in enumerate(self.modules):
            name = f'submodule-{index + 1}'
            relative = item['path']
            safe_relative('s/' + relative, self.logical_root)
            module_root = self.source.joinpath(*relative.split('/'))
            licenses = [x for x in ('LICENSE', 'LICENSE.txt', 'COPYING', 'COPYING.txt')
                        if (module_root / x).is_file()]
            if not licenses:
                raise PlanError('submodule needs an explicit root license: ' + relative)
            self.origins[name] = {'root': str(module_root), 'description': 'Tracked source submodule ' + relative,
                                  'revision': item['sha'],
                                  'license_files': ['s/' + relative + '/' + x for x in licenses]}
            self.origin_prefixes[name] = 's/' + relative
        for name in ('main-build', 'i18n-build'):
            if not Path(self.origins[name]['root']).is_dir():
                raise PlanError('configured test tree is missing: ' + name)
        self.files = {}
        self.directories = {'r'}
        self.blockers = []
        self.cases = []
        self.discoveries = {}
        self.allowed_outputs = {}
        self.runtime_dirs = []
        self.marker_guard_paths = None
        self.condition_patterns = [
            ('main', 'MainWindowLayoutImportE2ETest',
             'The separate live MCAP cloud service, real plugins and vectors are not supplied.'),
            ('main', 'WindowsApplicationContract',
             'Real Windows app-marker probe and token/NTFS negative-control evidence are not yet bound.'),
            ('main', 'ArduPilotLayoutRestoreTest',
             'Real Windows app-marker probe and token/NTFS negative-control evidence are not yet bound.'),
        ]
        self.tracked = set()
        self.add_tracked_source()
        self.add_generated_media()
        self.add_verified_tools()
        self.add_conan_runtime_candidates()
        self.add_test_input_candidates()
        if declarations is not None:
            self.add_declarations(declarations)

    def issue(self, code, detail, *, suite=None, case=None):
        self.blockers.append({'code': code, 'detail': detail, 'suite': suite, 'case': case})

    def add(self, origin, relative):
        if origin not in self.origins:
            raise PlanError('unknown source origin: ' + str(origin))
        relative = safe_relative(relative, self.logical_root)
        prefix = self.origin_prefixes[origin]
        destination = safe_relative(prefix + '/' + relative, self.logical_root)
        if destination.split('/')[0].casefold() == '_bundle':
            raise PlanError('reserved manifest directory cannot be selected')
        path = regular_under(self.origins[origin]['root'], relative)
        before = path.stat()
        value = digest(path)
        after = path.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise PlanError('candidate changed while hashing: ' + destination)
        item = {'origin': origin, 'source': relative, 'destination': destination, 'sha256': value}
        key = destination.casefold()
        prior = self.files.get(key)
        if prior and prior != item:
            raise PlanError('duplicate or case-colliding candidate destination: ' + destination)
        self.files[key] = item

    def add_tracked_source(self):
        raw = git(self.source, 'ls-files', '--recurse-submodules', '--stage', '-z', binary=True)
        modules = sorted(((v, self.origin_prefixes[v][2:]) for v in self.origins if v.startswith('submodule-')),
                         key=lambda item: len(item[1]), reverse=True)
        for entry in raw.split(b'\0'):
            if not entry:
                continue
            try:
                header, raw_name = entry.split(b'\t', 1)
                mode, _oid, stage = header.decode('ascii').split()
                name = raw_name.decode('utf-8', errors='strict')
            except (ValueError, UnicodeError) as exc:
                raise PlanError('malformed Git tracked-file entry') from exc
            if mode not in ('100644', '100755') or stage != '0':
                raise PlanError('tracked source is not an ordinary, resolved file: ' + name)
            # Conan backup blobs are build-time caches, not source test inputs.
            if name.startswith('.github/conan/source-backup/'):
                continue
            origin, local = 'project', name
            for candidate, prefix in modules:
                if name.startswith(prefix + '/'):
                    origin, local = candidate, name[len(prefix) + 1:]
                    break
            self.add(origin, local)
            self.tracked.add(('s/' + name).casefold())
        if 's/license' not in self.tracked:
            raise PlanError('tracked project license is missing')

    def add_generated_media(self):
        if not self.generated_media:
            return
        control = 'native-kit/media-fixtures/'
        for name in ('manifest.json', 'generation-receipt.json', 'MCAP-LICENSE'):
            self.add('main-build', control + name)
        self.origins['generated-media'] = {'root': str(self.source / 'pj_scene2D/testdata'),
            'description': 'Synthetic CI media bound to an independent generation-job digest',
            'revision': self.generated_media['manifest_sha256'],
            'license_files': ['s/LICENSE', 'b/native-kit/media-fixtures/MCAP-LICENSE']}
        self.origin_prefixes['generated-media'] = 's/pj_scene2D/testdata'
        for relative in self.generated_media['files']:
            self.add('generated-media', relative.rsplit('/', 1)[-1])

    def add_declarations(self, doc):
        """Use only explicitly named files and source origins; preserve paths."""
        if not isinstance(doc, dict) or doc.get('schema') != 1:
            raise PlanError('invalid explicit candidate-input declaration')
        origins, files = doc.get('origins', {}), doc.get('files', [])
        if not isinstance(origins, dict) or not isinstance(files, list):
            raise PlanError('candidate origins and files have invalid types')
        for name, entry in origins.items():
            if not isinstance(name, str) or not re.fullmatch(r'[a-z0-9][a-z0-9._-]*', name) or name in self.origins:
                raise PlanError('invalid or duplicate declared origin')
            if not isinstance(entry, dict) or set(entry) != {'root', 'description', 'revision', 'license_files'}:
                raise PlanError('declared origin requires root, description, revision and licenses')
            prefix = safe_relative(entry['root'], self.logical_root)
            if prefix.split('/')[0] not in {'q', 'c', 't', 'b', 'i'}:
                raise PlanError('declared origin must be a known same-root tree')
            root = self.root.joinpath(*prefix.split('/'))
            if not root.is_dir():
                raise PlanError('declared origin directory is missing: ' + prefix)
            try:
                audit.check_root(root, self.logical_root)
            except (audit.AuditError, OSError) as exc:
                raise PlanError(str(exc)) from exc
            description, revision, licenses = entry['description'], entry['revision'], entry['license_files']
            if (not isinstance(description, str) or not description.strip() or len(description) > 256 or
                    any(c in description for c in ('\n', '\r', '?', '@')) or
                    not isinstance(revision, str) or not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', revision) or
                    not isinstance(licenses, list) or not licenses):
                raise PlanError('invalid declared origin identity, description or licenses')
            for license_path in licenses:
                safe_relative(license_path, self.logical_root)
            self.origins[name] = {'root': str(root), 'description': description,
                                  'revision': revision, 'license_files': licenses}
            self.origin_prefixes[name] = prefix
        for item in files:
            if not isinstance(item, dict) or set(item) != {'origin', 'source'}:
                raise PlanError('each explicit file needs only origin and source')
            self.add(item['origin'], item['source'])

    def add_verified_tools(self):
        """Select files from helper-verified official tool distributions."""
        record_path = self.root / 't/tool-provenance.json'
        if not record_path.is_file():
            self.issue('missing-tool-provenance', 't/tool-provenance.json')
            return
        record = read_json(regular_under(self.root, 't/tool-provenance.json'))
        pins = read_json(regular_under(self.root, 's/.github/windows-native-kit/tool-pins.json'))
        if record.get('schema') != 1 or pins.get('schema') != 1 or \
                not isinstance(record.get('distributions'), list) or not isinstance(pins.get('artifacts'), list):
            raise PlanError('invalid verified-tool provenance or pin manifest')
        pin_map = {item.get('name'): item for item in pins['artifacts'] if isinstance(item, dict)}
        records = {item.get('name'): item for item in record['distributions'] if isinstance(item, dict)}
        required = {'cmake', 'python', '7zr-bootstrap', '7z-extra', 'ifw'}
        if set(pin_map) != required or set(records) != required or \
                len(pin_map) != len(pins['artifacts']) or len(records) != len(record['distributions']):
            raise PlanError('missing or duplicate pinned tool distribution')
        for name in sorted(required):
            pin, actual = pin_map[name], records[name]
            try:
                tools_helper.validate_pin(pin)
            except tools_helper.ToolError as exc:
                raise PlanError('invalid fixed tool pin: ' + name) from exc
            for field in ('name', 'version', 'url', 'sha256', 'source'):
                if not isinstance(pin.get(field), str) or actual.get(field) != pin[field]:
                    raise PlanError('tool provenance does not match pinned ' + name + ': ' + field)
            if not re.fullmatch(r'[A-Za-z0-9_.-]+', str(pin.get('file', ''))) or not audit.HEX64.fullmatch(pin['sha256']):
                raise PlanError('invalid pinned tool archive identity: ' + name)
            archive = regular_under(self.root, 'd/' + pin['file'])
            if digest(archive) != pin['sha256'] or ('bytes' in pin and archive.stat().st_size != pin['bytes']):
                raise PlanError('retained tool archive differs from its pin: ' + name)
        runtime = record.get('runtime_files')
        if not isinstance(runtime, dict):
            raise PlanError('missing extracted runtime tool hashes')
        for field, relative in (('7za_sha256', 't/7z/7za.exe'), ('ifw_sha256', 't/ifw/ifw.7z'),
                                ('python_pth_sha256', 't/python/python312._pth')):
            if not audit.HEX64.fullmatch(str(runtime.get(field, ''))) or digest(regular_under(self.root, relative)) != runtime[field]:
                raise PlanError('extracted tool identity differs: ' + relative)
        origins = {
            'driver-python': {'root': 't/python', 'description': 'Pinned Python embeddable distribution',
                              'revision': pin_map['python']['sha256'], 'license_files': ['t/python/LICENSE.txt']},
            'portable-cmake': {'root': 't/cmake', 'description': 'Pinned CMake CTest distribution',
                               'revision': pin_map['cmake']['sha256'],
                               'license_files': ['t/cmake/' + path for path in tools_helper.CMAKE_NOTICE_FILES]},
            'portable-7z': {'root': 't/7z', 'description': 'Pinned 7-Zip extra distribution',
                            'revision': pin_map['7z-extra']['sha256'], 'license_files': ['t/7z/License.txt']},
            'pinned-ifw': {'root': 't/ifw', 'description': 'Pinned Qt Installer Framework archive',
                           'revision': pin_map['ifw']['sha256'], 'license_files': []},
            'tool-evidence': {'root': 't', 'description': 'Generated verified tool provenance',
                              'revision': self.source_sha, 'license_files': ['s/LICENSE']},
        }
        ifw_root = self.root / 't/ifw'
        notices = sorted(p.relative_to(ifw_root).as_posix() for p in (ifw_root / 'notices').rglob('*') if p.is_file())
        if not notices:
            raise PlanError('verified IFW license notices are missing')
        origins['pinned-ifw']['license_files'] = ['t/ifw/' + item for item in notices]
        files = [{'origin': 'tool-evidence', 'source': 'tool-provenance.json'},
                 {'origin': 'portable-7z', 'source': '7za.exe'}, {'origin': 'portable-7z', 'source': 'License.txt'},
                 {'origin': 'pinned-ifw', 'source': 'ifw.7z'}]
        files += [{'origin': 'pinned-ifw', 'source': item} for item in notices]
        python_root = self.root / 't/python'
        python_archive = regular_under(self.root, 'd/' + pin_map['python']['file'])
        python_files = embedded_python_archive_members(python_archive, self.logical_root)
        expected_python = {name.casefold(): name for name in python_files}
        actual_runtime = {}
        for path in python_root.iterdir():
            if path.suffix.casefold() not in {'.dll', '.pyd'}:
                continue
            folded = path.name.casefold()
            if folded in actual_runtime or folded not in expected_python or path.name != expected_python[folded]:
                raise PlanError('unexpected or case-colliding extracted Python runtime file: ' + path.name)
            actual_runtime[folded] = path.name
        for name in python_files:
            try:
                regular_under(python_root, name)
            except FileNotFoundError as exc:
                raise PlanError('pinned embedded Python runtime is missing: ' + name) from exc
        cmake_root = self.root / 't/cmake'
        cmake_files = ['bin/cmake.exe', 'bin/ctest.exe',
                       'share/cmake-3.31/Modules/GoogleTestAddTests.cmake', *tools_helper.CMAKE_NOTICE_FILES]
        cmake_files += [(Path('bin') / p.name).as_posix() for p in (cmake_root / 'bin').iterdir()
                        if p.is_file() and p.suffix.casefold() == '.dll']
        # Except for the deliberately extended ._pth file, the selected ZIP
        # entries must match the exact official archives that the helper pinned.
        for name, root, members, prefix in (
                ('python', python_root, [x for x in python_files if x != 'python312._pth'], ''),
                ('cmake', cmake_root, cmake_files, 'cmake-3.31.10-windows-x86_64/')):
            with zipfile.ZipFile(self.root / 'd' / pin_map[name]['file']) as archive:
                for relative in members:
                    member = prefix + relative
                    try:
                        with archive.open(member) as stream:
                            value = hashlib.sha256()
                            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                                value.update(chunk)
                    except KeyError as exc:
                        raise PlanError('verified tool archive is missing ' + member) from exc
                    if digest(regular_under(root, relative)) != value.hexdigest():
                        raise PlanError('extracted tool file differs from verified archive: ' + relative)
        files += [{'origin': 'driver-python', 'source': item} for item in python_files]
        files += [{'origin': 'portable-cmake', 'source': item} for item in sorted(set(cmake_files))]
        self.add_declarations({'schema': 1, 'origins': origins, 'files': files})

    def add_conan_runtime_candidates(self):
        """Bind every installed host package and select only runtime files/notices."""
        graph_path = self.root / 'b/conan-install-graph.json'
        if not graph_path.is_file():
            self.issue('missing-conan-graph', 'b/conan-install-graph.json')
            for case in ('RuntimeCatalogLanguageTest', 'extension_manager_test'):
                self.condition_patterns.append(('main', case, 'The locked Conan SDK graph is missing.'))
            return
        graph = read_json(regular_under(self.root, 'b/conan-install-graph.json'))
        self.add('main-build', 'conan-install-graph.json')
        nodes = graph.get('graph', {}).get('nodes') if isinstance(graph, dict) else None
        if not isinstance(nodes, dict):
            raise PlanError('invalid Conan install graph')
        lock_path = self.source / 'conan.lock'
        locked = set()
        if lock_path.is_file():
            lock = read_json(regular_under(self.source, 'conan.lock'))
            requires = lock.get('requires') if isinstance(lock, dict) else None
            if not isinstance(requires, list) or any(not isinstance(item, str) for item in requires):
                raise PlanError('invalid Conan lock requires list')
            locked = {item.split('%', 1)[0] for item in requires}
        else:
            self.issue('missing-conan-lock', 's/conan.lock')
        packages = []
        for node_id, node in nodes.items():
            if not isinstance(node, dict) or node.get('context') != 'host':
                continue
            if not node.get('package_folder'):
                if str(node_id) != '0':
                    self.issue('missing-conan-host-package-folder', 'node ' + str(node_id) + ': ' + str(node.get('ref', 'unknown')))
                continue
            if not re.fullmatch(r'\d+', str(node_id)):
                raise PlanError('invalid Conan graph node ID')
            try:
                relative = audit.to_relative(node['package_folder'], self.logical_root)
                safe_relative(relative, self.logical_root)
            except (audit.AuditError, PlanError) as exc:
                raise PlanError('Conan package folder is outside the same root') from exc
            if not relative.casefold().startswith('c/'):
                raise PlanError('Conan package folder is outside the private Conan home')
            package = self.root.joinpath(*relative.split('/'))
            try:
                audit.check_root(package, self.logical_root)
            except (audit.AuditError, OSError) as exc:
                raise PlanError('unsafe Conan package root: ' + relative) from exc
            packages.append((str(node_id), node, relative, package))
        runtime_dirs = []
        for name in ('pj_ffmpeg_bin_dirs.txt', 'pj_python_bin_dirs.txt'):
            path = self.root / 'b' / name
            if not path.is_file():
                self.issue('missing-conan-runtime-list', 'b/' + name)
                continue
            self.add('main-build', name)
            for line in path.read_text(encoding='utf-8').splitlines():
                if not line.strip():
                    continue
                try:
                    relative = audit.to_relative(line.strip(), self.logical_root)
                    safe_relative(relative, self.logical_root)
                except (audit.AuditError, PlanError) as exc:
                    raise PlanError('Conan runtime path leaves the same root') from exc
                if not relative.casefold().startswith('c/'):
                    raise PlanError('Conan runtime path leaves the private home')
                directory = self.root.joinpath(*relative.split('/'))
                try:
                    audit.check_root(directory, self.logical_root)
                except (audit.AuditError, OSError) as exc:
                    raise PlanError('unsafe Conan runtime directory: ' + relative) from exc
                if not directory.is_dir():
                    raise PlanError('Conan runtime directory is missing: ' + relative)
                runtime_dirs.append(relative)
        seen_dirs, distinct_dirs = set(), []
        for item in runtime_dirs:
            if item.casefold() not in seen_dirs:
                seen_dirs.add(item.casefold())
                distinct_dirs.append(item)
        runtime_dirs = distinct_dirs
        self.runtime_dirs = runtime_dirs
        by_package = {}
        for directory in runtime_dirs:
            hits = [p for p in packages if directory.casefold() == p[2].casefold() or
                    directory.casefold().startswith(p[2].casefold() + '/')]
            if len(hits) != 1:
                self.issue('unresolved-conan-runtime-directory', directory)
                continue
            by_package.setdefault(hits[0][0], set()).add(directory)
        cpython = [item for item in packages if str(item[1].get('ref', '')).startswith('cpython/')]
        if len(cpython) != 1:
            self.issue('missing-or-ambiguous-embedded-cpython', 'Conan graph must resolve exactly one host cpython')
        else:
            by_package.setdefault(cpython[0][0], set())
        sdk = [item for item in packages if str(item[1].get('ref', '')).startswith('plotjuggler_sdk/0.39.0#')]
        sdk_module = load_module('native_stage_sdk_contract', 'verify_native_ci_closure.py')
        sdk_contract = sdk_module.SDK_FIXTURE_FILES
        rule_cases = {'runtime-catalog-language': 'RuntimeCatalogLanguageTest', 'extension-manager': 'extension_manager_test'}
        if len(sdk) != 1:
            self.issue('missing-or-ambiguous-locked-sdk', 'Conan graph must resolve exactly one host plotjuggler_sdk/0.39.0')
            for case in rule_cases.values():
                self.condition_patterns.append(('main', case, 'The locked SDK package source and fixture identity is missing or ambiguous.'))
        origins, entries, identities, seen_packages = {}, [], [], set()
        for node_id, node, prefix, package in packages:
            if prefix.casefold() in seen_packages:
                self.issue('duplicate-conan-host-package-folder', prefix)
                continue
            seen_packages.add(prefix.casefold())
            ref, package_id, prev = node.get('ref'), node.get('package_id'), node.get('prev')
            canonical_ref = ref.split('%', 1)[0] if isinstance(ref, str) else ''
            match = re.fullmatch(r'[^#\r\n]+#([0-9a-f]{32})', canonical_ref)
            if (not match or (node.get('rrev') is not None and node.get('rrev') != match.group(1)) or
                    not re.fullmatch(r'[0-9a-f]{40}', str(package_id or '')) or
                    not re.fullmatch(r'[0-9a-f]{32}', str(prev or ''))):
                self.issue('incomplete-conan-package-identity', prefix)
                continue
            if canonical_ref not in locked:
                self.issue('conan-host-recipe-not-locked', canonical_ref)
            manifest = package / 'conanmanifest.txt'
            if not manifest.is_file():
                self.issue('missing-conan-package-manifest', prefix)
                if len(sdk) == 1 and node_id == sdk[0][0]:
                    for case in rule_cases.values():
                        self.condition_patterns.append(('main', case, 'The locked SDK package manifest is missing.'))
                continue
            manifest = regular_under(package, 'conanmanifest.txt')
            lines = manifest.read_text(encoding='utf-8').splitlines()
            if not lines or not re.fullmatch(r'\d+', lines[0]):
                raise PlanError('invalid Conan package manifest: ' + prefix)
            hashes = {}
            for line in lines[1:]:
                name, separator, value = line.rpartition(': ')
                if not separator or not re.fullmatch(r'[0-9a-f]{32}', value) or name in hashes:
                    raise PlanError('invalid or duplicate Conan manifest entry: ' + prefix)
                safe_conan_manifest_name(name)
                hashes[name] = value
            license_root = package / 'licenses'
            if not license_root.is_dir():
                self.issue('missing-conan-package-license', prefix)
                if len(sdk) == 1 and node_id == sdk[0][0]:
                    for case in rule_cases.values():
                        self.condition_patterns.append(('main', case, 'The locked SDK package license is missing.'))
                continue
            def walk_files(directory, skip_tests=False):
                def onerror(error):
                    raise PlanError('cannot enumerate Conan package: ' + str(error)) from error
                for parent, dirs, names in os.walk(directory, followlinks=False, onerror=onerror):
                    if skip_tests:
                        dirs[:] = [x for x in dirs if x.casefold() not in {'__pycache__', 'test', 'tests'}]
                    for name in dirs:
                        item = Path(parent) / name
                        info = item.lstat()
                        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                            raise PlanError('link in Conan runtime package: ' + str(item))
                    for name in names:
                        item = Path(parent) / name
                        yield item.relative_to(package).as_posix()
            licenses = sorted(walk_files(license_root))
            if not licenses:
                self.issue('empty-conan-package-license', prefix)
                if len(sdk) == 1 and node_id == sdk[0][0]:
                    for case in rule_cases.values():
                        self.condition_patterns.append(('main', case, 'The locked SDK package license directory is empty.'))
                continue
            selected = set(licenses)
            if len(sdk) == 1 and node_id == sdk[0][0]:
                # Some main-build DLLs contain SDK fixture sources. Carry both
                # project and actual SDK notices for those built artifacts.
                notices = self.origins['main-build']['license_files'] + [prefix + '/' + item for item in licenses]
                self.origins['main-build']['license_files'] = sorted(set(notices), key=str.casefold)
                # These exact SDK source/helper files are used by CMake targets.
                # They must also be in this installed Conan package's manifest.
                for fixture, expected in sdk_contract.items():
                    path = package.joinpath(*fixture.split('/'))
                    if not path.is_file():
                        self.issue('missing-locked-sdk-fixture', prefix + '/' + fixture)
                        for rule_name, rule in sdk_module.CODEMODEL_RULES.items():
                            if fixture.endswith('PjSdkTestFixtures.cmake') or any(
                                    sdk_module.CODEMODEL_PLUGIN_SOURCES[target] == ('sdk', fixture)
                                    for target in rule['definitions'].values()):
                                self.condition_patterns.append(('main', rule_cases[rule_name],
                                                                'Locked SDK source fixture is missing: ' + prefix + '/' + fixture))
                        continue
                    path = regular_under(package, fixture)
                    if digest(path) != expected:
                        raise PlanError('locked SDK fixture differs from reviewed SHA-256: ' + fixture)
                    selected.add(fixture)
            for directory in by_package.get(node_id, set()):
                actual = self.root.joinpath(*directory.split('/'))
                for item in actual.iterdir():
                    if item.is_file() and item.suffix.casefold() in {'.dll', '.pyd'}:
                        selected.add(item.relative_to(package).as_posix())
            if len(cpython) == 1 and node_id == cpython[0][0]:
                for directory in ('bin/Lib', 'bin/DLLs'):
                    path = package.joinpath(*directory.split('/'))
                    if path.is_dir():
                        selected.update(walk_files(path, skip_tests=True))
                    else:
                        self.issue('missing-cpython-runtime-directory', prefix + '/' + directory)
            for relative in selected:
                path = regular_under(package, relative)
                if relative not in hashes:
                    raise PlanError('runtime file is not recorded in Conan package manifest: ' + prefix + '/' + relative)
                # Conan package manifests carry MD5 entries; also record SHA-256
                # for each staged file. This is identity evidence, not an
                # assertion that MD5 independently authenticates the package.
                md5 = hashlib.md5(usedforsecurity=False)
                with path.open('rb') as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                        md5.update(chunk)
                if md5.hexdigest() != hashes[relative]:
                    raise PlanError('Conan package file differs from its manifest: ' + prefix + '/' + relative)
            origin = 'conan-package-' + re.sub(r'[^a-z0-9_-]', '-', node_id.casefold())
            origins[origin] = {'root': prefix, 'description': 'Conan host package manifest identity',
                               'revision': digest(manifest),
                               'license_files': [prefix + '/' + item for item in licenses]}
            entries.append({'origin': origin, 'source': 'conanmanifest.txt'})
            entries += [{'origin': origin, 'source': item} for item in sorted(selected)]
            identities.append({'ref': ref, 'rrev': match.group(1), 'package_id': package_id, 'prev': prev,
                               'package_folder': prefix, 'manifest_sha256': digest(manifest),
                               'runtime_dirs': sorted(by_package.get(node_id, set()), key=str.casefold)})
        if origins:
            self.add_declarations({'schema': 1, 'origins': origins, 'files': entries})
        identity_path = self.root / 'b/native-kit/conan-runtime-identity.json'
        if identity_path.parent.is_dir():
            write_new(identity_path, {'schema': 1, 'source_sha': self.source_sha, 'source_tree': self.source_tree,
                                      'graph_sha256': digest(graph_path), 'packages': identities})
            self.add('main-build', 'native-kit/conan-runtime-identity.json')
        else:
            self.issue('missing-conan-evidence-directory', 'b/native-kit')

    def add_test_input_candidates(self):
        """Bind only verified font and exact plugin fixture files to origins."""
        font = self.root / 'b/ci-fonts/NotoSansCJKsc-Regular.otf'
        font_license = self.root / 'b/ci-fonts/LICENSE'
        if font.is_file() and font_license.is_file():
            source = regular_under(self.source, 'packaging/localization/prepare_payload.py')
            tree = ast.parse(source.read_text(encoding='utf-8'))
            wanted = {'FONT_SHA', 'FONT_LICENSE_SHA'}
            constants = {}
            for node in tree.body:
                if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and \
                        node.targets[0].id in wanted and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    key = node.targets[0].id
                    if key in constants:
                        raise PlanError('duplicate pinned font identity')
                    constants[key] = node.value.value
            if set(constants) != wanted or any(not audit.HEX64.fullmatch(value) for value in constants.values()):
                raise PlanError('missing authoritative font SHA-256 pins')
            if digest(font) != constants['FONT_SHA'] or digest(font_license) != constants['FONT_LICENSE_SHA']:
                raise PlanError('test font or license differs from its source pin')
            self.add_declarations({'schema': 1, 'origins': {'test-font': {
                'root': 'b/ci-fonts', 'description': 'Pinned Noto CJK test font', 'revision': constants['FONT_SHA'],
                'license_files': ['b/ci-fonts/LICENSE']}},
                'files': [{'origin': 'test-font', 'source': name} for name in ('LICENSE', 'NotoSansCJKsc-Regular.otf')]})
        else:
            self.issue('missing-pinned-font', 'b/ci-fonts/NotoSansCJKsc-Regular.otf or LICENSE')

        prefix = self.root / 'b/csv-prefix'
        release = prefix / 'share/plotjuggler4/release.json'
        if release.is_file():
            record = read_json(regular_under(prefix, 'share/plotjuggler4/release.json'))
            lock_path = regular_under(self.source, 'packaging/localization/plugin-patches/source-lock.json')
            lock = read_json(lock_path)
            sources = [item for item in lock.get('plugins', []) if isinstance(item, dict) and item.get('id') == 'csv-loader']
            actual = [item for item in record.get('localized_plugin_rebuilds', [])
                      if isinstance(item, dict) and item.get('id') == 'csv-loader']
            if len(sources) != 1 or len(actual) != 1:
                raise PlanError('CSV test prefix does not contain one locked rebuilt plugin')
            expected, plugin = sources[0], actual[0]
            for key in ('version', 'commit', 'sdk', 'patch_sha256'):
                if plugin.get(key) != expected.get(key):
                    raise PlanError('CSV test plugin source identity differs: ' + key)
            if not audit.HEX40.fullmatch(str(expected.get('commit', ''))):
                raise PlanError('CSV plugin source commit is invalid')
            selected = []
            for field, expected_prefix in (('files', 'lib/plotjuggler/plugins/csv-loader/'),
                                           ('license_files', 'share/licenses/localized-plugins/csv-loader/')):
                records = plugin.get(field)
                if not isinstance(records, list) or not records:
                    raise PlanError('CSV test plugin lacks its explicit ' + field)
                for item in records:
                    if not isinstance(item, dict) or not isinstance(item.get('path'), str) or \
                            not item['path'].startswith(expected_prefix) or not audit.HEX64.fullmatch(str(item.get('sha256', ''))):
                        raise PlanError('invalid CSV plugin file declaration')
                    relative = safe_relative(item['path'], self.logical_root)
                    if digest(regular_under(prefix, relative)) != item['sha256']:
                        raise PlanError('CSV plugin file differs from its recorded SHA-256: ' + relative)
                    selected.append(relative)
            if len(selected) != len({name.casefold() for name in selected}):
                raise PlanError('duplicate CSV plugin file declaration')
            dlls = [name for name in selected if name.casefold().endswith('.dll') and
                    name.startswith('lib/plotjuggler/plugins/csv-loader/')]
            if len(dlls) != 1:
                raise PlanError('CSV test prefix needs exactly one native plugin DLL')
            copied_lock = regular_under(prefix, 'share/plotjuggler4/localized-plugin-sources.json')
            if digest(copied_lock) != digest(lock_path):
                raise PlanError('CSV prefix source lock differs from exact source')
            selected += ['share/plotjuggler4/release.json', 'share/plotjuggler4/localized-plugin-sources.json']
            licenses = ['b/csv-prefix/' + item['path'] for item in plugin['license_files']]
            self.add_declarations({'schema': 1, 'origins': {'csv-plugin': {
                'root': 'b/csv-prefix', 'description': 'Locked rebuilt CSV test plugin',
                'revision': expected['commit'], 'license_files': licenses}},
                'files': [{'origin': 'csv-plugin', 'source': item} for item in selected]})
        else:
            self.issue('missing-csv-test-plugin', 'b/csv-prefix/share/plotjuggler4/release.json')

        identity = self.root / 'b/feedback-plugins-identity.json'
        if identity.is_file():
            record = read_json(regular_under(self.root, 'b/feedback-plugins-identity.json'))
            baseline = read_json(regular_under(self.source, 'docs/localization/upstream-baseline.json')).get('ardupilot_plugin', {})
            registry = read_json(regular_under(self.source, 'packaging/localization/registry-lock.json'))
            fft = [item for item in registry.get('extensions', []) if isinstance(item, dict) and item.get('id') == 'toolbox-fft']
            if len(fft) != 1 or record.get('platform') != 'windows-x86_64' or \
                    record.get('apbin_source_commit') != baseline.get('commit') or \
                    record.get('apbin_version') != baseline.get('version'):
                raise PlanError('feedback test plugin identity differs from exact source')
            upstream = fft[0].get('platforms', {}).get('windows-x86_64', {})
            if record.get('fft_url') != upstream.get('url') or 'sha256:' + str(record.get('fft_archive_sha256')) != upstream.get('checksum'):
                raise PlanError('feedback FFT archive differs from the fixed registry')
            records = record.get('files')
            if not isinstance(records, list) or not records:
                raise PlanError('feedback identity lacks its file list')
            apbin, fft_files = [], []
            seen = set()
            for item in records:
                if not isinstance(item, dict) or not isinstance(item.get('path'), str) or \
                        not audit.HEX64.fullmatch(str(item.get('sha256', ''))):
                    raise PlanError('invalid feedback file declaration')
                relative = safe_relative(item['path'], self.logical_root)
                if relative.casefold() in seen or not relative.startswith(('ardupilot-dataflash/', 'toolbox-fft/')):
                    raise PlanError('duplicate or unexpected feedback input path')
                seen.add(relative.casefold())
                if digest(regular_under(self.root / 'b/feedback-plugins', relative)) != item['sha256']:
                    raise PlanError('feedback input differs from its recorded SHA-256: ' + relative)
                if relative.startswith('ardupilot-dataflash/'):
                    apbin.append(relative[len('ardupilot-dataflash/'):])
                else:
                    fft_files.append(relative[len('toolbox-fft/'):])
            if len([item for item in apbin if item.casefold().endswith('.dll')]) != 1 or 'manifest.json' not in apbin:
                raise PlanError('feedback APBIN fixture is incomplete')
            licenses = ['s/3rdparty/plotjuggler-apbin-plugins/sdk4/' + name
                        for name in ('LICENSE', 'COPYING.GPL3', 'LICENSE.APACHE2')]
            if any(name.casefold() not in self.tracked for name in licenses):
                raise PlanError('tracked APBIN source licenses are missing')
            self.add_declarations({'schema': 1, 'origins': {'feedback-apbin': {
                'root': 'b/feedback-plugins/ardupilot-dataflash', 'description': 'Exact build APBIN test plugin',
                'revision': baseline['commit'], 'license_files': licenses}},
                'files': [{'origin': 'feedback-apbin', 'source': item} for item in apbin]})
            self.add('main-build', 'feedback-plugins-identity.json')
            fft_license = self.root / 'b/feedback-fft-notices/LICENSE'
            if fft_license.is_file():
                if digest(regular_under(self.root, 'b/feedback-fft-notices/LICENSE')) != FFT_LICENSE_SHA256:
                    raise PlanError('locked FFT source license differs from its pinned SHA-256')
                if len([item for item in fft_files if item.casefold().endswith('.dll')]) != 1 or 'manifest.json' not in fft_files:
                    raise PlanError('feedback FFT fixture is incomplete')
                license_relative = 'b/feedback-fft-notices/LICENSE'
                self.add_declarations({'schema': 1, 'origins': {
                    'feedback-fft': {'root': 'b/feedback-plugins/toolbox-fft', 'description': 'Locked official FFT test plugin',
                                     'revision': record['fft_archive_sha256'], 'license_files': [license_relative]},
                    'feedback-fft-license': {'root': 'b/feedback-fft-notices', 'description': 'FFT exact source license',
                                             'revision': FFT_SOURCE_COMMIT, 'license_files': [license_relative]}},
                    'files': ([{'origin': 'feedback-fft', 'source': item} for item in fft_files] +
                              [{'origin': 'feedback-fft-license', 'source': 'LICENSE'}])})
                self.condition_patterns.append(('main', 'PluginFeedbackMainWindow-',
                                                'FFT old-SDK and static dependency notices and runtime closure remain unverified.'))
            else:
                self.condition_patterns.append(('main', 'PluginFeedbackMainWindow-',
                                                'FFT exact-source license is unavailable for this test group.'))
        else:
            self.condition_patterns.append(('main', 'PluginFeedbackMainWindow-',
                                            'The verified APBIN/FFT feedback inputs are unavailable.'))

    def add_reference(self, suite, case, value, *, directory=False):
        try:
            relative = audit.to_relative(value, self.logical_root)
            if relative == '.':
                return
            safe_relative(relative, self.logical_root)
        except audit.AuditError:
            self.issue('outside-root', value, suite=suite, case=case)
            return
        except PlanError as exc:
            self.issue('invalid-path', str(exc), suite=suite, case=case)
            return
        actual = self.root.joinpath(*relative.split('/'))
        if directory or actual.is_dir():
            try:
                audit.check_root(actual, self.logical_root)
            except (audit.AuditError, OSError):
                self.issue('unsafe-working-directory', relative, suite=suite, case=case)
                return
            if not actual.is_dir():
                self.issue('missing-working-directory', relative, suite=suite, case=case)
            else:
                self.directories.add(relative)
                if not directory:
                    self.issue('directory-content-unreviewed', relative, suite=suite, case=case)
            return
        if not actual.is_file():
            self.issue('missing-referenced-file', relative, suite=suite, case=case)
            return
        if relative.casefold().startswith('s/'):
            generated = {x.casefold() for x in self.generated_media['files']} if self.generated_media else set()
            if relative.casefold() not in self.tracked and relative.casefold() not in generated:
                self.issue('untracked-source-input', relative, suite=suite, case=case)
            return
        if relative.casefold() in self.files:
            return
        folded = relative.casefold()
        if folded.startswith(('q/', 'c/', 't/', 'b/csv-prefix/', 'b/feedback-plugins/',
                              'b/ci-fonts/', 'b/csv-plugin-work/')):
            self.issue('runtime-file-not-declared', relative, suite=suite, case=case)
            return
        candidates = sorted(((name, prefix) for name, prefix in self.origin_prefixes.items()
                             if name in ('main-build', 'i18n-build')
                             if relative.casefold().startswith(prefix.casefold() + '/')),
                            key=lambda item: len(item[1]), reverse=True)
        if not candidates:
            self.issue('origin-not-declared', relative, suite=suite, case=case)
            return
        name, prefix = candidates[0]
        try:
            self.add(name, relative[len(prefix) + 1:])
        except (PlanError, OSError) as exc:
            self.issue('unsafe-referenced-file', str(exc), suite=suite, case=case)

    def add_discovery(self, suite, doc):
        if not isinstance(suite, str) or not re.fullmatch(r'[a-z][a-z0-9-]*', suite):
            raise PlanError('invalid suite identifier')
        tests = doc.get('tests') if isinstance(doc, dict) else None
        if not isinstance(doc, dict) or doc.get('kind') != 'ctestInfo' or not isinstance(tests, list) or not tests:
            raise PlanError('discovery must contain a nonempty CTest json-v1 test list')
        names = set()
        for test in tests:
            if not isinstance(test, dict) or not isinstance(test.get('name'), str) or not test['name']:
                raise PlanError('CTest case name is missing')
            name = test['name']
            if name in names or '\n' in name or '\r' in name:
                raise PlanError('duplicate or malformed CTest case: ' + name)
            names.add(name)
            command, properties = test.get('command'), test.get('properties')
            if test.get('config') != 'RelWithDebInfo' or not isinstance(command, list) or not command or \
                    not all(isinstance(x, str) for x in command) or not isinstance(properties, list):
                raise PlanError('malformed or wrong-configuration CTest case: ' + name)
            workdirs = [p.get('value') for p in properties if isinstance(p, dict) and p.get('name') == 'WORKING_DIRECTORY']
            if len(workdirs) != 1 or not isinstance(workdirs[0], str):
                raise PlanError('missing or ambiguous CTest working directory: ' + name)
            self.add_reference(suite, name, command[0])
            self.add_reference(suite, name, workdirs[0], directory=True)
            self.cases.append({'suite': suite, 'case': name, 'status': 'safety_unreviewed',
                               'reason': 'Runtime file, dynamic-load and side-effect closure needs review.'})
            arguments = command[1:]
            if name == 'pj_bundled_translations_test':
                if suite not in ('main', 'i18n'):
                    raise PlanError('bundled-translations output has an unexpected suite')
                tree = 'b' if suite == 'main' else 'i'
                expected = self.logical_root + '\\' + tree + r'\Testing\Temporary\bundled-translations.txt'
                if (PurePosixPath(command[0].replace('\\', '/')).name.casefold() != 'pj_bundled_translations_test.exe' or
                        len(arguments) != 4 or arguments[:3] != ['-o', '-,txt', '-o'] or
                        not arguments[3].endswith(',txt') or
                        ntpath.normcase(ntpath.normpath(arguments[3][:-4])) != ntpath.normcase(ntpath.normpath(expected))):
                    raise PlanError('bundled-translations test has unexpected QtTest output arguments')
                self.allowed_outputs[suite] = {name: [expected]}
                # This one exact QtTest -o argument denotes a future file and
                # the comma suffix is a format, not part of its pathname.
                arguments = arguments[:-1]
            for value in audit.walk_strings([arguments, properties]):
                try:
                    refs = list(audit.absolute_references(value))
                except audit.AuditError as exc:
                    self.issue('ambiguous-command-reference', str(exc), suite=suite, case=name)
                    continue
                for ref in refs:
                    if ntpath.normcase(ntpath.normpath(ref)) == ntpath.normcase(ntpath.normpath(workdirs[0])):
                        continue
                    self.add_reference(suite, name, ref)
        graph = doc.get('backtraceGraph', {})
        if not isinstance(graph, dict) or not isinstance(graph.get('files', []), list):
            raise PlanError('malformed CTest backtrace graph: ' + suite)
        for value in graph.get('files', []):
            if not isinstance(value, str):
                raise PlanError('malformed CTest backtrace path: ' + suite)
            try:
                refs = list(audit.absolute_references(value))
            except audit.AuditError as exc:
                self.issue('ambiguous-backtrace-reference', str(exc), suite=suite)
                continue
            for ref in refs:
                self.add_reference(suite, None, ref)
        self.discoveries[suite] = doc
        return names

    def add_ctest_metadata(self):
        """Add only CTest registration files, not build caches or object files."""
        selected = re.compile(r'(?:CTestTestfile\.cmake|.+_(?:include|tests)(?:-[^.]+)?\.cmake)\Z', re.I)
        for origin in ('main-build', 'i18n-build'):
            root = Path(self.origins[origin]['root'])
            count = 0
            def scan_error(error):
                raise PlanError('cannot enumerate generated CTest metadata: ' + str(error)) from error
            for parent, dirs, files in os.walk(root, followlinks=False, onerror=scan_error):
                excluded = {'Testing', 'CMakeFiles', 'csv-plugin-work', 'csv-prefix',
                            'feedback-plugins', 'ci-fonts', 'gui-acceptance', 'native-kit', 'temp-probe'}
                dirs[:] = [name for name in dirs if name not in excluded]
                for name in dirs:
                    path = Path(parent) / name
                    info = path.lstat()
                    if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                        raise PlanError('linked CTest metadata directory: ' + str(path))
                for name in files:
                    if selected.fullmatch(name):
                        path = Path(parent) / name
                        self.add(origin, path.relative_to(root).as_posix())
                        count += 1
            if not count:
                self.issue('missing-ctest-metadata', self.origin_prefixes[origin])
            for item in ('native-kit/build_identity.json', 'native-kit/discovery.json'):
                if (root / item).is_file():
                    self.add(origin, item)
                else:
                    self.issue('missing-build-evidence', self.origin_prefixes[origin] + '/' + item)
            if origin == 'main-build':
                item = 'native-kit/csv-prebuilt.json'
                if (root / item).is_file():
                    self.add(origin, item)
                else:
                    self.issue('missing-csv-prebuilt-identity', self.origin_prefixes[origin] + '/' + item)

    def add_producer_evidence(self):
        for relative in PRODUCER_EVIDENCE_FILES:
            if (self.root / 'b' / relative).is_file():
                self.add('main-build', relative)
            else:
                self.issue('missing-producer-evidence', 'b/' + relative)
        optional = 'native-kit/ci-temp-probe-evidence/before-marker-discovery'
        for suffix in ('.json', '.stdout.bin', '.stderr.bin'):
            if (self.root / 'b' / (optional + suffix)).is_file():
                self.add('main-build', optional + suffix)
        if (self.root / 'b/native-kit/marker-mutation-evidence/INCOMPLETE').exists():
            self.issue('incomplete-linked-marker-mutation', 'b/native-kit/marker-mutation-evidence/INCOMPLETE')

    def add_codemodel_candidates(self):
        """Recheck captured raw replies and stage their exact target artifacts."""
        base = 'b/native-kit/codemodel'
        receipt_path = self.root / base / 'capture.json'
        if not receipt_path.is_file():
            self.issue('missing-codemodel-evidence', base + '/capture.json')
            for case in ('RuntimeCatalogLanguageTest', 'extension_manager_test'):
                self.condition_patterns.append(('main', case, 'CMake File API target evidence is unavailable.'))
            return
        record = read_codemodel_json(regular_under(self.root, base + '/capture.json'))
        expected = {'schema': 1, 'source_sha': self.source_sha, 'source_tree': self.source_tree,
                    'configuration': 'RelWithDebInfo'}
        if not isinstance(record, dict) or any(record.get(k) != v for k, v in expected.items()):
            raise PlanError('captured CMake File API source identity differs')
        query = regular_under(self.root, base + '/query/codemodel-v2')
        if query.stat().st_size or record.get('query') != {'path': base + '/query/codemodel-v2',
                                                           'sha256': hashlib.sha256(b'').hexdigest()}:
            raise PlanError('retained CMake File API query differs')
        current = inspect_codemodel(self.root, self.logical_root, base + '/reply')
        if any(record.get(key) != value for key, value in current.items()):
            raise PlanError('retained CMake File API targets or reply bytes changed')
        case_names = {'runtime-catalog-language': 'RuntimeCatalogLanguageTest',
                      'extension-manager': 'extension_manager_test'}
        for rule in current['rule_coverage']:
            if rule['status'] == 'condition_missing':
                detail = '; '.join(item['target'] + ': ' + item['reason'] for item in rule['missing'])
                self.condition_patterns.append(('main', case_names[rule['rule']], 'CMake File API condition missing: ' + detail))
        for relative in [base + '/capture.json', base + '/query/codemodel-v2'] + \
                [item['path'] for item in current['reply_files']] + [item['path'] for item in current['targets']]:
            if not relative.startswith('b/'):
                raise PlanError('CMake File API candidate is not in the main tree')
            self.add('main-build', relative[2:])

    def pe_inventory(self):
        """List every static import without treating host names as trusted."""
        files = list(self.files.values())
        providers = {}
        for item in files:
            target = PurePosixPath(item['destination'])
            if target.suffix.casefold() == '.dll':
                providers.setdefault(target.name.casefold(), []).append(item)
        for name, entries in providers.items():
            if len({item['sha256'] for item in entries}) > 1:
                self.issue('conflicting-dll-basename', name + ': ' + ', '.join(item['destination'] for item in entries))
        records = []
        for item in files:
            if PurePosixPath(item['destination']).suffix.casefold() not in {'.exe', '.dll', '.pyd'}:
                continue
            path = Path(self.origins[item['origin']]['root']).joinpath(*item['source'].split('/'))
            try:
                if digest(path) != item['sha256']:
                    raise PlanError('PE candidate changed after hashing: ' + item['destination'])
                imports = pe_helper.imports(path)
            except (pe_helper.PEError, OSError, ValueError) as exc:
                self.issue('unreadable-pe', item['destination'] + ': ' + str(exc))
                continue
            dependencies = []
            for kind in ('normal', 'delay'):
                for name in imports[kind]:
                    matches = sorted((entry['destination'] for entry in providers.get(name.casefold(), [])), key=str.casefold)
                    dependencies.append({'kind': kind, 'name': name, 'candidate_files': matches})
                    if not matches:
                        self.issue('pe-import-needs-resolution', item['destination'] + ': ' + kind + ' ' + name)
            records.append({'path': item['destination'], 'sha256': item['sha256'], 'imports': dependencies})
        return records

    def add_marker_probe_candidates(self):
        """Retain real marker evidence when complete; do not approve App cases."""
        executables = ('native_app_marker_probe.exe', 'marker_probe_policy_test.exe',
                       'marker_probe_windows_tests.exe', 'plotjuggler_marker_test_fixture.exe')
        relatives = ['app-marker-probe/CMakeCache.txt'] + [
            'app-marker-probe/RelWithDebInfo/' + name for name in executables]
        evidence = ['build-identity.json', 'junit.xml'] + [phase + extension for phase in
                    ('configure', 'build', 'discovery', 'execution') for extension in
                    ('.json', '.stdout.bin', '.stderr.bin')]
        relatives += ['native-kit/app-marker-evidence/' + name for name in evidence]
        build = self.root / 'b'
        if not all((build / relative).is_file() for relative in relatives):
            return
        identity = read_json(build / 'native-kit/app-marker-evidence/build-identity.json')
        expected = {'schema': 1, 'role': 'app-marker-probe', 'source_sha': self.source_sha, 'source_tree': self.source_tree,
                    'configuration': 'RelWithDebInfo', 'source_dir': 's/scripts/windows/native_app_marker_probe',
                    'build_tree': 'b/app-marker-probe', 'cmake_cache_sha256': digest(build / relatives[0])}
        if not isinstance(identity, dict) or any(identity.get(k) != v for k, v in expected.items()):
            raise PlanError('actual App marker build identity does not match its CMake cache and source')
        hashes = identity.get('executables_sha256')
        names = dict(zip(('probe', 'policy_test', 'windows_test', 'process_fixture'), executables))
        if not isinstance(hashes, dict) or set(hashes) != set(names) or any(
                hashes[key] != digest(build / 'app-marker-probe/RelWithDebInfo' / name) for key, name in names.items()):
            raise PlanError('actual App marker executable hashes differ from the build identity')
        for phase in ('configure', 'build', 'discovery', 'execution'):
            record = read_json(build / ('native-kit/app-marker-evidence/' + phase + '.json'))
            for stream in ('stdout', 'stderr'):
                raw = build / ('native-kit/app-marker-evidence/' + phase + '.' + stream + '.bin')
                if record.get(stream + '_sha256') != digest(raw):
                    raise PlanError('App marker raw ' + phase + ' ' + stream + ' differs from its receipt')
        for relative in relatives:
            self.add('main-build', relative)
        # Only genuine successful processes and all-seven unfiltered JUnit can
        # produce guard validation. Failure simply leaves App cases unapproved.
        records = {phase: read_json(build / ('native-kit/app-marker-evidence/' + phase + '.json'))
                   for phase in ('configure', 'build', 'discovery', 'execution')}
        if any(value.get('exit_code') != 0 or value.get('still_running') is not False for value in records.values()):
            return
        try:
            marker_results = audit.audit_results(build / 'native-kit/app-marker-evidence/discovery.stdout.bin',
                                                 build / 'native-kit/app-marker-evidence/junit.xml')
        except (audit.AuditError, OSError, ValueError, ET.ParseError) as exc:
            self.cases.append({'suite': 'main', 'case': None, 'status': 'condition_missing',
                               'reason': 'App marker result audit failed: ' + str(exc)})
            return
        if not marker_results.get('complete_without_skips_or_failures'):
            return
        main = self.discoveries.get('main', {})
        matches = [test for test in main.get('tests', []) if test.get('name') == 'WindowsApplicationContract']
        if len(matches) != 1 or len(matches[0].get('command', [])) < 3:
            return
        try:
            application = audit.to_relative(matches[0]['command'][2], self.logical_root)
            script = audit.to_relative(matches[0]['command'][1], self.logical_root)
        except audit.AuditError:
            return
        if (script.casefold() != 's/scripts/verify_windows_application.py' or
                not application.casefold().startswith('b/') or not application.casefold().endswith('.exe') or
                application.casefold() not in self.files):
            return
        versions = {}
        for line in regular_under(self.source, 'versions.env').read_text(encoding='utf-8').splitlines():
            key, sep, value = line.split('#', 1)[0].partition('=')
            if sep:
                versions[key.strip()] = value.strip()
        qt_version = versions.get('PJ_QT_VERSION', '')
        if not re.fullmatch(r'\d+\.\d+\.\d+', qt_version):
            return
        qt = f'q/{qt_version}/msvc2022_64'
        qt_core = regular_under(self.root, qt + '/bin/Qt6Core.dll')
        if identity.get('qt_core_sha256') != digest(qt_core):
            raise PlanError('App marker Qt identity differs from the real Qt Core bytes')
        prefix = 'b/native-kit/app-marker-evidence/'
        validation = {'schema': 2, 'source_sha': self.source_sha, 'source_tree': self.source_tree,
                      'configuration': 'RelWithDebInfo', 'platform': 'windows', 'runner_environment': 'github-hosted',
                      'probe_sha256': hashes['probe'], 'qt_core_sha256': digest(qt_core),
                      'application_sha256': digest(regular_under(self.root, application)),
                      'build_identity': prefix + 'build-identity.json', 'junit': prefix + 'junit.xml'}
        for phase in records:
            validation[phase + '_process'] = prefix + phase + '.json'
            validation[phase + '_stdout'] = prefix + phase + '.stdout.bin'
            validation[phase + '_stderr'] = prefix + phase + '.stderr.bin'
        validation_path = build / 'native-kit/app-marker-evidence/validation.json'
        write_new(validation_path, validation)
        self.add('main-build', 'native-kit/app-marker-evidence/validation.json')
        paths = {'qt': qt, 'ctest': 't/cmake/bin/ctest.exe', 'application': application,
                 'app_guard_probe': 'b/app-marker-probe/RelWithDebInfo/native_app_marker_probe.exe',
                 'app_guard_validation': prefix + 'validation.json'}
        launcher = load_module('native_stage_marker_validation', 'run_native_test_bundle.py')
        stub = {'files': [{'path': item['destination']} for item in self.files.values()]}
        valid, reason = launcher.checked_app_guard(self.root, paths, stub, self.source_sha, self.source_tree, 'RelWithDebInfo')
        if not valid:
            self.cases.append({'suite': 'main', 'case': None, 'status': 'condition_missing', 'reason': reason})
            return
        self.marker_guard_paths = {key: paths[key] for key in ('application', 'app_guard_probe', 'app_guard_validation')}

    def add_run_plan_candidate(self):
        """Construct a source-bound launcher plan without approving any case."""
        if not {'main', 'i18n'} <= self.discoveries.keys():
            self.issue('run-plan-missing-discovery', 'Both full trees are needed before a launcher plan can be derived.')
            return
        main_path = self.root / 'b/native-kit/discovery.json'
        i18n_path = self.root / 'i/native-kit/discovery.json'
        if not main_path.is_file() or not i18n_path.is_file() or \
                read_json(main_path) != self.discoveries['main'] or read_json(i18n_path) != self.discoveries['i18n']:
            self.issue('run-plan-discovery-not-bound', 'Full discovery files must be the actual independent same-root records.')
            return
        version_file = regular_under(self.source, 'versions.env')
        versions = {}
        for line in version_file.read_text(encoding='utf-8').splitlines():
            line = line.split('#', 1)[0].strip()
            if not line:
                continue
            key, sep, value = line.partition('=')
            if not sep or key.strip() in versions:
                raise PlanError('invalid or duplicate versions.env entry')
            versions[key.strip()] = value.strip()
        qt_version = versions.get('PJ_QT_VERSION', '')
        if not re.fullmatch(r'\d+\.\d+\.\d+', qt_version):
            raise PlanError('run plan needs the exact source Qt version')
        file_dialog_path = regular_under(self.source, 'packaging/localization/audit_file_dialog_results.py')
        spec = importlib.util.spec_from_file_location('native_file_dialog_contract', file_dialog_path)
        dialog = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(dialog)
        dialog_cases = set(dialog.CASES)
        csv_cases = {'CsvRuntimeFileLoader_' + language for language in ('en_US', 'zh_CN', 'zh_TW')}
        full = self.discoveries['main']
        all_names = {item['name'] for item in full['tests']}
        if len(dialog_cases) != 4 or not dialog_cases <= all_names:
            self.issue('run-plan-file-dialog-selection', 'The exact four source-defined file-dialog cases are not registered.')
            return
        if not csv_cases <= all_names:
            self.issue('run-plan-csv-selection', 'The three CSV language cases are not registered in the main build.')
            return
        if not self.runtime_dirs:
            self.issue('run-plan-runtime-directories', 'No same-root Conan runtime DLL directories are identified.')
            return
        for path in ('b/native-kit/build_identity.json', 'i/native-kit/build_identity.json',
                     'b/native-kit/csv-prebuilt.json', 'i/temp-probe/RelWithDebInfo/pj_native_temp_probe.exe',
                     'b/ci-temp-probe/RelWithDebInfo/pj_native_ci_temp_probe.exe'):
            if not self.root.joinpath(*path.split('/')).is_file():
                self.issue('run-plan-missing-input', path)
                return
        cache_fields = {}
        role_compiler = None
        for role, build, source_dir in (('main', 'b', 's'), ('i18n', 'i', 's/pj_app/tests/i18n')):
            identity = read_json(regular_under(self.root, build + '/native-kit/build_identity.json'))
            cache = regular_under(self.root, build + '/CMakeCache.txt')
            expected = {'schema': 1, 'role': role, 'source_sha': self.source_sha, 'source_tree': self.source_tree,
                        'configuration': 'RelWithDebInfo', 'source_dir': source_dir, 'build_tree': build,
                        'native_bundle_mode': True, 'cmake_cache_sha256': digest(cache)}
            if identity.get('native_bundle_mode') is not True or any(identity.get(key) != value for key, value in expected.items()):
                raise PlanError('build identity differs from the actual ' + role + ' CMake cache')
            cache_fields[role] = validate_build_cache(cache_values(cache.read_text(encoding='utf-8')),
                                                       self.logical_root, role, qt_version)
            if role_compiler is not None and identity.get('compiler') != role_compiler:
                raise PlanError('main and i18n compiler identities differ')
            role_compiler = identity.get('compiler')
            evidence = identity.get('compiler_evidence')
            if not isinstance(evidence, dict):
                raise PlanError('build identity lacks independent compiler evidence')
            for phase in ('preflight', 'final'):
                expected_compiler, paths = verify_compiler_evidence(
                    self.root, self.logical_root, self.source_sha, self.source_tree, role,
                    evidence.get('expected_sha256'), evidence.get(phase + '_sha256'), phase, live=phase == 'final')
                if (identity.get('compiler') != expected_compiler['compiler'] or
                        compiler_path_key(cache_fields[role]['compiler']) != compiler_path_key(expected_compiler['compiler']['path'])):
                    raise PlanError('build identity compiler differs from independent evidence')
                for path in paths:
                    self.add('main-build' if role == 'main' else 'i18n-build', path[len(build) + 1:])
        csv_identity = read_json(regular_under(self.root, 'b/native-kit/csv-prebuilt.json'))
        if (csv_identity.get('schema') != 1 or csv_identity.get('source_sha') != self.source_sha or
                csv_identity.get('source_tree') != self.source_tree or csv_identity.get('configuration') != 'RelWithDebInfo' or
                csv_identity.get('qt_version') != qt_version):
            raise PlanError('CSV prebuilt identity differs from the exact source, tree or Qt')
        csv_paths = {}
        for field, expected_prefix in (('runner', 'b/'), ('plugin', 'b/csv-prefix/'),
                                       ('qt_core', f'q/{qt_version}/msvc2022_64/bin/'), ('ctest', 't/cmake/bin/')):
            try:
                relative = audit.to_relative(str(csv_identity.get(field, '')), self.logical_root)
                safe_relative(relative, self.logical_root)
            except (audit.AuditError, PlanError) as exc:
                raise PlanError('CSV identity has an invalid ' + field + ' path') from exc
            if not relative.casefold().startswith(expected_prefix.casefold()) or \
                    not audit.HEX64.fullmatch(str(csv_identity.get(field + '_sha256', ''))) or \
                    digest(regular_under(self.root, relative)) != csv_identity[field + '_sha256']:
                raise PlanError('CSV identity file differs from the actual ' + field + ' bytes')
            csv_paths[field] = relative
        if (csv_paths['plugin'].casefold() != cache_fields['main']['csv_plugin'].casefold() or
                csv_paths['qt_core'].casefold() != f'q/{qt_version}/msvc2022_64/bin/qt6core.dll'.casefold() or
                csv_paths['ctest'].casefold() != 't/cmake/bin/ctest.exe' or
                PurePosixPath(csv_paths['runner']).name.casefold() != 'csv_runtime_file_loader_test.exe'):
            raise PlanError('CSV identity paths do not match the real configured inputs')
        host_path = regular_under(self.source, 'packaging/localization/host_versions.py')
        host_spec = importlib.util.spec_from_file_location('native_stage_host_versions', host_path)
        host = importlib.util.module_from_spec(host_spec)
        host_spec.loader.exec_module(host)
        host_sdk = host.read_host_versions(self.source)['sdk_version']
        lock = read_json(regular_under(self.source, 'packaging/localization/plugin-patches/source-lock.json'))
        plugin_sdk = [item.get('sdk') for item in lock.get('plugins', []) if isinstance(item, dict) and item.get('id') == 'csv-loader']
        if len(plugin_sdk) != 1 or csv_identity.get('host_sdk') != host_sdk or csv_identity.get('plugin_sdk') != plugin_sdk[0]:
            raise PlanError('CSV identity SDK versions differ from the source locks')
        for item in full['tests']:
            if item['name'] not in csv_cases:
                continue
            command = item['command']
            properties = {prop['name']: prop['value'] for prop in item['properties']}
            language = item['name'].removeprefix('CsvRuntimeFileLoader_')
            environment = properties.get('ENVIRONMENT', [])
            if (len(command) != 1 or audit.to_relative(command[0], self.logical_root).casefold() != csv_paths['runner'].casefold() or
                    not isinstance(environment, list) or
                    properties.get('DISABLED', False) or f'PLOTJUGGLER_UI_LANGUAGE={language}' not in environment or
                    'QT_QPA_PLATFORM=offscreen' not in environment):
                raise PlanError('CSV discovery differs from the exact three-language runner contract')
        needle = csv_identity['plugin'].replace('\\', '/').encode('utf-8') + b'\0'
        overlap = b''
        found = False
        with regular_under(self.root, csv_paths['runner']).open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                data = overlap + chunk
                if needle in data:
                    found = True
                    break
                overlap = data[-(len(needle) - 1):] if len(needle) > 1 else b''
        if not found:
            raise PlanError('CSV runner does not contain the exact staged plugin path')
        def subset(names):
            return {'kind': 'ctestInfo', 'tests': [item for item in full['tests'] if item['name'] in names]}
        dialog_path = self.root / 'b/native-kit/file-dialog-discovery.json'
        csv_path = self.root / 'b/native-kit/csv-discovery.json'
        plan_path = self.root / 'b/native-kit/run-plan.json'
        output_paths = {suite: self.root / tree / 'native-kit/allowed-outputs.json'
                        for suite, tree in (('main', 'b'), ('i18n', 'i')) if suite in self.allowed_outputs}
        if any(path.exists() for path in (dialog_path, csv_path, plan_path, *output_paths.values())):
            raise PlanError('run-plan candidate outputs must not already exist')
        main = 'b/native-kit/discovery.json'
        i18n = 'i/native-kit/discovery.json'
        plan = {'schema': 1, 'source_sha': self.source_sha, 'source_tree': self.source_tree,
                'configuration': 'RelWithDebInfo', 'qt_version': qt_version,
                'paths': {'python': 't/python/python.exe', 'ctest': 't/cmake/bin/ctest.exe',
                          'probe': 'i/temp-probe/RelWithDebInfo/pj_native_temp_probe.exe',
                          'ci_temp_probe': 'b/ci-temp-probe/RelWithDebInfo/pj_native_ci_temp_probe.exe',
                          'qt': f'q/{qt_version}/msvc2022_64', 'fonts': 'b/ci-fonts',
                          'feedback': 'b/feedback-plugins'},
                'runtime_dirs': self.runtime_dirs,
                'suites': [
                    {'id': 'main', 'kind': 'ctest', 'tree': 'b', 'discovery': main, 'full_discovery': main,
                     'build_identity': 'b/native-kit/build_identity.json'},
                    {'id': 'i18n', 'kind': 'ctest', 'tree': 'i', 'discovery': i18n, 'full_discovery': i18n,
                     'build_identity': 'i/native-kit/build_identity.json'},
                    {'id': 'file-dialog', 'kind': 'ctest', 'tree': 'b',
                     'discovery': 'b/native-kit/file-dialog-discovery.json', 'full_discovery': main,
                     'pattern': r'^pj_widgets_tests\.FileDialogStartFolderTest\.', 'platform': 'windows'},
                    {'id': 'csv-runtime', 'kind': 'csv', 'tree': 'b', 'discovery': 'b/native-kit/csv-discovery.json',
                     'full_discovery': main, 'pattern': '^CsvRuntimeFileLoader_',
                     'build_identity': 'b/native-kit/build_identity.json', 'prefix': 'b/csv-prefix',
                     'identity': 'b/native-kit/csv-prebuilt.json'},
                ]}
        for suite in plan['suites']:
            if suite['id'] in output_paths:
                suite['allowed_outputs'] = ('b' if suite['id'] == 'main' else 'i') + '/native-kit/allowed-outputs.json'
        if self.marker_guard_paths:
            plan['paths'].update(self.marker_guard_paths)
        launcher = load_module('native_stage_launcher_contract', 'run_native_test_bundle.py')
        try:
            launcher.validate_plan(plan, self.source_sha, self.source_tree, 'RelWithDebInfo')
        except launcher.LauncherError as exc:
            raise PlanError('derived launcher plan is invalid: ' + str(exc)) from exc
        write_new(dialog_path, subset(dialog_cases))
        write_new(csv_path, subset(csv_cases))
        write_new(plan_path, plan)
        for suite, output in output_paths.items():
            write_new(output, self.allowed_outputs[suite])
            self.add('main-build' if suite == 'main' else 'i18n-build', 'native-kit/allowed-outputs.json')
        for item in ('native-kit/file-dialog-discovery.json', 'native-kit/csv-discovery.json', 'native-kit/run-plan.json'):
            self.add('main-build', item)
        self.add('i18n-build', 'temp-probe/RelWithDebInfo/pj_native_temp_probe.exe')
        self.add('main-build', 'ci-temp-probe/RelWithDebInfo/pj_native_ci_temp_probe.exe')

    def finish(self, discovered):
        self.add_producer_evidence()
        self.add_codemodel_candidates()
        for suite in ('main', 'i18n'):
            if suite not in discovered:
                self.issue('missing-discovery', suite)
        for name in ('CsvRuntimeFileLoader_zh_CN', 'CsvRuntimeFileLoader_zh_TW', 'CsvRuntimeFileLoader_en_US'):
            if 'main' in discovered and name not in discovered['main']:
                self.issue('missing-csv-case', name, suite='main', case=name)
        self.add_marker_probe_candidates()
        if self.marker_guard_paths:
            self.condition_patterns = [(suite, prefix,
                'The real-App guard evidence is packaged; the separate CI service-session execution is not approved.'
                if prefix in ('WindowsApplicationContract', 'ArduPilotLayoutRestoreTest') else reason)
                for suite, prefix, reason in self.condition_patterns]
        fixtures = {
            's/pj_scene2D/testdata/test_480p.mp4': ('ffmpeg_decoder_test', 'pj_scene2d_core_source_dir_tests.H264',
                                                    'pj_scene2d_core_source_dir_tests.StreamingVideoDecoder',
                                                    'pj_scene2d_core_source_dir_tests.StreamingVideoSource',
                                                    'pj_scene2d_core_source_dir_tests.StreamingVideoConsumer'),
            's/pj_scene2D/testdata/test_1080p_bframes.mp4': ('pj_scene2d_core_source_dir_tests.StreamingVideoDecoderBframe',),
            's/pj_scene2D/testdata/test_images.mcap': ('mcap_integration_test',),
            's/pj_scene2D/testdata/potato.mcap': ('dual_store_test',),
        }
        for relative, prefixes in fixtures.items():
            if not self.root.joinpath(*relative.split('/')).is_file():
                self.cases.append({'suite': 'main', 'case': None, 'status': 'condition_missing',
                                   'reason': 'Fixture unavailable: ' + relative})
                for prefix in prefixes:
                    self.condition_patterns.append(('main', prefix, 'Conservatively excluded because fixture is unavailable: ' + relative))
        for case in self.cases:
            if not case['case']:
                continue
            reasons = [reason for suite, prefix, reason in self.condition_patterns
                       if case['suite'] == suite and case['case'].startswith(prefix)]
            if reasons:
                case['status'] = 'condition_missing'
                case['reason'] = ' '.join(reasons)
        # These gates cannot be inferred from file extensions or PE import
        # tables. The candidate is deliberately never an upload authorization.
        for code, detail in (
            ('dynamic-dependencies-unreviewed', 'Qt/Python/plugin/subprocess dynamic loads need per-group evidence.'),
            ('provenance-unverified', 'Qt and Conan binary identities, package revisions and licenses need verified evidence.'),
            ('runtime-closure-unverified', 'Static PE normal/delay imports and the selected runtime directories need an independent audit.'),
            ('clean-job-unverified', 'A separate clean Windows job has not verified and run an explicitly closed group.'),
            ('source-selection-unreviewed', 'Tracked source is an over-inclusive candidate, not a reviewed minimum runtime allowlist.'),
        ):
            self.issue(code, detail)
        self.add_run_plan_candidate()
        pe_records = self.pe_inventory()
        referenced = {x['origin'] for x in self.files.values()}
        origins = {key: value for key, value in self.origins.items() if key in referenced}
        plan = {'origins': origins, 'directories': sorted(self.directories, key=str.casefold),
                'files': sorted(self.files.values(), key=lambda x: x['destination'].casefold())}
        report = {'schema': 1, 'status': 'candidate-only-not-uploadable', 'source_sha': self.source_sha,
                  'source_tree': self.source_tree, 'logical_root': self.logical_root,
                  'submodules': {item['path']: item['sha'] for item in self.modules},
                  'files': len(plan['files']), 'blockers': self.blockers, 'coverage': self.cases,
                  'pe_inventory': pe_records,
                  'configuration': 'RelWithDebInfo',
                  'uncovered_conditions': ['Debug-only branches', 'mixed-DPI or DPR configurations not exercised',
                                           'platform-specific cases outside Windows',
                                           'external-service cases without their required environment',
                                           'MainWindow surviving-root final-clear integration negative control not established']}
        return plan, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'logical-root', 'source-sha', 'source-tree', 'output'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--report')
    parser.add_argument('--declarations', type=Path)
    parser.add_argument('--discovery', action='append', default=[], metavar='SUITE=JSON')
    parser.add_argument('--capture-identity', choices=('main', 'i18n'))
    parser.add_argument('--prepare-compiler', choices=('main', 'i18n'))
    parser.add_argument('--check-compiler', choices=('main', 'i18n'))
    parser.add_argument('--compiler-expectation-sha256')
    parser.add_argument('--compiler-preflight-sha256')
    parser.add_argument('--capture-codemodel', action='store_true')
    parser.add_argument('--import-generated-media', type=Path)
    parser.add_argument('--check-generated-media', action='store_true')
    parser.add_argument('--select-codemodel-rules', action='store_true')
    parser.add_argument('--candidate-plan', type=Path)
    parser.add_argument('--reviewed-policy', type=Path)
    parser.add_argument('--qt-version')
    parser.add_argument('--windows-sdk')
    parser.add_argument('--msvc')
    parser.add_argument('--package', action='store_true', help='stage and archive only after source-reviewed closure')
    parser.add_argument('--staging', type=Path)
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--package-receipt', type=Path)
    args = parser.parse_args()
    try:
        if args.prepare_compiler or args.check_compiler:
            if (bool(args.prepare_compiler) == bool(args.check_compiler) or args.capture_identity or args.package or
                    args.capture_codemodel or args.select_codemodel_rules or args.import_generated_media or args.check_generated_media or
                    args.candidate_plan or args.reviewed_policy or args.report or args.declarations or args.discovery or
                    args.staging or args.archive or args.package_receipt or args.compiler_preflight_sha256):
                raise PlanError('compiler preparation/preflight cannot be combined with another mode')
            role = args.prepare_compiler or args.check_compiler
            base = Path(args.root).absolute() / ('b' if role == 'main' else 'i') / 'native-kit/compiler'
            expected_output = base / ('expected.json' if args.prepare_compiler else 'preflight.json')
            if Path(args.output).absolute() != expected_output or expected_output.exists():
                raise PlanError('compiler evidence must use its new exact role-specific output')
            if args.prepare_compiler:
                if args.compiler_expectation_sha256:
                    raise PlanError('compiler preparation cannot reuse an expectation')
                value = prepare_compiler_query(args.root, args.logical_root, args.source_sha, args.source_tree, role)
            else:
                value = capture_compiler_evidence(args.root, args.logical_root, args.source_sha, args.source_tree,
                                                  role, args.qt_version or '', args.compiler_expectation_sha256, 'preflight')
            write_new(args.output, value)
            print(json.dumps({'role': role, 'sha256': digest(expected_output)}))
            return 0
        if not args.capture_identity and (args.compiler_expectation_sha256 or args.compiler_preflight_sha256):
            raise PlanError('compiler hashes require compiler preflight or identity capture')
        if args.import_generated_media or args.check_generated_media:
            if (args.package or args.capture_identity or args.capture_codemodel or args.select_codemodel_rules or
                    args.candidate_plan or args.reviewed_policy or args.report or args.declarations or args.discovery or
                    args.staging or args.archive or args.package_receipt or bool(args.import_generated_media) == args.check_generated_media):
                raise PlanError('generated media import/check cannot be combined with another planner mode')
            if (sys.platform != 'win32' or os.environ.get('GITHUB_ACTIONS') != 'true' or
                    os.environ.get('RUNNER_ENVIRONMENT') != 'github-hosted' or os.environ.get('RUNNER_OS') != 'Windows' or
                    os.environ.get('GITHUB_EVENT_NAME') != 'workflow_dispatch'):
                raise PlanError('generated media import/check is limited to the disposable Windows CI job')
            expected_output = Path(args.root).absolute() / 'b/native-kit/media-fixtures/generation-receipt.json'
            if Path(args.output).absolute() != expected_output:
                raise PlanError('generated media receipt must have its exact same-root path')
            if args.import_generated_media:
                trusted_input = Path(os.environ.get('RUNNER_TEMP', '')).absolute() / 'pj-native-media'
                if args.import_generated_media.absolute() != trusted_input:
                    raise PlanError('generated media input must be the dedicated downloaded CI artifact')
                result = import_generated_media(args.root, args.logical_root, args.source_sha, args.source_tree,
                                                trusted_input, os.environ.get('PJ_MEDIA_MANIFEST_SHA256', ''))
            else:
                result = verified_source_state(args.root, args.logical_root, args.source_sha, args.source_tree)
                if result is None:
                    raise PlanError('generated media evidence is absent')
            print(json.dumps({'source_sha': args.source_sha, 'files': len(result['files'])}))
            return 0
        if args.package:
            if (not args.report or not args.staging or not args.archive or not args.package_receipt or
                    args.capture_identity or args.capture_codemodel or args.select_codemodel_rules or args.candidate_plan or
                    args.reviewed_policy or args.declarations or args.discovery):
                raise PlanError('packaging requires an existing candidate/report and new staging, archive and receipt')
            if args.package_receipt.exists():
                raise PlanError('package receipt must be a new file')
            result = package_candidate(args.root, args.logical_root, args.source_sha, args.source_tree,
                                       args.output, args.report, args.staging, args.archive)
            write_new(args.package_receipt, result)
            print(json.dumps(result, ensure_ascii=False))
            return 0
        if args.select_codemodel_rules:
            if (args.capture_identity or args.capture_codemodel or not args.candidate_plan or not args.report or
                    not args.reviewed_policy or args.declarations or args.discovery or args.staging or args.archive or args.package_receipt):
                raise PlanError('CMake rule selection needs only the exact candidate, report and reviewed policy')
            expected_output = Path(args.root).absolute() / 'b/native-kit/codemodel/selection.json'
            if Path(args.output).absolute() != expected_output or expected_output.exists():
                raise PlanError('CMake rule selection must use a new same-root selection.json')
            value = select_codemodel_rules(args.root, args.logical_root, args.source_sha, args.source_tree,
                                           args.candidate_plan, args.report, args.reviewed_policy)
            write_new(args.output, value)
            print(json.dumps({'selected_rules': [row['rule'] for row in value['rules'] if row['status'] == 'selected']}))
            return 0
        if args.capture_codemodel:
            if args.capture_identity or args.select_codemodel_rules or args.candidate_plan or args.reviewed_policy or args.report or args.declarations or args.discovery or args.staging or args.archive or args.package_receipt:
                raise PlanError('CMake File API capture does not accept other modes')
            expected_output = Path(args.root).absolute() / 'b/native-kit/codemodel/capture.json'
            if Path(args.output).absolute() != expected_output or expected_output.exists():
                raise PlanError('CMake File API capture receipt must be the new same-root capture.json')
            value = capture_codemodel(args.root, args.logical_root, args.source_sha, args.source_tree)
            write_new(args.output, value)
            print(json.dumps({'index': value['index'], 'targets': len(value['targets'])}))
            return 0
        if args.capture_identity:
            if args.select_codemodel_rules or args.candidate_plan or args.reviewed_policy or args.report or args.declarations or args.discovery or args.staging or args.archive or args.package_receipt:
                raise PlanError('build identity capture does not accept a candidate report or declarations')
            value = capture_build_identity(args.root, args.logical_root, args.source_sha, args.source_tree,
                                           args.capture_identity, args.qt_version or '', args.windows_sdk or '', args.msvc or '',
                                           args.compiler_expectation_sha256, args.compiler_preflight_sha256)
            write_new(args.output, value)
            print(json.dumps({'role': value['role'], 'cmake_cache_sha256': value['cmake_cache_sha256']}))
            return 0
        if args.candidate_plan or args.reviewed_policy:
            raise PlanError('candidate plan and reviewed policy options require CMake rule selection')
        if not args.report:
            raise PlanError('candidate planning requires a distinct report path')
        if Path(args.output).absolute() == Path(args.report).absolute() or Path(args.output).exists() or Path(args.report).exists():
            raise PlanError('plan and report must be distinct new files')
        declarations = read_json(args.declarations) if args.declarations else None
        candidate = Candidate(args.root, args.logical_root, args.source_sha, args.source_tree, declarations)
        discovered = {}
        for item in args.discovery:
            suite, sep, name = item.partition('=')
            if not sep or not name or suite in discovered:
                raise PlanError('each discovery needs a unique SUITE=JSON argument')
            discovered[suite] = candidate.add_discovery(suite, read_json(name))
        candidate.add_ctest_metadata()
        plan, report = candidate.finish(discovered)
        write_new(args.output, plan)
        write_new(args.report, report)
        print(json.dumps({'status': report['status'], 'files': report['files'],
                          'blockers': len(report['blockers']), 'cases': len(report['coverage'])}))
        return 2
    except (PlanError, audit.AuditError, OSError, ValueError, KeyError, TypeError, UnicodeError,
            zipfile.BadZipFile, pe_helper.PEError) as exc:
        print('native stage candidate stopped: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
