# SPDX-License-Identifier: MPL-2.0
"""Exercise AppImage registry staging without Qt, network or a native rebuild."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'packaging/appimage/build_appimage.sh'
sys.path.insert(0, str(ROOT / 'packaging/localization'))
from registry_inventory import read_inventory
from verify_package import expected_plugin_inventory


@unittest.skipUnless(os.name != 'nt' and shutil.which('bash') and shutil.which('unzip'),
                     'POSIX AppImage shell tooling required')
class AppImageRegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive = self.root / 'plugin.zip'
        with zipfile.ZipFile(self.archive, 'w') as out:
            out.writestr('example/manifest.json', '{"id":"example"}')
        self.entry = {'id': 'example', 'version': '1.0.0', 'platforms': {'linux-x86_64': {
            'url': str(self.archive),
            'checksum': 'sha256:' + hashlib.sha256(self.archive.read_bytes()).hexdigest()}}}
        self.registry = self.root / 'locked registry.json'

    def stage(self, entries, remote=False, ids=('example',), payload=None):
        self.registry.write_text(json.dumps({'extensions': entries}), encoding='utf-8')
        source = SCRIPT.read_text(encoding='utf-8')
        func = source[source.index('collect_plugins_registry() {'):source.index('\n# ---------------------------------------------------------------------------\n# 4.')]
        # Only wget transport is mocked: hash checks, unzip and staging run normally.
        harness = '''set -euo pipefail
ROOT="$1"
REGISTRY_URL="$2"
APPDIR="$3"
REGISTRY_FIXTURE="$4"
EXTRA_PREFIX="$5"
PJ_PLUGINS_REL=usr/lib/plotjuggler/plugins
PLATFORM=linux-x86_64
BUNDLE_IDS=("${@:6}")
wget() {
  if [[ "$3" == https://example.test/registry.json ]]; then
    cp -- "$REGISTRY_FIXTURE" "$2"
  else
    cp -- "$3" "$2"
  fi
}
mkdir -p "$APPDIR/usr"
'''
        place = source[source.index('# Fork-local payload is staged before sealing'):source.index('ARCH="${ARCH}" "./${AT}"')]
        return subprocess.run(['bash', '-c', harness + func + '\ncollect_plugins_registry\n' + place, 'test',
                               str(ROOT), 'https://example.test/registry.json' if remote else str(self.registry),
                               str(self.root / 'AppDir'), str(self.registry), str(payload) if payload else '', *ids],
                              text=True, capture_output=True)

    def test_local_snapshot_stages_verified_archive(self):
        result = self.stage([self.entry])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.root / 'AppDir/usr/lib/plotjuggler/plugins/example/manifest.json').is_file())

    def test_http_registry_transport_remains_supported(self):
        result = self.stage([self.entry], remote=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_entry_and_platform_report_identity(self):
        for entries in [[], [{'id': 'example', 'platforms': {}}]]:
            with self.subTest(entries=entries):
                result = self.stage(entries)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("registry has no usable 'example' for linux-x86_64", result.stderr)

    def test_checksum_mismatch_still_fails(self):
        self.entry['platforms']['linux-x86_64']['checksum'] = 'sha256:' + '0' * 64
        result = self.stage([self.entry])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('checksum mismatch', result.stdout + result.stderr)

    def test_relative_snapshot_resolved_before_packager_changes_directory(self):
        source = SCRIPT.read_text(encoding='utf-8')
        block = source[source.index('while [[ $# -gt 0 ]]'):source.index('\n# Keep -asan')]
        result = subprocess.run(['bash', '-c', 'set -eu\nREGISTRY_URL=\n' + block + '\nprintf "%s" "$REGISTRY_URL"',
                                 'test', '--plugins-registry', 'locked registry.json'], cwd=self.root,
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, str(self.registry))

    def test_remote_registry_still_selects_newest_version_on_current_arch(self):
        older = dict(self.entry, version='0.9.0', platforms={'linux-x86_64': {
            'url': str(self.root / 'not-the-newest.zip'),
            'checksum': 'sha256:' + '0' * 64}})
        other_arch = dict(self.entry, version='2.0.0', platforms={'linux-aarch64': {
            'url': str(self.root / 'wrong-architecture.zip'),
            'checksum': 'sha256:' + '0' * 64}})
        result = self.stage([self.entry, older, other_arch], remote=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_actual_lock_targets_and_separately_staged_bin_appear_exactly_once(self):
        source = SCRIPT.read_text(encoding='utf-8')
        bundle = source.split('BUNDLE_IDS=(\n', 1)[1].split('\n)', 1)[0]
        ids = [line.strip() for line in bundle.splitlines() if line.strip() and not line.lstrip().startswith('#')]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertNotIn('ardupilot-dataflash', ids)
        self.assertNotIn('log-widget', ids)
        self.assertTrue({'candump-loader', 'influx-parser', 'navmap-parser'} <= set(ids))
        registry, _ = read_inventory(ROOT)
        originals = {entry['id']: entry for entry in registry['extensions']}
        self.assertNotIn('ardupilot-dataflash', originals)
        expected = expected_plugin_inventory(ROOT, 'linux-x86_64')
        self.assertEqual(set(ids) | {'ardupilot-dataflash'}, set(expected))
        entries = []
        for identifier in ids:
            entry = originals[identifier]
            self.assertIn('linux-x86_64', entry['platforms'])
            fixture = self.root / f'{identifier}.zip'
            with zipfile.ZipFile(fixture, 'w') as out:
                out.writestr(f'{identifier}/manifest.json',
                             json.dumps({'id': identifier, 'version': entry['version']}))
            entries.append(dict(entry, platforms={'linux-x86_64': {
                'url': str(fixture), 'checksum': 'sha256:' + hashlib.sha256(fixture.read_bytes()).hexdigest()}}))
        payload = self.root / 'extra'
        bin_id = 'ardupilot-dataflash'
        target = payload / 'lib/plotjuggler/plugins' / bin_id
        target.mkdir(parents=True)
        (target / 'manifest.json').write_text(json.dumps({'id': bin_id, 'version': expected[bin_id]}), encoding='utf-8')
        licenses = payload / 'share/plotjuggler4'
        licenses.mkdir(parents=True)
        (licenses / 'release.json').write_text('{"localized_plugin_rebuilds":[]}', encoding='utf-8')
        result = self.stage(entries, ids=ids, payload=payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        staged = self.root / 'AppDir/usr/lib/plotjuggler/plugins'
        records = [json.loads(p.read_text(encoding='utf-8')) for p in staged.glob('*/manifest.json')]
        self.assertEqual(len(records), len(expected))
        self.assertEqual({r['id']: r['version'] for r in records}, expected)

    def test_candidate_workflow_uses_same_local_lock_on_both_platforms(self):
        workflow = (ROOT / '.github/workflows/zh-4x-packages.yml').read_text(encoding='utf-8')
        linux = workflow.split('- name: Package Linux artifacts', 1)[1].split('- name:', 1)[0]
        self.assertIn('registry="packaging/localization/registry-lock.json"', linux)
        self.assertIn('--plugins-registry "$registry"', linux)
        self.assertIn('-PluginRegistryUrl "packaging/localization/registry-lock.json"', workflow)


if __name__ == '__main__':
    unittest.main()
