# SPDX-License-Identifier: MPL-2.0
"""Offline fixture staging boundaries; synthetic PNG headers, no product pixels."""
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import stage_meme_references as staging

DATA = b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", 3, 4)


def catalog():
    images = []
    for i in range(107):
        entry = {"id": i}
        if i < 88:
            entry.update(variant={"image": "synthetic"}, reference={
                "file": f"zh_CN/meme_{i:02d}.png", "sha256": hashlib.sha256(DATA).hexdigest(), "size": [3, 4]})
        images.append(entry)
    return {"reference_commit": staging.PINNED_COMMIT, "images": images}


class StagingTests(unittest.TestCase):
    def test_manifest_rejections(self):
        for change in (lambda x: x.update(reference_commit="main"),
                       lambda x: x["images"].pop(),
                       lambda x: x["images"][0]["reference"].update(file="../private.png"),
                       lambda x: x["images"][0]["reference"].update(file="zh_CN\\meme_00.png"),
                       lambda x: x["images"][1]["reference"].update(file="zh_CN/meme_00.png"),
                       lambda x: x["images"][0]["reference"].update(sha256="bad"),
                       lambda x: x["images"][0].pop("variant")):
            value = catalog(); change(value)
            with self.assertRaises(ValueError): staging.required_references(value)

    def test_hash_and_dimension_rejections(self):
        ref = catalog()["images"][0]["reference"]
        with self.assertRaises(ValueError): staging.verify_png(DATA + b"modified", ref)
        bad = dict(ref, size=[4, 3])
        with self.assertRaises(ValueError): staging.verify_png(DATA, bad)

    def run_stage(self, failure=None):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "源码 with spaces"; root.mkdir()
            resources = root / staging.RESOURCE_DIR; resources.mkdir(parents=True)
            (resources / "zh_CN.json").write_text(json.dumps(catalog()), encoding="utf-8")
            out = root / "reference-memes"
            def git(args, **kwargs):
                if args[1] == "rev-parse": return staging.PINNED_COMMIT + "\n"
                if args[1] == "ls-tree":
                    mode = "120000" if failure == "symlink" else "100644"
                    return mode + " blob " + "a" * 40 + "\t" + args[-1] + "\n"
                if failure == "missing":
                    raise staging.subprocess.CalledProcessError(128, args)
                self.assertTrue(args[-1].startswith(staging.PINNED_COMMIT + ":"))
                return DATA + (b"bad" if failure == "corrupt" else b"")
            with patch.object(staging.subprocess, "check_output", side_effect=git):
                if failure:
                    with self.assertRaises((ValueError, staging.subprocess.CalledProcessError)): staging.stage(root, out)
                    self.assertFalse(out.exists())
                    self.assertFalse(list(root.glob(".meme-reference-stage-*")))
                else:
                    result = staging.stage(root, out)
                    self.assertEqual(result["verified_pngs"], 88)
                    self.assertEqual(len(list(out.rglob("*.png"))), 88)
                    with self.assertRaises((ValueError, staging.subprocess.CalledProcessError)): staging.stage(root, out)
                    self.assertEqual((out / "zh_CN/meme_00.png").read_bytes(), DATA)

    def test_success_and_existing_output_protection(self): self.run_stage()
    def test_corruption_never_leaves_partial_output(self): self.run_stage("corrupt")
    def test_missing_blob_never_leaves_partial_output(self): self.run_stage("missing")
    def test_git_symlinks_rejected(self): self.run_stage("symlink")


if __name__ == "__main__": unittest.main()
