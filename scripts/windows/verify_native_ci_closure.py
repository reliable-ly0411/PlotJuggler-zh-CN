#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Independently check parts of the source-reviewed native CI closure.

The partition and Qt archive checks below are useful before a Windows run. They
are NOT an execution-closure receipt: a caller must also authenticate extracted
members, Conan packages, host modules, source-reviewed dynamic dependencies and
actual producer/clean-job execution before any kit may be shipped. An optional
ETW trace can add observation; static PE imports and source inspection are not
dynamic observation or proof of user-VM safety.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import ntpath
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent

def _module(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

review = _module('native_ci_closure_review', 'native_test_review.py')
audit = _module('native_ci_closure_audit', 'native_bundle_audit.py')


class ClosureError(Exception):
    """Insufficient, mismatched or unreviewed closure evidence."""


def locked_cpython_host_node(graph, lock, tool_pins):
    """Derive the host recipe from the lock and match the pinned driver ABI."""
    graph_data = graph.get('graph') if isinstance(graph, dict) else None
    nodes = graph_data.get('nodes') if isinstance(graph_data, dict) else None
    requires = lock.get('requires') if isinstance(lock, dict) else None
    artifacts = tool_pins.get('artifacts') if isinstance(tool_pins, dict) else None
    if (not isinstance(nodes, dict) or not isinstance(requires, list) or
            any(not isinstance(item, str) for item in requires) or not isinstance(artifacts, list)):
        raise ClosureError('CPython lock, host graph or pinned tools are malformed')
    pins = [item for item in artifacts if isinstance(item, dict) and item.get('name') == 'python']
    if len(pins) != 1:
        raise ClosureError('expected exactly one pinned official driver Python')
    version = pins[0].get('version')
    driver = re.fullmatch(r'(\d+)\.(\d+)\.(\d+)', version) if isinstance(version, str) else None
    if not driver or f'python{driver[1]}{driver[2]}.dll' != 'python312.dll':
        raise ClosureError('pinned driver Python ABI is unsupported by this kit')
    locked = [ref for ref in requires if ref.startswith('cpython/')]
    hosts = [node for node in nodes.values() if isinstance(node, dict) and node.get('context') == 'host' and
             isinstance(node.get('ref'), str) and node['ref'].startswith('cpython/')]
    pattern = r'cpython/(\d+)\.(\d+)\.(\d+)#[0-9a-f]{32}(?:%[0-9]+(?:\.[0-9]+)?)?'
    if len(locked) != 1 or len(hosts) != 1:
        raise ClosureError('expected exactly one locked and one host CPython recipe')
    locked_version = re.fullmatch(pattern, locked[0])
    host_version = re.fullmatch(pattern, hosts[0]['ref'])
    if (not locked_version or not host_version or
            locked[0].split('%', 1)[0] != hosts[0]['ref'].split('%', 1)[0] or
            locked_version.group(1, 2) != driver.group(1, 2)):
        raise ClosureError('host CPython recipe or ABI differs from the lock and official driver')
    return hosts[0]


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def _safe_relative(value):
    if (not isinstance(value, str) or not value or '\\' in value or
            any(x in ('', '.', '..') or x.endswith((' ', '.')) or audit.is_reserved_component(x) or
                any(ord(c) < 32 or c in '<>:\"|?*' for c in x) for x in value.split('/'))):
        raise ClosureError('expected an unambiguous relative path')
    return value


SYNTHETIC_MEDIA_NAMES = ('test_480p.mp4', 'test_1080p_bframes.mp4', 'test_images.mcap', 'potato.mcap')
SYNTHETIC_MEDIA_PATHS = tuple('s/pj_scene2D/testdata/' + name for name in SYNTHETIC_MEDIA_NAMES)
MEDIA_CONTROL = 'b/native-kit/media-fixtures/'


def source_paths_match(tracked, destinations, generated=()):
    """Compare candidate sources to actual clean-Git paths, not a stale count.

    Recursive git ls-files is supplied by the caller after clean source and
    submodule verification. Conan source-backup blobs are build-only and are
    deliberately excluded by the stage planner.
    """
    if (not isinstance(tracked, list) or not isinstance(destinations, list) or
            any(not isinstance(x, str) for x in destinations)):
        raise ClosureError('source inventories must be explicit lists')
    if tuple(sorted(generated)) not in ((), tuple(sorted(SYNTHETIC_MEDIA_PATHS))):
        raise ClosureError('generated source exceptions must be exactly the four reviewed fixtures')
    expected = list(generated)
    for path in tracked:
        _safe_relative(path)
        if not path.startswith('.github/conan/source-backup/'):
            expected.append('s/' + path)
    actual = [x for x in destinations if isinstance(x, str) and x.casefold().startswith('s/')]
    for value in actual:
        _safe_relative(value)
    if (len({x.casefold() for x in expected}) != len(expected) or
            len({x.casefold() for x in actual}) != len(actual) or sorted(expected) != sorted(actual)):
        raise ClosureError('candidate source files differ from the exact tracked source set')
    return actual


def verify_generated_media(root, source_sha, source_tree, trusted_manifest_sha, manifest_files=None):
    """Bind the exact four source inputs to a successful independent CI job."""
    root = Path(root)
    if not re.fullmatch(r'[0-9a-f]{64}', str(trusted_manifest_sha)):
        raise ClosureError('trusted media-generation job digest is absent or malformed')
    receipt_path = root / (MEDIA_CONTROL + 'generation-receipt.json')
    manifest_path = root / (MEDIA_CONTROL + 'manifest.json')
    license_path = root / (MEDIA_CONTROL + 'MCAP-LICENSE')
    receipt, media = (_strict_json_file(_real_file(path)) for path in (receipt_path, manifest_path))
    for path in (receipt_path, manifest_path, _real_file(license_path)):
        audit.check_no_named_streams(path, False)
    if (not isinstance(receipt, dict) or set(receipt) != {'schema', 'source_sha', 'source_tree', 'manifest_sha256', 'files'} or
            type(receipt['schema']) is not int or receipt['schema'] != 1 or receipt['source_sha'] != source_sha or
            receipt['source_tree'] != source_tree or receipt['manifest_sha256'] != trusted_manifest_sha or
            digest(manifest_path) != trusted_manifest_sha or not isinstance(receipt['files'], dict) or
            set(receipt['files']) != set(SYNTHETIC_MEDIA_PATHS)):
        raise ClosureError('generated media receipt, job digest or source identity differs')
    if (not isinstance(media, dict) or type(media.get('schema')) is not int or media['schema'] != 1 or
            media.get('synthetic') is not True or not isinstance(media.get('files'), dict) or
            set(media['files']) != set(SYNTHETIC_MEDIA_NAMES)):
        raise ClosureError('generated media manifest has unexpected file or semantic identity')
    source_prefix = root / 's/scripts/native-fixtures'
    source_names = ('generate_media_fixtures.py', 'mcap_fixture_generator.cpp', 'mcap-source-lock.json')
    hashes = media.get('generator_sources')
    if not isinstance(hashes, dict) or set(hashes) != set(source_names):
        raise ClosureError('generated media lacks the exact generator source identities')
    for name in source_names:
        path = _real_file(source_prefix / name)
        audit.check_no_named_streams(path, False)
        if not re.fullmatch(r'[0-9a-f]{64}', str(hashes[name])) or digest(path) != hashes[name]:
            raise ClosureError('generated media was built with different source: ' + name)
    source_lock = _strict_json_file(_real_file(source_prefix / 'mcap-source-lock.json'))
    if (not isinstance(source_lock, dict) or media.get('mcap_source') != source_lock or
            not re.fullmatch(r'[0-9a-f]{64}', str(source_lock.get('license_sha256'))) or
            digest(license_path) != source_lock['license_sha256']):
        raise ClosureError('generated media MCAP source or license differs from the source lock')
    for name, relative in zip(SYNTHETIC_MEDIA_NAMES, SYNTHETIC_MEDIA_PATHS):
        entry = receipt['files'][relative]
        if (not isinstance(entry, dict) or set(entry) != {'bytes', 'sha256'} or type(entry['bytes']) is not int or
                entry['bytes'] <= 0 or not re.fullmatch(r'[0-9a-f]{64}', str(entry['sha256'])) or
                media['files'].get(name) != entry):
            raise ClosureError('generated media file identity is malformed or differs: ' + relative)
        path = _real_file(root.joinpath(*relative.split('/')))
        audit.check_no_named_streams(path, False)
        if path.stat().st_size != entry['bytes'] or digest(path) != entry['sha256']:
            raise ClosureError('generated media bytes differ: ' + relative)
    semantics = media.get('semantics')
    video = semantics.get('video') if isinstance(semantics, dict) else None
    mcap = semantics.get('mcap') if isinstance(semantics, dict) else None
    if not isinstance(video, dict) or not isinstance(mcap, dict):
        raise ClosureError('generated media semantic evidence is missing')
    for name, width, height in ((SYNTHETIC_MEDIA_NAMES[0], 640, 480), (SYNTHETIC_MEDIA_NAMES[1], 1920, 1080)):
        v = video.get(name)
        try:
            duration = float(v['duration']) if isinstance(v, dict) else float('nan')
            if (not isinstance(v, dict) or v.get('codec_name') != 'h264' or v.get('pix_fmt') != 'yuv420p' or
                    type(v.get('width')) is not int or v['width'] != width or
                    type(v.get('height')) is not int or v['height'] != height or
                    v.get('avg_frame_rate') != '30/1' or str(v.get('nb_read_frames')) != '120' or
                    not math.isfinite(duration) or abs(duration - 4.0) >= 0.001 or
                    (width == 1920 and (type(v.get('has_b_frames')) is not int or v['has_b_frames'] <= 0))):
                raise ClosureError('generated video semantic evidence differs: ' + name)
        except (ValueError, TypeError, KeyError) as exc:
            raise ClosureError('generated video semantic evidence is malformed: ' + name) from exc
    for name, channels, count in ((SYNTHETIC_MEDIA_NAMES[2], 1, 90), (SYNTHETIC_MEDIA_NAMES[3], 4, 8400)):
        item = mcap.get(name)
        if (not isinstance(item, dict) or type(item.get('channels')) is not int or item['channels'] != channels or
                type(item.get('messages_per_channel')) is not int or item['messages_per_channel'] != count or
                item.get('all_payloads_timestamps_sequences_validated') is not True):
            raise ClosureError('generated MCAP semantic evidence differs: ' + name)
    if manifest_files is not None:
        entries = {row['path'].casefold(): row for row in manifest_files}
        needed = [MEDIA_CONTROL + 'generation-receipt.json', MEDIA_CONTROL + 'manifest.json',
                  MEDIA_CONTROL + 'MCAP-LICENSE', *SYNTHETIC_MEDIA_PATHS,
                  *('s/scripts/native-fixtures/' + name for name in source_names)]
        for relative in needed:
            row = entries.get(relative.casefold())
            if not row or row.get('path') != relative or row.get('sha256') != digest(_real_file(root / relative)):
                raise ClosureError('generated media evidence is not bound to the staged manifest: ' + relative)
    return {'manifest_sha256': trusted_manifest_sha, 'files': receipt['files']}


def verify_generated_source_status(raw):
    """Permit only the four exact generated paths in a previously clean checkout."""
    expected = {'?? ' + path[2:] for path in SYNTHETIC_MEDIA_PATHS}
    if not isinstance(raw, str) or not raw.endswith('\0'):
        raise ClosureError('source status is not a NUL-terminated Git inventory')
    rows = raw[:-1].split('\0')
    if len(rows) != len(expected) or set(rows) != expected:
        raise ClosureError('source checkout has changes beyond the exact generated fixtures')


def parse_tracked_source(raw):
    """Parse ordinary, resolved recursive Git index records without shell quoting."""
    if not isinstance(raw, str) or not raw.endswith('\0'):
        raise ClosureError('tracked source index is not NUL-terminated')
    paths = []
    for row in raw[:-1].split('\0'):
        header, sep, name = row.partition('\t')
        if not sep or not re.fullmatch(r'100(?:644|755) [0-9a-f]{40} 0', header):
            raise ClosureError('tracked source index has a link or unresolved entry')
        _safe_relative(name)
        paths.append(name)
    if not paths:
        raise ClosureError('tracked source index is empty')
    return paths


def verify_independent_checkout(root, checkout, source_sha, source_tree, destinations, manifest_files):
    """Compare staged source with the separately held same-source checkout."""
    root, checkout = Path(root).absolute(), Path(checkout).absolute()
    if checkout == root or checkout.is_relative_to(root):
        raise ClosureError('CI source checkout cannot be inside the staged kit')
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith('GIT_')}
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull, GIT_ATTR_NOSYSTEM='1',
               GIT_TERMINAL_PROMPT='0', GIT_CONFIG_COUNT='1', GIT_CONFIG_KEY_0='core.fsmonitor',
               GIT_CONFIG_VALUE_0='false')
    def git(*args):
        process = subprocess.run(['git', '-C', str(checkout), *args], env=env,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120, check=False)
        if process.returncode:
            raise ClosureError('CI source checkout Git verification failed')
        return process.stdout.decode('utf-8', errors='strict').strip()
    if (git('rev-parse', 'HEAD') != source_sha or git('rev-parse', 'HEAD^{tree}') != source_tree or
            git('status', '--porcelain=v1', '-z', '--untracked-files=all', '--ignore-submodules=none')):
        raise ClosureError('CI source checkout is not the exact clean source')
    tracked = parse_tracked_source(git('ls-files', '--recurse-submodules', '--stage', '-z'))
    source_paths_match(tracked, destinations, SYNTHETIC_MEDIA_PATHS)
    records = {row['path'].casefold(): row for row in manifest_files}
    for relative in tracked:
        if relative.startswith('.github/conan/source-backup/'):
            continue
        path = 's/' + relative
        record = records.get(path.casefold())
        if not record or record.get('path') != path or digest(_real_file(checkout / relative)) != record.get('sha256'):
            raise ClosureError('staged source differs from the CI checkout: ' + relative)
    return {'tracked_files': len(tracked), 'generated_files': len(SYNTHETIC_MEDIA_PATHS)}


def _manifest_evidence(values, files):
    if not isinstance(values, list) or not values:
        raise ClosureError('reviewed evidence must name source files')
    if len({x.casefold() for x in values if isinstance(x, str)}) != len(values):
        raise ClosureError('reviewed evidence has duplicates or non-string paths')
    for value in values:
        _safe_relative(value)
        if not value.startswith('s/') or value.casefold() not in files:
            raise ClosureError('reviewed evidence must be a staged source file: ' + value)
    return values


def derive_partition(policy, discoveries, source_sha, source_tree, logical_root, candidate_files, coverage):
    """Approve only exact reviewed cases; explicitly partition every other case.

    The caller must run this on actual discovery and then verify runner bytes,
    fixture/DEPENDS closure, origins, PE imports, reviewed dynamic dependency
    identities and actual planned-group execution. Source/static analysis is
    not dynamic observation; optional tracing is supplementary. This function
    cannot review a case, manufacture an approval, or execute it.
    """
    if (not isinstance(policy, dict) or policy.get('schema') != 2 or
            not isinstance(discoveries, dict) or
            not isinstance(policy.get('suite_ids'), list) or
            len(set(policy['suite_ids'])) != len(policy['suite_ids']) or
            set(policy['suite_ids']) != set(discoveries)):
        raise ClosureError('reviewed suite identities differ from actual discovery')
    if not re.fullmatch(r'[0-9a-f]{40}', str(source_sha)) or not re.fullmatch(r'[0-9a-f]{40}', str(source_tree)):
        raise ClosureError('full source commit and tree are required')
    if not isinstance(candidate_files, list) or not all(isinstance(x, str) for x in candidate_files):
        raise ClosureError('candidate file list must be explicit')
    folded_files = {x.casefold() for x in candidate_files}
    if len(folded_files) != len(candidate_files):
        raise ClosureError('candidate files contain duplicate or case-colliding paths')
    default_evidence = _manifest_evidence(policy.get('unreviewed_evidence'), folded_files)
    approved = policy.get('approved_cases')
    if not isinstance(approved, list):
        raise ClosureError('exact source-reviewed cases must be an explicit list')
    selected = {}
    for item in approved:
        if not isinstance(item, dict) or not {'suite', 'case', 'executable', 'reason', 'evidence'} <= set(item):
            raise ClosureError('malformed exact approved case')
        suite, case, executable, reason = (item[k] for k in ('suite', 'case', 'executable', 'reason'))
        if suite not in discoveries or not isinstance(case, str) or not case or not isinstance(reason, str) or not reason.strip():
            raise ClosureError('invalid approved suite, case or reason')
        _safe_relative(executable)
        _manifest_evidence(item['evidence'], folded_files)
        key = (suite, case)
        if key in selected:
            raise ClosureError('duplicate exact case approval')
        selected[key] = item
    runners = policy.get('approved_runners', [])
    if not approved and not runners:
        raise ClosureError('at least one exact case or source-reviewed runner is required')
    if not isinstance(runners, list):
        raise ClosureError('approved runners must be an explicit list')
    runner_rules = {}
    for item in runners:
        required = {'suite', 'executable', 'registration_kind', 'name_prefix', 'reason', 'evidence',
                    'source_files', 'dynamic_files', 'subprocesses', 'exclusions', 'value_parameters'}
        if not isinstance(item, dict) or set(item) != required:
            raise ClosureError('malformed source-reviewed runner')
        suite, path = item['suite'], _safe_relative(item['executable'])
        if (suite not in discoveries or item['registration_kind'] != 'gtest-exact-filter' or
                not isinstance(item['name_prefix'], str) or not item['name_prefix'] or
                not isinstance(item['reason'], str) or not item['reason'].strip()):
            raise ClosureError('invalid source-reviewed runner identity')
        _manifest_evidence(item['evidence'], folded_files)
        _manifest_evidence(item['source_files'], folded_files)
        if (not isinstance(item['exclusions'], list) or
                any(not isinstance(x, dict) or set(x) != {'case', 'status', 'reason'} or
                    not isinstance(x['case'], str) or not x['case'] or
                    x['status'] not in {'condition_missing', 'safety_unreviewed', 'platform_not_applicable'} or
                    not isinstance(x['reason'], str) or not x['reason'].strip() for x in item['exclusions']) or
                len({x.get('case') for x in item['exclusions'] if isinstance(x, dict)}) != len(item['exclusions']) or
                not isinstance(item['dynamic_files'], list) or not isinstance(item['subprocesses'], list) or
                not isinstance(item['value_parameters'], dict) or
                any(not isinstance(k, str) or not re.fullmatch(r'[A-Za-z0-9_/]+', k) or
                    not isinstance(v, dict) or not v or len(v) > 1000 or
                    not (v == {'0': 'false', '1': 'true'} or
                         all(isinstance(a, str) and re.fullmatch(r'[A-Za-z0-9_]+', a) and a == b
                             for a, b in v.items()))
                    for k, v in item['value_parameters'].items())):
            raise ClosureError('invalid runner exclusions or dynamic dependencies')
        key = (suite, path.casefold())
        if key in runner_rules:
            raise ClosureError('duplicate runner rule')
        runner_rules[key] = item
    if not isinstance(coverage, list):
        raise ClosureError('candidate condition report must be a list')
    conditions = {}
    for row in coverage:
        if not isinstance(row, dict):
            raise ClosureError('invalid candidate condition record')
        if row.get('status') != 'condition_missing' or not row.get('case'):
            continue
        suite, case, reason = row.get('suite'), row.get('case'), row.get('reason')
        if not isinstance(suite, str) or not isinstance(case, str) or not isinstance(reason, str) or not reason.strip():
            raise ClosureError('invalid missing-condition record')
        for name in ([suite, 'file-dialog', 'csv-runtime'] if suite == 'main' else [suite]):
            conditions.setdefault((name, case), []).append(reason)
    suites = []
    observed_approvals, observed_runners = set(), set()
    for suite in policy['suite_ids']:
        try:
            index = review.indexed(discoveries[suite])
        except review.ReviewError as exc:
            raise ClosureError('invalid discovery for ' + suite + ': ' + str(exc)) from exc
        groups = []
        decisions = {}
        for number, case in enumerate(sorted(index)):
            test, props = index[case]
            item = selected.get((suite, case))
            command = test.get('command')
            runner = None
            if isinstance(command, list) and command and isinstance(command[0], str):
                try:
                    actual_runner = audit.to_relative(command[0], logical_root)
                    runner = runner_rules.get((suite, actual_runner.casefold()))
                except audit.AuditError:
                    pass
            if runner:
                observed_runners.add((suite, actual_runner.casefold()))
            condition = conditions.get((suite, case), [])
            disabled = bool(props.get('DISABLED', False))
            excluded = next((row for row in runner['exclusions'] if row['case'] == case), None) if runner else None
            if runner and not excluded and not item and not disabled and not condition:
                if runner['name_prefix'].endswith('.d3d11.'):
                    try:
                        environment = review.as_names(props.get('ENVIRONMENT'))
                    except review.ReviewError as exc:
                        raise ClosureError('RHI case lacks its exact D3D11 environment: ' + case) from exc
                    if environment != ['PJ_GRAPHICS_API=d3d11']:
                        raise ClosureError('RHI case has an unexpected graphics or output environment: ' + case)
                # Source-reviewed gtest-discover-tests registrations may expand
                # only to a single literal, same-named case: no wildcard,
                # negative filter, extra arguments, or invented executable.
                prefix = runner['name_prefix']
                displayed = case[len(prefix):] if case.startswith(prefix) else ''
                if len(command) != 3 or not command[1].startswith('--gtest_filter='):
                    raise ClosureError('runner registration has an unexpected case argv: ' + case)
                actual_filter = command[1].removeprefix('--gtest_filter=')
                expected_display = actual_filter
                stem, separator, value = actual_filter.rpartition('/')
                suite_name = stem.rpartition('.')[0]
                parameter_map = runner['value_parameters'].get(suite_name, {})
                if separator and value in parameter_map:
                    expected_display = stem + '/' + parameter_map[value]
                    if parameter_map != {'0': 'false', '1': 'true'}:
                        expected_display += '  # GetParam() = ' + parameter_map[value]
                if (not re.fullmatch(r'[A-Za-z0-9_./]+\.[A-Za-z0-9_./]+', actual_filter) or
                        displayed != expected_display or command[2] != '--gtest_also_run_disabled_tests'):
                    raise ClosureError('runner registration has an unexpected case name or argv: ' + case)
                item = runner
            if item:
                command = test.get('command')
                if not isinstance(command, list) or not command or not isinstance(command[0], str):
                    raise ClosureError('approved case has no actual executable')
                try:
                    executable = audit.to_relative(command[0], logical_root)
                except audit.AuditError as exc:
                    raise ClosureError('approved executable is outside the exact root') from exc
                if executable.casefold() != item['executable'].casefold():
                    raise ClosureError('approved case executable differs from the reviewed runner')
                if 'gtest_filter' in item:
                    expected_filter = item['gtest_filter']
                    if (not isinstance(expected_filter, str) or
                            not re.fullmatch(r'[A-Za-z0-9_./]+\.[A-Za-z0-9_./]+', expected_filter) or
                            command[1:] != ['--gtest_filter=' + expected_filter, '--gtest_also_run_disabled_tests']):
                        raise ClosureError('exact reviewed gtest case does not have its literal isolated filter: ' + case)
                if (suite, case) in selected:
                    observed_approvals.add((suite, case))
                if disabled:
                    status, reason, evidence = 'disabled', 'CTest discovery marks this case disabled.', item['evidence']
                elif condition:
                    status, reason, evidence = 'condition_missing', ' '.join(condition), item['evidence']
                elif executable.casefold() not in folded_files:
                    status, reason, evidence = ('condition_missing',
                        'The reviewed runner executable is absent from the candidate: ' + executable, item['evidence'])
                else:
                    status, reason, evidence = 'approved', item['reason'], item['evidence']
            elif disabled:
                status, reason, evidence = 'disabled', 'CTest discovery marks this case disabled.', default_evidence
            elif condition:
                status, reason, evidence = 'condition_missing', ' '.join(condition), default_evidence
            elif excluded:
                status, reason, evidence = excluded['status'], excluded['reason'], runner['evidence']
            else:
                status, reason, evidence = 'safety_unreviewed', 'This exact case has not been reviewed for CI execution.', default_evidence
            name = 'case-' + str(number + 1)
            groups.append({'name': name, 'status': status, 'reason': reason, 'evidence': evidence, 'cases': [case]})
            decisions[case] = {'status': status, 'reason': reason, 'evidence': evidence, 'group': name}
        try:
            review.approved_selection(discoveries[suite], decisions, 'reviewed-subset')
        except review.ReviewError as exc:
            raise ClosureError('approved CTest fixture or DEPENDS closure is incomplete: ' + str(exc)) from exc
        suites.append({'id': suite, 'groups': groups})
    # A reviewed target that the real build did not register is an explicit
    # missing condition, not an invented CTest case and not a reason to discard
    # unrelated safe groups. Consumers must include these records in unrun
    # reporting; only actual approved cases can enter the selection.
    unregistered = []
    for suite, case in sorted(set(selected) - observed_approvals):
        unregistered.append({'suite': suite, 'case': case, 'status': 'condition_missing',
                             'reason': 'This exact reviewed case is absent from the actual CTest discovery.'})
    for suite, path in sorted(set(runner_rules) - observed_runners):
        unregistered.append({'suite': suite, 'executable': runner_rules[(suite, path)]['executable'],
                             'status': 'condition_missing',
                             'reason': 'This reviewed runner has no cases in the actual CTest discovery.'})
    return {'schema': 1, 'scope': 'github-hosted-windows-ci', 'source_sha': source_sha,
            'source_tree': source_tree, 'configuration': 'RelWithDebInfo', 'suites': suites,
            'unregistered': unregistered}


def authenticate_qt_archive(path, pin):
    """Check one retained archive against its source-reviewed official SHA-256.

    This proves only archive bytes, not the extracted files or a running Qt.
    The caller must separately map and compare every staged Qt member to this
    archive using an authenticated extractor, and retain original notices.
    """
    keys = {'file', 'url', 'sha256', 'bytes', 'source'}
    if not isinstance(pin, dict) or set(pin) != keys:
        raise ClosureError('incomplete official Qt archive pin')
    name = pin['file']
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_.-]+\.7z', name):
        raise ClosureError('invalid Qt archive name')
    for field in ('url', 'source'):
        url = urlsplit(str(pin[field]))
        if (url.scheme != 'https' or url.netloc != 'download.qt.io' or url.query or url.fragment or
                url.username or url.password or not url.path.startswith('/online/qtsdkrepository/')):
            raise ClosureError('Qt archive pin must use the official HTTPS repository')
    if (not pin['url'].endswith('/' + name) or pin['source'] != pin['url'] + '.mirrorlist' or
            not re.fullmatch(r'[0-9a-f]{64}', str(pin['sha256'])) or
            type(pin['bytes']) is not int or not 0 < pin['bytes'] <= 1024**3):
        raise ClosureError('invalid official Qt archive identity')
    path = Path(path)
    info = path.lstat()
    if (path.name != name or not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode) or
            getattr(info, 'st_file_attributes', 0) & 0x400 or info.st_size != pin['bytes'] or
            digest(path) != pin['sha256']):
        raise ClosureError('retained Qt archive bytes differ from the official pin: ' + name)
    return {'file': name, 'sha256': pin['sha256'], 'bytes': info.st_size, 'source': pin['source']}



def _real_file(path):
    """Read only regular, single-link files with no redirected ancestors."""
    path = Path(path).absolute()
    for current in (path, *path.parents):
        info = current.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ClosureError('file has a link or reparse-point ancestor: ' + str(path))
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink > 1:
        raise ClosureError('file is not a single-link ordinary file: ' + str(path))
    return path


def _pinned_tool(directory, pin):
    path = _real_file(Path(directory) / pin['file'])
    if (not re.fullmatch(r'[0-9a-f]{64}', str(pin.get('sha256'))) or
            digest(path) != pin['sha256'] or
            ('bytes' in pin and path.stat().st_size != pin['bytes'])):
        raise ClosureError('retained extraction tool archive differs from the source pin')
    return path


def _extract_env(root, temp_dir=None):
    system = os.environ.get('SystemRoot')
    if not system or not ntpath.isabs(system):
        raise ClosureError('trusted Windows SystemRoot is required for Qt archive checks')
    temp = Path(temp_dir) if temp_dir is not None else Path(root) / 't/build-temp'
    if not temp.is_dir():
        raise ClosureError('same-root temporary directory is required for Qt archive checks')
    return {'SystemRoot': system, 'WINDIR': system, 'PATH': ntpath.join(system, 'System32'),
            'TEMP': str(temp), 'TMP': str(temp)}


def _extractor(root, tool_dir=None, temp_dir=None):
    """Verify 7za against pinned 7z-extra using the pinned official 7zr."""
    root = Path(root)
    pins = json.loads(_real_file(root / 's/.github/windows-native-kit/tool-pins.json').read_text(encoding='utf-8'))
    artifacts = pins.get('artifacts') if isinstance(pins, dict) else None
    if not isinstance(artifacts, list):
        raise ClosureError('invalid source-pinned tool manifest')
    values = {item.get('name'): item for item in artifacts if isinstance(item, dict)}
    if len(values) != len(artifacts) or not {'7zr-bootstrap', '7z-extra'} <= set(values):
        raise ClosureError('missing or duplicate pinned 7-Zip inputs')
    tool_dir = Path(tool_dir) if tool_dir is not None else root / 'd'
    bootstrap = _pinned_tool(tool_dir, values['7zr-bootstrap'])
    extra = _pinned_tool(tool_dir, values['7z-extra'])
    executable = _real_file(root / 't/7z/7za.exe')
    if executable.stat().st_size > 32 * 1024 * 1024:
        raise ClosureError('7za executable exceeds the safety size limit')
    # The verified source-pinned 7zr is the only executable used to authenticate
    # the 7za runtime. The member name is fixed, not a caller-provided option.
    result = subprocess.run([str(bootstrap), 'x', '-so', '-spd', str(extra), 'x64/7za.exe'],
                            cwd=root, env=_extract_env(root, temp_dir), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180, check=False)
    if (result.returncode or len(result.stdout) != executable.stat().st_size or
            hashlib.sha256(result.stdout).hexdigest() != digest(executable)):
        raise ClosureError('7za bytes do not match the pinned official 7z-extra archive')
    return executable


def parse_7z_listing(raw):
    """Parse 7-Zip technical listing and reject ambiguous archive member paths."""
    try:
        text = raw.decode('utf-8', errors='strict')
    except UnicodeError as exc:
        raise ClosureError('7-Zip archive listing is not UTF-8') from exc
    entries = {}
    for block in re.split(r'\r?\n\s*\r?\n', text.strip()):
        props = {}
        for line in block.splitlines():
            key, sep, value = line.partition(' = ')
            if not sep or key in props:
                raise ClosureError('malformed or duplicate 7-Zip listing field')
            props[key] = value
        if 'Path' not in props or 'Size' not in props:
            raise ClosureError('7-Zip member listing lacks path or size')
        path = props['Path'].replace('\\', '/')
        _safe_relative(path.rstrip('/'))
        if (props.get('Symbolic Link') or props.get('Hard Link') or props.get('Encrypted') == '+' or
                not re.fullmatch(r'\d+', props['Size'])):
            raise ClosureError('linked, encrypted or malformed Qt archive member')
        size = int(props['Size'])
        if size > 2 * 1024**3:
            raise ClosureError('Qt archive member exceeds size bound')
        key = path.rstrip('/').casefold()
        if key in entries:
            raise ClosureError('duplicate or case-colliding Qt archive members')
        entries[key] = {'path': path.rstrip('/'), 'bytes': size,
                        'directory': props.get('Folder') == '+' or props.get('Attributes', '').startswith('D')}
    if not entries:
        raise ClosureError('Qt archive contains no listed entries')
    return entries


def _qt_selected_files(qt):
    """Select runtime Qt bytes and original installed notices, never build files."""
    qt = Path(qt)
    paths = []
    for directory in ('bin', 'plugins', 'qml', 'translations', 'licenses', 'LICENSES', 'sbom'):
        base = qt / directory
        if not base.is_dir():
            continue
        for path in base.rglob('*'):
            if not path.is_file():
                continue
            relative = path.relative_to(qt).as_posix()
            low = relative.casefold()
            suffix = path.suffix.casefold()
            wanted = ((low.startswith('bin/') and (suffix == '.dll' or path.name.casefold() in
                       {'lrelease.exe', 'lupdate.exe', 'rcc.exe'})) or
                      (low.startswith('plugins/') and suffix == '.dll') or
                      (low.startswith('qml/') and (suffix in {'.dll', '.qml', '.js', '.mjs'} or path.name == 'qmldir')) or
                      (low.startswith('translations/') and suffix == '.qm') or
                      low.startswith(('licenses/', 'sbom/')))
            if wanted:
                _real_file(path)
                paths.append(relative)
    if not paths or len({x.casefold() for x in paths}) != len(paths):
        raise ClosureError('Qt runtime files are absent or case-colliding')
    notices = [x for x in paths if x.casefold().startswith('licenses/')]
    if not notices:
        raise ClosureError('installed Qt original license notices are absent')
    required = {'bin/qt6core.dll', 'bin/lrelease.exe', 'bin/lupdate.exe', 'bin/rcc.exe'}
    if not required <= {x.casefold() for x in paths}:
        raise ClosureError('required Qt runtime or Linguist tools are missing')
    return sorted(paths, key=str.casefold), sorted(notices, key=str.casefold)


def prepare_qt_declarations(root, policy, reference_dir, archive_dir=None, tool_dir=None, temp_dir=None):
    """Re-extract selected Qt files from official pinned archives and compare.

    Intended for the disposable producer only. `reference_dir` must be a new
    child of the owned build root and remains as evidence; no existing directory
    is cleared. Staging or independent job verification must repeat the checks.
    """
    root, reference_dir = Path(root).absolute(), Path(reference_dir).absolute()
    if not reference_dir.is_relative_to(root) or reference_dir.exists() or not reference_dir.parent.is_dir():
        raise ClosureError('Qt comparison output must be a new directory inside the build root')
    pins = policy.get('qt_archives') if isinstance(policy, dict) else None
    version = policy.get('qt_version') if isinstance(policy, dict) else None
    if not isinstance(pins, list) or not pins or not re.fullmatch(r'\d+\.\d+\.\d+', str(version)):
        raise ClosureError('source-reviewed Qt archive and version pins are required')
    pin_map = {pin.get('file'): pin for pin in pins if isinstance(pin, dict)}
    if len(pin_map) != len(pins):
        raise ClosureError('duplicate or malformed Qt archive pin')
    archive_dir = Path(archive_dir) if archive_dir is not None else root / 'd/qt-archives'
    if not archive_dir.is_dir() or archive_dir.is_symlink():
        raise ClosureError('retained Qt archive directory is missing or linked')
    archives = sorted((p for p in archive_dir.iterdir() if p.is_file()), key=lambda p: p.name.casefold())
    if not archives:
        raise ClosureError('retained Qt release archives are missing')
    for archive in archives:
        if archive.name not in pin_map:
            raise ClosureError('retained Qt archive has no source-reviewed official pin: ' + archive.name)
        authenticate_qt_archive(_real_file(archive), pin_map[archive.name])
    qt_rel = f'q/{version}/msvc2022_64'
    qt = root.joinpath(*qt_rel.split('/'))
    selected, notices = _qt_selected_files(qt)
    extractor = _extractor(root, tool_dir, temp_dir)
    prefix = f'{version}/msvc2022_64/'
    match, listings = {}, {}
    for archive in archives:
        result = subprocess.run([str(extractor), 'l', '-slt', '-ba', '-sccUTF-8', str(archive)],
                                cwd=root, env=_extract_env(root, temp_dir), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300, check=False)
        if result.returncode:
            raise ClosureError('7-Zip could not list the authenticated Qt archive: ' + archive.name)
        listing = parse_7z_listing(result.stdout)
        listings[archive.name] = listing
        for name in selected:
            item = listing.get((prefix + name).casefold())
            if item and not item['directory']:
                if name.casefold() in match:
                    raise ClosureError('staged Qt member occurs in more than one archive: ' + name)
                match[name.casefold()] = (archive, item)
    if set(match) != {x.casefold() for x in selected}:
        missing = sorted(set(x.casefold() for x in selected) - set(match))
        raise ClosureError('installed Qt members missing from authenticated archives: ' + ', '.join(missing[:10]))
    needed = sum(item['bytes'] for _, item in match.values())
    if shutil.disk_usage(reference_dir.parent).free < needed + 2 * 1024**3:
        raise ClosureError('insufficient free space to compare Qt members and retain two-GiB reserve')
    reference_dir.mkdir()
    by_archive = {}
    for relative in selected:
        archive, item = match[relative.casefold()]
        if item['bytes'] != _real_file(qt.joinpath(*relative.split('/'))).stat().st_size:
            raise ClosureError('installed Qt member size differs from authenticated archive: ' + relative)
        by_archive.setdefault(archive.name, []).append((relative, item['path']))
    for index, archive in enumerate(archives):
        members = by_archive.get(archive.name, [])
        if not members:
            continue
        target = reference_dir / str(index); target.mkdir()
        listing_file = reference_dir / (str(index) + '.txt')
        with listing_file.open('x', encoding='utf-8', newline='\n') as stream:
            stream.writelines(member + '\n' for _, member in members)
        result = subprocess.run([str(extractor), 'x', '-y', '-spd', '-sccUTF-8', '-scsUTF-8',
                                 '-o' + str(target), str(archive), '@' + str(listing_file)],
                                cwd=root, env=_extract_env(root, temp_dir), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=1800, check=False)
        if result.returncode:
            raise ClosureError('authenticated Qt archive member extraction failed: ' + archive.name)
        for relative, member in members:
            extracted = _real_file(target.joinpath(*member.split('/')))
            if digest(extracted) != digest(_real_file(qt.joinpath(*relative.split('/')))):
                raise ClosureError('installed Qt bytes differ from authenticated archive: ' + relative)
    all_notices = [qt_rel + '/' + name for name in notices]
    origins, files = {}, []
    for index, (name, members) in enumerate(sorted(by_archive.items())):
        origin = 'qt-release-' + str(index + 1)
        origins[origin] = {'root': qt_rel, 'description': 'Official source-pinned Qt release archive',
                           'revision': pin_map[name]['sha256'], 'license_files': all_notices}
        files.extend({'origin': origin, 'source': relative} for relative, _ in members)
    return {'schema': 1, 'origins': origins, 'files': sorted(files, key=lambda x: x['source'].casefold())}

def download_fixed_artifact(pin, directory):
    """Download exact official bytes into a new file; never trust a URL alone."""
    if not isinstance(pin, dict) or not isinstance(pin.get('file'), str) or not re.fullmatch(r'[A-Za-z0-9_.-]+', pin['file']):
        raise ClosureError('invalid fixed artifact filename')
    url = urlsplit(str(pin.get('url', '')))
    if (url.scheme != 'https' or not url.hostname or url.username or url.password or url.query or url.fragment or
            not re.fullmatch(r'[0-9a-f]{64}', str(pin.get('sha256'))) or
            type(pin.get('bytes')) is not int or not 0 < pin['bytes'] <= 1024**3):
        raise ClosureError('invalid HTTPS artifact pin')
    target = Path(directory) / pin['file']
    if target.exists() or not target.parent.is_dir():
        raise ClosureError('fixed artifact destination is not new')
    h, total = hashlib.sha256(), 0
    request = urllib.request.Request(pin['url'], headers={'User-Agent': 'PlotJuggler-native-test-proof/1'})
    with urllib.request.urlopen(request, timeout=120) as response, target.open('xb') as output:
        while True:
            data = response.read(1024 * 1024)
            if not data:
                break
            total += len(data)
            if total > pin['bytes']:
                raise ClosureError('download exceeds the exact source-reviewed artifact size')
            h.update(data); output.write(data)
    if total != pin['bytes'] or h.hexdigest() != pin['sha256']:
        raise ClosureError('download differs from source-reviewed official bytes')
    return target


def prepare_clean_qt_proof(root, policy, proof_dir):
    """Independently fetch and compare Qt on disposable CI, not on the VM."""
    root, proof_dir = Path(root).absolute(), Path(proof_dir).absolute()
    if (proof_dir.exists() or not proof_dir.parent.is_dir() or
            not proof_dir.is_relative_to(root / 'r')):
        raise ClosureError('clean Qt proof needs a new owned run-output directory')
    qt_pins = policy.get('qt_archives') if isinstance(policy, dict) else None
    if not isinstance(qt_pins, list) or not qt_pins:
        raise ClosureError('missing reviewed Qt archive pins')
    tool_document = json.loads(_real_file(root / 's/.github/windows-native-kit/tool-pins.json').read_text(encoding='utf-8'))
    tools = {x.get('name'): x for x in tool_document.get('artifacts', []) if isinstance(x, dict)}
    if not {'7zr-bootstrap', '7z-extra'} <= tools.keys():
        raise ClosureError('clean proof lacks both reviewed 7-Zip inputs')
    selected, _ = _qt_selected_files(root / ('q/' + str(policy.get('qt_version')) + '/msvc2022_64'))
    qt_dir = root / ('q/' + str(policy['qt_version']) + '/msvc2022_64')
    expansion = sum(_real_file(qt_dir.joinpath(*name.split('/'))).stat().st_size for name in selected)
    downloads = qt_pins + [tools['7zr-bootstrap'], tools['7z-extra']]
    if any(type(x.get('bytes')) is not int or x['bytes'] <= 0 for x in downloads):
        raise ClosureError('clean proof needs a source-reviewed byte count for every download')
    if shutil.disk_usage(proof_dir.parent).free < sum(x['bytes'] for x in downloads) + expansion + 2 * 1024**3:
        raise ClosureError('insufficient clean CI space for downloads, Qt extraction and two-GiB reserve')
    proof_dir.mkdir(); archive_dir = proof_dir / 'qt-archives'; archive_dir.mkdir()
    tool_dir = proof_dir / 'tools'; tool_dir.mkdir(); temp_dir = proof_dir / 'tmp'; temp_dir.mkdir()
    for pin in qt_pins:
        download_fixed_artifact(pin, archive_dir)
        authenticate_qt_archive(archive_dir / pin['file'], pin)
    for pin in (tools['7zr-bootstrap'], tools['7z-extra']):
        download_fixed_artifact(pin, tool_dir)
    return prepare_qt_declarations(root, policy, proof_dir / 'reference', archive_dir=archive_dir,
                                   tool_dir=tool_dir, temp_dir=temp_dir)


def verify_clean_tool_payload(root, files, proof_dir):
    """Compare staged runtime tools/notices with official pinned distributions.

    This recheck runs on the clean hosted CI worker, not on the user's VM. It
    does not retroactively authenticate the Python process running this code;
    a trusted pre-execution bootstrap must separately establish that identity.
    """
    root, proof_dir = Path(root).absolute(), Path(proof_dir).absolute()
    if not proof_dir.is_relative_to(root / 'r') or not proof_dir.is_dir():
        raise ClosureError('tool proof requires the existing owned clean-CI proof directory')
    table = {}
    for row in files:
        if not isinstance(row, dict):
            raise ClosureError('invalid staged tool file')
        relative, sha = row.get('path'), row.get('sha256')
        _safe_relative(relative)
        if relative.casefold() in table or not re.fullmatch(r'[0-9a-f]{64}', str(sha)):
            raise ClosureError('duplicate staged tool path or invalid SHA')
        table[relative.casefold()] = row
    def bound(relative):
        row = table.get(relative.casefold())
        if not row or row['path'] != relative:
            raise ClosureError('required official tool file is not manifest-bound: ' + relative)
        path = _real_file(root.joinpath(*relative.split('/')))
        if digest(path) != row['sha256']:
            raise ClosureError('staged tool file changed: ' + relative)
        return path
    document = _strict_json_file(bound('s/.github/windows-native-kit/tool-pins.json'))
    entries = document.get('artifacts') if isinstance(document, dict) else None
    if not isinstance(entries, list):
        raise ClosureError('source-reviewed official tool pins are missing')
    pins = {x.get('name'): x for x in entries if isinstance(x, dict)}
    if len(pins) != len(entries) or set(pins) != {'cmake', 'python', '7zr-bootstrap', '7z-extra', 'ifw'}:
        raise ClosureError('official tool pins are missing or duplicated')
    helper = _module('native_clean_tool_archive_helper', 'prepare_native_tools.py')
    proof = proof_dir / 'runtime-tools'
    if proof.exists() or shutil.disk_usage(proof_dir).free < 5 * 1024**3:
        raise ClosureError('tool proof output is not new or lacks five GiB free space')
    proof.mkdir()
    for name in ('cmake', 'python'):
        try:
            helper.download(pins[name], proof / pins[name]['file'])
            helper.extract_zip(proof / pins[name]['file'], proof / name,
                               'cmake-3.31.10-windows-x86_64/' if name == 'cmake' else '')
        except helper.ToolError as exc:
            raise ClosureError('official ' + name + ' distribution verification failed: ' + str(exc)) from exc
    counts = {}
    for name in ('cmake', 'python'):
        prefix = 't/' + name + '/'
        selected = [row['path'] for row in table.values() if row['path'].startswith(prefix)]
        if not selected:
            raise ClosureError('no official runtime files staged for ' + name)
        for relative in selected:
            suffix = relative[len(prefix):]
            official = _real_file((proof / name).joinpath(*suffix.split('/')))
            staged = bound(relative)
            if relative == 't/python/python312._pth':
                original = official.read_bytes()
                try:
                    original.decode('utf-8', errors='strict')
                except UnicodeError as exc:
                    raise ClosureError('official embedded Python path file is not UTF-8') from exc
                extra = b'' if original.endswith((b'\n', b'\r')) or not original else b'\n'
                for entry in ('s', 's/scripts', 's/tests', 's/packaging/localization'):
                    extra += (str(root.joinpath(*entry.split('/'))) + '\n').encode('utf-8')
                if staged.read_bytes() != original + extra:
                    raise ClosureError('embedded Python path file differs from the reviewed appended paths')
            elif digest(staged) != digest(official):
                raise ClosureError('staged runtime tool differs from the original ZIP: ' + relative)
        counts[name] = len(selected)
    if digest(bound('t/ifw/ifw.7z')) != pins['ifw']['sha256']:
        raise ClosureError('staged IFW archive differs from its official source pin')
    tool_dir, temp = proof_dir / 'tools', proof_dir / 'tmp'
    bootstrap = _pinned_tool(tool_dir, pins['7zr-bootstrap'])
    extra = _pinned_tool(tool_dir, pins['7z-extra'])
    extractor = _extractor(root, tool_dir, temp)
    def listing(executable, archive):
        result = subprocess.run([str(executable), 'l', '-slt', '-ba', '-sccUTF-8', str(archive)],
                                cwd=root, env=_extract_env(root, temp), stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=300, check=False)
        if result.returncode:
            raise ClosureError('official tool archive cannot be listed')
        return parse_7z_listing(result.stdout)
    def compare_member(executable, archive, member, staged):
        if member['bytes'] > 16 * 1024 * 1024:
            raise ClosureError('official tool notice exceeds the bounded size')
        result = subprocess.run([str(executable), 'x', '-so', '-spd', str(archive), member['path']],
                                cwd=root, env=_extract_env(root, temp), stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=300, check=False)
        if (result.returncode or len(result.stdout) != member['bytes'] or
                hashlib.sha256(result.stdout).hexdigest() != digest(bound(staged))):
            raise ClosureError('staged notice differs from the official archive: ' + staged)
    seven = [item for item in listing(bootstrap, extra).values() if not item['directory'] and
             item['path'].rsplit('/', 1)[-1].casefold() == 'license.txt']
    if len(seven) != 1:
        raise ClosureError('official 7-Zip archive has no unique original license')
    compare_member(bootstrap, extra, seven[0], 't/7z/License.txt')
    ifw = bound('t/ifw/ifw.7z')
    original = [x for x in listing(extractor, ifw).values() if not x['directory'] and
                re.search(r'license|licence|notice|copying', x['path'].rsplit('/', 1)[-1], re.I)]
    selected_notices = {x['path'] for x in table.values() if x['path'].startswith('t/ifw/notices/')}
    if not original or {'t/ifw/notices/' + x['path'] for x in original} != selected_notices:
        raise ClosureError('staged IFW notices differ from the complete official archive notices')
    for item in original:
        compare_member(extractor, ifw, item, 't/ifw/notices/' + item['path'])
    return {'scope': 'official tool-byte recheck after trusted process startup', 'cmake_files': counts['cmake'],
            'python_files': counts['python'], 'ifw_notices': len(original)}


def derive_dynamic_inventory(policy, ci_policy, candidate_plan, discoveries, logical_root):
    """Bind source-reviewed anticipated dynamic inputs, never observed loads."""
    if (not isinstance(ci_policy, dict) or ci_policy.get('schema') != 1 or
            not isinstance(candidate_plan, dict) or not isinstance(candidate_plan.get('files'), list)):
        raise ClosureError('invalid CI policy or staging plan for dependency inventory')
    source_pins = policy.get('reviewed_source_sha256') if isinstance(policy, dict) else None
    if not isinstance(source_pins, dict) or not source_pins:
        raise ClosureError('source-reviewed SHA-256 pins are required')
    records = {}
    input_rows = {}
    for row in candidate_plan['files']:
        if not isinstance(row, dict):
            raise ClosureError('invalid stage file entry')
        path, sha = row.get('destination'), row.get('sha256')
        _safe_relative(path)
        if (path.casefold() in records or not re.fullmatch(r'[0-9a-f]{64}', str(sha))):
            raise ClosureError('duplicate stage path or invalid SHA-256')
        records[path.casefold()] = {'path': path, 'sha256': sha}
        input_rows[path.casefold()] = row
    def source_csv_plugin():
        evidence = next((item for item in candidate_plan['files']
                         if item.get('destination') == 'b/native-kit/csv-prebuilt.json'), None)
        if not evidence or evidence.get('origin') not in candidate_plan.get('origins', {}):
            raise ClosureError('CSV plugin selector needs manifest-bound prebuilt identity')
        origin = candidate_plan['origins'][evidence['origin']].get('root')
        if not isinstance(origin, str) or not Path(origin).is_absolute():
            raise ClosureError('CSV prebuilt identity has an invalid source origin')
        record_file = _real_file(Path(origin).joinpath(*_safe_relative(evidence['source']).split('/')))
        if digest(record_file) != evidence['sha256']:
            raise ClosureError('CSV prebuilt identity bytes changed')
        record = json.loads(record_file.read_text(encoding='utf-8'))
        if (record.get('schema') != 1 or record.get('source_sha') != ci_policy['source_sha'] or
                record.get('source_tree') != ci_policy['source_tree'] or record.get('configuration') != ci_policy['configuration']):
            raise ClosureError('CSV prebuilt identity does not match the source and configuration')
        try:
            path = audit.to_relative(record['plugin'], logical_root)
        except (audit.AuditError, KeyError, TypeError) as exc:
            raise ClosureError('CSV prebuilt plugin does not resolve within the same root') from exc
        if (not path.casefold().startswith('b/csv-prefix/lib/plotjuggler/plugins/csv-loader/') or
                not path.casefold().endswith('.dll') or path.casefold() not in records or
                records[path.casefold()]['sha256'] != record.get('plugin_sha256')):
            raise ClosureError('CSV plugin is not the exact staged prebuilt identity')
        return records[path.casefold()]['path']

    def file_entry(path, source=False):
        _safe_relative(path)
        if source and not path.startswith('s/'):
            raise ClosureError('source review evidence must be a source file')
        if path.casefold() not in records:
            raise ClosureError('inventory file is not staged: ' + path)
        return dict(records[path.casefold()])
    def candidate_file(relative):
        item = input_rows.get(relative.casefold())
        origin = candidate_plan.get('origins', {}).get(item.get('origin')) if item else None
        source = item.get('source') if item else None
        if (not isinstance(origin, dict) or not isinstance(origin.get('root'), str) or
                not Path(origin['root']).is_absolute()):
            raise ClosureError('candidate evidence has an invalid source origin')
        path = _real_file(Path(origin['root']).joinpath(*_safe_relative(source).split('/')))
        if digest(path) != item['sha256']:
            raise ClosureError('candidate evidence bytes changed: ' + relative)
        return path
    codemodel_cache = {}
    def source_codemodel_plugin(macro):
        name = 'runtime-catalog-language'
        if name not in codemodel_cache:
            indexes = [x['path'] for x in records.values() if re.fullmatch(
                r'b/native-kit/codemodel/reply/index-[A-Za-z0-9_.-]+\.json', x['path'])]
            if len(indexes) != 1:
                raise ClosureError('runtime catalog requires one retained original CMake File API index')
            manifest_files = list(records.values())
            codemodel_cache[name] = verify_codemodel_dynamic_targets(
                None, logical_root, manifest_files, policy, indexes[0], name,
                ci_policy['source_sha'], ci_policy['source_tree'], resolver=candidate_file)
        result = [x for x in codemodel_cache[name]['artifacts'] if x['definition'] == macro]
        if len(result) != 1:
            raise ClosureError('unreviewed or ambiguous File API plugin definition')
        return result[0]['path']
    cpython_verified = {}
    def source_locked_cpython(artifact, executable):
        allowed = {'runtime-dll': 'bin/python312.dll', 'math-extension': 'bin/DLLs/math.pyd',
                   'stdlib-encodings': 'bin/Lib/encodings/__init__.py', 'stdlib-os': 'bin/Lib/os.py'}
        if artifact not in allowed:
            raise ClosureError('unknown locked CPython runtime artifact')
        graph = _strict_json_file(candidate_file('b/conan-install-graph.json'))
        lock = _strict_json_file(candidate_file('s/conan.lock'))
        pins = _strict_json_file(candidate_file('s/.github/windows-native-kit/tool-pins.json'))
        node = locked_cpython_host_node(graph, lock, pins)
        try:
            folder = audit.to_relative(node['package_folder'], logical_root)
        except (audit.AuditError, KeyError, TypeError) as exc:
            raise ClosureError('locked CPython package leaves the fixed root') from exc
        _safe_relative(folder)
        if not folder.casefold().startswith('c/'):
            raise ClosureError('locked CPython package is not in the controlled Conan tree')
        probe = 'b/pj_scripting/RelWithDebInfo/pj_scripting_python_tests.exe'
        if executable.casefold() != probe.casefold():
            raise ClosureError('locked CPython selector is restricted to the reviewed runtime-identity probe')
        if folder not in cpython_verified:
            dll = candidate_file(folder + '/' + allowed['runtime-dll'])
            math = candidate_file(folder + '/' + allowed['math-extension'])
            runner = candidate_file(probe)
            home = ntpath.join(logical_root, *folder.split('/'), 'bin')
            if (not any(_compiled_literal_present(runner, spelling) for spelling in (home, home.replace('\\', '/'))) or
                    not _compiled_literal_present(runner, digest(dll)) or
                    not _compiled_literal_present(runner, digest(math))):
                raise ClosureError('runtime identity probe does not contain the exact Conan home, DLL and math hashes')
            cpython_verified[folder] = True
        path = folder + '/' + allowed[artifact]
        candidate_file(path)
        return path
    cases = {(x['suite'], x['case']): x for x in policy.get('approved_cases', [])}
    runners = {(x['suite'], x['executable'].casefold()): x for x in policy.get('approved_runners', [])}
    scopes = {}
    for suite in ci_policy.get('suites', []):
        name = suite.get('id')
        if name not in discoveries:
            raise ClosureError('dependency inventory suite has no discovery')
        index = review.indexed(discoveries[name])
        for group in suite.get('groups', []):
            if group.get('status') != 'approved':
                continue
            for case in group.get('cases', []):
                if case not in index:
                    raise ClosureError('dependency inventory case is not discovered')
                test = index[case][0]
                cmd = test.get('command')
                if not isinstance(cmd, list) or not cmd or not isinstance(cmd[0], str):
                    raise ClosureError('dependency inventory case has no runner')
                try:
                    executable = audit.to_relative(cmd[0], logical_root)
                except audit.AuditError as exc:
                    raise ClosureError('dependency inventory runner is outside the root') from exc
                rule = cases.get((name, case)) or runners.get((name, executable.casefold()))
                if not rule or rule['executable'].casefold() != executable.casefold():
                    raise ClosureError('approved case has no exact reviewed inventory rule')
                source_files, dynamic, subprocesses = (rule.get(k) for k in ('source_files', 'dynamic_files', 'subprocesses'))
                if not isinstance(source_files, list) or not source_files or not isinstance(dynamic, list) or not isinstance(subprocesses, list):
                    raise ClosureError('reviewed rule lacks explicit source, dynamic or subprocess lists')
                absent = rule.get('absent_paths', [])
                if not isinstance(absent, list):
                    raise ClosureError('reviewed absent-path conditions must be explicit')
                for path in absent:
                    _safe_relative(path)
                    if any(key == path.casefold() or key.startswith(path.casefold() + '/') for key in records):
                        raise ClosureError('reviewed empty fixture directory is not empty in the stage: ' + path)
                source_entries = [file_entry(x, source=True) for x in source_files]
                if any(source_pins.get(x['path']) != x['sha256'] for x in source_entries):
                    raise ClosureError('source-reviewed file bytes differ from fixed policy pins')
                dynamic_entries = []
                for item in dynamic:
                    if not isinstance(item, dict) or item.get('role') not in {'qt-plugin', 'plugin', 'runtime-module', 'data'}:
                        raise ClosureError('invalid reviewed dynamic file')
                    if set(item) == {'path', 'role'}:
                        path = item['path']
                    elif set(item) == {'selector', 'role'} and item['selector'] == 'csv-prebuilt-plugin' and item['role'] == 'plugin':
                        path = source_csv_plugin()
                    elif (set(item) == {'selector', 'definition', 'role'} and
                          item['selector'] == 'cmake-runtime-catalog-plugin' and item['role'] == 'plugin'):
                        path = source_codemodel_plugin(item['definition'])
                    elif (set(item) == {'selector', 'artifact', 'role'} and item['selector'] == 'locked-cpython' and
                          ((item['artifact'] in {'runtime-dll', 'math-extension'} and item['role'] == 'runtime-module') or
                           (item['artifact'] in {'stdlib-encodings', 'stdlib-os'} and item['role'] == 'data'))):
                        path = source_locked_cpython(item['artifact'], executable)
                    else:
                        raise ClosureError('unknown or malformed reviewed dynamic file selector')
                    dynamic_entries.append({**file_entry(path), 'role': item['role']})
                child_entries = [file_entry(x) for x in subprocesses]
                for rows in (source_entries, dynamic_entries, child_entries):
                    if len({x['path'].casefold() for x in rows}) != len(rows):
                        raise ClosureError('duplicate reviewed inventory file')
                scope = {'suite': name, 'runner': file_entry(executable), 'source_files': source_entries,
                         'dynamic_files': dynamic_entries, 'subprocesses': child_entries, 'reason': rule['reason']}
                key = json.dumps(scope, sort_keys=True, ensure_ascii=False)
                scopes.setdefault(key, {**scope, 'cases': []})['cases'].append(case)
    if not scopes:
        raise ClosureError('dependency inventory has no approved scopes')
    result = list(scopes.values())
    for scope in result:
        scope['cases'].sort()
    return {'schema': 1, 'basis': 'source-analysis', 'source_sha': ci_policy['source_sha'],
            'source_tree': ci_policy['source_tree'], 'configuration': ci_policy['configuration'], 'scopes': result}


def verify_dynamic_inventory(actual, expected):
    if not isinstance(actual, dict) or actual != expected:
        raise ClosureError('dynamic dependency inventory differs from reviewed source and candidate bytes')


CODEMODEL_RULES = {
    'runtime-catalog-language': {
        'target': 'runtime_catalog_language_test',
        'runner': 'b/pj_app/RelWithDebInfo/runtime_catalog_language_test.exe',
        'source': 'pj_app/tests/runtime_catalog_language_test.cpp',
        'cmake': 's/pj_app/CMakeLists.txt',
        'definitions': {
            'PJ_LANGUAGE_SOURCE_PATH': 'pj_sdk_fixture_mock_data_source',
            'PJ_LANGUAGE_PARSER_PATH': 'runtime_host_object_parser_plugin',
            'PJ_LANGUAGE_TOOLBOX_PATH': 'pj_sdk_fixture_mock_toolbox',
            'PJ_LANGUAGE_WIDGET_PATH': 'catalog_language_widget_plugin',
        },
    },
    'extension-manager': {
        'target': 'extension_manager_test',
        'runner': 'b/pj_marketplace/tests/RelWithDebInfo/extension_manager_test.exe',
        'source': 'pj_marketplace/tests/extension_manager_test.cpp',
        'cmake': 's/pj_marketplace/CMakeLists.txt',
        'definitions': {
            'PJ_MOCK_DATA_SOURCE_PLUGIN_PATH': 'pj_sdk_fixture_mock_data_source',
            'PJ_MOCK_DATA_SOURCE_V2_PLUGIN_PATH': 'mock_data_source_v2_plugin',
            'PJ_MOCK_FILE_SOURCE_PLUGIN_PATH': 'pj_sdk_fixture_mock_file_source',
            'PJ_MISSING_ID_PLUGIN_PATH': 'pj_sdk_fixture_missing_id_data_source',
            'PJ_MOCK_PINNING_PLUGIN_PATH': 'mock_data_source_pinning_plugin',
            'PJ_MOCK_PINNING_V2_PLUGIN_PATH': 'mock_data_source_pinning_v2_plugin',
            'PJ_MOCK_INCOMPATIBLE_PLUGIN_PATH': 'mock_data_source_incompatible_plugin',
            'PJ_MOCK_COMPATIBLE_FLOOR_PLUGIN_PATH': 'mock_data_source_compatible_floor_plugin',
            'PJ_MOCK_MALFORMED_FLOOR_PLUGIN_PATH': 'mock_data_source_malformed_floor_plugin',
            'PJ_MOCK_MALFORMED_VERSION_PLUGIN_PATH': 'mock_data_source_malformed_version_plugin',
            'PJ_MOCK_NEWER_SDK_PLUGIN_PATH': 'mock_data_source_newer_sdk_plugin',
        },
    },
}

# Fixed bytes reviewed against the locked SDK 0.39.0 source and its Conan
# package, not generated from the producer's CMake reply.
SDK_FIXTURE_FILES = {
    'lib/cmake/plotjuggler_sdk/PjSdkTestFixtures.cmake': 'f75be371f6762d56a9589e702c0f4f64744cb171ffc22b6d3cc741b26f030a1b',
    'share/plotjuggler_sdk/test_fixtures/mock_data_source.cpp': '14a0408084de07098db8f9d3719269680b3e649e8b19ea1b80f64284e23001d6',
    'share/plotjuggler_sdk/test_fixtures/mock_file_source.cpp': '136ba71f13cad223a0b6e490e4dc4cd6d63b41b5b9866097a8b4805b4b2dd7ba',
    'share/plotjuggler_sdk/test_fixtures/mock_toolbox.cpp': 'bbd4562640abd5401b56e2e2defcffe1a8a33a1b8b4b04e0994ccaf25d5d265b',
    'share/plotjuggler_sdk/test_fixtures/missing_id_data_source_plugin.cpp': 'c1a03a08d7ff1160bdf29f7d82e5f940c2eb4b72e0956af7c5e7768a1fde5c6e',
}
CODEMODEL_PLUGIN_SOURCES = {
    'pj_sdk_fixture_mock_data_source': ('sdk', 'share/plotjuggler_sdk/test_fixtures/mock_data_source.cpp'),
    'pj_sdk_fixture_mock_file_source': ('sdk', 'share/plotjuggler_sdk/test_fixtures/mock_file_source.cpp'),
    'pj_sdk_fixture_mock_toolbox': ('sdk', 'share/plotjuggler_sdk/test_fixtures/mock_toolbox.cpp'),
    'pj_sdk_fixture_missing_id_data_source': ('sdk', 'share/plotjuggler_sdk/test_fixtures/missing_id_data_source_plugin.cpp'),
    'runtime_host_object_parser_plugin': ('source', 'pj_runtime/tests/runtime_host_object_parser_plugin.cpp'),
    'catalog_language_widget_plugin': ('source', 'pj_runtime/tests/runtime_widget_plugin.cpp'),
    'mock_data_source_v2_plugin': ('source', 'pj_runtime/tests/mock_data_source_v2_plugin.cpp'),
    'mock_data_source_pinning_plugin': ('source', 'pj_runtime/tests/mock_data_source_pinning_plugin.cpp'),
    'mock_data_source_pinning_v2_plugin': ('source', 'pj_runtime/tests/mock_data_source_pinning_plugin.cpp'),
    'mock_data_source_incompatible_plugin': ('source', 'pj_runtime/tests/mock_data_source_incompatible_plugin.cpp'),
    'mock_data_source_compatible_floor_plugin': ('source', 'pj_runtime/tests/mock_data_source_compatible_floor_plugin.cpp'),
    'mock_data_source_malformed_floor_plugin': ('source', 'pj_runtime/tests/mock_data_source_malformed_floor_plugin.cpp'),
    'mock_data_source_malformed_version_plugin': ('source', 'pj_runtime/tests/mock_data_source_malformed_version_plugin.cpp'),
    'mock_data_source_newer_sdk_plugin': ('source', 'pj_runtime/tests/mock_data_source_newer_sdk_plugin.cpp'),
}


def _strict_json_file(path):
    """CMake evidence is data, including duplicate keys, not an authority."""
    if path.stat().st_size > 64 * 1024 * 1024:
        raise ClosureError('CMake File API JSON exceeds the size limit')
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ClosureError('duplicate key in CMake File API JSON')
            value[key] = item
        return value
    try:
        return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique)
    except (UnicodeError, ValueError) as exc:
        raise ClosureError('invalid CMake File API JSON') from exc


def _compiled_literal_present(path, value):
    """Detect a NUL-terminated narrow or UTF-16 literal without loading the PE.

    Presence is a consistency check, not proof that the compiler consumed a
    particular command or that any code path executed. A missing literal fails
    closed, including when a compiler transforms it into an unrecognizable form.
    """
    needles = (value.encode('utf-8') + b'\0', value.encode('utf-16-le') + b'\0\0')
    overlap = max(map(len, needles)) - 1
    tail = b''
    with path.open('rb') as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                return False
            data = tail + chunk
            if any(needle in data for needle in needles):
                return True
            tail = data[-overlap:]


def verify_codemodel_dynamic_targets(root, logical_root, files, policy, index_relative,
                                     rule_name, source_sha, source_tree, resolver=None):
    """Bind reviewed TARGET_FILE macros to File API targets and actual bytes.

    All referenced reply JSON, source files, the executable and DLLs must be
    manifest-bound. The caller must independently authenticate the exact clean
    source, configure/query, build process and execution; neither File API nor
    a literal found in the PE proves those events or a dynamic load occurred.
    `resolver`, if supplied, maps staged relative paths to candidate source
    files; it does not change the required SHA-256 checks.
    """
    if (rule_name not in CODEMODEL_RULES or not isinstance(files, list) or
            not isinstance(policy, dict) or
            not re.fullmatch(r'[0-9a-f]{40}', str(source_sha)) or
            not re.fullmatch(r'[0-9a-f]{40}', str(source_tree))):
        raise ClosureError('invalid File API source, policy, or reviewed rule')
    try:
        logical_root = audit.windows_root(logical_root)
    except audit.AuditError as exc:
        raise ClosureError('invalid File API logical root') from exc
    table = {}
    for item in files:
        if not isinstance(item, dict):
            raise ClosureError('invalid File API manifest entry')
        relative, sha = item.get('path'), item.get('sha256')
        _safe_relative(relative)
        if (relative.casefold() in table or not re.fullmatch(r'[0-9a-f]{64}', str(sha))):
            raise ClosureError('duplicate File API manifest path or invalid hash')
        table[relative.casefold()] = item
    def bound(relative):
        _safe_relative(relative)
        row = table.get(relative.casefold())
        if not row or row['path'] != relative:
            raise ClosureError('File API input is not an exact manifest file: ' + relative)
        path = _real_file(resolver(relative) if resolver else Path(root).joinpath(*relative.split('/')))
        if digest(path) != row['sha256']:
            raise ClosureError('File API input bytes changed: ' + relative)
        return path
    def in_root(value, base):
        if not isinstance(value, str) or not value or any(ord(ch) < 32 or ch == '"' for ch in value):
            raise ClosureError('invalid File API path')
        if ntpath.isabs(value):
            full = value
        else:
            if ntpath.splitdrive(value)[0] or value.startswith(('/', '\\')):
                raise ClosureError('ambiguous File API relative path')
            full = ntpath.join(logical_root, base, value)
        parts = full.replace('\\', '/').split('/')
        if (not re.fullmatch(r'[A-Za-z]:', parts[0]) or
                any(part in ('', '.', '..') or part.endswith((' ', '.')) for part in parts[1:])):
            raise ClosureError('ambiguous or noncanonical File API path')
        try:
            relative = audit.to_relative(full, logical_root)
        except audit.AuditError as exc:
            raise ClosureError('File API path leaves the exact root') from exc
        _safe_relative(relative)
        if not relative.casefold().startswith(base.casefold() + '/'):
            raise ClosureError('File API path leaves the expected source/build tree')
        return relative
    def same_absolute(value, expected):
        if not isinstance(value, str) or not ntpath.isabs(value):
            return False
        return ntpath.normcase(ntpath.normpath(value)) == ntpath.normcase(ntpath.normpath(expected))
    def read_reply(parent, name, pattern):
        if (not isinstance(name, str) or not re.fullmatch(pattern, name) or '/' in name or '\\' in name):
            raise ClosureError('invalid CMake File API reply filename')
        rel = parent + '/' + name
        return _strict_json_file(bound(rel)), rel
    rule = CODEMODEL_RULES[rule_name]
    pins = policy.get('reviewed_source_sha256')
    for source in (rule['cmake'], 's/' + rule['source'], 's/pj_runtime/CMakeLists.txt'):
        if not isinstance(pins, dict) or pins.get(source) != digest(bound(source)):
            raise ClosureError('File API rule source is not pinned to the reviewed bytes: ' + source)
    helper_suffix = '/lib/cmake/plotjuggler_sdk/PjSdkTestFixtures.cmake'
    helpers = [x['path'] for x in table.values() if x['path'].startswith('c/') and x['path'].endswith(helper_suffix)]
    if len(helpers) != 1 or digest(bound(helpers[0])) != SDK_FIXTURE_FILES[helper_suffix[1:]]:
        raise ClosureError('the locked SDK fixture helper is missing or differs from the reviewed bytes')
    sdk_folder = helpers[0][:-len(helper_suffix)]
    index_relative = _safe_relative(index_relative)
    if not re.fullmatch(r'b/native-kit/codemodel/reply/index-[A-Za-z0-9_.-]+\.json', index_relative):
        raise ClosureError('File API index must be the retained original reply filename')
    index = _strict_json_file(bound(index_relative))
    parent = index_relative.rsplit('/', 1)[0]
    reply = index.get('reply', {}).get('codemodel-v2') if isinstance(index, dict) else None
    generator = index.get('cmake', {}).get('generator', {}) if isinstance(index, dict) else {}
    if (not isinstance(reply, dict) or reply.get('kind') != 'codemodel' or
            reply.get('version', {}).get('major') != 2 or
            generator.get('name') != 'Ninja Multi-Config' or generator.get('multiConfig') is not True):
        raise ClosureError('expected the original Ninja Multi-Config codemodel-v2 reply')
    model, model_path = read_reply(parent, reply.get('jsonFile'), r'codemodel-v2-[A-Za-z0-9_.-]+\.json')
    if (not isinstance(model, dict) or model.get('kind') != 'codemodel' or
            model.get('version', {}).get('major') != 2 or not isinstance(model.get('paths'), dict) or
            not same_absolute(model['paths'].get('source'), ntpath.join(logical_root, 's')) or
            not same_absolute(model['paths'].get('build'), ntpath.join(logical_root, 'b'))):
        raise ClosureError('codemodel source, build tree, or version differs')
    configs = model.get('configurations')
    if not isinstance(configs, list):
        raise ClosureError('codemodel has no configurations')
    matched = [x for x in configs if isinstance(x, dict) and x.get('name') == 'RelWithDebInfo']
    if len(matched) != 1 or not isinstance(matched[0].get('targets'), list):
        raise ClosureError('expected one complete RelWithDebInfo target set')
    refs = {}
    for item in matched[0]['targets']:
        if not isinstance(item, dict) or not isinstance(item.get('name'), str) or not isinstance(item.get('id'), str):
            raise ClosureError('invalid codemodel target reference')
        if item['name'] in refs:
            raise ClosureError('duplicate codemodel target name')
        refs[item['name']] = item
    needed = [rule['target'], *rule['definitions'].values()]
    if len(set(needed)) != len(needed) or any(name not in refs for name in needed):
        raise ClosureError('required runner or plugin target is missing or ambiguous')
    targets, json_paths = {}, [index_relative, model_path]
    for name in needed:
        ref = refs[name]
        target, json_path = read_reply(parent, ref.get('jsonFile'), r'target-[A-Za-z0-9_.+-]+\.json')
        if (not isinstance(target, dict) or target.get('name') != name or target.get('id') != ref['id'] or
                target.get('type') != ('EXECUTABLE' if name == rule['target'] else 'SHARED_LIBRARY')):
            raise ClosureError('File API target identity or type differs: ' + name)
        targets[name] = target
        json_paths.append(json_path)
        if name == rule['target']:
            continue
        kind, relative_source = CODEMODEL_PLUGIN_SOURCES[name]
        expected_source = ('s/' if kind == 'source' else sdk_folder + '/') + relative_source
        source_file = bound(expected_source)
        if kind == 'sdk':
            if digest(source_file) != SDK_FIXTURE_FILES[relative_source]:
                raise ClosureError('SDK fixture source differs from reviewed bytes: ' + relative_source)
        elif not isinstance(pins, dict) or pins.get(expected_source) != digest(source_file):
            raise ClosureError('plugin source is not pinned to reviewed bytes: ' + expected_source)
        entries = target.get('sources')
        if not isinstance(entries, list):
            raise ClosureError('plugin target does not record its compiled sources: ' + name)
        candidates = []
        for entry in entries:
            if not isinstance(entry, dict):
                raise ClosureError('invalid plugin target source')
            if entry.get('isGenerated') is True:
                continue
            value = entry.get('path')
            # The installed Conan package is a sibling of the source tree, so
            # File API records that fixture's path as an absolute c/ path.
            base = 'c' if kind == 'sdk' and isinstance(value, str) and ntpath.isabs(value) else 's'
            candidates.append(in_root(value, base))
        if sum(x.casefold() == expected_source.casefold() for x in candidates) != 1:
            raise ClosureError('plugin target does not compile the reviewed fixture source: ' + name)
    if len({x.casefold() for x in json_paths}) != len(json_paths):
        raise ClosureError('File API reply files must be distinct')
    def artifact(target, suffix):
        entries = target.get('artifacts')
        if not isinstance(entries, list):
            raise ClosureError('File API target has no artifacts')
        values = []
        for item in entries:
            if not isinstance(item, dict):
                raise ClosureError('invalid File API artifact')
            path = in_root(item.get('path'), 'b')
            if path.lower().endswith(suffix):
                values.append(path)
        if len(values) != 1:
            raise ClosureError('expected exactly one executable or DLL target artifact')
        bound(values[0])
        return values[0]
    runner = targets[rule['target']]
    runner_path = artifact(runner, '.exe')
    if runner_path.casefold() != rule['runner'].casefold():
        raise ClosureError('File API runner differs from the reviewed discovery executable')
    dependencies = runner.get('dependencies')
    if not isinstance(dependencies, list) or any(not isinstance(x, dict) or not isinstance(x.get('id'), str) for x in dependencies):
        raise ClosureError('File API runner has no explicit target dependencies')
    dependency_ids = {x['id'] for x in dependencies}
    if any(refs[name]['id'] not in dependency_ids for name in rule['definitions'].values()):
        raise ClosureError('File API runner is missing a reviewed plugin target dependency')
    sources, groups = runner.get('sources'), runner.get('compileGroups')
    if not isinstance(sources, list) or not isinstance(groups, list):
        raise ClosureError('File API runner compile groups are missing')
    selected = []
    for item in sources:
        if not isinstance(item, dict):
            raise ClosureError('invalid File API source entry')
        # Automoc and other generated sources are build-tree paths. They must
        # not be mistaken for the reviewed, non-generated test translation unit.
        base = 'b' if item.get('isGenerated') is True else 's'
        path = in_root(item.get('path'), base)
        if base == 's' and path.casefold() == ('s/' + rule['source']).casefold():
            selected.append(item)
    if len(selected) != 1 or type(selected[0].get('compileGroupIndex')) is not int:
        raise ClosureError('File API runner does not contain the reviewed test source once')
    group_index = selected[0]['compileGroupIndex']
    if group_index < 0 or group_index >= len(groups):
        raise ClosureError('File API compile group index is invalid')
    group = groups[group_index]
    if not isinstance(group, dict) or group.get('language') != 'CXX' or not isinstance(group.get('defines'), list):
        raise ClosureError('reviewed source needs an explicit C++ compile group')
    definitions = {}
    for entry in group['defines']:
        raw = entry.get('define') if isinstance(entry, dict) else None
        if not isinstance(raw, str):
            raise ClosureError('invalid CMake compile definition')
        key, separator, value = raw.partition('=')
        if key in rule['definitions']:
            if not separator or key in definitions:
                raise ClosureError('duplicate or valueless reviewed compile definition')
            if value.startswith('\\"') and value.endswith('\\"'):
                value = value[2:-2]
            elif value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            else:
                raise ClosureError('reviewed compile definition is not a quoted literal')
            definitions[key] = value
    if set(definitions) != set(rule['definitions']):
        raise ClosureError('reviewed target-file definitions are incomplete')
    runner_file = bound(runner_path)
    result = []
    for macro, target_name in rule['definitions'].items():
        value = definitions[macro]
        if not ntpath.isabs(value):
            raise ClosureError('compiled target path must be absolute')
        relative = in_root(value, 'b')
        target_path = artifact(targets[target_name], '.dll')
        if relative.casefold() != target_path.casefold():
            raise ClosureError('compile definition does not match its exact target artifact: ' + macro)
        if not _compiled_literal_present(runner_file, value):
            raise ClosureError('reviewed compile path is not present as a terminated executable literal: ' + macro)
        result.append({'definition': macro, 'target': target_name, 'path': target_path,
                       'sha256': table[target_path.casefold()]['sha256']})
    if len({x['path'].casefold() for x in result}) != len(result):
        raise ClosureError('distinct reviewed plugin targets resolved to the same DLL')
    return {'schema': 1, 'basis': 'cmake-file-api-and-executable-literals',
            'source_sha': source_sha, 'source_tree': source_tree, 'configuration': 'RelWithDebInfo',
            'runner': {'path': runner_path, 'sha256': table[runner_path.casefold()]['sha256']},
            'reply_files': [{'path': x, 'sha256': table[x.casefold()]['sha256']} for x in json_paths],
            'artifacts': result}



def verify_host_system_resolution(names, system_root, resolver):
    """Check each reviewed Windows system import, including API-set backing files.

    This independently measures this CI host only; it is not proof about the
    user's VM, all possible dynamic loads or modules not present in `names`.
    `resolver` must resolve with Windows' System32-only loader and return the
    real module path, SHA-256 and a verified Microsoft Authenticode identity.
    """
    if (not isinstance(names, list) or not names or any(not isinstance(x, str) or
            not re.fullmatch(r'[A-Za-z0-9_.+-]+\.dll', x, re.I) for x in names) or
            len({x.casefold() for x in names}) != len(names) or not ntpath.isabs(system_root)):
        raise ClosureError('individually reviewed Windows system DLL names are required')
    expected_dir = ntpath.normcase(ntpath.normpath(ntpath.join(system_root, 'System32')))
    results = []
    for name in names:
        entry = resolver(name)
        if (not isinstance(entry, dict) or entry.get('requested') != name or
                not isinstance(entry.get('path'), str) or
                ntpath.normcase(ntpath.normpath(ntpath.dirname(entry['path']))) != expected_dir or
                not re.fullmatch(r'[0-9a-f]{64}', str(entry.get('sha256'))) or
                entry.get('signature_status') != 'Valid' or
                not isinstance(entry.get('signature_subject'), str) or
                not re.search(r'(?:^|,\s*)CN=Microsoft(?: |,|$)', entry['signature_subject'], re.I) or
                not re.search(r'(?:^|,\s*)O=Microsoft Corporation(?:,|$)', entry['signature_subject'], re.I)):
            raise ClosureError('system DLL did not resolve to a signed Microsoft System32 image: ' + name)
        results.append(entry)
    return {'schema': 1, 'scope': 'disposable-windows-ci-only', 'modules': results}



def _real_system_file(path):
    """System32 may hard-link signed images to WinSxS; reject reparse points."""
    path = Path(path).absolute()
    for current in (path, *path.parents):
        info = current.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ClosureError('system file has a reparse-point ancestor: ' + str(path))
    if not stat.S_ISREG(path.lstat().st_mode):
        raise ClosureError('system image is not a regular file')
    return path

def windows_system_resolver(name, allow_not_found=False):
    """Resolve/load on disposable 64-bit Windows and verify its signature."""
    if (sys.platform != 'win32' or os.environ.get('GITHUB_ACTIONS') != 'true' or
            os.environ.get('RUNNER_ENVIRONMENT') != 'github-hosted' or sys.maxsize < 2**32):
        raise ClosureError('system resolution requires disposable 64-bit Windows hosted CI')
    import ctypes
    from ctypes import wintypes
    system = os.environ.get('SystemRoot', '')
    if not ntpath.isabs(system):
        raise ClosureError('Windows SystemRoot is missing')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.LoadLibraryExW.argtypes = [wintypes.LPCWSTR, wintypes.HANDLE, wintypes.DWORD]
    kernel.LoadLibraryExW.restype = wintypes.HMODULE
    kernel.GetModuleFileNameW.argtypes = [wintypes.HMODULE, wintypes.LPWSTR, wintypes.DWORD]
    kernel.GetModuleFileNameW.restype = wintypes.DWORD
    kernel.FreeLibrary.argtypes = [wintypes.HMODULE]
    kernel.FreeLibrary.restype = wintypes.BOOL
    virtual = name.casefold().startswith(('api-', 'ext-'))
    system_file = Path(system) / 'System32' / name
    if allow_not_found and not virtual:
        try:
            system_file.lstat()
        except FileNotFoundError:
            # Probe the intended system path first: a same-named bundled
            # module may already be loaded in this verifier process (notably
            # python312.dll), and must not impersonate System32 resolution.
            return None
        except OSError as exc:
            raise ClosureError('cannot establish the System32 module path: ' + name) from exc
    handle = kernel.LoadLibraryExW(name if virtual else str(system_file), None, 0x00000800)
    if not handle:
        error = ctypes.get_last_error()
        # An absent ordinary DLL may be a same-root bundled provider. A
        # virtual API-set contract, an existing System32 file with missing
        # dependencies, and every other loader error remain hard failures.
        raise ClosureError('Windows could not resolve this reviewed system import: ' + name)
    try:
        buffer = ctypes.create_unicode_buffer(32768)
        size = kernel.GetModuleFileNameW(handle, buffer, len(buffer))
        if not size or size >= len(buffer):
            raise ClosureError('Windows did not return a complete resolved module path')
        path = _real_system_file(Path(buffer.value))
        if ntpath.normcase(ntpath.normpath(str(path.parent))) != ntpath.normcase(ntpath.join(system, 'System32')):
            raise ClosureError('system import resolved outside System32: ' + name)
        before = digest(path)
        shell = Path(system) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
        _real_system_file(shell)
        env = {'SystemRoot': system, 'WINDIR': system, 'PATH': ntpath.join(system, 'System32'),
               'PJ_SIGNED_MODULE': str(path)}
        command = ("$s=Get-AuthenticodeSignature -LiteralPath $env:PJ_SIGNED_MODULE; "
                   "[pscustomobject]@{status=$s.Status.ToString(); subject=$s.SignerCertificate.Subject} | ConvertTo-Json -Compress")
        result = subprocess.run([str(shell), '-NoProfile', '-NonInteractive', '-Command', command], env=env,
                                capture_output=True, timeout=120, check=False)
        if result.returncode:
            raise ClosureError('Windows signature verification failed: ' + name)
        signature = json.loads(result.stdout.decode('utf-8-sig', errors='strict'))
        if digest(path) != before:
            raise ClosureError('resolved system module changed during signature verification')
        return {'requested': name, 'path': str(path), 'sha256': before,
                'signature_status': signature.get('status'), 'signature_subject': signature.get('subject')}
    finally:
        kernel.FreeLibrary(handle)


def windows_earlier_dll_presence(name, system_root, windows_directory=None):
    """Check ordinary Windows and legacy System directories without loading files."""
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_.+-]+\.dll', name, re.I):
        raise ClosureError('expected one unambiguous DLL basename')
    root = Path(system_root)
    if not root.is_absolute():
        raise ClosureError('Windows directory must be an absolute path')
    if windows_directory is None and os.name == 'nt':
        import ctypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.GetWindowsDirectoryW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint]
        kernel.GetWindowsDirectoryW.restype = ctypes.c_uint
        def windows_directory():
            buf = ctypes.create_unicode_buffer(32768)
            count = kernel.GetWindowsDirectoryW(buf, len(buf))
            if not count or count >= len(buf):
                raise ClosureError('cannot obtain the actual Windows directory')
            return buf.value
    if windows_directory is not None and os.path.normcase(os.path.normpath(str(root))) != \
            os.path.normcase(os.path.normpath(str(windows_directory()))):
        raise ClosureError('declared Windows directory differs from the actual system directory')
    for directory in (root, *root.parents):
        info = directory.lstat()
        if (not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode) or
                getattr(info, 'st_file_attributes', 0) & 0x400):
            raise ClosureError('Windows directory ancestry is not an ordinary directory')
    present = []
    for directory in (root / 'System', root):
        try:
            info = directory.lstat()
        except FileNotFoundError:
            continue
        if (not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode) or
                getattr(info, 'st_file_attributes', 0) & 0x400):
            raise ClosureError('legacy Windows DLL directory is redirected or not a directory')
        candidate = directory / name
        try:
            candidate.lstat()
        except FileNotFoundError:
            continue
        present.append(str(candidate))
    return present


def resolve_candidate_pe_imports(plan, processes, runtime_dirs, system_root, resolver, pe_reader=None, python_pair=None,
                                 legacy_probe=None):
    """Resolve reachable real PE imports separately for each process context.

    The resolver must return None only when System32 unambiguously has no such
    non-API-set module; all signature, access, loader or ambiguity errors fail.
    `system_imports` records actual requested names and the verified host file.
    This is static import closure, not evidence of arbitrary dynamic loads.
    """
    if (not isinstance(plan, dict) or not isinstance(plan.get('origins'), dict) or
            not isinstance(plan.get('files'), list) or not isinstance(processes, list) or not processes or
            not isinstance(runtime_dirs, list) or not runtime_dirs or not ntpath.isabs(system_root)):
        raise ClosureError('PE closure requires an explicit candidate, seeds, PATH and system root')
    if legacy_probe is None:
        if os.name != 'nt':
            raise ClosureError('actual earlier Windows DLL directories cannot be checked here')
        legacy_probe = lambda name: windows_earlier_dll_presence(name, system_root)
    dirs = set()
    for item in runtime_dirs:
        _safe_relative(item)
        if item.casefold() == 't/python' or item.casefold().startswith('t/python/'):
            raise ClosureError('driver Python must not be added to a test-process PATH')
        if item.casefold() in dirs:
            raise ClosureError('duplicate PE runtime directory')
        dirs.add(item.casefold())
    entries, by_name = {}, {}
    for item in plan['files']:
        if not isinstance(item, dict):
            raise ClosureError('invalid PE candidate entry')
        path, source = _safe_relative(item.get('destination')), _safe_relative(item.get('source'))
        origin = plan['origins'].get(item.get('origin'))
        if (path.casefold() in entries or not isinstance(origin, dict) or not isinstance(origin.get('root'), str) or
                not Path(origin['root']).is_absolute() or not re.fullmatch(r'[0-9a-f]{64}', str(item.get('sha256')))):
            raise ClosureError('duplicate or malformed PE candidate identity')
        entries[path.casefold()] = item
        if PurePosixPath(path).suffix.casefold() == '.dll':
            by_name.setdefault(PurePosixPath(path).name.casefold(), []).append(item)
    if python_pair is not None:
        if (not isinstance(python_pair, dict) or set(python_pair) != {'driver', 'conan'} or
                python_pair['driver'] != 't/python/python312.dll' or
                not isinstance(python_pair['conan'], str) or
                not python_pair['conan'].casefold().startswith('c/') or
                PurePosixPath(python_pair['conan']).name.casefold() != 'python312.dll' or
                any(x.casefold() not in entries for x in python_pair.values())):
            raise ClosureError('invalid exact driver and Conan Python DLL binding')
    reader = pe_reader or _module('native_closure_pe_reader', 'native_pe_closure.py').imports
    chosen, cache, results, legacy_cache, legacy_checks, seen_processes = {}, {}, [], {}, [], set()
    for process in processes:
        if (not isinstance(process, dict) or set(process) != {'executable', 'working_directory', 'modules'} or
                not isinstance(process.get('modules'), list)):
            raise ClosureError('PE process needs an executable, working directory and exact module seeds')
        exe = _safe_relative(process['executable'])
        cwd = process['working_directory']
        if cwd != '.':
            cwd = _safe_relative(cwd)
        process_key = (exe.casefold(), cwd.casefold())
        if PurePosixPath(exe).suffix.casefold() != '.exe' or process_key in seen_processes:
            raise ClosureError('PE process executable and working directory must be unique and explicit')
        seen_processes.add(process_key)
        app_dir = str(PurePosixPath(exe).parent).casefold()
        visible_dirs = dirs | {app_dir, cwd.casefold()}
        local, queue = {}, []
        for path in [exe, *process['modules']]:
            _safe_relative(path)
            item = entries.get(path.casefold())
            if (not item or item['destination'] != path or path.casefold() in local or
                    PurePosixPath(path).suffix.casefold() not in {'.exe', '.dll', '.pyd'}):
                raise ClosureError('PE process seed is missing, duplicated or not an image: ' + path)
            local[path.casefold()] = item; chosen[path.casefold()] = item; queue.append(path.casefold())
        seeded_names = {}
        for item in local.values():
            path = PurePosixPath(item['destination'])
            if path.suffix.casefold() != '.dll':
                continue
            old = seeded_names.setdefault(path.name.casefold(), item['sha256'])
            if old != item['sha256']:
                raise ClosureError('explicit modules have different bytes under one DLL name in ' + exe)
        if (exe == 't/python/python.exe' and python_pair and any(
                PurePosixPath(x).name.casefold() == 'python312.dll' and x != python_pair['driver']
                for x in process['modules'])):
            raise ClosureError('driver process cannot pre-load another Python runtime DLL')
        if exe == 't/python/python.exe' and python_pair:
            driver_entry = local[exe.casefold()]
            driver_file = _real_file(Path(plan['origins'][driver_entry['origin']]['root']).joinpath(*driver_entry['source'].split('/')))
            if digest(driver_file) != driver_entry['sha256']:
                raise ClosureError('driver Python bytes changed before import analysis')
            try:
                driver_imports = reader(driver_file, require_x64=True)
            except Exception as exc:
                raise ClosureError('cannot parse driver Python executable imports') from exc
            if ('python312.dll' not in {x.casefold() for x in driver_imports.get('normal', [])}):
                raise ClosureError('driver Python does not directly import its own Python 3.12 DLL')
        while queue:
            item = local[queue.pop()]
            target = PurePosixPath(item['destination'])
            origin = plan['origins'][item['origin']]['root']
            binary = _real_file(Path(origin).joinpath(*item['source'].split('/')))
            if digest(binary) != item['sha256']:
                raise ClosureError('reachable PE bytes differ from the candidate: ' + str(target))
            try:
                imports = reader(binary, require_x64=True)
            except Exception as exc:
                raise ClosureError('cannot parse reachable AMD64 PE ' + str(target) + ': ' + str(exc)) from exc
            if not isinstance(imports, dict) or any(not isinstance(imports.get(k), list) for k in ('normal', 'delay')):
                raise ClosureError('invalid PE import inventory')
            for kind in ('normal', 'delay'):
                for name in imports[kind]:
                    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_.+-]+\.dll', name, re.I):
                        raise ClosureError('PE import is not an exact DLL basename')
                    key = name.casefold()
                    if key not in cache:
                        resolved = resolver(name)
                        if resolved is not None:
                            verify_host_system_resolution([name], system_root, lambda _: resolved)
                        elif key.startswith(('api-', 'ext-')):
                            raise ClosureError('Windows API-set contract could not be resolved: ' + name)
                        cache[key] = resolved
                    resolved = cache[key]
                    if resolved is not None:
                        if key in by_name:
                            raise ClosureError('host import collides with a bundled DLL basename: ' + name)
                        results.append({'process': exe, 'importer': str(target), 'kind': kind, 'requested': name,
                                        'resolved_path': resolved['path'], 'sha256': resolved['sha256'],
                                        'signature_status': resolved['signature_status'],
                                        'signature_subject': resolved['signature_subject']})
                        continue
                    providers = [x for x in by_name.get(key, []) if
                                 str(PurePosixPath(x['destination']).parent).casefold() in visible_dirs or
                                 x['destination'].casefold() in local]
                    if not providers:
                        raise ClosureError('unresolved selected ' + kind + ' PE import ' + name + ' in ' + str(target))
                    # After the application directory and System32, Windows
                    # searches the legacy System and Windows directories before
                    # the working directory and PATH. Never silently choose a
                    # bundled PATH provider if either earlier location exists.
                    if not any(str(PurePosixPath(x['destination']).parent).casefold() == app_dir for x in providers):
                        if key not in legacy_cache:
                            try:
                                found = legacy_probe(name)
                            except OSError as exc:
                                raise ClosureError('cannot check earlier Windows DLL directories: ' + name) from exc
                            if not isinstance(found, list) or any(not isinstance(path, str) or not path for path in found):
                                raise ClosureError('earlier Windows DLL directory check is invalid: ' + name)
                            legacy_cache[key] = found
                        if legacy_cache[key]:
                            raise ClosureError('earlier Windows directory shadows the bundled DLL: ' + name)
                        legacy_checks.append({'process': exe, 'importer': str(target), 'kind': kind, 'requested': name,
                                              'checked_dirs': [ntpath.join(system_root, 'System'), ntpath.normpath(system_root)],
                                              'result': 'absent'})
                    if len({x['sha256'] for x in providers}) != 1:
                        # The driver interpreter's own verified image directory
                        # precedes PATH. Only this exact pair is eligible; the
                        # caller must independently derive it from the official
                        # Python and locked Conan package evidence.
                        paths = {x['destination'].casefold() for x in providers}
                        pair = {x.casefold() for x in python_pair.values()} if python_pair else set()
                        if (exe != 't/python/python.exe' or key != 'python312.dll' or paths != pair or
                                app_dir != 't/python'):
                            raise ClosureError('different visible PE providers share the same DLL name in ' + exe + ': ' + name)
                        providers = [x for x in providers if x['destination'] == python_pair['driver']]
                    for provider in providers:
                        provider_key = provider['destination'].casefold()
                        chosen[provider_key] = provider
                        if provider_key not in local:
                            local[provider_key] = provider; queue.append(provider_key)
    results.sort(key=lambda x: (x['process'].casefold(), x['importer'].casefold(), x['kind'], x['requested'].casefold()))
    legacy_checks.sort(key=lambda x: (x['process'].casefold(), x['importer'].casefold(), x['kind'], x['requested'].casefold()))
    return {'schema': 1, 'scope': 'reachable static normal/delay PE imports; not dynamic-load observation',
            'plan': {'origins': plan['origins'], 'files': [chosen[x] for x in sorted(chosen)]},
            'system_imports': results, 'legacy_checks': legacy_checks}


def derive_verified_python_pair(root, manifest_files, source_sha, source_tree, logical_root):
    """Identify the exact embedded driver and same-root locked Conan DLL pair.

    This binds bytes, the host graph and configured package/bin paths. It does
    not by itself establish an embedded interpreter's stdlib or observed loads.
    """
    root = Path(root)
    verify_conan_graph(root, manifest_files, source_sha, source_tree, logical_root)
    files = {x['path'].casefold(): x for x in manifest_files}
    def bound(relative):
        row = files.get(relative.casefold())
        if not row or row.get('path') != relative:
            raise ClosureError('Python DLL identity is not manifest-bound: ' + relative)
        path = _real_file(root.joinpath(*_safe_relative(relative).split('/')))
        if digest(path) != row.get('sha256'):
            raise ClosureError('Python DLL identity changed: ' + relative)
        return path
    graph = _strict_json_file(bound('b/conan-install-graph.json'))
    lock = _strict_json_file(bound('s/conan.lock'))
    pins = _strict_json_file(bound('s/.github/windows-native-kit/tool-pins.json'))
    node = locked_cpython_host_node(graph, lock, pins)
    try:
        folder = audit.to_relative(node['package_folder'], logical_root)
    except (audit.AuditError, KeyError, TypeError) as exc:
        raise ClosureError('locked CPython package is outside the same root') from exc
    _safe_relative(folder)
    values = bound('b/pj_python_bin_dirs.txt').read_text(encoding='utf-8').splitlines()
    expected = [ntpath.join(logical_root, *folder.split('/'), 'bin'), ntpath.join(logical_root, *folder.split('/'))]
    if (len(values) != 2 or any(ntpath.normcase(ntpath.normpath(actual)) != ntpath.normcase(ntpath.normpath(wanted))
                                for actual, wanted in zip(values, expected))):
        raise ClosureError('configured CPython runtime directories differ from the locked package')
    dlls = [row['path'] for row in manifest_files if row['path'].casefold().startswith(folder.casefold() + '/') and
            PurePosixPath(row['path']).name.casefold() == 'python312.dll']
    if len(dlls) != 1:
        raise ClosureError('locked CPython python312.dll is missing or ambiguous')
    bound(dlls[0]); bound('t/python/python312.dll'); bound('t/python/python.exe')
    return {'driver': 't/python/python312.dll', 'conan': dlls[0]}


def derive_pe_processes(suites, prepared, discoveries, inventory, manifest_files, logical_root):
    """Build per-image/working-directory seeds from real reviewed selection."""
    if not isinstance(suites, list) or not isinstance(prepared, dict) or not isinstance(discoveries, dict):
        raise ClosureError('PE process derivation requires actual suites and discovery')
    if not isinstance(inventory, dict) or not isinstance(inventory.get('scopes'), list):
        raise ClosureError('PE process derivation requires source-reviewed dynamic scopes')
    files = {row['path'].casefold(): row['path'] for row in manifest_files}
    groups = {}
    def add(exe, cwd, modules):
        _safe_relative(exe)
        if cwd != '.': _safe_relative(cwd)
        if exe.casefold() not in files or files[exe.casefold()] != exe:
            raise ClosureError('PE process executable is not an exact staged file: ' + exe)
        key = (exe.casefold(), cwd.casefold())
        value = groups.setdefault(key, {'executable': exe, 'working_directory': cwd, 'modules': set()})
        for item in modules:
            if not isinstance(item, dict) or not isinstance(item.get('path'), str):
                raise ClosureError('invalid reviewed dynamic PE module')
            path = item['path']
            if PurePosixPath(path).suffix.casefold() not in {'.dll', '.pyd'}:
                continue
            if path.casefold() not in files or files[path.casefold()] != path:
                raise ClosureError('reviewed dynamic PE module is absent from the stage: ' + path)
            value['modules'].add(path)
    add('t/python/python.exe', '.', [{'path': x} for x in files.values()
                                    if x.startswith('t/python/') and x.casefold().endswith('.pyd')])
    for executable in ('t/cmake/bin/cmake.exe', 't/cmake/bin/ctest.exe', 't/7z/7za.exe',
                       'b/ci-temp-probe/RelWithDebInfo/pj_native_ci_temp_probe.exe',
                       'i/temp-probe/RelWithDebInfo/pj_native_temp_probe.exe'):
        add(executable, '.', [])
    scope_map = {}
    for scope in inventory['scopes']:
        if (not isinstance(scope, dict) or not isinstance(scope.get('suite'), str) or
                not isinstance(scope.get('cases'), list) or not isinstance(scope.get('dynamic_files'), list) or
                not isinstance(scope.get('subprocesses'), list)):
            raise ClosureError('invalid source-reviewed dynamic process scope')
        if scope['subprocesses']:
            raise ClosureError('child process needs an exact source-reviewed working-directory contract')
        for case in scope['cases']:
            key = (scope['suite'], case)
            if key in scope_map:
                raise ClosureError('duplicate dynamic PE case scope')
            scope_map[key] = scope
    expected = set()
    for suite in suites:
        name = suite.get('id') if isinstance(suite, dict) else None
        if name not in prepared or name not in discoveries:
            raise ClosureError('PE process suite is missing its selected discovery')
        try:
            index = review.indexed(discoveries[name])
        except review.ReviewError as exc:
            raise ClosureError('invalid PE process discovery: ' + str(exc)) from exc
        for case in prepared[name]['selected']:
            key = (name, case); expected.add(key)
            if key not in scope_map or case not in index:
                raise ClosureError('selected PE case is not in an exact reviewed dynamic scope')
            test, props = index[case]
            cmd, cwd = test.get('command'), props.get('WORKING_DIRECTORY')
            if not isinstance(cmd, list) or not cmd or not isinstance(cmd[0], str) or not isinstance(cwd, str):
                raise ClosureError('selected PE case lacks its command or working directory')
            try:
                executable, working = audit.to_relative(cmd[0], logical_root), audit.to_relative(cwd, logical_root)
            except audit.AuditError as exc:
                raise ClosureError('selected PE process or working directory leaves the root') from exc
            scope = scope_map[key]
            if scope.get('runner', {}).get('path', '').casefold() != executable.casefold():
                raise ClosureError('selected PE process differs from the source-reviewed runner')
            add(files.get(executable.casefold(), executable), working, scope['dynamic_files'])
    if set(scope_map) != expected:
        raise ClosureError('dynamic PE scopes do not exactly cover selected CTest cases')
    return [{'executable': v['executable'], 'working_directory': v['working_directory'],
             'modules': sorted(v['modules'], key=str.casefold)} for _, v in sorted(groups.items())]


def verify_conan_graph(root, manifest_files, source_sha, source_tree, logical_root):
    """Independently bind every staged host package to graph/lock and notices.

    Conan's manifest uses MD5; SHA-256 binds the staged bytes independently.
    This verifies graph and packaged contents, not the remote transport or
    reproducibility of binaries. Those remain separate producer evidence.
    """
    root = Path(root)
    files = {}
    for row in manifest_files:
        if not isinstance(row, dict):
            raise ClosureError('invalid Conan stage file record')
        path = row.get('path', row.get('destination'))
        _safe_relative(path)
        sha = row.get('sha256')
        if path.casefold() in files or not re.fullmatch(r'[0-9a-f]{64}', str(sha)):
            raise ClosureError('duplicate Conan stage file or invalid SHA-256')
        files[path.casefold()] = {'path': path, 'sha256': sha}
    def staged(path):
        row = files.get(path.casefold())
        if not row or row['path'] != path:
            raise ClosureError('Conan evidence is not staged: ' + path)
        actual = _real_file(root.joinpath(*path.split('/')))
        if digest(actual) != row['sha256']:
            raise ClosureError('Conan staged bytes differ: ' + path)
        return actual
    graph_path = staged('b/conan-install-graph.json')
    identity_path = staged('b/native-kit/conan-runtime-identity.json')
    lock_path = staged('s/conan.lock')
    graph = json.loads(graph_path.read_text(encoding='utf-8'))
    identity = json.loads(identity_path.read_text(encoding='utf-8'))
    lock = json.loads(lock_path.read_text(encoding='utf-8'))
    nodes = graph.get('graph', {}).get('nodes') if isinstance(graph, dict) else None
    requires = lock.get('requires') if isinstance(lock, dict) else None
    packages = identity.get('packages') if isinstance(identity, dict) else None
    if (not isinstance(nodes, dict) or not isinstance(requires, list) or
            any(not isinstance(x, str) for x in requires) or not isinstance(packages, list) or
            identity.get('schema') != 1 or identity.get('source_sha') != source_sha or
            identity.get('source_tree') != source_tree or identity.get('graph_sha256') != digest(graph_path)):
        raise ClosureError('Conan graph, lock or identity metadata is malformed')
    locked = {x.split('%', 1)[0] for x in requires}
    by_folder = {}
    for item in packages:
        if not isinstance(item, dict) or not isinstance(item.get('package_folder'), str):
            raise ClosureError('invalid Conan package identity')
        key = item['package_folder'].casefold()
        if key in by_folder:
            raise ClosureError('duplicate Conan package identity')
        by_folder[key] = item
    if not by_folder:
        raise ClosureError('Conan host package identity is empty')
    claimed = set()
    for node_id, node in nodes.items():
        if not isinstance(node, dict) or node.get('context') != 'host' or str(node_id) == '0':
            continue
        if not isinstance(node.get('package_folder'), str):
            raise ClosureError('Conan host package has no actual package folder: ' + str(node_id))
        try:
            folder = audit.to_relative(node['package_folder'], logical_root)
        except audit.AuditError as exc:
            raise ClosureError('Conan package leaves the fixed root') from exc
        _safe_relative(folder)
        if not folder.casefold().startswith('c/') or folder.casefold() in claimed:
            raise ClosureError('invalid or duplicate Conan host package folder')
        record = by_folder.get(folder.casefold())
        ref = node.get('ref')
        canonical_ref = ref.split('%', 1)[0] if isinstance(ref, str) else ''
        match = re.fullmatch(r'[^#\r\n]+#([0-9a-f]{32})', canonical_ref)
        if (not match or canonical_ref not in locked or
                (node.get('rrev') is not None and node['rrev'] != match.group(1)) or
                not re.fullmatch(r'[0-9a-f]{40}', str(node.get('package_id'))) or
                not re.fullmatch(r'[0-9a-f]{32}', str(node.get('prev'))) or not record or
                any(record.get(k) != value for k, value in {'ref': ref, 'rrev': match.group(1),
                    'package_id': node['package_id'], 'prev': node['prev'], 'package_folder': folder}.items())):
            raise ClosureError('Conan package identity differs from graph or locked recipe: ' + folder)
        manifest_path = staged(folder + '/conanmanifest.txt')
        if record.get('manifest_sha256') != digest(manifest_path):
            raise ClosureError('Conan package manifest digest differs: ' + folder)
        lines = manifest_path.read_text(encoding='utf-8').splitlines()
        if not lines or not re.fullmatch(r'\d+', lines[0]):
            raise ClosureError('malformed Conan package manifest timestamp')
        hashes = {}
        for line in lines[1:]:
            name, sep, value = line.rpartition(': ')
            _safe_relative(name)
            if not sep or not re.fullmatch(r'[0-9a-f]{32}', value) or name.casefold() in hashes:
                raise ClosureError('malformed or case-colliding Conan package manifest entry')
            hashes[name.casefold()] = (name, value)
        selected = [x for x in files.values() if x['path'].casefold().startswith(folder.casefold() + '/')]
        licenses = {x['path'][len(folder)+1:] for x in selected if x['path'][len(folder)+1:].casefold().startswith('licenses/')}
        original_licenses = {name for name, _ in hashes.values() if name.casefold().startswith('licenses/')}
        if not original_licenses or licenses != original_licenses:
            raise ClosureError('original Conan license files are missing or incomplete: ' + folder)
        for row in selected:
            name = row['path'][len(folder)+1:]
            if name == 'conanmanifest.txt':
                continue
            stored = hashes.get(name.casefold())
            if not stored or stored[0] != name:
                raise ClosureError('staged Conan file absent from original package manifest: ' + name)
            content = staged(row['path'])
            md5 = hashlib.md5(usedforsecurity=False)
            with content.open('rb') as stream:
                for part in iter(lambda: stream.read(1024 * 1024), b''):
                    md5.update(part)
            if md5.hexdigest() != stored[1]:
                raise ClosureError('staged Conan file differs from original package manifest: ' + name)
        claimed.add(folder.casefold())
    if claimed != set(by_folder):
        raise ClosureError('Conan identity includes a package outside the actual host graph')
    for row in files.values():
        value = row['path'].casefold()
        if value.startswith('c/') and not any(value.startswith(folder + '/') for folder in claimed):
            raise ClosureError('staged Conan file has no exact host-graph package: ' + row['path'])
    return {'host_packages': len(claimed), 'graph_sha256': digest(graph_path),
            'scope': 'host graph and staged package bytes; remote provenance checked separately'}


def verify_conan_process_records(root, manifest_files, source_sha, source_tree, logical_root):
    """Check raw producer Conan records, not tool provenance or reproducibility.

    The producer records an executable hash but the build-only venv is not in
    the kit. Therefore these records alone cannot independently authenticate
    the Conan executable or prove a remote actually supplied particular bytes.
    The graph, lock and original package manifests are checked separately.
    """
    root = Path(root)
    files = {}
    for row in manifest_files:
        if not isinstance(row, dict):
            raise ClosureError('invalid Conan process manifest entry')
        relative, sha = row.get('path'), row.get('sha256')
        _safe_relative(relative)
        if relative.casefold() in files or not re.fullmatch(r'[0-9a-f]{64}', str(sha)):
            raise ClosureError('duplicate Conan process file or invalid hash')
        files[relative.casefold()] = row
    def bound(relative):
        row = files.get(relative.casefold())
        if not row or row['path'] != relative:
            raise ClosureError('required Conan producer evidence is not manifest-bound: ' + relative)
        path = _real_file(root.joinpath(*relative.split('/')))
        if digest(path) != row['sha256']:
            raise ClosureError('Conan producer evidence bytes changed: ' + relative)
        return path
    def win(relative):
        return ntpath.join(logical_root, *relative.split('/'))
    def same_path(left, right):
        return isinstance(left, str) and ntpath.normcase(ntpath.normpath(left)) == ntpath.normcase(ntpath.normpath(right))
    lock_sha = digest(bound('s/conan.lock'))
    graph_sha = digest(bound('b/conan-install-graph.json'))
    directory = 'b/native-kit/conan-evidence/'
    conan_sha, records = None, {}
    for phase in ('remotes', 'install'):
        record = _strict_json_file(bound(directory + phase + '.process.json'))
        stdout = bound(directory + phase + '.stdout.bin')
        stderr = bound(directory + phase + '.stderr.bin')
        if (not isinstance(record, dict) or record.get('exit_code') != 0 or
                type(record.get('exit_code')) is not int or record.get('source_sha') != source_sha or
                record.get('source_tree') != source_tree or record.get('lock_sha256') != lock_sha or
                record.get('stdout_sha256') != digest(stdout) or record.get('stderr_sha256') != digest(stderr) or
                not re.fullmatch(r'[0-9a-f]{64}', str(record.get('conan_sha256'))) or
                not same_path(record.get('cwd'), win('s'))):
            raise ClosureError('Conan ' + phase + ' raw process identity or result differs')
        if conan_sha is not None and conan_sha != record['conan_sha256']:
            raise ClosureError('Conan process executable identity changed')
        conan_sha = record['conan_sha256']
        argv = record.get('argv')
        if (not isinstance(argv, list) or not argv or any(not isinstance(x, str) for x in argv) or
                not same_path(argv[0], win('t/builder/Scripts/conan.exe'))):
            raise ClosureError('Conan producer command does not name the expected executable')
        if phase == 'remotes':
            if argv[1:] != ['remote', 'list', '--format=json']:
                raise ClosureError('Conan remote-list command differs')
            remotes = _strict_json_file(stdout)
            expected = {'conancenter': 'https://center2.conan.io',
                        'plotjuggler-conan': 'https://plotjuggler.jfrog.io/artifactory/api/conan/plotjuggler-conan'}
            if not isinstance(remotes, list) or len(remotes) != len(expected):
                raise ClosureError('Conan public remote list is incomplete or contains extras')
            names = set()
            for remote in remotes:
                if (not isinstance(remote, dict) or remote.get('name') not in expected or
                        remote['name'] in names or remote.get('url') != expected[remote['name']] or
                        remote.get('enabled') is not True or remote.get('verify_ssl') is not True or
                        remote.get('force_auth') is not False or remote.get('allowed_packages') is not None or
                        remote.get('recipes_only') is not False):
                    raise ClosureError('Conan public remote settings differ from the reviewed sources')
                names.add(remote['name'])
        else:
            if record.get('graph_sha256') != graph_sha:
                raise ClosureError('Conan install process did not bind the staged graph')
            expected = ['install', win('s'), '--output-folder=' + win('b'), '--build=missing',
                        '-r=plotjuggler-conan', '-r=conancenter', '--lockfile=' + win('s/conan.lock'),
                        '--lockfile-partial', '-s', 'build_type=RelWithDebInfo', '-s', 'compiler.cppstd=20',
                        '-c', 'tools.build:jobs=2', '-o', 'cpython/*:shared=True', '-s',
                        'cpython/*:build_type=Release', '-s', 'compiler.version=194', '-c',
                        'tools.cmake.cmaketoolchain:generator=Ninja Multi-Config', '--format=json',
                        '--out-file=' + win('b/conan-install-graph.json')]
            # Exact option order and values prevent a self-filled summary from
            # widening remotes, build type, lock, or output destinations.
            if len(argv[1:]) != len(expected):
                raise ClosureError('Conan install command length differs from the source-reviewed command')
            path_positions = {1, 2, 6, len(expected) - 1}
            for i, (actual, wanted) in enumerate(zip(argv[1:], expected)):
                if i in path_positions:
                    prefix = wanted.partition('=')[0] + '=' if '=' in wanted else ''
                    if not actual.startswith(prefix) or not same_path(actual[len(prefix):], wanted[len(prefix):]):
                        raise ClosureError('Conan install command path differs')
                elif actual != wanted:
                    raise ClosureError('Conan install command option differs')
        records[phase] = {'stdout_sha256': digest(stdout), 'stderr_sha256': digest(stderr)}
    return {'scope': 'manifest-bound producer Conan process records; tool distribution not independently authenticated',
            'conan_sha256': conan_sha, 'lock_sha256': lock_sha, 'graph_sha256': graph_sha, 'records': records}


def verify_cmake_build_records(root, manifest_files, source_sha, source_tree, logical_root, qt_version, selected):
    """Check raw initial configure/build records and exact fixed query bytes."""
    root = Path(root)
    files = {x['path'].casefold(): x for x in manifest_files}
    def bound(relative):
        row = files.get(relative.casefold())
        if not row or row.get('path') != relative:
            raise ClosureError('required CMake producer record is not manifest-bound: ' + relative)
        path = _real_file(root.joinpath(*_safe_relative(relative).split('/')))
        if digest(path) != row.get('sha256'):
            raise ClosureError('CMake producer record changed: ' + relative)
        return path
    def win(relative): return ntpath.join(logical_root, *relative.split('/'))
    def same(a, b): return isinstance(a, str) and ntpath.normcase(ntpath.normpath(a)) == ntpath.normcase(ntpath.normpath(b))
    query = bound('b/native-kit/codemodel/query/codemodel-v2')
    if query.stat().st_size:
        raise ClosureError('the retained CMake codemodel-v2 query is not the exact empty query')
    lock = digest(bound('s/conan.lock'))
    cmake = digest(bound('t/cmake/bin/cmake.exe'))
    extractor = digest(bound('t/7z/7za.exe'))
    csv = _strict_json_file(bound('b/native-kit/csv-prebuilt.json'))
    plugin = csv.get('plugin') if isinstance(csv, dict) else None
    if not isinstance(plugin, str):
        raise ClosureError('CMake build input lacks the exact prebuilt CSV plugin path')
    expected = {
        'configure': [win('t/cmake/bin/cmake.exe'), '-S', win('s'), '-B', win('b'),
            '-DCMAKE_TOOLCHAIN_FILE=' + win('b/conan_toolchain.cmake'), '-DPJ_BUILD_TESTS=ON', '-DPJ_BUILD_DEMOS=OFF',
            '-DPJ_PLUGIN_FEEDBACK_ACCEPTANCE=ON', '-DPJ_CSV_RUNTIME_PLUGIN=' + plugin, '-G', 'Ninja Multi-Config',
            '-DCMAKE_PREFIX_PATH=' + win('q/' + qt_version + '/msvc2022_64'), '-DCMAKE_MAKE_PROGRAM=' + win('t/builder/Scripts/ninja.exe'),
            '-DPython3_EXECUTABLE=' + win('t/python/python.exe'), '-DPJ_TEST_PYTHON=' + win('t/python/python.exe'),
            '-DPJ_IFW_TEST_ARCHIVE=' + win('t/ifw/ifw.7z'), '-DPJ_IFW_TEST_EXTRACTOR=' + win('t/7z/7za.exe'),
            '-DPJ_IFW_TEST_EXTRACTOR_SHA256=' + extractor, '-DPJ_NATIVE_BUNDLE_MODE=ON', '-DCMAKE_BUILD_TYPE=RelWithDebInfo',
            '-DCMAKE_POLICY_DEFAULT_CMP0141=NEW', '-DCMAKE_MSVC_DEBUG_INFORMATION_FORMAT=Embedded'],
        'build': [win('t/cmake/bin/cmake.exe'), '--build', win('b'), '--config', 'RelWithDebInfo', '--parallel', '2'],
    }
    base = 'b/native-kit/codemodel/process/'
    ninja = None; build_log = ''
    for phase in ('configure', 'build'):
        record = _strict_json_file(bound(base + phase + '.process.json'))
        stdout, stderr = bound(base + phase + '.stdout.bin'), bound(base + phase + '.stderr.bin')
        if (not isinstance(record, dict) or record.get('schema') != 1 or record.get('source_sha') != source_sha or
                record.get('source_tree') != source_tree or record.get('exit_code') != 0 or
                type(record.get('exit_code')) is not int or record.get('still_running') is not False or
                not same(record.get('cwd'), logical_root) or record.get('lock_sha256') != lock or
                record.get('cmake_sha256') != cmake or not re.fullmatch(r'[0-9a-f]{64}', str(record.get('ninja_sha256'))) or
                record.get('stdout_sha256') != digest(stdout) or record.get('stderr_sha256') != digest(stderr)):
            raise ClosureError('CMake ' + phase + ' process or raw output identity differs')
        if ninja is not None and ninja != record['ninja_sha256']:
            raise ClosureError('configured Ninja executable changed during the build')
        ninja = record['ninja_sha256']
        argv = record.get('argv')
        if not isinstance(argv, list) or len(argv) != len(expected[phase]):
            raise ClosureError('CMake ' + phase + ' command length differs')
        for actual, wanted in zip(argv, expected[phase]):
            # CMake option prefixes are exact; Windows path values are case
            # insensitive and may use either native separator.
            if isinstance(wanted, str) and ('=' in wanted and ntpath.isabs(wanted.partition('=')[2])):
                prefix, _, path = wanted.partition('=')
                if not isinstance(actual, str) or not actual.startswith(prefix + '=') or not same(actual[len(prefix)+1:], path):
                    raise ClosureError('CMake ' + phase + ' command path differs')
            elif ntpath.isabs(wanted):
                if not same(actual, wanted): raise ClosureError('CMake ' + phase + ' command path differs')
            elif actual != wanted:
                raise ClosureError('CMake ' + phase + ' command option differs')
        if phase == 'build':
            build_log = stdout.read_text(encoding='utf-8', errors='replace') + '\n' + stderr.read_text(encoding='utf-8', errors='replace')
    for case, cpp, exe in (('RuntimeCatalogLanguageTest', 'runtime_catalog_language_test.cpp', 'runtime_catalog_language_test.exe'),
                           ('extension_manager_test', 'extension_manager_test.cpp', 'extension_manager_test.exe')):
        if ('main', case) in selected and (cpp.casefold() not in build_log.casefold() or exe.casefold() not in build_log.casefold()):
            raise ClosureError('actual build log does not show the selected source and linked runner: ' + case)
    return {'scope': 'manifest-bound raw producer configure/build and retained query', 'cmake_sha256': cmake,
            'ninja_sha256': ninja, 'query_sha256': digest(query)}


REQUIRED_EVIDENCE_KINDS = frozenset({
    'qt-origin-extraction', 'conan-origin-license', 'host-system-resolution',
    'dynamic-dependency-inventory', 'case-source-review', 'private-registry-lifecycle',
    'ci-temp-safety', 'linked-marker-mutation', 'bootstrap-adversarial', 'candidate-input',
})


def check_staged_receipt_integrity(root, manifest, receipt, source_sha, source_tree):
    """Check receipt/control/evidence identities against a verified manifest.

    This only validates bytes and coverage labels. It does not interpret the raw
    Qt, Conan, host, lifecycle or execution evidence and cannot authorize a run.
    The caller must verify the manifest against an independent digest first and
    independently replay every evidence-specific check afterwards.
    """
    root = Path(root)
    if not isinstance(manifest, dict) or not isinstance(manifest.get('files'), list) or not isinstance(receipt, dict):
        raise ClosureError('invalid staged receipt or manifest')
    files = {}
    for row in manifest['files']:
        if not isinstance(row, dict) or not isinstance(row.get('path'), str) or not re.fullmatch(r'[0-9a-f]{64}', str(row.get('sha256'))):
            raise ClosureError('invalid staged manifest file')
        key = row['path'].casefold()
        if key in files:
            raise ClosureError('staged manifest has case-colliding files')
        files[key] = row
    def checked(relative):
        _safe_relative(relative)
        row = files.get(relative.casefold())
        if row is None or row['path'] != relative:
            raise ClosureError('required evidence is not an exact manifest file: ' + relative)
        path = _real_file(root.joinpath(*relative.split('/')))
        if not path.stat().st_size or digest(path) != row['sha256']:
            raise ClosureError('manifest-bound evidence is empty or changed: ' + relative)
        return row['sha256']
    policy_path = 's/.github/windows-native-kit/ci-closure-policy.json'
    verifier_path = 's/scripts/windows/verify_native_ci_closure.py'
    control = 'b/native-kit/closure-evidence/'
    for rel in (policy_path, verifier_path, control + 'receipt.json', control + 'ci-policy.json', control + 'provenance.json'):
        checked(rel)
    expected = {'schema': 1, 'source_sha': source_sha, 'source_tree': source_tree,
                'configuration': 'RelWithDebInfo', 'reviewed_policy_sha256': checked(policy_path),
                'verifier_sha256': checked(verifier_path)}
    if any(receipt.get(k) != v for k, v in expected.items()):
        raise ClosureError('receipt source, policy or verifier identity differs')
    try:
        recorded_receipt = json.loads((root / control / 'receipt.json').read_text(encoding='utf-8'))
    except (ValueError, UnicodeError) as exc:
        raise ClosureError('retained receipt is not valid JSON') from exc
    if recorded_receipt != receipt:
        raise ClosureError('supplied receipt differs from manifest-bound receipt bytes')
    for field, path in (('candidate_plan_sha256', control + 'candidate-plan.json'),
                        ('candidate_report_sha256', control + 'candidate-report.json')):
        if receipt.get(field) != checked(path):
            raise ClosureError('receipt is not bound to the retained candidate input: ' + field)
    evidence = receipt.get('evidence')
    if not isinstance(evidence, list) or not evidence:
        raise ClosureError('receipt contains no raw evidence')
    seen, kinds, candidate_inputs = set(), set(), set()
    for item in evidence:
        if (not isinstance(item, dict) or item.get('kind') not in REQUIRED_EVIDENCE_KINDS or
                not isinstance(item.get('path'), str) or not item['path'].startswith(control) or
                not re.fullmatch(r'[0-9a-f]{64}', str(item.get('sha256')))):
            raise ClosureError('invalid staged raw evidence entry')
        relative = item['path']
        if relative.casefold() in seen or relative in (control + 'receipt.json', control + 'ci-policy.json', control + 'provenance.json'):
            raise ClosureError('duplicate or control-file raw evidence')
        if checked(relative) != item['sha256']:
            raise ClosureError('raw evidence hash differs from manifest')
        if item['kind'] == 'candidate-input':
            candidate_inputs.add(relative)
        if item['kind'] == 'case-source-review':
            cases = item.get('cases')
            if (not isinstance(cases, list) or not cases or any(not isinstance(x, dict) or
                    set(x) != {'suite', 'case'} or not all(isinstance(v, str) and v for v in x.values()) for x in cases)):
                raise ClosureError('source-review evidence needs exact suite/case bindings')
        seen.add(relative.casefold()); kinds.add(item['kind'])
    if candidate_inputs != {control + 'candidate-plan.json', control + 'candidate-report.json'}:
        raise ClosureError('receipt must retain exactly both candidate input files')
    if kinds != REQUIRED_EVIDENCE_KINDS:
        raise ClosureError('raw evidence kinds are incomplete')
    return {'source_sha': source_sha, 'source_tree': source_tree, 'evidence_files': len(seen),
            'scope': 'manifest-bound-bytes-only; evidence-specific replay still required'}

def verify_hosted_preflights(root, source_sha, source_tree, logical_root, qt_version):
    """Recheck actual producer raw controls; never certify the target VM."""
    root = Path(root)
    def file(relative):
        _safe_relative(relative)
        return _real_file(root.joinpath(*relative.split('/')))
    def document(relative):
        return json.loads(file(relative).read_text(encoding='utf-8'))
    def windows_equal(value, expected):
        return isinstance(value, str) and ntpath.normcase(ntpath.normpath(value)) == ntpath.normcase(ntpath.normpath(expected))
    def winpath(relative):
        return ntpath.join(logical_root, *relative.split('/'))
    def raw_hash(record, key, relative):
        if record.get(key + '_sha256') != digest(file(relative)):
            raise ClosureError('producer raw stream differs: ' + relative)
    bootstrap = 'b/native-kit/bootstrap-selftest-evidence/'
    process = document(bootstrap + 'process.json')
    expected_bootstrap = {'schema': 1, 'scope': 'disposable-windows-ci-only', 'source_sha': source_sha,
                          'exit_code': 0, 'test_sha256': digest(file('s/tests/test_windows_native_bootstrap.py')),
                          'bootstrap_sha256': digest(file('s/scripts/windows/bootstrap_native_test_kit.ps1'))}
    if (any(process.get(k) != v for k, v in expected_bootstrap.items()) or
            not re.fullmatch(r'[0-9a-f]{40}', str(process.get('synthetic_sha', ''))) or
            process['synthetic_sha'] == source_sha or not isinstance(process.get('argv'), list) or
            process['argv'][1:] != ['-B', '-m', 'unittest', 'discover', '-s', 'tests', '-p',
                                   'test_windows_native_bootstrap.py', '-v']):
        raise ClosureError('bootstrap adversarial process/source identity differs')
    for name in ('stdout', 'stderr'):
        raw_hash(process, name, bootstrap + name + '.bin')
    log = file(bootstrap + 'stderr.bin').read_text(encoding='utf-8', errors='strict')
    for test in ('test_actual_embedded_verifier_rejects_malformed_cases', 'test_full_fixed_root_and_refuse_reuse'):
        if not re.search(r'(?m)^' + test + r'[^\r\n]*\.\.\. ok\r?$', log):
            raise ClosureError('real Windows bootstrap adversarial test did not pass: ' + test)
    origin = document(bootstrap + 'python-origin.process.json')
    if (origin.get('schema') != 1 or origin.get('scope') != 'disposable-windows-ci-only' or
            origin.get('source_sha') != source_sha or origin.get('source_tree') != source_tree or origin.get('exit_code') != 0 or
            origin.get('test_sha256') != digest(file('s/tests/test_windows_native_python_origin.py')) or
            origin.get('python_origin_script_sha256') != digest(file('s/scripts/windows/verify_embedded_python_origin.ps1')) or
            origin.get('synthetic_sha') != process.get('synthetic_sha') or
            origin.get('bootstrap_sha256') != process.get('bootstrap_sha256') or
            not re.fullmatch(r'[0-9a-f]{64}', str(origin.get('executable_sha256'))) or
            not isinstance(origin.get('executable'), str) or
            not windows_equal(origin.get('executable'), process.get('executable')) or
            not isinstance(origin.get('argv'), list) or not origin['argv'] or
            not windows_equal(origin['argv'][0], origin['executable']) or
            origin['argv'][1:] != ['-I', '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-p',
                                   'test_windows_native_python_origin.py', '-v']):
        raise ClosureError('Python-origin adversarial process or source identity differs')
    for name in ('stdout', 'stderr'):
        raw_hash(origin, name, bootstrap + 'python-origin.' + name + '.bin')
    origin_log = file(bootstrap + 'python-origin.stderr.bin').read_text(encoding='utf-8', errors='strict')
    if not re.search(r'(?m)^test_actual_dotnet_compare_accepts_exact_zip_and_rejects_tampering[^\r\n]*\.\.\. ok\r?$', origin_log):
        raise ClosureError('real Windows Python-origin positive and adversarial controls did not pass')
    qtcore = f'q/{qt_version}/msvc2022_64/bin/Qt6Core.dll'
    temp_exe = 'b/ci-temp-probe/RelWithDebInfo/pj_native_ci_temp_probe.exe'
    temp_base = 'b/native-kit/ci-temp-probe-evidence/'
    previous = None
    for phase in ('before-plugin-preflight', 'before-marker-mutation', 'before-main-discovery'):
        record = document(temp_base + phase + '.json')
        for field in ('stdout', 'stderr'):
            raw_hash(record, field, temp_base + phase + '.' + field + '.bin')
        proof = document(temp_base + phase + '.stdout.bin')
        run_root = winpath('ci-discovery'); temp = ntpath.join(run_root, 'tmp')
        expected_argv = ['--run-root', run_root, '--temp', temp, '--qt', qt_version, '--qt-core', winpath(qtcore)]
        if (record.get('schema') != 1 or record.get('phase') != phase or record.get('exit_code') != 0 or
                record.get('argv') != expected_argv or not windows_equal(record.get('cwd'), winpath('s')) or
                not windows_equal(record.get('executable'), winpath(temp_exe)) or
                not windows_equal(record.get('temp'), temp) or not windows_equal(record.get('tmp'), temp) or
                record.get('executable_sha256') != digest(file(temp_exe)) or
                record.get('qt_core_sha256') != digest(file(qtcore)) or
                proof.get('scope') != 'disposable-windows-ci-only' or proof.get('qt_version') != qt_version or
                not windows_equal(proof.get('run_root'), run_root) or not windows_equal(proof.get('qt_temp'), temp) or
                not windows_equal(proof.get('qt_core'), winpath(qtcore)) or type(proof.get('pid')) is not int or proof['pid'] <= 0):
            raise ClosureError('actual producer Qt temporary path or binary identity differs: ' + phase)
        identity = tuple(proof.get(k) for k in ('user_sid', 'session', 'integrity_rid', 'auth_luid', 'elevation_type'))
        if (not isinstance(identity[0], str) or not identity[0].startswith('S-1-') or type(identity[1]) is not int or
                identity[1] < 0 or type(identity[2]) is not int or identity[2] <= 0 or
                not re.fullmatch(r'[0-9a-f]{8}:[0-9a-f]{8}', str(identity[3])) or
                identity[4] not in ('default', 'full', 'limited') or (previous is not None and identity != previous)):
            raise ClosureError('actual producer Qt probe token changed or is incomplete')
        previous = identity
    registry = 'b/native-kit/registry-smoke-evidence/'
    lifecycle = document(registry + 'receipt.json')
    build = document('b/native-kit/registry-smoke-build/producer-identity.json')
    guard = 's/cmake/test_mains/pj_test_windows_registry.h'
    registry_exe = 'b/registry-smoke/RelWithDebInfo/registry_fixture_smoke.exe'
    if (lifecycle.get('schema') != 1 or lifecycle.get('complete') is not True or
            lifecycle.get('exe_sha256') != digest(file(registry_exe)) or
            lifecycle.get('guard_header_sha256') != digest(file(guard)) or
            lifecycle.get('qt_core_sha256') != digest(file(qtcore)) or
            any(build.get(k) != v for k, v in {'schema': 1, 'source_sha': source_sha, 'source_tree': source_tree,
                'configuration': 'RelWithDebInfo', 'executable_sha256': digest(file(registry_exe)),
                'qt_core_sha256': digest(file(qtcore)), 'receipt_sha256': digest(file(registry + 'receipt.json'))}.items())):
        raise ClosureError('private-registry lifecycle source/binary identity differs')
    sources = build.get('source_files')
    if not isinstance(sources, list) or not sources:
        raise ClosureError('private-registry producer source hashes are missing')
    for item in sources:
        if (not isinstance(item, dict) or not isinstance(item.get('path'), str) or
                not item['path'].startswith('scripts/windows/native_registry_smoke/') or
                item.get('sha256') != digest(file('s/' + item['path']))):
            raise ClosureError('private-registry producer source hash differs')
    smoke = _module('native_clean_registry_smoke', 'native_registry_smoke/run_smoke.py')
    normal, injected = lifecycle.get('normal', {}), lifecycle.get('injected', {})
    for phase, result in (('normal', normal), ('injected', injected)):
        stderr = file(registry + phase + '.stderr.bin').read_bytes()
        file(registry + phase + '.stdout.bin')
        try:
            keys = smoke.owned_names(stderr)
        except smoke.SmokeError as exc:
            raise ClosureError('private-registry raw owned identities are incomplete') from exc
        if result.get('owned_keys') != keys or b'Native guard initialized; QApplication-free lifecycle probe.' not in stderr:
            raise ClosureError('private-registry raw output and exact owned identities differ')
        if phase == 'normal':
            if (result.get('exit_code') != 0 or result.get('absent_after') != [True, True] or
                    b'Late QSettings write failed closed; self-owned real sentinel untouched.' not in stderr):
                raise ClosureError('private-registry normal lifecycle did not complete')
        elif (result.get('exit_code') != 1 or result.get('present_before_exact_cleanup') != [True, True] or
              result.get('absent_after_exact_cleanup') != [True, True] or
              b'Injected owned-key cleanup failure: 5' not in stderr):
            raise ClosureError('private-registry injected failure control did not complete')
    mutation_base = 'b/native-kit/marker-mutation-evidence/'
    if (root / mutation_base / 'INCOMPLETE').exists():
        raise ClosureError('linked marker mutation remains incomplete')
    mutation = document(mutation_base + 'receipt.json')
    marker = file('s/pj_runtime/src/ActiveWidgetsMarker.cpp')
    runner = file('b/pj_app/RelWithDebInfo/pj_app_gui_tests.exe')
    module = _module('native_clean_marker_mutation', 'native_marker_mutation.py')
    actual_mutation = hashlib.sha256(module.mutant(marker.read_bytes())).hexdigest()
    if (mutation.get('schema') != 1 or mutation.get('complete') is not True or
            mutation.get('scope') != 'disposable-windows-ci-only' or mutation.get('source_sha') != source_sha or
            mutation.get('source_tree') != source_tree or mutation.get('case') != module.CASE or
            mutation.get('original_source_sha256') != digest(marker) or mutation.get('mutated_source_sha256') != actual_mutation or
            mutation.get('restored_runner_sha256') != digest(runner) or
            mutation.get('qt_preflight_sha256') != digest(file(temp_base + 'before-marker-mutation.stdout.bin')) or
            not re.fullmatch(r'[0-9a-f]{64}', str(mutation.get('baseline_runner_sha256', ''))) or
            not re.fullmatch(r'[0-9a-f]{64}', str(mutation.get('mutant_runner_sha256', ''))) or
            mutation['mutant_runner_sha256'] in (mutation['baseline_runner_sha256'], mutation['restored_runner_sha256'])):
        raise ClosureError('linked marker mutation source or runner identity differs')
    for phase in ('mutant-build', 'mutant-test', 'original-build', 'original-test'):
        record = document(mutation_base + phase + '.process.json')
        for field in ('stdout', 'stderr'):
            raw_hash(record, field, mutation_base + phase + '.' + field + '.bin')
        try:
            module.require_same_ci_identity(record['identity'], mutation['ci_identity'])
            if phase.endswith('build'):
                module.require_incremental_build(record, file(mutation_base + phase + '.stdout.bin').read_bytes() +
                                                 file(mutation_base + phase + '.stderr.bin').read_bytes())
            else:
                module.check_case(file(mutation_base + ('mutant.xml' if phase == 'mutant-test' else 'original.xml')),
                                  record.get('exit_code'), mutated=phase == 'mutant-test')
        except (module.MutationError, ET.ParseError, KeyError, ValueError) as exc:
            raise ClosureError('linked marker actual build or test evidence is invalid: ' + phase) from exc
    return {'scope': 'producer hosted CI controls only; not VM safety',
            'bootstrap_controls': 2, 'qt_temp_probes': 3, 'registry_phases': 2, 'mutation_phases': 4}


def verify_staged_inputs(root, manifest, receipt, policy, source_sha, source_tree, logical_root, proof_dir):
    """Recompute manifest-bound case/Conan/Qt/host inputs on disposable CI.

    This is a subset of staged verification. A caller must additionally replay
    the original producer bootstrap, registry/temp, mutation and real selected
    group evidence. The return value is not an execution authorization.
    """
    root = Path(root).absolute()
    check_staged_receipt_integrity(root, manifest, receipt, source_sha, source_tree)
    files = manifest['files']
    generated = verify_generated_media(root, source_sha, source_tree,
                                       os.environ.get('PJ_MEDIA_MANIFEST_SHA256', ''), files)
    provenance = manifest.get('provenance')
    if (not isinstance(provenance, dict) or provenance.get('generated_fixtures') != generated or
            provenance.get('source_clean_scope') != 'tracked checkout clean; four generated fixture inputs are identified separately'):
        raise ClosureError('staged provenance does not identify the generated source exceptions')
    by_path = {item['path'].casefold(): item for item in files}
    control = root / 'b/native-kit/closure-evidence'
    candidate = json.loads((control / 'candidate-plan.json').read_text(encoding='utf-8'))
    report = json.loads((control / 'candidate-report.json').read_text(encoding='utf-8'))
    ci_policy = json.loads((control / 'ci-policy.json').read_text(encoding='utf-8'))
    if (not isinstance(candidate, dict) or not isinstance(candidate.get('files'), list) or
            not isinstance(report, dict) or any(report.get(k) != value for k, value in {
                'source_sha': source_sha, 'source_tree': source_tree, 'logical_root': logical_root,
                'configuration': 'RelWithDebInfo'}.items())):
        raise ClosureError('retained candidate source or root differs')
    for item in candidate['files']:
        if not isinstance(item, dict) or not isinstance(item.get('destination'), str):
            raise ClosureError('invalid retained candidate file')
        row = by_path.get(item['destination'].casefold())
        if not row or row['path'] != item['destination'] or row['sha256'] != item.get('sha256'):
            raise ClosureError('retained candidate file differs from staged manifest')
    checkout = os.environ.get('GITHUB_WORKSPACE', '')
    if not checkout:
        raise ClosureError('independent CI source checkout is missing')
    source_inventory = verify_independent_checkout(root, checkout, source_sha, source_tree,
        [item['path'] for item in files], files)
    launcher = _module('native_clean_closure_launcher', 'run_native_test_bundle.py')
    driver = _module('native_clean_closure_ci_driver', 'run_native_ci_verification.py')
    plan = json.loads((root / 'b/native-kit/run-plan.json').read_text(encoding='utf-8'))
    _, _, suites = launcher.validate_plan(plan, source_sha, source_tree, 'RelWithDebInfo')
    docs = {suite['id']: json.loads(_real_file(root.joinpath(*suite['full_discovery'].split('/'))).read_text(encoding='utf-8'))
            for suite in suites}
    derived = derive_partition(policy, docs, source_sha, source_tree, logical_root,
                               [x['destination'] for x in candidate['files']], report.get('coverage'))
    if derived != ci_policy:
        raise ClosureError('clean CI partition differs from source-reviewed discovery')
    try:
        decisions = driver.validate_policy(ci_policy, docs, source_sha, source_tree, 'RelWithDebInfo', manifest)
        selected_docs = {suite['id']: json.loads(_real_file(root.joinpath(*suite['discovery'].split('/'))).read_text(encoding='utf-8'))
                         for suite in suites}
        prepared = launcher.selection_plan(suites, docs, selected_docs, decisions, 'reviewed-subset')
        driver.validate_ci_selection(prepared, decisions)
    except (driver.CIError, launcher.LauncherError, review.ReviewError) as exc:
        raise ClosureError('clean CI selection lacks exact case or fixture closure: ' + str(exc)) from exc
    inventories = [x for x in receipt['evidence'] if x['kind'] == 'dynamic-dependency-inventory']
    if len(inventories) != 1:
        raise ClosureError('expected one source-reviewed dynamic dependency inventory')
    saved = json.loads(_real_file(root.joinpath(*inventories[0]['path'].split('/'))).read_text(encoding='utf-8'))
    expected = derive_dynamic_inventory(policy, ci_policy, candidate, docs, logical_root)
    verify_dynamic_inventory(saved, expected)
    selected_keys = {(suite, case) for suite, value in prepared.items() for case in value['selected']}
    cmake_build = verify_cmake_build_records(root, files, source_sha, source_tree, logical_root,
                                            policy['qt_version'], selected_keys)
    conan = verify_conan_graph(root, files, source_sha, source_tree, logical_root)
    conan_process = verify_conan_process_records(root, files, source_sha, source_tree, logical_root)
    preflights = verify_hosted_preflights(root, source_sha, source_tree, logical_root, policy['qt_version'])
    declarations = prepare_clean_qt_proof(root, policy, proof_dir)
    tools = verify_clean_tool_payload(root, files, proof_dir)
    prefix = 'q/' + policy['qt_version'] + '/msvc2022_64/'
    expected_qt = {prefix + x['source'] for x in declarations['files']}
    staged_qt = {x['destination'] for x in candidate['files'] if x['destination'].startswith(prefix)}
    if expected_qt != staged_qt:
        raise ClosureError('clean re-extracted Qt file set differs from the candidate and manifest')
    expected_dirs, seen_dirs = [], set()
    for value in [plan['paths']['qt'].rstrip('/') + '/bin',
                  str(PurePosixPath(plan['paths']['ctest']).parent), *plan['runtime_dirs'],
                  *policy.get('loader_extra_dirs', [])]:
        _safe_relative(value)
        if value.casefold() not in seen_dirs:
            expected_dirs.append(value); seen_dirs.add(value.casefold())
    if receipt.get('runtime_dirs') != expected_dirs:
        raise ClosureError('clean PE runtime directories differ from the actual test PATH')
    pair = derive_verified_python_pair(root, files, source_sha, source_tree, logical_root)
    processes = derive_pe_processes(suites, prepared, docs, saved, files, logical_root)
    pe = resolve_candidate_pe_imports(candidate, processes, expected_dirs, os.environ.get('SystemRoot', ''),
                                      lambda name: windows_system_resolver(name, allow_not_found=True), python_pair=pair)
    host_evidence = [x for x in receipt['evidence'] if x['kind'] == 'host-system-resolution']
    if len(host_evidence) != 1:
        raise ClosureError('producer system-import evidence must be unique')
    recorded_host = _strict_json_file(_real_file(root.joinpath(*host_evidence[0]['path'].split('/'))))
    def imported_names(value):
        if (not isinstance(value, dict) or not isinstance(value.get('system_imports'), list) or
                any(not isinstance(x, dict) or any(not isinstance(x.get(k), str) or not x[k]
                    for k in ('process', 'importer', 'kind', 'requested')) for x in value['system_imports'])):
            raise ClosureError('invalid producer system-import evidence')
        return [(x.get('process'), x.get('importer'), x.get('kind'), x.get('requested'))
                for x in value['system_imports']]
    if imported_names(recorded_host) != imported_names(pe):
        raise ClosureError('clean PE system import identities differ from the producer')
    if recorded_host.get('legacy_checks') != pe.get('legacy_checks'):
        raise ClosureError('clean earlier-directory DLL checks differ from the producer')
    return {'scope': 'hosted CI staged input checks only; producer and clean group executions are separately required',
            'generated_media': generated, 'source_inventory': source_inventory,
            'conan_host_packages': conan['host_packages'], 'system_imports': len(pe['system_imports']),
            'qt_files': len(expected_qt), 'selected_cases': sum(len(x['selected']) for x in prepared.values()),
            'hosted_preflights': preflights, 'conan_process': conan_process, 'official_tools': tools,
            'cmake_build': cmake_build}


def candidate_provenance(root, policy, source_sha, source_tree, logical_root, candidate_files):
    """Construct provenance from exact build records, public pins and graph.

    This describes build inputs, not a claim of complete runtime observation.
    For a local Conan build, the displayed remote identifies the locked recipe,
    while the executable digest identifies the produced CPython DLL.
    """
    root = Path(root)
    def file(relative):
        return _real_file(root.joinpath(*_safe_relative(relative).split('/')))
    def doc(relative):
        return _strict_json_file(file(relative))
    identity = doc('b/native-kit/build_identity.json')
    expected = {'schema': 1, 'role': 'main', 'source_sha': source_sha, 'source_tree': source_tree,
                'configuration': 'RelWithDebInfo', 'native_bundle_mode': True,
                'generator': 'Ninja Multi-Config', 'qt_version': policy.get('qt_version')}
    if not isinstance(identity, dict) or any(identity.get(k) != v for k, v in expected.items()):
        raise ClosureError('main build provenance does not match the real configured source and Qt')
    if identity.get('cmake_cache_sha256') != digest(file('b/CMakeCache.txt')):
        raise ClosureError('main build provenance CMake cache changed')
    compiler = identity.get('compiler')
    if (not isinstance(compiler, dict) or not isinstance(compiler.get('path'), str) or
            ntpath.basename(compiler['path']).casefold() != 'cl.exe' or
            not re.fullmatch(r'[0-9a-f]{64}', str(compiler.get('sha256'))) or
            digest(_real_system_file(compiler['path'])) != compiler['sha256'] or
            not re.fullmatch(r'14\.4[0-9][0-9.]*', str(identity.get('msvc_toolset'))) or
            not re.fullmatch(r'[0-9.\\]+', str(identity.get('windows_sdk')))):
        raise ClosureError('actual MSVC compiler or Windows SDK provenance is incomplete')
    source_tools = doc('s/.github/windows-native-kit/tool-pins.json')
    pins = {x['name']: x for x in source_tools.get('artifacts', []) if isinstance(x, dict) and 'name' in x}
    if not {'cmake', 'python', '7z-extra', 'ifw'} <= set(pins):
        raise ClosureError('source-pinned build tools are incomplete')
    tools = []
    for name, pin_name in (('cmake', 'cmake'), ('ctest', 'cmake'), ('python', 'python'),
                           ('7z', '7z-extra'), ('ifw', 'ifw')):
        pin = pins[pin_name]
        tools.append({'name': name, 'version': pin['version'], 'origin': pin['url'], 'sha256': pin['sha256']})
    qt_tools = [x for x in policy.get('qt_archives', []) if 'qttools-Windows-' in x.get('file', '')]
    if len(qt_tools) != 1:
        raise ClosureError('source policy does not identify one official Qt tools archive')
    for name in ('lrelease', 'lupdate', 'rcc'):
        tools.append({'name': name, 'version': policy['qt_version'], 'origin': qt_tools[0]['url'],
                      'sha256': qt_tools[0]['sha256']})
    graph = doc('b/conan-install-graph.json')
    nodes = graph.get('graph', {}).get('nodes', {}) if isinstance(graph, dict) else {}
    if not isinstance(nodes, dict):
        raise ClosureError('Conan graph cannot establish SDK and CPython provenance')
    host = [x for x in nodes.values() if isinstance(x, dict) and x.get('context') == 'host']
    def package(name):
        result = [x for x in host if isinstance(x.get('ref'), str) and x['ref'].startswith(name + '/')]
        if len(result) != 1:
            raise ClosureError('Conan host graph must identify exactly one ' + name + ' package')
        return result[0]
    sdk, cpython = package('plotjuggler_sdk'), package('cpython')
    sdk_ref = re.fullmatch(r'plotjuggler_sdk/([^#%]+)#[0-9a-f]{32}(?:%.*)?', sdk['ref'])
    python_ref = re.fullmatch(r'cpython/([^#%]+)#[0-9a-f]{32}(?:%.*)?', cpython['ref'])
    if not sdk_ref or not python_ref:
        raise ClosureError('Conan SDK or CPython graph ref lacks an exact recipe revision')
    urls = {'conancenter': 'https://center2.conan.io',
            'plotjuggler-conan': 'https://plotjuggler.jfrog.io/artifactory/api/conan/plotjuggler-conan'}
    remote = cpython.get('binary_remote')
    python_version = python_ref.group(1)
    if remote not in urls:
        if cpython.get('binary') != 'Build' or cpython.get('remote') not in urls:
            raise ClosureError('embedded CPython graph must identify its binary remote or locked source-build recipe remote')
        remote = cpython['remote']
        python_version += ' (built from locked Conan recipe)'
    try:
        folder = audit.to_relative(cpython.get('package_folder'), logical_root)
    except (audit.AuditError, TypeError) as exc:
        raise ClosureError('embedded CPython package folder is not in the same root') from exc
    _safe_relative(folder)
    dlls = [x for x in candidate_files if x.get('path', '').casefold().startswith(folder.casefold() + '/') and
            re.fullmatch(r'python3[0-9]+\.dll', x['path'].rsplit('/', 1)[-1], re.I)]
    if len(dlls) != 1 or digest(file(dlls[0]['path'])) != dlls[0]['sha256']:
        raise ClosureError('embedded CPython DLL is missing, ambiguous or not the candidate bytes')
    tools.append({'name': 'embedded-cpython', 'version': python_version, 'origin': urls[remote],
                  'sha256': dlls[0]['sha256']})
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith('GIT_')}
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull, GIT_ATTR_NOSYSTEM='1',
               GIT_TERMINAL_PROMPT='0', GIT_CONFIG_COUNT='1', GIT_CONFIG_KEY_0='core.fsmonitor',
               GIT_CONFIG_VALUE_0='false')
    completed = subprocess.run(['git', '-C', str(root / 's'), 'submodule', 'status', '--recursive'],
                               env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120, check=False)
    if completed.returncode:
        raise ClosureError('cannot verify exact recursive source submodule identities')
    subs = {}
    for line in completed.stdout.decode('utf-8', errors='strict').splitlines():
        match = re.fullmatch(r' ([0-9a-f]{40}) ([^\s]+)(?: \(.*\))?', line)
        if not match or match.group(2) in subs:
            raise ClosureError('source submodule is uninitialized, dirty or ambiguous')
        subs[match.group(2)] = match.group(1)
    workflow_sha = os.environ.get('GITHUB_WORKFLOW_SHA', '')
    image = (os.environ.get('ImageOS', '') + ' ' + os.environ.get('ImageVersion', '')).strip()
    generated = verify_generated_media(root, source_sha, source_tree, os.environ.get('PJ_MEDIA_MANIFEST_SHA256', ''))
    value = {'source_sha': source_sha, 'source_tree': source_tree, 'workflow_sha': workflow_sha,
             'source_clean': True, 'configuration': 'RelWithDebInfo', 'qt': policy['qt_version'],
             'source_clean_scope': 'tracked checkout clean; four generated fixture inputs are identified separately',
             'generated_fixtures': generated,
             'sdk': sdk_ref.group(1), 'compiler': 'MSVC ' + identity['msvc_toolset'] + ' SHA-256 ' + compiler['sha256'],
             'windows_sdk': identity['windows_sdk'], 'generator': 'Ninja Multi-Config', 'runner_image': image,
             'conan_lock_sha256': digest(file('s/conan.lock')), 'conan_graph_sha256': digest(file('b/conan-install-graph.json')),
             'submodules': subs, 'tools': tools}
    try:
        audit.check_provenance(value)
    except audit.AuditError as exc:
        raise ClosureError('derived build provenance is incomplete: ' + str(exc)) from exc
    return value


def prepare_candidate_receipt(root, candidate_path, report_path, policy_path, output):
    """Build only a pre-execution candidate after all real inputs close."""
    root, output = Path(root).absolute(), Path(output).absolute()
    candidate_path, report_path, policy_path = map(lambda x: _real_file(Path(x).absolute()),
                                                   (candidate_path, report_path, policy_path))
    if (output != root / 'b/native-kit/closure-evidence' or not output.is_dir() or
            policy_path != root / 's/.github/windows-native-kit/ci-closure-policy.json' or
            candidate_path != root / 'b/native-kit/stage-candidate.json' or
            report_path != root / 'b/native-kit/stage-gaps.json' or any(output.iterdir())):
        raise ClosureError('candidate control paths must be exact, new and empty')
    policy, candidate, report = map(_strict_json_file, (policy_path, candidate_path, report_path))
    if (not isinstance(policy, dict) or policy.get('schema') != 2 or policy.get('verifier_sha256') != digest(Path(__file__)) or
            not isinstance(candidate, dict) or not isinstance(candidate.get('files'), list) or
            not isinstance(candidate.get('origins'), dict) or not isinstance(report, dict)):
        raise ClosureError('candidate, source-reviewed policy or verifier identity is invalid')
    sha, tree, logical = (report.get(x) for x in ('source_sha', 'source_tree', 'logical_root'))
    required_root = 'C:\\Users\\Administrator\\PlotJuggler-4.1.0-zh-test-558a\\n\\' + str(sha)[:12]
    if (not re.fullmatch(r'[0-9a-f]{40}', str(sha)) or not re.fullmatch(r'[0-9a-f]{40}', str(tree)) or
            os.environ.get('GITHUB_SHA') != sha or report.get('configuration') != 'RelWithDebInfo' or
            audit.windows_root(logical) != logical or logical != required_root):
        raise ClosureError('candidate report does not match the actual CI source and fixed root')
    audit.check_root(root, logical, require_exact=True)
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith('GIT_')}
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull, GIT_ATTR_NOSYSTEM='1',
               GIT_TERMINAL_PROMPT='0', GIT_CONFIG_COUNT='1', GIT_CONFIG_KEY_0='core.fsmonitor',
               GIT_CONFIG_VALUE_0='false')
    def git(*values):
        proc = subprocess.run(['git', '-C', str(root / 's'), *values], env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120, check=False)
        if proc.returncode:
            raise ClosureError('cannot independently verify candidate source identity')
        return proc.stdout.decode('utf-8', errors='strict').strip()
    if git('rev-parse', 'HEAD') != sha or git('rev-parse', 'HEAD^{tree}') != tree:
        raise ClosureError('candidate source commit or recursive worktree differs')
    verify_generated_media(root, sha, tree, os.environ.get('PJ_MEDIA_MANIFEST_SHA256', ''))
    verify_generated_source_status(git('status', '--porcelain=v1', '-z', '--untracked-files=all', '--ignore-submodules=none'))
    files, seen = [], set()
    for row in candidate['files']:
        if not isinstance(row, dict):
            raise ClosureError('invalid candidate stage entry')
        dest, source = _safe_relative(row.get('destination')), _safe_relative(row.get('source'))
        origin = candidate['origins'].get(row.get('origin'))
        if (dest.casefold() in seen or not isinstance(origin, dict) or not isinstance(origin.get('root'), str) or
                not Path(origin['root']).is_absolute() or not re.fullmatch(r'[0-9a-f]{64}', str(row.get('sha256')))):
            raise ClosureError('candidate origin, destination or hash is invalid')
        actual = _real_file(Path(origin['root']).joinpath(*source.split('/')))
        if digest(actual) != row['sha256']:
            raise ClosureError('candidate source bytes changed: ' + dest)
        seen.add(dest.casefold()); files.append({'path': dest, 'sha256': row['sha256']})
    tracked = parse_tracked_source(git('ls-files', '--recurse-submodules', '--stage', '-z'))
    source_paths_match(tracked, [row['path'] for row in files], SYNTHETIC_MEDIA_PATHS)
    launcher = _module('native_producer_closure_launcher', 'run_native_test_bundle.py')
    driver = _module('native_producer_closure_driver', 'run_native_ci_verification.py')
    run_plan = _strict_json_file(root / 'b/native-kit/run-plan.json')
    paths, runtime_dirs, suites = launcher.validate_plan(run_plan, sha, tree, 'RelWithDebInfo')
    docs = {suite['id']: _strict_json_file(root.joinpath(*suite['full_discovery'].split('/'))) for suite in suites}
    selected_docs = {suite['id']: _strict_json_file(root.joinpath(*suite['discovery'].split('/'))) for suite in suites}
    derived = derive_partition(policy, docs, sha, tree, logical, [x['path'] for x in files], report.get('coverage'))
    try:
        decisions = driver.validate_policy(derived, docs, sha, tree, 'RelWithDebInfo', {'files': files})
        prepared = launcher.selection_plan(suites, docs, selected_docs, decisions, 'reviewed-subset')
        driver.validate_ci_selection(prepared, decisions)
    except (driver.CIError, launcher.LauncherError, review.ReviewError) as exc:
        raise ClosureError('candidate case/fixture/DEPENDS selection does not close: ' + str(exc)) from exc
    dynamic = derive_dynamic_inventory(policy, derived, candidate, docs, logical)
    selected_keys = {(suite, case) for suite, value in prepared.items() for case in value['selected']}
    cmake_build = verify_cmake_build_records(root, files, sha, tree, logical, policy['qt_version'], selected_keys)
    conan = verify_conan_graph(root, files, sha, tree, logical)
    conan_process = verify_conan_process_records(root, files, sha, tree, logical)
    preflights = verify_hosted_preflights(root, sha, tree, logical, policy['qt_version'])
    qt = prepare_qt_declarations(root, policy, output / 'qt-reference')
    qt_prefix = 'q/' + policy['qt_version'] + '/msvc2022_64/'
    selected_qt = {qt_prefix + item['source'] for item in qt['files']}
    if selected_qt != {x['path'] for x in files if x['path'].startswith(qt_prefix)}:
        raise ClosureError('candidate Qt files differ from verified official archive members')
    provenance = candidate_provenance(root, policy, sha, tree, logical, files)
    dirs = [paths['qt'].rstrip('/') + '/bin', str(Path(paths['ctest']).parent).replace('\\', '/'),
            *runtime_dirs, *policy.get('loader_extra_dirs', [])]
    runtime, seen_dirs = [], set()
    for value in dirs:
        _safe_relative(value)
        if value.casefold() not in seen_dirs:
            runtime.append(value); seen_dirs.add(value.casefold())
    pair = derive_verified_python_pair(root, files, sha, tree, logical)
    processes = derive_pe_processes(suites, prepared, docs, dynamic, files, logical)
    pe = resolve_candidate_pe_imports(candidate, processes, runtime, os.environ.get('SystemRoot', ''),
                                      lambda name: windows_system_resolver(name, allow_not_found=True), python_pair=pair)
    modules = {'schema': 1, 'scope': pe['scope'], 'system_imports': pe['system_imports'],
               'legacy_checks': pe['legacy_checks']}
    selected = sorted(({'suite': suite, 'case': case} for suite, value in prepared.items()
                       for case in value['selected']), key=lambda x: (x['suite'], x['case']))
    if not selected:
        raise ClosureError('candidate has no selected source-reviewed tests')
    # Write controls only after independent checks have succeeded; these are
    # pre-execution records. The two real hosted executions remain mandatory.
    def write(name, value):
        path = output / name
        with path.open('x', encoding='utf-8', newline='\n') as stream:
            json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2); stream.write('\n')
        return path
    write('ci-policy.json', derived); write('provenance.json', provenance)
    evidence = []
    def record(kind, name, value, **extra):
        path = write(name, value)
        evidence.append({'kind': kind, 'path': path.relative_to(root).as_posix(), 'sha256': digest(path), **extra})
    for kind, name, value in (
        ('qt-origin-extraction', 'qt-origin-extraction.json', {'scope': 'verified producer archive members', 'declarations': qt}),
        ('conan-origin-license', 'conan-origin-license.json', {'graph': conan, 'process': conan_process,
                                                               'cmake_build': cmake_build}),
        ('host-system-resolution', 'host-system-resolution.json', modules),
        ('dynamic-dependency-inventory', 'dynamic-dependency-inventory.json', dynamic),
        ('private-registry-lifecycle', 'private-registry-lifecycle.json', preflights),
        ('ci-temp-safety', 'ci-temp-safety.json', preflights),
        ('linked-marker-mutation', 'linked-marker-mutation.json', preflights),
        ('bootstrap-adversarial', 'bootstrap-adversarial.json', preflights)):
        record(kind, name, value)
    record('case-source-review', 'case-source-review.json', {'scope': 'exact source-reviewed case partition',
           'source_sha': sha, 'source_tree': tree, 'cases': selected}, cases=selected)
    for name, source in (('candidate-plan.json', candidate_path), ('candidate-report.json', report_path)):
        target = output / name
        with source.open('rb') as src, target.open('xb') as dst:
            shutil.copyfileobj(src, dst, 1024 * 1024)
        evidence.append({'kind': 'candidate-input', 'path': target.relative_to(root).as_posix(), 'sha256': digest(target)})
    receipt = {'schema': 1, 'source_sha': sha, 'source_tree': tree, 'configuration': 'RelWithDebInfo',
               'candidate_plan_sha256': digest(candidate_path), 'candidate_report_sha256': digest(report_path),
               'reviewed_policy_sha256': digest(policy_path), 'verifier_sha256': digest(Path(__file__)),
               'runtime_dirs': runtime, 'evidence': evidence}
    write('receipt.json', receipt)
    return {'scope': 'input-verified candidate only; producer and independent CI test runs remain required',
            'selected_cases': len(selected), 'evidence_files': len(evidence)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--candidate-plan')
    parser.add_argument('--candidate-report')
    parser.add_argument('--reviewed-policy', required=True)
    parser.add_argument('--output-dir')
    parser.add_argument('--output')
    parser.add_argument('--prepare-declarations', action='store_true')
    parser.add_argument('--verify-codemodel', action='store_true')
    parser.add_argument('--codemodel-index')
    parser.add_argument('--codemodel-rule', choices=sorted(CODEMODEL_RULES))
    parser.add_argument('--verify-staged', action='store_true')
    parser.add_argument('--manifest')
    parser.add_argument('--manifest-sha256')
    parser.add_argument('--source-sha')
    parser.add_argument('--source-tree')
    parser.add_argument('--evidence-receipt')
    args = parser.parse_args()
    if args.verify_codemodel:
        try:
            if (sys.platform != 'win32' or os.environ.get('GITHUB_ACTIONS') != 'true' or
                    os.environ.get('RUNNER_ENVIRONMENT') != 'github-hosted' or
                    os.environ.get('GITHUB_SHA') != args.source_sha or
                    not re.fullmatch(r'[0-9a-f]{40}', str(args.source_sha)) or
                    not re.fullmatch(r'[0-9a-f]{40}', str(args.source_tree))):
                raise ClosureError('File API verification requires the exact source on disposable Windows hosted CI')
            root = Path(args.root).absolute()
            logical = 'C:\\Users\\Administrator\\PlotJuggler-4.1.0-zh-test-558a\\n\\' + args.source_sha[:12]
            audit.check_root(root, logical, require_exact=True)
            policy_path = Path(args.reviewed_policy).absolute()
            plan_path = Path(args.candidate_plan).absolute() if args.candidate_plan else None
            output = Path(args.output).absolute() if args.output else None
            if (policy_path != root / 's/.github/windows-native-kit/ci-closure-policy.json' or
                    plan_path != root / 'b/native-kit/stage-candidate.json' or not output or
                    not output.is_relative_to(root / 'b/native-kit/codemodel') or
                    not output.parent.is_dir() or output.exists() or not args.codemodel_rule):
                raise ClosureError('File API policy, candidate or new output path is invalid')
            env = {k: v for k, v in os.environ.items() if not k.upper().startswith('GIT_')}
            env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull, GIT_ATTR_NOSYSTEM='1',
                       GIT_TERMINAL_PROMPT='0', GIT_CONFIG_COUNT='1', GIT_CONFIG_KEY_0='core.fsmonitor',
                       GIT_CONFIG_VALUE_0='false')
            def git(*values):
                result = subprocess.run(['git', '-C', str(root / 's'), *values], capture_output=True, env=env, timeout=120)
                if result.returncode:
                    raise ClosureError('cannot verify the File API source checkout with git')
                return result.stdout.decode('utf-8', errors='strict').strip()
            if git('rev-parse', 'HEAD') != args.source_sha or git('rev-parse', 'HEAD^{tree}') != args.source_tree:
                raise ClosureError('File API verification requires the exact clean source commit and tree')
            verify_generated_media(root, args.source_sha, args.source_tree, os.environ.get('PJ_MEDIA_MANIFEST_SHA256', ''))
            verify_generated_source_status(git('status', '--porcelain=v1', '-z', '--untracked-files=all', '--ignore-submodules=none'))
            policy = _strict_json_file(_real_file(policy_path))
            if policy.get('schema') != 2 or policy.get('verifier_sha256') != digest(Path(__file__)):
                raise ClosureError('File API verification needs the exact source-reviewed verifier policy')
            before = digest(_real_file(plan_path))
            plan = _strict_json_file(plan_path)
            if not isinstance(plan, dict) or not isinstance(plan.get('files'), list) or not isinstance(plan.get('origins'), dict):
                raise ClosureError('invalid File API candidate plan')
            rows = {}
            for row in plan['files']:
                if not isinstance(row, dict):
                    raise ClosureError('invalid File API candidate file')
                relative = _safe_relative(row.get('destination'))
                if relative.casefold() in rows:
                    raise ClosureError('duplicate File API candidate path')
                rows[relative.casefold()] = row
            def candidate_file(relative):
                row = rows.get(relative.casefold())
                origin = plan['origins'].get(row.get('origin')) if row else None
                if not isinstance(origin, dict) or not isinstance(origin.get('root'), str) or not Path(origin['root']).is_absolute():
                    raise ClosureError('File API candidate origin is not absolute')
                return Path(origin['root']).joinpath(*_safe_relative(row.get('source')).split('/'))
            files = [{'path': row['destination'], 'sha256': row.get('sha256')} for row in plan['files']]
            result = verify_codemodel_dynamic_targets(root, logical, files, policy, args.codemodel_index,
                                                     args.codemodel_rule, args.source_sha, args.source_tree,
                                                     resolver=candidate_file)
            if digest(plan_path) != before:
                raise ClosureError('File API candidate changed during verification')
            with output.open('x', encoding='utf-8', newline='\n') as stream:
                json.dump(result, stream, ensure_ascii=False, sort_keys=True, indent=2)
                stream.write('\n')
            return 0
        except (ClosureError, audit.AuditError, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
            print('File API static verification failed: ' + str(exc), file=sys.stderr)
            return 1
    if args.prepare_declarations:
        try:
            root = Path(args.root).absolute()
            if (not re.fullmatch(r'[0-9a-f]{40}', str(args.source_sha)) or
                    not re.fullmatch(r'[0-9a-f]{40}', str(args.source_tree)) or not args.output):
                raise ClosureError('declarations require the full source commit/tree and a new output')
            source = root / 's'
            output = Path(args.output).absolute()
            policy_path = Path(args.reviewed_policy).absolute()
            if (output.exists() or not output.is_relative_to(root / 'b') or not output.parent.is_dir() or
                    policy_path != source / '.github/windows-native-kit/ci-closure-policy.json'):
                raise ClosureError('declaration output or reviewed policy path is invalid')
            env = {k: v for k, v in os.environ.items() if not k.upper().startswith('GIT_')}
            env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
                       GIT_ATTR_NOSYSTEM='1', GIT_TERMINAL_PROMPT='0', GIT_CONFIG_COUNT='1',
                       GIT_CONFIG_KEY_0='core.fsmonitor', GIT_CONFIG_VALUE_0='false')
            def git(*values):
                result = subprocess.run(['git', '-C', str(source), *values], capture_output=True, env=env, timeout=120)
                if result.returncode:
                    raise ClosureError('cannot verify clean source identity using git')
                return result.stdout.decode('utf-8', errors='strict').strip()
            if git('rev-parse', 'HEAD') != args.source_sha or git('rev-parse', 'HEAD^{tree}') != args.source_tree:
                raise ClosureError('Qt declaration source commit or tree is not the exact clean source')
            verify_generated_media(root, args.source_sha, args.source_tree, os.environ.get('PJ_MEDIA_MANIFEST_SHA256', ''))
            verify_generated_source_status(git('status', '--porcelain=v1', '-z', '--untracked-files=all', '--ignore-submodules=none'))
            policy = json.loads(_real_file(policy_path).read_text(encoding='utf-8'))
            if policy.get('schema') != 2 or policy.get('verifier_sha256') != digest(Path(__file__)):
                raise ClosureError('Qt declarations require the exact source-reviewed verifier policy')
            declarations = prepare_qt_declarations(root, policy, root / 'b/native-kit/qt-reference')
            with output.open('x', encoding='utf-8', newline='\n') as stream:
                json.dump(declarations, stream, indent=2, sort_keys=True)
                stream.write('\n')
            return 0
        except (ClosureError, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
            print('Qt declaration preparation failed: ' + str(exc), file=sys.stderr)
            return 1
    if args.verify_staged:
        try:
            if (sys.platform != 'win32' or os.environ.get('GITHUB_ACTIONS') != 'true' or
                    os.environ.get('RUNNER_ENVIRONMENT') != 'github-hosted'):
                raise ClosureError('staged replay requires a disposable Windows hosted CI runner')
            if (not re.fullmatch(r'[0-9a-f]{40}', str(args.source_sha)) or
                    not re.fullmatch(r'[0-9a-f]{40}', str(args.source_tree)) or
                    not re.fullmatch(r'[0-9a-f]{64}', str(args.manifest_sha256)) or
                    os.environ.get('GITHUB_SHA') != args.source_sha):
                raise ClosureError('staged replay source or manifest identity is invalid')
            root = Path(args.root).absolute()
            logical = 'C:\\Users\\Administrator\\PlotJuggler-4.1.0-zh-test-558a\\n\\' + args.source_sha[:12]
            manifest_path = Path(args.manifest).absolute()
            policy_path = Path(args.reviewed_policy).absolute()
            receipt_path = Path(args.evidence_receipt).absolute()
            if (manifest_path != root / '_bundle/manifest.json' or
                    policy_path != root / 's/.github/windows-native-kit/ci-closure-policy.json' or
                    receipt_path != root / 'b/native-kit/closure-evidence/receipt.json'):
                raise ClosureError('staged manifest, policy or receipt path differs')
            audit.verify_manifest(root, manifest_path, True, args.manifest_sha256, logical,
                                  args.source_sha, args.source_tree, 'RelWithDebInfo', allow_owned_runs=True)
            manifest = audit.read_json(manifest_path)
            policy = audit.read_json(policy_path)
            receipt = audit.read_json(receipt_path)
            if policy.get('schema') != 2 or policy.get('verifier_sha256') != digest(Path(__file__)):
                raise ClosureError('staged source-reviewed verifier hash differs')
            proof_dir = root / 'r' / ('ci-qt-proof-' + uuid.uuid4().hex)
            summary = verify_staged_inputs(root, manifest, receipt, policy, args.source_sha, args.source_tree, logical, proof_dir)
            print('staged input checks completed; reviewed-group execution is still required: ' +
                  json.dumps(summary, ensure_ascii=False), file=sys.stderr)
            return 0
        except (ClosureError, audit.AuditError, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
            print('hosted CI staged closure failed: ' + str(exc), file=sys.stderr)
            return 1
    try:
        if (sys.platform != 'win32' or os.environ.get('GITHUB_ACTIONS') != 'true' or
                os.environ.get('RUNNER_ENVIRONMENT') != 'github-hosted'):
            raise ClosureError('candidate preparation requires disposable Windows hosted CI')
        if not args.candidate_plan or not args.candidate_report or not args.output_dir:
            raise ClosureError('candidate preparation requires plan, report and a new evidence directory')
        summary = prepare_candidate_receipt(args.root, args.candidate_plan, args.candidate_report,
                                            args.reviewed_policy, args.output_dir)
        print('pre-execution candidate inputs verified: ' + json.dumps(summary, ensure_ascii=False), file=sys.stderr)
        return 0
    except (ClosureError, audit.AuditError, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print('candidate input closure failed: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
