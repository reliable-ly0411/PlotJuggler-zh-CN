# SPDX-License-Identifier: MPL-2.0
"""Validate the public SemVer and the installer's numeric component mapping."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--build-file", default="build/FORK-VERSION.json")
parser.add_argument("--source-only", action="store_true", help="check static candidate/installer consistency before expensive builds")
args = parser.parse_args()
cmake = (root / "CMakeLists.txt").read_text(encoding="utf-8")
core = re.search(r"\bVERSION\s+(\d+\.\d+\.\d+)", cmake)[1]
version_cmake = (root / "cmake/ForkVersion.cmake").read_text(encoding="utf-8")
prerelease = re.search(r'set\(PJ_FORK_PRERELEASE "([^"]+)"\)', version_cmake)[1]
candidate = re.fullmatch(r"rc\.([1-9][0-9]*)", prerelease)
assert candidate, "invalid candidate prerelease"
for path in ("installer/config.xml", "installer/io.plotjuggler.application/meta/package.xml"):
    assert ET.parse(root / path).getroot().findtext("Version") == core + "-" + candidate[1], path
assert ET.parse(root / "package.xml").getroot().findtext("version") == core
if args.source_only:
    print("PASS: source-only candidate/installer versions: " + core + "-" + prerelease)
    raise SystemExit(0)
version = json.loads((root / args.build_file).read_text(encoding="utf-8"))
pattern = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$")
match = pattern.fullmatch(version["version"])
assert match and ".".join(match.groups()[:3]) == core and match[4] == prerelease, version
assert version["source_revision"] == subprocess.check_output(
    ["git", "rev-parse", "--short=12", "HEAD"], cwd=root, text=True).strip(), version
assert match[5] == f"upstream.{version['upstream_version']}.apbin.{version['ardupilot_revision']}.g{version['source_revision']}", version
for identifier in match[4].split("."):
    assert not (identifier.isdigit() and len(identifier) > 1 and identifier.startswith("0"))
assert version["upstream_sha"] == "df5cbaad9bb087413470e818fa5cdb88d6357ce5", version
assert version["downstream_start"] == "cbc7b7287884208b5a9042de45bcab4b5dcd79c0", version
assert ET.parse(root / "package.xml").getroot().findtext("version") == core
print("PASS: SemVer product, upstream metadata, installer and package versions: " + version["version"])
