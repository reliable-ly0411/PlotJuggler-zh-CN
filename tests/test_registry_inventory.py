# SPDX-License-Identifier: MPL-2.0
"""Keep native bundle inventories, immutable registry bytes and notices aligned."""
import copy
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packaging/localization'))
from registry_inventory import read_inventory, stage_notices
from prepare_payload import CORE_PLUGINS, expected_plugin_versions
from test_release_manifest import release_inventory_fixture
from verify_package import validate_installed_plugins, validate_release_inventory, verify_registry_notices


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
        baseline = 'docs/localization/upstream-baseline.json'
        (self.root / baseline).parent.mkdir(parents=True)
        shutil.copy2(ROOT / baseline, self.root / baseline)

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
        self.assertCountEqual(windows, CORE_PLUGINS)
        self.assertEqual(len(linux), len(set(linux)))
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

    def test_bundle_fails_when_required_platform_payload_is_absent(self):
        registry, _ = read_inventory(self.root)
        entry = next(record for record in registry['extensions'] if record['id'] == 'candump-loader')
        del entry['platforms']['linux-x86_64']
        with self.assertRaisesRegex(ValueError, 'candump-loader has no locked payload'):
            expected_plugin_versions(registry, 'linux-x86_64', 'fixture')

    def test_duplicate_curated_identity_or_unsupported_platform_fails(self):
        registry, _ = read_inventory(self.root)
        for duplicate in ('candump-loader', 'ardupilot-dataflash'):
            with mock.patch('prepare_payload.CORE_PLUGINS', ['candump-loader', duplicate]), \
                 self.assertRaisesRegex(ValueError, 'Duplicate curated plugin identity'):
                expected_plugin_versions(registry, 'windows-x86_64', 'fixture')
        with self.assertRaisesRegex(ValueError, 'Unsupported native package platform'):
            expected_plugin_versions(registry, 'invalid', 'fixture')

    def test_report_declaration_is_bound_to_curated_source_and_bin_pin(self):
        for windows, platform, count in ((True, 'windows-x86_64', 27), (False, 'linux-x86_64', 29)):
            record = release_inventory_fixture(windows)
            expected, _ = validate_release_inventory(record, self.root, platform)
            self.assertEqual(len(expected), count)
            self.assertNotIn('log-widget', expected)
            self.assertEqual('ros2-topic-subscriber' in expected, not windows)
            self.assertEqual('toolbox-assistant-agent' in expected, not windows)
            for key, replacement in (
                    ('expected_plugins', record['expected_plugins'][1:]),
                    ('expected_plugins', record['expected_plugins'] + record['expected_plugins'][:1]),
                    ('expected_plugins', ['log-widget=1.0.0'] + record['expected_plugins'][1:]),
                    ('expected_plugins', ['ardupilot-dataflash=bad' if spec.startswith('ardupilot-dataflash=')
                                          else spec for spec in record['expected_plugins']]),
                    ('bin_plugin_commit', 'bad'), ('bin_plugin_version', 'bad'), ('bin_plugin_license', 'bad'),
                    ('registry_sources', record['registry_sources'][:1])):
                changed = copy.deepcopy(record)
                changed[key] = replacement
                with self.subTest(platform=platform, field=key), self.assertRaises(ValueError):
                    validate_release_inventory(changed, self.root, platform)

    def test_installed_manifests_reject_missing_extra_duplicate_wrong_version_and_wrong_location(self):
        record = release_inventory_fixture(False)
        expected, _ = validate_release_inventory(record, self.root, 'linux-x86_64')
        installed = self.root / 'plugins'

        def plugin(identifier, version, *, folder=None, license='LGPL-3.0-only'):
            path = installed / (folder or identifier) / 'manifest.json'
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({'id': identifier, 'version': version, 'license': license}), encoding='utf-8')
            return path

        paths = sorted(plugin(key, value) for key, value in expected.items())
        self.assertEqual(validate_installed_plugins(paths, expected), sorted(record['expected_plugins']))
        with self.assertRaisesRegex(ValueError, 'missing='):
            validate_installed_plugins(paths[1:], expected)
        legacy = plugin('log-widget', '1.0.0')
        with self.assertRaisesRegex(ValueError, r"extra=\['log-widget'\]"):
            validate_installed_plugins([*paths, legacy], expected)
        with self.assertRaisesRegex(ValueError, 'Duplicate installed plugin'):
            validate_installed_plugins([*paths, paths[0]], expected)
        misplaced = plugin('csv-loader', expected['csv-loader'], folder='wrong-directory')
        with self.assertRaisesRegex(ValueError, 'differs from its directory'):
            validate_installed_plugins([misplaced, *paths], expected)
        plugin('csv-loader', '999.0.0')
        with self.assertRaisesRegex(ValueError, r"version_mismatches=\['csv-loader'\]"):
            validate_installed_plugins(paths, expected)
        plugin('csv-loader', expected['csv-loader'])
        plugin('ardupilot-dataflash', expected['ardupilot-dataflash'], license='unknown')
        with self.assertRaisesRegex(ValueError, 'Installed BIN plugin license'):
            validate_installed_plugins(paths, expected)

    def test_shipped_supplement_notices_and_registry_sources_bound_to_source(self):
        expected, provenance = validate_release_inventory(
            release_inventory_fixture(True), self.root, 'windows-x86_64')
        dest = self.root / 'licenses'
        records = stage_notices(self.root, dest, plugin_ids=expected)
        self.assertEqual(len(records), 3)
        verify_registry_notices(dest, provenance, expected)
        path = dest / 'registry-provenance.json'
        original = path.read_bytes()
        path.write_text('{}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Shipped registry provenance differs'):
            verify_registry_notices(dest, provenance, expected)
        path.write_bytes(original)
        path = dest / 'registry-plugins/candump-loader/LICENSE'
        path.write_text('modified license', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Shipped registry notice differs'):
            verify_registry_notices(dest, provenance, expected)
        path.unlink()
        with self.assertRaises(FileNotFoundError):
            verify_registry_notices(dest, provenance, expected)

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
