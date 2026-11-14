# SPDX-License-Identifier: MPL-2.0
"""Isolated SDK A/B experiment, not application acceptance or production SDK."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
CASES = ('missing-directory', 'invalid-library', 'null-handle',
         'unsupported-unicode-suffix', 'scan-invalid-library', 'file-as-directory')
PINS = {'sdk': 'cc83815a1a8124d5947ed567790c3393a6cf0a5c',
        'fmt': '1be298e1bd68957e4cd352e1f676f00e07dcfb57',
        'json': '55f93686c01528224f448c19128836e7df245f72'}


def command(args, **kwargs):
    """Require successful setup; no arbitrary shell or user-provided commands."""
    return subprocess.run(args, check=True, text=True, **kwargs)


def collect(text):
    """Fail closed rather than publish unexpected probe text."""
    pattern = re.compile(r'(?:ACP=[0-9]{1,10}|case=(?:' + '|'.join(CASES) +
                         r') (?:result=(?:pass|fail)|exception=system_error code=-?[0-9]{1,10}|exception=other)|cleanup=failed)')
    lines = text.splitlines()
    if not lines or any(not pattern.fullmatch(line) for line in lines):
        raise RuntimeError('Unexpected probe output; raw output withheld')
    return lines


def main():
    if sys.platform != 'win32':
        raise RuntimeError('This experiment requires native Windows MSVC')
    root = Path.cwd()
    out = root / 'sdk-ab-evidence'
    out.mkdir(exist_ok=False)
    for name, sha in PINS.items():
        actual = command(['git', '-C', str(root / name), 'rev-parse', 'HEAD'], capture_output=True).stdout.strip()
        if actual != sha:
            raise RuntimeError('Dependency commit mismatch')
    original = root / 'sdk'
    fixed = root / 'sdk-fixed'
    shutil.copytree(original, fixed, ignore=shutil.ignore_patterns('.git'))
    catalog = Path('pj_plugins/src/plugin_catalog.cpp')
    def source_hash(path):
        return hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
    if source_hash(original / catalog) != '596ef5f1b5490463e0926528b67f64c3dd82e77ed709913f5c7dc1e3b11fc9a4':
        raise RuntimeError('Original catalog source does not match reviewed baseline')
    patch = HERE / 'sdk-source.patch'
    command(['git', '-C', str(fixed), 'apply', '--check', str(patch)])
    command(['git', '-C', str(fixed), 'apply', str(patch)])
    if source_hash(fixed / catalog) != 'daf68eb0d4c41ddfc49bcb3d1519bb4aa00024151b65c5133e5d59618bdc3a6b':
        raise RuntimeError('Patch did not produce reviewed SDK candidate')
    results = {}
    for variant, source in [('original', original), ('fixed', fixed)]:
        build = root / ('sdk-ab-build-' + variant)
        command(['cmake', '-S', str(HERE), '-B', str(build), '-G', 'Ninja',
                 '-DCMAKE_BUILD_TYPE=Release', '-DSDK_SOURCE=' + source.as_posix(),
                 '-DFMT_INCLUDE=' + (root / 'fmt/include').as_posix(),
                 '-DJSON_INCLUDE=' + (root / 'json/include').as_posix()])
        command(['cmake', '--build', str(build), '--parallel', '2'])
        exe = build / 'sdk_unicode_probe.exe'
        run = subprocess.run([str(exe), str(root / ('sdk-ab-owned-' + variant))],
                             capture_output=True, text=True, timeout=60)
        if run.stderr:
            raise RuntimeError('Unexpected stderr; raw output withheld')
        lines = collect(run.stdout)
        (out / (variant + '.txt')).write_text('\n'.join(lines) + '\n', encoding='utf-8')
        shutil.copy2(exe, out / ('sdk_unicode_' + variant + '.exe'))
        results[variant] = {'exit': run.returncode, 'markers': lines,
                            'exe_sha256': hashlib.sha256(exe.read_bytes()).hexdigest()}
        print(variant + ': ' + ', '.join(lines))
    receipt = {'purpose': 'SDK A/B experiment; not application acceptance', 'pins': PINS,
               'source_commit': command(['git', 'rev-parse', 'HEAD'], capture_output=True).stdout.strip(),
               'patch_sha256': hashlib.sha256(patch.read_bytes()).hexdigest(), 'results': results}
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    a, b = results['original'], results['fixed']
    # Expected A failure is experimental evidence, never a passing app test.
    required = [f'case={name} exception=system_error code=1113' for name in ('invalid-library', 'scan-invalid-library')]
    if (a['exit'] != 1 or not all(line in a['markers'] for line in required) or
            'ACP=1252' not in a['markers'] or 'ACP=1252' not in b['markers'] or
            b['exit'] != 0 or any(f'case={name} result=pass' not in b['markers'] for name in CASES)):
        raise RuntimeError('A/B expectation not established; inspect bounded evidence')


if __name__ == '__main__':
    main()
