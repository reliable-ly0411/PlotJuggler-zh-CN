#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Guard explicit native display selection without weakening headless tests."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class NativeDisplayContractTest(unittest.TestCase):
    def test_native_ctest_preserves_qpa_boundaries_and_complete_evidence(self):
        for name in ('zh-4x-ci.yml', 'zh-4x-packages.yml'):
            with self.subTest(workflow=name):
                workflow = (ROOT / '.github/workflows' / name).read_text(encoding='utf-8')
                self.assertIn('permissions:\n  contents: read', workflow)
                lines = workflow.splitlines()
                ordinary = next(line for line in lines if 'env -u QT_QPA_PLATFORM ctest' in line)
                self.assertIn('-LE qrhi -E "$window_suite"', ordinary)
                native = [line for line in lines if 'QT_QPA_PLATFORM=windows' in line and 'ctest' in line]
                self.assertEqual(len(native), 3)
                self.assertTrue(any('-L qrhi ' in line and 'PJ_REQUIRE_GPU_TESTS=1' in line for line in native))
                self.assertTrue(any('-LE qrhi -R "$window_suite"' in line and 'PJ_REQUIRE_GPU_TESTS=1' in line
                                    for line in native))
                self.assertIn('MainWindowFileDrop(Loading)?Test', workflow)
                self.assertIn('--native-regressions build/native-widget-regressions.xml', workflow)
                self.assertIn('build/native-headless.xml build/native-qrhi.xml build/native-window.xml || status=1', workflow)
                self.assertIn('test "$status" -eq 0', workflow)
                self.assertEqual(workflow.count(
                    'QT_QPA_PLATFORM=xcb PJ_REQUIRE_GPU_TESTS=1 xvfb-run -a ctest --test-dir build '), 1)
                before_native = workflow.split('      - name: Run native tests', 1)[0]
                self.assertNotIn('QT_QPA_PLATFORM=windows', before_native)
                self.assertNotIn('QT_QPA_PLATFORM=xcb', before_native)
                self.assertIn('ctest --test-dir build-i18n ', before_native)

    def test_native_regressions_cover_both_drop_fixtures(self):
        from test_ctest_report_merge import gate
        source = (ROOT / 'pj_app/tests/main_window_file_drop_test.cpp').read_text(encoding='utf-8')
        drops = {'pj_app_gui_tests.' + suite + '.' + case for suite, case in
                 re.findall(r'TEST(?:_F)?\((MainWindowFileDrop\w+),\s*(\w+)\)', source)}
        self.assertEqual(len(drops), 7)
        self.assertEqual({name for name in gate.NATIVE_CASES if name.startswith('pj_app_gui_tests.')}, drops)
        self.assertEqual(len(gate.NATIVE_CASES), 9)

    def test_file_dialog_restores_memory_only_after_widget_initialization(self):
        source = (ROOT / 'pj_widgets/src/FileDialog.cpp').read_text(encoding='utf-8')
        constructor = source.split('FileDialog::FileDialog(QWidget* parent)', 1)[1].split('FileDialog::~', 1)[0]
        option = constructor.index('inner_->setOption(QFileDialog::DontUseNativeDialog)')
        for setter in ('inner_->setHistory(', 'inner_->setSidebarUrls('):
            self.assertLess(option, constructor.index(setter))
        markdown = (ROOT / 'pj_dialog_host/tests/widget_binding_test.cpp').read_text(encoding='utf-8')
        self.assertIn('QFontDatabase::systemFont(QFontDatabase::FixedFont).families()', markdown)
        self.assertIn('EXPECT_EQ(code.charFormat().fontFamilies().toStringList(), fixed_families)', markdown)

    def test_gui_runner_still_defaults_to_offscreen(self):
        main = (ROOT / 'cmake/test_mains/pj_test_main_gui.cpp').read_text(encoding='utf-8')
        self.assertIn('if (!qEnvironmentVariableIsSet("QT_QPA_PLATFORM"))', main)
        self.assertIn('qputenv("QT_QPA_PLATFORM", "offscreen")', main)
        gate = (ROOT / 'cmake/test_mains/pj_gpu_test_gate.h').read_text(encoding='utf-8')
        self.assertNotIn('pjPreferRealDisplayQpa', gate)
        self.assertIn('if (pjGpuRequiredByEnv())', gate)
        self.assertIn('GTEST_FAIL() << reason', gate)

    def test_x11_wayland_lifecycle_lanes_stay_separate(self):
        workflow = (ROOT / '.github/workflows/zh-4x-ci.yml').read_text(encoding='utf-8')
        lane = workflow.split('      - name: Verify native window lifetime on X11 and Wayland', 1)[1]
        self.assertIn('QT_QPA_PLATFORM=xcb xvfb-run -a ctest', lane)
        self.assertIn('env -u DISPLAY QT_QPA_PLATFORM=wayland ctest', lane)
        self.assertIn('export PJ_REQUIRE_GPU_TESTS=1 PJ_GRAPHICS_API=opengl', lane)


if __name__ == '__main__':
    unittest.main()
