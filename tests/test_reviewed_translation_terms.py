#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Guard reviewed UI wording by its full Qt lookup key, including plural form."""
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from check_translations_4x import catalog_messages, check_translation

ROOT = Path(__file__).resolve().parents[1]


class ReviewedTranslationTermsTest(unittest.TestCase):
    def test_reviewed_contextual_wording(self):
        fixture = json.loads((ROOT / 'pj_app/translations/reviewed_zh_CN.json').read_text(encoding='utf-8'))
        self.assertEqual(fixture['schema'], 1)
        self.assertEqual(fixture['language'], 'zh_CN')
        entries = fixture['entries']
        self.assertTrue(entries)
        keys = [(x['context'], x['source'], x['comment'], x['numerus']) for x in entries]
        self.assertEqual(len(keys), len(set(keys)), 'ambiguous reviewed lookup key')
        messages = catalog_messages(ET.parse(ROOT / 'pj_app/translations/plotjuggler4_zh_CN.ts').getroot())
        for entry, key in zip(entries, keys):
            with self.subTest(context=key[0], source=key[1]):
                self.assertIn(key, messages, 'source changed: review the wording contract, do not silently drop it')
                translated = messages[key].find('translation')
                self.assertIsNotNone(translated)
                self.assertNotIn(translated.get('type'), ('unfinished', 'obsolete', 'vanished'))
                forms = translated.findall('numerusform') if entry['numerus'] else [translated]
                self.assertEqual([''.join(form.itertext()) for form in forms], entry['translations'])
                for value in entry['translations']:
                    self.assertFalse(check_translation(entry['source'], value))

    def test_marketplace_registry_is_an_extension_catalog(self):
        for locale, word in (('zh_CN', '扩展清单'), ('zh_TW', '擴充功能清單')):
            catalog = ET.parse(ROOT / f'pj_app/translations/plotjuggler4_{locale}.ts').getroot()
            messages = catalog_messages(catalog)
            registry = {
                key: msg for key, msg in messages.items()
                if 'registry' in key[1].lower()
                and ('Marketplace' in key[0] or key[0] == 'PreferencesContent')
            }
            self.assertIn(('PJ::MarketplaceWindow', 'Loading registry...', '', False), registry)
            for key, message in registry.items():
                with self.subTest(locale=locale, context=key[0], source=key[1]):
                    self.assertIn(word, message.findtext('translation'))
                    self.assertNotRegex(message.findtext('translation'), '注册表|註冊表')

    def test_traditional_chart_zoom_actions_fit_data_ranges(self):
        catalog = ET.parse(ROOT / 'pj_app/translations/plotjuggler4_zh_TW.ts').getroot()
        messages = catalog_messages(catalog)
        for source, expected in (
            ('Zoom Out Horizontally', '水平縮放至完整範圍'),
            ('Zoom Out Vertically', '垂直縮放至可見資料範圍'),
        ):
            with self.subTest(source=source):
                message = messages['PJ::PlotWidget', source, '', False]
                self.assertEqual(message.findtext('translation'), expected)


if __name__ == '__main__':
    unittest.main()
