# SPDX-License-Identifier: MPL-2.0
"""Check both Qt5 catalogs, including extraction and non-text attributes."""
import argparse
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
import os
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
CATALOGS = [ROOT / f"plotjuggler_app/translations/plotjuggler_{locale}.ts"
            for locale in ("zh_CN", "zh_TW")]


class Markup(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.tags = Counter()
        self.attributes = Counter()
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.tags[tag] += 1
        for key, value in attrs:
            if key not in {"title", "alt"}:
                self.attributes[(tag, key, value)] += 1

    handle_startendtag = handle_starttag


def placeholders(text):
    return Counter(re.findall(r"%L?\d+|%L?n", text))


def mnemonics(text):
    return len(re.findall(r"&(?!&|\s|$)", text.replace("&&", "")))


def validate(root):
    errors, keys = [], set()
    for context in root.findall("context"):
        for message in context.findall("message"):
            source = message.findtext("source") or ""
            key = (context.findtext("name"), source, message.findtext("comment") or "",
                   message.get("numerus", "no"))
            if key in keys:
                errors.append(f"Duplicate: {key!r}")
            keys.add(key)
            translation = message.find("translation")
            if translation is None or translation.get("type") in {"unfinished", "vanished", "obsolete"}:
                errors.append(f"Missing/obsolete: {key!r}")
                continue
            forms = translation.findall("numerusform") if message.get("numerus") == "yes" else [translation]
            if not forms or (message.get("numerus") == "yes" and len(forms) != 1):
                errors.append(f"Chinese plural forms: {key!r}")
            for form in forms:
                text = "".join(form.itertext())
                if source and not text:
                    errors.append(f"Empty: {key!r}")
                if placeholders(source) != placeholders(text):
                    errors.append(f"Placeholders: {key!r}")
                if re.search(r"<\s*(?:html|p|span|a|b|br)\b", source):
                    original, translated = Markup(source), Markup(text)
                    if original.tags != translated.tags or original.attributes != translated.attributes:
                        errors.append(f"Rich text structure/attributes: {key!r}")
                elif mnemonics(source) != mnemonics(text):
                    errors.append(f"Mnemonic count: {key!r}")
                if re.fullmatch(r"(?:(?:Ctrl|Alt|Shift|Meta)\+)+[^\s]+", source) and source != text:
                    errors.append(f"Shortcut: {key!r}")
    return errors, keys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fresh", action="store_true")
    args = parser.parse_args()
    errors, key_sets = [], []
    for path in CATALOGS:
        current_errors, original_keys = validate(ET.parse(path).getroot())
        errors.extend(f"{path.name}: {error}" for error in current_errors)
        key_sets.append(original_keys)
        if args.fresh:
            lupdate = os.environ.get("LUPDATE") or shutil.which("lupdate") or shutil.which("lupdate-qt5")
            if not lupdate:
                raise SystemExit("Qt5 lupdate is required for extraction freshness")
            with tempfile.TemporaryDirectory(prefix="pj-translation-check-") as directory:
                snapshot = Path(directory) / path.name
                shutil.copyfile(path, snapshot)
                result = subprocess.run([lupdate, "plotjuggler_app", "plotjuggler_base",
                                         "plotjuggler_plugins", "-no-obsolete", "-ts", str(snapshot)],
                                        cwd=ROOT, text=True, capture_output=True, check=True)
                if result.stderr.strip():
                    errors.append(f"Extraction diagnostics: {result.stderr.strip()}")
                fresh_errors, fresh_keys = validate(ET.parse(snapshot).getroot())
                errors.extend(f"Fresh {path.name}: {error}" for error in fresh_errors)
                if fresh_keys != original_keys:
                    errors.append(f"Stale keys in {path.name}: added={fresh_keys - original_keys!r}, "
                                  f"removed={original_keys - fresh_keys!r}")
        print(f"{path.name}: {len(original_keys)} message keys")
    if key_sets[0] != key_sets[1]:
        errors.append("Simplified and Traditional catalog key sets differ")
    if errors:
        raise SystemExit("\n".join(errors))
    print("PASS: both catalogs complete; placeholders, mnemonics, shortcuts, plurals and markup preserved")


if __name__ == "__main__":
    main()
