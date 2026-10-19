#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Guard the fork's declared 4.x development lineage and SemVer metadata."""
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
record = json.loads((ROOT / "docs/localization/upstream-baseline.json").read_text(encoding="utf-8"))
assert record["upstream_branch"] == "main-4.x"
assert record["stable_branch"] == "zh-CN-4.x"
assert record["development_branch"] == "zh-CN-4.x-dev"
assert record["status"] == "development"
for key in ("upstream_commit", "localization_source_commit"):
    assert re.fullmatch(r"[0-9a-f]{40}", record[key]), f"Invalid {key}"
values = dict(line.split("=", 1) for line in (ROOT / "versions.env").read_text().splitlines()
              if line and not line.startswith("#"))
assert re.fullmatch(r"4\.\d+\.\d+-zh\.[1-9]\d*\.dev\.[1-9]\d*", values["PJ_APP_VERSION"]), \
    "The 4.x development line must use an explicit SemVer prerelease"
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
assert plugin["sdk_version"] == "0.34.1"
for key in ("commit", "upstream_commit", "sdk_source_commit"):
    assert re.fullmatch(r"[0-9a-f]{40}", plugin[key]), f"Invalid plugin {key}"
# The Git index exists even when a source-check job has not initialized submodules.
entry = subprocess.run(["git", "ls-files", "--stage", "--", plugin["path"]], cwd=ROOT,
                       check=True, capture_output=True, text=True).stdout.split()
assert entry[:3] == ["160000", plugin["commit"], "0"], "BIN gitlink must match the declared fixed commit"
url = subprocess.run(["git", "config", "-f", ".gitmodules", "--get",
                      f"submodule.{plugin['path']}.url"], cwd=ROOT,
                     check=True, capture_output=True, text=True).stdout.strip()
assert url == plugin["repository"] + ".git", "Unexpected BIN submodule repository"
print("4.x provenance, development SemVer and fixed BIN gitlink verified")
