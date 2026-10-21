#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PATCHES = ROOT / 'packaging/localization/plugin-patches'
spec = importlib.util.spec_from_file_location('replace_plugins', ROOT / 'packaging/localization/replace_localized_plugins.py')
replacement = importlib.util.module_from_spec(spec)
spec.loader.exec_module(replacement)


class LocalizedPluginBuildTest(unittest.TestCase):
    def test_locked_patches_and_peeled_commits(self):
        lock = json.loads((PATCHES / 'source-lock.json').read_text())
        self.assertEqual(len(lock['plugins']), 4)
        self.assertEqual(hashlib.sha256((PATCHES / 'pj_display_language.hpp').read_bytes()).hexdigest(), lock['helper_sha256'])
        for item in lock['plugins']:
            self.assertRegex(item['commit'], r'^[a-f0-9]{40}$')
            self.assertNotEqual(item['commit'], item['tag_object'])
            self.assertEqual(hashlib.sha256((PATCHES / (item['id'] + '.patch')).read_bytes()).hexdigest(), item['patch_sha256'])
            self.assertIn(item['sdk'], lock['sdk_commits'])
        self.assertEqual(lock['sdk_commits']['0.32.0'], 'e325fe38138690a79c8b4bbea28fa6b63066b75c')
        self.assertNotEqual(lock['sdk_commits']['0.32.0'], lock['sdk_tag_objects']['0.32.0'])

    def test_mosaico_original_package_identity_is_preserved(self):
        lock = json.loads((PATCHES / 'source-lock.json').read_text())
        self.assertNotIn('toolbox-mosaico', {p['id'] for p in lock['plugins']})
        self.assertEqual([p['id'] for p in lock['deferred_plugins']], ['toolbox-mosaico'])
        originals = json.loads((ROOT / 'packaging/localization/preserved-upstream-plugins.json').read_text())
        registry = json.loads((ROOT / 'packaging/localization/registry-lock.json').read_text())
        upstream = next(p for p in registry['extensions'] if p['id'] == 'toolbox-mosaico')
        self.assertEqual(set(originals), {'linux-x86_64', 'windows-x86_64'})
        for platform, item in originals.items():
            self.assertEqual(item['version'], upstream['version'])
            self.assertEqual(item['url'], upstream['platforms'][platform]['url'])
            self.assertEqual('sha256:' + item['archive_sha256'], upstream['platforms'][platform]['checksum'])
            self.assertEqual(len(item['files']), 2)
            for entry in item['files']:
                self.assertTrue(entry['path'].startswith('lib/plotjuggler/plugins/toolbox-mosaico/'))
                self.assertRegex(entry['sha256'], r'^[a-f0-9]{64}$')

    def test_replace_removes_old_binary_and_verifies_new_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            extra, dest = root / 'extra', root / 'dest'
            relative = Path('lib/plotjuggler/plugins/protobuf-parser')
            (extra / relative).mkdir(parents=True)
            (dest / relative).mkdir(parents=True)
            (dest / relative / 'upstream-old.so').write_bytes(b'old')
            new = extra / relative / 'new.so'
            new.write_bytes(b'localized')
            record_path = extra / 'share/plotjuggler4/release.json'
            record_path.parent.mkdir(parents=True)
            record_path.write_text(json.dumps({'localized_plugin_rebuilds': [{
                'id': 'protobuf-parser', 'files': [{'path': (relative / 'new.so').as_posix(),
                    'sha256': hashlib.sha256(new.read_bytes()).hexdigest()}]}]}))
            replacement.replace(extra, dest)
            self.assertEqual(list((dest / relative).iterdir()), [dest / relative / 'new.so'])
            new.write_bytes(b'corrupt')
            with self.assertRaises(AssertionError):
                replacement.replace(extra, dest)
            self.assertEqual((dest / relative / 'new.so').read_bytes(), b'localized')

    def test_native_build_offline_and_separate_sdk_graphs(self):
        script = (ROOT / 'packaging/localization/build_localized_plugins.py').read_text()
        self.assertIn("source / 'SDK_VERSION'", script)
        self.assertIn("'--lockfile-out='", script)
        self.assertIn("'-DCMAKE_CXX_FLAGS=/utf-8'", script)
        self.assertIn('ChatSession|UsageLedger|SettingsStore|ConversationState|SeriesStats|StreamJson', script)
        self.assertNotIn('AssistantDialog|', script)
        self.assertNotIn('upload_conan_artifacts', script)
        self.assertNotIn('--sdk-local', script)
        self.assertIn("assert identifier != 'toolbox-mosaico'", script)
        self.assertNotIn("'toolbox-mosaico'", (ROOT / 'packaging/localization/replace_localized_plugins.py').read_text())
        self.assertIn("'fork-localized-rebuild-not-upstream-binary'", script)


if __name__ == '__main__':
    unittest.main()
