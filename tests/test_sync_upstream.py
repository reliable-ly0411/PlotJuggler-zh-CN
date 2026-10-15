# SPDX-License-Identifier: MPL-2.0
"""Disposable Git repositories verify preservation, abort, and version boundaries."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/sync_upstream.py"


class SyncTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="plotjuggler-sync-test-")
        self.root = Path(self.temp.name)
        self.upstream = self.root / "upstream"
        self.fork = self.root / "fork"
        self.report = self.root / "report.json"
        self.git(self.root, "init", "-b", "main", str(self.upstream))
        (self.upstream / "CMakeLists.txt").write_text("project(example VERSION 3.17.2)\n")
        (self.upstream / "shared.txt").write_text("baseline\n")
        self.commit(self.upstream)
        self.git(self.root, "clone", str(self.upstream), str(self.fork))
        self.git(self.fork, "switch", "-c", "zh-CN")
        (self.fork / "custom.txt").write_text("Chinese UI and bundled parser\n")
        self.commit(self.fork)
        self.before = self.git(self.fork, "rev-parse", "HEAD").strip()

    def tearDown(self):
        self.temp.cleanup()

    def git(self, repo, *args):
        return subprocess.check_output(
            [os.environ.get("GIT", "git"), "-C", str(repo), *args],
            text=True, encoding="utf-8", stderr=subprocess.STDOUT,
        )

    def commit(self, repo):
        self.git(repo, "add", "-A")
        self.git(repo, "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                 "commit", "-m", "fixture")

    def run_sync(self, *extra):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--repo", str(self.fork), "--upstream-url",
             str(self.upstream), "--report", str(self.report), *extra], capture_output=True,
        )
        return result.returncode, json.loads(self.report.read_text(encoding="utf-8"))

    def test_no_change_is_success(self):
        code, report = self.run_sync()
        self.assertEqual(code, 0)
        self.assertEqual(report["result"], "up_to_date")
        self.assertFalse(report["changed"])
        self.assertEqual(self.git(self.fork, "rev-parse", "HEAD").strip(), self.before)

    def test_clean_merge_preserves_custom_commit(self):
        (self.upstream / "new.txt").write_text("new upstream data\n")
        self.commit(self.upstream)
        code, report = self.run_sync()
        self.assertEqual(code, 0)
        self.assertTrue(report["changed"])
        self.assertTrue((self.fork / "new.txt").exists())
        self.assertIn("Chinese UI", (self.fork / "custom.txt").read_text())
        self.git(self.fork, "merge-base", "--is-ancestor", self.before, "HEAD")

    def test_conflict_aborts_and_preserves_branch(self):
        (self.fork / "shared.txt").write_text("custom localization\n")
        self.commit(self.fork)
        before = self.git(self.fork, "rev-parse", "HEAD").strip()
        (self.upstream / "shared.txt").write_text("upstream rewrite\n")
        self.commit(self.upstream)
        code, report = self.run_sync()
        self.assertNotEqual(code, 0)
        self.assertEqual(report["result"], "conflict")
        self.assertIn("shared.txt", report["conflicts"])
        self.assertEqual(self.git(self.fork, "rev-parse", "HEAD").strip(), before)
        self.assertEqual((self.fork / "shared.txt").read_text(), "custom localization\n")
        self.assertEqual(self.git(self.fork, "status", "--porcelain").strip(), "")

    def test_major_upgrade_requires_manual_migration(self):
        (self.upstream / "CMakeLists.txt").write_text("project(example VERSION 4.0.0)\n")
        self.commit(self.upstream)
        code, report = self.run_sync()
        self.assertNotEqual(code, 0)
        self.assertEqual(report["result"], "unsupported_major")
        self.assertEqual(self.git(self.fork, "rev-parse", "HEAD").strip(), self.before)

    def test_validation_failure_does_not_commit_merge(self):
        (self.upstream / "tests").mkdir()
        (self.upstream / "tests/check_translations.py").write_text("raise SystemExit(1)\n")
        self.commit(self.upstream)
        code, report = self.run_sync("--validate")
        self.assertNotEqual(code, 0)
        self.assertEqual(report["result"], "validation_failed")
        self.assertEqual(self.git(self.fork, "rev-parse", "HEAD").strip(), self.before)
        self.assertEqual(self.git(self.fork, "status", "--porcelain").strip(), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
