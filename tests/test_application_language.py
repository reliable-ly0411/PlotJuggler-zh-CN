# SPDX-License-Identifier: MPL-2.0
"""Test persistence across processes and launcher argument/exit behavior."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

PROBE, LAUNCHER = map(lambda value: Path(value).resolve(), sys.argv[1:3])
sys.argv = sys.argv[:1]


class ApplicationLanguage(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="pj3-language-")
        self.root = Path(self.temporary.name)
        self.config = self.root / "設定 空格"

    def tearDown(self):
        self.temporary.cleanup()

    def probe(self, *arguments):
        return json.loads(subprocess.check_output(
            [str(PROBE), "--config-dir", str(self.config), *arguments], text=True, encoding="utf-8"))

    def test_languages_and_qt_dialogs(self):
        for language, menu, close in (("en_US", "App", "Close"), ("zh_CN", "应用", "关闭"),
                                      ("zh_TW", "應用", "關閉")):
            with self.subTest(language=language):
                result = self.probe("--language", language)
                self.assertEqual((result["language"], result["menu"], result["close"]),
                                 (language, menu, close))
                self.assertTrue(result["numeric_locale_preserved"])
                self.assertEqual(result["fallback"], "Untranslated sample")
                if language != "en_US":
                    self.assertNotEqual(result["qt_file_name"], "File &name:")

    def test_default_and_restart_persistence(self):
        self.assertEqual(self.probe()["language"], "zh_CN")
        for language in ("en_US", "zh_CN", "zh_TW"):
            subprocess.check_call([str(PROBE), "--config-dir", str(self.config),
                                   "--set-language", language])
            self.assertEqual(self.probe()["language"], language)
            self.assertEqual(self.probe("--language=en_US")["language"], "en_US")
            self.assertEqual(self.probe()["language"], language)

    def test_alias_and_unknown_fallback(self):
        self.assertEqual(self.probe("--language=zh-TW")["language"], "zh_TW")
        self.assertEqual(self.probe("--language=zh-Hant")["language"], "zh_TW")
        self.assertEqual(self.probe("--language=unknown")["language"], "en_US")

    def test_settings_identity_and_directory(self):
        result = self.probe()
        self.assertTrue(Path(result["settings_file"]).is_relative_to(self.config))
        self.assertIn("io.plotjuggler.PlotJuggler.zh-CN", result["settings_file"])

    def test_invalid_configuration_directory_fails_closed(self):
        for arguments in (["--config-dir"], ["--config-dir="]):
            result = subprocess.run([str(PROBE), *arguments], capture_output=True)
            self.assertEqual(result.returncode, 2)

    def stage(self, child=True):
        directory = self.root / "便攜 Portable 應用"
        directory.mkdir()
        launcher = directory / LAUNCHER.name
        shutil.copy2(LAUNCHER, launcher)
        if child:
            shutil.copy2(PROBE, directory / ("plotjuggler.exe" if os.name == "nt" else "plotjuggler"))
        return launcher

    def test_launcher_unicode_spaces_arguments_and_directory(self):
        launcher = self.stage()
        output = self.root / "報告 空格.json"
        arguments = ["--config-dir", str(self.config), "--language", "zh_TW", "--probe-output",
                     str(output), "-d", "相對資料 sample.csv", "--layout=版面 layout.xml",
                     "--", "--launch", "--help-launcher"]
        subprocess.check_call([str(launcher), "--launch", *arguments], cwd=self.root)
        result = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(result["arguments"], arguments)
        self.assertEqual(Path(result["directory"]), self.root)
        self.assertEqual(result["language"], "zh_TW")
        self.assertFalse(self.config.exists(), "session override must not save preferences")

    def test_launcher_child_exit_status(self):
        launcher = self.stage()
        result = subprocess.run([str(launcher), "--launch", "--config-dir", str(self.config),
                                 "--exit-code", "23"], capture_output=True)
        self.assertEqual(result.returncode, 23)

    def test_launcher_missing_sibling_does_not_search_path(self):
        launcher = self.stage(child=False)
        result = subprocess.run([str(launcher), "--launch", "--config-dir", str(self.config)],
                                capture_output=True)
        self.assertEqual(result.returncode, 127)
        self.assertTrue(result.stderr)


if __name__ == "__main__":
    unittest.main()
