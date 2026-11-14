# SPDX-License-Identifier: MPL-2.0
"""Offline acceptance-orchestration regressions; no Qt or real processes needed."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import subprocess
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location(
    "zh_acceptance", Path(__file__).resolve().parents[1] / "scripts/zh_acceptance.py")
acceptance = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(acceptance)


class AcceptanceStages(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pj-acceptance-unit-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.version = "3.18.1-rc.5+upstream.3.17.2.apbin.1.g123456789abc"
        self.write(self.root / "build/FORK-VERSION.json", {"version": self.version})
        self.write(self.root / "plotjuggler_app/resources/memes/zh_CN.json",
                   {"images": [{"variant": "one"}, {"variant": "two"}, {}]})
        for name in ("plotjuggler.exe", "plugin.dll",
                     "plotjuggler_plugins/DataLoadAPBin/tests/curves.BIN"):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"offline fixture")
        self.args = SimpleNamespace(app=str(self.root / "plotjuggler.exe"),
                                    plugin=str(self.root / "plugin.dll"),
                                    out=str(self.root / "out"), window_size="1100x700",
                                    original_images=False, version_file=None, ui_only=False)
        self.calls = []
        self.fault = None
        self.skip_settings = False
        self.mutate = None

    @staticmethod
    def write(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")

    def runner(self, command, **kwargs):
        self.assertEqual(kwargs["timeout"], 60)
        if "--export-memes" in command:
            out = Path(command[command.index("--export-memes") + 1])
            language, stage, path = out.parent.name, "memes", out / "memes.json"
            report = [{"text_fits": True, "saved": True, "english_original": True,
                       "rendering": "english-original"} for _ in range(107)]
            if language == "zh_CN" and not self.args.original_images:
                for item in report[:2]:
                    item["rendering"] = "localized-overlay"
        else:
            out = Path(command[command.index("--self-test-ui") + 1])
            stage = "restart" if out.name == "restarted" else "ui"
            language = out.parent.name if stage == "restart" else out.name
            path = out / "ui.json"
            report = {"version": self.version, "language": language,
                      "language_ok": True, "menu_ok": True, "screenshot_ok": True,
                      "data_ok": True, "numeric_series": 4, "platform": "fixture",
                      "regression": {"ok": True}, "localization": {"ok": True}}
            if stage == "ui" and not (language == "zh_CN" and self.skip_settings):
                ini = acceptance.settings_file(out)
                ini.parent.mkdir(parents=True, exist_ok=True)
                ini.write_text("[General]\nPreferences%3A%3Alanguage=" + language + "\n",
                               encoding="utf-8")
        if stage in ("ui", "memes"):
            self.assertIn("--language", command)
            self.assertEqual(command[command.index("--language") + 1], language)
        if stage in ("restart", "memes"):
            self.assertIn("--config-dir", command)
            self.assertEqual(Path(command[command.index("--config-dir") + 1]),
                             Path(self.args.out).resolve() / language / "settings")
        self.calls.append((language, stage))
        if self.mutate and (language, stage) == self.mutate[:2]:
            self.mutate[2](report)
        fault = self.fault[2] if self.fault and (language, stage) == self.fault[:2] else None
        if fault == "bad-json":
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("CANARY-invalid-json", encoding="utf-8")
        elif fault != "missing-json":
            self.write(path, report)
        if fault == "timeout":
            raise subprocess.TimeoutExpired(command, 60, output=b"CANARY-process-output")
        return subprocess.CompletedProcess(command, 20 if fault == "nonzero" else 0,
                                           stdout=b"CANARY-process-output")

    def run_checks(self):
        code = acceptance.run_acceptance(self.args, root=self.root, runner=self.runner)
        output = Path(self.args.out)
        summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
        stages = json.loads((output / "stage-results.json").read_text(encoding="utf-8"))
        self.assertIsInstance(summary, list)
        self.assertEqual(len(summary), 3)
        self.assertEqual(len(stages["stages"]), 9)
        self.assertNotIn("CANARY", json.dumps(summary) + json.dumps(stages))
        return code, summary, stages

    def test_all_nine_stages_preserve_success_summary(self):
        code, summary, result = self.run_checks()
        self.assertEqual(code, 0)
        self.assertEqual(len(self.calls), 9)
        self.assertEqual(result["counts"], {"passed": 9, "failed": 0, "not-executed": 0, "not-selected": 0})
        for row in summary:
            self.assertEqual(row["version"], self.version)
            self.assertEqual(row["meme_images"], 107)
            self.assertEqual(row["platform"], "fixture")
            self.assertNotIn("acceptance_status", row)

    def test_external_version_file_and_failure_modes(self):
        external = self.root / "independent-build/FORK-VERSION.json"
        self.write(external, {"version": self.version})
        self.args.version_file = str(external)
        (self.root / "build/FORK-VERSION.json").unlink()
        code, _, result = self.run_checks()
        self.assertEqual(code, 0)
        self.assertEqual(result["counts"]["passed"], 9)
        for mode in ("missing", "invalid", "mismatch"):
            with self.subTest(mode=mode):
                self.args.out = str(self.root / ("version-" + mode))
                if mode == "missing":
                    external.unlink()
                elif mode == "invalid":
                    external.write_text("not json", encoding="utf-8")
                else:
                    self.write(external, {"version": "different"})
                code, _, result = self.run_checks()
                self.assertEqual(code, 1)
                if mode in ("missing", "invalid"):
                    self.assertIn("expected-version-unavailable", result["preflight"]["reasons"])
                for stage in result["stages"]:
                    if stage["stage"] in ("ui", "restart"):
                        self.assertIn("version-gate-failed", stage["reasons"])

    def test_version_file_cli_option(self):
        args = acceptance.parse_args(["--app", "app", "--plugin", "plugin", "--out", "out",
                                      "--version-file", "external/FORK-VERSION.json"])
        self.assertEqual(args.version_file, "external/FORK-VERSION.json")

    def test_ui_only_skips_image_export_and_catalog(self):
        self.args.ui_only = True
        (self.root / "plotjuggler_app/resources/memes/zh_CN.json").unlink()
        code, summary, result = self.run_checks()
        self.assertEqual(code, 0)
        self.assertEqual(result["scope"], "ui-only")
        self.assertEqual(result["selected_stage_count"], 6)
        self.assertEqual(result["counts"], {"passed": 6, "failed": 0, "not-executed": 0,
                                           "not-selected": 3})
        self.assertEqual(len(self.calls), 6)
        self.assertTrue(all(stage != "memes" for _, stage in self.calls))
        self.assertTrue(all("meme_images" not in row for row in summary))

    def test_ui_only_does_not_hide_selected_failure(self):
        self.args.ui_only = True
        self.fault = ("zh_CN", "ui", "nonzero")
        code, summary, result = self.run_checks()
        self.assertEqual(code, 1)
        self.assertEqual(result["counts"]["failed"], 1)
        self.assertEqual(result["counts"]["not-selected"], 3)
        self.assertEqual(summary[0]["failed_stages"], ["ui"])
        self.assertEqual(len(self.calls), 6)

    def test_first_language_failure_keeps_others_and_exports(self):
        self.fault = ("zh_CN", "ui", "nonzero")
        code, summary, result = self.run_checks()
        self.assertEqual(code, 1)
        self.assertEqual(len(self.calls), 9)
        self.assertEqual(summary[0]["failed_stages"], ["ui"])
        for language in acceptance.LANGUAGES:
            self.assertIn((language, "memes"), self.calls)
        self.assertIn(("en_US", "restart"), self.calls)
        self.assertEqual(result["counts"]["failed"], 1)

    def test_missing_bad_json_and_timeout_keep_complete_reports(self):
        for fault, reason in (("missing-json", "report-missing"),
                              ("bad-json", "report-invalid-or-unreadable"),
                              ("timeout", "process-timeout")):
            with self.subTest(fault=fault):
                self.args.out = str(self.root / fault)
                # A stale valid file must not hide a missing report from this process.
                self.write(Path(self.args.out) / "zh_CN/ui.json", {"stale": True})
                self.calls = []
                self.fault = ("zh_CN", "ui", fault)
                code, _, result = self.run_checks()
                self.assertEqual(code, 1)
                self.assertEqual(len(self.calls), 9)
                self.assertIn(reason, result["stages"][0]["reasons"])

    def test_missing_or_stale_config_does_not_claim_restart(self):
        self.skip_settings = True
        for mode in ("missing", "stale"):
            with self.subTest(mode=mode):
                self.args.out = str(self.root / mode)
                self.calls = []
                if mode == "stale":
                    ini = acceptance.settings_file(Path(self.args.out) / "zh_CN")
                    ini.parent.mkdir(parents=True, exist_ok=True)
                    ini.write_text("[General]\nPreferences%3A%3Alanguage=zh_CN\n", encoding="utf-8")
                code, _, result = self.run_checks()
                self.assertEqual(code, 1)
                restart = result["stages"][1]
                self.assertEqual(restart["status"], "not-executed")
                self.assertNotIn(("zh_CN", "restart"), self.calls)
                self.assertIn(("en_US", "restart"), self.calls)
                self.assertEqual(len(self.calls), 8)

    def test_ui_and_image_gates_remain_mandatory(self):
        mutations = [("ui", lambda r: r.update(version="wrong")),
                     ("ui", lambda r: r.update(menu_ok=False)),
                     ("ui", lambda r: r.update(numeric_series=3)),
                     ("ui", lambda r: r["regression"].update(ok=False)),
                     ("ui", lambda r: r["localization"].update(ok=False)),
                     ("memes", lambda r: r.pop()),
                     ("memes", lambda r: r[0].update(text_fits=False)),
                     ("memes", lambda r: r[0].update(saved=False)),
                     ("memes", lambda r: r[0].update(english_original=False)),
                     ("memes", lambda r: r[0].update(rendering="english-original"))]
        for index, (stage, mutate) in enumerate(mutations):
            with self.subTest(gate=index):
                self.args.out = str(self.root / ("gate-" + str(index)))
                self.calls = []
                self.mutate = ("zh_CN", stage, mutate)
                code, _, result = self.run_checks()
                self.assertEqual(code, 1)
                self.assertEqual(len(self.calls), 9)
                self.assertEqual(result["counts"]["failed"], 1)

    def test_disabled_images_still_checks_all_107(self):
        self.args.original_images = True
        code, summary, _ = self.run_checks()
        self.assertEqual(code, 0)
        self.assertTrue(all(row["meme_images"] == 107 for row in summary))


if __name__ == "__main__":
    unittest.main()
