# SPDX-License-Identifier: MPL-2.0
"""Guard the Windows compiler invocation for the real catalog widget fixture."""

import ast
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class WindowsRuntimeWidgetFixtureTest(unittest.TestCase):
    def test_localized_name_never_enters_compiler_definitions(self):
        cmake = (ROOT / 'pj_app/CMakeLists.txt').read_text(encoding='utf-8')
        match = re.search(
            r'target_compile_definitions\(catalog_language_widget_plugin\s+PRIVATE\s+(.*?)\)',
            cmake, re.DOTALL,
        )
        self.assertIsNotNone(match)
        definitions = match.group(1)
        self.assertIn('PJ_TEST_WIDGET_LANGUAGE_FIXTURE', definitions)
        self.assertNotIn('PJ_TEST_WIDGET_NAME', definitions)
        self.assertNotIn('%', definitions)
        self.assertTrue(definitions.isascii())
        self.assertIn('target_compile_options(catalog_language_widget_plugin PRIVATE /utf-8)', cmake)

    def test_localized_bytes_and_runtime_assertions_are_preserved(self):
        fixture = (ROOT / 'pj_runtime/tests/runtime_widget_plugin.cpp').read_text(encoding='utf-8')
        match = re.search(
            r'#ifdef PJ_TEST_WIDGET_LANGUAGE_FIXTURE\s+(?://[^\n]*\s+)?'
            r'#define PJ_TEST_WIDGET_NAME "([^"\n]+)"', fixture,
        )
        self.assertIsNotNone(match)
        self.assertEqual(ast.literal_eval('b"' + match.group(1) + '"'),
                         'Unicode \u5143\u4ef6 from %2'.encode('utf-8'))
        test = (ROOT / 'pj_app/tests/runtime_catalog_language_test.cpp').read_text(encoding='utf-8')
        self.assertIn('std::string("Unicode \u5143\u4ef6 from %2")', test)
        self.assertIn('u"/\u8cc7\u6599 from %1"_s', test)
        self.assertIn('expected_utf8.find("\u8cc7\u6599 from %1")', test)
        self.assertIn('{u"en_US"_s, u"zh_CN"_s, u"zh_TW"_s}', test)


if __name__ == '__main__':
    unittest.main()
