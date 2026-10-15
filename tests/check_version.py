# SPDX-License-Identifier: MPL-2.0
"""Validate the public SemVer and the installer's numeric component mapping."""
import argparse
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--build-file", default="build/FORK-VERSION.json")
args = parser.parse_args()
cmake = (root / "CMakeLists.txt").read_text(encoding="utf-8")
core = re.search(r"\bVERSION\s+(\d+\.\d+\.\d+)", cmake)[1]
version = json.loads((root / args.build_file).read_text(encoding="utf-8"))
pattern = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$")
match = pattern.fullmatch(version["version"])
assert match, version
assert ".".join(match.groups()[:3]) == core, version
assert match[4] == "zh.1", version
assert match[5] == f"upstream.{version['upstream_version']}.apbin.{version['ardupilot_revision']}.g{version['source_revision']}", version
for identifier in match[4].split("."):
    assert not (identifier.isdigit() and len(identifier) > 1 and identifier.startswith("0"))
for path in ("installer/config.xml", "installer/io.plotjuggler.application/meta/package.xml"):
    assert ET.parse(root / path).getroot().findtext("Version") == core + "-1", path
assert ET.parse(root / "package.xml").getroot().findtext("version") == core
print("PASS: SemVer product, upstream metadata, installer and package versions: " + version["version"])
