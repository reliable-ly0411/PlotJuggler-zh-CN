# SPDX-License-Identifier: MPL-2.0
"""Exercise AppImage registry staging without Qt, network or a native rebuild."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'packaging/appimage/build_appimage.sh'


@unittest.skipUnless(shutil.which('bash') and shutil.which('unzip'), 'bash and unzip required')
class AppImageRegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive = self.root / 'plugin.zip'
        with zipfile.ZipFile(self.archive, 'w') as out:
            out.writestr('example/manifest.json', '{"id":"example"}')
        self.entry = {'id': 'example', 'platforms': {'linux-x86_64': {
            'url': str(self.archive),
            'checksum': 'sha256:' + hashlib.sha256(self.archive.read_bytes()).hexdigest()}}}
        self.registry = self.root / 'locked registry.json'

    def stage(self, entries, remote=False):
        self.registry.write_text(json.dumps({'extensions': entries}), encoding='utf-8')
        source = SCRIPT.read_text(encoding='utf-8')
        function = source[source.index('collect_plugins_registry() {'):source.index('\n# ---------------------------------------------------------------------------\n# 4.')]
        # Only transport is mocked: SHA verification, unzip and staging run normally.
        harness = '''set -euo pipefail
REGISTRY_URL="$1"
APPDIR="$2"
PJ_PLUGINS_REL=usr/lib/plotjuggler/plugins
PLATFORM=linux-x86_64
BUNDLE_IDS=(example)
wget() { if [[ "$3" == https://example.test/registry.json ]]; then cp -- "$4" "$2"; else cp -- "$3" "$2"; fi; }
'''
        # A remote registry resolves to the same fixture while archive calls stay local.
        harness = harness.replace('cp -- "$4" "$2"', 'cp -- "' + str(self.registry) + '" "$2"')
        return subprocess.run(['bash', '-c', harness + function + '\ncollect_plugins_registry', 'test',
                               'https://example.test/registry.json' if remote else str(self.registry),
                               str(self.root / 'AppDir')], text=True, capture_output=True)

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

    def test_candidate_workflow_uses_same_local_lock_on_both_platforms(self):
        workflow = (ROOT / '.github/workflows/zh-4x-packages.yml').read_text(encoding='utf-8')
        linux = workflow.split('- name: Package Linux artifacts', 1)[1].split('- name:', 1)[0]
        self.assertIn('registry="packaging/localization/registry-lock.json"', linux)
        self.assertIn('--plugins-registry "$registry"', linux)
        self.assertIn('-PluginRegistryUrl "packaging/localization/registry-lock.json"', workflow)


if __name__ == '__main__':
    unittest.main()
