# SPDX-License-Identifier: MPL-2.0
"""Stdlib coverage unit checks for the actual catalog glyph policy."""
import importlib.util
from io import StringIO
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('cjk', ROOT / 'scripts/check_cjk_font_coverage.py')
CJK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CJK)


class CjkCoverageTest(unittest.TestCase):
    def test_actual_symbols_are_checked_without_requiring_placeholder_ranges(self):
        text = '中文▸：\n\t\u200e'
        covered = set(map(ord, '中文▸：'))
        CJK.check_coverage(text, covered)
        self.assertNotIn(0xFF00, CJK.required_codepoints(text))
        with self.assertRaisesRegex(ValueError, r'U\+25B8'):
            CJK.check_coverage(text, covered - {0x25B8})

    def test_unassigned_character_actually_present_is_rejected(self):
        with self.assertRaisesRegex(ValueError, r'U\+0378'):
            CJK.check_coverage('中文\u0378', set(map(ord, '中文')))

    def test_only_active_translations_contribute(self):
        catalog = StringIO("""<TS>
          <message><translation>現行▸</translation></message>
          <message><translation type="unfinished">U</translation></message>
          <message><translation type="vanished">V</translation></message>
          <message><translation type="obsolete">O</translation></message>
          <message><translation><numerusform>甲</numerusform><numerusform>乙</numerusform></translation></message>
        </TS>""")
        self.assertEqual(CJK.active_catalog_text(catalog), '現行▸甲乙')


if __name__ == '__main__':
    unittest.main()
