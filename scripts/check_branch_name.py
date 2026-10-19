# SPDX-License-Identifier: MPL-2.0
"""Check localization branch names. Upstream mirrors retain their exact names."""
import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
TOPIC = r"[a-z0-9]+(?:-[a-z0-9]+)*"
PATTERNS = (
    r"zh-CN(?:-dev)?",
    rf"zh-CN-(?:feat|ci|docs)/{TOPIC}",
    rf"zh-CN-fix/[1-9][0-9]*-{TOPIC}",
    r"zh-CN-release/v[0-9]+\.[0-9]+\.[0-9]+(?:-zh\.[1-9][0-9]*)?",
)


def valid(name):
    mirrors = json.loads((ROOT / "docs/upstream-mirrors.json").read_text())
    return name in mirrors or any(re.fullmatch(pattern, name) for pattern in PATTERNS)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("branch")
    args = parser.parse_args()
    if not valid(args.branch):
        parser.error("Use zh-CN, zh-CN-dev, zh-CN-{feat,ci,docs}/<topic>, "
                     "zh-CN-fix/<issue>-<topic>, or zh-CN-release/<version>; "
                     "see docs/BRANCHING.zh-CN.md")
    print(f"Accepted branch: {args.branch}")
