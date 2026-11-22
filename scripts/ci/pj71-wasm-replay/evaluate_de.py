"""Distinguish a reproduced original 100ms failure from infrastructure/unrelated failures."""
import json
import re
import sys
from pathlib import Path

TITLE = "Transform Editor creates a large exact Luau series while the browser main thread stays responsive"

def parse(name):
    report = json.loads(Path(name).read_text())
    found = []
    def walk(suite):
        for spec in suite.get("specs", []):
            assert spec["title"] == TITLE and spec["file"] == "editors.spec.js"
            found.extend(spec["tests"])
        for nested in suite.get("suites", []):
            walk(nested)
    for suite in report["suites"]:
        walk(suite)
    assert len(found) == 1 and found[0]["projectName"] == "firefox"
    assert report["stats"]["skipped"] == report["stats"]["flaky"] == 0
    results = found[0]["results"]
    assert len(results) == 1
    return results[0]

d = parse(sys.argv[1])
e = parse(sys.argv[2])
assert e["status"] == "passed" and sys.argv[4] == "0", "E did not pass the exact gate"
if d["status"] == "passed":
    raise SystemExit("Inconclusive: D also passed; the baseline slowdown did not reproduce")
assert d["status"] == "failed" and sys.argv[3] != "0", "D infrastructure/test failure unrelated to 100ms gate"
errors = "\n".join(re.sub(r"\x1b\[[0-9;]*m", "", error.get("message", "")) for error in d["errors"])
match = re.search(r"Expected:\s*< 100\s+Received:\s*([0-9.]+)", errors)
assert match and float(match[1]) >= 100, "D failed for a different assertion"
print(f"D reproduced {match[1]} ms; E passed the unchanged strict gate and exact 30k/N=32-prefix output checks.")
print("This is a single paired observation, not evidence that the improvement persists or a release gate pass.")
