#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Verify an extracted/installed final package, using only its shipped runtime."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time

FONT_SHA = '2c76254f6fc379fddfce0a7e84fb5385bb135d3e399294f6eeb6680d0365b74b'
LOG_SHA = '28dcbac522ceb75eee10f6af37b0d6e342c1dc79e2be1a9f766fe18a14336766'


def verify(prefix, executable, log, output, expected_source, expected_version, capture=False):
    """Check provenance, native plugins, Python and real BIN curve restoration."""
    prefix, executable, output = prefix.resolve(), executable.resolve(), output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    record = json.loads((prefix / 'share/plotjuggler4/release.json').read_text(encoding='utf-8'))
    assert record['source_commit'] == expected_source, 'package source differs from candidate run'
    assert record['version'] == expected_version, 'package version differs from source version'
    font = prefix / 'bin/fonts/NotoSansCJKsc-Regular.otf'
    assert hashlib.sha256(font.read_bytes()).hexdigest() == FONT_SHA
    for name in ['ardupilot-dataflash/LICENSE', 'ardupilot-dataflash/COPYING.GPL3',
                 'ardupilot-dataflash/LICENSE.APACHE2', 'ardupilot-dataflash/UPSTREAM.md',
                 'NotoSansCJK-OFL.txt', 'PlotJuggler-MPL-2.0.txt', 'Qt-LGPL.txt', 'DEPENDENCIES.json',
                 'Qt-6.11.1/HPND-sell-variant.txt',
                 'ardupilot-dataflash/dependencies/fmt-12.1.0-LICENSE.txt',
                 'ardupilot-dataflash/dependencies/fast-float-8.1.0-LICENSE.txt',
                 'ardupilot-dataflash/dependencies/nlohmann-json-3.12.0-LICENSE.txt',
                 'ardupilot-dataflash/dependencies/plotjuggler-sdk-NOTICE.txt']:
        assert (prefix / 'share/licenses' / name).is_file(), name
    notices = json.loads((prefix / 'share/licenses/DEPENDENCIES.json').read_text(encoding='utf-8'))
    for item in notices['files']:
        assert hashlib.sha256((prefix / 'share/licenses' / item['path']).read_bytes()).hexdigest() == item['sha256']
    assert hashlib.sha256(log.read_bytes()).hexdigest() == LOG_SHA, 'unexpected real BIN fixture'
    manifests = sorted((prefix / 'lib/plotjuggler/plugins').glob('*/manifest.json'))
    plugin_records = [json.loads(p.read_text(encoding='utf-8')) for p in manifests]
    bin_manifest = next(m for m in plugin_records if m['id'] == 'ardupilot-dataflash')
    assert bin_manifest['license'] == record['bin_plugin_license'] == 'LGPL-3.0-only'
    expected = [f"{m['id']}={m['version']}" for m in plugin_records]
    assert f"ardupilot-dataflash={record['bin_plugin_version']}" in expected
    assert sorted(expected) == sorted(record['expected_plugins']), expected
    assert len(expected) == (19 if os.name == 'nt' else 21), expected
    env = os.environ.copy()
    for name in ['QT_PLUGIN_PATH', 'QML2_IMPORT_PATH', 'QT_QPA_FONTDIR', 'PYTHONHOME',
                 'PYTHONPATH', 'LD_LIBRARY_PATH']:
        env.pop(name, None)
    env['PJ_DISABLE_TELEMETRY'] = '1'
    env['QT_LOGGING_RULES'] = 'pj.runtime.ingest.info=true'
    # Use the installed DLLs plus the operating system, never a Qt/Conan tree.
    if os.name == 'nt':
        system = Path(env['SystemRoot'])
        env['PATH'] = os.pathsep.join(map(str, [prefix / 'bin', system / 'System32', system]))
        for name in ['vcruntime140.dll', 'vcruntime140_1.dll', 'msvcp140.dll']:
            assert (prefix / 'bin' / name).is_file(), f'missing app-local VC runtime: {name}'
    def stop(process):
        # AppImage extract-and-run forks AppRun. Stop the whole isolated session
        # so a previous-language window cannot survive into the next capture.
        if os.name == 'nt':
            if process.poll() is None:
                process.terminate()
        else:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        try:
            process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            if os.name == 'nt':
                process.kill()
            else:
                os.killpg(process.pid, signal.SIGKILL)
            process.wait()
    def run(name, args):
        process = subprocess.Popen([str(executable), *args], env=env, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace',
                                   start_new_session=os.name != 'nt')
        try:
            stdout, stderr = process.communicate(timeout=150)
        except subprocess.TimeoutExpired:
            stop(process)
            raise
        combined = stdout + stderr
        (output / f'{name}.log').write_text(combined, encoding='utf-8')
        print(combined)
        assert process.returncode == 0, f'{name}: exit {process.returncode}'
        assert 'Failed to load bundled CJK fallback font' not in combined
        return combined
    with tempfile.TemporaryDirectory(prefix='pj4-package-') as temp:
        work = Path(temp)
        env.update(HOME=str(work), XDG_CONFIG_HOME=str(work / 'config'),
                   XDG_DATA_HOME=str(work / 'data'), XDG_CACHE_HOME=str(work / 'cache'))
        version_text = run('version', ['--version'])
        assert any(line.strip() == 'PlotJuggler4 ' + expected_version for line in version_text.splitlines()), version_text
        assert '[selftest-python] OK' in run('python', ['--selftest-python'])
        args = ['--validate-plugins', str(prefix / 'lib/plotjuggler/plugins')]
        for spec in expected:
            args.extend(['--expect-plugin', spec])
        run('plugins', args)
        shutil.copy2(log, work / '飞行日志.BIN')
        layout = work / '真实日志.pj4.xml'
        layout.write_text('''<root format="PlotJuggler" pj4_version="4" binding="source">
<tabbed_widget parent="main_window"><Tab id="t1" tab_name="BIN" containers="1">
<Container><DockArea id="a1" name="BIN"><plot id="p1" mode="TimeSeries">
<curve topic="/RCOU" field="C1&#9;[us]"/></plot></DockArea></Container></Tab></tabbed_widget>
<previouslyLoaded_Datafiles><fileInfo filename="飞行日志.BIN"><plugin ID="ArduPilot BIN"
manifest_id="ardupilot-dataflash" filepath_mode="source"><![CDATA[{}]]></plugin></fileInfo>
</previouslyLoaded_Datafiles></root>''', encoding='utf-8')
        for language in ['zh_CN', 'en_US']:
            diagnostics = output / f'bin-{language}.json'
            text = run('bin-' + language, ['--language', language, '--nosplash', '--layout', str(layout),
                       '--exit-after-layout', '--exit-after-layout-timeout', '90', '--dump-diagnostics', str(diagnostics)])
            assert 'ArduPilot BIN: imported 1940 numeric series' in text
            records = json.loads(diagnostics.read_text(encoding='utf-8'))['records']
            rejected = [x for x in records if x['level'] == 'error' or
                        x['id'] in ['layout-import-unresolved-curves', 'layout-import-unresolved-curves-sync']]
            assert not rejected, rejected
            if capture:
                with (output / f'gui-{language}.log').open('w', encoding='utf-8') as stream:
                    process = subprocess.Popen([str(executable), '--language', language, '--nosplash',
                                                '--layout', str(layout)], env=env, stdout=stream, stderr=stream,
                                                start_new_session=os.name != 'nt')
                    try:
                        time.sleep(12)
                        assert process.poll() is None, 'packaged GUI exited early'
                        png = output / f'gui-{language}.png'
                        if os.name == 'nt':
                            from PIL import ImageGrab
                            ImageGrab.grab(all_screens=True).save(png)
                        else:
                            subprocess.run(['import', '-window', 'root', str(png)], check=True, timeout=20)
                        assert png.stat().st_size > 10000, 'empty GUI screenshot'
                    finally:
                        stop(process)
    summary = {'status': 'automated_checks_passed',
               'visual_review': 'required separately for the captured Chinese and English screenshots', 'release': record, 'plugin_count': len(expected),
               'checks': ['embedded version', 'CJK font bytes', 'licenses', 'Python backend',
                          'all bundled plugins', 'real BIN in Unicode path', 'Chinese and English curve restoration']}
    (output / 'acceptance.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prefix', type=Path, required=True)
    p.add_argument('--executable', type=Path, required=True)
    p.add_argument('--real-bin', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--expected-source', required=True)
    p.add_argument('--expected-version', required=True)
    p.add_argument('--capture', action='store_true')
    a = p.parse_args()
    verify(a.prefix, a.executable, a.real_bin, a.output, a.expected_source, a.expected_version, a.capture)
