# SPDX-License-Identifier: MPL-2.0
"""Offline release review helpers. No credentials, downloads, uploads, or publishing.

Adapted from the historical backfill/zh.3/zh.4 guards recorded in archive/.
The maintained package builder and seven-package collector remain in scripts/.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


def require(condition, message):
    # Unlike the historical assert guards, checks remain active under python -O.
    if not condition:
        raise ValueError(message)


def source_sha(source):
    require(isinstance(source, str) and re.fullmatch(r"[0-9a-f]{40}", source),
            "A full lowercase source commit is required")
    return source


def sha256(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def files_under(root):
    """Inventory plain files without following symlinks or reading special files."""
    root = Path(root)
    require(root.is_dir() and not root.is_symlink(), "Expected a real directory")
    result = {}
    for path in sorted(root.rglob("*")):
        require(not path.is_symlink(), "Symlinks are not supported: " + str(path))
        if path.is_dir():
            continue
        require(path.is_file(), "Special files are not supported: " + str(path))
        result[path.relative_to(root).as_posix()] = path
    return result


def index_assets(assets):
    result = {}
    for item in assets:
        name = item["name"]
        require(isinstance(name, str) and name not in ("", ".", "..")
                and "/" not in name and "\\" not in name,
                "Asset names must be plain filenames")
        require(name not in result, "Duplicate release asset: " + name)
        result[name] = item
    return result


def plan_assets(directory, manifest, release, release_id):
    """Compare local bytes with a reviewed manifest and an existing release snapshot.

    The output is an advisory plan only. It cannot upload or authorize an upload.
    """
    source = source_sha(manifest["source_commit"])
    require(release["id"] == release_id, "Wrong release ID")
    require(release["tag_name"] == manifest["tag"], "Wrong release tag")
    expected = index_assets(manifest["software_assets"])
    require(expected, "Manifest must name at least one software asset")
    require(manifest["asset_count"] == len(expected), "Wrong manifest asset count")
    local = {}
    for path in files_under(directory).values():
        require(path.name not in local, "Duplicate local asset: " + path.name)
        local[path.name] = path
    require(set(local) == set(expected), "Local files do not match the manifest exactly")
    existing = index_assets(release["assets"])
    missing, unchanged = [], []
    for name, wanted in sorted(expected.items()):
        require(type(wanted["bytes"]) is int and wanted["bytes"] > 0,
                "Asset size must be a positive integer: " + name)
        require(isinstance(wanted["sha256"], str)
                and re.fullmatch(r"[0-9a-f]{64}", wanted["sha256"]),
                "Invalid expected SHA256: " + name)
        require(local[name].stat().st_size == wanted["bytes"]
                and sha256(local[name]) == wanted["sha256"],
                "Local asset differs from its reviewed manifest: " + name)
        if name in existing:
            asset = existing[name]
            require(asset.get("state") == "uploaded"
                    and asset["size"] == wanted["bytes"]
                    and asset.get("digest") == "sha256:" + wanted["sha256"],
                    "Existing release asset differs or lacks verified identity: " + name)
            unchanged.append(name)
        else:
            missing.append(name)
    return {"dry_run": True, "published": False, "release_id": release_id,
            "tag": manifest["tag"], "source_commit": source,
            "upload_candidates": missing, "unchanged": unchanged,
            "preserved_existing": sorted(existing)}


def verify_preserved(before, after):
    """Require all pre-existing asset identities and release text to stay unchanged."""
    for key in ("id", "tag_name", "body", "draft", "prerelease"):
        require(before[key] == after[key], "Release metadata changed: " + key)
    old, new = index_assets(before["assets"]), index_assets(after["assets"])
    for name, asset in old.items():
        require(name in new, "Existing release asset removed: " + name)
        for key in ("id", "size", "digest", "state"):
            require(asset.get(key) == new[name].get(key),
                    "Existing release asset changed: " + name + " (" + key + ")")
    return {"preserved_assets": len(old), "added_assets": sorted(set(new) - set(old))}


def verify_ci(run, jobs, source, repository, required, allowed_skipped=()):
    """Validate complete, externally obtained GitHub run/jobs JSON snapshots."""
    source_sha(source)
    require(run["head_sha"] == source
            and run["head_repository"]["full_name"] == repository,
            "CI run repository/source mismatch")
    require(run["status"] == "completed" and run["conclusion"] == "success",
            "Exact-source CI run did not succeed")
    rows = jobs["jobs"]
    require(jobs["total_count"] == len(rows), "Incomplete jobs snapshot; include all pages")
    names = [job["name"] for job in rows]
    require(len(names) == len(set(names)), "Duplicate job names require explicit review")
    require(required and set(required) <= set(names), "Required CI jobs are missing")
    require(not set(required) & set(allowed_skipped), "Required jobs cannot be skipped")
    for job in rows:
        require(job["run_id"] == run["id"] and job["head_sha"] == source,
                "Job does not belong to the exact-source run: " + job["name"])
        require(job["status"] == "completed", "Incomplete CI job: " + job["name"])
        expected = "skipped" if job["name"] in allowed_skipped else "success"
        require(job["conclusion"] == expected, "Unexpected CI conclusion: " + job["name"])
    return {"source_commit": source, "run_id": run["id"], "verified_jobs": len(rows)}


def verify_source(checkout, source, tag):
    """Check existing refs only; no fetch, checkout, tag creation, or ref updates."""
    source_sha(source)
    require(isinstance(tag, str) and tag and not tag.startswith("-"), "Invalid tag")
    subprocess.run(["git", "check-ref-format", "refs/tags/" + tag], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    def resolve(ref):
        return subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "--verify",
                                        ref + "^{commit}"], text=True).strip()
    require(resolve("HEAD") == source, "Checkout is not at the expected source")
    require(resolve("refs/tags/" + tag) == source, "Tag does not resolve to the expected source")
    subprocess.run(["git", "-C", str(checkout), "diff", "--quiet", source, "--"], check=True)
    return {"source_commit": source, "tag": tag, "tracked_sources_unchanged": True}


def compare_payloads(portable, installer, source, version, repository):
    """Compare already-extracted complete payloads, including embedded ZIP bytes.

    Extraction and privacy/runtime audits remain separate. Never execute an installer.
    """
    source_sha(source)
    inventories = [files_under(root) for root in (portable, installer)]
    for files in inventories:
        require("BUILD-INFO.json" in files, "Pass the payload root containing BUILD-INFO.json")
        info = read_json(files["BUILD-INFO.json"])
        require(info["commit"] == source and info["version"] == version
                and info["repository"] == repository and info["dataflash_formats"] == ["BIN"],
                "Payload build identity mismatch")
        require("DataAPBin.dll" in files or "libDataAPBin.so" in files,
                "DataFlash BIN plugin is missing")
    left, right = inventories
    require(set(left) == set(right), "Installer and portable file sets differ")
    for name, path in left.items():
        require(path.stat().st_size == right[name].stat().st_size
                and sha256(path) == sha256(right[name]), "Payload bytes differ: " + name)
    return {"source_commit": source, "version": version, "matching_files": len(left)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("plan-assets", help="Offline append-only plan; never uploads")
    for option in ("artifacts", "manifest", "release"):
        command.add_argument("--" + option, required=True)
    command.add_argument("--release-id", type=int, required=True)
    command = commands.add_parser("verify-preserved")
    for option in ("before", "after"):
        command.add_argument("--" + option, required=True)
    command = commands.add_parser("verify-ci")
    for option in ("run", "jobs", "source", "repository"):
        command.add_argument("--" + option, required=True)
    command.add_argument("--required-job", action="append", required=True)
    command.add_argument("--allowed-skipped-job", action="append", default=[])
    command = commands.add_parser("verify-source")
    for option in ("checkout", "source", "tag"):
        command.add_argument("--" + option, required=True)
    command = commands.add_parser("compare-payloads")
    for option in ("portable", "installer", "source", "version", "repository"):
        command.add_argument("--" + option, required=True)
    args = parser.parse_args()
    try:
        if args.command == "plan-assets":
            result = plan_assets(args.artifacts, read_json(args.manifest), read_json(args.release),
                                 args.release_id)
        elif args.command == "verify-preserved":
            result = verify_preserved(read_json(args.before), read_json(args.after))
        elif args.command == "verify-ci":
            result = verify_ci(read_json(args.run), read_json(args.jobs), args.source, args.repository,
                               args.required_job, args.allowed_skipped_job)
        elif args.command == "verify-source":
            result = verify_source(args.checkout, args.source, args.tag)
        else:
            result = compare_payloads(args.portable, args.installer, args.source, args.version,
                                      args.repository)
    except (ValueError, KeyError, TypeError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, "Review failed: " + str(error) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
