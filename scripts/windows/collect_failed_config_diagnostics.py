#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Fail-closed, content-free diagnostics. Never copy raw process output."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import stat

_spec = importlib.util.spec_from_file_location('safe_ci_evidence', Path(__file__).with_name('collect_native_ci_evidence.py'))
safe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(safe)
LIMIT = 4 * 1024 * 1024
CATEGORIES = {
    'missing-package': r'could not find a package configuration file|could not find .*cmake',
    'missing-source': r'cannot find source file|does not contain a cmakelists.txt',
    'unknown-command': r'unknown cmake command',
    'invalid-target': r'cannot specify .* for target|target .* was not found',
    'generator-conflict': r'does not match the generator used previously',
    'compiler-check-failed': r'is not able to compile a simple test program',
}


def read_checked(path):
    safe._ordinary_chain(path.parent)
    info = safe.audit.regular_file(path)
    safe.audit.check_no_named_streams(path, False)
    if info.st_size > LIMIT:
        return None
    with path.open('rb') as stream:
        import os
        before = os.fstat(stream.fileno())
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns):
            raise ValueError('file changed before reading')
        data = stream.read(LIMIT + 1)
        after = os.fstat(stream.fileno())
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) or len(data) != info.st_size:
            raise ValueError('file changed while reading')
    return data


def collect(root, output, sha, tree):
    if any(not re.fullmatch('[a-f0-9]{40}', v) for v in (sha, tree)):
        raise ValueError('invalid source identity')
    root, output = Path(root).absolute(), Path(output).absolute()
    safe._ordinary_chain(output.parent)
    if output.exists() or output.is_symlink():
        raise ValueError('output already exists')
    report = {'schema': 1, 'status': 'build-failed-not-a-candidate', 'source_sha': sha,
              'source_tree': tree, 'phase': 'configure-not-observed', 'binding': 'unverified', 'files': [], 'diagnostic_categories': [],
              'limitation': 'No raw text retained. Categories are hints, not a root-cause finding.'}
    process = root / 'b/native-kit/codemodel/process'
    receipt = None
    for name in ('configure.process.json', 'configure.stdout.bin', 'configure.stderr.bin'):
        path = process / name
        if not path.exists() and not path.is_symlink():
            report['files'].append({'name': name, 'status': 'missing'})
            continue
        data = read_checked(path)
        if data is None:
            report['files'].append({'name': name, 'status': 'over-limit-omitted'})
            continue
        report['files'].append({'name': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
        if name.endswith('.json'):
            receipt = json.loads(data)
            if receipt.get('source_sha') != sha or receipt.get('source_tree') != tree:
                raise ValueError('process source identity mismatch')
            code = receipt.get('exit_code')
            if type(code) is not int or not -2147483648 <= code <= 2147483647:
                raise ValueError('invalid process exit code')
            report['exit_code'] = code
            report['binding'] = 'receipt-identity-matched'
            report['phase'] = 'configure-observed'
        else:
            key = 'stdout_sha256' if 'stdout' in name else 'stderr_sha256'
            if receipt is None:
                continue
            if receipt.get(key) != hashlib.sha256(data).hexdigest():
                raise ValueError('stream hash mismatch')
            text = data.decode('utf-8', errors='replace')
            for label, pattern in CATEGORIES.items():
                if re.search(pattern, text, re.I):
                    report['diagnostic_categories'].append(label)
            report['cmake_error_headers'] = report.get('cmake_error_headers', 0) + len(re.findall(r'^CMake Error', text, re.M))
    report['diagnostic_categories'] = sorted(set(report['diagnostic_categories']))
    output.mkdir()
    (output / 'failure-diagnostics.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('root', 'output', 'source-sha', 'source-tree'):
        parser.add_argument('--' + key, required=True)
    args = parser.parse_args()
    try:
        collect(args.root, args.output, args.source_sha, args.source_tree)
    except Exception:
        # Do not echo exception text: paths and malformed JSON can contain secrets.
        raise SystemExit('Safe failure diagnostics could not be collected.')
