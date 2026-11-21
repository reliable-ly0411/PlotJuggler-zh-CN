#!/usr/bin/env python3
"""Check exact source-only overlays and exact, non-skipped CTest coverage."""
from base64 import decodebytes
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys
from xml.etree import ElementTree

PATCHES = {
    "windows": (
        "pj4-windows-fixtures-c1cd3652.patch",
        "dac27d8df652b0926416af9cc4f9d8366ea4ddc39d42f098b723a5e232a015f8",
        {
            "pj_app/tests/layout_xml_test.cpp",
            "pj_app/tests/main_window_layout_dataset_paths_test.cpp",
            "pj_log/tests/log_dock_widget_test.cpp",
        },
    ),
    "mac": (
        "apbin-fc6065fd-portable-test-tmp.patch",
        "da5fcbe284d8f9c548b641d48d445c1d69ad27b573982e0641189e0510fe695b",
        {"sdk4/tests/source_test.cpp"},
    ),
}
TESTS = {
    "windows": {
        "pj_log_tests.LogDockWidgetTest.AVanishedTopicKeepsItsDatasetIdentityAndRebinds",
        "pj_app_unit_tests.KeptFileQualifiers.CanonicalMatchTakesTheExplicitFilesName",
        "pj_app_gui_tests.LayoutDatasetPathsTest.StartupKeptTransformInputTakesTheExplicitFileName",
    },
    "mac": {"ArduPilotDataFlashPlugin"},
}


def assert_true(condition, message):
    if not condition:
        raise SystemExit(message)


def patch(lane, repo):
    path, expected_digest, expected_files = PATCHES[lane]
    blob = decodebytes(Path(__file__).with_name(path + ".b64").read_bytes())
    assert_true(sha256(blob).hexdigest() == expected_digest, f"Unexpected patch bytes: {path}")
    git = ["git", "-C", repo]
    subprocess.run([*git, "diff", "HEAD", "--exit-code"], check=True)
    subprocess.run([*git, "apply", "--check", "-"], input=blob, check=True)
    subprocess.run([*git, "apply", "-"], input=blob, check=True)
    subprocess.run([*git, "diff", "HEAD", "--check"], check=True)
    detected = set(subprocess.check_output([*git, "diff", "HEAD", "--name-only"], text=True).splitlines())
    assert_true(detected == expected_files, f"Expected {expected_files}; found {detected}")
    print(f"Applied {path} ({expected_digest}) to {repo}: {', '.join(sorted(detected))}", flush=True)


def test(lane):
    expected = sorted(TESTS[lane])
    regexp = "^(" + "|".join(re.escape(n) for n in expected) + ")$"
    command = ["ctest", "--test-dir", "build"]
    if lane == "windows":
        command += ["--build-config", "RelWithDebInfo"]
    command += ["-R", regexp]
    selected_json = subprocess.check_output([*command, "--show-only=json-v1"], text=True)
    selected = sorted(t["name"] for t in json.loads(selected_json)["tests"])
    assert_true(selected == expected, f"Expected {expected}; CTest selected {selected}")
    for name in selected:
        print(f"Selected {name}", flush=True)
    report = Path("build/pj71-focused-results.xml").resolve()
    report.unlink(missing_ok=True)
    subprocess.run(
        [*command, "--no-tests=error", "--output-on-failure", "--timeout", "120", "--output-junit", str(report)],
        check=True,
    )
    cases = ElementTree.parse(report).findall(".//testcase")
    executed = sorted(case.get("name") for case in cases)
    assert_true(executed == expected, f"Expected {expected}; JUnit executed {executed}")
    for case in cases:
        assert_true(
            case.get("status") == "run"
            and all(case.find(child) is None for child in ("failure", "error", "skipped")),
            f"Expected actual pass: {case.get('name')}: {ElementTree.tostring(case, encoding='unicode')}",
        )
    print(f"{len(cases)}/{len(expected)} passed with no skips.", flush=True)


if __name__ == "__main__":
    action, lane, *args = sys.argv[1:]
    if action == "patch":
        patch(lane, *args)
    elif action == "test":
        test(lane)
    else:
        raise SystemExit(f"Unknown action {action}")
