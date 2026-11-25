# SPDX-License-Identifier: MPL-2.0
"""Synthetic input tests; no network access or Windows executable is used."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import tempfile
from types import SimpleNamespace
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

    def prepare_fixture(self, *, missing_notice=None):
        """Exercise extraction and notice checks without executing Windows binaries."""
        def zip_bytes(entries):
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, 'w') as archive:
                for name, data in entries.items():
                    archive.writestr(name, data)
            return buffer.getvalue()

        prefix = 'cmake-3.31.10-windows-x86_64/'
        notice_paths = ('doc/cmake/Copyright.txt', 'doc/cmake/cmcppdap/NOTICE', 'doc/cmake/cmcurl/COPYING',
                        'doc/cmake/cmlibarchive/COPYING', 'doc/cmake/cmliblzma/COPYING',
                        'doc/cmake/cmlibrhash/COPYING', 'doc/cmake/cmlibuv/LICENSE',
                        'doc/cmake/cmnghttp2/COPYING', 'doc/cmake/cmsys/Copyright.txt',
                        'doc/cmake/cmzlib/Copyright.txt', 'doc/cmake/cmzstd/LICENSE')
        notices = {path: ('fixture ' + path + '\r\nlicense bytes\r\n').encode() for path in notice_paths}
        cmake_entries = {prefix + 'bin/cmake.exe': b'cmake', prefix + 'bin/ctest.exe': b'ctest'}
        cmake_entries.update({prefix + path: data for path, data in notices.items() if path != missing_notice})
        if missing_notice == 'doc/cmake/Copyright.txt':
            # A notice at the unrelated layout must not satisfy the required path.
            cmake_entries[prefix + 'doc/cmake-3.31/Copyright.txt'] = b'unrelated notice'
        payloads = {
            'cmake.zip': zip_bytes(cmake_entries),
            'python.zip': zip_bytes({'python.exe': b'python', 'LICENSE.txt': b'python license',
                                     'python312._pth': b'python312.zip\n'}),
            '7zr.exe': b'bootstrap', 'extra.7z': b'extra', 'ifw.7z': b'ifw',
        }
        artifacts = []
        for name, filename in [('cmake', 'cmake.zip'), ('python', 'python.zip'),
                               ('7zr-bootstrap', '7zr.exe'), ('7z-extra', 'extra.7z'), ('ifw', 'ifw.7z')]:
            data = payloads[filename]
            artifacts.append({'name': name, 'version': '1', 'file': filename,
                              'url': 'https://example.invalid/' + filename,
                              'source': 'https://example.invalid/checksums',
                              'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)})
        pins = self.root / 'pins.json'
        pins.write_text(json.dumps({'schema': 1, 'artifacts': artifacts}), encoding='utf-8')
        ci_root = self.root / 'ci'; ci_root.mkdir()

        def open_download(request, timeout):
            return io.BytesIO(payloads[request.full_url.rsplit('/', 1)[-1]])

        def run_fixture(args, **kwargs):
            executable = Path(args[0]).name
            if executable in ('7zr.exe', '7za.exe'):
                output = Path(next(str(arg)[2:] for arg in args if str(arg).startswith('-o')))
                if executable == '7zr.exe':
                    for relative, data in [('x64/7za.exe', b'7za'), ('License.txt', b'7z license')]:
                        target = output / relative; target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(data)
                else:
                    for relative in ('bin/binarycreator.exe', 'bin/installerbase.exe', 'bin/repogen.exe',
                                     'licenses/LICENSE.txt'):
                        target = output / relative; target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(b'ifw fixture')
                return ''
            if executable == 'installerbase.exe':
                return 'IFW Version: 4.10.0, built with Qt fixture'
            if executable == 'ctest.exe':
                return 'ctest version 3.31.10'
            if executable == 'python.exe':
                return 'driver modules OK'
            self.fail('unexpected executable: ' + executable)

        with mock.patch.object(tools.sys, 'platform', 'win32'), \
             mock.patch.object(tools.urllib.request, 'urlopen', side_effect=open_download), \
             mock.patch.object(tools, 'run_checked', side_effect=run_fixture), \
             mock.patch.object(tools.shutil, 'disk_usage', return_value=SimpleNamespace(free=4 * 1024**3)), \
             mock.patch.dict(os.environ, {'SystemRoot': str(self.root / 'Windows')}):
            if missing_notice is None:
                record = tools.prepare(ci_root, pins)
                for path, data in notices.items():
                    self.assertEqual((ci_root / 't/cmake' / path).read_bytes(), data)
                self.assertEqual(len(record['distributions']), 5)
                self.assertTrue((ci_root / 't/tool-provenance.json').is_file())
            else:
                with self.assertRaisesRegex(tools.ToolError,
                                            'missing required pinned tool file: ' + Path(missing_notice).name):
                    tools.prepare(ci_root, pins)
                self.assertFalse((ci_root / 't/tool-provenance.json').exists())

    def test_preparation_preserves_windows_cmake_archive_notice(self):
        self.prepare_fixture()

    def test_preparation_rejects_missing_windows_cmake_archive_notice(self):
        self.prepare_fixture(missing_notice='doc/cmake/Copyright.txt')

    def test_preparation_rejects_missing_cmake_third_party_notice(self):
        self.prepare_fixture(missing_notice='doc/cmake/cmcurl/COPYING')


if __name__ == '__main__':
    unittest.main()
