# SPDX-License-Identifier: MPL-2.0
"""Run installer JavaScript guards through the existing source-check suite."""
from pathlib import Path
import shutil
import subprocess
import unittest


class InstallerLanguageNodeTest(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node.js is needed for IFW script guards')
    def test_installer_language_restart(self):
        script = Path(__file__).with_name('test_installer_language_switch.js')
        subprocess.run([shutil.which('node'), str(script)], check=True, timeout=30)


if __name__ == '__main__':
    unittest.main()
