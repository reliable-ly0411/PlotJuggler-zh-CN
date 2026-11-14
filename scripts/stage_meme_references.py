# SPDX-License-Identifier: MPL-2.0
"""Stage only hash-verified immutable PNG fixtures needed by LocalizedMemes.

No network access, ref fallback, archive extraction or product resource changes.
The workflow must fetch PINNED_COMMIT first. Existing output is never overwritten.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import tempfile
import os

PINNED_COMMIT = "3117288ce8d710bde4f7a86ca5ed5240ebb1c301"
RESOURCE_DIR = "plotjuggler_app/resources/memes"


def required_references(catalog):
    if catalog.get("reference_commit") != PINNED_COMMIT:
        raise ValueError("Unexpected reference commit")
    images = catalog.get("images", [])
    if [entry.get("id") for entry in images] != list(range(107)):
        raise ValueError("Expected all 107 catalog entries")
    result = {}
    for entry in images:
        if not entry.get("variant"):
            continue
        ref = entry.get("reference", {})
        name = ref.get("file", "")
        if not re.fullmatch(r"zh_CN/meme_[0-9]{2,3}\.png", name) or name in result:
            raise ValueError("Invalid or duplicate reference path")
        if not re.fullmatch(r"[0-9a-f]{64}", ref.get("sha256", "")):
            raise ValueError("Missing reference SHA256")
        size = ref.get("size")
        if not isinstance(size, list) or len(size) != 2 or any(type(n) is not int or n <= 0 for n in size):
            raise ValueError("Missing reference dimensions")
        result[name] = ref
    if len(result) != 88:
        raise ValueError("Expected exactly 88 localized references")
    return result


def verify_png(data, reference):
    if hashlib.sha256(data).hexdigest() != reference["sha256"]:
        raise ValueError("Reference SHA256 mismatch")
    if (len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR" or
            list(struct.unpack(">II", data[16:24])) != reference["size"]):
        raise ValueError("Reference PNG dimensions mismatch")


def stage(repo, out):
    repo, out = Path(repo).resolve(), Path(out).absolute()
    catalog = json.loads((repo / RESOURCE_DIR / "zh_CN.json").read_text(encoding="utf-8"))
    references = required_references(catalog)
    # Explicit immutable object only. Never use FETCH_HEAD or a mutable branch.
    actual = subprocess.check_output(["git", "rev-parse", "--verify", PINNED_COMMIT + "^{commit}"], cwd=repo, text=True).strip()
    if actual != PINNED_COMMIT:
        raise ValueError("Pinned commit unavailable")
    if out.exists() or out.is_symlink():
        raise ValueError("Reference destination already exists; refusing stale/partial fixtures")
    if out.parent.resolve() == (repo / RESOURCE_DIR).resolve() or (repo / RESOURCE_DIR).resolve() in out.parent.resolve().parents:
        raise ValueError("Reference fixtures must not overwrite product resources")
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".meme-reference-stage-", dir=out.parent) as temporary:
        temp = Path(temporary) / "payload"
        temp.mkdir()
        for name, reference in references.items():
            path = RESOURCE_DIR + "/" + name
            tree = subprocess.check_output(["git", "ls-tree", PINNED_COMMIT, "--", path], cwd=repo, text=True)
            if not tree.startswith("100644 blob ") or tree.rstrip().split("\t")[-1] != path:
                raise ValueError("Reference must be a regular Git blob")
            data = subprocess.check_output(["git", "show", PINNED_COMMIT + ":" + path], cwd=repo)
            verify_png(data, reference)
            destination = temp / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
            verify_png(destination.read_bytes(), reference)
        # Commit the complete directory only after every reference has passed.
        os.rename(temp, out)
    return {"reference_commit": PINNED_COMMIT, "verified_pngs": len(references),
            "sha256_verified": True, "dimensions_verified": True}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(stage(args.repo, args.out), sort_keys=True))
