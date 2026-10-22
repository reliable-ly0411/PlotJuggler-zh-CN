#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Guard the IFW component catalog independently of the application catalog."""
import ast
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / 'packaging/installer/packages/io.plotjuggler.application/meta'


class InstallerTranslationsTest(unittest.TestCase):
    def test_every_script_template_is_translated(self):
        script = (META / 'installscript.qs').read_text(encoding='utf-8')
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
        self.assertIsNone(package.find('Translations'))  # OS locale must not override --lang.
        build = (ROOT / 'packaging/installer/build_windows_installer.ps1').read_text(encoding='utf-8')
        self.assertIn('Resolve-Exe "lrelease.exe" (Split-Path $windeployqt -Parent)', build)
        self.assertIn('if (-not $lrelease)', build)
        self.assertIn('(Join-Path $installerRoot "translations/ifw_zh_CN.ts") (Join-Path $stageMeta "zh_CN.ts") -qm', build)
        smoke = (ROOT / 'scripts/verify_windows_installer_resources.py').read_text(encoding='utf-8')
        self.assertIn("meta / 'zh_CN.ts', '-qm', translations / 'ifw_zh_CN.qm'", smoke)
        self.assertIn('zh_CN.ts', build)

    def test_standard_pages_are_explicit_resources(self):
        root = ROOT / 'packaging/installer'
        catalog = ET.parse(root / 'translations/ifw_zh_CN.ts').getroot()
        messages = catalog.findall('.//message')
        self.assertEqual(len(messages), 700)
        for message in messages:
            self.assertNotEqual(message.find('translation').get('type'), 'unfinished')
            self.assertTrue(message.findtext('translation'))
        config = ET.parse(root / 'config.xml').getroot()
        self.assertIsNone(config.find('Translations'))  # Must not bypass --lang.
        self.assertIn('zh-CN', config.findtext('Name'))
        self.assertTrue(config.findtext('TargetDir').endswith('/PlotJuggler4-zh-CN'))
        build = (root / 'build_windows_installer.ps1').read_text(encoding='utf-8')
        self.assertIn('prefix="/translations_new"', build)
        self.assertIn('--offline-only -r $translationQrc', build)
        self.assertIn('qtbase_zh_CN.qm', build)
        self.assertIn('requires Qt Installer Framework 4.10.0', build)

    def test_language_selection_is_registered(self):
        package = ET.parse(META / 'package.xml').getroot()
        self.assertIn('languagewidget.ui', [e.text for e in package.findall('UserInterfaces/UserInterface')])
        script = (META / 'installscript.qs').read_text(encoding='utf-8')
        self.assertIn('installer.addWizardPage(component, "LanguageWidget", QInstaller.TargetDirectory)', script)
        self.assertIn('Component.prototype.retranslateUi', script)
        self.assertIn('if (!installer.isInstaller() || installer.isCommandLineInstance())', script)

    def test_tool_discovery_uses_supported_version_command(self):
        build = (ROOT / 'packaging/installer/build_windows_installer.ps1').read_text(encoding='utf-8')
        self.assertIn('& $installerbase --version', build)
        self.assertNotIn('& $binarycreator --version', build)
        self.assertIn('if ($LASTEXITCODE -ne 0) { return $null }', build)
        self.assertIn('if ($IfwDir) {', build)
        self.assertLess(build.index('$pinned = Join-Path'), build.index('$found = Resolve-Exe $name'))
        self.assertIn('$ifwVersion = Get-IfwVersion $binarycreator', build)
        self.assertIn('It will not be replaced or bypassed', build)
        helper = (ROOT / 'packaging/installer/install_ifw.ps1').read_text(encoding='utf-8')
        self.assertIn('windows_x86/ifw/tools_ifw_410/qt.tools.ifw.410/', helper)
        self.assertIn('bf460f2f60b858d9bfb6c709fc4687fd6967856984bd730711df2c4df9dd49f2', helper)
        self.assertLess(helper.index('Get-FileHash $archive'), helper.index('& $extractor.Source x $archive'))
        self.assertIn('"-o$payload"', helper)  # One argument, even with spaces.
        self.assertIn('-OutFile $archive -ErrorAction Stop', helper)
        self.assertIn('finally {', helper)
        self.assertIn('Refusing to replace existing IFW directory', helper)

    def test_version_output_fixtures(self):
        build = (ROOT / 'packaging/installer/build_windows_installer.ps1').read_text(encoding='utf-8')
        pattern = re.search(r"if \(\$output -match '([^']+)'", build).group(1)
        for version in ('4.7.0', '4.10.0', '4.11.0'):
            output = f'IFW Version: {version}, built with Qt 6.7.2.\nBuild date: May 29 2025\nSHA1: example\n'
            self.assertEqual(re.search(pattern, output).group(1), version)
        self.assertIsNone(re.search(pattern, 'Unknown option: --version'))

    @unittest.skipUnless(shutil.which('pwsh') or shutil.which('powershell'), 'PowerShell runtime unavailable')
    def test_helper_download_failure_with_space_path(self):
        # Run real PowerShell control flow, replacing only network/tool discovery.
        # No network, executable download, or GUI is invoked by this test.
        shell = shutil.which('pwsh') or shutil.which('powershell')
        helper = str(ROOT / 'packaging/installer/install_ifw.ps1').replace("'", "''")
        with tempfile.TemporaryDirectory(prefix='ifw path with spaces ') as directory:
            dest = str(Path(directory) / 'new tools').replace("'", "''")
            script = f"""
function Get-Command {{ return [pscustomobject]@{{Source='unused-extractor'}} }}
function Invoke-WebRequest {{ throw 'simulated-download-failure' }}
try {{ & '{helper}' -Destination '{dest}'; throw 'unexpected-success' }}
catch {{ if ($_.Exception.Message -notlike '*simulated-download-failure*') {{ throw }} }}
if (Test-Path '{dest}') {{ throw 'Partial destination survived failed download' }}
"""
            run = subprocess.run([shell, '-NoProfile', '-NonInteractive', '-Command', script], capture_output=True, text=True, timeout=30)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_no_placeholder_labels(self):
        strings = [e.text for e in ET.parse(META / 'targetwidget.ui').findall('.//string')]
        self.assertNotIn('TextLabel', strings)
        self.assertNotIn('Form', strings)

    def test_replacement_is_still_confirmed(self):
        script = (META / 'installscript.qs').read_text(encoding='utf-8')
        self.assertIn('if (answer !== QMessageBox.Yes)', script)
        self.assertIn('gui.rejectPage(QInstaller.ComponentSelection)', script)
        self.assertLess(script.index('if (answer !== QMessageBox.Yes)'),
                        script.index('result = installer.execute(powershell'))


if __name__ == '__main__':
    unittest.main()
