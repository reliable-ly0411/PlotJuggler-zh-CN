# SPDX-License-Identifier: MPL-2.0
"""Keep native bundle inventories, immutable registry bytes and notices aligned."""
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packaging/localization'))
from registry_inventory import read_inventory, stage_notices
from prepare_payload import CORE_PLUGINS


class RegistryInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.base = self.root / 'packaging/localization'
        self.base.mkdir(parents=True)
        for name in ['registry-lock.json', 'registry-provenance.json']:
            shutil.copy2(ROOT / 'packaging/localization' / name, self.base / name)
        shutil.copytree(ROOT / 'packaging/localization/registry-notices', self.base / 'registry-notices')

    def test_all_curated_native_plugins_are_locked_and_expected(self):
        registry, _ = read_inventory(self.root)
        entries = {x['id']: x for x in registry['extensions']}
        ps = (ROOT / 'packaging/installer/build_windows_installer.ps1').read_text(encoding='utf-8')
        block = re.search(r'\[string\[\]\]\$PluginIds = @\((.*?)\n  \)', ps, re.S).group(1)
        windows = re.findall(r'"([a-z0-9-]+)"', block)
        bash = (ROOT / 'packaging/appimage/build_appimage.sh').read_text(encoding='utf-8')
        block = re.search(r'BUNDLE_IDS=\((.*?)\n\)', bash, re.S).group(1)
        linux = [line.split('#', 1)[0].strip() for line in block.splitlines()]
        linux = [x for x in linux if x]
        self.assertEqual(set(windows), set(CORE_PLUGINS))
        self.assertEqual(set(linux), set(windows) | {'toolbox-assistant-agent', 'ros2-topic-subscriber'})
        self.assertIn('log-widget', entries)
        self.assertNotIn('log-widget', linux)  # The built-in Log panel replaces the legacy DSO.
        for platform, ids in [('windows-x86_64', windows), ('linux-x86_64', linux)]:
            for identifier in ids:
                self.assertIn(identifier, entries)
                self.assertRegex(entries[identifier]['platforms'][platform]['checksum'], r'^sha256:[0-9a-f]{64}$')

    def test_original_entries_and_four_supplements_have_separate_sources(self):
        registry, source = read_inventory(self.root)
        self.assertEqual(len(registry['extensions']), 34)
        self.assertEqual(len(source['sources'][0]['entries']), 30)
        self.assertEqual(set(source['sources'][1]['entries']),
                         {'candump-loader', 'influx-parser', 'navmap-parser', 'log-widget'})

    def test_missing_changed_or_duplicate_registry_entry_fails(self):
        path = self.base / 'registry-lock.json'
        original = json.loads(path.read_text(encoding='utf-8'))
        for mode in ['missing', 'changed', 'duplicate']:
            data = json.loads(json.dumps(original))
            if mode == 'missing':
                data['extensions'].pop()
            elif mode == 'changed':
                data['extensions'][0]['version'] = '999.0.0'
            else:
                data['extensions'].append(data['extensions'][0])
            path.write_text(json.dumps(data), encoding='utf-8')
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                read_inventory(self.root)

    def test_duplicate_provenance_fails(self):
        path = self.base / 'registry-provenance.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        data['sources'].append(data['sources'][0])
        path.write_text(json.dumps(data), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Duplicate registry provenance'):
            read_inventory(self.root)

    def test_full_notices_are_staged_and_tampering_rejected(self):
        dest = self.root / 'licenses'
        records = stage_notices(self.root, dest)
        self.assertEqual(len(records), 4)
        for record in records:
            self.assertEqual((dest / record['notices'] / 'LICENSE').read_bytes(),
                             (self.root / record['source']['path']).read_bytes())
        notice = self.root / records[0]['source']['path']
        notice.write_text('MIT', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'notice hash differs'):
            read_inventory(self.root)

    def test_staged_notices_describe_selected_plugins_without_mutating_provenance(self):
        dest = self.root / 'licenses'
        records = stage_notices(self.root, dest, plugin_ids=CORE_PLUGINS)
        self.assertEqual({record['component'] for record in records},
                         {'candump-loader', 'influx-parser', 'navmap-parser'})
        self.assertFalse((dest / 'registry-plugins/log-widget').exists())
        self.assertEqual(json.loads((dest / 'registry-provenance.json').read_text(encoding='utf-8')),
                         read_inventory(self.root)[1])


if __name__ == '__main__':
    unittest.main()
