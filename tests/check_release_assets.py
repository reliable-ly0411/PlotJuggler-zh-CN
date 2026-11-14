# SPDX-License-Identifier: MPL-2.0
"""Release attachment policy tests; fixtures contain no actual executable code."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import subprocess
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from release_assets import collect, expected_files, inventory, source_contract, verify_upload


class ReleaseAssets(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.software = self.root / "software"
        self.metadata = self.root / "metadata"
        self.software.mkdir()
        self.metadata.mkdir()
        self.source = "a" * 40
        self.contract = source_contract()
        self.contract_mock = patch("release_assets.source_contract", return_value=self.contract).start()
        self.addCleanup(patch.stopall)
        self.version, names = expected_files(self.source)
        self.audits = []
        for name in sorted(names):
            data = name.encode()
            (self.software / name).write_bytes(data)
            package = {"name": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            if "Windows" in name and self.audits and any("Windows" in audit["packages"][0]["name"] for audit in self.audits):
                next(audit for audit in self.audits if "Windows" in audit["packages"][0]["name"])["packages"].append(package)
                continue
            codename = "bookworm" if "bookworm" in name else "trixie" if "trixie" in name else "noble"
            self.audits.append({"privacy_scan": "passed", "test_executables_absent": True,
                                "build_info": {"commit": self.source, "version": self.version},
                                "build_arch": "aarch64" if "aarch64" in name else "x86_64",
                                "build_os": {"VERSION_CODENAME": codename}, "packages": [package]})
        self.write_audits()

    def write_audits(self):
        for index, audit in enumerate(self.audits):
            folder = self.metadata / str(index)
            folder.mkdir(exist_ok=True)
            (folder / "package-size.json").write_text(json.dumps(audit))

    def collect(self):
        return collect(self.software, self.metadata, self.source, self.root / "out", self.root / "report")

    def test_seven_software_only(self):
        result = self.collect()
        self.assertEqual(result["asset_count"], 7)
        self.assertEqual(result["process_attachments"], 0)
        self.assertFalse(result["published"])
        self.assertEqual(len(list((self.root / "out").iterdir())), 7)
        contract = source_contract()
        self.assertEqual(result["tag"], contract["tag"])
        notes = (self.root / "report/notes.md").read_text(encoding="utf-8")
        self.assertIn(contract["tag"], notes)
        self.assertIn(contract["upstream_sha"], notes)

    def test_next_candidate_uses_its_declared_version(self):
        contract = dict(source_contract(), base_version="3.18.1-rc.12", tag="v3.18.1-rc.12")
        with patch("release_assets.source_contract", return_value=contract):
            version, names = expected_files(self.source)
        self.assertEqual(version, "3.18.1-rc.12+upstream.3.17.2.apbin.1.g" + self.source[:12])
        self.assertEqual(len(names), 7)
        self.assertTrue(all(name.startswith("PlotJuggler-" + version + "-") for name in names))

    def contract_fixture(self, declarations):
        fixture = self.root / "contract"
        (fixture / "cmake").mkdir(parents=True)
        (fixture / "CMakeLists.txt").write_text(
            'project(\nplotjuggler\nLANGUAGES C CXX\nVERSION 3.18.1)\n', encoding="utf-8")
        (fixture / "cmake/ForkVersion.cmake").write_text(declarations, encoding="utf-8")
        return fixture

    def test_ambiguous_declaration_rejected(self):
        original = (Path(__file__).resolve().parents[1] / "cmake/ForkVersion.cmake").read_text()
        fixture = self.contract_fixture(original + '\nset(PJ_FORK_PRERELEASE "rc.99")\n')
        with self.assertRaises(ValueError):
            source_contract(fixture)

    def test_prerelease_leading_zero_rejected(self):
        original = (Path(__file__).resolve().parents[1] / "cmake/ForkVersion.cmake").read_text()
        import re
        original = re.sub(r'set\(PJ_FORK_PRERELEASE "[^"]+"\)',
                          'set(PJ_FORK_PRERELEASE "rc.01")', original)
        with self.assertRaises(ValueError):
            source_contract(self.contract_fixture(original))

    def commit_fixture(self):
        original = (Path(__file__).resolve().parents[1] / "cmake/ForkVersion.cmake").read_text()
        fixture = self.contract_fixture(original)
        def git(*args):
            return subprocess.check_output(["git", "-C", str(fixture), *args], text=True).strip()
        git("init", "-q")
        git("add", "CMakeLists.txt", "cmake/ForkVersion.cmake")
        git("-c", "user.name=Fixture", "-c", "user.email=fixture@local.invalid", "commit", "-qm", "fixture")
        return fixture, git("rev-parse", "HEAD"), git

    def test_contract_comes_from_commit_even_with_dirty_worktree(self):
        fixture, source, git = self.commit_fixture()
        before = source_contract(fixture, source)
        (fixture / "cmake/ForkVersion.cmake").write_text('set(PJ_FORK_PRERELEASE "rc.999")\n')
        self.assertEqual(source_contract(fixture, source), before)

    def test_missing_commit_and_non_commit_identity_rejected(self):
        fixture, source, git = self.commit_fixture()
        for identity in ("b" * 40, git("rev-parse", "HEAD^{tree}")):
            with self.assertRaises(ValueError):
                source_contract(fixture, identity)

    def test_report_attachment_rejected(self):
        (self.software / "report.json").write_text("{}")
        with self.assertRaises(ValueError):
            self.collect()

    def test_missing_package_rejected(self):
        next(self.software.iterdir()).unlink()
        with self.assertRaises(ValueError):
            self.collect()

    def test_tampered_package_rejected(self):
        next(self.software.iterdir()).write_bytes(b"changed")
        with self.assertRaises(ValueError):
            self.collect()

    def test_failed_privacy_rejected(self):
        self.audits[0]["privacy_scan"] = "failed"
        self.write_audits()
        with self.assertRaises(ValueError):
            self.collect()

    def test_wrong_source_rejected(self):
        self.audits[0]["build_info"]["commit"] = "b" * 40
        self.write_audits()
        with self.assertRaises(ValueError):
            self.collect()

    def test_mixed_candidate_versions_rejected(self):
        self.audits[0]["build_info"]["version"] = "3.18.1-rc.9+upstream.3.17.2.apbin.1.g" + self.source[:12]
        self.write_audits()
        with self.assertRaises(ValueError):
            self.collect()

    def test_relabelled_debian_package_rejected(self):
        next(audit for audit in self.audits if "bookworm" in audit["packages"][0]["name"])["build_os"]["VERSION_CODENAME"] = "noble"
        self.write_audits()
        with self.assertRaises(ValueError):
            self.collect()

    def test_wrong_arm_architecture_rejected(self):
        next(audit for audit in self.audits if "aarch64" in audit["packages"][0]["name"])["build_arch"] = "x86_64"
        self.write_audits()
        with self.assertRaises(ValueError):
            self.collect()

    def test_uploaded_draft_exact_identities(self):
        manifest = self.collect()
        release = {"tag_name": manifest["tag"], "draft": True, "assets": [
            {"name": item["name"], "size": item["bytes"], "digest": "sha256:" + item["sha256"]}
            for item in manifest["software_assets"]]}
        verify_upload(manifest, release)
        for change in ("extra", "hash", "published"):
            bad = copy.deepcopy(release)
            if change == "extra":
                bad["assets"].append({"name": "report.json"})
            elif change == "hash":
                bad["assets"][0]["digest"] = "sha256:" + "0" * 64
            else:
                bad["draft"] = False
            with self.assertRaises(ValueError):
                verify_upload(manifest, bad)


if __name__ == "__main__":
    unittest.main()
