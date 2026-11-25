#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Content-bound fork identities and audited predecessor coverage."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKAGING = ROOT / 'packaging/localization'
spec = importlib.util.spec_from_file_location('localized_identity', PACKAGING / 'localized_plugin_identity.py')
identity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(identity)


class LocalizedSeedIdentityTest(unittest.TestCase):
    def test_exact_predecessors_and_registry_provenance(self):
        entries = json.loads(identity.LOCK.read_text(encoding='utf-8'))['builds']
        self.assertEqual(len(entries), 20)
        registry = {x['id']: x for x in json.loads((PACKAGING / 'registry-lock.json').read_text(encoding='utf-8'))['extensions']}
        keys = set()
        for entry in entries:
            key = (entry['id'], entry['version'], entry['platform'], entry['kind'])
            self.assertNotIn(key, keys)
            keys.add(key)
            self.assertEqual(len(entry['files']), 1)
            self.assertRegex(entry['files'][0]['sha256'], r'^[0-9a-f]{64}$')
            if entry['kind'] == 'official-registry-artifact':
                artifact = registry[entry['id']]['platforms'][entry['platform']]
                self.assertEqual(entry['url'], artifact['url'])
                self.assertEqual('sha256:' + entry['archive_sha256'], artifact['checksum'])
                self.assertEqual(entry['version'], registry[entry['id']]['version'])
            else:
                self.assertEqual(entry['source_commit'], '09487081b7dc144c1bfaf674c4a08769e12538ad')
                self.assertTrue(entry['url'].endswith('/v4.0.0-zh.1.rc.2'))

    def test_new_marker_hashes_actual_bytes_and_selects_exact_platform(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            binary = directory / 'mcap_source_plugin.dll'
            binary.write_bytes(b'new localized build')
            marker = identity.write_identity(directory, {'id': 'mcap-loader', 'version': '1.3.0'}, 'Windows')
            self.assertEqual(marker['sha256'], hashlib.sha256(binary.read_bytes()).hexdigest())
            self.assertEqual(marker['dso'], binary.name)
            self.assertEqual(len(marker['legacy_sha256']), 2)
            self.assertEqual(json.loads((directory / identity.MARKER).read_text(encoding='utf-8')), marker)
            future = identity.write_identity(directory, {'id': 'mcap-loader', 'version': '9.0.0'}, 'Windows')
            self.assertEqual(future['legacy_sha256'], [])
            (directory / 'other.dll').write_bytes(b'other')
            with self.assertRaises(ValueError):
                identity.write_identity(directory, {'id': 'mcap-loader', 'version': '1.3.0'}, 'Windows')

    def test_csv_marker_accepts_only_audited_platform_and_version_predecessor(self):
        entries = json.loads(identity.LOCK.read_text(encoding='utf-8'))['builds']
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / 'csv_source_plugin.dll').write_bytes(b'synthetic repaired CSV DLL')
            for platform, key in [('Windows', 'windows-x86_64'), ('Linux', 'linux-x86_64')]:
                with self.subTest(platform=platform):
                    marker = identity.write_identity(directory, {'id': 'csv-loader', 'version': '1.0.7'}, platform)
                    expected = [entry['files'][0]['sha256'] for entry in entries
                                if (entry['id'], entry['version'], entry['platform']) == ('csv-loader', '1.0.7', key)]
                    self.assertEqual(len(expected), 1)
                    self.assertEqual(marker['legacy_sha256'], expected)
                    self.assertEqual(marker['sha256'], hashlib.sha256(b'synthetic repaired CSV DLL').hexdigest())
            for version in ['1.0.6', '1.0.8']:
                marker = identity.write_identity(directory, {'id': 'csv-loader', 'version': version}, 'Windows')
                self.assertEqual(marker['legacy_sha256'], [])

    def test_migration_avoids_loading_installed_dll_and_validates_staging(self):
        source = (ROOT / 'pj_runtime/src/ExtensionCatalogService.cpp').read_text(encoding='utf-8')
        self.assertLess(source.index('LocalizedPluginSeed::decide('), source.index('const std::optional<PluginDescriptor> installed = localized_migration'))
        self.assertIn('? std::optional<PluginDescriptor>{descriptor} : installedPluginDescriptor(dst, descriptor.id)', ' '.join(source.split()))
        self.assertIn('LocalizedPluginSeed::preserveFiles(dst, stage_new)', source)
        self.assertIn('installedDsoPath(stage_new, rel)', source)
        self.assertIn('LocalizedPluginSeed::begin(localized_seed_settings', source)
        self.assertIn('LocalizedPluginSeed::complete(localized_seed_settings', source)
        self.assertIn('nullptr, marketplace_dir_, pending_dir, sink_, this, true', source)
        self.assertLess(source.index('  seedBundledPlugins();'), source.index('extension_manager_->finishInitialScan();'))
        manager = (ROOT / 'pj_marketplace/src/core/ExtensionManager.cpp').read_text(encoding='utf-8')
        self.assertRegex(manager, r'if \(!defer_initial_scan\)\s*\{\s*finishInitialScan\(\);\s*\}')



if __name__ == '__main__':
    unittest.main()
