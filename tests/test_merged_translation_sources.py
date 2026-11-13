#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Regression keys introduced/restored while merging the 4.1 release history."""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
KEYS = {
    'PJ::MainWindow': [
        "%1 is controlling PlotJuggler through MCP. Closing the agent's session or this page stops it.",
        'Not connecting to the AI agent relay %1: it must be an http address on this computer (127.0.0.1).',
    ],
    'PJ::PluginRuntimeCatalog': [
        f'Loaded {kind} %1 from %2' for kind in ('DataSource', 'MessageParser', 'Toolbox', 'Widget')
    ],
}


class MergedTranslationSourcesTest(unittest.TestCase):
    def test_six_merge_keys_are_translated_in_both_catalogs(self):
        for language in ('zh_CN', 'zh_TW'):
            root = ET.parse(ROOT / f'pj_app/translations/plotjuggler4_{language}.ts').getroot()
            for context, sources in KEYS.items():
                for source in sources:
                    with self.subTest(language=language, context=context, source=source):
                        matches = [m for c in root.findall('context') if c.findtext('name') == context
                                   for m in c.findall('message') if m.findtext('source') == source]
                        self.assertEqual(len(matches), 1)
                        translation = matches[0].find('translation')
                        self.assertIsNotNone(translation)
                        self.assertNotIn(translation.get('type'), ('unfinished', 'vanished', 'obsolete'))
                        self.assertTrue(translation.text)
                        self.assertNotEqual(translation.text, source)
                        for token in ('%1', '%2', '127.0.0.1', 'http', 'MCP', 'PlotJuggler'):
                            self.assertEqual(source.count(token), translation.text.count(token))


if __name__ == '__main__':
    unittest.main()
