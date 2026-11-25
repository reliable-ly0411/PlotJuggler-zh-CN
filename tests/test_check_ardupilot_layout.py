# SPDX-License-Identifier: MPL-2.0
"""Contract tests for the real-app layout regression's process invocation."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location('ardupilot_layout', Path(__file__).with_name('check_ardupilot_layout.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ArduPilotLayoutInvocationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='layout test with spaces ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.log = self.root / 'fixture.BIN'
        self.log.write_bytes(b'canonical-test-input')
        self.app = self.root / 'application.exe'
        self.plugins = self.root / 'plugins'
        self.expected_hash = hashlib.sha256(self.log.read_bytes()).hexdigest()

    def test_three_languages_receive_separate_absolute_profiles_and_original_flags(self):
        invocations = []
        def run(command, **kwargs):
            invocations.append((command, kwargs))
            Path(command[command.index('--dump-plot-state') + 1]).write_text('{}', encoding='utf-8')
            return subprocess.CompletedProcess(command, 0, stdout='', stderr='')
        with mock.patch.object(module.acceptance, 'LOG_SHA', self.expected_hash), \
             mock.patch.object(module.acceptance, 'write_bin_layout', side_effect=lambda work, log: work / 'layout.xml'), \
             mock.patch.object(module.acceptance, 'validate_bin_plot_state') as validate, \
             mock.patch.object(module.subprocess, 'run', side_effect=run):
            module.check(self.app, self.plugins, self.log)
        self.assertEqual(validate.call_count, 3)
        profiles = []
        for (command, kwargs), language in zip(invocations, ('zh_CN', 'zh_TW', 'en_US')):
            self.assertEqual(command.count('--profile-dir'), 1)
            profile = Path(command[command.index('--profile-dir') + 1])
            self.assertTrue(profile.is_absolute())
            work = Path(kwargs['env']['HOME'])
            self.assertEqual(profile, work / 'profiles' / language)
            profiles.append(profile)
            self.assertEqual(command[0], str(self.app))
            self.assertEqual(command[command.index('--plugin-dir') + 1], str(self.plugins))
            self.assertEqual(command[command.index('--language') + 1], language)
            for flag in ('--nosplash', '--disable-opengl', '--layout', '--exit-after-layout',
                         '--exit-after-layout-timeout', '--dump-plot-state'):
                self.assertIn(flag, command)
            self.assertEqual(command[command.index('--exit-after-layout-timeout') + 1], '60')
            self.assertEqual(kwargs['timeout'], 80)
        self.assertEqual(len(set(profiles)), 3)

    def test_failed_app_does_not_continue_or_validate(self):
        with mock.patch.object(module.acceptance, 'LOG_SHA', self.expected_hash), \
             mock.patch.object(module.acceptance, 'write_bin_layout', side_effect=lambda work, log: work / 'layout.xml'), \
             mock.patch.object(module.acceptance, 'validate_bin_plot_state') as validate, \
             mock.patch.object(module.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, stdout='', stderr='')) as run:
            with self.assertRaisesRegex(AssertionError, 'app exit 1'):
                module.check(self.app, self.plugins, self.log)
        self.assertEqual(run.call_count, 1)
        validate.assert_not_called()

    def test_each_language_flows_through_per_launch_guard_entry(self):
        calls = []
        def run(command, **kwargs):
            calls.append(command)
            Path(command[command.index('--dump-plot-state') + 1]).write_text('{}', encoding='utf-8')
            return subprocess.CompletedProcess(command, 0, stdout='', stderr='')
        with mock.patch.object(module.acceptance, 'LOG_SHA', self.expected_hash), \
             mock.patch.object(module.acceptance, 'write_bin_layout', side_effect=lambda work, log: work / 'layout.xml'), \
             mock.patch.object(module.acceptance, 'validate_bin_plot_state'), \
             mock.patch.object(module, 'launch_app', side_effect=run):
            module.check(self.app, self.plugins, self.log)
        self.assertEqual([cmd[cmd.index('--language') + 1] for cmd in calls], ['zh_CN', 'zh_TW', 'en_US'])

    def test_wrong_input_hash_never_launches(self):
        with mock.patch.object(module.acceptance, 'LOG_SHA', '0' * 64), \
             mock.patch.object(module.subprocess, 'run') as run:
            with self.assertRaises(AssertionError):
                module.check(self.app, self.plugins, self.log)
        run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
