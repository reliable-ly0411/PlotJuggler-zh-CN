#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Windows renderer notices must match both source pins and deployed bytes."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packaging/localization'))
import windows_mesa_notices as notices


class WindowsMesaNoticesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'packaging/localization/windows-mesa-notices'
        self.source.mkdir(parents=True)
        self.qt = self.root / 'qt'
        (self.qt / 'bin').mkdir(parents=True)
        self.binary = b'test-only renderer bytes'
        (self.qt / 'bin/opengl32sw.dll').write_bytes(self.binary)
        self.text = b'Test-only original notice\r\nCopyright example\r\n'
        (self.source / 'notice.txt').write_bytes(self.text)
        self.lock = {'schema': 1, 'component': 'test renderer',
                     'binary': {'path': 'bin/opengl32sw.dll', 'bytes': len(self.binary),
                                'sha256': hashlib.sha256(self.binary).hexdigest()},
                     'files': [{'file': 'notice.txt', 'bytes': len(self.text),
                                'sha256': hashlib.sha256(self.text).hexdigest(),
                                'url': 'https://raw.githubusercontent.com/llvm/llvm-project/' + '1' * 40 + '/llvm/LICENSE.TXT'}]}
        self.write_lock()
        self.prefix = self.root / 'payload'
        self.licenses = self.prefix / 'share/licenses'
        self.licenses.mkdir(parents=True)
        (self.prefix / 'bin').mkdir()
        (self.prefix / 'bin/opengl32sw.dll').write_bytes(self.binary)

    def write_lock(self):
        (self.source.parent / notices.LOCK).write_text(json.dumps(self.lock), encoding='utf-8')

    def stage(self):
        item = notices.collect_windows_mesa_notices(self.root, self.qt, self.licenses)
        files = [{'path': p.relative_to(self.licenses).as_posix(),
                  'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                 for p in self.licenses.rglob('*') if p.is_file()]
        (self.licenses / 'DEPENDENCIES.json').write_text(
            json.dumps({'components': [item], 'files': files}), encoding='utf-8')
        return self.licenses / notices.DIRECTORY

    def test_original_bytes_and_binary_unchanged(self):
        destination = self.stage()
        self.assertEqual((destination / 'notice.txt').read_bytes(), self.text)
        self.assertEqual((self.qt / 'bin/opengl32sw.dll').read_bytes(), self.binary)
        self.assertEqual((self.prefix / 'bin/opengl32sw.dll').read_bytes(), self.binary)
        notices.verify_windows_mesa_notices(self.root, self.prefix)

    def test_unknown_sdk_renderer_fails_before_copy(self):
        (self.qt / 'bin/opengl32sw.dll').write_bytes(b'unknown')
        with self.assertRaisesRegex(ValueError, 'differ'):
            self.stage()
        self.assertFalse((self.licenses / notices.DIRECTORY).exists())

    def test_missing_source_notice(self):
        (self.source / 'notice.txt').unlink()
        with self.assertRaisesRegex(ValueError, 'source set'):
            self.stage()

    def test_extra_source_notice(self):
        (self.source / 'extra.txt').write_text('not reviewed', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'source set'):
            self.stage()

    def test_tampered_original_notice(self):
        (self.source / 'notice.txt').write_bytes(b'x' * len(self.text))
        with self.assertRaisesRegex(ValueError, 'differ'):
            self.stage()

    def test_reused_destination_rejected(self):
        self.stage()
        with self.assertRaises(FileExistsError):
            self.stage()

    def test_deployed_binary_changed(self):
        self.stage()
        (self.prefix / 'bin/opengl32sw.dll').write_bytes(b'x' * len(self.binary))
        with self.assertRaisesRegex(ValueError, 'differ'):
            notices.verify_windows_mesa_notices(self.root, self.prefix)

    def test_missing_deployed_binary(self):
        self.stage()
        (self.prefix / 'bin/opengl32sw.dll').unlink()
        with self.assertRaisesRegex(ValueError, 'regular'):
            notices.verify_windows_mesa_notices(self.root, self.prefix)

    def test_rewritten_manifest_does_not_bless_notice_tamper(self):
        destination = self.stage()
        (destination / 'notice.txt').write_bytes(b'x' * len(self.text))
        p = self.licenses / 'DEPENDENCIES.json'
        manifest = json.loads(p.read_text(encoding='utf-8'))
        manifest['files'][0]['sha256'] = hashlib.sha256(b'x' * len(self.text)).hexdigest()
        p.write_text(json.dumps(manifest), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'differ'):
            notices.verify_windows_mesa_notices(self.root, self.prefix)

    def test_missing_extra_or_wrong_provenance(self):
        destination = self.stage()
        path = destination / 'SOURCE.json'
        original = path.read_bytes()
        path.write_text('{}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'provenance'):
            notices.verify_windows_mesa_notices(self.root, self.prefix)
        path.write_bytes(original)
        (destination / 'extra.txt').write_text('extra', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'inventory'):
            notices.verify_windows_mesa_notices(self.root, self.prefix)
        (destination / 'extra.txt').unlink()
        (destination / 'notice.txt').unlink()
        with self.assertRaisesRegex(ValueError, 'inventory'):
            notices.verify_windows_mesa_notices(self.root, self.prefix)

    def test_missing_or_duplicate_component_or_file_records(self):
        self.stage()
        p = self.licenses / 'DEPENDENCIES.json'
        original = json.loads(p.read_text(encoding='utf-8'))
        for key in ['components', 'files']:
            for operation in ['missing', 'duplicate']:
                with self.subTest(key=key, operation=operation):
                    manifest = copy.deepcopy(original)
                    if operation == 'missing':
                        manifest[key] = []
                    else:
                        manifest[key].append(copy.deepcopy(manifest[key][0]))
                    p.write_text(json.dumps(manifest), encoding='utf-8')
                    with self.assertRaises(ValueError):
                        notices.verify_windows_mesa_notices(self.root, self.prefix)

    def test_invalid_source_lock(self):
        original = copy.deepcopy(self.lock)
        mutations = [lambda x: x['files'].append(copy.deepcopy(x['files'][0])),
                     lambda x: x['files'][0].update(file='../escape'),
                     lambda x: x['files'][0].update(file='SOURCE.json'),
                     lambda x: x['files'][0].update(url='https://example.com/' + '1' * 40 + '/x'),
                     lambda x: x['files'][0].update(bytes=True),
                     lambda x: x['files'][0].update(sha256='bad'),
                     lambda x: x['binary'].update(path='../other.dll')]
        for mutation in mutations:
            self.lock = copy.deepcopy(original)
            mutation(self.lock)
            self.write_lock()
            with self.assertRaises(ValueError):
                notices.read_lock(self.root)

    def test_source_link_rejected(self):
        path = self.source / 'notice.txt'
        outside = self.root / 'outside.txt'
        outside.write_bytes(path.read_bytes())
        path.unlink()
        try:
            path.symlink_to(outside)
        except OSError:
            self.skipTest('symlink privilege unavailable')
        with self.assertRaisesRegex(ValueError, 'regular'):
            self.stage()

    def test_bundled_d3dcompiler_rejected_anywhere(self):
        self.stage()
        for name in ['bin/d3dcompiler_47.dll', 'lib/D3DCompiler_43.DLL',
                     'plugins/nested/d3dcompiler_46.dll']:
            path = self.prefix / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'not permitted in product')
            with self.assertRaisesRegex(ValueError, 'system D3D compiler'):
                notices.verify_windows_mesa_notices(self.root, self.prefix)
            path.unlink()
        notices.verify_windows_mesa_notices(self.root, self.prefix)

    def test_system_compiler_uses_only_system32(self):
        with mock.patch.object(notices.sys, 'getwindowsversion', create=True,
                               return_value=SimpleNamespace(major=10, build=17763)), \
             mock.patch.object(notices.ctypes, 'WinDLL', create=True) as load:
            notices.verify_system_d3dcompiler()
            load.assert_called_once_with('d3dcompiler_47.dll', winmode=0x00000800)

    def test_unsupported_windows_rejected(self):
        for major, build in [(6, 9600), (10, 17762)]:
            with mock.patch.object(notices.sys, 'getwindowsversion', create=True,
                                   return_value=SimpleNamespace(major=major, build=build)), \
                 mock.patch.object(notices.ctypes, 'WinDLL', create=True) as load:
                with self.assertRaisesRegex(ValueError, '1809'):
                    notices.verify_system_d3dcompiler()
                load.assert_not_called()

    def test_missing_system_compiler_or_export_rejected(self):
        with mock.patch.object(notices.sys, 'getwindowsversion', create=True,
                               return_value=SimpleNamespace(major=10, build=19045)):
            with mock.patch.object(notices.ctypes, 'WinDLL', create=True, side_effect=OSError('missing')):
                with self.assertRaisesRegex(ValueError, 'D3DCompile'):
                    notices.verify_system_d3dcompiler()
            with mock.patch.object(notices.ctypes, 'WinDLL', create=True, return_value=object()):
                with self.assertRaisesRegex(ValueError, 'D3DCompile'):
                    notices.verify_system_d3dcompiler()

    def test_actual_retained_sources_match_fixed_hashes(self):
        lock = notices.read_lock(ROOT)
        source = ROOT / 'packaging/localization/windows-mesa-notices'
        self.assertEqual({p.name for p in source.iterdir()}, {x['file'] for x in lock['files']})
        for item in lock['files']:
            notices._matches(source / item['file'], item)
        self.assertIn('Brian Paul', (source / 'Mesa-license.html').read_text(encoding='utf-8'))
        self.assertIn('University of Illinois', (source / 'LLVM-LICENSE.TXT').read_text(encoding='utf-8'))
        for name in ['Mesa-lp_context.c.txt', 'Mesa-lp_bld_init.c.txt', 'Mesa-libgl_gdi.c.txt']:
            self.assertIn('VMware', (source / name).read_text(encoding='utf-8'))
        self.assertIn('windows-mesa-notices/* -text', (ROOT / '.gitattributes').read_text(encoding='utf-8'))

    def test_packaging_and_clean_checks_remain_wired(self):
        installer = (ROOT / 'packaging/installer/build_windows_installer.ps1').read_text(encoding='utf-8')
        self.assertLess(installer.index('windows_mesa_notices.py'), installer.index('& $binarycreator'))
        calls = [line for line in installer.splitlines() if '& $windeployqt ' in line]
        self.assertEqual(len(calls), 2)
        self.assertTrue(all('@systemCompilerArgs' in line for line in calls))
        self.assertIn("if ($ExtraPrefix) { $systemCompilerArgs = @('--no-system-d3d-compiler') }", installer)
        self.assertIn('verify_system_d3dcompiler()', (ROOT / 'packaging/localization/verify_package.py').read_text(encoding='utf-8'))
        self.assertIn('verify_windows_mesa_notices', (ROOT / 'packaging/localization/verify_package.py').read_text(encoding='utf-8'))
        self.assertIn('windows=not linux_tools', (ROOT / 'packaging/localization/prepare_payload.py').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
