# SPDX-License-Identifier: MPL-2.0
"""Reject missing translations and changed Qt argument placeholders."""
from pathlib import Path
import collections
import re
import xml.etree.ElementTree as ET

path = Path(__file__).resolve().parents[1] / "plotjuggler_app/translations/plotjuggler_zh_CN.ts"
root = ET.parse(path).getroot()
errors = []
count = 0
for context in root.findall("context"):
    for message in context.findall("message"):
        source = message.findtext("source") or ""
        translated = message.find("translation")
        text = "" if translated is None else "".join(translated.itertext())
        count += 1
        if translated is None or translated.get("type") in {"unfinished", "vanished", "obsolete"} or (source and not text):
            errors.append(f"Missing: {context.findtext('name')}: {source!r}")
        placeholder = lambda value: collections.Counter(re.findall(r"%L?\d+|%n", value))
        if placeholder(source) != placeholder(text):
            errors.append(f"Placeholders: {source!r}")
if errors:
    raise SystemExit("\n".join(errors))
print(f"PASS: {count} complete translations; Qt placeholders preserved")
