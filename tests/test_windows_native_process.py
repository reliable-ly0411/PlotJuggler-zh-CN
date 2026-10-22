# SPDX-License-Identifier: MPL-2.0
import os
from pathlib import Path
import shutil
import subprocess
import unittest
import threading
import time

ROOT = Path(__file__).resolve().parents[1]

class NativeProcessTests(unittest.TestCase):
    def test_production_callers_use_explicit_process_result(self):
        builder = (ROOT/'packaging/installer/build_windows_installer.ps1').read_text(encoding='utf-8')
        validation = builder.split('# --- prove every whitelisted plugin loads', 1)[1].split('# --- render config.xml', 1)[0]
        self.assertIn('Invoke-PjNativeProcess -FilePath $stagedExe -ArgumentValues $validationArgs', validation)
        self.assertIn('$validation.ExitCode -ne 0', validation)
        self.assertIn('[Console]::Error.Write($validation.StandardError)', validation)
        self.assertNotIn('$LASTEXITCODE', validation)
        launcher = (ROOT/'scripts/windows/run.ps1').read_text(encoding='utf-8')
        self.assertIn('-FilePath $Bin -ArgumentValues $appArgs -InheritOutput', launcher)
        self.assertIn('exit $result.ExitCode', launcher)
        self.assertNotIn('& $Bin', launcher)

    @unittest.skipUnless(os.name == 'nt', 'Genuine GUI-subsystem regression requires Windows')
    def test_delayed_gui_under_available_powershell_versions(self):
        shells = [shutil.which(name) for name in ('powershell.exe', 'pwsh.exe')]
        self.assertTrue(any(shells), 'PowerShell runtime missing')
        for shell in dict.fromkeys(filter(None, shells)):
            with self.subTest(shell=Path(shell).name):
                command = [shell, '-NoProfile', '-NonInteractive', '-File',
                           str(ROOT/'tests/test_windows_native_process.ps1')]
                lines = []
                with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                      text=True, encoding='utf-8') as process:
                    def observe():
                        for line in process.stdout:
                            lines.append((time.monotonic(), line.rstrip()))
                    reader = threading.Thread(target=observe, daemon=True)
                    reader.start()
                    try:
                        code = process.wait(timeout=60)
                    except subprocess.TimeoutExpired:
                        process.kill()  # Only this test harness; never an installer/uninstaller.
                        raise
                    reader.join(timeout=5)
                self.assertEqual(code, 0, '\n'.join(line for _, line in lines))
                timings = {line: timestamp for timestamp, line in lines}
                self.assertIn('INHERITED-STDERR', timings)
                self.assertGreaterEqual(timings['INHERITED-END'] - timings['INHERITED-START'], .6,
                                        'Developer output was buffered until process exit')

if __name__ == '__main__': unittest.main()
