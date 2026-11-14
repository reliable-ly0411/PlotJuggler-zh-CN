# SPDX-License-Identifier: MPL-2.0
"""Exercise the real source hook with temporary files, without running Conan/builds."""
import ast
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
RECIPE = ROOT / "cmake/conan/openssl-overlay/conanfile.py"
ORIGINAL = "my $cflags = join(' ', @ARGV);"


def source_hook():
    module = ast.parse(RECIPE.read_text(encoding="utf-8"))
    recipe = next(node for node in module.body if isinstance(node, ast.ClassDef)
                  and node.name == "OpenSSLConan")
    method = next(node for node in recipe.body if isinstance(node, ast.FunctionDef)
                  and node.name == "build")

    def replace_in_file(_, filename, old, new, strict=False):
        path = Path(filename)
        text = path.read_text(encoding="utf-8")
        if strict and old not in text:
            raise RuntimeError("missing source pattern")
        path.write_text(text.replace(old, new), encoding="utf-8")

    scope = {"os": os, "replace_in_file": replace_in_file,
             "ConanInvalidConfiguration": RuntimeError}
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(RECIPE), "exec"), scope)
    return scope["build"]


class OpenSSLOverlay(unittest.TestCase):
    def test_windows_link_flags_are_additive_not_environment_override(self):
        module = ast.parse(RECIPE.read_text(encoding="utf-8"))
        recipe = next(n for n in module.body if isinstance(n, ast.ClassDef) and n.name == "OpenSSLConan")
        method = next(n for n in recipe.body if isinstance(n, ast.FunctionDef) and n.name == "generate")
        for platform, compiler, expect_unset in (("Windows", "msvc", True), ("Linux", "gcc", False), ("Windows", "gcc", False)):
            with self.subTest(platform=platform, compiler=compiler):
                events = []
                env = SimpleNamespace(unset=lambda key: events.append(("unset", key)), define_path=lambda *args: None)
                tc = SimpleNamespace(environment=lambda: env, cflags=[], cxxflags=[], defines=[], ldflags=["/Brepro"], generate=lambda arg: events.append(("generate", arg)))
                obj = SimpleNamespace(settings=SimpleNamespace(os=platform, compiler=compiler), _perl="perl",
                    _create_targets=lambda *args: events.append(("target", args[-1])))
                scope = {"AutotoolsToolchain": lambda _: tc, "is_apple_os": lambda _: False}
                exec(compile(ast.Module(body=[method], type_ignores=[]), str(RECIPE), "exec"), scope)
                scope["generate"](obj)
                self.assertEqual(("unset", "LDFLAGS") in events, expect_unset)
                self.assertIn(("target", ["/Brepro"]), events)
                self.assertEqual(events[-1], ("generate", env))
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="pj-openssl-hook-")
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        (root / "util").mkdir()
        self.input = root / "util/mkbuildinf.pl"
        self.events = []
        self.recipe = SimpleNamespace(
            source_folder=str(root), settings=SimpleNamespace(os="Windows"),
            _make=lambda: self.events.append("compile"), _adjust_path=lambda path: path,
            _perl="fixture-perl", run=lambda command: self.events.append(command))

    def test_windows_changes_only_buildinfo_before_compilation(self):
        self.input.write_text("prefix\n" + ORIGINAL + "\nsuffix\n", encoding="utf-8")
        source_hook()(self.recipe)
        self.assertEqual(self.input.read_text(encoding="utf-8"),
                         "prefix\nmy $cflags = 'information not available';\nsuffix\n")
        self.assertEqual(self.events[0], "compile")
        self.assertEqual(len(self.events), 2)
        self.assertTrue(self.events[1].endswith("configdata.pm --dump"))

    def test_missing_or_duplicate_pattern_stops_before_compilation(self):
        for text in ("different upstream source", ORIGINAL + "\n" + ORIGINAL):
            self.input.write_text(text, encoding="utf-8")
            with self.subTest(text=text), self.assertRaises(RuntimeError):
                source_hook()(self.recipe)
            self.assertEqual(self.events, [])
            self.assertEqual(self.input.read_text(encoding="utf-8"), text)

    def test_non_windows_source_is_unchanged(self):
        self.recipe.settings.os = "Linux"
        self.input.write_text(ORIGINAL, encoding="utf-8")
        source_hook()(self.recipe)
        self.assertEqual(self.input.read_text(encoding="utf-8"), ORIGINAL)
        self.assertEqual(self.events[0], "compile")


if __name__ == "__main__":
    unittest.main()
