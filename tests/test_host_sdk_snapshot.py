#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Keep package and source SDK paths on the same reviewed snapshot."""
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
