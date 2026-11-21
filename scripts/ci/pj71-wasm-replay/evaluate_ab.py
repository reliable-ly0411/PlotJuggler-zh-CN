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

a = parse(sys.argv[1])
d = parse(sys.argv[2])
assert d["status"] == "passed" and sys.argv[4] == "0", "D did not pass the exact gate"
if a["status"] == "passed":
    raise SystemExit("Inconclusive: A also passed; the baseline slowdown did not reproduce")
assert a["status"] == "failed" and sys.argv[3] != "0", "A infrastructure/test failure unrelated to 100ms gate"
errors = "\n".join(re.sub(r"\x1b\[[0-9;]*m", "", e.get("message", "")) for e in a["errors"])
match = re.search(r"Expected:\s*< 100\s+Received:\s*([0-9.]+)", errors)
assert match and float(match[1]) >= 100, "A failed for a different assertion"
print(f"A reproduced {match[1]} ms; D passed the unchanged strict gate and exact 30k outputs.")
print("This is a single paired observation, not evidence that the improvement persists or a release gate pass.")
