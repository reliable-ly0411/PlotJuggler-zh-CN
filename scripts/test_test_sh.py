#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Exercise test.sh's CLI with mock CTest/setarch; no native tests are run."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


class TestScriptCli(unittest.TestCase):
    """Keep the checkout and the caller's sanitizer environment untouched."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pj-test-cli-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        repo = Path(__file__).resolve().parent.parent
        for name in ("test.sh", "versions.env"):
            shutil.copyfile(repo / name, self.root / name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.capture = self.root / "ctest.json"
        ctest = self.bin / "ctest"
        ctest.write_text(
            f"#!{sys.executable}\n"
            "import json, os, sys\n"
            "with open(os.environ['CLI_CAPTURE'], 'w') as output:\n"
            "    json.dump({'args': sys.argv[1:], 'env': dict(os.environ)}, output)\n"
            "sys.exit(int(os.environ.get('CLI_EXIT', '0')))\n"
        )
        ctest.chmod(0o755)
        # Never alter process personality or invoke the host's real setarch.
        setarch = self.bin / "setarch"
        setarch.write_text("#!/bin/sh\nexit 1\n")
        setarch.chmod(0o755)
        # CLI-only shim: verify virtual-display dispatch without starting X11.
        xvfb = self.bin / "xvfb-run"
        xvfb.write_text('#!/bin/sh\n[ "$1" = "-a" ] || exit 9\nshift\nexport CLI_PRIVATE_DISPLAY=1\nexec "$@"\n', encoding='utf-8')
        xvfb.chmod(0o755)
        self.env = os.environ.copy()
        for key in ("PJ_SANITIZE", "ASAN_OPTIONS", "LSAN_OPTIONS", "UBSAN_OPTIONS",
                    "TSAN_OPTIONS", "MSAN_OPTIONS", "PYTHONMALLOC"):
            self.env.pop(key, None)
        self.env.update(PATH=f"{self.bin}:{os.environ['PATH']}",
                        CLI_CAPTURE=str(self.capture))

    def run_script(self, *args, env=None):
        """Return exit/output plus the exact argv/environment seen by mock CTest."""
        self.capture.unlink(missing_ok=True)
        result = subprocess.run(
            ["bash", str(self.root / "test.sh"), *args], cwd=self.root,
            env={**self.env, **(env or {})}, text=True, capture_output=True,
            timeout=10,
        )
        call = json.loads(self.capture.read_text()) if self.capture.exists() else None
        return result, call

    def assert_lane(self, lane, *args, env=None):
        """Check lane selection and the failure-on-empty-suite guard."""
        result, call = self.run_script(*args, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        directory = self.root / "build"
        if lane != "none":
            directory /= lane
        self.assertEqual(call["args"], ["--test-dir", str(directory),
                                       "--output-on-failure", "--no-tests=error"])
        return call

    def test_supported_selectors(self):
        for lane in ("none", "asan", "tsan", "msan"):
            for args in (("--sanitize", lane), (f"--sanitize={lane}",), ()):
                with self.subTest(lane=lane, args=args):
                    self.assert_lane(lane, *args, env={"PJ_SANITIZE": lane})

    def test_default_and_conflicting_selectors(self):
        self.assert_lane("none")
        self.assert_lane("msan", "--sanitize=asan", "--sanitize", "msan",
                         env={"PJ_SANITIZE": "tsan"})
        self.assert_lane("none", "--sanitize=none", env={"PJ_SANITIZE": "invalid"})

    def test_invalid_and_empty_selectors(self):
        for value in ("", "invalid", "ASAN", "asan,tsan", "--display"):
            for args, env in ((("--sanitize", value), {}),
                              ((f"--sanitize={value}",), {}),
                              ((), {"PJ_SANITIZE": value})):
                with self.subTest(value=value, args=args, env=env):
                    result, call = self.run_script(*args, env=env)
                    self.assertEqual(result.returncode, 2)
                    self.assertIn("--sanitize/PJ_SANITIZE must be", result.stderr)
                    self.assertIsNone(call)
        result, call = self.run_script("--sanitize")
        self.assertEqual(result.returncode, 2)
        self.assertIsNone(call)

    def test_explicit_directory_wins_and_warns(self):
        result, call = self.run_script("--sanitize=msan", "--test-dir", "first",
                                       "--test-dir=custom tree")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(call["args"].count("--test-dir"), 1)
        self.assertEqual(call["args"][1], "custom tree")
        self.assertIn('runtime options follow lane "msan"', result.stderr)
        result, _ = self.run_script("--sanitize=msan", "--test-dir", "build/msan")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")

    def test_empty_or_missing_directory(self):
        for args in (("--test-dir",), ("--test-dir", ""), ("--test-dir=",),
                     ("--test-dir", "--display")):
            with self.subTest(args=args):
                result, call = self.run_script(*args)
                self.assertEqual(result.returncode, 2)
                self.assertIsNone(call)

    def test_passthrough_preserves_arguments_and_exit_status(self):
        forwarded = ["-R", "^(one|two)\\.case with spaces$", "--timeout", "42", "-V", ""]
        result, call = self.run_script("--sanitize=msan", *forwarded,
                                       env={"CLI_EXIT": "7"})
        self.assertEqual(result.returncode, 7)
        self.assertEqual(call["args"][4:], forwarded)

    def test_display_and_runtime_overrides(self):
        for lane in ("none", "asan", "tsan", "msan"):
            with self.subTest(lane=lane):
                call = self.assert_lane(lane, f"--sanitize={lane}", env={
                    "ASAN_OPTIONS": "", "MSAN_OPTIONS": "halt_on_error=1 exitcode=77",
                    "QT_QPA_PLATFORM": "xcb",
                })
                self.assertEqual(call["env"]["QT_QPA_PLATFORM"], "offscreen")
                self.assertEqual(call["env"]["ASAN_OPTIONS"], "")
                self.assertEqual(call["env"]["MSAN_OPTIONS"], "halt_on_error=1 exitcode=77")
        result, call = self.run_script("--display", env={"QT_QPA_PLATFORM": "xcb", "WAYLAND_DISPLAY": "user-desktop"})
        self.assertEqual(result.returncode, 0)
        if sys.platform == "darwin":
            self.assertEqual(call["env"]["QT_QPA_PLATFORM"], "cocoa")
        else:
            self.assertEqual(call["env"]["QT_QPA_PLATFORM"], "xcb")
            self.assertEqual(call["env"]["CLI_PRIVATE_DISPLAY"], "1")
            self.assertNotIn("WAYLAND_DISPLAY", call["env"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
