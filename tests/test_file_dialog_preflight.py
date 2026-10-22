# SPDX-License-Identifier: MPL-2.0
"""The diagnostic entry is opt-in and compiles real production dialog sources."""
from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[1]
class FileDialogPreflightPolicy(unittest.TestCase):
    def test_exact_first_creation_only(self):
        text = (ROOT / '.github/workflows/zh-4x-dialog-preflight.yml').read_text(encoding='utf-8')
        branch = 'zh-CN-4.x-ci/dialog-preflight-rc2-final8-fixed'
        self.assertIn("branches: ['" + branch + "']", text)
        self.assertIn("github.event.created && github.ref_name == '" + branch + "'", text)
        self.assertIn('contents: read', text)
        self.assertNotIn('contents: write', text)
        self.assertNotIn('conan install', text)
        self.assertNotIn('gh release', text)
    def test_actual_dialog_sources_without_sdk(self):
        text = (ROOT / 'pj_widgets/tests/standalone/CMakeLists.txt').read_text(encoding='utf-8')
        for source in ['FileDialog.cpp', 'Dialog.cpp', 'FrameworkTokens.cpp', 'SideDrawer.cpp', 'Scrollbar.cpp']:
            self.assertIn('../../src/' + source, text)
        self.assertNotIn('plotjuggler_sdk', text)
        self.assertIn('Qt6::Svg', text)
        self.assertIn('/utf-8', text)
        self.assertNotIn('CMAKE_CXX_FLAGS', text)
if __name__ == '__main__':
    unittest.main()
