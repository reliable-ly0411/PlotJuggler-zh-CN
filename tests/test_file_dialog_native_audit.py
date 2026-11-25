#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Keep the Windows native picker check distinct from the offscreen suite."""
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packaging/localization'))
import audit_file_dialog_results as checker


class FileDialogNativeAuditTest(unittest.TestCase):
    def report(self):
        root = ET.Element('testsuite', tests='4', failures='0', disabled='0', skipped='0')
        for name in sorted(checker.CASES):
            case = ET.SubElement(root, 'testcase', name=name, status='run')
            ET.SubElement(case, 'system-out').text = (
                '[       OK ] ' + name.removeprefix('pj_widgets_tests.')
                + ' (23 ms)\n[  PASSED  ] 1 test.\n')
        return root

    def check(self, root):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'native.xml'
            ET.ElementTree(root).write(path, encoding='utf-8')
            return checker.audit(path)

    def test_four_complete_cases_pass(self):
        self.assertEqual(set(self.check(self.report())), checker.CASES)

    def test_suite_failures_and_skips_rejected(self):
        for field in ('tests', 'failures', 'errors', 'disabled', 'skipped'):
            root = self.report()
            root.set(field, '1')
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.check(root)

    def test_missing_duplicate_and_unknown_cases_rejected(self):
        for operation in ('missing', 'duplicate', 'unknown'):
            root = self.report()
            if operation == 'missing':
                root.remove(root[0])
            else:
                root[0].set('name', root[1].get('name') if operation == 'duplicate' else 'Other')
            with self.subTest(operation=operation), self.assertRaises(ValueError):
                self.check(root)

    def test_hidden_skips_failures_and_truncation_rejected(self):
        for text in ('', '[  PASSED  ] 1 test.', '[  SKIPPED ] hidden',
                     '[  FAILED  ] hidden', 'Output truncated',
                     '[This part of the test output was removed since it exceeds the threshold of 256 bytes.]'):
            root = self.report()
            output = root[0].find('system-out')
            output.text = text if text in ('', '[  PASSED  ] 1 test.') else output.text + text
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.check(root)
        for tag in ('failure', 'error', 'skipped'):
            root = self.report()
            ET.SubElement(root[0], tag)
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                self.check(root)

    def test_candidate_enforces_native_platform_and_retains_report(self):
        workflow = (ROOT / '.github/workflows/zh-4x-packages.yml').read_text(encoding='utf-8')
        self.assertIn('QT_QPA_PLATFORM=windows ctest', workflow)
        self.assertIn('--no-tests=error', workflow)
        self.assertIn('audit_file_dialog_results.py --junit build/native-file-dialog.xml', workflow)
        self.assertIn('            build/native-file-dialog.xml', workflow)


if __name__ == '__main__':
    unittest.main()
