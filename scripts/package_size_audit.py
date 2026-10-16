# SPDX-License-Identifier: MPL-2.0
"""Inventory a staged package; fail if regression executables or private metadata ship."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from package_metadata import package_metadata

p = argparse.ArgumentParser()
p.add_argument("--payload", required=True)
p.add_argument("--package", action="append", default=[])
p.add_argument("--out", required=True)
a = p.parse_args()
root = Path(a.payload)
files = []
contacts = re.compile(br"@[qQ][qQ]\.com|@\x00[qQ]\x00[qQ]\x00\.\x00c\x00o\x00m\x00", re.I)
private_path = re.compile(r"[A-Z]:\\Users\\(?!Public\\|Default\\|runneradmin\\)[^\\\x00\r\n]+", re.I)
qt_public_pdb = re.compile(r"[A-Z]:\\Users\\qt\\work\\qt\\[^\x00\r\n]*?\.pdb", re.I)
upstream_markers = []

def check_paths(data, name):
    # Check ASCII and both UTF-16 alignments. Do not exempt a whole dependency:
    # only the specific published Qt builder record / CPython example is classified.
    representations = [data.decode("latin1"), data.decode("utf-16le", errors="ignore"),
                       data[1:].decode("utf-16le", errors="ignore")]
    for text in representations:
        if name.lower().endswith(".dll"):
            text, count = qt_public_pdb.subn("<published Qt PDB record>", text)
            if count:
                upstream_markers.append({"path": name, "kind": "published Qt builder PDB path", "count": count})
        if re.search(r"(^|/)python3\.\d+/venv/scripts/common/Activate\.ps1$", name):
            # Literal documented example in python/cpython v3.10.12, not host data.
            example = "C:\\Users\\MyUser\\Common\\.venv"
            count = text.count(example)
            text = text.replace(example, "<published CPython documentation example>")
            if count:
                upstream_markers.append({"path": name, "kind": "CPython venv documentation example", "count": count})
        assert not private_path.search(text), "Unexpected private path in " + name
for path in sorted(root.rglob("*")):
    if not path.is_file() or path.is_symlink():
        continue
    name = path.relative_to(root).as_posix()
    assert not re.search(r"(^|/)(pj_.*_test|.*_test\.exe)(\.|$)", name), name
    data = path.read_bytes()
    assert not contacts.search(data), "Unexpected personal contact in " + name
    check_paths(data, name)
    files.append({"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
packages = []
for filename in a.package:
    path = Path(filename)
    packages.append({"name": path.name, "bytes": path.stat().st_size,
                     "container": package_metadata(path),
                     "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
result = {"payload_bytes": sum(f["bytes"] for f in files), "file_count": len(files),
          "test_executables_absent": True, "privacy_scan": "passed", "files": files, "packages": packages,
          "classified_upstream_markers": upstream_markers}
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
