#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Run opt-in Qt launcher acceptance against a real launcher and sibling.

This injects Qt events, not OS input; screenshots need human review and do not
establish window-manager focus, input-method or native-dialog behavior.
"""
import argparse
import configparser
import hashlib
import json
import os
from pathlib import Path
import secrets
import re
import signal
import subprocess
import struct
import tempfile

INI = Path('PlotJuggler/io.plotjuggler.PlotJuggler.zh-CN.ini')
EXPECTED = {
'en_US': ('PlotJuggler 3 launcher', 'Interface language:', 'The selected language is saved when you click Start. Files and command-line options are passed to PlotJuggler.', 'Start', 'Cancel'),
'zh_CN': ('PlotJuggler 3 启动器', '界面语言：', '点击“启动”时保存所选语言。文件和命令行选项会传递给 PlotJuggler。', '启动', '取消'),
'zh_TW': ('PlotJuggler 3 啟動器', '介面語言：', '點選“啟動”時儲存所選語言。檔案和命令列選項會傳遞給 PlotJuggler。', '啟動', '取消'),
}
OPTIONS = ['English', '简体中文', '繁體中文']

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


def normalized_cancel(text):
    # Qt standard buttons may add a mnemonic, including a trailing "(&C)".
    text = re.sub(r"\s*\(&?[A-Za-z]\)$", "", text)
    return text.replace('&', '')


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
    for initial, target in [('en_US', 'zh_CN'), ('zh_CN', 'zh_TW'), ('zh_TW', 'en_US')]:
        # Every pair starts with a synthetic file created exclusively inside our fresh root.
        ini.write_text('[General]\nPreferences%3A%3Alanguage=' + initial + '\nAcceptanceSentinel=keep-this-value\n', encoding='utf-8')
        for scenario in ('start-' + target, 'cancel'):
            case = root / ('case-' + initial + '-' + scenario)
            before = digest(ini)
            marker = {'schema': 1, 'purpose': 'launcher-gui-acceptance', 'nonce': nonce,
                      'ini': INI.as_posix(), 'before_sha256': before}
            (root / 'launcher-acceptance.json').write_text(json.dumps(marker), encoding='utf-8')
            args = [str(launcher), '--config-dir', str(config), '--self-test-launcher-ui', str(case),
                    '--launcher-test-scenario', scenario, '--launcher-test-nonce', nonce]
            if scenario != 'cancel':
                args += ['--help', '--', '中文 文件 sample', '--self-test-launcher-ui=payload', '--launcher-test-scenario']
            item = {'initial': initial, 'scenario': scenario, 'output': str(case)}
            try:
                code = run_owned(args, root, a.timeout, item)
                require(code == 0, 'launcher exit code ' + str(code))
                report = json.loads((case / 'report.json').read_text(encoding='utf-8'))
                shown = initial if scenario != 'cancel' else target
                expected = EXPECTED[shown]
                require(report['initial'] == shown, 'initial locale mismatch')
                require(report['title'] == expected[0], 'title mismatch')
                require(expected[1] in report['labels'] and expected[2] in report['labels'], 'label mismatch')
                require(report['start'] == expected[3], 'Start text mismatch')
                require(normalized_cancel(report['cancel']) == expected[4], 'Cancel text mismatch')
                require(report['options'] == OPTIONS, 'language options mismatch')
                require(report['selected'] == target, 'selected locale mismatch')
                require(report['width'] > 0 and report['height'] > 0 and report['dpr'] > 0, 'invalid dimensions or DPR')
                if a.expected_version is not None:
                    require('PlotJuggler ' + a.expected_version in report['labels'], 'version label mismatch')
                if a.expected_platform is not None:
                    require(report['platform'] == a.expected_platform, 'platform mismatch')
                for name in ('before.png', 'after.png'):
                    png = (case / name).read_bytes()
                    require(len(png) > 24 and png[:8] == b'\x89PNG\r\n\x1a\n', 'invalid PNG ' + name)
                    width, height = struct.unpack('>II', png[16:24])
                    require(width > 0 and height > 0, 'empty PNG ' + name)
                child = case / 'child-started.json'
                if scenario == 'cancel':
                    require(not child.exists(), 'Cancel started a child')
                else:
                    child_info = json.loads(child.read_text(encoding='utf-8'))
                    require(Path(child_info['cwd']) == root, 'child cwd mismatch')
                    expected_args = ['--config-dir', str(config), '--help', '--language=' + target,
                                     '--', '中文 文件 sample', '--self-test-launcher-ui=payload', '--launcher-test-scenario']
                    require(child_info['arguments'] == expected_args, 'child arguments mismatch')
                    item['child'] = child_info
                values = read_ini(ini)
                require(values['Preferences%3A%3Alanguage'] == target, 'saved language mismatch')
                require(values['AcceptanceSentinel'] == 'keep-this-value', 'sentinel changed')
                if scenario == 'cancel':
                    require(digest(ini) == before, 'Cancel changed settings')
                require(digest(external) == external_hash, 'external sentinel changed')
                item['report'] = report
                item['passed'] = True
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
