# SPDX-License-Identifier: MPL-2.0
"""Synthetic input tests; no network access or Windows executable is used."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('native_tools', ROOT / 'scripts/windows/prepare_native_tools.py')
tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tools)


class NativeToolTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def pin(self, data=b'expected'):
        return {'name': 'synthetic', 'version': '1', 'file': 'tool.zip',
                'url': 'https://example.invalid/tool.zip', 'source': 'https://example.invalid/source.json',
                'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}

    def zip(self, entries):
        archive = self.root / 'fixture.zip'
        with zipfile.ZipFile(archive, 'w') as out:
            for name, data in entries:
                out.writestr(name, data)
        return archive

    def test_official_pins_are_complete_and_ifw_matches_existing_helper(self):
        pins = json.loads((ROOT / '.github/windows-native-kit/tool-pins.json').read_text(encoding='utf-8'))
        self.assertEqual(pins['schema'], 1)
        for pin in pins['artifacts']:
            tools.validate_pin(pin)
        self.assertEqual({p['name'] for p in pins['artifacts']}, {'cmake', 'python', '7zr-bootstrap', '7z-extra', 'ifw'})
        ifw = next(p for p in pins['artifacts'] if p['name'] == 'ifw')
        self.assertIn(ifw['sha256'], (ROOT / 'packaging/installer/install_ifw.ps1').read_text(encoding='utf-8'))

    def test_download_checks_digest_size_and_no_overwrite(self):
        output = self.root / 'tool.zip'
        with mock.patch.object(tools.urllib.request, 'urlopen', return_value=io.BytesIO(b'expected')):
            record = tools.download(self.pin(), output)
        self.assertEqual(record['bytes'], 8)
        self.assertEqual(output.read_bytes(), b'expected')
        with self.assertRaises(tools.ToolError):
            tools.download(self.pin(), output)
        with mock.patch.object(tools.urllib.request, 'urlopen', return_value=io.BytesIO(b'incorrect')):
            with self.assertRaises(tools.ToolError):
                tools.download(self.pin(), self.root / 'wrong.zip')

    def test_pin_rejects_credentials_queries_and_ambiguous_names(self):
        for field, value in [('url', 'https://u:p@example.invalid/tool'),
                             ('source', 'https://example.invalid/a?token=abc'),
                             ('file', '../escape'), ('sha256', '0' * 63)]:
            pin = self.pin(); pin[field] = value
            with self.subTest(field=field), self.assertRaises(tools.ToolError):
                tools.validate_pin(pin)

    def test_extracts_only_expected_zip_root(self):
        archive = self.zip([('package/bin/tool.exe', b'abc'), ('package/LICENSE.txt', b'license')])
        output = self.root / 'out'
        tools.extract_zip(archive, output, 'package/')
        self.assertEqual((output / 'bin/tool.exe').read_bytes(), b'abc')
        with self.assertRaises(tools.ToolError):
            tools.extract_zip(archive, output, 'package/')

    def test_zip_traversal_absolute_reserved_and_case_collisions_fail(self):
        for index, entries in enumerate([
                [('package/../escape', b'x')], [('package/C:/escape', b'x')],
                [('package/a//b', b'x')], [('package/CON.txt', b'x')], [('package/NUL .txt', b'x')],
                [('package/a.txt', b'x'), ('package/A.txt', b'y')],
                [('package/a/one.txt', b'x'), ('package/A/two.txt', b'y')],
                [('other/file', b'x')], [('package/with\\\\slash', b'x')]]):
            with self.subTest(entries=entries):
                archive = self.zip(entries)
                with self.assertRaises(tools.ToolError):
                    tools.extract_zip(archive, self.root / f'out{index}', 'package/')

    def test_zip_symlink_fails(self):
        archive = self.root / 'link.zip'
        info = zipfile.ZipInfo('package/link')
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        with zipfile.ZipFile(archive, 'w') as out:
            out.writestr(info, 'target')
        with self.assertRaises(tools.ToolError):
            tools.extract_zip(archive, self.root / 'out', 'package/')

    def test_preparation_fails_closed_on_non_windows(self):
        with mock.patch.object(tools.sys, 'platform', 'linux'):
            with self.assertRaisesRegex(tools.ToolError, 'requires Windows'):
                tools.prepare(self.root, ROOT / '.github/windows-native-kit/tool-pins.json')


if __name__ == '__main__':
    unittest.main()
