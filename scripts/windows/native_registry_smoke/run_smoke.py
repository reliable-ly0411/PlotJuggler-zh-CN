#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Exercise self-owned HKCU fixture keys on a disposable GitHub Windows runner.

Never scan registry prefixes and never run this fault-injection controller on
another machine. On ambiguous output, leave any keys alone and fail the job.
"""
from __future__ import annotations
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

UUID = r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}'
GUARD = re.compile(rb'^Private test registry: HKCU\\(PlotJugglerTest-' + UUID.encode() + rb')\r?$', re.MULTILINE)
LATE = re.compile(rb'^Owned late sentinel: HKCU\\(Software\\PJFixtureLate-' + UUID.encode() + rb')\r?$', re.MULTILINE)


class SmokeError(Exception):
    pass


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(data)
    return h.hexdigest()


def owned_names(stderr):
    matches = [pattern.findall(stderr) for pattern in (GUARD, LATE)]
    if any(len(items) != 1 for items in matches):
        raise SmokeError('the child did not provide exactly two self-owned identities')
    return [items[0].decode('ascii') for items in matches]


class WindowsRegistry:
    def __init__(self):
        import winreg
        self.winreg = winreg

    def exists(self, key):
        try:
            with self.winreg.OpenKey(self.winreg.HKEY_CURRENT_USER, key, 0, self.winreg.KEY_READ):
                return True
        except FileNotFoundError:
            return False

    def remove_exact_owned(self, key):
        w = self.winreg
        with w.OpenKey(w.HKEY_CURRENT_USER, key, 0, w.KEY_READ | w.KEY_WRITE | 0x00010000) as handle:
            advapi = ctypes.WinDLL('advapi32', use_last_error=True)
            advapi.RegDeleteTreeW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p]
            advapi.RegDeleteTreeW.restype = ctypes.c_long
            status = advapi.RegDeleteTreeW(int(handle), None)
            if status:
                raise SmokeError('cannot clear the exact owned key: Win32 error ' + str(status))
        w.DeleteKey(w.HKEY_CURRENT_USER, key)


def execute(executable, output, environment, registry, run=subprocess.run):
    """Only explicit, child-created UUID identities are queried or removed."""
    receipt = {'schema': 1, 'complete': False, 'normal': {}, 'injected': {}}
    for label, injected in (('normal', False), ('injected', True)):
        env = dict(environment)
        env.pop('PJ_FIXTURE_FAIL_CLEANUP', None)
        if injected:
            env['PJ_FIXTURE_FAIL_CLEANUP'] = '1'
        result = run([str(executable)], env=env, capture_output=True, timeout=60)
        (output / (label + '.stdout.bin')).write_bytes(result.stdout)
        (output / (label + '.stderr.bin')).write_bytes(result.stderr)
        keys = owned_names(result.stderr)
        item = receipt[label] = {'exit_code': result.returncode, 'owned_keys': keys,
                                 'stdout': label + '.stdout.bin', 'stderr': label + '.stderr.bin'}
        if b'Native guard initialized; QApplication-free lifecycle probe.' not in result.stderr:
            raise SmokeError(label + ' did not reach initialized guard')
        if not injected:
            if result.returncode != 0 or b'Late QSettings write failed closed; self-owned real sentinel untouched.' not in result.stderr:
                raise SmokeError('normal lifecycle did not fail closed and exit successfully')
            item['absent_after'] = [not registry.exists(key) for key in keys]
            if item['absent_after'] != [True, True]:
                raise SmokeError('normal lifecycle left an owned identity behind')
        else:
            if result.returncode != 1 or b'Injected owned-key cleanup failure: 5' not in result.stderr:
                raise SmokeError('injected cleanup did not report ERROR_ACCESS_DENIED and exit 1')
            item['present_before_exact_cleanup'] = [registry.exists(key) for key in keys]
            if item['present_before_exact_cleanup'] != [True, True]:
                raise SmokeError('both exact injected-run identities must exist before cleanup')
            for key in keys:
                registry.remove_exact_owned(key)
            item['absent_after_exact_cleanup'] = [not registry.exists(key) for key in keys]
            if item['absent_after_exact_cleanup'] != [True, True]:
                raise SmokeError('exact injected-run cleanup did not remove both owned identities')
    receipt['complete'] = True
    return receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--exe', required=True, type=Path)
    parser.add_argument('--source-dir', required=True, type=Path)
    parser.add_argument('--test-mains-dir', required=True, type=Path)
    parser.add_argument('--qt-core', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    try:
        if (sys.platform != 'win32' or os.environ.get('GITHUB_ACTIONS') != 'true' or
                os.environ.get('RUNNER_ENVIRONMENT') != 'github-hosted'):
            raise SmokeError('this fault-injection controller requires a disposable GitHub-hosted Windows runner')
        inputs = {'exe': args.exe, 'qt_core': args.qt_core,
                  'cmake': args.source_dir / 'CMakeLists.txt', 'source': args.source_dir / 'main.cpp',
                  'guard_header': args.test_mains_dir / 'pj_test_windows_registry.h'}
        if any(not p.is_absolute() or not p.is_file() for p in inputs.values()) or not args.output.is_absolute():
            raise SmokeError('all inputs and output must be absolute and inputs must exist')
        hashes = {name + '_sha256': digest(path) for name, path in inputs.items()}
        args.output.mkdir(parents=False, exist_ok=False)
        receipt = execute(args.exe, args.output, os.environ, WindowsRegistry())
        receipt.update(hashes)
        (args.output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
        return 0
    except (OSError, ValueError, SmokeError, subprocess.SubprocessError) as exc:
        print('registry fixture smoke failed: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
