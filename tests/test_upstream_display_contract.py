#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Guard explicit native display selection without weakening headless tests."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class NativeDisplayContractTest(unittest.TestCase):
    def test_only_full_native_ctest_selects_a_real_platform(self):
        for name in ('zh-4x-ci.yml', 'zh-4x-packages.yml'):
            with self.subTest(workflow=name):
                workflow = (ROOT / '.github/workflows' / name).read_text(encoding='utf-8')
                self.assertIn('permissions:\n  contents: read', workflow)
                self.assertEqual(workflow.count('QT_QPA_PLATFORM=windows ctest --test-dir build '), 1)
                self.assertEqual(workflow.count(
                    'QT_QPA_PLATFORM=xcb PJ_REQUIRE_GPU_TESTS=1 xvfb-run -a ctest --test-dir build '), 1)
                before_native = workflow.split('      - name: Run native tests', 1)[0]
                self.assertNotIn('QT_QPA_PLATFORM=windows', before_native)
                self.assertNotIn('QT_QPA_PLATFORM=xcb', before_native)
                self.assertIn('ctest --test-dir build-i18n ', before_native)

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
