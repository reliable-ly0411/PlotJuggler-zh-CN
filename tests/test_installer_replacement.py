#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Source/mocked checks; native Windows descendant tests run when available."""
import base64
import gzip
from pathlib import Path
import re
import tempfile
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]

class InstallerReplacementTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node unavailable')
    def test_production_slot(self):
        subprocess.run(['node', str(ROOT / 'tests/test_installer_replacement.js')], check=True, timeout=30)

    @unittest.skipUnless(shutil.which('pwsh') or shutil.which('powershell.exe'), 'PowerShell unavailable')
    def test_supervisor(self):
        shell = shutil.which('powershell.exe') or shutil.which('pwsh')
        subprocess.run([shell, '-NoProfile', '-NonInteractive', '-File', str(ROOT / 'tests/test_installer_replacement.ps1')], check=True, timeout=60)

    @unittest.skipUnless(shutil.which('pwsh') or shutil.which('powershell.exe'), 'PowerShell unavailable')
    def test_real_builder_embedding(self):
        shell = shutil.which('powershell.exe') or shutil.which('pwsh')
        builder = (ROOT / 'packaging/installer/build_windows_installer.ps1').read_text(encoding='utf-8')
        fragment = builder[builder.index('$guardBytes ='):builder.index('# Compile the component catalog')]
        with tempfile.TemporaryDirectory(prefix='replacement embed ') as directory:
            stage = Path(directory)
            source = ROOT / 'packaging/installer/packages/io.plotjuggler.application/meta/installscript.qs'
            shutil.copy2(source, stage / 'installscript.qs')
            script = stage / 'embed.ps1'
            script.write_text("$ErrorActionPreference='Stop'\nfunction Die($message) { throw $message }\n" +
                              "$installerRoot='" + str(ROOT / 'packaging/installer').replace("'", "''") + "'\n" +
                              "$stageMeta='" + str(stage).replace("'", "''") + "'\n" + fragment, encoding='utf-8')
            subprocess.run([shell, '-NoProfile', '-NonInteractive', '-File', str(script)], check=True, timeout=30)
            result = (stage / 'installscript.qs').read_text(encoding='utf-8')
            payload = re.search(r'var replacementGuard = "([A-Za-z0-9+/=]+)";', result).group(1)
            self.assertEqual(gzip.decompress(base64.b64decode(payload)),
                             (ROOT / 'packaging/installer/replacement_guard.ps1').read_bytes())

if __name__ == '__main__':
    unittest.main()
