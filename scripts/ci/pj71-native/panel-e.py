"""Materialize independent candidate E and require precise, non-skipped Qt CTest coverage."""
from base64 import decodebytes
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess as sp
import sys
from xml.etree import ElementTree as ET

A = "857bd12b935579458914de18b59d8950b8bf71bd"
D = "2e9235ef1575551f4fa14c84ce150301e4022bcd"
TREE = "483bb27b54c929697295978fc66a1c59da4870d5"
PATCH = "fc472e762767f3da60cfcb27ca0dcc38445c74610d19d38c7099c39b7da9ba94"
E = "84eabea0353dba95b7288166a618f5d827af1fc1"
E_TREE = "22ea9ccccd54ab2e78bdc2f44ed0ef94c2ad2de5"
E_PATCH = "a737da3dd27f114e9448dd7b36f49509c466cccad7edbd90bf44602bc5440c7a"
E_SCOPE = ["pj_dialog_host/include/pj_plugins/host_qt/widget_binding.hpp",
           "pj_dialog_host/src/panel_engine.cpp", "pj_dialog_host/src/widget_binding.cpp"]
HERE = Path(__file__).parent
EVID = Path("panel-e-evidence")
EVID.mkdir(exist_ok=True)
PRODUCT_FILE = Path("pj_dialog_host/src/panel_engine.cpp")
REGRESSION = "a045779d6fa10b9a181bb467234e620ec95f9f941a87d8d39ba85e923391d90e"
TEST_BLOBS = {
    "pj_dialog_host/tests/mock_panel_plugin.cpp": "1308e57fbeaa4cdf29a39ef85db716631d496c4e",
    "pj_dialog_host/tests/mock_panel_plugin.hpp": "c6e83fb86db7b5daf08ab9fd8e025b90af087c8b",
    "pj_dialog_host/tests/panel_engine_test.cpp": "cf4a3ffd30c941815296313b7e19d560fd48702a",
}
TEST_SCOPE = sorted(TEST_BLOBS)


def require(valid, message):
    if not valid:
        raise SystemExit(message)


def git(*args, **kwargs):
    return sp.check_output(["git", *args], text=True, **kwargs).strip()


def patch(name, digest):
    blob = decodebytes((HERE / name).read_bytes())
    require(sha256(blob).hexdigest() == digest, f"Patch mismatch: {name}")
    return blob


def overlay(*args, blob):
    sp.run(["git", "apply", *args, "--whitespace=error", "-"], input=blob, check=True)


def require_test_overlay():
    require(git("diff", "--name-only", "HEAD").splitlines() == TEST_SCOPE, "Unexpected tracked diff")
    git("diff", "--cached", "HEAD", "--exit-code")
    # Formatted diffs abbreviate blob IDs differently for shallow and full repositories.
    # Check full Git blob identities after applying the separately hash-verified patch.
    for path, expected in TEST_BLOBS.items():
        require(git("hash-object", "--", path) == expected, f"Test overlay bytes changed: {path}")


if sys.argv[1] == "source":
    require(git("rev-parse", "HEAD") == A, "Wrong original product")
    require(git("-C", "probe-control", "rev-parse", "HEAD") == os.environ["GITHUB_SHA"], "Wrong control")
    git("diff", "HEAD", "--exit-code")
    blob = decodebytes((HERE / "panel-d.patch.b64").read_bytes())
    require(sha256(blob).hexdigest() == PATCH, "Exact D patch mismatch")
    (EVID / "D-product.patch").write_bytes(blob)
    for check in [["--check"], []]:
        sp.run(["git", "apply", *check, "--index", "--whitespace=error", "-"], input=blob, check=True)
    git("diff", "--cached", "--check", A)
    require(git("diff", "--cached", "--name-only", A) == "pj_dialog_host/src/panel_engine.cpp", "Unexpected product scope")
    require(git("write-tree") == TREE, "Candidate tree mismatch")
    env = os.environ.copy()
    for prefix in ["AUTHOR", "COMMITTER"]:
        env.update({f"GIT_{prefix}_NAME": "PlotJuggler candidate CI",
                    f"GIT_{prefix}_EMAIL": "candidate-ci@example.invalid",
                    f"GIT_{prefix}_DATE": "2026-11-21T17:20:00Z"})
    result = git("-c", "commit.gpgSign=false", "commit-tree", TREE, "-p", A, "-m",
                 "Preserve startup registrations with shared parsed panel data", env=env)
    require(result == D, "Candidate commit mismatch")
    git("checkout", "--detach", D)
    identity = git("rev-parse", "HEAD", "HEAD^{tree}", "HEAD^").splitlines()
    require(identity == [D, TREE, A], "Candidate readback mismatch")
    git("diff", "HEAD", "--exit-code")
    (EVID / "D-product.commit").write_bytes(sp.check_output(["git", "cat-file", "commit", D]))
    e_patch = patch("panel-e.patch.b64", E_PATCH)
    (EVID / "E-product.patch").write_bytes(e_patch)
    overlay("--index", "--check", blob=e_patch)
    overlay("--index", blob=e_patch)
    git("diff", "--cached", "--check", D)
    require(git("diff", "--cached", "--name-only", D).splitlines() == E_SCOPE, "Unexpected E scope")
    require(git("write-tree") == E_TREE, "E tree mismatch")
    for prefix in ["AUTHOR", "COMMITTER"]:
        env[f"GIT_{prefix}_DATE"] = "2026-11-22T02:00:00Z"
    result = git("-c", "commit.gpgSign=false", "commit-tree", E_TREE, "-p", D, "-m",
                 "Apply parsed panel updates without re-encoding changed widget data", env=env)
    require(result == E, "E commit mismatch")
    git("checkout", "--detach", E)
    require(git("rev-parse", "HEAD", "HEAD^{tree}", "HEAD^").splitlines() == [E, E_TREE, D],
            "E readback mismatch")
    git("diff", "HEAD", "--exit-code")
    (EVID / "E-product.commit").write_bytes(sp.check_output(["git", "cat-file", "commit", E]))
    (EVID / "identity.json").write_text(json.dumps({
        "product": E, "tree": E_TREE, "parent": D, "base": A, "patch_sha256": E_PATCH,
        "controller": os.environ["GITHUB_SHA"], "run": os.environ["GITHUB_RUN_ID"],
        "required_qt": "6.12.0",
    }, indent=2))
    tests = patch("panel-e-regression.patch.b64", REGRESSION)
    (EVID / "E-native-test.patch").write_bytes(tests)
    overlay("--check", blob=tests)
    overlay(blob=tests)
    require_test_overlay()
elif sys.argv[1] == "test":
    require(git("rev-parse", "HEAD", "HEAD^{tree}").splitlines() == [E, E_TREE], "Product moved before CTest")
    require_test_overlay()
    expected = sorted((HERE / "panel-e-tests.txt").read_text().splitlines())
    require(len(expected) == len(set(expected)) == 34, "Wrong exact test roster")
    expr = r"^pj_dialog_host_panel_tests\.(PanelEngineTest|ParsedWidgetData)\."
    command = ["ctest", "--test-dir", "build", "-R", expr]
    raw = sp.check_output([*command, "--show-only=json-v1"], text=True)
    (EVID / "ctest-selection.json").write_text(raw)
    selected = sorted(t["name"] for t in json.loads(raw)["tests"])
    require(selected == expected, f"Wrong CTest selection: {selected!r}")
    junit = EVID.resolve() / "panel-e-results.xml"
    sp.run([*command, "--no-tests=error", "--output-on-failure", "--timeout", "120",
            "--output-junit", str(junit)], check=True)
    cases = ET.parse(junit).findall(".//testcase")
    require(sorted(case.get("name") for case in cases) == expected, "Actual cases differ from selected cases")
    for case in cases:
        require(case.get("status") == "run" and not any(
            case.find(name) is not None for name in ("skipped", "failure", "error")),
            f"Case did not pass: {case.get('name')}")
    print(f"{len(cases)}/34 executed and passed, no skips.")
else:
    raise SystemExit("Use source or test")
