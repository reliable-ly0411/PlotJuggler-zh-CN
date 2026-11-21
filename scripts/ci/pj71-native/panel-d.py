"""Materialize independent candidate D and require precise, non-skipped Qt CTest coverage."""
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
HERE = Path(__file__).parent
EVID = Path("panel-d-evidence")
EVID.mkdir(exist_ok=True)
PRODUCT_FILE = Path("pj_dialog_host/src/panel_engine.cpp")
REGRESSION = "bc4ab9d843de918f4d47fff424efa83fb0e3ec48c0876f25798198fce77f71da"
C_TO_D = "9fdbece580d57e5277c2625af254754661d6674d6e7501881825ee71cf4fe0a6"
C_SOURCE_BLOB = "c7e865a6e9fefbe0eee53a9073a5b59ea612b7d6"
TEST_SCOPE = ["pj_dialog_host/tests/" + name for name in (
    "mock_panel_plugin.cpp", "mock_panel_plugin.hpp", "panel_engine_test.cpp",
)]
NEGATIVE_FAILURES = {
    "StartupDocumentInstallsCatalogDropTarget": "panel->acceptDrops()",
    "StartupDocumentInstallsButtonShortcut": "shortcuts.end()",
}


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
    require(git("diff", "--binary", "HEAD") + "\n" == (EVID / "D-native-test.patch").read_text(),
            "Test overlay bytes changed")


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
        env.update({f"GIT_{prefix}_NAME": "PlotJuggler candidate DI",
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
    (EVID / "identity.json").write_text(json.dumps({
        "product": D, "tree": TREE, "parent": A, "patch_sha256": PATCH,
        "controller": os.environ["GITHUB_SHA"], "run": os.environ["GITHUB_RUN_ID"],
        "required_qt": "6.12.0",
    }, indent=2))
    tests = patch("panel-d-regression.patch.b64", REGRESSION)
    (EVID / "D-native-test.patch").write_bytes(tests)
    overlay("--check", blob=tests)
    overlay(blob=tests)
    require_test_overlay()
elif sys.argv[1] == "test":
    require(git("rev-parse", "HEAD", "HEAD^{tree}").splitlines() == [D, TREE], "Product moved before CTest")
    require_test_overlay()
    expected = sorted((HERE / "panel-d-tests.txt").read_text().splitlines())
    require(len(expected) == len(set(expected)) == 31, "Wrong exact test roster")
    expr = r"^pj_dialog_host_panel_tests\.(PanelEngineTest|ParsedWidgetData)\."
    command = ["ctest", "--test-dir", "build", "-R", expr]
    raw = sp.check_output([*command, "--show-only=json-v1"], text=True)
    (EVID / "ctest-selection.json").write_text(raw)
    selected = sorted(t["name"] for t in json.loads(raw)["tests"])
    require(selected == expected, f"Wrong CTest selection: {selected!r}")
    junit = EVID.resolve() / "panel-d-results.xml"
    sp.run([*command, "--no-tests=error", "--output-on-failure", "--timeout", "120",
            "--output-junit", str(junit)], check=True)
    cases = ET.parse(junit).findall(".//testcase")
    require(sorted(case.get("name") for case in cases) == expected, "Actual cases differ from selected cases")
    for case in cases:
        require(case.get("status") == "run" and not any(
            case.find(name) is not None for name in ("skipped", "failure", "error")),
            f"Case did not pass: {case.get('name')}")
    print(f"{len(cases)}/31 executed and passed, no skips.")
elif sys.argv[1] == "negative":
    require(git("rev-parse", "HEAD", "HEAD^{tree}").splitlines() == [D, TREE], "Wrong D negative-control base")
    require_test_overlay()
    require((EVID / "panel-d-results.xml").is_file(), "D positive test evidence missing")
    c_to_d = patch("panel-d-to-c.patch.b64", C_TO_D)
    overlay("--check", "--reverse", blob=c_to_d)
    original = PRODUCT_FILE.read_bytes()
    try:
        overlay("--reverse", blob=c_to_d)
        require(git("hash-object", str(PRODUCT_FILE)) == C_SOURCE_BLOB, "Wrong exact C source blob")
        require(git("diff", "--name-only", "HEAD").splitlines() == [str(PRODUCT_FILE), *TEST_SCOPE],
                "Negative control must only swap the former source file")
        sp.run(["cmake", "--build", "build", "--target", "pj_dialog_host_panel_tests", "--parallel", "2"], check=True)
        expr = r"^pj_dialog_host_panel_tests\.PanelEngineTest\.(" + "|".join(NEGATIVE_FAILURES) + ")$"
        command = ["ctest", "--test-dir", "build", "-R", expr]
        raw = sp.check_output([*command, "--show-only=json-v1"], text=True)
        (EVID / "negative-control-selection.json").write_text(raw)
        selected = {t["name"].rsplit(".", 1)[-1] for t in json.loads(raw)["tests"]}
        require(selected == NEGATIVE_FAILURES.keys(), f"Wrong negative test selection: {selected}")
        junit = EVID.resolve() / "panel-c-negative-results.xml"
        result = sp.run([*command, "--no-tests=error", "--output-on-failure", "--timeout", "120",
                         "--output-junit", str(junit)], check=False)
        require(result.returncode == 8, f"Unexpected CTest result: {result.returncode}")
        cases = ET.parse(junit).findall(".//testcase")
        require(len(cases) == 2, "Missing negative-control evidence")
        for case in cases:
            name = case.get("name").rsplit(".", 1)[-1]
            require(case.get("status") == "fail" and case.find("failure") is not None
                    and case.find("skipped") is None and case.find("error") is None,
                    f"Test did not assert a regression: {name}")
            require(NEGATIVE_FAILURES[name] in (case.findtext("system-out") or ""),
                    f"Wrong failure cause: {name}")
        print("Exact candidate C translation unit rejected by both focused startup assertions.")
    finally:
        PRODUCT_FILE.write_bytes(original)
        require_test_overlay()
else:
    raise SystemExit("Use source, test or negative")
