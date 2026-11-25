# SPDX-License-Identifier: MPL-2.0
"""Verify the historical release tree, without freezing the development tree."""
import ast
import re
import hashlib
import json
import subprocess
import shutil
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class UpstreamReleaseBaselineTests(unittest.TestCase):
    def historical_bytes(self, path):
        scope = json.loads((ROOT / 'docs/localization/release-4.1.0-historical-scope.json').read_text(encoding="utf-8"))
        commit = scope['source_commit']
        self.assertEqual(commit, '0113492d7a7f96e486de1f9adcde6e43893ab630')
        if not shutil.which('git') or subprocess.run(
                ['git', 'cat-file', '-e', commit + '^{commit}'], cwd=ROOT,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
            self.skipTest('Historical tree validation needs Git history containing ' + commit)
        listing = subprocess.check_output(['git', 'ls-tree', commit, '--', path], cwd=ROOT)
        if not listing:
            return None
        return subprocess.check_output(['git', 'show', commit + ':' + path], cwd=ROOT)

    def test_historical_scope_matches_recorded_git_source(self):
        scope = json.loads((ROOT / 'docs/localization/release-4.1.0-historical-scope.json').read_text(encoding="utf-8"))
        self.assertEqual(scope['baseline'], json.loads(self.historical_bytes('docs/localization/upstream-baseline.json')))
        self.assertIn('never a constraint on current development', scope['scope'])
        self.assertEqual(scope['rebuilt_plugins'], json.loads(self.historical_bytes(
            'packaging/localization/plugin-patches/source-lock.json'))['plugins'])
        source = self.historical_bytes('packaging/localization/prepare_payload.py').decode()
        core = next(ast.literal_eval(node.value) for node in ast.parse(source).body
                    if isinstance(node, ast.Assign) and any(
                        isinstance(t, ast.Name) and t.id == 'CORE_PLUGINS' for t in node.targets))
        self.assertEqual(scope['core_plugins'], core)
        verifier = self.historical_bytes('packaging/localization/verify_package.py').decode()
        self.assertEqual(scope['bin_numeric_series'], int(re.search(
            r'ArduPilot BIN: imported (\d+) numeric series', verifier).group(1)))


    def test_tag_boundaries_are_exact(self):
        record = json.loads((ROOT / 'docs/localization/release-4.1.0-baseline-files.json').read_text(encoding='utf-8'))
        self.assertEqual(record['upstream_commit'], '1b8fb491f56cc185ae395e2c7a0561443ad18d07')
        entries = record['tag_matches'] + record['fork_modified']
        self.assertEqual(len(entries), 52)
        self.assertEqual(len({entry['path'] for entry in entries}), 52)
        for entry in record['tag_matches']:
            with self.subTest(path=entry['path']):
                content = self.historical_bytes(entry['path'])
                if entry['sha256'] is None:
                    self.assertIsNone(content)
                else:
                    self.assertEqual(hashlib.sha256(content).hexdigest(), entry['sha256'])

    def test_modified_entry_digests_remain_upstream_baselines(self):
        record = json.loads((ROOT / 'docs/localization/release-4.1.0-baseline-files.json').read_text(encoding='utf-8'))
        self.assertIn('not a candidate digest', record['sha256_semantics'])
        entries = {entry['path']: entry['sha256'] for entry in record['fork_modified']}
        self.assertEqual(entries['pj_widgets/src/FileDialog.cpp'],
                         'a741ba73e77fb936ef18274ec0c24e40d70944fbd78a2daf2f4d606af4517d6c')
        self.assertEqual(entries['pj_widgets/CLAUDE.md'],
                         '7a77f60075366b196aa28e8a8ec23d8094064759f12002155e4c3f7a2adb3aaf')

    def test_tag_baseline_checkout_preserves_original_bytes(self):
        record = json.loads((ROOT / 'docs/localization/release-4.1.0-baseline-files.json').read_text(encoding='utf-8'))
        attributes = self.historical_bytes('.gitattributes').decode('utf-8').splitlines()
        for entry in record['tag_matches']:
            if entry['sha256'] is not None:
                with self.subTest(path=entry['path']):
                    self.assertIn(entry['path'] + ' text eol=lf', attributes)

    def test_localization_source_and_release_tag_are_distinct(self):
        record = json.loads((ROOT / 'docs/localization/release-4.1.0-historical-scope.json').read_text(encoding='utf-8'))['baseline']
        self.assertEqual(record['upstream_tag'], '4.1.0')
        self.assertEqual(record['upstream_commit'], record['upstream_release']['commit'])
        self.assertEqual(len(record['release_source']['post_tag_commits_reviewed']), 14)
        self.assertNotEqual(record['upstream_commit'], record['release_source']['development_parent'])
        self.assertTrue(record['release_source']['distribution_backports'])

    def test_upstream_release_text_is_complete(self):
        record = json.loads((ROOT / 'docs/localization/release-4.1.0-historical-scope.json').read_text(encoding='utf-8'))['baseline']
        notes = (ROOT / 'docs/localization/RELEASE-4.1.0+zh.1.md').read_text(encoding='utf-8')
        upstream = notes.split('\n# PlotJuggler 4.1.0\n', 1)[1].split('\n## 汉化与插件差异', 1)[0]
        upstream = '# PlotJuggler 4.1.0\n' + upstream.rstrip('\n') + '\n'
        self.assertEqual(hashlib.sha256(upstream.encode()).hexdigest(), record['upstream_release']['body_sha256_lf'])


if __name__ == '__main__':
    unittest.main()
