#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Regression guards for clean-host acceptance, without needing packaged binaries."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('verify_package', Path(__file__).parents[1] / 'packaging/localization/verify_package.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

EXPECTED = ['ardupilot-dataflash=1.2.0-pj4.rc.1', 'csv-loader=1.0.0', 'ros2-topic-subscriber=1.1.1']
MISSING_ROS = '''[plugin-validation][info] ardupilot-dataflash: Loaded DataSource ArduPilot BIN from /pkg/bin.so
[plugin-validation][info] csv-loader: Loaded DataSource CSV Loader from /pkg/csv.so
[ros2.proxy] ROS 2 not detected; source /opt/ros/<distro>/setup.bash before starting PlotJuggler.
[plugin-validation][error] ros2-topic-subscriber: /pkg/ros2/libros2_stream_plugin.so: plugin instance creation failed (create() returned null)
[plugin-validation][error] ros2-topic-subscriber: /pkg/ros2/libros2_stream_plugin.so: failed to load data_source plugin
[plugin-validation] expected plugin did not load: ros2-topic-subscriber=1.1.1
[plugin-validation] FAILED: loaded 2 plugin(s), expected 3
'''

class CleanAcceptanceTests(unittest.TestCase):
    def test_windows_key_case(self):
        for key in ['SYSTEMROOT', 'SystemRoot', 'systemroot']:
            self.assertEqual(module.windows_system_root({key: 'C:/Windows'}), Path('C:/Windows'))

    def test_windows_missing_or_ambiguous_root_rejected(self):
        for env in [{}, {'SYSTEMROOT': ''}, {'SYSTEMROOT': 'x', 'SystemRoot': 'y'}]:
            with self.assertRaises(AssertionError):
                module.windows_system_root(env)

    def test_complete_success(self):
        self.assertEqual(module.validate_plugin_result(0, '[plugin-validation] OK: loaded all 3 whitelisted plugin(s)', EXPECTED, False), [])

    def test_explicit_missing_ros_only(self):
        result = module.validate_plugin_result(1, MISSING_ROS, EXPECTED, True)
        self.assertEqual(result[0]['id'], 'ros2-topic-subscriber')
        self.assertEqual(result[0]['status'], 'not_tested_missing_external_dependency')

    def test_missing_ros_not_allowed_on_windows(self):
        with self.assertRaises(AssertionError):
            module.validate_plugin_result(1, MISSING_ROS, EXPECTED, False)

    def test_arbitrary_exit_rejected(self):
        with self.assertRaises(AssertionError):
            module.validate_plugin_result(139, MISSING_ROS, EXPECTED, True)

    def test_missing_prerequisite_message_rejected(self):
        with self.assertRaises(AssertionError):
            module.validate_plugin_result(1, MISSING_ROS.replace('ROS 2 not detected', 'Unexpected failure'), EXPECTED, True)

    def test_additional_plugin_failure_rejected(self):
        with self.assertRaises(AssertionError):
            module.validate_plugin_result(1, MISSING_ROS + '[plugin-validation][error] csv-loader: failed to load\n', EXPECTED, True)

    def test_ros_other_error_rejected(self):
        with self.assertRaises(AssertionError):
            module.validate_plugin_result(1, MISSING_ROS.replace('failed to load data_source plugin', 'undefined symbol: bad_abi'), EXPECTED, True)

    def test_missing_bin_rejected(self):
        with self.assertRaises(AssertionError):
            module.validate_plugin_result(1, MISSING_ROS.replace('ardupilot-dataflash: Loaded', 'wrong-plugin: Loaded'), EXPECTED, True)

    def test_version_mismatch_rejected(self):
        with self.assertRaises(AssertionError):
            module.validate_plugin_result(1, MISSING_ROS + '[plugin-validation] version mismatch for csv-loader: expected 1.0.0, loaded 2.0.0\n', EXPECTED, True)

    def test_wrong_ros_version_rejected(self):
        with self.assertRaises(AssertionError):
            module.validate_plugin_result(1, MISSING_ROS, [*EXPECTED[:-1], 'ros2-topic-subscriber=2.0.0'], True)

    def test_duplicate_loaded_plugin_rejected(self):
        with self.assertRaises(AssertionError):
            module.validate_plugin_result(1, MISSING_ROS + '[plugin-validation][info] csv-loader: Loaded duplicate\n', EXPECTED, True)

if __name__ == '__main__':
    unittest.main()
