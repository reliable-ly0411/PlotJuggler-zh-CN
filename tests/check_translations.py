# SPDX-License-Identifier: MPL-2.0
"""Reject missing translations and changed Qt argument placeholders."""
from pathlib import Path
import collections
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

path = Path(__file__).resolve().parents[1] / "plotjuggler_app/translations/plotjuggler_zh_CN.ts"
root = ET.parse(path).getroot()
if "--fresh" in sys.argv:
    lupdate = os.environ.get("LUPDATE") or shutil.which("lupdate") or shutil.which("lupdate-qt5")
    if not lupdate:
        raise SystemExit("Qt lupdate is required to verify extraction freshness")
    with tempfile.TemporaryDirectory(prefix="pj-translation-check-") as temporary:
        snapshot = Path(temporary) / path.name
        shutil.copyfile(path, snapshot)
        subprocess.run([lupdate, "plotjuggler_app", "plotjuggler_base", "plotjuggler_plugins",
                        "-no-obsolete", "-ts", str(snapshot)], cwd=path.parents[2], check=True)
        root = ET.parse(snapshot).getroot()
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
