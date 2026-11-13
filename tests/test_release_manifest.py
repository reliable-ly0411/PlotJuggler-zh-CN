#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Require complete clean-host format coverage and original-asset checksums."""
import json
import os
from unittest import mock
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packaging/localization'))
import create_release_manifest as manifest


class ReleaseManifestTests(unittest.TestCase):
    def test_exact_report_identities(self):
        root = Path('reports')
        paths = [root / path for path in manifest.REPORT_IDENTITIES]
        self.assertEqual(set(manifest.report_identities(paths, root)), {
            ('windows-2022', 'ifw'), ('windows-2022', 'portable'),
            ('ubuntu-22.04', 'deb'), ('ubuntu-22.04', 'appimage'),
            ('ubuntu-24.04', 'deb'), ('ubuntu-24.04', 'appimage')})
        for missing in paths:
            with self.subTest(missing=missing), self.assertRaises(AssertionError):
                manifest.report_identities([p for p in paths if p != missing], root)
        for invalid in [paths + paths[:1], paths[:-1] + paths[:1],
                        paths[:-1] + [root / 'unknown/acceptance.json']]:
            with self.assertRaises(AssertionError):
                manifest.report_identities(invalid, root)

    def test_hash_tool_includes_portable_and_gate_requires_all_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = [root / ('package' + ext) for ext in ('.exe', '.zip', '.AppImage', '.deb')]
            for path in files:
                path.write_bytes(path.name.encode())
            subprocess.run([sys.executable, str(ROOT / 'packaging/localization/hash_packages.py'),
                            str(root), '--output', 'SHA256SUMS-test.txt'], check=True, capture_output=True)
            sums = root / 'SHA256SUMS-test.txt'
            original = sums.read_text(encoding='utf-8')
            self.assertEqual(len(original.splitlines()), 4)
            manifest.verify_checksums(root, files)
            for invalid in ['\n'.join(original.splitlines()[:-1]) + '\n',
                            original + original.splitlines()[0] + '\n',
                            original.replace('package.zip', 'unknown.zip'),
                            original.replace('package.zip', '../package.zip')]:
                sums.write_text(invalid, encoding='utf-8')
                with self.assertRaises(AssertionError):
                    manifest.verify_checksums(root, files)
            sums.write_text(original, encoding='utf-8')
            files[1].write_bytes(b'changed portable bytes')
            with self.assertRaises(AssertionError):
                manifest.verify_checksums(root, files)

    def test_manifest_requires_six_reports_eighteen_screenshots_four_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            previous = Path.cwd()
            os.chdir(directory)
            try:
                version = '4.0.0-zh.1.rc.1'
                Path('versions.env').write_text(f'PJ_APP_VERSION={version}\n', encoding='utf-8')
                candidate = Path('candidate')
                candidate.mkdir()
                names = [f'PlotJuggler-{version}-Windows-x64-zh-CN.exe',
                         f'PlotJuggler-{version}-Windows-x64-portable-zh-CN.zip',
                         f'PlotJuggler-{version}-x86_64-zh-CN.AppImage',
                         f'plotjuggler4_{manifest.versions(version)["deb"]}_amd64-zh-CN.deb']
                for name in names:
                    (candidate / name).write_bytes(name.encode())
                sums = ''.join(f'{manifest.sha256(candidate / n)}  {n}\n' for n in names)
                (candidate / 'SHA256SUMS-test.txt').write_text(sums, encoding='utf-8')
                for relative, (platform, kind) in manifest.REPORT_IDENTITIES.items():
                    path = Path('reports') / relative
                    path.parent.mkdir(parents=True)
                    windows = platform == 'windows-2022'
                    report = {'status': 'automated_checks_passed',
                              'languages': list(manifest.ACCEPTANCE_LANGUAGES),
                              'release': {'source_commit': 'source', 'source_tree': 'tree', 'version': version},
                              'plugin_count': 19 if windows else 21,
                              'loaded_plugin_count': 19 if windows else 20,
                              'unavailable_plugins': [] if windows else [{
                                  'id': 'ros2-topic-subscriber',
                                  'status': 'not_tested_missing_external_dependency'}], 'checks': []}
                    path.write_text(json.dumps(report), encoding='utf-8')
                    for language in manifest.ACCEPTANCE_LANGUAGES:
                        (path.parent / f'gui-{language}.png').write_bytes(b'x' * 10001)
                    if windows:
                        name = names[1 if kind == 'portable' else 0]
                        digest = manifest.sha256(candidate / name)
                        (path.parent / 'package-integrity.json').write_text(json.dumps({
                            'format': kind, 'name': name, 'before': digest, 'after': digest}), encoding='utf-8')
                env = {'GITHUB_SHA': 'source', 'GITHUB_WORKFLOW_SHA': 'workflow',
                       'GITHUB_RUN_ID': '1', 'GITHUB_RUN_ATTEMPT': '1'}
                with mock.patch.dict(os.environ, env), mock.patch.object(
                        manifest.subprocess, 'check_output', return_value='tree'):
                    manifest.main()
                    result = json.loads(Path('release-manifest.json').read_text(encoding='utf-8'))
                    self.assertEqual(len(result['assets']), 4)
                    self.assertEqual(len(result['acceptance_reports']), 6)
                    self.assertEqual(len(result['screenshots']), 18)
                    integrity = Path('reports/zh4-final-Windows-portable/runtime/package-integrity.json')
                    data = json.loads(integrity.read_text(encoding='utf-8'))
                    data['after'] = '0' * 64
                    integrity.write_text(json.dumps(data), encoding='utf-8')
                    with self.assertRaises(AssertionError):
                        manifest.main()
            finally:
                os.chdir(previous)

    def test_portable_job_is_independent_and_required(self):
        workflow = (ROOT / '.github/workflows/zh-4x-packages.yml').read_text(encoding='utf-8')
        job = workflow.split('  windows-portable-clean:', 1)[1].split('  release-manifest:', 1)[0]
        self.assertIn('runs-on: windows-2022', job)
        self.assertIn('-Format portable', job)
        self.assertNotIn('build_windows_installer.ps1', job)
        self.assertIn('needs: [native, linux-clean, windows-clean, windows-portable-clean]', workflow)
        script = (ROOT / 'packaging/localization/verify_windows.ps1').read_text(encoding='utf-8')
        self.assertIn('ExtractToDirectory($package[0].FullName, $root)', script)
        self.assertIn('--capture', script)
        self.assertIn('Original package changed during acceptance', script)


if __name__ == '__main__':
    unittest.main()
