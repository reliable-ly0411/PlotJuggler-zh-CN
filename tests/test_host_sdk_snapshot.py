#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Keep package and source SDK paths on the same reviewed snapshot."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('host_sdk_bootstrap', ROOT / 'scripts/bootstrap_host_sdk.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


class HostSdkSnapshotTests(unittest.TestCase):
    def test_all_pins_agree(self):
        pin = json.loads((ROOT / 'cmake/host-sdk-source.json').read_text(encoding='utf-8'))
        self.assertIn('plotjuggler_sdk/' + pin['version'], (ROOT / 'conanfile.txt').read_text(encoding='utf-8'))
        self.assertIn('plotjuggler_sdk/' + pin['version'] + '#' + pin['recipe_revision'],
                      json.loads((ROOT / 'conan.lock').read_text(encoding='utf-8'))['requires'])
        cmake = (ROOT / 'CMakeLists.txt').read_text(encoding='utf-8')
        self.assertIn(pin['archive_url'], cmake)
        self.assertIn('SHA256=' + pin['archive_sha256'], cmake)
        self.assertIn(pin['commit'], pin['archive_url'])
        self.assertEqual(pin['license'], 'Apache-2.0')
        self.assertEqual(pin['version'], '0.40.0')
        self.assertEqual(pin['host_contract_version'], '0.40.0')
        self.assertEqual(pin['upstream_base'], '9fc42b1a81867da812d7f1880bf67b1c74f3f813')

    def test_source_version_and_license_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary)
            content = b'license fixture'
            pin = {'version': '0.40.0', 'license': 'Apache-2.0',
                   'license_files_sha256': {name: hashlib.sha256(content).hexdigest()
                       for name in ('LICENSE', 'LICENSE-APACHE')}}
            (source / 'VERSION').write_text(pin['version'], encoding='utf-8')
            for name in pin['license_files_sha256']:
                (source / name).write_bytes(content)
            bootstrap.verify_source(source, pin)
            (source / 'LICENSE').write_bytes(b'changed')
            with self.assertRaisesRegex(RuntimeError, 'license mismatch'):
                bootstrap.verify_source(source, pin)
            (source / 'VERSION').write_text('0.39.0', encoding='utf-8')
            with self.assertRaisesRegex(RuntimeError, 'version mismatch'):
                bootstrap.verify_source(source, pin)

    def test_license_provenance_is_required(self):
        pin = json.loads((ROOT / 'cmake/host-sdk-source.json').read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary)
            (source / 'VERSION').write_text(pin['version'], encoding='utf-8')
            with self.assertRaisesRegex(RuntimeError, 'license mismatch'):
                bootstrap.verify_source(source, pin)
            pin['license_files_sha256'] = {}
            with self.assertRaisesRegex(RuntimeError, 'provenance missing'):
                bootstrap.verify_source(source, pin)

    def test_corrupt_archive_is_rejected_before_export(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / 'wrong.tar.gz'
            archive.write_bytes(b'not the pinned archive')
            with mock.patch('sys.argv', ['bootstrap_host_sdk.py', '--archive', str(archive)]), \
                    mock.patch.object(bootstrap.subprocess, 'run') as run:
                with self.assertRaisesRegex(RuntimeError, 'SHA256 mismatch'):
                    bootstrap.main()
                run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
