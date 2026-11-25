# SPDX-License-Identifier: MPL-2.0
"""Source guards for bundle lookup order, not macOS package acceptance."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MacosPythonStartupTests(unittest.TestCase):
    def test_core_only_python_check_uses_bundle_before_starting_python(self):
        source = (ROOT / 'pj_app/src/main.cpp').read_text(encoding='utf-8')
        core = source.split('if (std::strcmp(argv[i], "--selftest-python") == 0)', 1)[1]
        core = core.split('return selftestPython();', 1)[0]
        self.assertLess(core.index('QCoreApplication app(argc, argv);'),
                        core.index('configureBundledPythonHome();'))
        self.assertIn('#if defined(Q_OS_MACOS)', core)
        self.assertNotIn('QApplication app(', core)

    def test_gui_uses_same_bundle_lookup_before_runtime_startup(self):
        source = (ROOT / 'pj_app/src/main.cpp').read_text(encoding='utf-8')
        gui = source.split('QApplication app(argc, argv);', 1)[1]
        self.assertLess(gui.index('configureBundledPythonHome();'),
                        gui.index('PJ::preferredGraphicsApi()'))
        self.assertIn('#if defined(Q_OS_MACOS)', gui.split('configureBundledPythonHome();', 1)[0])

    def test_bundle_lookup_respects_user_override_and_missing_directory(self):
        source = (ROOT / 'pj_app/src/main.cpp').read_text(encoding='utf-8')
        helper = source.split('void configureBundledPythonHome() {', 1)[1].split('\n#endif', 1)[0]
        self.assertIn('qEnvironmentVariableIsEmpty("PYTHONHOME")', helper)
        self.assertIn('QCoreApplication::applicationDirPath()', helper)
        self.assertIn('/../Resources/python', helper)
        self.assertLess(helper.index('QFileInfo(bundled_python).isDir()'),
                        helper.index('qputenv("PYTHONHOME"'))


if __name__ == '__main__':
    unittest.main()
