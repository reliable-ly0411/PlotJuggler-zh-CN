# SPDX-License-Identifier: MPL-2.0
"""Keep browser expectations bound to exact Qt contexts and both catalogs."""
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


class WasmUiTranslationTest(unittest.TestCase):
    def test_display_expectations_match_finished_catalog_entries(self):
        expected = json.loads((ROOT / 'tests/wasm/support/ui_translations.json').read_text(encoding='utf-8'))
        for language in ('zh_CN', 'zh_TW'):
            root = ET.parse(ROOT / f'pj_app/translations/plotjuggler4_{language}.ts').getroot()
            messages = {(context.findtext('name'), message.findtext('source')): message
                        for context in root.findall('context') for message in context.findall('message')}
            for context, entries in expected.items():
                for source, translations in entries.items():
                    with self.subTest(language=language, context=context, source=source):
                        translation = messages[(context, source)].find('translation')
                        self.assertNotIn(translation.get('type'), ('unfinished', 'vanished', 'obsolete'))
                        forms = translation.findall('numerusform')
                        self.assertLessEqual(len(forms), 1)
                        self.assertEqual(translations[language], forms[0].text if forms else translation.text)


if __name__ == '__main__':
    unittest.main()
