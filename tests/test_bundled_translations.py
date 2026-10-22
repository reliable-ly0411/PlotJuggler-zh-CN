#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Deterministic pinned plugin mappings and C++ macro boundary regression guards."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import unittest
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('bundled_generator', ROOT / 'packaging/localization/generate_bundled_ui_translations.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)

class BundledTranslationTest(unittest.TestCase):
    def test_generated_source_current(self):
        self.assertEqual(generator.generated(), (ROOT / 'pj_dialog_host/src/bundled_translation_entries.hpp').read_text(encoding='utf-8'))

    def test_scope_and_fixture(self):
        data = json.loads((ROOT / 'packaging/localization/bundled-ui-translations.json').read_text(encoding='utf-8'))
        hashes = {ui['sha256'] for ui in data['uis']}
        self.assertEqual(len(hashes), len(data['uis']))
        digest = hashlib.sha256((ROOT / 'pj_dialog_host/tests/fixtures/csv_1_0_7.ui').read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        self.assertIn(digest, hashes)
        for row in data['exact'] + data['templates']:
            self.assertTrue(row['scope'] in hashes or re.fullmatch(r'plugin:[a-z0-9-]+@[0-9.]+', row['scope']))
            self.assertNotIn(row['property'], ['plainText', 'code', 'items', 'currentText'])
            if not row['widget']:
                self.assertEqual((row['scope'], row['property'], row['source']),
                    ('7c826680efbe07cb23b581828e3106ec10db69e9b000ef356981163ecd89fca0', 'text', 'Output:'))
            if row['property'] == 'pickerFilter':
                self.assertEqual(re.findall(r'\([^)]*\)', row['source']), re.findall(r'\([^)]*\)', row['translation']))
            if row['property'] == 'pj_context_actions':
                self.assertEqual([x.split('=', 1)[0] for x in row['source'].split(';')],
                                 [x.split('=', 1)[0] for x in row['translation'].split(';')])

    def test_marketplace_display_keeps_category_identity_and_escapes_details(self):
        source = (ROOT / 'pj_marketplace/src/ui/marketplace_window.cpp').read_text(encoding='utf-8')
        self.assertIn('category_item->setData(kCategoryTokenRole, ext.category)', source)
        self.assertIn('data(kCategoryTokenRole).toString(), other.data(kCategoryTokenRole).toString()', source)
        self.assertIn('category_item->setData(kCategoryNameKeyRole, ext.name)', source)
        self.assertIn('detail_title_->setText(PJ::marketplacePluginText(ext->id, ext->version, ext->name))', source)
        self.assertIn('esc(PJ::marketplacePluginText(ext->id, ext->version, ext->description))', source)
        self.assertIn('meta << esc(displayCategory(ext->category))', source)
        self.assertIn('return category;', source)
        self.assertIn('const ExtensionDiagnostic diagnostic = ext_mgr_->diagnostics().back();', source)

    def test_literal_macros_never_wrap_runtime_translation(self):
        bad = re.compile(r'(?:QStringLiteral|QLatin1String|QT_TRANSLATE_NOOP)\s*\(\s*(?:QCoreApplication::translate|(?:QObject::)?tr)\s*\(')
        for module in ROOT.glob('pj_*'):
            for source in module.rglob('*.cpp'):
                self.assertIsNone(bad.search(source.read_text(encoding='utf-8')), str(source))

    def test_native_build_remains_explicit(self):
        workflow = (ROOT / '.github/workflows/zh-4x-packages.yml').read_text(encoding='utf-8')
        self.assertIn("github.event_name == 'push' && github.event.created", workflow)
        self.assertIn("'zh-CN-4.x-ci/release-candidate-rc2-final8'", workflow)
        release_doc = (ROOT / 'packaging/localization/README.md').read_text(encoding='utf-8')
        self.assertIn('`zh-CN-4.x-ci/release-candidate-rc2-final8`', release_doc)
        self.assertNotIn("branches: ['zh-CN-4.x-*", workflow)
        condition = "github.event_name == 'workflow_dispatch' || (github.event_name == 'push' && github.event.created)"
        self.assertIn('    if: ' + condition, workflow)
        branches = re.search(r"branches: \[(.*?)\]", workflow).group(1)
        admitted = re.findall(r"'([^']+)'", branches)
        self.assertEqual(set(admitted), {'zh-CN-4.x-ci/release-candidate', 'zh-CN-4.x-ci/release-candidate-rc2-final8'})
        def runs(event, branch, created):
            trigger = event == 'workflow_dispatch' or (event == 'push' and branch in admitted)
            gate = event == 'workflow_dispatch' or (event == 'push' and created)
            return trigger and gate
        for branch in ['main', 'zh-CN-4.x-dev', 'zh-CN-4.x', 'zh-CN-4.x-ci/other']:
            self.assertFalse(runs('push', branch, True))
            self.assertFalse(runs('push', branch, False))
            self.assertFalse(runs('pull_request', branch, False))
        for branch in admitted:
            self.assertTrue(runs('push', branch, True))
            self.assertFalse(runs('push', branch, False))
        self.assertTrue(runs('workflow_dispatch', 'zh-CN-4.x-dev', False))


if __name__ == '__main__':
    unittest.main()
