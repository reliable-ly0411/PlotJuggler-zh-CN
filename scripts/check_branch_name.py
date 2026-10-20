# SPDX-License-Identifier: MPL-2.0
"""Validate localization branch names while preserving exact upstream mirrors."""
import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
TOPIC = r"[a-z0-9]+(?:-[a-z0-9]+)*"
# The optional generation suffix is deliberately explicit. Do not accept an
# arbitrary major that has no independently managed stable/development pair.
LINE = r"zh-CN(?:-4\.x)?"
PATTERNS = (
    rf"{LINE}(?:-dev)?",
    rf"{LINE}-(?:feat|ci|docs)/{TOPIC}",
    rf"{LINE}-fix/[1-9][0-9]*-{TOPIC}",
    rf"{LINE}-release/v[0-9]+\.[0-9]+\.[0-9]+(?:-zh\.[1-9][0-9]*)?",
)


def valid(name):
    mirrors = json.loads((ROOT / "docs/upstream-mirrors.json").read_text(encoding="utf-8"))
    return name in mirrors or any(re.fullmatch(pattern, name) for pattern in PATTERNS)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("branch")
    args = parser.parse_args()
    if not valid(args.branch):
        parser.error("Use a documented zh-CN or zh-CN-4.x stable/development/topic branch; "
                     "see docs/BRANCHING.zh-CN.md")
    print(f"Accepted branch: {args.branch}")
