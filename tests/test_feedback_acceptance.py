#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Offline regressions for native input/result gates and package source identity."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest import mock
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
        with mock.patch.object(fixtures.urllib.request, 'urlopen', side_effect=AssertionError('No test network')):
            return fixtures.prepare(self.source, self.build, self.output, 'Release', platform, self.archive)

    def test_exact_two_inputs_and_external_identity(self):
        record = self.prepare()
        self.assertEqual({p.name for p in self.output.iterdir()}, {'ardupilot-dataflash', 'toolbox-fft'})
        self.assertTrue(self.output.with_name('inputs-identity.json').is_file())
        for row in record['files']:
            self.assertEqual(hashlib.sha256((self.output/row['path']).read_bytes()).hexdigest(), row['sha256'])

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


class PackageLanguagesTests(unittest.TestCase):
    def run_manifest(self, languages, png_languages):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); old = Path.cwd()
            try:
                os.chdir(root)
                Path('versions.env').write_text('PJ_APP_VERSION=4.0.0-zh.1.rc.4\n', encoding='utf-8')
                for i in range(5):
                    directory = root/'reports'/str(i); directory.mkdir(parents=True)
                    report = {'status': 'automated_checks_passed', 'languages': languages,
                              'release': {'source_commit': 'a'*40, 'source_tree': 'b'*40, 'version': '4.0.0-zh.1.rc.4'},
                              'plugin_count': 19 if i==0 else 21, 'loaded_plugin_count': 19 if i==0 else 20,
                              'unavailable_plugins': [] if i==0 else [{'id': 'ros2-topic-subscriber', 'status': 'not_tested_missing_external_dependency'}],
                              'checks': ['synthetic test']}
                    (directory/'acceptance.json').write_text(json.dumps(report), encoding='utf-8')
                    for language in png_languages:
                        (directory/f'gui-{language}.png').write_bytes(b'synthetic-size-check-only'*500)
                Path('candidate').mkdir()
                for name in ['PlotJuggler-4.0.0-zh.1.rc.4-Windows-x64-zh-CN.exe',
                             'PlotJuggler-4.0.0-zh.1.rc.4-x86_64-zh-CN.AppImage',
                             'plotjuggler4_4.0.0~zh.1~rc.4-1_amd64-zh-CN.deb']:
                    (Path('candidate')/name).write_bytes(b'synthetic package')
                with mock.patch.dict(os.environ, {'GITHUB_SHA':'a'*40,'GITHUB_WORKFLOW_SHA':'c'*40,'GITHUB_RUN_ID':'1','GITHUB_RUN_ATTEMPT':'1'}), \
                     mock.patch.object(manifest.subprocess, 'check_output', return_value='b'*40):
                    manifest.main()
                return json.loads(Path('release-manifest.json').read_text(encoding='utf-8'))
            finally:
                os.chdir(old)

    def test_five_reports_require_fifteen_language_screenshots(self):
        result = self.run_manifest(['zh_CN','zh_TW','en_US'], ['zh_CN','zh_TW','en_US'])
        self.assertEqual(len(result['screenshots']), 15)

    def test_old_two_language_reports_rejected(self):
        with self.assertRaisesRegex(AssertionError, 'Incomplete language'):
            self.run_manifest(['zh_CN','en_US'], ['zh_CN','en_US'])

    def test_missing_traditional_screenshot_rejected(self):
        with self.assertRaises(FileNotFoundError):
            self.run_manifest(['zh_CN','zh_TW','en_US'], ['zh_CN','en_US'])


if __name__ == '__main__':
    unittest.main()
