# SPDX-License-Identifier: MPL-2.0
"""Isolated audit-control-flow tests; RCC is mocked, never a real Qt result."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/package_size_audit.py"


class PackageAuditInventory(unittest.TestCase):
    def audit(self, payload, version="rcc 5.15.13\n"):
        """Run the production script and privacy scanner, faking only RCC I/O."""
        with tempfile.TemporaryDirectory(prefix="pj-package-audit-fixture-") as directory:
            root = Path(directory)
            stage = root / "payload"
            stage.mkdir()
            contents = {"BUILD-INFO.json": json.dumps({
                "commit": "1" * 40, "version": "fixture-only-not-a-candidate",
                "repository": "https://github.com/reliable-ly0411/PlotJuggler-zh-CN"
            }).encode(), **payload}
            for name, data in contents.items():
                path = stage / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            out = root / "audit.json"
            output = io.StringIO()
            rcc = "/fixture-only/rcc"
            environment = dict(os.environ)
            environment.pop("QT_ROOT_DIR", None)
            environment["GITHUB_ACTIONS"] = "true"

            def resource_audit(command, **kwargs):
                self.assertEqual(Path(command[1]).name, "resource_size_audit.py")
                self.assertIn("--current-only", command)
                self.assertEqual(command[command.index("--rcc") + 1], rcc)
                self.assertTrue(kwargs["check"])
                report = Path(command[command.index("--out") + 1])
                report.write_text(json.dumps({"fixture_only": True, "versions": []}))
                return subprocess.CompletedProcess(command, 0)

            argv = [str(SCRIPT), "--payload", str(stage), "--out", str(out)]
            with (mock.patch.object(sys, "argv", argv),
                  mock.patch.object(sys, "path", [str(ROOT / "scripts"), *sys.path]),
                  mock.patch.dict(os.environ, environment, clear=True),
                  mock.patch("shutil.which", return_value=rcc),
                  mock.patch("subprocess.check_output", return_value=version) as rcc_version,
                  mock.patch("subprocess.run", side_effect=resource_audit) as rcc_audit,
                  contextlib.redirect_stdout(output), contextlib.redirect_stderr(output)):
                try:
                    runpy.run_path(str(SCRIPT), run_name="__main__")
                except SystemExit as error:
                    code = error.code if isinstance(error.code, int) else 1
                    diagnostic = str(error.code)
                else:
                    code, diagnostic = 0, ""
            rcc_version.assert_called_once_with([rcc, "--version"], stderr=subprocess.STDOUT,
                                                text=True)
            rcc_audit.assert_called_once()
            return code, json.loads(out.read_text()), output.getvalue() + diagnostic, contents

    def assert_full_inventory(self, report, contents):
        inventory = {item["path"]: item for item in report["files"]}
        self.assertEqual(set(inventory), set(contents))
        self.assertEqual(report["file_count"], len(contents))
        self.assertEqual(report["payload_bytes"], sum(map(len, contents.values())))
        for name, data in contents.items():
            self.assertEqual(inventory[name]["bytes"], len(data))
            self.assertEqual(inventory[name]["sha256"], hashlib.sha256(data).hexdigest())

    def test_early_test_payload_cannot_hide_later_privacy_violations(self):
        token = "gh" + "p_" + "s" * 36
        private = "C:\\Users\\SyntheticPrivate\\unpublished.bin"
        payload = {
            "000_test.bin": token.encode(),
            "lib/python3.10/lib-dynload/_ctypes_test.cpython-310-x86_64-linux-gnu.so": b"test fixture",
            "test_helper.exe": b"another test fixture",
            "y_secret.dll": token.encode(),
            "z_private.dll": private.encode(),
            "zz_clean.bin": b"last clean file must also be inventoried",
        }
        code, report, diagnostic, contents = self.audit(payload)
        self.assertNotEqual(code, 0)
        self.assert_full_inventory(report, contents)
        self.assertIs(report["test_executables_absent"], False)
        self.assertEqual({x["path"] for x in report["unexpected_test_payloads"]}, {
            "000_test.bin", "lib/python3.10/lib-dynload/_ctypes_test.cpython-310-x86_64-linux-gnu.so",
            "test_helper.exe"})
        errors = {x["path"]: x["rule"] for x in report["privacy_errors"]}
        self.assertEqual(set(errors), {"000_test.bin", "y_secret.dll", "z_private.dll"})
        self.assertIn("credential", errors["y_secret.dll"])
        self.assertIn("private path", errors["z_private.dll"])
        self.assertEqual(report["privacy_scan"], "failed")
        recorded = diagnostic + json.dumps(report)
        self.assertTrue(token not in recorded, "Credential value leaked into audit diagnostics")
        self.assertTrue(private not in recorded, "Private path value leaked into audit diagnostics")
        self.assertTrue(json.dumps(private)[1:-1] not in recorded,
                        "JSON-escaped private path leaked into audit diagnostics")

    def test_test_payload_alone_still_fails_after_inventory(self):
        code, report, _, contents = self.audit({"pj_language_probe.exe": b"fixture", "z.bin": b"clean"})
        self.assertNotEqual(code, 0)
        self.assert_full_inventory(report, contents)
        self.assertEqual(report["privacy_scan"], "passed")
        self.assertEqual(report["privacy_errors"], [])
        self.assertIs(report["test_executables_absent"], False)
        self.assertEqual([x["path"] for x in report["unexpected_test_payloads"]], ["pj_language_probe.exe"])

    def test_privacy_violation_alone_still_fails(self):
        code, report, _, contents = self.audit({"z.bin": ("gh" + "s_" + "f" * 36).encode()})
        self.assertNotEqual(code, 0)
        self.assert_full_inventory(report, contents)
        self.assertIs(report["test_executables_absent"], True)
        self.assertEqual(report["unexpected_test_payloads"], [])
        self.assertEqual(report["privacy_scan"], "failed")

    def test_clean_payload_still_passes(self):
        code, report, _, contents = self.audit({"plotjuggler": b"application fixture", "Licenses/MPL.txt": b"license fixture"})
        self.assertEqual(code, 0)
        self.assert_full_inventory(report, contents)
        self.assertIs(report["test_executables_absent"], True)
        self.assertEqual(report["unexpected_test_payloads"], [])
        self.assertEqual(report["privacy_errors"], [])
        self.assertEqual(report["privacy_scan"], "passed")
        self.assertTrue(report["qt5_rcc"]["fixture_only"])

    def test_non_qt5_rcc_remains_rejected(self):
        with self.assertRaisesRegex(AssertionError, "production Qt5 RCC"):
            self.audit({"plotjuggler": b"application fixture"}, version="rcc 6.8.0\n")


if __name__ == "__main__":
    unittest.main()
