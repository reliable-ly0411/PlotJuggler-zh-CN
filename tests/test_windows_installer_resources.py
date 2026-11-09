#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Cross-platform unit checks, not the Windows integration result."""
import base64
import gzip
import hashlib
import shutil
import subprocess
import zipfile
import re
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest
from unittest import mock
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ifw_smoke', ROOT / 'scripts/verify_windows_installer_resources.py')
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


class InstallerResourceSmokeTests(unittest.TestCase):
    def test_stage_real_metadata_and_only_synthetic_payload(self):
        with tempfile.TemporaryDirectory(prefix='smoke space ') as directory:
            config, packages, meta, translations, qrc = smoke.stage_inputs(ROOT, Path(directory))
            self.assertNotIn('__PJ_', config.read_text(encoding='utf-8'))
            self.assertNotIn('__PJ_', (meta / 'package.xml').read_text(encoding='utf-8'))
            original = ROOT / 'packaging/installer/packages/io.plotjuggler.application/meta'
            for name in ('targetwidget.ui', 'languagewidget.ui', 'zh_CN.ts'):
                self.assertEqual((meta / name).read_bytes(), (original / name).read_bytes())
            script = (meta / 'installscript.qs').read_text(encoding='utf-8')
            encoded = re.search(r'var replacementGuard = "([A-Za-z0-9+/=]+)";', script).group(1)
            self.assertEqual(gzip.decompress(base64.b64decode(encoded)),
                             (ROOT / 'packaging/installer/replacement_guard.ps1').read_bytes())
            self.assertEqual(script.replace(encoded, '__PJ_REPLACEMENT_HELPER_GZIP__'),
                             (original / 'installscript.qs').read_text(encoding='utf-8'))
            self.assertEqual([p.name for p in (meta.parent / 'data').iterdir()],
                             ['SYNTHETIC-NOT-AN-APPLICATION.txt'])
            group = ET.parse(qrc).getroot().find('qresource')
            self.assertEqual(group.attrib['prefix'], '/translations_new')
            self.assertEqual([e.text for e in group], ['ifw_zh_CN.qm', 'qt_zh_CN.qm', smoke.MARKER])

    def test_license_sources_and_historical_notice_are_preserved(self):
        root = ROOT / 'packaging/installer'
        original = root / 'packages/io.plotjuggler.application/meta/license_lgpl.txt'
        # Git LF and Windows CRLF checkouts contain the same unedited notice.
        self.assertEqual(hashlib.sha256(original.read_bytes().replace(b'\r\n', b'\n')).hexdigest(),
                         '0a81c0c611ee9d06f6c247045ae7fa79316cf220431acdf5330e195abbac78c5')
        builder = (root / 'build_windows_installer.ps1').read_text(encoding='utf-8')
        self.assertIn('Copy-Item (Join-Path $pkgSrc "meta/license_lgpl.txt") (Join-Path $historyDir "license_lgpl.txt")', builder)
        self.assertLess(builder.index('$historyDir ='), builder.index('Copy-Item (Join-Path $stageData "share/licenses/Qt-LGPL.txt")'))
        portable = (root / 'build_windows_portable.ps1').read_text(encoding='utf-8')
        self.assertIn('$metadata = Join-Path $StageDir "packages/io.plotjuggler.application/meta"', portable)
        self.assertIn('Copy-Item -LiteralPath (Join-Path $metadata $name)', portable)
        self.assertNotIn('Join-Path $PSScriptRoot', portable)

    @unittest.skipUnless(shutil.which('pwsh') or shutil.which('powershell'), 'PowerShell runtime unavailable')
    def test_portable_uses_staged_bytes_and_keeps_history(self):
        # Execute the actual builder's notice-copy block and portable entry point
        # against a tiny synthetic stage. No binary is launched or downloaded.
        shell = shutil.which('pwsh') or shutil.which('powershell')
        root = ROOT / 'packaging/installer'
        builder = (root / 'build_windows_installer.ps1').read_text(encoding='utf-8')
        block = builder[builder.index('$historyDir ='):builder.index('# --- build the installer')]
        quote = lambda path: "'" + str(path).replace("'", "''") + "'"
        with tempfile.TemporaryDirectory(prefix="license 中文 stage's ") as directory:
            stage = Path(directory)
            payload = stage / 'packages/io.plotjuggler.application/data'
            meta = payload.parent / 'meta'
            meta.mkdir(parents=True)
            (payload / 'bin').mkdir(parents=True)
            (payload / 'bin/PlotJuggler4.exe').write_bytes(b'not executable')
            (payload / 'share/licenses').mkdir(parents=True)
            canonical = b'SYNTHETIC pinned Qt LGPL\n'
            mpl = b'SYNTHETIC staged MPL\n'
            (payload / 'share/licenses/Qt-LGPL.txt').write_bytes(canonical)
            (meta / 'license_mpl.txt').write_bytes(mpl)
            script = (f"$ErrorActionPreference='Stop'; $stageData={quote(payload)}; "
                      f"$stageMeta={quote(meta)}; $pkgSrc={quote(root / 'packages/io.plotjuggler.application')}; "
                      f"$installerRoot={quote(root)}; $ExtraPrefix=$true;\n" + block)
            run = subprocess.run([shell, '-NoProfile', '-NonInteractive', '-Command', script],
                                 capture_output=True, text=True, timeout=30)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            archive = stage / 'portable.zip'
            command = [shell, '-NoProfile', '-NonInteractive', '-File', str(root / 'build_windows_portable.ps1'),
                       '-StageDir', str(stage), '-OutFile', str(archive)]
            run = subprocess.run(command, capture_output=True, text=True, timeout=30)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            original = (root / 'packages/io.plotjuggler.application/meta/license_lgpl.txt').read_bytes()
            with zipfile.ZipFile(archive) as package:
                self.assertEqual(package.read('licenses/license_lgpl.txt'), canonical)
                self.assertEqual(package.read('licenses/license_mpl.txt'), mpl)
                self.assertEqual(package.read('share/licenses/PlotJuggler-installer-history/license_lgpl.txt'), original)
                self.assertEqual(package.read('share/licenses/PlotJuggler-installer-history/LICENSE-PROVENANCE.txt'),
                                 (root / 'LICENSE-PROVENANCE.txt').read_bytes())
            # Missing staged license must fail, never silently fall back to source.
            (meta / 'license_lgpl.txt').unlink()
            command[-1] = str(stage / 'must-not-exist.zip')
            run = subprocess.run(command, capture_output=True, text=True, timeout=30)
            self.assertNotEqual(run.returncode, 0)
            self.assertFalse((stage / 'must-not-exist.zip').exists())

    def test_offline_pin_matches_the_existing_installer_helper(self):
        helper = (ROOT / 'packaging/installer/install_ifw.ps1').read_text(encoding='utf-8')
        expected = re.search(r"\$expected = '([0-9a-f]{64})'", helper)
        self.assertIsNotNone(expected)
        self.assertEqual(smoke.IFW_ARCHIVE_SHA256, expected.group(1))

    def test_offline_extraction_checks_both_hashes_before_running_7z(self):
        with tempfile.TemporaryDirectory(prefix='ifw offline space ') as directory:
            root = Path(directory)
            archive, extractor, destination = root / 'ifw.7z', root / '7z.exe', root / 'ifw tools'
            archive.write_bytes(b'fake official archive')
            extractor.write_bytes(b'fake verified extractor')
            archive_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
            extractor_hash = hashlib.sha256(extractor.read_bytes()).hexdigest()
            def fake_run(command):
                self.assertEqual(command, [extractor, 'x', archive, '-o' + str(destination), '-y'])
                (destination / 'bin').mkdir(parents=True)
                for name in ('binarycreator.exe', 'installerbase.exe', 'repogen.exe'):
                    (destination / 'bin' / name).write_bytes(b'synthetic')
                return ''
            with mock.patch.object(smoke, 'IFW_ARCHIVE_SHA256', archive_hash), \
                 mock.patch.object(smoke, 'run', side_effect=fake_run) as run:
                smoke.extract_pinned_ifw(archive, extractor, extractor_hash, destination)
                self.assertEqual(run.call_count, 1)
                with self.assertRaisesRegex(ValueError, 'existing IFW destination'):
                    smoke.extract_pinned_ifw(archive, extractor, extractor_hash, destination)

    def test_offline_bad_hash_or_partial_tools_fail_without_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive, extractor = root / 'ifw.7z', root / '7z.exe'
            archive.write_bytes(b'archive'); extractor.write_bytes(b'extractor')
            archive_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
            extractor_hash = hashlib.sha256(extractor.read_bytes()).hexdigest()
            with mock.patch.object(smoke, 'IFW_ARCHIVE_SHA256', archive_hash), mock.patch.object(smoke, 'run') as run:
                with self.assertRaisesRegex(ValueError, 'Extractor SHA-256 mismatch'):
                    smoke.extract_pinned_ifw(archive, extractor, '0' * 64, root / 'tools')
                with self.assertRaisesRegex(ValueError, '64 lower-case'):
                    smoke.extract_pinned_ifw(archive, extractor, 'X' * 64, root / 'tools')
                archive.write_bytes(b'tampered')
                with self.assertRaisesRegex(ValueError, 'IFW archive SHA-256 mismatch'):
                    smoke.extract_pinned_ifw(archive, extractor, extractor_hash, root / 'tools')
                run.assert_not_called()
            archive.write_bytes(b'archive')
            with mock.patch.object(smoke, 'IFW_ARCHIVE_SHA256', archive_hash), mock.patch.object(smoke, 'run'):
                with self.assertRaisesRegex(ValueError, 'missing tool'):
                    smoke.extract_pinned_ifw(archive, extractor, extractor_hash, root / 'tools')

    @unittest.skipUnless(shutil.which('cmake'), 'CMake is not installed in this source-only environment')
    def test_cmake_offline_inputs_are_all_or_none_and_fail_closed(self):
        cmake = shutil.which('cmake')
        with tempfile.TemporaryDirectory(prefix='ifw cmake options ') as directory:
            root = Path(directory)
            archive, extractor = root / 'ifw.7z', root / '7z.exe'
            archive.write_bytes(b'archive'); extractor.write_bytes(b'extractor')
            output = root / 'arguments.txt'; script = root / 'check.cmake'
            module = (ROOT / 'cmake/PjIfwTestOptions.cmake').as_posix()
            script.write_text(f'include("{module}")\nfile(WRITE "{output.as_posix()}" "${{PJ_IFW_TEST_ARGS}}")\n', encoding='utf-8')
            def call(*args):
                return subprocess.run([cmake, *args, '-P', str(script)], capture_output=True, text=True)
            self.assertEqual(call().returncode, 0)
            self.assertEqual(output.read_text(encoding='utf-8'), '')
            archive_arg = '-DPJ_IFW_TEST_ARCHIVE=' + str(archive)
            extractor_arg = '-DPJ_IFW_TEST_EXTRACTOR=' + str(extractor)
            digest_arg = '-DPJ_IFW_TEST_EXTRACTOR_SHA256=' + 'A' * 64
            valid = call(archive_arg, extractor_arg, digest_arg)
            self.assertEqual(valid.returncode, 0, valid.stderr)
            self.assertIn('--extractor-sha256;' + 'a' * 64, output.read_text(encoding='utf-8'))
            partial = call(archive_arg)
            self.assertNotEqual(partial.returncode, 0)
            self.assertIn('require archive, extractor and extractor SHA-256 together', partial.stderr)
            self.assertNotEqual(call(archive_arg, extractor_arg, '-DPJ_IFW_TEST_EXTRACTOR_SHA256=wrong').returncode, 0)
            self.assertNotEqual(call('-DPJ_IFW_TEST_ARCHIVE=' + str(root / 'missing'), extractor_arg, digest_arg).returncode, 0)
            for key in ('ARCHIVE', 'EXTRACTOR', 'EXTRACTOR_SHA256'):
                for value in ('0', 'OFF', 'NO', 'FALSE', 'a-NOTFOUND'):
                    with self.subTest(key=key, value=value):
                        result = call(f'-DPJ_IFW_TEST_{key}={value}')
                        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_missing_embedded_resource_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fixture.exe'
            content = bytearray(128)
            content[:2] = b'MZ'
            struct.pack_into('<I', content, 0x3c, 64)
            content[64:68] = b'PE\0\0'
            path.write_bytes(content)
            with self.assertRaisesRegex(ValueError, 'resource name missing'):
                smoke.verify_pe_resources(path)
            for name in ('ifw_zh_CN.qm', 'qt_zh_CN.qm', smoke.MARKER):
                content += name.encode('utf-16-be')
            path.write_bytes(content)
            smoke.verify_pe_resources(path)

    def test_non_pe_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'not-pe.exe'
            path.write_bytes(b'not a PE file')
            with self.assertRaisesRegex(ValueError, 'not a PE'):
                smoke.verify_pe_resources(path)


if __name__ == '__main__':
    unittest.main()
