#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Offline regressions for native input/result gates and package source identity."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shlex
import shutil
import struct
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest import mock
import urllib.error
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'packaging/localization'))


def load(name):
    spec = importlib.util.spec_from_file_location('feedback_test_'+name, ROOT/'packaging/localization'/(name+'.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fixtures = load('prepare_feedback_tests')
gate = load('audit_feedback_results')
payload = load('prepare_payload')
manifest = load('create_release_manifest')


def elf():
    data = bytearray(64)
    data[:6] = b'\x7fELF\x02\x01'
    struct.pack_into('<H', data, 18, 62)
    return bytes(data)


class FixtureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source, self.build, self.output = [self.root/n for n in ['source', 'build', 'inputs']]
        (self.source/'packaging/localization').mkdir(parents=True)
        (self.source/'docs/localization').mkdir(parents=True)
        (self.build/'ardupilot-dataflash').mkdir(parents=True)
        self.apbin = self.build/'ardupilot.so'
        self.apbin.write_bytes(elf())
        (self.build/'ardupilot-package-path-Release.txt').write_text(str(self.apbin), encoding='utf-8')
        info = {'id': 'ardupilot-dataflash', 'version': '1.2.0-pj4.rc.1', 'license': 'LGPL-3.0-only'}
        (self.build/'ardupilot-dataflash/ardupilot_source_plugin.pjmanifest.json').write_text(json.dumps(info), encoding='utf-8')
        (self.source/'docs/localization/upstream-baseline.json').write_text(json.dumps({'ardupilot_plugin': {**info, 'commit': 'f'*40}}), encoding='utf-8')
        self.archive = self.root/'fft.zip'
        self.write_archive()

    def write_archive(self, extra=None):
        with zipfile.ZipFile(self.archive, 'w') as zipped:
            zipped.writestr('toolbox-fft/manifest.json', json.dumps({'id': 'toolbox-fft', 'version': '1.0.1'}))
            zipped.writestr('toolbox-fft/fft.so', elf())
            if extra:
                zipped.writestr(extra, 'synthetic')
        spec = {'url': 'https://github.com/PlotJuggler/pj-official-plugins/releases/download/synthetic/fixture.zip',
                'checksum': 'sha256:'+hashlib.sha256(self.archive.read_bytes()).hexdigest()}
        self.lock = self.source/'packaging/localization/registry-lock.json'
        self.lock.write_text(json.dumps({'extensions': [{'id': 'toolbox-fft', 'version': '1.0.1',
            'platforms': {'linux-x86_64': spec, 'windows-x86_64': spec}}]}), encoding='utf-8')

    def prepare(self, platform='linux-x86_64'):
        with mock.patch.object(fixtures.download_retry.urllib.request, 'urlopen', side_effect=AssertionError('No test network')):
            return fixtures.prepare(self.source, self.build, self.output, 'Release', platform, self.archive)

    def test_exact_two_inputs_and_external_identity(self):
        record = self.prepare()
        self.assertEqual({p.name for p in self.output.iterdir()}, {'ardupilot-dataflash', 'toolbox-fft'})
        self.assertTrue(self.output.with_name('inputs-identity.json').is_file())
        for row in record['files']:
            self.assertEqual(hashlib.sha256((self.output/row['path']).read_bytes()).hexdigest(), row['sha256'])

    def test_network_retry_keeps_locked_url_bound_and_platform_validation(self):
        for platform in ('linux-x86_64', 'windows-x86_64'):
            with self.subTest(platform=platform):
                self.output = self.root / ('inputs-' + platform)
                if platform == 'windows-x86_64':
                    pe = bytearray(128)
                    pe[:2] = b'MZ'
                    struct.pack_into('<I', pe, 60, 64)
                    pe[64:68] = b'PE\0\0'
                    struct.pack_into('<H', pe, 68, 0x8664)
                    self.apbin = self.build/'ardupilot.dll'
                    self.apbin.write_bytes(pe)
                    (self.build/'ardupilot-package-path-Release.txt').write_text(str(self.apbin), encoding='utf-8')
                    with zipfile.ZipFile(self.archive, 'w') as zipped:
                        zipped.writestr('toolbox-fft/manifest.json', json.dumps({'id': 'toolbox-fft', 'version': '1.0.1'}))
                        zipped.writestr('toolbox-fft/fft.dll', pe)
                    lock = json.loads(self.lock.read_text(encoding='utf-8'))
                    lock['extensions'][0]['platforms'][platform]['checksum'] = 'sha256:' + hashlib.sha256(self.archive.read_bytes()).hexdigest()
                    self.lock.write_text(json.dumps(lock), encoding='utf-8')
                spec = json.loads(self.lock.read_text(encoding='utf-8'))['extensions'][0]['platforms'][platform]
                raw = self.archive.read_bytes()
                response = io.BytesIO(raw)
                error = urllib.error.HTTPError(spec['url'], 503, 'unavailable', {}, None)
                with mock.patch.object(fixtures.download_retry.urllib.request, 'urlopen',
                                       side_effect=[error, TimeoutError(), response]) as fetch, \
                     mock.patch.object(response, 'read', wraps=response.read) as read, \
                     mock.patch.object(fixtures.download_retry.time, 'sleep') as sleep:
                    record = fixtures.prepare(self.source, self.build, self.output, 'Release', platform)
                self.assertEqual(fetch.call_args_list, [mock.call(spec['url'], timeout=120)] * 3)
                read.assert_called_once_with(32*1024*1024+1)
                self.assertEqual(sleep.call_args_list, [mock.call(2), mock.call(4)])
                self.assertEqual(record['fft_url'], spec['url'])
                self.assertEqual(record['fft_archive_sha256'], spec['checksum'].removeprefix('sha256:'))
                self.assertEqual(record['platform'], platform)
                self.assertEqual({p.name for p in self.output.iterdir()}, {'ardupilot-dataflash', 'toolbox-fft'})

    def test_network_checksum_and_size_failure_are_not_retried(self):
        for raw, message in ((b'wrong bytes', 'checksum'), (b'x' * (32*1024*1024+1), 'too large')):
            with self.subTest(message=message), \
                 mock.patch.object(fixtures.download_retry.urllib.request, 'urlopen', return_value=io.BytesIO(raw)) as fetch, \
                 mock.patch.object(fixtures.download_retry.time, 'sleep') as sleep:
                with self.assertRaisesRegex(ValueError, message):
                    fixtures.prepare(self.source, self.build, self.output, 'Release', 'linux-x86_64')
                self.assertEqual(fetch.call_count, 1)
                sleep.assert_not_called()
                self.assertFalse(self.output.exists())
                self.assertFalse(self.output.with_name('inputs-identity.json').exists())

    def test_network_archive_platform_failure_is_not_retried(self):
        with mock.patch.object(fixtures.download_retry.urllib.request, 'urlopen',
                               return_value=io.BytesIO(self.archive.read_bytes())) as fetch, \
             mock.patch.object(fixtures.download_retry.time, 'sleep') as sleep:
            with self.assertRaisesRegex(ValueError, 'platform'):
                fixtures.prepare(self.source, self.build, self.output, 'Release', 'windows-x86_64')
        self.assertEqual(fetch.call_count, 1)
        sleep.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_network_timeout_exhaustion_leaves_no_fixture_or_identity(self):
        with mock.patch.object(fixtures.download_retry.urllib.request, 'urlopen', side_effect=TimeoutError()) as fetch, \
             mock.patch.object(fixtures.download_retry.time, 'sleep') as sleep:
            with self.assertRaises(TimeoutError):
                fixtures.prepare(self.source, self.build, self.output, 'Release', 'linux-x86_64')
        self.assertEqual(fetch.call_count, 3)
        self.assertEqual(sleep.call_args_list, [mock.call(2), mock.call(4)])
        self.assertFalse(self.output.exists())
        self.assertFalse(self.output.with_name('inputs-identity.json').exists())

    def test_wrong_checksum_stops_before_output(self):
        self.archive.write_bytes(self.archive.read_bytes()+b'changed')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_wrong_platform_stops_before_output(self):
        with self.assertRaisesRegex(ValueError, 'platform'):
            self.prepare('windows-x86_64')
        self.assertFalse(self.output.exists())

    def test_unsafe_archive_path_rejected(self):
        self.write_archive('toolbox-fft/../escape')
        with self.assertRaisesRegex(ValueError, 'archive path'):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_windows_archive_separator_and_drive_rejected(self):
        for name in ['toolbox-fft/..\\escape.dll', 'toolbox-fft/C:escape.dll']:
            with self.subTest(name=name):
                self.write_archive(name)
                with self.assertRaisesRegex(ValueError, 'archive path'):
                    self.prepare()
                self.assertFalse(self.output.exists())

    def test_wrong_apbin_manifest_rejected(self):
        path = self.build/'ardupilot-dataflash/ardupilot_source_plugin.pjmanifest.json'
        data = json.loads(path.read_text(encoding='utf-8')); data['version'] = 'wrong'
        path.write_text(json.dumps(data), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'APBIN manifest'):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_does_not_overwrite_existing_inputs(self):
        self.output.mkdir(); (self.output/'keep').write_bytes(b'unrelated')
        with self.assertRaisesRegex(ValueError, 'new isolated'):
            self.prepare()
        self.assertEqual((self.output/'keep').read_bytes(), b'unrelated')

    def test_does_not_overwrite_existing_identity(self):
        identity = self.output.with_name('inputs-identity.json')
        identity.write_bytes(b'previous evidence')
        with self.assertRaisesRegex(ValueError, 'new isolated'):
            self.prepare()
        self.assertEqual(identity.read_bytes(), b'previous evidence')
        self.assertFalse(self.output.exists())


class SourceIdentityTests(unittest.TestCase):
    def test_clean_source_has_exact_commit_and_tree(self):
        with mock.patch.object(payload.subprocess, 'check_output', side_effect=['', 'a'*40+'\n', 'b'*40+'\n']):
            self.assertEqual(payload.require_clean_source(), ('a'*40, 'b'*40))

    def test_dirty_source_stops_before_any_copy_or_download(self):
        for status in [' M pj_app/main.cpp\n', 'M  pj_app/main.cpp\n', '?? added.cpp\n', ' m 3rdparty/plugin\n']:
            with self.subTest(status=status), tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp)/'payload'
                with mock.patch.object(payload.subprocess, 'check_output', return_value=status), \
                     mock.patch.object(payload, 'download', side_effect=AssertionError('Must not download')):
                    with self.assertRaisesRegex(ValueError, 'clean committed'):
                        payload.stage(Path(tmp)/'missing-build', out, 'Release', False)
                self.assertFalse(out.exists())


class EvidenceTests(unittest.TestCase):
    def root(self):
        root = ET.Element('testsuite')
        for name in sorted(gate.EXPECTED):
            case = ET.SubElement(root, 'testcase', name=name, status='run')
            marker = 'PluginDisplayMetadataTest::installedApbin()' if name == 'PluginDisplayMetadataTest' else 'PluginFeedbackTest::mainWindowFlow()'
            ET.SubElement(case, 'system-out').text = f'PASS   : {marker}\nTotals: 3 passed, 0 failed, 0 skipped, 0 blacklisted, 1ms\n'
        return root

    def test_required_cases_accepted(self):
        self.assertEqual(len(gate.audit_cases(self.root())), 4)

    def test_skip_hidden_inside_ctest_success_rejected(self):
        root = self.root(); root[0].find('system-out').text = root[0].findtext('system-out').replace('0 skipped', '1 skipped')
        with self.assertRaisesRegex(ValueError, 'failures/skips'):
            gate.audit_cases(root)

    def test_missing_traditional_chinese_rejected(self):
        root = self.root(); root.remove(next(c for c in root if c.get('name').endswith('zh_TW')))
        with self.assertRaisesRegex(ValueError, 'Missing required'):
            gate.audit_cases(root)

    def test_truncation_rejected_even_with_visible_pass_and_totals(self):
        root = self.root()
        root[0].find('system-out').text += (
            '[This part of the test output was removed since it exceeds the threshold of 1024 bytes.]')
        with self.assertRaisesRegex(ValueError, 'truncated CTest output'):
            gate.audit_cases(root)


@unittest.skipUnless(all(shutil.which(tool) for tool in ('cmake', 'ctest', 'bash')),
                     'CMake, CTest and Bash are required')
class WorkflowExecutionTests(unittest.TestCase):
    """Execute the checked-in shell steps with real CTest and synthetic runners.

    Discovery needs two simulated runtime paths, just as PRE_TEST executables
    need their DLL search paths. No native plugin, GUI, compiler or network runs.
    """

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='feedback ctest ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.build = self.root/'build'
        self.build.mkdir()
        self.screens = self.build/'gui-acceptance'
        self.screens.mkdir()
        png = b'\x89PNG\r\n\x1a\n' + struct.pack('>I', 13) + b'IHDR' + struct.pack('>II', 1, 1) + bytes(9)
        for language in gate.LANGUAGES:
            for stage in gate.STAGES:
                (self.screens/f'full-{stage}-{language}.png').write_bytes(png)
        scripts = self.root/'packaging/localization'
        scripts.mkdir(parents=True)
        shutil.copyfile(ROOT/'packaging/localization/audit_feedback_results.py',
                        scripts/'audit_feedback_results.py')
        ci_scripts = self.root/'scripts/ci'
        ci_scripts.mkdir(parents=True)
        shutil.copyfile(ROOT/'scripts/ci/merge_ctest_reports.py', ci_scripts/'merge_ctest_reports.py')
        for dependency in ('ffmpeg', 'python'):
            (self.build/f'pj_{dependency}_bin_dirs.txt').write_text(
                f'fixture-runtime-{dependency}\n', encoding='utf-8')
        self.runner = self.root/'synthetic_qt.py'
        self.runner.write_text(textwrap.dedent("""\
            import os
            from pathlib import Path
            import sys
            if os.environ.get('RUNNER_OS') == 'Windows':
                for dependency in ('ffmpeg', 'python'):
                    if 'fixture-runtime-' + dependency not in os.environ['PATH']:
                        raise SystemExit('Missing simulated runtime path: ' + dependency)
            if sys.argv[1] == '--discover':
                raise SystemExit(0)
            if sys.argv[1] == '--gtest-fixture':
                if os.environ.get('RUNNER_OS') == 'Windows':
                    qpa = os.environ.get('QT_QPA_PLATFORM')
                    if sys.argv[2] == 'native':
                        assert qpa == 'windows', qpa
                        assert os.environ.get('PJ_REQUIRE_GPU_TESTS') == '1'
                    elif sys.argv[2] == 'ordinary':
                        assert qpa is None, qpa
                    else:
                        assert qpa in (None, 'windows'), qpa
                print('[  PASSED  ] 1 test.')
                raise SystemExit(0)
            # Model a Qt process whose console output is absent on Windows.
            # Only its explicit file logger makes the result observable.
            if '-o' in sys.argv:
                output = sys.argv[sys.argv.index('-o') + 1]
                assert output.endswith(',txt')
                Path(output[:-4]).write_text(
                    ('QDEBUG: synthetic fixture output ' + 'x' * 80 + '\\n') * 40 +
                    'PASS   : ' + sys.argv[1] + '\\n' +
                    'Totals: 3 passed, 0 failed, 0 skipped, 0 blacklisted, 1ms\\n',
                    encoding='utf-8')
            """), encoding='utf-8')
        # CTest evaluates this include during --show-only as well as execution.
        python = Path(sys.executable).as_posix()
        runner = self.runner.as_posix()
        discovery = [
            f'execute_process(COMMAND [==[{python}]==] [==[{runner}]==] --discover RESULT_VARIABLE result)',
            'if(NOT result EQUAL 0)',
            '  message(FATAL_ERROR "Synthetic PRE_TEST discovery lacks runtime paths")',
            'endif()',
        ]
        discovery_file = self.root/'runtime-discovery.cmake'
        discovery_file.write_text('\n'.join(discovery)+'\n', encoding='utf-8')
        commands = [
            'cmake_minimum_required(VERSION 3.22)',
            'project(SyntheticQtEvidence NONE)',
            'enable_testing()',
            'add_executable(synthetic_qt IMPORTED GLOBAL)',
            f'set_target_properties(synthetic_qt PROPERTIES IMPORTED_LOCATION [==[{python}]==])',
            f'include([==[{(ROOT/"cmake/PjQtTestLog.cmake").as_posix()}]==])',
            f'set_property(DIRECTORY PROPERTY TEST_INCLUDE_FILES [==[{discovery_file.as_posix()}]==])',
        ]
        for name in sorted(gate.EXPECTED):
            marker = ('PluginDisplayMetadataTest::installedApbin()' if name == 'PluginDisplayMetadataTest'
                      else 'PluginFeedbackTest::mainWindowFlow()')
            commands.append(f'pj_add_logged_qt_test({name} synthetic_qt TIMEOUT 15 '
                            f'ARGS [==[{runner}]==] "{marker}")')
        # The actual Windows step now partitions QRhi and unlabelled window
        # lifecycle cases, then repeats exact portability cases under native QPA.
        from test_ctest_report_merge import gate as native_gate
        extra = {name: 'either' for name in native_gate.NATIVE_CASES}
        extra.update({
            'synthetic_qrhi.d3d11.Frame': 'native',
            'pj_app_gui_tests.MainWindowRhiWindowTest.FirstGpuWidgetKeepsTheNativeWindow': 'native',
            'pj_app_gui_tests.MainWindowRhiWindowTest.WithoutTheGpuCanvasQtRecreatesTheNativeWindow': 'native',
            'OrdinaryWidget.Fixture': 'ordinary',
        })
        for name, mode in extra.items():
            commands.append(f'add_test(NAME {name} COMMAND [==[{python}]==] [==[{runner}]==] --gtest-fixture {mode})')
        commands.append('set_tests_properties(synthetic_qrhi.d3d11.Frame PROPERTIES LABELS qrhi-d3d11)')
        source = self.root/'source'
        source.mkdir()
        (source/'CMakeLists.txt').write_text('\n'.join(commands)+'\n', encoding='utf-8')
        # Both emulated workflow branches share a single-config fixture. In
        # particular, a Windows host must not silently select Visual Studio
        # for the Linux branch, whose real build does not need ctest -C.
        result = subprocess.run([shutil.which('cmake'), '-G', 'Ninja',
                                 '-S', str(source), '-B', str(self.build),
                                 '-DPython3_EXECUTABLE=' + sys.executable],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_real_multi_config_registration_with_explicit_configuration(self):
        build = self.root/'multi-config'
        result = subprocess.run([shutil.which('cmake'), '-G', 'Ninja Multi-Config',
                                 '-S', str(self.root/'source'), '-B', str(build),
                                 '-DPython3_EXECUTABLE=' + sys.executable],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = self.root/'multi-config.xml'
        result = subprocess.run([shutil.which('ctest'), '--test-dir', str(build), '-C', 'Release',
                                 '--test-output-size-passed', '262144', '--output-junit', str(report)],
                                env={**os.environ, 'RUNNER_OS': 'Linux'},
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(gate.audit_cases(ET.parse(report).getroot(), allow_other_cases=True)), 4)

    def ctest(self, *args, runner_os='Linux'):
        return subprocess.run([shutil.which('ctest'), '--test-dir', str(self.build), *args],
                              env={**os.environ, 'RUNNER_OS': runner_os}, capture_output=True,
                              text=True, timeout=30)

    def test_real_ctest_truncation_rejected(self):
        report = self.root/'truncated.xml'
        result = self.ctest('--test-output-size-passed', '1024', '--output-junit', str(report))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        with self.assertRaisesRegex(ValueError, 'truncated CTest output'):
            gate.audit_cases(ET.parse(report).getroot(), allow_other_cases=True)

    def test_discovery_without_runtime_environment_fails(self):
        result = self.ctest('--show-only=json-v1', runner_os='Windows')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Synthetic PRE_TEST discovery lacks runtime paths', result.stderr)

    def test_empty_console_without_file_relay_is_rejected(self):
        commands = []
        for name in sorted(gate.EXPECTED):
            marker = ('PluginDisplayMetadataTest::installedApbin()' if name == 'PluginDisplayMetadataTest'
                      else 'PluginFeedbackTest::mainWindowFlow()')
            commands.append(f'add_test({name} [==[{Path(sys.executable).as_posix()}]==] '
                            f'[==[{self.runner.as_posix()}]==] "{marker}")')
        (self.build/'CTestTestfile.cmake').write_text('\n'.join(commands)+'\n', encoding='utf-8')
        report = self.root/'empty-console.xml'
        result = self.ctest('--output-junit', str(report))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        with self.assertRaisesRegex(ValueError, 'missing or ambiguous Qt result summary'):
            gate.audit_cases(ET.parse(report).getroot(), allow_other_cases=True)

    def test_workflows_preserve_runtime_and_complete_evidence(self):
        for workflow in ('zh-4x-ci.yml', 'zh-4x-packages.yml'):
            content = (ROOT/'.github/workflows'/workflow).read_text(encoding='utf-8')
            marker = '      - name: Run native tests\n        run: |\n'
            self.assertEqual(content.count(marker), 1)
            body = textwrap.dedent(content.split(marker)[1].split('\n      - ', 1)[0])
            body = body.replace('${{ matrix.qt_arch }}', 'fixture')
            # Run the actual step. Only platform path conversion and the GUI
            # wrapper are replaced; CTest, discovery and the auditor are real.
            wrapper = (
                'set -euo pipefail\n'
                f'python() {{ command {shlex.quote(Path(sys.executable).as_posix())} "$@"; }}\n'
                'cygpath() { printf "%s\\n" "$2"; }\n'
                'xvfb-run() { shift; "$@"; }\n'
            )
            for platform in ('Linux', 'Windows'):
                with self.subTest(workflow=workflow, platform=platform):
                    result = subprocess.run([shutil.which('bash'), '-c', wrapper + body],
                                            cwd=self.root, env={**os.environ, 'RUNNER_OS': platform,
                                                               'PJ_QT_VERSION': 'fixture'},
                                            capture_output=True, text=True, timeout=30)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    report = json.loads((self.build/'feedback-results.json').read_text(encoding='utf-8'))
                    self.assertEqual(report['required_ctest_cases'], 4)
                    self.assertEqual(len(report['images']), 24)
                    for case in report['cases']:
                        self.assertEqual(case['qt_passed_including_init_cleanup'], 3)


    def test_nonzero_ctest_exit_cannot_hide_behind_passing_xml(self):
        content = (ROOT/'.github/workflows/zh-4x-ci.yml').read_text(encoding='utf-8')
        marker = '      - name: Run native tests\n        run: |\n'
        body = textwrap.dedent(content.split(marker)[1].split('\n      - ', 1)[0])
        body = body.replace('${{ matrix.qt_arch }}', 'fixture')
        ctest = shlex.quote(shutil.which('ctest'))
        wrapper = (
            'set -euo pipefail\n'
            f'python() {{ command {shlex.quote(Path(sys.executable).as_posix())} "$@"; }}\n'
            'cygpath() { printf "%s\\n" "$2"; }\n'
            f'ctest() {{ command {ctest} "$@"; result=$?; '
            'if [[ " $* " == *" --output-junit "* ]]; then return 42; fi; return "$result"; }\n'
            'export -f ctest\n'
        )
        result = subprocess.run([shutil.which('bash'), '-c', wrapper + body], cwd=self.root,
                                env={**os.environ, 'RUNNER_OS': 'Windows', 'PJ_QT_VERSION': 'fixture'},
                                capture_output=True, text=True, timeout=30)
        self.assertNotEqual(result.returncode, 0)
        # env -u invokes the actual ordinary ctest; the native commands are
        # wrapped and report nonzero after their real all-passing XML exists.
        report = ET.parse(self.build/'native-tests.xml').getroot()
        self.assertEqual(report.get('failures'), '0')
        self.assertFalse((self.build/'feedback-results.json').exists())


class VulkanWorkflowSetupTests(unittest.TestCase):
    def test_lavapipe_is_prepared_before_native_test_execution(self):
        for workflow in ('zh-4x-ci.yml', 'zh-4x-packages.yml'):
            with self.subTest(workflow=workflow):
                content = (ROOT/'.github/workflows'/workflow).read_text(encoding='utf-8')
                setup = content.split('      - name: Linux build dependencies\n', 1)[1].split('\n      - ', 1)[0]
                self.assertIn("if: runner.os == 'Linux'", setup)
                self.assertIn('mesa-vulkan-drivers libvulkan-dev', setup)
                selection = setup.index('VK_ICD_FILENAMES="$(ls /usr/share/vulkan/icd.d/lvp_icd*.json')
                validation = setup.index('test -f "${VK_ICD_FILENAMES}"')
                persistence = setup.index('>> "$GITHUB_ENV"')
                self.assertLess(setup.index('sudo apt-get install'), selection)
                self.assertLess(selection, validation)
                self.assertLess(validation, persistence)
                self.assertIn("printf 'VK_ICD_FILENAMES=%s\\n'", setup)
                native = content.split('      - name: Run native tests\n', 1)[1].split('\n      - ', 1)[0]
                self.assertNotIn('/usr/share/vulkan', native)
                self.assertIn('PJ_REQUIRE_GPU_TESTS=1 xvfb-run -a ctest', native)


class PackageLanguagesTests(unittest.TestCase):
    def run_manifest(self, languages, png_languages):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); old = Path.cwd()
            try:
                os.chdir(root)
                Path('versions.env').write_text('PJ_APP_VERSION=4.0.0-zh.1.rc.4\n', encoding='utf-8')
                for relative, (platform, kind) in manifest.REPORT_IDENTITIES.items():
                    i = 0 if platform == 'windows-2022' else 1
                    directory = (root/'reports'/relative).parent; directory.mkdir(parents=True)
                    report = {'status': 'automated_checks_passed', 'languages': languages,
                              'release': {'source_commit': 'a'*40, 'source_tree': 'b'*40, 'version': '4.0.0-zh.1.rc.4'},
                              'plugin_count': 19 if i==0 else 21, 'loaded_plugin_count': 19 if i==0 else 20,
                              'unavailable_plugins': [] if i==0 else [{'id': 'ros2-topic-subscriber', 'status': 'not_tested_missing_external_dependency'}],
                              'checks': ['synthetic test']}
                    (directory/'acceptance.json').write_text(json.dumps(report), encoding='utf-8')
                    for language in png_languages:
                        (directory/f'gui-{language}.png').write_bytes(b'synthetic-size-check-only'*500)
                    if i == 0:
                        suffix = 'portable-zh-CN.zip' if kind == 'portable' else 'zh-CN.exe'
                        name = 'PlotJuggler-4.0.0-zh.1.rc.4-Windows-x64-' + suffix
                        digest = manifest.hashlib.sha256(b'synthetic package').hexdigest()
                        (directory/'package-integrity.json').write_text(json.dumps({
                            'format': kind, 'name': name, 'before': digest, 'after': digest}), encoding='utf-8')
                Path('candidate').mkdir()
                for name in ['PlotJuggler-4.0.0-zh.1.rc.4-Windows-x64-zh-CN.exe',
                             'PlotJuggler-4.0.0-zh.1.rc.4-Windows-x64-portable-zh-CN.zip',
                             'PlotJuggler-4.0.0-zh.1.rc.4-x86_64-zh-CN.AppImage',
                             'plotjuggler4_4.0.0~zh.1~rc.4-1_amd64-zh-CN.deb']:
                    (Path('candidate')/name).write_bytes(b'synthetic package')
                (Path('candidate')/'SHA256SUMS-test.txt').write_text(''.join(
                    f'{manifest.sha256(p)}  {p.name}\n' for p in sorted(Path('candidate').iterdir())), encoding='utf-8')
                with mock.patch.dict(os.environ, {'GITHUB_SHA':'a'*40,'GITHUB_WORKFLOW_SHA':'c'*40,'GITHUB_RUN_ID':'1','GITHUB_RUN_ATTEMPT':'1'}), \
                     mock.patch.object(manifest.subprocess, 'check_output', return_value='b'*40):
                    manifest.main()
                return json.loads(Path('release-manifest.json').read_text(encoding='utf-8'))
            finally:
                os.chdir(old)

    def test_six_reports_require_eighteen_language_screenshots(self):
        result = self.run_manifest(['zh_CN','zh_TW','en_US'], ['zh_CN','zh_TW','en_US'])
        self.assertEqual(len(result['screenshots']), 18)

    def test_old_two_language_reports_rejected(self):
        with self.assertRaisesRegex(AssertionError, 'Incomplete language'):
            self.run_manifest(['zh_CN','en_US'], ['zh_CN','en_US'])

    def test_missing_traditional_screenshot_rejected(self):
        with self.assertRaises(FileNotFoundError):
            self.run_manifest(['zh_CN','zh_TW','en_US'], ['zh_CN','en_US'])


if __name__ == '__main__':
    unittest.main()
