# SPDX-License-Identifier: MPL-2.0
"""Final packages must match independently pinned source identities."""
import copy
import json
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packaging/localization'))
from prepare_payload import CORE_PLUGINS
from registry_inventory import read_inventory
from verify_package import validate_installed_inventory

class PackageInventoryTests(unittest.TestCase):
    def fixture(self, windows):
        lock, provenance = read_inventory(ROOT)
        ids = set(CORE_PLUGINS) | (set() if windows else {'toolbox-assistant-agent', 'ros2-topic-subscriber'})
        plugins = [{'id': x['id'], 'version': x['version']} for x in lock['extensions'] if x['id'] in ids]
        version = json.loads((ROOT / 'docs/localization/upstream-baseline.json').read_text(encoding='utf-8'))['ardupilot_plugin']['version']
        plugins.append({'id': 'ardupilot-dataflash', 'version': version})
        record = {'bin_plugin_version': version, 'expected_plugins': [f"{x['id']}={x['version']}" for x in plugins], 'registry_sources': provenance['sources']}
        return plugins, record

    def test_exact_source_inventory_on_both_platforms(self):
        for windows, count in [(True, 28), (False, 30)]:
            with self.subTest(windows=windows):
                plugins, record = self.fixture(windows)
                self.assertEqual(len(validate_installed_inventory(plugins, record, ROOT, windows)), count)

    def test_missing_extra_duplicate_and_wrong_version_fail_even_if_release_agrees(self):
        for windows in (True, False):
            for mode in ('missing', 'extra', 'duplicate', 'version'):
                with self.subTest(windows=windows, mode=mode):
                    plugins, record = self.fixture(windows)
                    if mode == 'missing': plugins.pop(0)
                    if mode == 'extra': plugins.append({'id': 'unexpected-plugin', 'version': '1.0.0'})
                    if mode == 'duplicate': plugins.append(copy.deepcopy(plugins[0]))
                    if mode == 'version': plugins[0]['version'] = '999.0.0'
                    record['expected_plugins'] = [f"{x['id']}={x['version']}" for x in plugins]
                    with self.assertRaisesRegex(AssertionError, 'source lock'):
                        validate_installed_inventory(plugins, record, ROOT, windows)

    def test_release_inventory_provenance_and_bin_pin_must_match(self):
        for key, value in [('expected_plugins', []), ('registry_sources', []), ('bin_plugin_version', '999.0.0')]:
            with self.subTest(key=key):
                plugins, record = self.fixture(True)
                record[key] = value
                with self.assertRaises(AssertionError):
                    validate_installed_inventory(plugins, record, ROOT, True)

if __name__ == '__main__':
    unittest.main()
