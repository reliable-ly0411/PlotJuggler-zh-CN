#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
PATCHES = ROOT / 'packaging/localization/plugin-patches'
spec = importlib.util.spec_from_file_location('replace_plugins', ROOT / 'packaging/localization/replace_localized_plugins.py')
replacement = importlib.util.module_from_spec(spec)
spec.loader.exec_module(replacement)
with mock.patch.object(sys, 'path', [str(ROOT / 'packaging/localization'), *sys.path]):
    build_spec = importlib.util.spec_from_file_location('build_plugins', ROOT / 'packaging/localization/build_localized_plugins.py')
    builder = importlib.util.module_from_spec(build_spec)
    build_spec.loader.exec_module(builder)


class LocalizedPluginBuildTest(unittest.TestCase):
    def test_locked_patches_and_peeled_commits(self):
        lock = json.loads((PATCHES / 'source-lock.json').read_text(encoding='utf-8'))
        self.assertEqual(len(lock['plugins']), 6)
        self.assertIn('packaging/localization/plugin-patches/pj_display_language.hpp text eol=lf',
                      (ROOT / '.gitattributes').read_text(encoding='utf-8'))
        self.assertEqual(hashlib.sha256((PATCHES / 'pj_display_language.hpp').read_bytes()).hexdigest(), lock['helper_sha256'])
        for item in lock['plugins']:
            self.assertRegex(item['commit'], r'^[a-f0-9]{40}$')
            self.assertNotEqual(item['commit'], item['tag_object'])
            self.assertEqual(hashlib.sha256((PATCHES / (item['id'] + '.patch')).read_bytes()).hexdigest(), item['patch_sha256'])
            self.assertIn(item['sdk'], lock['sdk_commits'])
        self.assertEqual(lock['sdk_commits']['0.32.0'], 'e325fe38138690a79c8b4bbea28fa6b63066b75c')
        self.assertNotEqual(lock['sdk_commits']['0.32.0'], lock['sdk_tag_objects']['0.32.0'])

    def test_mosaico_original_package_identity_is_preserved(self):
        lock = json.loads((PATCHES / 'source-lock.json').read_text(encoding='utf-8'))
        self.assertNotIn('toolbox-mosaico', {p['id'] for p in lock['plugins']})
        self.assertEqual([p['id'] for p in lock['deferred_plugins']], ['toolbox-mosaico'])
        originals = json.loads((ROOT / 'packaging/localization/preserved-upstream-plugins.json').read_text(encoding='utf-8'))
        registry = json.loads((ROOT / 'packaging/localization/registry-lock.json').read_text(encoding='utf-8'))
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
                    'sha256': hashlib.sha256(new.read_bytes()).hexdigest()}]}]}), encoding='utf-8')
            replacement.replace(extra, dest)
            self.assertEqual(list((dest / relative).iterdir()), [dest / relative / 'new.so'])
            new.write_bytes(b'corrupt')
            with self.assertRaises(AssertionError):
                replacement.replace(extra, dest)
            self.assertEqual((dest / relative / 'new.so').read_bytes(), b'localized')

    def test_csv_is_pinned_to_reviewed_source_and_packaging_consumes_it(self):
        lock = json.loads((PATCHES / 'source-lock.json').read_text(encoding='utf-8'))
        csv = next(item for item in lock['plugins'] if item['id'] == 'csv-loader')
        self.assertEqual(csv['module'], 'data_load_csv')
        self.assertEqual(csv['commit'], 'ba6ee417d91a01aae778a0ec3a4443a024671123')
        self.assertEqual(csv['sdk'], '0.34.1')
        self.assertEqual(csv['platforms'], ['Linux', 'Windows'])
        self.assertEqual(csv['target'], 'csv_source_plugin')
        patch = (PATCHES / 'csv-loader.patch').read_text(encoding='utf-8')
        self.assertIn('std::filesystem::path(std::u8string', patch)
        self.assertIn('csv_file_paths_test', patch)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            extra, destination = root / 'extra', root / 'destination'
            relative = Path('lib/plotjuggler/plugins/csv-loader')
            (extra / relative).mkdir(parents=True)
            (destination / relative).mkdir(parents=True)
            (destination / relative / 'old.dll').write_bytes(b'old synthetic DLL')
            binary = extra / relative / 'csv_source_plugin.dll'
            binary.write_bytes(b'new synthetic DLL')
            record = extra / 'share/plotjuggler4/release.json'
            record.parent.mkdir(parents=True)
            record.write_text(json.dumps({'localized_plugin_rebuilds': [{
                'id': 'csv-loader', 'files': [{'path': (relative / binary.name).as_posix(),
                'sha256': hashlib.sha256(binary.read_bytes()).hexdigest()}]}]}), encoding='utf-8')
            replacement.replace(extra, destination)
            self.assertEqual([f.name for f in (destination / relative).iterdir()], [binary.name])
            binary.write_bytes(b'corrupt synthetic DLL')
            with self.assertRaises(AssertionError):
                replacement.replace(extra, destination)
            self.assertEqual((destination / relative / binary.name).read_bytes(), b'new synthetic DLL')

    def test_scoped_preflight_cannot_stage_partial_release_or_unknown_plugin(self):
        script = ROOT / 'packaging/localization/build_localized_plugins.py'
        for options, message in [(['--plugin', 'csv-loader'], '--plugin requires --preflight'),
                                 (['--preflight', '--plugin', 'unknown-plugin'], 'not locked for this platform')]:
            with self.subTest(options=options), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                result = subprocess.run([sys.executable, str(script), '--work', str(root / 'work'),
                                         '--prefix', str(root / 'prefix'), *options],
                                        capture_output=True, text=True, timeout=10)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)
                self.assertFalse((root / 'prefix').exists())

    def test_csv_preflight_requires_the_complete_three_language_test_set(self):
        """Exercise the real builder up to dispatch, without fetching or compiling sources."""
        lock = json.loads((PATCHES / 'source-lock.json').read_text(encoding='utf-8'))
        item = next(entry for entry in lock['plugins'] if entry['id'] == 'csv-loader')
        expected = {'csv_parser_test', 'csv_file_paths_test', 'LocalizedDisplay_zh_CN',
                    'LocalizedDisplay_zh_TW', 'LocalizedDisplay_en_US',
                    'LocalizedDisplay_unknown', 'LocalizedDisplay_empty'}

        class TestsDispatched(Exception):
            pass

        cases = [('complete', expected, TestsDispatched),
                 ('missing-traditional', expected - {'LocalizedDisplay_zh_TW'}, AssertionError),
                 ('missing-paths', expected - {'csv_file_paths_test'}, AssertionError),
                 ('unexpected', expected | {'LocalizedDisplay_unexpected'}, AssertionError)]
        for name, selected, outcome in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                source = root / 'work/csv-loader/source'

                def checkout(url, commit, directory):
                    self.assertEqual((url, commit), (lock['repository'], item['commit']))
                    directory.mkdir(parents=True)
                    (directory / item['module']).mkdir()
                    (directory / 'SDK_VERSION').write_text(item['sdk'], encoding='utf-8')
                    (directory / 'CMakeLists.txt').write_text('', encoding='utf-8')
                    (directory / item['module'] / 'manifest.json').write_text(
                        json.dumps({'id': item['id'], 'version': item['version']}), encoding='utf-8')

                def listing(args, **kwargs):
                    self.assertEqual(args[0], 'ctest')
                    self.assertIn('--show-only=json-v1', args)
                    self.assertEqual(args[-2:], ['-R', '^(LocalizedDisplay_.*|csv_(parser|file_paths)_test)$'])
                    generated = (source / 'CMakeLists.txt').read_text(encoding='utf-8')
                    for language in ['zh_CN', 'zh_TW', 'en_US', 'unknown', 'empty']:
                        self.assertIn('add_test(NAME LocalizedDisplay_' + language + ' ', generated)
                    return json.dumps({'tests': [{'name': test} for test in sorted(selected)]})

                def run(args, **kwargs):
                    if args[0] == 'ctest':
                        self.assertIn('--no-tests=error', args)
                        self.assertEqual(args[-2:], ['-R', '^(LocalizedDisplay_.*|csv_(parser|file_paths)_test)$'])
                        raise TestsDispatched()

                with mock.patch.object(builder, 'checkout', side_effect=checkout), \
                     mock.patch.object(builder, 'run', side_effect=run), \
                     mock.patch.object(builder.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)), \
                     mock.patch.object(builder.subprocess, 'check_output', side_effect=listing):
                    with self.assertRaises(outcome):
                        builder.build_one(item, lock, root / 'work', root / 'prefix', 'Linux')
                self.assertFalse((root / 'prefix').exists())

    def test_native_build_offline_and_separate_sdk_graphs(self):
        script = (ROOT / 'packaging/localization/build_localized_plugins.py').read_text(encoding='utf-8')
        self.assertIn("source / 'SDK_VERSION'", script)
        self.assertIn("'--lockfile-out='", script)
        self.assertIn('add_compile_options("$<$<CXX_COMPILER_ID:MSVC>:/utf-8>")', script)
        self.assertNotIn("-DCMAKE_CXX_FLAGS=", script)
        self.assertNotIn("-DCMAKE_C_FLAGS=", script)
        self.assertIn('ChatSession|UsageLedger|SettingsStore|ConversationState|SeriesStats|StreamJson', script)
        self.assertNotIn('AssistantDialog|', script)
        self.assertNotIn('upload_conan_artifacts', script)
        self.assertNotIn('--sdk-local', script)
        self.assertIn("assert identifier != 'toolbox-mosaico'", script)
        self.assertNotIn("'toolbox-mosaico'", (ROOT / 'packaging/localization/replace_localized_plugins.py').read_text(encoding='utf-8'))
        self.assertIn("'fork-localized-rebuild-not-upstream-binary'", script)


if __name__ == '__main__':
    unittest.main()
