# SPDX-License-Identifier: MPL-2.0
"""Inventory a staged package; fail if regression executables or private metadata ship."""
import argparse
import hashlib
import json
import os
import platform
from pathlib import Path
import re
import shutil
import subprocess
import sys
from package_metadata import package_metadata
from package_privacy import check_metadata, load_public_records, TASK_PRIVATE_ROOT
from private_build_roots import load_private_roots, contains_private_root, stage_inventory_sha256

p = argparse.ArgumentParser()
p.add_argument("--payload", required=True)
p.add_argument("--package", action="append", default=[])
p.add_argument("--out", required=True)
p.add_argument("--private-build-roots", required=True, help="private manifest path; never published")
a = p.parse_args()
if Path(a.out).exists():
    raise SystemExit("Audit output must be a new file")
try:
    private_roots = load_private_roots(a.private_build_roots)
except ValueError:
    raise SystemExit("Invalid private build roots manifest") from None
root = Path(a.payload)
if not root.is_dir() or root.is_symlink():
    raise SystemExit("Invalid payload directory")
root_absolute = root.resolve()
if Path(a.private_build_roots).resolve().is_relative_to(root_absolute):
    raise SystemExit("Private build roots manifest must be outside payload")
covered_files = set()
linked_files = []
linked_dirs = []
covered_dirs = set()
files = []
upstream_markers = []
public_records = load_public_records()
privacy_errors = []
unexpected_test_payloads = []
root_errors = []
def reject_walk_error(error):
    raise OSError("Payload enumeration failed") from error

entries = []
for directory, dirnames, filenames in os.walk(root, topdown=True, onerror=reject_walk_error, followlinks=False):
    covered_dirs.add(Path(directory).resolve())
    entries.extend(Path(directory) / name for name in dirnames + filenames)
for path in sorted(entries):
    if path.is_symlink():
        reason = "readlink-failed"
        link_data = b""
        try:
            link_data = os.readlink(path).encode("utf-8")
            reason = "target-metadata-rejected"
            check_metadata(link_data, "payload-symlink", {}, private_roots)
            reason = "target-missing-or-loop"
            resolved = path.resolve(strict=True)
            reason = "target-outside-payload"
            if not resolved.is_relative_to(root_absolute):
                raise ValueError()
            reason = "target-not-file-or-directory"
            if resolved.is_file():
                linked_files.append(resolved)
            elif resolved.is_dir():
                linked_dirs.append(resolved)
            else:
                raise ValueError()
        except (OSError, ValueError, RuntimeError):
            relative = path.relative_to(root).as_posix()
            try:
                check_metadata(relative.encode(), "symlink-name", {}, private_roots)
                safe_name = relative
            except ValueError:
                safe_name = "sha256:" + hashlib.sha256(relative.encode()).hexdigest()
            failure = {"status": "failed", "rule": "unsafe-payload-symlink",
                       "path": safe_name, "reason": reason,
                       "target_sha256": hashlib.sha256(link_data).hexdigest()}
            # Never print an absolute link target or the private-root manifest.
            diagnostic = Path(a.out + ".failure.json")
            with diagnostic.open("x", encoding="utf-8") as stream:
                json.dump(failure, stream, indent=2)
            raise SystemExit("Unsafe or unscanned payload symlink: " +
                             json.dumps(failure)) from None
        continue
    if not path.is_file():
        if not path.is_dir():
            raise SystemExit("Unsupported payload entry")
        continue
    name = path.relative_to(root).as_posix()
    is_test_payload = bool(re.search(r"(^|/)(pj_.*_tests?|pj_language_probe|test_[^/]+|[^/]*_tests?)(\.|$)", name))
    data = path.read_bytes()
    covered_files.add(path.resolve())
    task_views = (data.decode("latin1"), data.decode("utf-8", errors="replace"),
                  data.decode("utf-16le", errors="ignore"), data[1:].decode("utf-16le", errors="ignore"))
    if contains_private_root(data, private_roots) or any(TASK_PRIVATE_ROOT.search(v) for v in task_views):
        root_errors.append({"path": name, "rule": "Unexpected private path"})
    try:
        upstream_markers.extend(check_metadata(data, name, public_records, private_roots))
    except ValueError as error:
        # Preserve file identity for review without printing matched content.
        privacy_errors.append({"path": name, "sha256": hashlib.sha256(data).hexdigest(),
                               "rule": str(error)})
    file_info = {"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    files.append(file_info)
    if is_test_payload:
        unexpected_test_payloads.append(file_info)
if (not files or any(path not in covered_files for path in linked_files)
        or any(path not in covered_dirs for path in linked_dirs)):
    raise SystemExit("Payload scan incomplete")
packages = []
for filename in a.package:
    path = Path(filename)
    packages.append({"name": path.name, "bytes": path.stat().st_size,
                     "container": package_metadata(path),
                     "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
result = {"private_build_root_scan": {"scope": "staged payload",
          "status": "failed" if root_errors else "passed",
          "manifest_sha256": private_roots["manifest_sha256"],
          "root_count": private_roots["root_count"],
          "scanned_files": len(covered_files), "errors": root_errors,
          "stage_inventory_sha256": stage_inventory_sha256(files)},
          "payload_bytes": sum(f["bytes"] for f in files), "file_count": len(files),
          "test_executables_absent": not unexpected_test_payloads,
          "unexpected_test_payloads": unexpected_test_payloads,
          "privacy_scan": "failed" if privacy_errors else "passed",
          "privacy_errors": privacy_errors, "files": files, "packages": packages,
          "classified_upstream_markers": upstream_markers}
build_info = list(root.rglob("BUILD-INFO.json"))
assert len(build_info) == 1, "Exactly one package build identity is required"
result["build_info"] = json.loads(build_info[0].read_text(encoding="utf-8-sig"))
result["build_arch"] = platform.machine()
if Path("/etc/os-release").is_file():
    result["build_os"] = dict(line.split("=", 1) for line in
                             Path("/etc/os-release").read_text().splitlines()
                             if "=" in line and not line.startswith("#"))
out = Path(a.out)
out.parent.mkdir(parents=True, exist_ok=True)
qt_root = os.environ.get("QT_ROOT_DIR")
qt_rcc = Path(qt_root) / "bin" / ("rcc.exe" if os.name == "nt" else "rcc") if qt_root else None
rcc = str(qt_rcc) if qt_rcc and qt_rcc.is_file() else (shutil.which("rcc") or shutil.which("rcc-qt5"))
if rcc:
    version = subprocess.check_output([rcc, "--version"], stderr=subprocess.STDOUT, text=True)
    assert re.search(r"\brcc 5\.", version), "Package audit requires the production Qt5 RCC"
    resource_report = out.with_name("qt5-rcc.json")
    subprocess.run([sys.executable, str(Path(__file__).with_name("resource_size_audit.py")),
                    "--rcc", rcc, "--current-only", "--out", str(resource_report)], check=True)
    result["qt5_rcc"] = json.loads(resource_report.read_text(encoding="utf-8"))
else:
    assert os.environ.get("GITHUB_ACTIONS") != "true", "Production Qt5 RCC is missing from PATH"
out.write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps({k: v for k, v in result.items() if k != "files"}, indent=2))
if unexpected_test_payloads or privacy_errors:
    raise SystemExit("Package policy failed; review the recorded test payloads, privacy errors and file hashes")
