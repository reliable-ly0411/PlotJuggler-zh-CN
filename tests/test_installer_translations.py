#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Guard the IFW component catalog independently of the application catalog."""
import ast
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / 'packaging/installer/packages/io.plotjuggler.application/meta'


class InstallerTranslationsTest(unittest.TestCase):
    def test_every_script_template_is_translated(self):
        script = (META / 'installscript.qs').read_text()
        sources = {ast.literal_eval(value) for value in re.findall(
            r'qsTranslate\("PlotJugglerInstaller", ("(?:[^"\\]|\\.)*")\)', script)}
        catalog = ET.parse(META / 'zh_CN.ts').getroot()
        messages = catalog.find("context[name='PlotJugglerInstaller']").findall('message')
        self.assertEqual(sources, {m.findtext('source') for m in messages})
        self.assertGreaterEqual(len(sources), 8)
        for message in messages:
            translation = message.find('translation')
            self.assertIsNone(translation.get('type'))
            self.assertRegex(translation.text, r'[\u4e00-\u9fff]')
            self.assertEqual(re.findall(r'%[1-9]', message.findtext('source')),
                             re.findall(r'%[1-9]', translation.text))

    def test_catalog_is_built_and_registered(self):
        package = ET.parse(META / 'package.xml').getroot()
        self.assertIn('zh_CN.qm', [t.text for t in package.findall('Translations/Translation')])
        build = (ROOT / 'packaging/installer/build_windows_installer.ps1').read_text()
        self.assertIn('Resolve-Exe "lrelease.exe" (Split-Path $windeployqt -Parent)', build)
        self.assertIn('if (-not $lrelease)', build)
        self.assertIn('Installer translation compilation failed.', build)
        self.assertIn('zh_CN.ts', build)

    def test_no_placeholder_labels(self):
        strings = [e.text for e in ET.parse(META / 'targetwidget.ui').findall('.//string')]
        self.assertNotIn('TextLabel', strings)
        self.assertNotIn('Form', strings)

    def test_replacement_is_still_confirmed(self):
        script = (META / 'installscript.qs').read_text()
        self.assertIn('if (answer !== QMessageBox.Yes)', script)
        self.assertIn('gui.rejectPage(QInstaller.ComponentSelection)', script)
        self.assertLess(script.index('if (answer !== QMessageBox.Yes)'),
                        script.index('installer.execute(dir + "/maintenancetool.exe"'))


if __name__ == '__main__':
    unittest.main()
