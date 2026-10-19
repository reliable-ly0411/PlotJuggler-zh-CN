# SPDX-License-Identifier: MPL-2.0
"""Hermetic tests: synthetic bytes/snapshots only; never contact a release service."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from release_review import (compare_payloads, files_under, plan_assets, source_sha,
                            verify_ci, verify_preserved, verify_source)


SOURCE = "a" * 40
VERSION = "3.18.0-zh.99+upstream.3.17.2.apbin.1.g" + SOURCE[:12]
REPOSITORY = "https://github.com/example/project"


class OfflineReview(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.artifacts = self.root / "artifacts"
        self.artifacts.mkdir()
        self.name = "PlotJuggler-" + VERSION + "-Windows-x64.zip"
        data = b"synthetic package, not executable"
        (self.artifacts / self.name).write_bytes(data)
        item = {"name": self.name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        self.manifest = {"source_commit": SOURCE, "tag": "v3.18.0-zh.99", "version": VERSION,
                         "asset_count": 1, "software_assets": [item]}
        self.asset = {"id": 11, "name": self.name, "size": item["bytes"],
                      "digest": "sha256:" + item["sha256"], "state": "uploaded"}
        self.release = {"id": 7, "tag_name": self.manifest["tag"], "body": "Unchanged notes",
                        "draft": False, "prerelease": True, "assets": []}

    def plan(self):
        return plan_assets(self.artifacts, self.manifest, self.release, 7)

    def test_plan_is_offline_and_append_only(self):
        before = copy.deepcopy(self.release)
        result = self.plan()
        self.assertTrue(result["dry_run"])
        self.assertFalse(result["published"])
        self.assertEqual(result["upload_candidates"], [self.name])
        self.assertEqual(self.release, before)

    def test_matching_existing_is_unchanged(self):
        self.release["assets"] = [self.asset]
        result = self.plan()
        self.assertEqual(result["unchanged"], [self.name])
        self.assertEqual(result["upload_candidates"], [])

    def test_other_existing_assets_are_preserved(self):
        extra = dict(self.asset, name="other-package.zip", id=12)
        self.release["assets"] = [extra]
        self.assertEqual(self.plan()["preserved_existing"], ["other-package.zip"])

    def test_existing_different_or_missing_digest_rejected(self):
        for key, value in (("digest", None), ("digest", "sha256:" + "0" * 64),
                           ("size", 1), ("state", "new")):
            with self.subTest(key=key, value=value):
                self.release["assets"] = [dict(self.asset, **{key: value})]
                with self.assertRaises(ValueError):
                    self.plan()

    def test_duplicate_remote_assets_rejected(self):
        self.release["assets"] = [self.asset, dict(self.asset)]
        with self.assertRaises(ValueError):
            self.plan()

    def test_wrong_release_identity_rejected(self):
        for key, value in (("id", 8), ("tag_name", "v0")):
            release = dict(self.release, **{key: value})
            with self.subTest(key=key), self.assertRaises(ValueError):
                plan_assets(self.artifacts, self.manifest, release, 7)

    def test_tampered_local_file_rejected(self):
        (self.artifacts / self.name).write_bytes(b"tampered")
        with self.assertRaises(ValueError):
            self.plan()

    def test_missing_or_extra_file_rejected(self):
        path = self.artifacts / "unexpected.txt"
        path.write_text("unexpected")
        with self.assertRaises(ValueError):
            self.plan()
        path.unlink()
        (self.artifacts / self.name).unlink()
        with self.assertRaises(ValueError):
            self.plan()

    def test_duplicate_basename_rejected(self):
        nested = self.artifacts / "nested"
        nested.mkdir()
        shutil.copyfile(self.artifacts / self.name, nested / self.name)
        with self.assertRaises(ValueError):
            self.plan()

    def test_symlinks_rejected(self):
        for target in (self.root / "missing", self.artifacts / self.name, self.artifacts):
            link = self.artifacts / "link"
            link.symlink_to(target)
            with self.assertRaises(ValueError):
                self.plan()
            link.unlink()
        link = self.root / "root-link"
        link.symlink_to(self.artifacts, target_is_directory=True)
        with self.assertRaises(ValueError):
            files_under(link)

    def test_manifest_guards(self):
        for key, value in (("source_commit", "a" * 12), ("asset_count", 2),
                           ("software_assets", []),
                           ("software_assets", self.manifest["software_assets"] * 2)):
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                plan_assets(self.artifacts, dict(self.manifest, **{key: value}), self.release, 7)

    def test_malformed_asset_guards(self):
        for key, value in (("name", "../x"), ("name", "..\\x"), ("bytes", 0),
                           ("bytes", True), ("sha256", "bad")):
            manifest = copy.deepcopy(self.manifest)
            manifest["software_assets"][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                plan_assets(self.artifacts, manifest, self.release, 7)

    def test_preserved_snapshot(self):
        self.release["assets"] = [self.asset]
        after = copy.deepcopy(self.release)
        after["assets"].append(dict(self.asset, name="new.zip", id=12))
        self.assertEqual(verify_preserved(self.release, after),
                         {"preserved_assets": 1, "added_assets": ["new.zip"]})

    def test_preserved_snapshot_rejects_mutation(self):
        self.release["assets"] = [self.asset]
        for key, value in (("id", 9), ("tag_name", "v0"), ("body", "new notes"),
                           ("draft", True), ("prerelease", False), ("assets", [])):
            with self.subTest(key=key), self.assertRaises(ValueError):
                verify_preserved(self.release, dict(self.release, **{key: value}))
        for key, value in (("id", 22), ("size", 1), ("digest", None), ("state", "new")):
            after = dict(self.release, assets=[dict(self.asset, **{key: value})])
            with self.subTest(key=key), self.assertRaises(ValueError):
                verify_preserved(self.release, after)

    def payload(self, name):
        folder = self.root / name
        folder.mkdir()
        info = {"commit": SOURCE, "version": VERSION, "repository": REPOSITORY,
                "dataflash_formats": ["BIN"]}
        (folder / "BUILD-INFO.json").write_text(json.dumps(info))
        (folder / "DataAPBin.dll").write_bytes(b"fake plugin")
        (folder / "plotjuggler.exe").write_bytes(b"fake application")
        (folder / "python312.zip").write_bytes(b"fake raw embedded ZIP")
        return folder

    def test_complete_payloads_match(self):
        left, right = self.payload("portable"), self.payload("installer")
        result = compare_payloads(left, right, SOURCE, VERSION, REPOSITORY)
        self.assertEqual(result["matching_files"], 4)

    def test_missing_raw_python_payload_rejected(self):
        left, right = self.payload("portable"), self.payload("installer")
        (right / "python312.zip").unlink()
        with self.assertRaises(ValueError):
            compare_payloads(left, right, SOURCE, VERSION, REPOSITORY)

    def test_payload_byte_mismatch_rejected(self):
        left, right = self.payload("portable"), self.payload("installer")
        (right / "DataAPBin.dll").write_bytes(b"changed")
        with self.assertRaises(ValueError):
            compare_payloads(left, right, SOURCE, VERSION, REPOSITORY)

    def test_payload_identity_and_plugin_guards(self):
        left, right = self.payload("portable"), self.payload("installer")
        for source, version, repo in (("b" * 40, VERSION, REPOSITORY),
                                       (SOURCE, "different", REPOSITORY),
                                       (SOURCE, VERSION, "other")):
            with self.subTest(source=source, version=version, repo=repo), self.assertRaises(ValueError):
                compare_payloads(left, right, source, version, repo)
        for folder in (left, right):
            (folder / "DataAPBin.dll").unlink()
        with self.assertRaises(ValueError):
            compare_payloads(left, right, SOURCE, VERSION, REPOSITORY)

    def test_cli_has_no_publish_command(self):
        script = Path(__file__).with_name("release_review.py")
        result = subprocess.run([sys.executable, str(script), "publish"], capture_output=True)
        self.assertNotEqual(result.returncode, 0)


class CiReview(unittest.TestCase):
    def setUp(self):
        self.run = {"id": 17, "head_sha": SOURCE, "head_repository": {"full_name": "example/project"},
                    "status": "completed", "conclusion": "success"}
        self.jobs = {"total_count": 2, "jobs": [
            {"name": name, "run_id": 17, "head_sha": SOURCE, "status": "completed", "conclusion": result}
            for name, result in (("verify-seven", "success"), ("publish", "skipped"))]}

    def verify(self):
        return verify_ci(self.run, self.jobs, SOURCE, "example/project", ["verify-seven"], ["publish"])

    def test_exact_source_run(self):
        self.assertEqual(self.verify()["verified_jobs"], 2)

    def test_run_identity_or_success_mismatch(self):
        for key, value in (("head_sha", "b" * 40), ("head_repository", {"full_name": "other/project"}),
                           ("status", "in_progress"), ("conclusion", "failure")):
            with self.subTest(key=key), self.assertRaises(ValueError):
                verify_ci(dict(self.run, **{key: value}), self.jobs, SOURCE, "example/project",
                          ["verify-seven"], ["publish"])

    def test_incomplete_job_snapshot(self):
        self.jobs["total_count"] = 3
        with self.assertRaises(ValueError):
            self.verify()

    def test_job_guards(self):
        original = copy.deepcopy(self.jobs)
        for key, value in (("name", "unknown"), ("run_id", 18), ("head_sha", "b" * 40),
                           ("status", "queued"), ("conclusion", "skipped")):
            self.jobs = copy.deepcopy(original)
            self.jobs["jobs"][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.verify()

    def test_required_job_cannot_be_allowed_to_skip(self):
        with self.assertRaises(ValueError):
            verify_ci(self.run, self.jobs, SOURCE, "example/project", ["verify-seven"], ["verify-seven"])

    def test_duplicate_job_names_rejected(self):
        self.jobs["jobs"][1]["name"] = "verify-seven"
        with self.assertRaises(ValueError):
            self.verify()


class SourceAndArchive(unittest.TestCase):
    def test_full_sha_required(self):
        for value in (None, "a" * 12, "g" * 40, "A" * 40):
            with self.subTest(value=value), self.assertRaises(ValueError):
                source_sha(value)

    @unittest.skipUnless(shutil.which("git"), "git is needed for local ref checks")
    def test_source_checks_are_read_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            def git(*args):
                return subprocess.check_output(["git", "-C", temp, *args], text=True,
                                               stderr=subprocess.DEVNULL).strip()
            git("init", "-q")
            (root / "tracked.txt").write_text("original")
            git("add", "tracked.txt")
            git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "fixture")
            sha = git("rev-parse", "HEAD")
            git("tag", "fixture")
            refs = git("show-ref")
            self.assertTrue(verify_source(temp, sha, "fixture")["tracked_sources_unchanged"])
            self.assertEqual(git("show-ref"), refs)
            with self.assertRaises(ValueError):
                verify_source(temp, "b" * 40, "fixture")
            (root / "tracked.txt").write_text("changed")
            with self.assertRaises(subprocess.CalledProcessError):
                verify_source(temp, sha, "fixture")
            self.assertEqual(git("show-ref"), refs)

    def test_archived_sources_have_exact_checksums(self):
        archives = list(Path(__file__).with_name("archive").glob("*.json"))
        self.assertEqual(len(archives), 7)
        branches = set()
        for path in archives:
            item = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(item["archive_format"], 1)
            self.assertEqual(hashlib.sha256(item["content"].encode()).hexdigest(), item["sha256"])
            self.assertRegex(item["commit"], r"^[0-9a-f]{40}$")
            self.assertRegex(item["blob"], r"^[0-9a-f]{40}$")
            self.assertFalse(path.stat().st_mode & 0o111)
            branches.add(item["origin_ref"])
        self.assertEqual(len(branches), 4)


if __name__ == "__main__":
    unittest.main()
