#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Offline safety regressions for the two fixed upstream mirror refs."""

import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import urllib.error

import sync_mirrors as sync

OLD = "1" * 40
NEW = "2" * 40
OTHER = "3" * 40


class FakeGitHub:
    def __init__(self):
        self.refs = {(repo, branch): (OLD if repo == sync.REPOSITORY else NEW)
                     for repo in (sync.REPOSITORY, sync.UPSTREAM) for branch in sync.BRANCHES}
        self.calls = []
        self.comparison = {"status": "ahead", "behind_by": 0, "ahead_by": 9,
                           "merge_base_commit": {"sha": OLD}}
        self.race = None
        self.write_error = None
        self.mutate_after_write = False

    def request(self, method, path, body=None):
        self.calls.append((method, path, body))
        if "/compare/" in path:
            if self.race:
                self.refs[(sync.REPOSITORY, "main")] = self.race
            return self.comparison
        repository, branch = path[len("/repos/"):].split("/git/ref", 1)
        branch = branch.removeprefix("s").removeprefix("/heads/")
        if method == "PATCH":
            if self.write_error:
                raise sync.SyncError(self.write_error)
            assert body == {"sha": NEW, "force": False}
            assert repository == sync.REPOSITORY
            assert branch in sync.BRANCHES
            self.refs[(repository, branch)] = OTHER if self.mutate_after_write else body["sha"]
        return {"ref": f"refs/heads/{branch}", "object": {
            "type": "commit", "sha": self.refs[(repository, branch)]}}

    def writes(self):
        return [call for call in self.calls if call[0] != "GET"]


class MirrorSyncTests(unittest.TestCase):
    def setUp(self):
        self.api = FakeGitHub()

    def test_dry_run_is_read_only(self):
        report = sync.run(self.api, False)
        self.assertEqual([r["status"] for r in report["branches"]], ["would_fast_forward"] * 2)
        self.assertEqual(self.api.writes(), [])

    def test_live_updates_only_both_fixed_refs(self):
        report = sync.run(self.api, True)
        self.assertEqual([r["status"] for r in report["branches"]], ["fast_forwarded"] * 2)
        self.assertEqual(self.api.writes(), [
            ("PATCH", f"/repos/{sync.REPOSITORY}/git/refs/heads/{branch}", {"sha": NEW, "force": False})
            for branch in sync.BRANCHES])
        self.assertTrue(all(r["after"] == NEW for r in report["branches"]))

    def test_idempotent_second_run_performs_no_writes(self):
        sync.run(self.api, True)
        self.api.calls.clear()
        report = sync.run(self.api, True)
        self.assertEqual([r["status"] for r in report["branches"]], ["already_current"] * 2)
        self.assertEqual(self.api.writes(), [])

    def test_diverged_history_is_preserved(self):
        self.api.comparison.update(status="diverged", behind_by=1)
        result = sync.sync_branch(self.api, "main", True)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(self.api.writes(), [])

    def test_local_ahead_is_not_rewound(self):
        self.api.comparison.update(status="behind", behind_by=2, ahead_by=0)
        self.assertEqual(sync.sync_branch(self.api, "main", True)["status"], "blocked")
        self.assertEqual(self.api.writes(), [])

    def test_wrong_merge_base_is_rejected(self):
        self.api.comparison["merge_base_commit"]["sha"] = OTHER
        self.assertEqual(sync.sync_branch(self.api, "main", True)["status"], "blocked")
        self.assertEqual(self.api.writes(), [])

    def test_missing_comparison_evidence_is_rejected(self):
        self.api.comparison = {"status": "ahead"}
        self.assertEqual(sync.sync_branch(self.api, "main", True)["status"], "blocked")
        self.assertEqual(self.api.writes(), [])

    def test_racing_destination_is_not_updated(self):
        self.api.race = OTHER
        result = sync.sync_branch(self.api, "main", True)
        self.assertEqual(result["status"], "blocked")
        self.assertIn("changed during comparison", result["error"])
        self.assertEqual(self.api.writes(), [])

    def test_protection_rejection_is_not_retried(self):
        self.api.write_error = "HTTP 422: protected ref"
        result = sync.sync_branch(self.api, "main", True)
        self.assertEqual(result["status"], "blocked")
        self.assertTrue(result["write_attempted"])
        self.assertEqual(len(self.api.writes()), 1)
        self.assertEqual(self.api.refs[(sync.REPOSITORY, "main")], OLD)

    def test_uncertain_write_failure_is_not_retried(self):
        self.api.write_error = "request failed; no request retried"
        self.assertEqual(sync.sync_branch(self.api, "main", True)["status"], "blocked")
        self.assertEqual(len(self.api.writes()), 1)

    def test_post_write_ref_must_be_verified(self):
        self.api.mutate_after_write = True
        result = sync.sync_branch(self.api, "main", True)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["after"], OTHER)
        self.assertEqual(len(self.api.writes()), 1)

    def test_one_blocked_branch_does_not_skip_the_other(self):
        self.api.race = OTHER
        result = sync.run(self.api, True)
        self.assertEqual([r["status"] for r in result["branches"]], ["blocked", "fast_forwarded"])

    def test_missing_ref_does_not_create_a_branch(self):
        del self.api.refs[(sync.REPOSITORY, "main")]
        self.assertEqual(sync.sync_branch(self.api, "main", True)["status"], "blocked")
        self.assertEqual(self.api.writes(), [])

    def test_invalid_sha_is_rejected(self):
        self.api.refs[(sync.UPSTREAM, "main")] = "not-a-sha"
        self.assertEqual(sync.sync_branch(self.api, "main", True)["status"], "blocked")
        self.assertEqual(self.api.writes(), [])

    def test_malformed_ref_response_still_reports_each_branch(self):
        with patch.object(self.api, "request", return_value=[]):
            result = sync.run(self.api, True)
        self.assertEqual([r["status"] for r in result["branches"]], ["blocked"] * 2)

    def test_malformed_comparison_response_is_rejected(self):
        for comparison in ([], None, {"merge_base_commit": []}):
            with self.subTest(comparison=comparison):
                self.api.comparison = comparison
                self.assertEqual(sync.sync_branch(self.api, "main", True)["status"], "blocked")
        self.assertEqual(self.api.writes(), [])

    def test_localization_and_topic_refs_are_not_targets(self):
        for branch in ("zh-CN", "zh-CN-dev", "zh-CN-4.x", "zh-CN-4.x-dev", "feature/topic", "refs/tags/v4"):
            with self.subTest(branch=branch), self.assertRaises(sync.SyncError):
                sync.sync_branch(self.api, branch, True)
        self.assertEqual(self.api.calls, [])

    def test_http_payload_uses_false_not_force(self):
        api = sync.GitHub("synthetic-test-token")
        with patch.object(api.opener, "open", return_value=io.BytesIO(b'{}')) as opener:
            api.request("PATCH", f"/repos/{sync.REPOSITORY}/git/refs/heads/main", {"sha": NEW, "force": False})
        request = opener.call_args.args[0]
        self.assertEqual(request.full_url, f"https://api.github.com/repos/{sync.REPOSITORY}/git/refs/heads/main")
        self.assertEqual(json.loads(request.data), {"sha": NEW, "force": False})
        self.assertEqual(request.get_header("Authorization"), "Bearer synthetic-test-token")

    def test_api_redirects_are_not_followed(self):
        with self.assertRaises(sync.SyncError):
            sync.NoRedirect().redirect_request(None, None, 302, "redirect", {}, "https://example.invalid")

    def test_api_rejects_other_repositories(self):
        with self.assertRaises(sync.SyncError):
            sync.GitHub("").request("GET", "/repos/other/repo/git/ref/heads/main")

    def test_http_failure_is_not_retried(self):
        api = sync.GitHub("")
        error = urllib.error.HTTPError("https://api.github.com", 403, "forbidden", {}, None)
        with patch.object(api.opener, "open", side_effect=error) as opener:
            with self.assertRaises(sync.SyncError):
                api.request("GET", f"/repos/{sync.REPOSITORY}/git/ref/heads/main")
        self.assertEqual(opener.call_count, 1)

    def test_workflow_safety_contract(self):
        workflow = (Path(__file__).parents[1] / "workflows/upstream-mirrors.yml").read_text(encoding="utf-8")
        self.assertIn("cron: '13 */6 * * *'", workflow)
        self.assertIn("default: true", workflow)
        self.assertIn("github.ref == 'refs/heads/zh-CN-4.x'", workflow)
        self.assertIn("github.event_name != 'pull_request'", workflow)
        self.assertIn("GH_TOKEN: ${{ github.token }}", workflow)
        self.assertNotIn("secrets.", workflow)
        self.assertNotIn("workflow_run:", workflow)
        self.assertNotIn("pull_request_target:", workflow)
        self.assertNotIn("contents: write", workflow.split("  sync:")[0])
        self.assertNotIn("release", workflow.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
