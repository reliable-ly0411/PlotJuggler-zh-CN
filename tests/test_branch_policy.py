# SPDX-License-Identifier: MPL-2.0
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('branch_policy', ROOT / 'scripts/check_branch_name.py')
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


class BranchPolicyTest(unittest.TestCase):
    def test_accepted(self):
        for branch in ['zh-CN', 'zh-CN-dev', 'zh-CN-feat/menu', 'zh-CN-fix/3-scaled-caption-determinism',
                       'zh-CN-ci/branch-policy', 'zh-CN-docs/readme', 'zh-CN-release/v3.18.0-zh.5',
                       'main', 'main-4.x', 'fix/issue-839-parser-layout-state']:
            with self.subTest(branch=branch):
                self.assertTrue(policy.valid(branch))

    def test_rejected(self):
        for branch in ['zh-CN/feature', 'feature/new', 'fix/scaled-caption-determinism',
                       'zh4/resource-overlays', 'zh-CN-ci/', 'zh-CN-ci/Uppercase',
                       'zh-CN-fix/3', 'zh-CN-fix/0-test', 'zh-CN-ci/a/b',
                       'zh-CN-release/latest', 'zh-CN-dev-malformed', 'zh-CN-ci/a\n']:
            with self.subTest(branch=branch):
                self.assertFalse(policy.valid(branch))

    def test_development_is_not_release_trigger(self):
        text = (ROOT / '.github/workflows/zh-release.yml').read_text()
        self.assertNotIn('  publish:', text)
        self.assertNotIn('gh release ', text)
        self.assertNotIn('contents: write', text)
        self.assertIn('contents: read', text)
        self.assertNotIn('    tags:', text)
        self.assertNotIn('tags: [v3.18.0-zh.4]', text)
        sync = (ROOT / '.github/workflows/zh-sync.yml').read_text()
        self.assertIn('ref: zh-CN-dev', sync)
        self.assertIn('--branch zh-CN-dev ', sync)


if __name__ == '__main__':
    unittest.main()
