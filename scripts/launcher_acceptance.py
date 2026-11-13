#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Run opt-in Qt launcher acceptance against a real launcher and sibling.

Verifies the default launcher path, child forwarding, and isolated settings.
Main-window language menu behavior is covered by the separate UI acceptance.
"""
import argparse
import configparser
import hashlib
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import tempfile

INI = Path('PlotJuggler/io.plotjuggler.PlotJuggler.zh-CN.ini')
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else 'missing'

def read_ini(path):
    parser = configparser.RawConfigParser(interpolation=None, strict=False)
    parser.optionxform = str
    parser.read(path, encoding='utf-8')
    return dict(parser['General'])

def require(condition, message):
    if not condition:
        raise AssertionError(message)


def run_owned(args, cwd, timeout, item):
    process = subprocess.Popen(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, encoding='utf-8', errors='replace',
                               start_new_session=(os.name != 'nt'))
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        item['timeout'] = True
        if os.name == 'nt':
            if process.poll() is None:
                try:
                    result = subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                                            capture_output=True, text=True, timeout=10)
                    item['termination'] = {'method': 'taskkill-tree', 'exit_code': result.returncode}
                    if result.returncode and process.poll() is None:
                        process.kill()
                        item['termination']['fallback'] = 'launcher-kill'
                except (OSError, subprocess.TimeoutExpired) as exc:
                    item['termination'] = {'method': 'taskkill-tree', 'error': str(exc)}
                    if process.poll() is None:
                        process.kill()
                        item['termination']['fallback'] = 'launcher-kill'
            else:
                item['termination'] = {'method': 'none', 'reason': 'launcher already exited; child state unknown'}
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
                item['termination'] = {'method': 'owned-process-group', 'signal': 'SIGKILL'}
            except ProcessLookupError:
                item['termination'] = {'method': 'owned-process-group', 'result': 'already exited'}
            except OSError as exc:
                item['termination'] = {'method': 'owned-process-group', 'error': str(exc)}
                if process.poll() is None:
                    process.kill()
                    item['termination']['fallback'] = 'launcher-kill'
        try:
            stdout, stderr = process.communicate(timeout=10)
            item['exit_code'] = process.returncode
            item['stderr'] = stderr[-4000:]
        except subprocess.TimeoutExpired:
            item['termination']['result'] = 'pipes still open after termination'
            process.stdout.close()
            process.stderr.close()
        raise AssertionError('launcher timed out')
    item.update(exit_code=process.returncode, stderr=stderr[-4000:])
    return process.returncode


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--launcher', required=True, type=Path)
    p.add_argument('--out-base', required=True, type=Path)
    p.add_argument('--timeout', type=float, default=30)
    p.add_argument('--expected-version')
    p.add_argument('--expected-platform')
    a = p.parse_args()
    launcher = a.launcher.resolve(strict=True)
    base = a.out_base.resolve(strict=True)
    root = Path(tempfile.mkdtemp(prefix='launcher GUI 验收 ', dir=base))
    nonce = secrets.token_hex(32)
    config = root / 'config'
    ini = config / INI
    ini.parent.mkdir(parents=True)
    external = root / 'external-sentinel.ini'
    external.write_text('external sentinel\n', encoding='utf-8')
    external_hash = digest(external)
    results = []
    for initial in ('en_US', 'zh_CN', 'zh_TW'):
        # Every case uses a fresh, isolated synthetic configuration.
        ini.write_text('[General]\nPreferences%3A%3Alanguage=' + initial +
                       '\nAcceptanceSentinel=keep-this-value\n', encoding='utf-8')
        case = root / ('case-' + initial)
        before = digest(ini)
        marker = {'schema': 1, 'purpose': 'launcher-gui-acceptance', 'nonce': nonce,
                  'ini': INI.as_posix(), 'before_sha256': before}
        (root / 'launcher-acceptance.json').write_text(json.dumps(marker), encoding='utf-8')
        forwarded = ['--config-dir', str(config), '--help', '--language=zh_Hant_HK',
                     '--', '中文 文件 sample', '--self-test-launcher-ui=payload', '--launcher-test-scenario']
        args = [str(launcher), '--config-dir', str(config), '--self-test-launcher-ui', str(case),
                '--launcher-test-scenario', 'start', '--launcher-test-nonce', nonce, *forwarded[2:]]
        item = {'initial': initial, 'scenario': 'start', 'output': str(case)}
        try:
            code = run_owned(args, root, a.timeout, item)
            require(code == 0, 'launcher exit code ' + str(code))
            child_info = json.loads((case / 'child-started.json').read_text(encoding='utf-8'))
            require(Path(child_info['cwd']) == root, 'child cwd mismatch')
            require(child_info['arguments'] == forwarded, 'child arguments mismatch')
            require(Path(child_info['program']).parent == launcher.parent, 'child is not bundled sibling')
            if a.expected_version is not None:
                require(child_info['version'] == a.expected_version, 'version mismatch')
            if a.expected_platform is not None:
                require(child_info['platform'] == a.expected_platform, 'platform mismatch')
            values = read_ini(ini)
            require(values['Preferences%3A%3Alanguage'] == initial, 'session language was saved')
            require(values['AcceptanceSentinel'] == 'keep-this-value', 'sentinel changed')
            require(digest(ini) == before, 'startup changed settings')
            require(digest(external) == external_hash, 'external sentinel changed')
            item.update(child=child_info, passed=True)
        except (AssertionError, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as exc:
            item.update(passed=False, error=str(exc))
        results.append(item)
    summary = {'runroot': str(root), 'launcher': str(launcher), 'results': results,
               'passed': all(x['passed'] for x in results), 'scope': __doc__,
               'expected_version': a.expected_version, 'expected_platform': a.expected_platform,
               'version_checked': a.expected_version is not None, 'platform_checked': a.expected_platform is not None}
    temp = root / 'summary.tmp'
    temp.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(root / 'summary.json')
    # Console encoding varies by platform; JSON escapes keep output ASCII-safe.
    print(json.dumps(summary, ensure_ascii=True, indent=2))
    return 0 if summary['passed'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
