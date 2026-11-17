#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Exercise source preflight with real Git LF and Windows CRLF checkouts."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ApbinManifestProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'host'
        self.root.mkdir()
        self.git(self.root, 'init', '-q')
        self.git(self.root, 'commit', '-q', '--allow-empty', '-m', 'upstream fixture')
        upstream = self.git(self.root, 'rev-parse', 'HEAD').strip()
        self.record = json.loads((ROOT / 'docs/localization/upstream-baseline.json').read_text(encoding='utf-8'))
        self.record['upstream_commit'] = upstream
        self.record['status'] = 'development'
        self.plugin = self.record['ardupilot_plugin']
        origin = Path(self.temp.name) / 'origin'
        (origin / 'sdk4').mkdir(parents=True)
        self.blob = (json.dumps({'id': 'ardupilot-dataflash', 'version': self.plugin['version'],
                                 'license': self.plugin['license']}, indent=2) + '\n').encode()
        (origin / 'sdk4/manifest.json').write_bytes(self.blob)
        self.git(origin, 'init', '-q')
        self.git(origin, '-c', 'core.autocrlf=false', 'add', 'sdk4/manifest.json')
        self.git(origin, 'commit', '-q', '-m', 'pinned manifest')
        self.source = self.root / self.plugin['path']
        self.git(self.root, '-c', 'core.autocrlf=true', 'clone', '-q', str(origin), str(self.source))
        self.plugin['commit'] = self.git(self.source, 'rev-parse', 'HEAD').strip()
        self.plugin['source_manifest_sha256'] = hashlib.sha256(self.blob).hexdigest()
        self.git(self.root, 'update-index', '--add', '--cacheinfo',
                 '160000,' + self.plugin['commit'] + ',' + self.plugin['path'])
        for relative in ['tests/check_localization_provenance.py', 'cmake/host-sdk-source.json',
                         'packaging/localization/bundled-plugin-metadata.json']:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)
        (self.root / 'versions.env').write_text('PJ_APP_VERSION=4.2.0-zh.1.dev.1\nPJ_QT_VERSION=6.12.0\n', encoding='utf-8')
        (self.root / '.gitmodules').write_text(
            f'[submodule "{self.plugin["path"]}"]\n\turl = {self.plugin["repository"]}.git\n', encoding='utf-8')
        self.baseline = self.root / 'docs/localization/upstream-baseline.json'
        self.baseline.parent.mkdir(parents=True)
        self.save_record()

    @staticmethod
    def git(root, *args):
        return subprocess.check_output(['git', '-C', str(root), '-c', 'user.name=Test',
                                        '-c', 'user.email=test@example.invalid', *args], text=True)

    def save_record(self):
        self.baseline.write_text(json.dumps(self.record), encoding='utf-8')

    def check(self):
        return subprocess.run([sys.executable, str(self.root / 'tests/check_localization_provenance.py')],
                              capture_output=True, text=True)

    def test_real_crlf_checkout_and_lf_source_both_pass(self):
        manifest = self.source / 'sdk4/manifest.json'
        self.assertEqual(manifest.read_bytes(), self.blob.replace(b'\n', b'\r\n'))
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest.write_bytes(self.blob)
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_modified_checkout_is_rejected(self):
        manifest = self.source / 'sdk4/manifest.json'
        manifest.write_bytes(manifest.read_bytes().replace(b'ardupilot-dataflash', b'other-plugin'))
        result = self.check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('BIN checkout manifest differs from pinned source', result.stderr)

    def test_wrong_blob_hash_is_rejected(self):
        self.plugin['source_manifest_sha256'] = '0' * 64
        self.save_record()
        result = self.check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('BIN source manifest hash differs', result.stderr)


if __name__ == '__main__':
    unittest.main()
