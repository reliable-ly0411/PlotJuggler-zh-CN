# SPDX-License-Identifier: MPL-2.0
"""Capture both language modes from the compiled app using synthetic data only."""
import argparse
import json
import os
from pathlib import Path
import subprocess

p = argparse.ArgumentParser()
p.add_argument("--app", required=True)
p.add_argument("--plugin", required=True)
p.add_argument("--out", required=True)
a = p.parse_args()
app = Path(a.app).resolve()
plugin = Path(a.plugin).resolve()
assert app.is_file(), app
assert plugin.is_file(), plugin
root = Path(__file__).resolve().parents[1]
fixture = root / "plotjuggler_plugins/DataLoadAPBin/tests/synthetic.BIN"
expected_version = json.loads((root / "build/FORK-VERSION.json").read_text(encoding="utf-8"))["version"]
reports = []
for language in ("zh_CN", "en_US"):
    out = Path(a.out).resolve() / language
    out.mkdir(parents=True, exist_ok=True)
    command = [str(app), "-n", "--disable_opengl",
               "--self-test-ui", str(out), "-d", str(fixture)]
    if language == "en_US": command += ["--language", "en_US"]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=45)
    (out / "process.log").write_bytes(result.stdout)
    if result.returncode:
        raise SystemExit(f"{language} UI acceptance failed: {result.returncode}\n{result.stdout.decode('utf-8', errors='replace')}")
    report = json.loads((out / "ui.json").read_text(encoding="utf-8"))
    assert report["version"] == expected_version, report
    assert report["language_ok"] and report["menu_ok"] and report["screenshot_ok"], report
    assert report["data_ok"] and report["numeric_series"] >= 4, report
    reports.append({"language": language, **report})
Path(a.out, "summary.json").write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
print("PASS: Chinese default catalog, English override, real UI screenshots, bundled DataFlash loader")
