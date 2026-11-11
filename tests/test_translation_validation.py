# SPDX-License-Identifier: MPL-2.0
import unittest
import xml.etree.ElementTree as ET
from check_translations import validate


class TranslationValidation(unittest.TestCase):
    def message(self, source, translation, **attributes):
        root = ET.Element("TS")
        context = ET.SubElement(root, "context")
        ET.SubElement(context, "name").text = "TestContext"
        message = ET.SubElement(context, "message", attributes)
        ET.SubElement(message, "source").text = source
        ET.SubElement(message, "translation").text = translation
        return root, message

    def test_complete_translation(self):
        root, _ = self.message("Open %1", "開啟 %1")
        self.assertEqual(validate(root)[0], [])

    def test_placeholder_count_and_localized_placeholder(self):
        for source, translation in (("%1 %1", "%1"), ("%L1", "%1"), ("%n", "%1")):
            root, _ = self.message(source, translation)
            self.assertTrue(validate(root)[0])

    def test_obsolete_and_unfinished(self):
        for kind in ("obsolete", "vanished", "unfinished"):
            root, message = self.message("Open", "開啟")
            message.find("translation").set("type", kind)
            self.assertTrue(validate(root)[0])

    def test_shortcut_and_mnemonic(self):
        for source, translation in (("Ctrl+S", "Ctrl+O"), ("&Save", "儲存")):
            root, _ = self.message(source, translation)
            self.assertTrue(validate(root)[0])

    def test_rich_text_and_url(self):
        for translated in ('<p>開啟</p>', '<p><a href="https://invalid.example/">開啟</a></p>'):
            root, _ = self.message('<p><a href="https://example.com/">Open</a></p>', translated)
            self.assertTrue(validate(root)[0])

    def test_stylesheet_and_identifier(self):
        root, _ = self.message('<p id="stable" style="font-size:12pt">Open</p>',
                               '<p id="changed" style="font-size:14pt">開啟</p>')
        self.assertTrue(validate(root)[0])

    def test_chinese_plural_form(self):
        root, message = self.message("%n file(s)", None, numerus="yes")
        translation = message.find("translation")
        self.assertTrue(validate(root)[0])
        ET.SubElement(translation, "numerusform").text = "%n 個檔案"
        self.assertEqual(validate(root)[0], [])
        ET.SubElement(translation, "numerusform").text = "%n 個檔案"
        self.assertTrue(validate(root)[0])

    def test_duplicate_keys(self):
        root, message = self.message("Open", "開啟")
        root.find("context").append(message)
        self.assertTrue(validate(root)[0])


if __name__ == "__main__":
    unittest.main()
