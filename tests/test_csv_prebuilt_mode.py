# SPDX-License-Identifier: MPL-2.0
"""Prebuilt CSV gate tests use synthetic bytes and never run CTest or a plugin."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import xml.etree.ElementTree as ET

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('csv_gate_prebuilt', REPO / 'packaging/localization/run_csv_runtime_acceptance.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
SHA = 'a' * 40
TREE = 'b' * 40


class CsvPrebuiltTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.kit = Path(self.temp.name) / 'kit'
        self.root = self.kit / 's'; self.root.mkdir(parents=True)
        self.build = self.kit / 'b'; self.build.mkdir()
        self.prefix = self.build / 'fork-prefix'
        self.qt = self.kit / 'q'; (self.qt / 'bin').mkdir(parents=True); (self.qt / 'plugins').mkdir()
        self.qt_core = self.qt / 'bin/Qt6Core.dll'; self.qt_core.write_bytes(b'synthetic Qt')
        self.ctest = self.kit / 't/cmake/bin/ctest.exe'; self.ctest.parent.mkdir(parents=True); self.ctest.write_bytes(b'synthetic ctest')
        self.lock = self.root / 'packaging/localization/plugin-patches/source-lock.json'
        self.lock.parent.mkdir(parents=True)
        self.lock.write_bytes((REPO / 'packaging/localization/plugin-patches/source-lock.json').read_bytes())
        self.script = self.root / 'packaging/localization/run_csv_runtime_acceptance.py'; self.script.parent.mkdir(parents=True, exist_ok=True)
        self.script.write_bytes(b'synthetic script identity')
        source = next(x for x in json.loads(self.lock.read_text(encoding='utf-8'))['plugins'] if x['id'] == 'csv-loader')
        self.plugin = self.prefix / 'lib/plotjuggler/plugins/csv-loader/csv_source_plugin.dll'
        self.plugin.parent.mkdir(parents=True); self.plugin.write_bytes(b'actual-staged-fixture')
        record = dict(source)
        record['files'] = [{'path': self.plugin.relative_to(self.prefix).as_posix(), 'sha256': self.digest(self.plugin)}]
        self.release = self.prefix / 'share/plotjuggler4/release.json'; self.release.parent.mkdir(parents=True)
        self.release.write_text(json.dumps({'source_commit': SHA, 'localized_plugin_rebuilds': [record]}), encoding='utf-8')
        self.runner = self.build / 'pj_app/RelWithDebInfo/csv_runtime_file_loader_test.exe'; self.runner.parent.mkdir(parents=True)
        self.runner.write_bytes(b'PE fixture\0' + self.plugin.resolve().as_posix().encode('utf-8') + b'\0')
        self.listing = {'kind': 'ctestInfo', 'tests': []}
        for language in ('zh_CN', 'zh_TW', 'en_US'):
            self.listing['tests'].append({'name': 'CsvRuntimeFileLoader_' + language, 'config': 'RelWithDebInfo',
                                          'command': [str(self.runner)], 'properties': [
                                              {'name': 'ENVIRONMENT', 'value': ['PLOTJUGGLER_UI_LANGUAGE=' + language,
                                                                                'QT_QPA_PLATFORM=offscreen']}]})
        for name in ('pj_ffmpeg_bin_dirs.txt', 'pj_python_bin_dirs.txt'):
            path = self.kit / ('c/' + name); path.mkdir(parents=True)
            (self.build / name).write_text(str(path) + '\n', encoding='utf-8')
        self.identity = self.kit / '_bundle/csv-prebuilt.json'
        self.manifest = self.kit / '_bundle/manifest.json'
        self.report = self.kit / 'r/run/csv.xml'; self.report.parent.mkdir(parents=True)
        self.root_patch = mock.patch.object(gate, 'ROOT', self.root); self.root_patch.start(); self.addCleanup(self.root_patch.stop)
        self.file_patch = mock.patch.object(gate, '__file__', str(self.script)); self.file_patch.start(); self.addCleanup(self.file_patch.stop)
        gate.capture_prebuilt(self.identity, json.dumps(self.listing), self.plugin, SHA, TREE, self.qt, '6.12.0', '0.39.0', self.ctest)
        self.make_manifest()

    @staticmethod
    def digest(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def make_manifest(self):
        files = [self.identity, self.runner, self.plugin, self.qt_core, self.ctest, self.lock, self.release, self.script,
                 self.build / 'pj_ffmpeg_bin_dirs.txt', self.build / 'pj_python_bin_dirs.txt']
        entries = [{'path': p.relative_to(self.kit).as_posix(), 'bytes': p.stat().st_size, 'sha256': self.digest(p)} for p in files]
        self.manifest.write_text(json.dumps({'schema': 1, 'logical_root': str(self.kit),
            'provenance': {'source_sha': SHA, 'source_tree': TREE, 'configuration': 'RelWithDebInfo',
                           'qt': '6.12.0', 'sdk': '0.39.0'}, 'files': entries,
            'directories': ['q/bin', 'q/plugins', 'c/pj_ffmpeg_bin_dirs.txt', 'c/pj_python_bin_dirs.txt']}), encoding='utf-8')
        self.manifest_sha = self.digest(self.manifest)

    def args(self):
        return ['gate', '--build', str(self.build), '--prefix', str(self.prefix), '--prebuilt-identity', str(self.identity),
                '--source-sha', SHA, '--source-tree', TREE, '--kit-root', str(self.kit), '--qt-dir', str(self.qt),
                '--ctest', str(self.ctest), '--manifest', str(self.manifest), '--manifest-sha256', self.manifest_sha,
                '--report', str(self.report)]

    def result(self):
        root = ET.Element('testsuite', tests='3', failures='0', disabled='0', skipped='0')
        for name in sorted(gate.EXPECTED):
            case = ET.SubElement(root, 'testcase', name=name, status='run')
            output = ''.join(f'[ RUN      ] {x}\n[       OK ] {x} (0 ms)\n' for x in sorted(gate.CASES))
            ET.SubElement(case, 'system-out').text = output + '[  PASSED  ] 7 tests.\n'
        ET.ElementTree(root).write(self.report, encoding='utf-8', xml_declaration=True)

    def test_explicit_prebuilt_runs_exact_existing_gate_without_cmake_or_cache(self):
        def execute(command, **kwargs):
            self.assertEqual(command[0], str(self.ctest.resolve()))
            self.assertIn('--no-tests=error', command)
            self.assertIn('--verbose', command)
            self.assertEqual(command[command.index('--test-output-size-passed') + 1], '1073741824')
            self.assertEqual(command[command.index('--test-output-size-failed') + 1], '1073741824')
            self.assertEqual(command[-2:], ['-R', '^CsvRuntimeFileLoader_'])
            self.result()
        with mock.patch.object(sys, 'platform', 'win32'), mock.patch.object(sys, 'argv', self.args()), \
             mock.patch.object(gate.subprocess, 'check_output', return_value=json.dumps(self.listing)) as discover, \
             mock.patch.object(gate.subprocess, 'run', side_effect=execute) as run:
            gate.main()
        self.assertEqual(discover.call_count, 1)
        self.assertEqual(run.call_count, 1)
        self.assertFalse((self.build / 'CMakeCache.txt').exists())

    def test_tampered_identity_manifest_or_input_fails_before_discovery(self):
        for item in (self.runner, self.qt_core, self.ctest, self.plugin, self.lock, self.identity,
                     self.build / 'pj_ffmpeg_bin_dirs.txt'):
            with self.subTest(item=item.name):
                original = item.read_bytes(); item.write_bytes(original + b'tampered')
                with mock.patch.object(sys, 'platform', 'win32'), mock.patch.object(sys, 'argv', self.args()), \
                     mock.patch.object(gate.subprocess, 'check_output') as discover, \
                     mock.patch.object(gate.subprocess, 'run') as run:
                    with self.assertRaises((ValueError, AssertionError, json.JSONDecodeError)):
                        gate.main()
                    discover.assert_not_called(); run.assert_not_called()
                item.write_bytes(original)
        args = self.args(); args[args.index('--manifest-sha256') + 1] = '0' * 64
        with mock.patch.object(sys, 'platform', 'win32'), mock.patch.object(sys, 'argv', args), \
             mock.patch.object(gate.subprocess, 'check_output') as discover:
            with self.assertRaises(ValueError): gate.main()
            discover.assert_not_called()

    def test_wrong_source_qt_sdk_or_runner_path_fails_closed(self):
        record = json.loads(self.identity.read_text(encoding='utf-8'))
        for field, value in [('source_sha', 'c' * 40), ('host_sdk', 'wrong'), ('qt_version', 'wrong'),
                             ('plugin_sdk', 'wrong'), ('runner', str(self.kit / 'missing.exe'))]:
            with self.subTest(field=field):
                altered = dict(record); altered[field] = value
                self.identity.write_text(json.dumps(altered), encoding='utf-8'); self.make_manifest()
                with mock.patch.object(sys, 'platform', 'win32'), mock.patch.object(sys, 'argv', self.args()), \
                     mock.patch.object(gate.subprocess, 'check_output') as discover:
                    with self.assertRaises((ValueError, OSError)): gate.main()
                    discover.assert_not_called()
        self.identity.write_text(json.dumps(record), encoding='utf-8'); self.make_manifest()

    def test_registration_changes_fail_before_execution(self):
        altered = json.loads(json.dumps(self.listing)); altered['tests'][0]['properties'][0]['value'].append('PLOTJUGGLER_UI_LANGUAGE=other')
        altered['tests'][0]['properties'][0]['value'].remove('PLOTJUGGLER_UI_LANGUAGE=zh_CN')
        with mock.patch.object(sys, 'platform', 'win32'), mock.patch.object(sys, 'argv', self.args()), \
             mock.patch.object(gate.subprocess, 'check_output', return_value=json.dumps(altered)), \
             mock.patch.object(gate.subprocess, 'run') as run:
            with self.assertRaises(ValueError): gate.main()
            run.assert_not_called()

    def test_capture_rejects_runner_without_exact_plugin_path(self):
        self.runner.write_bytes(b'no path')
        with self.assertRaises(ValueError):
            gate.capture_prebuilt(self.kit / '_bundle/other.json', json.dumps(self.listing), self.plugin, SHA, TREE,
                                  self.qt, '6.12.0', '0.39.0', self.ctest)

    def test_release_record_must_match_source_commit_before_discovery(self):
        record = json.loads(self.release.read_text(encoding='utf-8')); record['source_commit'] = 'f' * 40
        self.release.write_text(json.dumps(record), encoding='utf-8'); self.make_manifest()
        with mock.patch.object(sys, 'platform', 'win32'), mock.patch.object(sys, 'argv', self.args()), \
             mock.patch.object(gate.subprocess, 'check_output') as discover:
            with self.assertRaisesRegex(ValueError, 'exact source commit'): gate.main()
            discover.assert_not_called()

    def test_runtime_paths_reject_owned_outputs_or_unmanifested_directories_before_discovery(self):
        for relative in ('r/previous-run', 'c/unmanifested'):
            path = self.kit / relative; path.mkdir(parents=True)
            listing = self.build / 'pj_ffmpeg_bin_dirs.txt'; original = listing.read_text(encoding='utf-8')
            listing.write_text(str(path) + '\n', encoding='utf-8'); self.make_manifest()
            with self.subTest(relative=relative), mock.patch.object(sys, 'platform', 'win32'), \
                 mock.patch.object(sys, 'argv', self.args()), mock.patch.object(gate.subprocess, 'check_output') as discover:
                with self.assertRaisesRegex(ValueError, 'immutable manifest input'): gate.main()
                discover.assert_not_called()
            listing.write_text(original, encoding='utf-8'); self.make_manifest()


if __name__ == '__main__':
    unittest.main()
