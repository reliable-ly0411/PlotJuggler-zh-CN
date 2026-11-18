# SPDX-License-Identifier: MPL-2.0
"""Pin consent defaults and exclusions in the localized shell."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class LocalizedTelemetryPolicyTests(unittest.TestCase):
    def test_both_startup_and_dialog_defaults_require_opt_in(self):
        defaults = {
            "pj_app/src/main.cpp": ['value(u"Preferences::send_anonymous_stats"_s, false)'],
            "pj_app/src/MainWindow.cpp": ['value(kUsageStatsKey, false)'],
            "pj_app/src/PreferencesDialog.cpp": [
                'value(u"Preferences::send_anonymous_stats"_s, false)',
                'value(MainWindow::kUsageStatsKey, false)'],
        }
        for name, expressions in defaults.items():
            source = (ROOT / name).read_text()
            for expression in expressions:
                self.assertIn(expression, source)
                self.assertNotIn(expression.replace(', false)', ', true)'), source)

    def test_opt_out_precedes_registry_and_network_initialization(self):
        source = (ROOT / "pj_app/src/MainWindow.cpp").read_text()
        body = source.split("void MainWindow::startUsageReporting", 1)[1].split("void MainWindow::resizeEvent", 1)[0]
        self.assertLess(body.index('value(kUsageStatsKey, false)'), body.index('new UsageReporter'))
        self.assertLess(body.index('counters.setEnabled(false)'), body.index('return;'))
        self.assertIn('!may_report || !UsageReporter::canUpload(installation)', body)

    def test_automation_exclusions_remain(self):
        source = (ROOT / "pj_app/src/main.cpp").read_text()
        for token in ['parser.isSet(screenshot_option)', 'qEnvironmentVariableIsSet("CI")',
                      'qEnvironmentVariableIsSet("PJ_DISABLE_TELEMETRY")', '/*may_report=*/!automated']:
            self.assertIn(token, source)

if __name__ == "__main__":
    unittest.main()
