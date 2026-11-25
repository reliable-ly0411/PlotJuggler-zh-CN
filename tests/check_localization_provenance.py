#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Guard the fork's declared 4.x development lineage and SemVer metadata."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
record = json.loads((ROOT / "docs/localization/upstream-baseline.json").read_text(encoding="utf-8"))
assert record["upstream_branch"] == "main"
assert record["stable_branch"] == "zh-CN-4.x"
assert record["development_branch"] == "zh-CN-4.x-dev"
assert record["status"] in ("development", "prerelease", "release")
for key in ("upstream_commit", "localization_source_commit"):
    assert re.fullmatch(r"[0-9a-f]{40}", record[key]), f"Invalid {key}"
values = dict(line.split("=", 1) for line in (ROOT / "versions.env").read_text(encoding='utf-8').splitlines()
              if line and not line.startswith("#"))
version = values["PJ_APP_VERSION"]
if record["status"] == "release":
    match = re.fullmatch(r"(4\.\d+\.\d+)\+zh\.[1-9]\d*", version)
    assert match, "Stable Chinese releases use a SemVer core plus build metadata"
    assert record["upstream_tag"] == record["upstream_release"]["tag"] == match.group(1)
    assert record["upstream_commit"] == record["upstream_release"]["commit"]
    assert re.fullmatch(r"[0-9a-f]{40}", record["upstream_tag_object"])
else:
    assert re.fullmatch(r"4\.\d+\.\d+-zh\.[1-9]\d*\.(?:dev|rc)\.[1-9]\d*", version), \
        "Development and candidate builds require an explicit SemVer prerelease"
    assert (".rc." in version) == (record["status"] == "prerelease")
assert values["PJ_QT_VERSION"].startswith("6."), "Qt5 is not the PJ4 toolchain"
# Shallow CI clones cannot prove historical ancestry. Deep checkouts must.
shallow = subprocess.run(["git", "rev-parse", "--is-shallow-repository"], cwd=ROOT,
                         check=True, capture_output=True, text=True).stdout.strip()
if shallow == "false":
    subprocess.run(["git", "merge-base", "--is-ancestor", record["upstream_commit"], "HEAD"],
                   cwd=ROOT, check=True)
plugin = record["ardupilot_plugin"]
assert plugin["repository"] == "https://github.com/reliable-ly0411/plotjuggler-apbin-plugins"
assert plugin["branch"] == "plotjuggler-4.x-sdk"
assert plugin["sdk_version"] == record["host_sdk_version"], "BIN rebuild SDK differs from host baseline"
host_sdk = json.loads((ROOT / "cmake/host-sdk-source.json").read_text(encoding="utf-8"))
assert plugin["sdk_version"] == host_sdk["version"], "BIN rebuild SDK differs from locked host SDK"
assert plugin["sdk_source_commit"] == host_sdk["commit"], "BIN rebuild SDK source differs from locked host SDK"
for key in ("commit", "upstream_commit", "sdk_source_commit", "release_commit"):
    assert re.fullmatch(r"[0-9a-f]{40}", plugin[key]), f"Invalid plugin {key}"
assert plugin['release_tag'] == 'v' + plugin['version'], 'BIN release tag and manifest version differ'
assert re.fullmatch(r'[0-9a-f]{64}', plugin['source_manifest_sha256']), 'Invalid BIN source manifest SHA256'
# The Git index exists even when a source-check job has not initialized submodules.
entry = subprocess.run(["git", "ls-files", "--stage", "--", plugin["path"]], cwd=ROOT,
                       check=True, capture_output=True, text=True).stdout.split()
assert entry[:3] == ["160000", plugin["commit"], "0"], "BIN gitlink must match the declared fixed commit"
url = subprocess.run(["git", "config", "-f", ".gitmodules", "--get",
                      f"submodule.{plugin['path']}.url"], cwd=ROOT,
                     check=True, capture_output=True, text=True).stdout.strip()
assert url == plugin["repository"] + ".git", "Unexpected BIN submodule repository"
display = json.loads((ROOT / 'packaging/localization/bundled-plugin-metadata.json').read_text(encoding='utf-8'))
apbin_display = [item for item in display if item['id'] == 'ardupilot-dataflash']
assert len(apbin_display) == 1 and apbin_display[0]['version'] == plugin['version'], 'BIN display identity must match baseline'
# Source-only CI may omit submodules; initialized build checkouts must prove the
# actual pinned manifest before downloading dependencies or compiling the host.
source_manifest = ROOT / plugin['path'] / 'sdk4/manifest.json'
if source_manifest.is_file():
    source_head = subprocess.check_output(['git', '-C', str(ROOT / plugin['path']), 'rev-parse', 'HEAD'], text=True).strip()
    assert source_head == plugin['commit'], 'BIN source checkout differs from its pin'
    # The submodule has no .gitattributes: Windows may check JSON out with CRLF.
    # Hash the immutable Git blob, then bind the file consumed by CMake to those
    # same bytes, permitting only uniform checkout newline conversion.
    source_blob = subprocess.check_output(['git', '-C', str(ROOT / plugin['path']),
                                           'show', plugin['commit'] + ':sdk4/manifest.json'])
    assert hashlib.sha256(source_blob).hexdigest() == plugin['source_manifest_sha256'], 'BIN source manifest hash differs'
    assert source_manifest.read_bytes() in (source_blob, source_blob.replace(b'\n', b'\r\n')), 'BIN checkout manifest differs from pinned source'
    manifest = json.loads(source_manifest.read_text(encoding='utf-8'))
    assert manifest['id'] == 'ardupilot-dataflash' and manifest['version'] == plugin['version'], 'BIN source manifest identity differs'
    assert manifest['license'] == plugin['license'] == 'LGPL-3.0-only', 'BIN source manifest license differs'
print("4.x provenance, release/development SemVer and fixed BIN gitlink verified")
