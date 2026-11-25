#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Preserve only the raw test evidence from one disposable hosted-CI run.

The candidate ZIP remains byte-for-byte unchanged. This CI-only sidecar is not
interactive-VM evidence and does not turn an incomplete or skipped run green.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import ntpath
import os
from pathlib import Path
import re
import stat
import sys

spec = importlib.util.spec_from_file_location('native_ci_evidence_audit', Path(__file__).with_name('native_bundle_audit.py'))
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

ROOT_FILES = (
    'artifact-binding.json', 'execution-plan.json', 'incomplete.json', 'summary.json', 'environment.json',
    'ci-identity.json', 'ci-temp-started.json', 'ci-temp-process.json', 'ci-temp.stdout.bin', 'ci-temp.stderr.bin',
    'driver-python-started.json', 'driver-python-process.json', 'driver-python.stdout.bin', 'driver-python.stderr.bin',
)
SUITES = ('main', 'i18n', 'file-dialog', 'csv-runtime')
SUITE_FILES = (
    'selection.json', 'environment.json', 'selected.txt', 'selected-discovery.json',
    'discovery-started.json', 'discovery-process.json', 'discovery.stdout.bin', 'discovery.stderr.bin',
    'execution-started.json', 'process.json', 'stdout.bin', 'stderr.bin', 'ctest.log', 'LastTest.log',
    'junit.xml', 'coverage.json', 'owned-output-inventory.json', 'post-suite-inventory.json',
    'csv-audit.json', 'file-dialog-audit.json', 'feedback-audit.json', 'app-guard-audit.json',
)
GUARD_FILES = (
    'app-argv.json', 'app-start.json', 'app-process.json', 'app-exit.json', 'guard-status.json',
    'before.stdout.bin', 'before.stderr.bin', 'before.process.json',
    'after.stdout.bin', 'after.stderr.bin', 'after.process.json',
)
SCREENSHOT_STAGES = ('apbin', 'fft-menu', 'fft-initial', 'fft-computed', 'fft-exported',
                     'fft-computed-compact', 'fft-exported-compact', 'language-switch')
LANGUAGES = ('en_US', 'zh_CN', 'zh_TW')


class EvidenceError(Exception):
    """Evidence cannot safely or unambiguously be retained."""


def _directory(path):
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
        raise EvidenceError('evidence path is not an ordinary directory: ' + str(path))
    audit.check_no_named_streams(path, True)


def _ordinary_chain(path):
    for item in (path, *path.parents):
        _directory(item)


def _hash(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def _copy_file(source, destination, rel):
    info = audit.regular_file(source)
    audit.check_no_named_streams(source, False)
    destination.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    with source.open('rb') as reader, destination.open('xb') as writer:
        current = os.fstat(reader.fileno())
        if (current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns) != (
                info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns):
            raise EvidenceError('evidence file changed before copying: ' + rel)
        for block in iter(lambda: reader.read(1024 * 1024), b''):
            writer.write(block)
            digest.update(block)
        end = os.fstat(reader.fileno())
        if (end.st_dev, end.st_ino, end.st_size, end.st_mtime_ns) != (
                current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns):
            raise EvidenceError('evidence file changed while copying: ' + rel)
    if destination.stat().st_size != info.st_size or _hash(destination) != digest.hexdigest():
        raise EvidenceError('retained evidence differs from original bytes: ' + rel)
    return {'path': rel, 'bytes': info.st_size, 'sha256': digest.hexdigest()}


def collect(root, output, binding, outcome, scope, bootstrap=None, python_origin=None, require_origin=False):
    """Copy a fixed allowlist, keeping failure evidence without following links."""
    root, output = Path(root).absolute(), Path(output).absolute()
    if (not isinstance(binding, dict) or binding.get('schema') != 1 or
            binding.get('scope') != 'github-hosted-windows-ci' or
            not re.fullmatch(r'[0-9a-f]{40}', str(binding.get('source_sha', ''))) or
            not re.fullmatch(r'[0-9a-f]{40}', str(binding.get('source_tree', ''))) or
            any(not re.fullmatch(r'[0-9a-f]{64}', str(binding.get(k, ''))) for k in ('archive_sha256', 'manifest_sha256')) or
            binding.get('configuration') != 'RelWithDebInfo' or scope not in ('producer', 'clean') or
            outcome not in ('success', 'failure', 'cancelled', 'skipped', '')):
        raise EvidenceError('invalid CI candidate binding or step outcome')
    _ordinary_chain(output.parent)
    if output.exists() or output.is_symlink():
        raise EvidenceError('refusing to replace existing CI evidence')
    output.mkdir()
    rows = []

    def copy_if_present(source, rel):
        if source.exists() or source.is_symlink():
            _ordinary_chain(source.parent)
            rows.append(_copy_file(source, output.joinpath(*rel.split('/')), rel))

    if bootstrap is not None:
        bootstrap = Path(bootstrap).absolute()
        if bootstrap.exists() or bootstrap.is_symlink():
            _ordinary_chain(bootstrap.parent)
            audit.regular_file(bootstrap)
            audit.check_no_named_streams(bootstrap, False)
            record = json.loads(bootstrap.read_text(encoding='utf-8'))
            if (not isinstance(record, dict) or record.get('status') != 'verified' or
                    any(record.get(k) != binding[k] for k in ('source_sha', 'source_tree', 'archive_sha256', 'manifest_sha256'))):
                raise EvidenceError('bootstrap receipt does not match the candidate')
            copy_if_present(bootstrap, 'bootstrap.json')

    origin_found = False
    if python_origin is not None:
        python_origin = Path(python_origin).absolute()
        if python_origin.exists() or python_origin.is_symlink():
            _ordinary_chain(python_origin.parent)
            audit.regular_file(python_origin)
            audit.check_no_named_streams(python_origin, False)
            record = json.loads(python_origin.read_text(encoding='utf-8'))
            if (not isinstance(record, dict) or record.get('schema') != 1 or
                    record.get('scope') != 'disposable-github-hosted-windows-ci' or
                    any(record.get(k) != binding[k] for k in ('source_sha', 'source_tree', 'archive_sha256', 'manifest_sha256')) or
                    not isinstance(record.get('members'), list) or not record['members']):
                raise EvidenceError('pre-execution Python origin receipt does not match the candidate')
            copy_if_present(python_origin, 'python-origin.json')
            origin_found = True
    if require_origin and outcome == 'success' and not origin_found:
        raise EvidenceError('successful CI verification lacks pre-execution Python origin evidence')

    runs = []
    if root.exists() or root.is_symlink():
        _ordinary_chain(root)
        run_parent = root / 'r'
        if run_parent.exists() or run_parent.is_symlink():
            _ordinary_chain(run_parent)
            for entry in run_parent.iterdir():
                if re.fullmatch(r'ci-[0-9a-f]{32}', entry.name):
                    _directory(entry)
                    runs.append(entry)
    if len(runs) > 1:
        raise EvidenceError('more than one CI run claims this candidate root')
    run = runs[0] if runs else None
    status = 'not-started'
    if run is not None:
        binding_file = run / 'artifact-binding.json'
        if binding_file.exists() or binding_file.is_symlink():
            audit.regular_file(binding_file)
            audit.check_no_named_streams(binding_file, False)
            if json.loads(binding_file.read_text(encoding='utf-8')) != binding:
                raise EvidenceError('run binding does not match the candidate')
        elif outcome == 'success':
            raise EvidenceError('successful run has no candidate binding')
        for name in ROOT_FILES:
            copy_if_present(run / name, name)
        for suite in SUITES:
            directory = run / suite
            if not (directory.exists() or directory.is_symlink()):
                continue
            _directory(directory)
            for name in SUITE_FILES:
                copy_if_present(directory / name, suite + '/' + name)
            diagnostics = directory / 'csv-diagnostics'
            if diagnostics.exists() or diagnostics.is_symlink():
                _directory(diagnostics)
                for language in LANGUAGES:
                    copy_if_present(diagnostics / (language + '.json'), suite + '/csv-diagnostics/' + language + '.json')
            golden = directory / 'pointcloud-golden'
            if golden.exists() or golden.is_symlink():
                _directory(golden)
                for item in sorted(golden.iterdir(), key=lambda p: p.name):
                    if re.fullmatch(r'[A-Za-z0-9_.-]+_(?:actual|diff)\.png', item.name):
                        copy_if_present(item, suite + '/pointcloud-golden/' + item.name)
        screenshots = run / 'screenshots'
        if screenshots.exists() or screenshots.is_symlink():
            _directory(screenshots)
            for stage in SCREENSHOT_STAGES:
                for language in LANGUAGES:
                    name = 'full-' + stage + '-' + language + '.png'
                    copy_if_present(screenshots / name, 'screenshots/' + name)
        guards = run / 'app-guard'
        if guards.exists() or guards.is_symlink():
            _directory(guards)
            for launch in sorted(guards.iterdir(), key=lambda p: p.name):
                if not re.fullmatch(r'launch-[0-9a-f]{32}', launch.name):
                    continue
                _directory(launch)
                for name in GUARD_FILES:
                    copy_if_present(launch / name, 'app-guard/' + launch.name + '/' + name)
        if (run / 'summary.json').is_file():
            if (run / 'incomplete.json').exists():
                raise EvidenceError('run cannot be both complete and incomplete')
            if not binding_file.is_file():
                raise EvidenceError('a completed run must carry its candidate binding')
            # Read the already verified retained bytes, not a changing source.
            summary = json.loads((output / 'summary.json').read_text(encoding='utf-8'))
            if summary.get('status') not in ('planned-ci-groups-completed', 'ci-executed-with-conditional-skips'):
                raise EvidenceError('unexpected CI run summary status')
            status = summary['status']
        else:
            status = 'incomplete'
    if outcome == 'success' and (run is None or status in ('not-started', 'incomplete')):
        raise EvidenceError('CI verification reported success without a completed run receipt')
    receipt = {'schema': 1, 'scope': scope + '-github-hosted-windows-ci', 'binding': binding,
               'verification_step_outcome': outcome, 'run_status': status,
               'run_directory': run.name if run else None, 'files': sorted(rows, key=lambda row: row['path'])}
    with (output / 'evidence-manifest.json').open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(receipt, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write('\n')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'output', 'source-sha', 'source-tree', 'archive-sha256', 'manifest-sha256', 'scope', 'outcome'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    try:
        if (sys.platform != 'win32' or os.environ.get('GITHUB_ACTIONS') != 'true' or
                os.environ.get('RUNNER_ENVIRONMENT') != 'github-hosted' or
                os.environ.get('RUNNER_OS') != 'Windows' or os.environ.get('GITHUB_SHA') != args.source_sha):
            raise EvidenceError('only the exact source on a disposable Windows hosted CI runner is allowed')
        expected = 'C:\\Users\\Administrator\\PlotJuggler-4.1.0-zh-test-558a\\n\\' + args.source_sha[:12]
        if ntpath.normcase(ntpath.normpath(args.root)) != ntpath.normcase(expected):
            raise EvidenceError('the evidence root differs from the fixed same-source kit root')
        temp = Path(os.environ['RUNNER_TEMP']).absolute()
        output = Path(args.output).absolute()
        if output.parent != temp or output.name != 'pj-native-ci-evidence-' + args.scope:
            raise EvidenceError('evidence output is not the dedicated hosted runner directory')
        binding = {'schema': 1, 'scope': 'github-hosted-windows-ci', 'source_sha': args.source_sha,
                   'source_tree': args.source_tree, 'configuration': 'RelWithDebInfo',
                   'archive_sha256': args.archive_sha256, 'manifest_sha256': args.manifest_sha256}
        bootstrap = Path(args.root).parent.parent / 'receipts' / args.source_sha[:12] / 'bootstrap.json'
        origin = bootstrap.with_name('python-origin.json')
        receipt = collect(args.root, output, binding, args.outcome, args.scope, bootstrap, origin, True)
        print(json.dumps({'scope': receipt['scope'], 'run_status': receipt['run_status'],
                          'files': len(receipt['files'])}, ensure_ascii=False))
        return 0
    except (EvidenceError, audit.AuditError, OSError, ValueError, KeyError, TypeError) as exc:
        print('CI evidence preservation failed: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
