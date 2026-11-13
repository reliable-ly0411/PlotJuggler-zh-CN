# SPDX-License-Identifier: MPL-2.0
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("branch_policy", ROOT / "scripts/check_branch_name.py")
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


class BranchPolicyTest(unittest.TestCase):
    def test_accepted(self):
        for branch in ["zh-CN", "zh-CN-dev", "zh-CN-feat/menu", "zh-CN-fix/3-scaled-caption-determinism",
                       "zh-CN-ci/branch-policy", "zh-CN-docs/readme", "zh-CN-release/v3.18.0-zh.5",
                       "zh-CN-4.x", "zh-CN-4.x-dev", "zh-CN-4.x-feat/localization-foundation",
                       "zh-CN-4.x-fix/7-bin-reader", "zh-CN-4.x-ci/windows", "zh-CN-4.x-docs/building",
                       "zh-CN-4.x-release/v4.0.0-zh.1", "main", "main-3.x"]:
            with self.subTest(branch=branch):
                self.assertTrue(policy.valid(branch))

    def test_rejected(self):
        for branch in ["main-4.x", "main4", "zh-CN/feature", "zh-CN-4.x/feature", "feature/new", "zh-CN-5.x",
                       "zh-CN-4.x-fix/0-test", "zh-CN-4.x-fix/3", "zh-CN-4.x-ci/Uppercase",
                       "zh-CN-4.x-feat/a/b", "zh-CN-4.x-ci/a\n", "zh-CN-4.x-dev-malformed",
                       "zh-CN-4.x-release/latest", "zh-CN-4.x-feat/-a", "zh-CN-4.x-feat/a--b"]:
            with self.subTest(branch=branch):
                self.assertFalse(policy.valid(branch))

    def test_development_workflow_is_read_only(self):
        text = (ROOT / ".github/workflows/zh-4x-ci.yml").read_text(encoding="utf-8")
        self.assertIn("contents: read", text)
        for forbidden in ["contents: write", "pull_request_target:", "gh release", "gh api",
                          "git push", "action-gh-release", "  publish:", "    tags:"]:
            self.assertNotIn(forbidden, text)
        self.assertIn("zh-CN-4.x-dev", text)
        self.assertIn("zh-CN-4.x-*/**", text)


    def test_new_upstream_workflows_do_not_enable_fork_publication(self):
        for workflow in ['conda-release.yml', 'macos-ci.yml', 'macos-release.yml']:
            text = (ROOT / '.github/workflows' / workflow).read_text(encoding='utf-8')
            events = text.split('\non:', 1)[1].split('\n\n', 1)[0]
            self.assertIn('  workflow_dispatch:', events)
            self.assertNotIn('  push:', events)
            self.assertNotIn('  pull_request:', events)
            self.assertNotIn('  schedule:', events)
        conda = (ROOT / '.github/workflows/conda-release.yml').read_text(encoding='utf-8')
        self.assertIn("if: github.repository == 'PlotJuggler/PlotJuggler' && startsWith(github.ref, 'refs/tags/')", conda)
        self.assertIn("if: github.repository == 'PlotJuggler/PlotJuggler' && github.event_name == 'workflow_dispatch'", conda)

        macos = (ROOT / '.github/workflows/macos-release.yml').read_text(encoding='utf-8')
        self.assertIn("if: github.repository == 'PlotJuggler/PlotJuggler'", macos)
        self.assertIn('contents: read', macos)
        for forbidden in ('contents: write', 'gh release', 'action-gh-release'):
            self.assertNotIn(forbidden, macos)


if __name__ == "__main__":
    unittest.main()
