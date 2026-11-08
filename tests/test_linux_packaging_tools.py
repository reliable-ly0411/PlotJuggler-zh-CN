#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Offline regressions for fail-closed Linux packaging tool staging."""
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packaging/localization'))
import linux_tools


class LinuxToolsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = b'audited executable bytes'
        self.tool = dict(repository='official/tool', asset_id=123, name='tool.AppImage',
                         size=len(self.data), sha256=hashlib.sha256(self.data).hexdigest())
        lock = self.root / 'lock.json'
        lock.write_text(json.dumps({'tools': [self.tool]}), encoding='utf-8')
        self.patcher = patch.object(linux_tools, 'LOCK', lock)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.out = self.root / 'out'

    def test_asset_id_download_and_metadata(self):
        metadata = dict(id=123, name=self.tool['name'], size=len(self.data),
                        digest='sha256:' + self.tool['sha256'], state='uploaded')
        with patch.object(linux_tools.urllib.request, 'urlopen', side_effect=[
                io.BytesIO(json.dumps(metadata).encode()), io.BytesIO(self.data)]) as fetch:
            linux_tools.prepare_linux_tools(self.out, verify_metadata=True)
        self.assertEqual(fetch.call_count, 2)
        request = fetch.call_args.args[0]
        self.assertEqual(request.full_url, 'https://api.github.com/repos/official/tool/releases/assets/123')
        self.assertEqual(request.get_header('Accept'), 'application/octet-stream')
        self.assertEqual((self.out / self.tool['name']).read_bytes(), self.data)

    def test_bad_metadata_does_not_download(self):
        with patch.object(linux_tools.urllib.request, 'urlopen', return_value=io.BytesIO(b'{}')) as fetch:
            with self.assertRaisesRegex(ValueError, 'metadata mismatch'):
                linux_tools.prepare_linux_tools(self.out, verify_metadata=True)
        self.assertEqual(fetch.call_count, 1)

    def test_bad_download_is_not_written(self):
        for data in [b'wrong length', b'x' * len(self.data)]:
            with patch.object(linux_tools.urllib.request, 'urlopen', return_value=io.BytesIO(data)):
                with self.assertRaisesRegex(ValueError, 'size/checksum mismatch'):
                    linux_tools.prepare_linux_tools(self.out)
            self.assertFalse((self.out / self.tool['name']).exists())

    def test_cached_bytes_are_rehashed_without_network(self):
        self.out.mkdir()
        target = self.out / self.tool['name']
        target.write_bytes(self.data)
        with patch.object(linux_tools.urllib.request, 'urlopen') as fetch:
            linux_tools.prepare_linux_tools(self.out)
            target.write_bytes(b'x' * len(self.data))
            with self.assertRaisesRegex(ValueError, 'size/checksum mismatch'):
                linux_tools.prepare_linux_tools(self.out)
        fetch.assert_not_called()

    def test_real_lock_and_preflight_order(self):
        entries = json.loads((ROOT / 'packaging/localization/linux-tools-lock.json').read_text(encoding='utf-8'))['tools']
        self.assertEqual(len(entries), 3)
        for entry in entries:
            self.assertIsInstance(entry['asset_id'], int)
            self.assertRegex(entry['source_commit'], r'^[0-9a-f]{40}$')
            self.assertRegex(entry['sha256'], r'^[0-9a-f]{64}$')
            self.assertGreater(entry['size'], 0)
        workflow = (ROOT / '.github/workflows/zh-4x-packages.yml').read_text(encoding='utf-8')
        self.assertLess(workflow.index('linux_tools.py --directory'), workflow.index('- name: Build tools'))


if __name__ == '__main__':
    unittest.main()
