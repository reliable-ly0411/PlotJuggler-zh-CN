# SPDX-License-Identifier: MPL-2.0
"""Pre-execution official Python source checks; no user VM is used."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/windows/verify_embedded_python_origin.ps1'


class EmbeddedPythonOriginTests(unittest.TestCase):
    def test_script_is_ci_only_and_uses_the_reviewed_fixed_official_pin(self):
        text = SCRIPT.read_text(encoding='utf-8')
        pins = json.loads((ROOT / '.github/windows-native-kit/tool-pins.json').read_text(encoding='utf-8'))
        pin = next(item for item in pins['artifacts'] if item['name'] == 'python')
        self.assertIn(pin['url'], text)
        self.assertIn(pin['sha256'], text)
        self.assertIn("$env:RUNNER_ENVIRONMENT -cne 'github-hosted'", text)
        self.assertIn("[IO.FileMode]::CreateNew", text)
        self.assertIn("Get-StreamSha256", text)
        self.assertIn("python312._pth", text)
        self.assertNotIn('ExecutionPolicy Bypass', text)

    @unittest.skipUnless(os.name == 'nt' and (shutil.which('pwsh.exe') or shutil.which('powershell.exe')),
                         'Real PowerShell/.NET ZIP comparison requires Windows')
    def test_actual_dotnet_compare_accepts_exact_zip_and_rejects_tampering(self):
        shell = shutil.which('pwsh.exe') or shutil.which('powershell.exe')
        with tempfile.TemporaryDirectory(prefix='pj-python-origin-') as temp:
            base = Path(temp); python = base / 'python'; python.mkdir(); archive = base / 'official.zip'
            files = {'python.exe': b'exe', 'python3.dll': b'dll3', 'python312.dll': b'dll312',
                     'python312.zip': b'stdlib', 'LICENSE.txt': b'license', '_ssl.pyd': b'module',
                     'vcruntime140.dll': b'redistributable', 'libcrypto-3.dll': b'crypto',
                     'libssl-3.dll': b'ssl', 'libffi-8.dll': b'ffi', 'sqlite3.dll': b'sqlite'}
            with zipfile.ZipFile(archive, 'w') as package:
                for name, data in files.items():
                    package.writestr(name, data)
                    (python / name).write_bytes(data)
            (python / 'python312._pth').write_text('python312.zip\n.\n', encoding='utf-8')
            command = (". '" + str(SCRIPT).replace("'", "''") + "'; "
                       "Add-Type -AssemblyName System.IO.Compression.FileSystem; "
                       "$rows = @(Compare-EmbeddedPythonDistribution $env:TEST_ZIP $env:TEST_PYTHON); "
                       "if ($rows.Count -ne 11) { throw 'wrong verified member count' }")
            env = dict(os.environ, TEST_ZIP=str(archive), TEST_PYTHON=str(python))
            def call():
                return subprocess.run([shell, '-NoProfile', '-NonInteractive', '-Command', command],
                                      env=env, capture_output=True, text=True, timeout=60)
            self.assertEqual(call().returncode, 0)
            (python / 'python312.dll').write_bytes(b'bad')
            self.assertNotEqual(call().returncode, 0)
            (python / 'python312.dll').write_bytes(files['python312.dll'])
            (python / '_ssl.pyd').unlink()
            self.assertNotEqual(call().returncode, 0)
            (python / '_ssl.pyd').write_bytes(files['_ssl.pyd'])
            (python / 'libcrypto-3.dll').unlink()
            self.assertNotEqual(call().returncode, 0)
            (python / 'libcrypto-3.dll').write_bytes(files['libcrypto-3.dll'])
            (python / 'unknown.exe').write_bytes(b'new')
            self.assertNotEqual(call().returncode, 0)
            # An unreviewed digest is rejected before any HTTP operation.
            invalid = (". '" + str(SCRIPT).replace("'", "''") + "'; "
                       "Save-BoundedOfficialZip 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip' "
                       "$env:OUTFILE '" + '0' * 64 + "'")
            result = subprocess.run([shell, '-NoProfile', '-NonInteractive', '-Command', invalid],
                                    env=dict(env, OUTFILE=str(base / 'must-not-download.zip')),
                                    capture_output=True, text=True, timeout=60)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((base / 'must-not-download.zip').exists())


if __name__ == '__main__':
    unittest.main()
