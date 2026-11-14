# SPDX-License-Identifier: MPL-2.0
"""Reject plain untranslated Qt dialog titles and custom button captions.

This is a deliberately small lexical guard for the missing-curve Warning
regression. It does not prove that every message body or dynamic label is
translated. Data, identifiers and third-party diagnostics are outside its scope.
Pure canonical product/protocol names may retain their spelling as titles.
"""
import argparse
import ast
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
BRAND_ONLY_TITLES = {"Arrow/Parquet", "Foxglove Bridge", "PlotJuggler"}
TOKENS = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*.*?\*/', re.S)
CALLS = re.compile(
    r"\b(?:(QMessageBox\s*::\s*(?:warning|critical|information|question))|"
    r"(QMessageBox(?:\s+[A-Za-z_]\w*)?)|(setWindowTitle)|(addButton))\s*\(")
RAW_TEXT = re.compile(
    r'^(?:(?:u8|u|U|L)?(?=")|(?:QStringLiteral|QString|QString::fromLatin1|'
    r'QString::fromUtf8)\s*\(\s*)("(?:\\.|[^"\\])*")')


def without_comments(source):
    def replace(match):
        token = match.group()
        if token.startswith(('"', "'")):
            return token
        return "".join("\n" if char == "\n" else " " for char in token)
    return TOKENS.sub(replace, source)


def arguments(source, start):
    """Read top-level arguments, respecting strings and nested Qt expressions."""
    values, begin, depth, quote, escaped = [], start, 0, None, False
    for at in range(start, len(source)):
        char = source[at]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char in ('"', "'"):
            quote = char
        elif char in "([{":
            depth += 1
        elif char in ")]}":
            if char == ")" and depth == 0:
                values.append(source[begin:at].strip())
                return values
            depth -= 1
        elif char == "," and depth == 0:
            values.append(source[begin:at].strip())
            begin = at + 1
    return []


def find_raw_ui(source, filename="<fixture>"):
    source = without_comments(source)
    literals = [(token.start(), token.end()) for token in TOKENS.finditer(source)
                if token.group().startswith(('"', "'"))]
    found = []
    for match in CALLS.finditer(source):
        if any(start <= match.start() < end for start, end in literals):
            continue
        args = arguments(source, match.end())
        if match[1] or match[2]:
            if len(args) < 3:
                continue
            expression, kind = args[1], "message-box title"
        else:
            if not args:
                continue
            expression = args[0]
            kind = "window title" if match[3] else "custom button caption"
        raw = RAW_TEXT.match(expression)
        if not raw:
            continue
        try:
            text = ast.literal_eval(raw[1])
        except (SyntaxError, ValueError):
            text = raw[1]
        if not any(char.isalpha() for char in text):
            continue
        if kind != "custom button caption" and text in BRAND_ONLY_TITLES:
            continue
        found.append({"file": filename, "line": source.count("\n", 0, match.start()) + 1,
                      "kind": kind, "source": text})
    return found


class RawUiGuardTests(unittest.TestCase):
    def test_missing_curve_warning_title(self):
        source = 'QMessageBox::warning(qwtPlot(), "Warning", tr("Missing curve"));'
        self.assertEqual([x["source"] for x in find_raw_ui(source)], ["Warning"])

    def test_multiline_window_title(self):
        source = 'setWindowTitle(\n QString("Statistics | %1").arg(name));'
        self.assertEqual(find_raw_ui(source)[0]["kind"], "window title")
        self.assertEqual(find_raw_ui(source)[0]["line"], 1)

    def test_custom_continue_button(self):
        source = 'box.addButton("Continue", QMessageBox::AcceptRole);'
        self.assertEqual(find_raw_ui(source)[0]["source"], "Continue")

    def test_message_box_constructor(self):
        source = 'QMessageBox box(QMessageBox::Warning, "Warning", body, buttons, this);'
        self.assertEqual(find_raw_ui(source)[0]["source"], "Warning")

    def test_translations_and_dynamic_data(self):
        source = '''
QMessageBox::warning(this, tr("Warning"), error.what());
setWindowTitle(QObject::tr("Statistics | %1").arg(name));
box.addButton(QCoreApplication::translate("Dialog", "Continue"), role);
setWindowTitle(plugin->name());
settings.setValue("title", "Warning");
'''
        self.assertEqual(find_raw_ui(source), [])

    def test_canonical_brands_and_symbols(self):
        source = '''
QMessageBox::warning(this, "Arrow/Parquet", tr("Unable to load"));
box.addButton("+", role);
setWindowTitle("");
'''
        self.assertEqual(find_raw_ui(source), [])
        source = 'QMessageBox::warning(this, QString::fromLatin1("QtAV error"), tr("Error"));'
        self.assertEqual(find_raw_ui(source)[0]["source"], "QtAV error")

    def test_example_in_string_is_not_a_call(self):
        source = r'const char* example = "QMessageBox::warning(this, \"Warning\", body);";'
        self.assertEqual(find_raw_ui(source), [])

    def test_comments_are_not_ui(self):
        source = '''
// QMessageBox::warning(this, "Warning", body);
/* box.addButton("Continue", role); */
setWindowTitle(tr("https://example.invalid/title"));
'''
        self.assertEqual(find_raw_ui(source), [])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(RawUiGuardTests)
        raise SystemExit(0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1)
    errors = []
    for name in ("plotjuggler_app", "plotjuggler_base", "plotjuggler_plugins"):
        for path in sorted((ROOT / name).rglob("*")):
            if path.suffix not in {".cpp", ".h"} or "tests" in path.relative_to(ROOT).parts:
                continue
            errors.extend(find_raw_ui(path.read_text(encoding="utf-8"), path.relative_to(ROOT).as_posix()))
    if errors:
        raise SystemExit("\n".join(f'{x["file"]}:{x["line"]}: untranslated {x["kind"]}: {x["source"]}'
                                   for x in errors))
    print("PASS: no plain untranslated dialog titles or custom button captions")


if __name__ == "__main__":
    main()
