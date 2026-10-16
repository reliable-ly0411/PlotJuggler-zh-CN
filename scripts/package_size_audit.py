# SPDX-License-Identifier: MPL-2.0
"""Inventory a staged package; fail if regression executables or private metadata ship."""
import argparse
import hashlib
import json
from pathlib import Path
import re

p = argparse.ArgumentParser()
p.add_argument("--payload", required=True)
p.add_argument("--package", action="append", default=[])
p.add_argument("--out", required=True)
a = p.parse_args()
root = Path(a.payload)
files = []
private = re.compile(br"@[qQ][qQ]\.com|@\x00[qQ]\x00[qQ]\x00\.\x00c\x00o\x00m\x00|[A-Z]:\\Users\\(?!Public\\|Default\\|runneradmin\\)[^\\\x00\r\n]+", re.I)
for path in sorted(root.rglob("*")):
    if not path.is_file() or path.is_symlink():
        continue
    name = path.relative_to(root).as_posix()
    assert not re.search(r"(^|/)(pj_.*_test|.*_test\.exe)(\.|$)", name), name
    data = path.read_bytes()
    assert not private.search(data), "Unexpected private metadata in " + name
    files.append({"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
packages = []
for filename in a.package:
    path = Path(filename)
    packages.append({"name": path.name, "bytes": path.stat().st_size,
                     "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
result = {"payload_bytes": sum(f["bytes"] for f in files), "file_count": len(files),
          "test_executables_absent": True, "privacy_scan": "passed", "files": files, "packages": packages}
out = Path(a.out)
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps({k: v for k, v in result.items() if k != "files"}, indent=2))
