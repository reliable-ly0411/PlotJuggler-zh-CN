#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Cross-platform unit checks, not the Windows integration result."""
import base64
import gzip
import re
import shutil
import subprocess
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest
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

    def test_mesa_stage_gate_invocation_and_failure_propagation(self):
        """Exercise only the external gate, never treat a synthetic stage as accepted."""
        shell = shutil.which('pwsh') or shutil.which('powershell')
        if not shell:
            self.skipTest('PowerShell unavailable; real Windows stage not exercised')
        builder = (ROOT / 'packaging/installer/build_windows_installer.ps1').read_text(encoding='utf-8')
        start = builder.index('# Check the actual deployed helper DLL')
        block = builder[start:builder.index('# --- build the installer', start)]
        quote = lambda path: "'" + str(path).replace("'", "''") + "'"
        with tempfile.TemporaryDirectory() as directory:
            setup = ("$ErrorActionPreference='Stop'; $ExtraPrefix=$true; "
                     f"$stageData={quote(directory)}; $PSScriptRoot={quote(ROOT / 'packaging/installer')}; "
                     f"$expectedHelper={quote(ROOT / 'packaging/localization/windows_mesa_notices.py')}; "
                     "$script:helperCalls=0; "
                     "function Die([string]$message) { throw $message }; "
                     "function python { if ($args.Count -ne 3 -or "
                     "[IO.Path]::GetFullPath($args[0]) -cne $expectedHelper -or "
                     "$args[1] -cne '--prefix' -or $args[2] -cne $stageData) "
                     "{ throw 'Unexpected verifier invocation' }; "
                     "$script:helperCalls++; Write-Output 'EXACT_MESA_GATE_CALLED'; "
                     "$global:LASTEXITCODE=$helperExit }; ")
            for code in (23, 0):
                script = setup + f"$helperExit={code};\n" + block
                script += "\nif ($helperCalls -ne 1) { throw 'Expected one gate call' }"
                run = subprocess.run([shell, '-NoProfile', '-NonInteractive', '-Command', script],
                                     capture_output=True, text=True, timeout=30)
                self.assertEqual(run.stdout.count('EXACT_MESA_GATE_CALLED'), 1, run.stdout + run.stderr)
                if code:
                    self.assertNotEqual(run.returncode, 0)
                    self.assertIn('Windows Mesa notice verification failed.', run.stderr)
                else:
                    self.assertEqual(run.returncode, 0, run.stdout + run.stderr)

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
