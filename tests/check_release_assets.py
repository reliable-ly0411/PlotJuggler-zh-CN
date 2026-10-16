# SPDX-License-Identifier: MPL-2.0
"""Release attachment policy tests; fixtures contain no actual executable code."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from release_assets import collect, expected_files, inventory, verify_upload


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
