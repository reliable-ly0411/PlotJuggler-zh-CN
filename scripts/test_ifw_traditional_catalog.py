#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Check the dormant Traditional Chinese installer catalogs without Qt."""
from collections import Counter
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "packaging" / "installer"
PAIRS = (
    (BASE / "translations" / "ifw_zh_CN.ts",
     BASE / "translations" / "ifw_zh_TW.ts", 700),
    (BASE / "packages" / "io.plotjuggler.application" / "meta" / "zh_CN.ts",
     BASE / "packages" / "io.plotjuggler.application" / "meta" / "zh_TW.ts", 14),
)
PLACEHOLDERS = re.compile(r"%(?:L?[1-9][0-9]*|n)")
RICH_TAGS = re.compile(r"</?(?:html|body|p|br|font|b|i|u|a|span)\b[^>]*>", re.I)


def entries(root):
    result = []
    for context in root.findall("context"):
        name = context.findtext("name", "")
        for message in context.findall("message"):
            key = (name, message.findtext("source", ""),
                   message.findtext("comment", ""), message.get("numerus", "no"))
            result.append((key, message))
    return result


class TraditionalInstallerCatalogTest(unittest.TestCase):
    def test_exact_source_inventory(self):
        for source, translated, count in PAIRS:
            with self.subTest(path=str(translated)):
                original = entries(ET.parse(source).getroot())
                target = entries(ET.parse(translated).getroot())
                self.assertEqual(len(original), count)
                self.assertEqual(len(target), count)
                self.assertEqual([key for key, _ in original],
                                 [key for key, _ in target])

    def test_finished_nonempty_translations_and_numerus(self):
        for _, path, _ in PAIRS:
            root = ET.parse(path).getroot()
            self.assertEqual(root.get("language"), "zh_TW")
            for key, message in entries(root):
                with self.subTest(path=str(path), key=key):
                    value = message.find("translation")
                    self.assertIsNotNone(value)
                    self.assertNotIn(value.get("type"), ("unfinished", "obsolete", "vanished"))
                    forms = value.findall("numerusform")
                    if key[3] == "yes":
                        self.assertEqual(len(forms), 1)
                    else:
                        self.assertEqual(len(forms), 0)
                    for form in forms or [value]:
                        self.assertTrue("".join(form.itertext()).strip())

    def test_placeholders_and_markup(self):
        for _, path, _ in PAIRS:
            for key, message in entries(ET.parse(path).getroot()):
                source = key[1]
                value = message.find("translation")
                for form in value.findall("numerusform") or [value]:
                    translated = "".join(form.itertext())
                    with self.subTest(path=str(path), key=key):
                        self.assertEqual(Counter(PLACEHOLDERS.findall(source)),
                                         Counter(PLACEHOLDERS.findall(translated)))
                        self.assertEqual(RICH_TAGS.findall(source),
                                         RICH_TAGS.findall(translated))

    def test_keyboard_accelerators(self):
        for _, path, _ in PAIRS:
            for key, message in entries(ET.parse(path).getroot()):
                value = message.find("translation")
                translated = "".join(value.itertext())
                source_keys = re.findall(r"(?<!&)&([A-Za-z])", key[1])
                target_keys = re.findall(r"(?<!&)&([A-Za-z])", translated)
                with self.subTest(path=str(path), key=key):
                    self.assertEqual([s.lower() for s in source_keys],
                                     [s.lower() for s in target_keys])


if __name__ == "__main__":
    unittest.main()
