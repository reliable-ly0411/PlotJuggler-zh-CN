# SPDX-License-Identifier: MPL-2.0
"""Source-level hosted screenshot-environment contract, not a Windows run."""
from pathlib import Path
import unittest


class ProducerScreenshotEnvironmentTest(unittest.TestCase):
    def test_inherited_paths_are_cleared_before_any_process(self):
        source = (Path(__file__).resolve().parents[1] / 'scripts/windows/prepare_native_ci.ps1').read_text(encoding='utf-8')
        clearing = "foreach ($name in @('PJ_GUI_ACCEPTANCE_DIR', 'PJ_UI_TEST_DUMP_DIR'))"
        action = "[Environment]::SetEnvironmentVariable($name, $null, 'Process')"
        self.assertLess(source.index(clearing), source.index(action))
        for later in ("Invoke-CiTempProbe 'before-plugin-preflight'", 'Invoke-Checked $builderPython',
                      "$env:PJ_GUI_ACCEPTANCE_DIR = Join-Path $build 'gui-acceptance'"):
            self.assertLess(source.index(action), source.index(later))
        self.assertNotIn('$env:PJ_UI_TEST_DUMP_DIR =', source)


if __name__ == '__main__':
    unittest.main()
