"""Materialize independent candidate C and require precise, non-skipped Qt CTest coverage."""
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
C = "982a614372d7fda3b20ba3e31f246850f2ab6f82"
TREE = "128250ace3e03e3ab728bed21535731b588c64c3"
PATCH = "23fe3be903d043d0802a50139847356d2ae20bafa176e68a74ee76c74375eb4d"
HERE = Path(__file__).parent
EVID = Path("panel-c-evidence")
EVID.mkdir(exist_ok=True)


def require(valid, message):
    if not valid:
        raise SystemExit(message)


def git(*args, **kwargs):
    return sp.check_output(["git", *args], text=True, **kwargs).strip()


if sys.argv[1] == "source":
    require(git("rev-parse", "HEAD") == A, "Wrong original product")
    require(git("-C", "probe-control", "rev-parse", "HEAD") == os.environ["GITHUB_SHA"], "Wrong control")
    git("diff", "HEAD", "--exit-code")
    blob = decodebytes((HERE / "panel-c.patch.b64").read_bytes())
    require(sha256(blob).hexdigest() == PATCH, "Exact C patch mismatch")
    (EVID / "C-product.patch").write_bytes(blob)
    for check in [["--check"], []]:
        sp.run(["git", "apply", *check, "--index", "--whitespace=error", "-"], input=blob, check=True)
    git("diff", "--cached", "--check", A)
    require(git("diff", "--cached", "--name-only", A) == "pj_dialog_host/src/panel_engine.cpp", "Unexpected product scope")
    require(git("write-tree") == TREE, "Candidate tree mismatch")
    env = os.environ.copy()
    for prefix in ["AUTHOR", "COMMITTER"]:
        env.update({f"GIT_{prefix}_NAME": "PlotJuggler candidate CI",
                    f"GIT_{prefix}_EMAIL": "candidate-ci@example.invalid",
                    f"GIT_{prefix}_DATE": "2026-11-21T16:30:00Z"})
    result = git("-c", "commit.gpgSign=false", "commit-tree", TREE, "-p", A, "-m",
                 "Share owning parsed WidgetData in the panel engine", env=env)
    require(result == C, "Candidate commit mismatch")
    git("checkout", "--detach", C)
    identity = git("rev-parse", "HEAD", "HEAD^{tree}", "HEAD^").splitlines()
    require(identity == [C, TREE, A], "Candidate readback mismatch")
    git("diff", "HEAD", "--exit-code")
    (EVID / "C-product.commit").write_bytes(sp.check_output(["git", "cat-file", "commit", C]))
    (EVID / "identity.json").write_text(json.dumps({
        "product": C, "tree": TREE, "parent": A, "patch_sha256": PATCH,
        "controller": os.environ["GITHUB_SHA"], "run": os.environ["GITHUB_RUN_ID"],
        "required_qt": "6.12.0",
    }, indent=2))
elif sys.argv[1] == "test":
    require(git("rev-parse", "HEAD", "HEAD^{tree}").splitlines() == [C, TREE], "Product moved before CTest")
    git("diff", "HEAD", "--exit-code")
    expected = sorted((HERE / "panel-c-tests.txt").read_text().splitlines())
    require(len(expected) == len(set(expected)) == 29, "Wrong exact test roster")
    expr = r"^pj_dialog_host_panel_tests\.(PanelEngineTest|ParsedWidgetData)\."
    command = ["ctest", "--test-dir", "build", "-R", expr]
    raw = sp.check_output([*command, "--show-only=json-v1"], text=True)
    (EVID / "ctest-selection.json").write_text(raw)
    selected = sorted(t["name"] for t in json.loads(raw)["tests"])
    require(selected == expected, f"Wrong CTest selection: {selected!r}")
    junit = EVID.resolve() / "panel-c-results.xml"
    sp.run([*command, "--no-tests=error", "--output-on-failure", "--timeout", "120",
            "--output-junit", str(junit)], check=True)
    cases = ET.parse(junit).findall(".//testcase")
    require(sorted(case.get("name") for case in cases) == expected, "Actual cases differ from selected cases")
    for case in cases:
        require(case.get("status") == "run" and not any(
            case.find(name) is not None for name in ("skipped", "failure", "error")),
            f"Case did not pass: {case.get('name')}")
    print(f"{len(cases)}/29 executed and passed, no skips.")
else:
    raise SystemExit("Use source or test")
