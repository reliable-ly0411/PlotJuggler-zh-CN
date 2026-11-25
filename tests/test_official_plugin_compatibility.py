#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Exercise real git apply inside a host checkout's FetchContent directory."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('cmake') and shutil.which('git'), 'CMake and Git integration')
class OfficialPluginCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / 'host'
        self.root.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        self.source = self.root / 'build/_deps/pj_official_plugins-src'
        self.source.mkdir(parents=True)
        self.patches = self.root / 'packaging/localization/plugin-patches/compatibility-candidates'
        self.patches.mkdir(parents=True)
        cmake = self.root / 'cmake'
        cmake.mkdir()
        shutil.copy2(ROOT / 'cmake/PjOfficialPluginCompatibility.cmake', cmake)
        record = {'patches_sha256': {}, 'wasm_result_files_sha256': {}}
        for module, patch in [('data_load_csv', 'wasm-csv397.patch'), ('widget_log', 'wasm-log391.patch')]:
            relative = module + '/source.txt'
            target = self.source / relative
            target.parent.mkdir()
            target.write_bytes(b'before\n')
            # A same-named host file must never be patched instead of the fetched source.
            host_target = self.root / relative
            host_target.parent.mkdir()
            host_target.write_bytes(b'host sentinel\n')
            data = (f'--- a/{relative}\n+++ b/{relative}\n@@ -1 +1 @@\n-before\n+after\n').encode()
            (self.patches / patch).write_bytes(data)
            record['patches_sha256'][patch] = hashlib.sha256(data).hexdigest()
            record['wasm_result_files_sha256'][relative] = hashlib.sha256(b'after\n').hexdigest()
        (self.patches / 'provenance.json').write_text(json.dumps(record), encoding='utf-8')
        self.script = self.root / 'apply.cmake'
        self.script.write_text(
            f'include("{(cmake / "PjOfficialPluginCompatibility.cmake").as_posix()}")\n'
            f'pj_apply_official_plugin_compatibility("{self.source.as_posix()}")\n', encoding='utf-8')

    def run_apply(self, crlf=False):
        env = os.environ.copy()
        env.update(GIT_DIR=str(self.root / '.git'), GIT_WORK_TREE=str(self.root))
        if crlf:
            env.update(GIT_CONFIG_COUNT='2', GIT_CONFIG_KEY_0='core.autocrlf',
                       GIT_CONFIG_VALUE_0='true', GIT_CONFIG_KEY_1='core.eol',
                       GIT_CONFIG_VALUE_1='crlf')
        return subprocess.run(['cmake', '-P', str(self.script)], cwd=self.root, env=env,
                              text=True, capture_output=True)

    def test_nested_fetchcontent_applies_and_reconfigure_is_idempotent(self):
        for _ in range(2):
            result = self.run_apply()
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            for module in ['data_load_csv', 'widget_log']:
                self.assertEqual((self.source / module / 'source.txt').read_bytes(), b'after\n')
                self.assertEqual((self.root / module / 'source.txt').read_bytes(), b'host sentinel\n')

    def test_corrupt_applied_source_is_not_accepted_on_reconfigure(self):
        result = self.run_apply()
        self.assertEqual(result.returncode, 0, result.stderr)
        target = self.source / 'widget_log/source.txt'
        target.write_bytes(b'corrupt\n')
        result = self.run_apply()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('input mismatch', result.stderr)
        self.assertEqual(target.read_bytes(), b'corrupt\n')

    def test_crlf_user_configuration_preserves_exact_archive_bytes(self):
        for _ in range(2):
            result = self.run_apply(crlf=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            for module in ['data_load_csv', 'widget_log']:
                self.assertEqual((self.source / module / 'source.txt').read_bytes(), b'after\n')
                self.assertEqual((self.root / module / 'source.txt').read_bytes(), b'host sentinel\n')

    def test_patch_hash_is_checked_before_mutation(self):
        patch = self.patches / 'wasm-csv397.patch'
        patch.write_bytes(patch.read_bytes() + b'\n')
        result = self.run_apply()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('patch hash mismatch', result.stderr)
        self.assertEqual((self.source / 'data_load_csv/source.txt').read_bytes(), b'before\n')


@unittest.skipUnless(shutil.which('cmake'), 'CMake integration')
class OfficialPluginAdoptionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        cmake = self.root / 'cmake'
        cmake.mkdir()
        self.module = cmake / 'PjOfficialPluginCompatibility.cmake'
        shutil.copy2(ROOT / 'cmake' / self.module.name, self.module)
        self.source = self.root / 'source'
        self.commit = 'a' * 40
        paths = ('data_load_csv/test.cpp', 'widget_log/test.cpp')
        self.old = dict.fromkeys(paths, hashlib.sha256(b'historical patch result').hexdigest())
        self.files = {}
        for path in paths:
            output = self.source / path
            output.parent.mkdir(parents=True)
            data = path.encode()
            output.write_bytes(data)
            self.files[path] = hashlib.sha256(data).hexdigest()
        self.provenance = self.root / 'packaging/localization/plugin-patches/compatibility-candidates/provenance.json'
        self.provenance.parent.mkdir(parents=True)
        self.script = self.root / 'verify.cmake'

    def verify(self, commit=None):
        self.provenance.write_text(json.dumps({
            'wasm_result_files_sha256': self.old,
            'wasm_adopted_upstream': {'commit': self.commit, 'files_sha256': self.files},
        }), encoding='utf-8')
        self.script.write_text(
            f'include("{self.module.as_posix()}")\n'
            f'pj_verify_official_plugin_compatibility("{self.source.as_posix()}" "{commit or self.commit}")\n',
            encoding='utf-8')
        return subprocess.run(['cmake', '-P', str(self.script)], cwd=self.root, text=True, capture_output=True)

    def test_adopted_source_never_needs_patch_bytes_and_is_read_only(self):
        for _ in range(2):
            result = self.verify()
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(sorted(p.relative_to(self.source).as_posix()
                                    for p in self.source.rglob('*') if p.is_file()), sorted(self.files))
            for key in self.files:
                self.assertEqual((self.source / key).read_bytes(), key.encode())

    def test_wrong_commit_rejected(self):
        result = self.verify(commit='b' * 40)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('commit mismatch', result.stderr)

    def test_corrupt_or_missing_adopted_file_fails_without_mutation(self):
        path = self.source / 'widget_log/test.cpp'
        path.write_bytes(b'tampered')
        result = self.verify()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('adopted file hash mismatch', result.stderr)
        self.assertEqual(path.read_bytes(), b'tampered')
        path.unlink()
        result = self.verify()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('adopted file missing', result.stderr)
        self.assertFalse(path.exists())

    def test_shortened_provenance_rejected(self):
        del self.files['widget_log/test.cpp']
        result = self.verify()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('adopted path set mismatch', result.stderr)


if __name__ == '__main__':
    unittest.main()
