#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('csv_acceptance', ROOT / 'packaging/localization/run_csv_runtime_acceptance.py')
acceptance = importlib.util.module_from_spec(spec)
spec.loader.exec_module(acceptance)


class CsvRuntimeAcceptanceTest(unittest.TestCase):
    def configure_runtime(self, build):
        """Model CMake's exact kit and optional Conan runtime path records."""
        build.mkdir(parents=True, exist_ok=True)
        qt = build.parent / 'Qt kit 测试'
        (build / 'CMakeCache.txt').write_text(
            'Qt6_DIR:PATH=' + (qt / 'lib/cmake/Qt6').as_posix() + '\n', encoding='utf-8')
        dirs = [build.parent / 'Conan FFmpeg/bin', build.parent / 'Conan CPython/bin']
        for name, directory in zip(['pj_ffmpeg_bin_dirs.txt', 'pj_python_bin_dirs.txt'], dirs):
            (build / name).write_text('\n' + directory.as_posix() + '\r\n\n', encoding='utf-8')
        return qt, dirs

    def test_windows_runtime_uses_configured_paths_without_mutating_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            build = Path(tmp) / 'build'
            qt, dirs = self.configure_runtime(build)
            inherited = {'PATH': 'unrelated-qt;system-python', 'QT_PLUGIN_PATH': 'stale-qt/plugins',
                         'QT_QPA_FONTDIR': 'test-fonts', 'PLOTJUGGLER_UI_LANGUAGE': 'zh_TW'}
            with mock.patch.object(sys, 'platform', 'win32'), \
                 mock.patch.dict(os.environ, inherited, clear=True):
                env = acceptance.runtime_environment(build)
                self.assertEqual(dict(os.environ), inherited)
            self.assertEqual(env['PATH'].split(';'),
                             [str(qt / 'bin'), *(directory.as_posix() for directory in dirs),
                              'unrelated-qt', 'system-python'])
            self.assertEqual(env['QT_PLUGIN_PATH'], str(qt / 'plugins'))
            self.assertEqual(env['QT_QPA_FONTDIR'], inherited['QT_QPA_FONTDIR'])
            self.assertEqual(env['PLOTJUGGLER_UI_LANGUAGE'], inherited['PLOTJUGGLER_UI_LANGUAGE'])

    def test_non_windows_runtime_keeps_environment_without_reading_windows_paths(self):
        with mock.patch.object(sys, 'platform', 'linux'):
            self.assertEqual(acceptance.runtime_environment(Path('nonexistent-build')), dict(os.environ))

    def test_windows_runtime_requires_unambiguous_configured_qt(self):
        for cache in ['', 'Qt6_DIR:PATH=/one/lib/cmake/Qt6\nQt6_DIR:PATH=/two/lib/cmake/Qt6\n']:
            with self.subTest(cache=cache), tempfile.TemporaryDirectory() as tmp:
                build = Path(tmp)
                (build / 'CMakeCache.txt').write_text(cache, encoding='utf-8')
                with mock.patch.object(sys, 'platform', 'win32'):
                    with self.assertRaisesRegex(ValueError, 'configured Qt6_DIR'):
                        acceptance.runtime_environment(build)

    def junit(self, destination):
        root = ET.Element('testsuite', tests='3', failures='0', disabled='0', skipped='0')
        for language in sorted(acceptance.EXPECTED):
            case = ET.SubElement(root, 'testcase', name=language, status='run')
            output = ''.join(f'[ RUN      ] {name}\n[       OK ] {name} (0 ms)\n' for name in sorted(acceptance.CASES))
            ET.SubElement(case, 'system-out').text = output + '[  PASSED  ] 7 tests.\n'
        destination.parent.mkdir(parents=True, exist_ok=True)
        ET.ElementTree(root).write(destination, encoding='utf-8', xml_declaration=True)
        return root

    def test_actual_results_reject_partial_skipped_or_truncated_success(self):
        for defect in ['disabled', 'skipped', 'failure', 'error', 'empty', 'truncated', 'missing', 'duplicate', 'filtered', 'wrong-count', 'missing-case', 'skipped-marker']:
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as tmp:
                report = Path(tmp) / 'results.xml'
                root = self.junit(report)
                self.assertEqual(acceptance.audit_results(report), sorted(acceptance.EXPECTED))
                case = list(root)[1]
                output = case.find('system-out')
                if defect == 'disabled':
                    case.set('status', 'notrun')
                elif defect in ['skipped', 'failure', 'error']:
                    ET.SubElement(case, defect)
                elif defect == 'empty':
                    output.text = ''
                elif defect == 'truncated':
                    output.text += '[This part of the test output was removed since it exceeds the threshold]'
                elif defect == 'missing':
                    root.remove(case)
                elif defect == 'duplicate':
                    case.set('name', list(root)[0].get('name'))
                elif defect == 'missing-case':
                    output.text = '\n'.join(output.text.splitlines()[2:])
                elif defect == 'skipped-marker':
                    output.text += '[  SKIPPED ] CsvRuntimeFileLoader.ShortWarningClose\n'
                elif defect == 'filtered':
                    output.text += 'Note: Google Test filter = CsvRuntimeFileLoader.*'
                else:
                    output.text = output.text.replace('[  PASSED  ] 7 tests.', '[  PASSED  ] 6 tests.')
                ET.ElementTree(root).write(report, encoding='utf-8', xml_declaration=True)
                with self.assertRaises(ValueError):
                    acceptance.audit_results(report)

    def stage(self, root):
        lock = json.loads((ROOT / 'packaging/localization/plugin-patches/source-lock.json').read_text(encoding='utf-8'))
        record = dict(next(item for item in lock['plugins'] if item['id'] == 'csv-loader'))
        binary = root / 'lib/plotjuggler/plugins/csv-loader/csv_source_plugin.dll'
        binary.parent.mkdir(parents=True)
        binary.write_bytes(b'synthetic-test-only')
        record['files'] = [{'path': binary.relative_to(root).as_posix(),
                            'sha256': hashlib.sha256(binary.read_bytes()).hexdigest()}]
        manifest = root / 'share/plotjuggler4/release.json'
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({'localized_plugin_rebuilds': [record]}), encoding='utf-8')
        return binary, manifest, record

    def test_staged_plugin_must_match_current_source_and_bytes(self):
        for field in ['version', 'commit', 'sdk', 'patch_sha256', 'binary', 'duplicate', 'path']:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                binary, manifest, record = self.stage(root)
                self.assertEqual(acceptance.staged_csv(root), binary)
                records = [record]
                if field == 'binary':
                    binary.write_bytes(b'tampered')
                elif field == 'duplicate':
                    records.append(record)
                elif field == 'path':
                    record['files'][0]['path'] = 'other/csv_source_plugin.dll'
                else:
                    record[field] = 'not-the-locked-value'
                manifest.write_text(json.dumps({'localized_plugin_rebuilds': records}), encoding='utf-8')
                with self.assertRaises(AssertionError):
                    acceptance.staged_csv(root)

    def test_missing_or_extra_language_never_runs_an_incomplete_gate(self):
        for selected in [acceptance.EXPECTED - {'CsvRuntimeFileLoader_zh_TW'},
                         acceptance.EXPECTED | {'CsvRuntimeFileLoader_unknown'}]:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.stage(root)
                self.configure_runtime(root / 'build')
                listing = json.dumps({'tests': [{'name': name} for name in selected]})
                with mock.patch.object(sys, 'argv', ['gate', '--build', str(root / 'build'), '--prefix', str(root)]), \
                     mock.patch.object(acceptance.subprocess, 'run') as run, \
                     mock.patch.object(acceptance.subprocess, 'check_output', return_value=listing):
                    with self.assertRaises(AssertionError):
                        acceptance.main()
                    self.assertEqual(run.call_count, 2)  # Configure/build only, never a partial ctest.

    def test_complete_gate_builds_and_runs_without_skip(self):
        for platform in ['win32', 'linux']:
            with self.subTest(platform=platform), tempfile.TemporaryDirectory() as tmp:
                self.check_complete_gate(Path(tmp), platform)

    def check_complete_gate(self, root, platform):
        """Discovery and execution must inherit the same prepared runtime."""
        with mock.patch.object(sys, 'platform', platform):
            self.stage(root)
            qt, dirs = self.configure_runtime(root / 'build')
            listing = json.dumps({'tests': [{'name': name} for name in acceptance.EXPECTED]})
            self.junit(root / 'build/csv-runtime.xml')
            with mock.patch.object(sys, 'argv', ['gate', '--build', str(root / 'build'), '--prefix', str(root)]), \
                 mock.patch.object(acceptance.subprocess, 'run') as run, \
                 mock.patch.object(acceptance.subprocess, 'check_output', return_value=listing) as discover:
                acceptance.main()
                self.assertEqual(run.call_count, 3)
                self.assertIn('--no-tests=error', run.call_args.args[0])
                self.assertIn('--output-junit', run.call_args.args[0])
                self.assertIn('--test-output-size-passed', run.call_args.args[0])
                self.assertEqual(run.call_args.args[0][-2:], ['-R', '^CsvRuntimeFileLoader_'])
                env = run.call_args.kwargs['env']
                self.assertIs(discover.call_args.kwargs['env'], env)
                if platform == 'win32':
                    self.assertEqual(env['PATH'].split(';')[:3],
                                     [str(qt / 'bin'), *(directory.as_posix() for directory in dirs)])
                    self.assertEqual(env['QT_PLUGIN_PATH'], str(qt / 'plugins'))
                else:
                    self.assertEqual(env, dict(os.environ))


if __name__ == '__main__':
    unittest.main()
