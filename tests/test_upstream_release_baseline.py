# SPDX-License-Identifier: MPL-2.0
"""Reject accidental leakage of post-tag application features into the release."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class UpstreamReleaseBaselineTests(unittest.TestCase):
    def test_tag_boundaries_are_exact(self):
        record = json.loads((ROOT / 'docs/localization/release-4.1.0-baseline-files.json').read_text(encoding='utf-8'))
        self.assertEqual(record['upstream_commit'], '1b8fb491f56cc185ae395e2c7a0561443ad18d07')
        entries = record['tag_matches'] + record['fork_modified']
        self.assertEqual(len(entries), 52)
        self.assertEqual(len({entry['path'] for entry in entries}), 52)
        for entry in record['tag_matches']:
            with self.subTest(path=entry['path']):
                path = ROOT / entry['path']
                if entry['sha256'] is None:
                    self.assertFalse(path.exists())
                else:
                    self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), entry['sha256'])

    def test_tag_baseline_checkout_preserves_original_bytes(self):
        record = json.loads((ROOT / 'docs/localization/release-4.1.0-baseline-files.json').read_text(encoding='utf-8'))
        attributes = (ROOT / '.gitattributes').read_text(encoding='utf-8').splitlines()
        for entry in record['tag_matches']:
            if entry['sha256'] is not None:
                with self.subTest(path=entry['path']):
                    self.assertIn(entry['path'] + ' text eol=lf', attributes)

    def test_localization_source_and_release_tag_are_distinct(self):
        record = json.loads((ROOT / 'docs/localization/upstream-baseline.json').read_text(encoding='utf-8'))
        self.assertEqual(record['upstream_tag'], '4.1.0')
        self.assertEqual(record['upstream_commit'], record['upstream_release']['commit'])
        self.assertEqual(len(record['release_source']['post_tag_commits_reviewed']), 14)
        self.assertNotEqual(record['upstream_commit'], record['release_source']['development_parent'])
        self.assertTrue(record['release_source']['distribution_backports'])

    def test_upstream_release_text_is_complete(self):
        record = json.loads((ROOT / 'docs/localization/upstream-baseline.json').read_text(encoding='utf-8'))
        notes = (ROOT / 'docs/localization/RELEASE-4.1.0+zh.1.md').read_text(encoding='utf-8')
        upstream = notes.split('\n# PlotJuggler 4.1.0\n', 1)[1].split('\n## 汉化与插件差异', 1)[0]
        upstream = '# PlotJuggler 4.1.0\n' + upstream.rstrip('\n') + '\n'
        self.assertEqual(hashlib.sha256(upstream.encode()).hexdigest(), record['upstream_release']['body_sha256_lf'])


if __name__ == '__main__':
    unittest.main()
