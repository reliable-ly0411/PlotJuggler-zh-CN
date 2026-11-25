#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Verify source-reviewed CTest groups on a disposable GitHub Windows runner.

This is not the interactive-VM launcher and cannot establish target safety,
GPU use, graphical acceptance or complete dynamic dependency closure. Every
omitted case is reported; only the explicitly approved CI groups are executed.
A trusted host bootstrap must have checked the complete artifact first.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('native_ci_launcher', Path(__file__).with_name('run_native_test_bundle.py'))
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)
audit, review = launcher.audit, launcher.review


class CIError(Exception):
    """CI identity, reviewed selection or test evidence is incomplete."""


def validate_policy(record, discoveries, source_sha, source_tree, config, manifest):
    """Require a complete per-tree case partition with explicit source evidence."""
    if not isinstance(record, dict) or any(record.get(k) != v for k, v in {
            'schema': 1, 'scope': 'github-hosted-windows-ci', 'source_sha': source_sha,
            'source_tree': source_tree, 'configuration': config}.items()):
        raise CIError('CI policy source, configuration or scope differs')
    suites = record.get('suites')
    if not isinstance(suites, list) or len(suites) != len(discoveries) or \
            {item.get('id') for item in suites if isinstance(item, dict)} != set(discoveries):
        raise CIError('CI policy does not cover the declared suite identities exactly once')
    files = {entry['path'].casefold(): entry for entry in manifest['files']}
    decisions = {}
    statuses = {'approved', 'platform_not_applicable', 'condition_missing', 'safety_unreviewed', 'disabled'}
    for suite in suites:
        name = suite['id']; index = review.indexed(discoveries[name])
        groups = suite.get('groups')
        if not isinstance(groups, list) or not groups:
            raise CIError('CI suite has no explicit source-reviewed groups: ' + name)
        cases, group_names = {}, set()
        for group in groups:
            if (not isinstance(group, dict) or not isinstance(group.get('name'), str) or not group['name'] or
                    group['name'] in group_names or group.get('status') not in statuses or
                    not isinstance(group.get('reason'), str) or not group['reason'].strip()):
                raise CIError('invalid CI policy group')
            group_names.add(group['name'])
            evidence = group.get('evidence')
            if not isinstance(evidence, list) or not evidence or any(not isinstance(x, str) or x.casefold() not in files for x in evidence):
                raise CIError('each CI group needs immutable manifest-bound source/closure evidence')
            members = group.get('cases')
            if not isinstance(members, list) or not members:
                raise CIError('CI policy group must list actual discovered cases')
            for case in members:
                if not isinstance(case, str) or case not in index or case in cases:
                    raise CIError('unknown or duplicate CI case: ' + str(case))
                if index[case][1].get('DISABLED', False) and group['status'] == 'approved':
                    raise CIError('disabled CTest case cannot be approved as executed')
                cases[case] = {'status': group['status'], 'reason': group['reason'], 'group': group['name'], 'evidence': evidence}
        if set(cases) != set(index):
            raise CIError('CI policy omits or invents discovered cases: ' + name)
        decisions[name] = cases
    return decisions


def ci_process(argv, cwd, env, stdout_file, stderr_file, expected_identity, timeout):
    """Save CTest streams and identify the actual child; never impersonate a VM."""
    with stdout_file.open('xb') as stdout, stderr_file.open('xb') as stderr:
        child = subprocess.Popen([str(x) for x in argv], cwd=str(cwd), env=env, stdin=subprocess.DEVNULL,
                                 stdout=stdout, stderr=stderr)
        try:
            identity = launcher.process_identity(int(child._handle), child.pid)
            for key in ('sid', 'session', 'integrity_rid', 'auth_luid', 'elevation_type'):
                if identity.get(key) != expected_identity.get(key):
                    raise CIError('CI child process token differs from its actual parent')
        except Exception as exc:
            try:
                child.terminate()
            except OSError:
                pass
            raise CIError('CI child token was not verified; outcome may be uncertain') from exc
        try:
            code = child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            raise CIError('CI process exceeded its outer timeout and may still be running') from None
    return {'argv': [str(x) for x in argv], 'cwd': str(cwd), 'identity': identity, 'exit_code': code,
            'stdout_sha256': launcher.sha256(stdout_file), 'stderr_sha256': launcher.sha256(stderr_file)}


def validate_ci_temp_evidence(evidence, parent, run_root, qt_core, qt_version):
    """Match the actual disposable-CI child token, Qt module and temp path."""
    if (not isinstance(evidence, dict) or evidence.get('scope') != 'disposable-windows-ci-only' or
            evidence.get('qt_version') != qt_version or type(evidence.get('session')) is not int or
            evidence.get('session') != parent['session'] or type(evidence.get('integrity_rid')) is not int or
            evidence.get('integrity_rid') != parent['integrity_rid'] or
            evidence.get('auth_luid') != parent['auth_luid'] or
            evidence.get('elevation_type') != parent['elevation_type'] or
            not isinstance(evidence.get('user_sid'), str) or
            evidence['user_sid'].casefold() != parent['sid'].casefold() or
            type(evidence.get('pid')) is not int or evidence['pid'] <= 0):
        raise CIError('CI Qt temp probe identity or version is inconsistent')
    for field, expected in (('run_root', run_root), ('qt_temp', run_root / 'tmp'), ('qt_core', qt_core)):
        value = evidence.get(field)
        if not isinstance(value, str) or Path(value).resolve(strict=True) != expected.resolve(strict=True):
            raise CIError('CI Qt temp probe reported a different ' + field)


def verify_ci_temp_probe(root, run_root, qt, env, parent, manifest, config, qt_version):
    relative = 'b/ci-temp-probe/' + config + '/pj_native_ci_temp_probe.exe'
    if relative.casefold() not in {item['path'].casefold() for item in manifest['files']}:
        raise CIError('the CI Qt temp probe is not part of the authenticated kit')
    probe = launcher.root_path(root, relative, file=True)
    qt_core = qt / 'bin/Qt6Core.dll'
    command = [probe, '--run-root', run_root, '--temp', run_root / 'tmp', '--qt', qt_version, '--qt-core', qt_core]
    launcher.write_json_new(run_root / 'ci-temp-started.json', {'phase': 'ci-temp', 'argv': [str(x) for x in command],
                            'cwd': str(root), 'started_utc': datetime.now(timezone.utc).isoformat(),
                            'outcome': 'uncertain until ci-temp-process.json exists'})
    process = ci_process(command, root, env, run_root / 'ci-temp.stdout.bin', run_root / 'ci-temp.stderr.bin', parent, 120)
    process.update({'probe_sha256': launcher.sha256(probe), 'qt_core_sha256': launcher.sha256(qt_core),
                    'scope': 'disposable-windows-ci-only'})
    launcher.write_json_new(run_root / 'ci-temp-process.json', process)
    if process['exit_code'] != 0:
        raise CIError('CI Qt temp probe rejected this actual token or temp path')
    evidence = json.loads((run_root / 'ci-temp.stdout.bin').read_text(encoding='utf-8'))
    validate_ci_temp_evidence(evidence, parent, run_root, qt_core, qt_version)
    if evidence['pid'] != process['identity']['pid']:
        raise CIError('CI Qt temp probe PID differs from observed child token')
    return evidence


def validate_ci_selection(prepared, decisions):
    if not any(item['selected'] for item in prepared.values()):
        raise CIError('no source-reviewed CI case can execute')
    for suite, item in prepared.items():
        for row in item['unrun']:
            if decisions[suite][row['case']]['status'] == 'approved':
                raise CIError('an approved CI group lacks fixture, dependency or execution closure: ' + row['case'])


def real_pass_count(coverage):
    nested = {item['test'] for item in coverage['nested_skips']}
    truncated = set(coverage['truncated_outputs'])
    return sum(item['category'] == 'pass' and item['test'] not in nested and item['test'] not in truncated
               for item in coverage['case_results'])


def preserve_ctest_last_log(tree, output):
    """Keep the CTest-owned bytes for this suite before the next one replaces them."""
    tree = Path(tree).absolute()
    output = Path(output).absolute()
    audit.check_root(tree, '', require_exact=False)
    audit.check_root(output, '', require_exact=False)
    output_info = output.lstat()
    if not stat.S_ISDIR(output_info.st_mode):
        raise CIError('CTest evidence destination is not an ordinary directory')
    audit.check_no_named_streams(output, True)
    for directory in (tree, tree / 'Testing', tree / 'Testing/Temporary'):
        try:
            info = directory.lstat()
        except FileNotFoundError:
            return None
        if (not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode) or
                getattr(info, 'st_file_attributes', 0) & 0x400):
            raise CIError('CTest log ancestry contains a link or non-directory')
        audit.check_no_named_streams(directory, True)
    source = tree / 'Testing/Temporary/LastTest.log'
    if not source.exists() and not source.is_symlink():
        return None
    original = audit.regular_file(source)
    audit.check_no_named_streams(source, False)
    destination = output / 'LastTest.log'
    with source.open('rb') as reader, destination.open('xb') as writer:
        opened = os.fstat(reader.fileno())
        identity = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)
        if identity(opened) != identity(original):
            raise CIError('CTest LastTest.log changed before its bytes were opened')
        shutil.copyfileobj(reader, writer)
        if identity(os.fstat(reader.fileno())) != identity(opened):
            raise CIError('CTest LastTest.log changed while preserving its raw bytes')
    before, after = launcher.sha256(source), launcher.sha256(destination)
    if before != after:
        raise CIError('CTest LastTest.log changed while preserving its raw bytes')
    return {'path': 'LastTest.log', 'sha256': after}


def run(args):
    if (sys.platform != 'win32' or os.environ.get('GITHUB_ACTIONS') != 'true' or
            os.environ.get('RUNNER_ENVIRONMENT') != 'github-hosted' or os.environ.get('RUNNER_OS') != 'Windows'):
        raise CIError('this verifier runs only on a disposable GitHub-hosted Windows runner')
    expected_root = 'C:\\Users\\Administrator\\PlotJuggler-4.1.0-zh-test-558a\\n\\' + args.source_sha[:12]
    root = Path(args.root).absolute()
    receipt = audit.read_json(Path(args.bootstrap_receipt))
    expected_receipt = {'schema': 1, 'status': 'verified', 'manifest_sha256': args.manifest_sha256,
                        'archive_sha256': args.archive_sha256,
                        'source_sha': args.source_sha, 'source_tree': args.source_tree, 'configuration': args.config,
                        'logical_root': expected_root, 'kit_code_executed': False}
    if not isinstance(receipt, dict) or any(receipt.get(k) != v for k, v in expected_receipt.items()):
        raise CIError('trusted host bootstrap receipt does not match the exact kit')
    manifest_path = Path(args.manifest).absolute()
    audit.verify_manifest(root, manifest_path, True, args.manifest_sha256, expected_root,
                          args.source_sha, args.source_tree, args.config, allow_owned_runs=True)
    manifest = audit.read_json(manifest_path)
    files = {item['path'].casefold() for item in manifest['files']}
    for relative in (args.plan, args.policy):
        if relative.casefold() not in files:
            raise CIError('CI plan and policy must be authenticated manifest files')
    plan = audit.read_json(launcher.root_path(root, args.plan, file=True))
    paths, runtime_dirs, suites = launcher.validate_plan(plan, args.source_sha, args.source_tree, args.config)
    launcher.validate_plan_bindings(paths, runtime_dirs, suites, manifest)
    python = launcher.root_path(root, paths['python'], file=True)
    if Path(sys.executable).resolve() != python or not sys.flags.isolated or not sys.flags.dont_write_bytecode:
        raise CIError('CI verification must use the verified Python with -I -B')
    launcher.check_driver_import_paths(root)
    if plan.get('qt_version') != manifest['provenance']['qt']:
        raise CIError('CI Qt version differs from the manifest')
    full_docs, selected_docs = {}, {}
    for suite in suites:
        name = suite['id']
        launcher.check_build_identity(root, suite, args.source_sha, args.source_tree, args.config,
                                      next(item['tree'] for item in suites if item['id'] == 'main'))
        full = launcher.root_path(root, suite['full_discovery'], file=True)
        full_docs[name] = audit.read_json(full)
        selected_docs[name] = audit.read_json(launcher.root_path(root, suite['discovery'], file=True))
        launcher.check_suite_contract(root, suite, selected_docs[name])
    policy = audit.read_json(launcher.root_path(root, args.policy, file=True))
    decisions = validate_policy(policy, full_docs, args.source_sha, args.source_tree, args.config, manifest)
    prepared = launcher.selection_plan(suites, full_docs, selected_docs, decisions, 'reviewed-subset')
    validate_ci_selection(prepared, decisions)
    parent = launcher.current_identity()  # CI may have session 0; it is not a user-session attestation.
    run_root = launcher.root_path(root, 'r', directory=True) / ('ci-' + uuid.uuid4().hex)
    run_root.mkdir()
    # This binding is present even if the subsequent Qt probe or a test fails.
    # It identifies the CI candidate; it does not itself grant test approval.
    launcher.write_json_new(run_root / 'artifact-binding.json', {
        'schema': 1, 'scope': 'github-hosted-windows-ci', 'source_sha': args.source_sha,
        'source_tree': args.source_tree, 'configuration': args.config,
        'archive_sha256': args.archive_sha256, 'manifest_sha256': args.manifest_sha256})
    env, qt, python, ctest = launcher.clean_environment(root, run_root, paths, runtime_dirs)
    env.pop('PJ_REQUIRE_GPU_TESTS', None)  # The hosted runner is not the user's GPU.
    launcher.write_json_new(run_root / 'environment.json', env)
    # Persist the complete selected/unrun plan before the first child process,
    # including the Qt probe; an early preflight failure still has a receipt.
    progress = launcher.initialize_execution_plan(run_root, suites, prepared, full_docs, 'reviewed-subset')
    completed = False
    try:
        generated = launcher.generated_ctest_outputs(suites, full_docs, prepared, manifest['logical_root'], root)
        temp_evidence = verify_ci_temp_probe(root, run_root, qt, env, parent, manifest, args.config, plan['qt_version'])
        launcher.check_immutable(root, manifest, manifest_path=manifest_path)
        driver_command = launcher.driver_probe_command(root, manifest, python, manifest_path, args.manifest_sha256)
        launcher.write_json_new(run_root / 'driver-python-started.json', {'argv': driver_command, 'cwd': str(root),
                                'outcome': 'uncertain until driver-python-process.json exists'})
        driver_process = ci_process(driver_command, root, env, run_root / 'driver-python.stdout.bin',
                                    run_root / 'driver-python.stderr.bin', parent, 120)
        launcher.write_json_new(run_root / 'driver-python-process.json', driver_process)
        if driver_process['exit_code'] != 0:
            raise CIError('isolated driver Python identity probe failed')
        driver_evidence = json.loads((run_root / 'driver-python.stdout.bin').read_text(encoding='utf-8'))
        launcher.validate_driver_probe(driver_evidence, manifest, root, args.manifest_sha256, driver_process)
        launcher.check_immutable(root, manifest, manifest_path=manifest_path)
        launcher.write_json_new(run_root / 'ci-identity.json', {'scope': 'github-hosted-windows-ci', 'identity': parent,
                                'source_sha': args.source_sha, 'source_tree': args.source_tree,
                                'manifest_sha256': args.manifest_sha256, 'bootstrap_receipt_sha256': launcher.sha256(args.bootstrap_receipt),
                                'qt_temp_evidence': temp_evidence, 'driver_python_evidence': driver_evidence})
        summary = []; actual_passes = 0
        for suite in suites:
            name = suite['id']; output = run_root / name
            selected, unrun = prepared[name]['selected'], prepared[name]['unrun']
            launcher.check_immutable(root, manifest, generated, manifest_path)
            if not selected:
                summary.append({'suite': name, 'status': 'not_run', 'unrun': unrun})
                continue
            tree = launcher.root_path(root, suite['tree'], directory=True)
            suite_env = launcher.prepare_owned_suite_outputs(root, run_root, suite, selected, full_docs[name], env)
            if suite.get('platform') == 'windows':
                suite_env['QT_QPA_PLATFORM'] = 'windows'
            launcher.write_json_new(output / 'environment.json', suite_env)
            selection_file = output / 'selected.txt'
            with selection_file.open('x', encoding='utf-8', newline='\n') as stream:
                stream.write(''.join(case + '\n' for case in sorted(selected)))
            selection = ['--tests-from-file', str(selection_file)]
            baseline = output / 'selected-discovery.json'
            launcher.write_json_new(baseline, launcher.selected_document(full_docs[name], selected))
            launcher.audit_selected_discovery(root, expected_root, suite, baseline, selected, output, args.config)
            command = [ctest, '--test-dir', tree, '-C', args.config, '--show-only=json-v1', *selection]
            launcher.mark_process_start(output, 'discovery', command, root); progress[name]['phase'] = 'discovery_started'
            result = ci_process(command, root, suite_env, output / 'discovery.stdout.bin', output / 'discovery.stderr.bin', parent, 1800)
            launcher.write_json_new(output / 'discovery-process.json', result); progress[name]['phase'] = 'discovery_finished'
            if result['exit_code'] != 0:
                raise CIError('CI CTest discovery failed: ' + name)
            actual = json.loads((output / 'discovery.stdout.bin').read_text(encoding='utf-8'))
            launcher.same_discovery(audit.read_json(baseline), actual)
            launcher.check_immutable(root, manifest, generated, manifest_path)
            if suite['kind'] == 'csv':
                gate = launcher.load_source_module(root, 's/packaging/localization/run_csv_runtime_acceptance.py', 'ci_csv_gate')
                identity = gate.verify_prebuilt_files(launcher.root_path(root, suite['identity'], file=True),
                    gate.staged_csv(launcher.root_path(root, suite['prefix'], directory=True)), args.source_sha, args.source_tree,
                    qt, ctest, root, manifest_path, args.manifest_sha256,
                    launcher.root_path(root, suite['prefix'], directory=True), tree)
                gate.verify_runtime_directories(tree, qt, root, manifest_path)
                gate.verify_prebuilt_selection(identity, json.dumps(actual))
            report = output / 'junit.xml'
            command = [ctest, '--test-dir', tree, '-C', args.config, '--no-tests=error', '--verbose',
                       '--test-output-size-passed', '1073741824', '--test-output-size-failed', '1073741824',
                       '--output-log', output / 'ctest.log', '--output-junit', report, *selection]
            launcher.mark_process_start(output, 'execution', command, root); progress[name]['phase'] = 'execution_started'
            result = ci_process(command, root, suite_env, output / 'stdout.bin', output / 'stderr.bin', parent, args.timeout)
            result['last_test_log'] = preserve_ctest_last_log(tree, output)
            launcher.write_json_new(output / 'process.json', result); progress[name]['phase'] = 'execution_finished'
            if result['exit_code'] == 0 and result['last_test_log'] is None:
                raise CIError('successful CTest group did not retain LastTest.log: ' + name)
            launcher.write_json_new(output / 'owned-output-inventory.json',
                                    launcher.inventory_owned_suite_outputs(output, selected, result['exit_code'] == 0))
            launcher.write_json_new(output / 'post-suite-inventory.json', launcher.check_immutable(root, manifest, generated, manifest_path))
            if not report.is_file():
                raise CIError('CI suite did not produce its JUnit report: ' + name)
            coverage = audit.audit_results(baseline, report)
            if suite['kind'] == 'csv':
                launcher.write_json_new(output / 'csv-audit.json', {'cases': gate.audit_results(report)})
            if name == 'file-dialog' and selected == prepared[name]['desired']:
                dialog = launcher.load_source_module(root, 's/packaging/localization/audit_file_dialog_results.py', 'ci_dialog_gate')
                launcher.write_json_new(output / 'file-dialog-audit.json', {'cases': dialog.audit(report)})
            if name == 'main':
                feedback = launcher.load_source_module(root, 's/packaging/localization/audit_feedback_results.py', 'ci_feedback_gate')
                if feedback.EXPECTED <= selected:
                    launcher.write_json_new(output / 'feedback-audit.json', {
                        'cases': feedback.audit_cases(ET.parse(report).getroot(), allow_other_cases=True),
                        'screenshots': feedback.audit_images(Path(env['PJ_GUI_ACCEPTANCE_DIR']))})
            launcher.write_json_new(output / 'coverage.json', coverage); progress[name]['phase'] = 'completed'
            actual_passes += real_pass_count(coverage)
            summary.append({'suite': name, 'status': 'completed', 'exit_code': result['exit_code'],
                            'coverage': coverage, 'unrun': unrun, 'repeat_of': progress[name]['repeat_of'],
                            'overlapping_main_case_names': progress[name]['overlapping_main_case_names']})
            if (result['exit_code'] != 0 or coverage['failures'] or coverage['truncated_outputs'] or
                    any(item['category'] in ('not_run', 'disabled') for item in coverage['case_results'])):
                raise CIError('planned CI group failed or had removed output: ' + name)
        launcher.check_immutable(root, manifest, generated, manifest_path)
        if actual_passes == 0:
            raise CIError('CI selected cases produced no fully executed pass')
        conditional = any(row.get('status') == 'completed' and
                          (row['coverage']['top_level_skips'] or row['coverage']['nested_skips']) for row in summary)
        launcher.write_json_new(run_root / 'summary.json', {'schema': 1,
                                'status': 'ci-executed-with-conditional-skips' if conditional else 'planned-ci-groups-completed',
                                'scope': 'github-hosted-windows-ci; target VM safety and coverage are separate',
                                'actual_passes': actual_passes, 'suites': summary})
        completed = True
        return run_root, summary
    finally:
        if not completed:
            launcher.write_json_new(run_root / 'incomplete.json', launcher.incomplete_receipt(progress))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'manifest', 'manifest-sha256', 'archive-sha256', 'source-sha', 'source-tree', 'config', 'plan', 'policy', 'bootstrap-receipt'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--timeout', type=int, default=21600)
    args = parser.parse_args()
    try:
        if (args.timeout <= 0 or not audit.HEX40.fullmatch(args.source_sha) or not audit.HEX40.fullmatch(args.source_tree) or
                not audit.HEX64.fullmatch(args.manifest_sha256) or not audit.HEX64.fullmatch(args.archive_sha256)):
            raise CIError('invalid CI timeout or source identity')
        root, summary = run(args)
        print(json.dumps({'run_root': str(root), 'scope': 'planned-ci-groups-only', 'suites': len(summary)}))
        return 0
    except (CIError, launcher.LauncherError, audit.AuditError, review.ReviewError, OSError, ValueError, KeyError, TypeError, ET.ParseError) as exc:
        print('native CI verification stopped: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
