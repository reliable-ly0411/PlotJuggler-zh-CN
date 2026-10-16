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
from package_privacy import check_metadata, load_public_records

p = argparse.ArgumentParser()
p.add_argument("--payload", required=True)
p.add_argument("--package", action="append", default=[])
p.add_argument("--out", required=True)
a = p.parse_args()
root = Path(a.payload)
files = []
upstream_markers = []
public_records = load_public_records()
privacy_errors = []
for path in sorted(root.rglob("*")):
    if not path.is_file() or path.is_symlink():
        continue
    name = path.relative_to(root).as_posix()
    assert not re.search(r"(^|/)(pj_.*_test|.*_test\.exe)(\.|$)", name), name
    data = path.read_bytes()
    try:
        upstream_markers.extend(check_metadata(data, name, public_records))
    except ValueError as error:
        # Preserve file identity for review without printing matched content.
        privacy_errors.append({"path": name, "sha256": hashlib.sha256(data).hexdigest(),
                               "rule": str(error)})
    files.append({"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
packages = []
for filename in a.package:
    path = Path(filename)
    packages.append({"name": path.name, "bytes": path.stat().st_size,
                     "container": package_metadata(path),
                     "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
result = {"payload_bytes": sum(f["bytes"] for f in files), "file_count": len(files),
          "test_executables_absent": True, "privacy_scan": "failed" if privacy_errors else "passed",
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
if privacy_errors:
    raise SystemExit("Package privacy policy failed; review the recorded file hashes")
