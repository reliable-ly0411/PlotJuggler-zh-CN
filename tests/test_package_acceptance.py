#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Regression guards for clean-host acceptance, without needing packaged binaries."""
import importlib.util
import copy
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

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
    def test_acceptance_forces_qt_logs_to_stderr(self):
        for inherited in [{}, {'QT_FORCE_STDERR_LOGGING': '0', 'QT_LOGGING_RULES': '*.info=false'}]:
            env = module.acceptance_environment(inherited)
            self.assertEqual(env['QT_FORCE_STDERR_LOGGING'], '1')
            self.assertEqual(env['QT_LOGGING_RULES'], 'pj.runtime.ingest.info=true')

    def test_acceptance_environment_remains_isolated(self):
        development = ['QT_PLUGIN_PATH', 'QML2_IMPORT_PATH', 'QT_QPA_FONTDIR',
                       'PYTHONHOME', 'PYTHONPATH', 'LD_LIBRARY_PATH']
        inherited = {name: '/development/runtime' for name in development}
        inherited.update(SystemRoot='C:/Windows', PJ_DISABLE_TELEMETRY='0')
        original = inherited.copy()
        env = module.acceptance_environment(inherited)
        self.assertTrue(all(name not in env for name in development))
        self.assertEqual(env['PJ_DISABLE_TELEMETRY'], '1')
        self.assertEqual(env['SystemRoot'], 'C:/Windows')
        self.assertEqual(inherited, original)

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


class BinPlotStateTests(unittest.TestCase):
    def setUp(self):
        self.state = {
            'version': 1,
            'plots': [{
                'id': 'p1',
                'viewport': {'x_min': 27.0, 'x_max': 82.0, 'y_min': 978.0, 'y_max': 1462.0},
                'curves': [{
                    'topic': '/RCOU', 'field': 'C1\t[us]', 'visible': True,
                    'sample_count': 5300, 'finite_sample_count': 5300,
                    'finite_samples_in_view': 5300,
                    'sample_bounds': {'x_min': 28.0, 'x_max': 81.0, 'y_min': 1000.0, 'y_max': 1440.0},
                }],
            }],
        }

    def test_visible_real_waveform_accepted_without_mutation(self):
        before = copy.deepcopy(self.state)
        module.validate_bin_plot_state(self.state)
        self.assertEqual(self.state, before)

    def test_missing_duplicate_or_wrong_plot_rejected(self):
        for plots in [[], [self.state['plots'][0]] * 2,
                      [dict(self.state['plots'][0], id='another-plot')]]:
            with self.subTest(plots=plots), self.assertRaises(AssertionError):
                module.validate_bin_plot_state(dict(self.state, plots=plots))

    def test_wrong_or_duplicate_curve_rejected(self):
        original = self.state['plots'][0]['curves'][0]
        for curves in [[], [original] * 2, [dict(original, topic='/WRONG')],
                       [dict(original, field='C1 [us]')]]:
            self.state['plots'][0]['curves'] = curves
            with self.subTest(curves=curves), self.assertRaises(AssertionError):
                module.validate_bin_plot_state(self.state)

    def test_empty_hidden_nonfinite_or_offscreen_curve_rejected(self):
        original = self.state['plots'][0]['curves'][0].copy()
        for values in [
            {'sample_count': 0, 'finite_sample_count': 0, 'finite_samples_in_view': 0},
            {'sample_count': 1, 'finite_sample_count': 1, 'finite_samples_in_view': 1},
            {'visible': False}, {'finite_sample_count': 5299}, {'finite_samples_in_view': 0},
        ]:
            self.state['plots'][0]['curves'] = [dict(original, **values)]
            with self.subTest(values=values), self.assertRaises(AssertionError):
                module.validate_bin_plot_state(self.state)

    def test_default_or_clipped_viewport_rejected(self):
        for viewport in [
            {'x_min': -1, 'x_max': 1, 'y_min': -1, 'y_max': 1},
            {'x_min': 29, 'x_max': 80, 'y_min': 978, 'y_max': 1462},
            {'x_min': 27, 'x_max': 82, 'y_min': 1001, 'y_max': 1439},
        ]:
            self.state['plots'][0]['viewport'] = viewport
            with self.subTest(viewport=viewport), self.assertRaises(AssertionError):
                module.validate_bin_plot_state(self.state)

    def test_nonfinite_reversed_or_wrong_waveform_bounds_rejected(self):
        plot = self.state['plots'][0]
        curve = plot['curves'][0]
        for target in [plot['viewport'], curve['sample_bounds']]:
            original = target.copy()
            for key in ['x_min', 'x_max', 'y_min', 'y_max']:
                for value in [float('nan'), float('inf'), '1000']:
                    target[key] = value
                    with self.subTest(key=key, value=value), self.assertRaises(AssertionError):
                        module.validate_bin_plot_state(self.state)
                    target.update(original)
            target['x_max'] = target['x_min']
            with self.assertRaises(AssertionError):
                module.validate_bin_plot_state(self.state)
            target.update(original)
            target['y_max'] = target['y_min']
            with self.assertRaises(AssertionError):
                module.validate_bin_plot_state(self.state)
            target.update(original)
        for changed in [{'x_max': 29.0}, {'y_min': 0.0}, {'y_max': 1.0}]:
            original = curve['sample_bounds'].copy()
            curve['sample_bounds'].update(changed)
            with self.subTest(changed=changed), self.assertRaises(AssertionError):
                module.validate_bin_plot_state(self.state)
            curve['sample_bounds'].update(original)

    def test_layout_preserves_exact_tabbed_field_and_unicode_log_path(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            log = work / 'source.BIN'
            log.write_bytes(b'fixture-copy')
            layout = module.write_bin_layout(work, log)
            self.assertEqual((work / '飞行日志.BIN').read_bytes(), log.read_bytes())
            root = ET.parse(layout).getroot()
            self.assertEqual(root.find('.//plot').attrib, {'id': 'p1', 'mode': 'TimeSeries'})
            self.assertEqual(root.find('.//curve').attrib, {'topic': '/RCOU', 'field': 'C1\t[us]'})
            self.assertEqual(root.find('.//fileInfo').get('filename'), '飞行日志.BIN')


if __name__ == '__main__':
    unittest.main()
