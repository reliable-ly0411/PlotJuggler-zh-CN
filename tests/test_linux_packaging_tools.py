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
import urllib.error

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

    def test_transient_metadata_and_asset_failures_retry_independently(self):
        metadata = dict(id=123, name=self.tool['name'], size=len(self.data),
                        digest='sha256:' + self.tool['sha256'], state='uploaded')
        error = urllib.error.HTTPError('https://api.github.com/locked', 503, 'unavailable', {}, None)
        with patch.object(linux_tools.urllib.request, 'urlopen', side_effect=[
                error, io.BytesIO(json.dumps(metadata).encode()), TimeoutError(), io.BytesIO(self.data)]) as fetch, \
             patch.object(linux_tools.download_retry.time, 'sleep') as sleep:
            linux_tools.prepare_linux_tools(self.out, verify_metadata=True)
        self.assertEqual(fetch.call_count, 4)
        requests = [item.args[0] for item in fetch.call_args_list]
        self.assertIs(requests[0], requests[1])
        self.assertIs(requests[2], requests[3])
        self.assertEqual(requests[0].full_url, requests[2].full_url)
        self.assertEqual(requests[0].get_header('Accept'), 'application/vnd.github+json')
        self.assertEqual(requests[2].get_header('Accept'), 'application/octet-stream')
        self.assertEqual(sleep.call_count, 2)
        self.assertEqual((self.out / self.tool['name']).read_bytes(), self.data)

    def test_invalid_json_and_all_metadata_identity_fields_fail_without_retry(self):
        metadata = dict(id=123, name=self.tool['name'], size=len(self.data),
                        digest='sha256:' + self.tool['sha256'], state='uploaded')
        invalid = [b'{', b'\xff']
        invalid += [json.dumps({**metadata, key: 'wrong'}).encode() for key in metadata]
        for raw in invalid:
            with self.subTest(raw=raw), \
                 patch.object(linux_tools.urllib.request, 'urlopen', return_value=io.BytesIO(raw)) as fetch, \
                 patch.object(linux_tools.download_retry.time, 'sleep') as sleep:
                with self.assertRaises(ValueError):
                    linux_tools.prepare_linux_tools(self.out, verify_metadata=True)
                self.assertEqual(fetch.call_count, 1)
                sleep.assert_not_called()
                self.assertFalse((self.out / self.tool['name']).exists())

    def test_exhausted_metadata_does_not_fetch_asset_or_write(self):
        with patch.object(linux_tools.urllib.request, 'urlopen', side_effect=TimeoutError()) as fetch, \
             patch.object(linux_tools.download_retry.time, 'sleep'):
            with self.assertRaises(TimeoutError):
                linux_tools.prepare_linux_tools(self.out, verify_metadata=True)
        self.assertEqual(fetch.call_count, 3)
        self.assertTrue(all(item.args[0].get_header('Accept') == 'application/vnd.github+json'
                            for item in fetch.call_args_list))
        self.assertFalse((self.out / self.tool['name']).exists())

    def test_write_permission_failure_does_not_redownload(self):
        with patch.object(linux_tools.urllib.request, 'urlopen', return_value=io.BytesIO(self.data)) as fetch, \
             patch.object(Path, 'write_bytes', side_effect=PermissionError('denied')), \
             patch.object(linux_tools.download_retry.time, 'sleep') as sleep:
            with self.assertRaises(PermissionError):
                linux_tools.prepare_linux_tools(self.out)
        self.assertEqual(fetch.call_count, 1)
        sleep.assert_not_called()

    def test_bad_download_is_not_written(self):
        for data in [b'wrong length', b'x' * len(self.data)]:
            with patch.object(linux_tools.urllib.request, 'urlopen', return_value=io.BytesIO(data)) as fetch, \
                 patch.object(linux_tools.download_retry.time, 'sleep') as sleep:
                with self.assertRaisesRegex(ValueError, 'size/checksum mismatch'):
                    linux_tools.prepare_linux_tools(self.out)
                self.assertEqual(fetch.call_count, 1)
                sleep.assert_not_called()
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
