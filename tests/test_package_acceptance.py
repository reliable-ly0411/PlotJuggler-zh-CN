#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Regression guards for clean-host acceptance, without needing packaged binaries."""
import importlib.util
import copy
import json
import os
import shutil
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
    def test_both_linux_artifacts_run_upstream_smoke_before_localized_acceptance(self):
        root = Path(__file__).resolve().parents[1]
        script = (root / 'packaging/localization/verify_linux.sh').read_text(encoding='utf-8')
        deb = script.index('bash /src/packaging/deb/smoke_test.sh')
        appimage = script.index('bash /src/packaging/appimage/smoke_test.sh /pkg/*.AppImage')
        self.assertLess(deb, appimage)
        self.assertLess(appimage, script.index('verify_package.py'))
        for kind in ('deb', 'appimage'):
            smoke = (root / 'packaging' / kind / 'smoke_test.sh').read_text(encoding='utf-8')
            self.assertIn('render_check.sh', smoke)
            self.assertNotIn('wayland_check.sh', smoke)

    def test_tag_locked_ci_keeps_gpu_requirement(self):
        workflow = (Path(__file__).resolve().parents[1] / '.github/workflows/zh-4x-ci.yml').read_text(encoding='utf-8')
        self.assertIn('PJ_REQUIRE_GPU_TESTS=1 xvfb-run -a ctest', workflow)
        self.assertNotIn('MainWindowRhiWindowTest', workflow)

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

    def test_plugin_diagnostics_force_english_without_weakening_whitelist(self):
        prefix = Path('/package')
        args = module.plugin_validation_arguments(prefix, EXPECTED)
        self.assertEqual(args, ['--language', 'en_US', '--validate-plugins',
                               str(prefix / 'lib/plotjuggler/plugins'),
                               *[arg for spec in EXPECTED for arg in ('--expect-plugin', spec)]])
        self.assertEqual(module.ACCEPTANCE_LANGUAGES, ('zh_CN', 'zh_TW', 'en_US'))

    def test_unexpected_localized_diagnostics_still_fail_closed(self):
        with self.assertRaises(AssertionError):
            module.validate_plugin_result(1, MISSING_ROS.replace('Loaded ', '已加载 '), EXPECTED, True)

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


class CsvPlotStateTests(unittest.TestCase):
    def setUp(self):
        self.state = {'version': 1, 'plots': [{'id': 'csv-plot',
            'viewport': {'x_min': -0.1, 'x_max': 2.1, 'y_min': -3.0, 'y_max': 4.0},
            'curves': [{'topic': 'synthetic', 'field': field, 'visible': True,
                        'sample_count': 3, 'finite_sample_count': 3, 'finite_samples_in_view': 3,
                        'sample_bounds': {'x_min': 0.0, 'x_max': 2.0, 'y_min': low, 'y_max': high}}
                       for field, low, high in [('sample_index', 0.0, 2.0), ('synthetic_signal', -2.0, 3.5)]]}]}

    def test_two_complete_visible_synthetic_curves_pass_without_mutation(self):
        before = copy.deepcopy(self.state)
        module.validate_csv_plot_state(self.state, 'synthetic')
        self.assertEqual(self.state, before)

    def test_empty_duplicate_unbound_hidden_or_partial_data_fail(self):
        changes = [
            lambda state: state.update(plots=[]),
            lambda state: state['plots'].append(copy.deepcopy(state['plots'][0])),
            lambda state: state['plots'][0].update(curves=[]),
            lambda state: state['plots'][0]['curves'][1].update(field='sample_index'),
            lambda state: state['plots'][0]['curves'][0].update(topic='wrong-topic'),
            lambda state: state['plots'][0]['curves'][0].update(visible=False),
            lambda state: state['plots'][0]['curves'][0].update(sample_count=0),
            lambda state: state['plots'][0]['curves'][0].update(finite_sample_count=2),
            lambda state: state['plots'][0]['curves'][0].update(finite_samples_in_view=2),
            lambda state: state['plots'][0]['curves'][1]['sample_bounds'].update(y_max=3.0),
            lambda state: state['plots'][0]['curves'][0]['sample_bounds'].update(x_max=1.0),
            lambda state: state['plots'][0]['viewport'].update(x_max=1.0),
            lambda state: state['plots'][0]['viewport'].update(y_min=0.0),
        ]
        for number, change in enumerate(changes):
            with self.subTest(change=number):
                state = copy.deepcopy(self.state)
                change(state)
                with self.assertRaises(AssertionError):
                    module.validate_csv_plot_state(state, 'synthetic')

    def test_nonfinite_or_nonnumeric_bounds_fail(self):
        for target in ['view', 'data']:
            for key in ['x_min', 'x_max', 'y_min', 'y_max']:
                for value in [float('nan'), float('inf'), '0', False]:
                    with self.subTest(target=target, key=key, value=value):
                        state = copy.deepcopy(self.state)
                        plot = state['plots'][0]
                        bounds = plot['viewport'] if target == 'view' else plot['curves'][0]['sample_bounds']
                        bounds[key] = value
                        with self.assertRaises(AssertionError):
                            module.validate_csv_plot_state(state, 'synthetic')

    def test_generated_layouts_use_identical_synthetic_bytes_and_native_paths(self):
        with tempfile.TemporaryDirectory(prefix='csv fixture & ') as temporary:
            work = Path(temporary)
            inputs = []
            for unicode_path in [False, True]:
                layout, topic = module.write_csv_layout(work, unicode_path)
                root = ET.parse(layout).getroot()
                info = root.find('.//fileInfo')
                source = Path(info.get('filename'))
                self.assertTrue(source.is_file())
                self.assertEqual(source.stem, topic)
                self.assertEqual(root.find('.//plot').get('id'), 'csv-plot')
                self.assertEqual({curve.get('field') for curve in root.findall('.//curve')},
                                 {'sample_index', 'synthetic_signal'})
                self.assertEqual({curve.get('topic') for curve in root.findall('.//curve')}, {topic})
                plugin = info.find('plugin')
                self.assertEqual(plugin.get('manifest_id'), 'csv-loader')
                config = json.loads(plugin.text)
                self.assertEqual(Path(config['filepath']), source)
                self.assertEqual(config['time_mode'], 'row_number')
                self.assertEqual(config['delimiter'], ',')
                self.assertFalse(config['detect_delimiter'])
                inputs.append(source.read_bytes())
            self.assertEqual(inputs[0], inputs[1])
            self.assertEqual(inputs[0], b'sample_index,synthetic_signal\n0,-2\n1,3.5\n2,0\n')



class CaptureGeometryTests(unittest.TestCase):
    def snapshot(self, **changes):
        value = {'backend': 'test', 'window_id': 123, 'pid': 456, 'frame': (8, 8, 1016, 720),
                 'work_area': (0, 0, 1024, 728), 'desktop': (0, 0, 1024, 768), 'occluded': False}
        return dict(value, **changes)

    def png(self, path, size=(1024, 768)):
        import struct
        path.write_bytes(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR' + struct.pack('>II', *size) + bytes(11000))

    def test_windows_window_fits_work_area_without_taskbar_or_pixel_scaling(self):
        target = module.capture_target((0, 0, 1585, 980), (0, 0, 1024, 728), (800, 600), resize=True)
        self.assertEqual(target, (8, 8, 1016, 720))
        module.validate_capture_geometry(self.snapshot(frame=target))

    def test_negative_monitor_origin_and_exact_minimum_fit(self):
        work = (-1280, 40, 0, 1000)
        target = module.capture_target((20, 20, 1500, 1000), work, (1280, 960), resize=True)
        self.assertEqual(target, work)
        module.validate_capture_geometry(self.snapshot(frame=target, work_area=work, desktop=(-1280, 0, 1920, 1080)))

    def test_cannot_shrink_below_actual_content_minimum(self):
        for minimum in ((1025, 600), (800, 729), (0, 500), (True, 600)):
            with self.subTest(minimum=minimum), self.assertRaises(ValueError):
                module.capture_target((0, 0, 1585, 980), (0, 0, 1024, 728), minimum, resize=True)
        with self.assertRaises(ValueError):
            module.capture_target((0, 0, 500, 300), (0, 0, 1024, 728), (800, 600), resize=True)

    def test_linux_preserves_default_window_size_and_refuses_small_screen(self):
        frame = (0, 0, 1569, 941)
        self.assertEqual(module.capture_target(frame, (0, 0, 1920, 1080), (1569, 941), resize=False),
                         (8, 8, 1577, 949))
        with self.assertRaises(ValueError):
            module.capture_target(frame, (0, 0, 1440, 1000), (1569, 941), resize=False)

    def test_partial_frame_taskbar_overlap_and_occlusion_fail(self):
        for change in ({'frame': (-1, 0, 1000, 700)}, {'frame': (0, 0, 1025, 700)},
                       {'frame': (0, 0, 1024, 729)}, {'occluded': True},
                       {'work_area': (0, 0, 2000, 1000)}, {'frame': (1, 2, 1, 700)}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                module.validate_capture_geometry(self.snapshot(**change))
        self.assertFalse(module.rectangles_overlap((0, 0, 1024, 728), (0, 728, 1024, 768)))

    def test_original_png_and_identical_measured_snapshot_are_required(self):
        with tempfile.TemporaryDirectory() as directory:
            png = Path(directory) / 'gui.png'; self.png(png)
            ready = self.snapshot()
            module.validate_capture_result(ready, copy.deepcopy(ready), png)
            for change in ({'pid': 999}, {'window_id': 789}, {'frame': (9, 8, 1016, 720)}, {'occluded': True}):
                with self.subTest(change=change), self.assertRaises(ValueError):
                    module.validate_capture_result(ready, self.snapshot(**change), png)
            self.png(png, (800, 600))
            with self.assertRaisesRegex(ValueError, 'dimensions'):
                module.validate_capture_result(ready, ready, png)
            png.write_bytes(b'not a screenshot' * 1000)
            with self.assertRaisesRegex(ValueError, 'PNG'):
                module.validate_capture_result(ready, ready, png)

    def test_capture_receipt_hashes_the_original_pixels(self):
        from unittest import mock
        import hashlib
        with tempfile.TemporaryDirectory() as directory:
            png = Path(directory) / 'gui-en_US.png'; self.png(png)
            before = png.read_bytes()
            backend = 'capture_windows_gui' if module.os.name == 'nt' else 'capture_linux_gui'
            with mock.patch.object(module, backend, return_value=self.snapshot()) as capture:
                result = module.capture_gui(object(), Path(directory), Path(directory)/'app', Path(directory)/'profile', png)
            capture.assert_called_once()
            self.assertEqual(png.read_bytes(), before)
            self.assertEqual(result['sha256'], hashlib.sha256(before).hexdigest())
            self.assertEqual(result['capture'], 'unscaled-full-desktop')
            self.assertTrue(result['complete_window_visible'])
            saved = json.loads(png.with_suffix('.geometry.json').read_text(encoding='utf-8'))
            self.assertEqual(saved['screenshot'], 'gui-en_US.png')


class LinuxCaptureIdentityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.proc = self.root / 'proc'; self.proc.mkdir()
        self.profile = self.root / 'isolated profile'
        self.binary = self.root / 'packaged-app'; self.binary.write_bytes(b'exact packaged executable')

    def process(self, pid, *, profile=None, binary=None, start=123):
        import os
        entry = self.proc / str(pid); entry.mkdir()
        (entry / 'cmdline').write_bytes(b'plotjuggler4\0--profile-dir\0' +
                                        os.fsencode(str(profile or self.profile)) + b'\0--language\0en_US\0')
        fields = ['0'] * 20; fields[19] = str(start)
        (entry / 'stat').write_text(str(pid)+' (name with spaces) '+' '.join(fields), encoding='utf-8')
        (entry / 'exe').write_bytes(binary or self.binary.read_bytes())

    def test_appimage_child_pid_is_bound_to_launch_session_profile_and_binary(self):
        self.process(100, binary=b'AppImage launcher'); self.process(200)
        self.process(300, profile=self.root/'other-profile'); self.process(400)
        result = module.linux_capture_processes(100, self.profile, self.binary, self.proc,
                                               getsid=lambda pid: 100 if pid in (100, 200, 300) else 400)
        self.assertEqual(set(result), {200})
        self.assertEqual(result[200]['start_ticks'], 123)

    def test_wrong_binary_or_no_owned_process_fails(self):
        self.process(200, binary=b'different executable')
        with self.assertRaisesRegex(ValueError, 'no exact'):
            module.linux_capture_processes(100, self.profile, self.binary, self.proc, getsid=lambda pid: 100)
        with self.assertRaisesRegex(ValueError, 'no exact'):
            module.linux_capture_processes(100, self.profile, self.binary, self.proc, getsid=lambda pid: 200)

    def test_ambiguous_profile_argument_is_not_process_identity(self):
        self.process(200)
        path = self.proc/'200/cmdline'; path.write_bytes(path.read_bytes()+b'--profile-dir\0other\0')
        with self.assertRaises(ValueError):
            module.linux_capture_processes(100, self.profile, self.binary, self.proc, getsid=lambda pid: 100)

    def test_x11_search_errors_are_not_treated_as_no_matching_window(self):
        from unittest import mock
        import subprocess
        for code, stderr in ((1, 'cannot open display'), (2, ''), (0, '')):
            result = subprocess.CompletedProcess([], code, '', stderr)
            with self.subTest(code=code, stderr=stderr), mock.patch.object(module.subprocess, 'run', return_value=result):
                if code:
                    with self.assertRaises(ValueError):
                        module.x11_call({'xdotool': '/tool/xdotool'}, 'xdotool', 'search', empty_ok=True)
                else:
                    self.assertEqual(module.x11_call({'xdotool': '/tool/xdotool'}, 'xdotool', 'search', empty_ok=True), '')
        with mock.patch.object(module.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, '', '')):
            self.assertEqual(module.x11_call({'xdotool': '/tool/xdotool'}, 'xdotool', 'search', empty_ok=True), '')

    def test_missing_x11_helper_fails_without_launching_a_fallback(self):
        from unittest import mock
        with mock.patch.object(module.shutil, 'which', side_effect=lambda name: None if name == 'xdotool' else '/tool/'+name), \
             mock.patch.object(module.subprocess, 'run') as run:
            with self.assertRaises(ValueError): module.x11_capture_tools()
            run.assert_not_called()


class X11CaptureTests(unittest.TestCase):
    @staticmethod
    def geometry(x=0, y=0, width=1569, height=941, border=0, visible=True):
        return (f'  Absolute upper-left X: {x}\n  Absolute upper-left Y: {y}\n'
                f'  Width: {width}\n  Height: {height}\n  Border width: {border}\n'
                '  Class: InputOutput\n  Map State: '+('IsViewable' if visible else 'IsUnMapped')+'\n')

    def setUp(self):
        from unittest import mock
        self.process = mock.Mock(pid=100); self.process.poll.return_value = None
        self.identity = {200: {'start_ticks': 123, 'image_sha256': 'a'*64}}
        self.properties = ('_NET_WM_PID = 200\n_NET_WM_WINDOW_TYPE = _NET_WM_WINDOW_TYPE_NORMAL\n'
                           'WM_TRANSIENT_FOR:  not found.\n')
        self.windows = '512\n'; self.children = '  0x200 "PlotJuggler 4": 1569x941+0+0\n'
        self.wm = '_NET_SUPPORTING_WM_CHECK:  no such atom on any window.\n'
        self.other = self.geometry(1700, 10, 100, 100)

    def call(self, tools, name, *args, **kwargs):
        if name == 'xprop' and args[0] == '-root': return self.wm
        if name == 'xprop': return self.properties
        if name == 'xdotool': return self.windows
        if args == ('-root', '-stats'): return self.geometry(width=1920, height=1080)
        if args == ('-root', '-children'): return self.children
        if args == ('-id', '0x200', '-stats'): return self.geometry(8, 8)
        if args == ('-id', '0x300', '-stats'): return self.other
        self.fail((name, args))

    def snapshot(self):
        from unittest import mock
        with mock.patch.object(module, 'linux_capture_processes', return_value=self.identity), \
             mock.patch.object(module, 'x11_call', side_effect=self.call):
            return module.linux_capture_snapshot(self.process, Path('/profile'), Path('/app'), {})

    def test_exact_child_pid_window_and_root_bounds_pass(self):
        result = self.snapshot()
        self.assertEqual((result['launcher_pid'], result['pid'], result['window_id']), (100, 200, 512))
        module.validate_capture_geometry(result)
        self.assertEqual(result['frame'], (8, 8, 1577, 949))

    def test_wrong_pid_multiple_windows_transient_or_managed_display_fail(self):
        for field, value in (('properties', self.properties.replace('= 200', '= 999')),
                             ('windows', '512\n513\n'),
                             ('properties', self.properties.replace('WM_TRANSIENT_FOR:  not found.', 'WM_TRANSIENT_FOR = window id # 0x42')),
                             ('wm', '_NET_SUPPORTING_WM_CHECK(WINDOW): window id # 0x100')):
            with self.subTest(field=field):
                original = getattr(self, field); setattr(self, field, value)
                try:
                    with self.assertRaises(ValueError): self.snapshot()
                finally:
                    setattr(self, field, original)

    def test_root_child_and_visible_other_windows_are_checked(self):
        self.children += '  0x300 "other": 100x100+0+0\n'
        module.validate_capture_geometry(self.snapshot())
        self.other = self.geometry(10, 10, 100, 100)
        with self.assertRaisesRegex(ValueError, 'overlaps'):
            module.validate_capture_geometry(self.snapshot())
        self.other = self.geometry(10, 10, 100, 100, visible=False)
        module.validate_capture_geometry(self.snapshot())
        self.children = '  0x300 "other": 100x100+0+0\n'
        with self.assertRaisesRegex(ValueError, 'root child'): self.snapshot()

    def test_border_pixels_and_malformed_measurement_are_not_ignored(self):
        value = module.x11_window_geometry(self.geometry(-10, 20, 100, 50, border=2))
        self.assertEqual(value['frame'], (-12, 18, 92, 72))
        with self.assertRaises(ValueError): module.x11_window_geometry('Width: 100\n')
        for old, new in (('IsViewable', 'Unknown'), ('InputOutput', 'Unknown'),
                         ('  Map State: IsViewable\n', ''), ('  Class: InputOutput\n', '')):
            with self.subTest(old=old), self.assertRaises(ValueError):
                module.x11_window_geometry(self.geometry().replace(old, new))

    def test_capture_moves_actual_window_and_preserves_full_root_pixels(self):
        from unittest import mock
        with tempfile.TemporaryDirectory() as directory:
            png = Path(directory)/'gui.png'
            before = self.snapshot(); ready = dict(before, frame=(8, 8, 1577, 949))
            before = dict(before, frame=(0, 0, 1569, 941))
            calls = []
            def call(tools, name, *args, **kwargs):
                calls.append((name, args))
                if name == 'import': CaptureGeometryTests().png(png, (1920, 1080))
                return '512\n' if args == ('getwindowfocus',) else ''
            with mock.patch.object(module, 'x11_capture_tools', return_value={}), \
                 mock.patch.object(module, 'linux_capture_snapshot', side_effect=[before, ready, ready]), \
                 mock.patch.object(module, 'x11_call', side_effect=call), mock.patch.object(module.time, 'sleep'):
                result = module.capture_linux_gui(self.process, Path('/prefix'), Path('/profile'), png)
            self.assertEqual(result, ready)
            self.assertEqual(calls, [('xdotool', ('windowmove', '512', 8, 8)),
                                     ('xdotool', ('windowraise', '512')), ('xdotool', ('windowfocus', '512')),
                                     ('xdotool', ('getwindowfocus',)), ('import', ('-window', 'root', png))])

    def test_resize_or_pid_replacement_before_capture_fails(self):
        from unittest import mock
        before = self.snapshot()
        for changed in (dict(before, frame=(8, 8, 1500, 949)), dict(before, pid=201),
                        dict(before, process_identity={'start_ticks': 999, 'image_sha256': 'a'*64})):
            with self.subTest(changed=changed), \
                 mock.patch.object(module, 'x11_capture_tools', return_value={}), \
                 mock.patch.object(module, 'linux_capture_snapshot', side_effect=[before, changed]), \
                 mock.patch.object(module, 'x11_call'), mock.patch.object(module.time, 'sleep'):
                with self.assertRaises(ValueError):
                    module.capture_linux_gui(self.process, Path('/prefix'), Path('/profile'), Path('/unused.png'))



class WindowsCaptureIdentityTests(unittest.TestCase):
    def window(self, **changes):
        return dict({'window_id': 123, 'pid': 456, 'owner': None, 'style': 0x00CF0000,
                     'extended_style': 0, 'visible': True, 'enabled': True}, **changes)

    def test_unique_standard_main_window_is_selected_without_title_matching(self):
        windows = [self.window(pid=999, window_id=222), self.window(),
                   self.window(window_id=333, style=0x80C80000)]
        self.assertEqual(module.windows_capture_main_window(windows, 456), 123)

    def test_hidden_main_cannot_be_replaced_by_visible_dialog(self):
        windows = [self.window(visible=False), self.window(window_id=333, style=0x80C80000)]
        with self.assertRaisesRegex(ValueError, 'hidden'):
            module.windows_capture_main_window(windows, 456)
        with self.assertRaisesRegex(ValueError, 'standard main'):
            module.windows_capture_main_window(windows[1:], 456)

    def test_multiple_main_windows_including_hidden_ones_fail(self):
        for visible in (True, False):
            with self.subTest(visible=visible), self.assertRaisesRegex(ValueError, 'one standard'):
                module.windows_capture_main_window([self.window(), self.window(window_id=999, visible=visible)], 456)

    def test_owned_popup_child_tool_modal_disabled_and_wrong_pid_fail(self):
        for change in ({'owner': 99}, {'style': 0x00CF0000 | 0x80000000}, {'style': 0x00CF0000 | 0x40000000},
                       {'style': 0x00CF0000 & ~0x00040000}, {'extended_style': 0x80}, {'extended_style': 0x1},
                       {'enabled': False}, {'pid': 999}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                module.windows_capture_main_window([self.window(**change)], 456)


class CapturePlatformContractTests(unittest.TestCase):
    def test_helpers_are_installed_inside_each_clean_container_and_screen_is_real(self):
        root = Path(__file__).resolve().parents[1]
        script = (root/'packaging/localization/verify_linux.sh').read_text(encoding='utf-8')
        self.assertIn('python3 imagemagick xdotool x11-utils', script)
        self.assertEqual(script.count("--server-args='-screen 0 1920x1080x24'"), 2)
        self.assertNotIn('1440x1000', script)
        self.assertIn('--executable /tmp/appimage/app.AppImage', script)

    def test_windows_uses_explicit_pointer_types_work_area_minimum_and_visible_frame(self):
        import inspect
        source = inspect.getsource(module.capture_windows_gui)
        for required in ('SetThreadDpiAwarenessContext', 'GetWindowThreadProcessId', 'QueryFullProcessImageNameW',
                         'os.path.samefile', 'GetMonitorInfoW', 'monitor.work', 'SendMessageTimeoutW',
                         'minimum_track', 'DwmGetWindowAttribute', 'GetForegroundWindow', 'GetTopWindow',
                         'validate_capture_result(ready, after, png)', 'ImageGrab.grab(include_layered_windows=True, all_screens=True)'):
            self.assertIn(required, source)
        for forbidden in ('ChangeDisplaySettings', 'SetProcessDPIAware', '.resize(', '.crop(', 'PrintWindow'):
            self.assertNotIn(forbidden, source)



@unittest.skipUnless(os.name == 'posix' and all(shutil.which(name) for name in
                     ('Xvfb', 'xdotool', 'xprop', 'xwininfo', 'import')), 'actual Xvfb capture requires all X11 helpers')
class ActualXvfbCaptureTests(unittest.TestCase):
    def test_offscreen_real_window_is_moved_and_whole_desktop_captured(self):
        """A synthetic Xlib window checks capture mechanics, not final-package UI."""
        import select
        import signal
        import subprocess
        import sys
        import time
        from unittest import mock
        fixture = r'''
import ctypes as c, ctypes.util, os, random, sys
from pathlib import Path
x = c.CDLL(ctypes.util.find_library('X11'))
specs = {
 'XOpenDisplay': ([c.c_char_p], c.c_void_p), 'XDefaultRootWindow': ([c.c_void_p], c.c_ulong),
 'XCreateSimpleWindow': ([c.c_void_p,c.c_ulong,c.c_int,c.c_int,c.c_uint,c.c_uint,c.c_uint,c.c_ulong,c.c_ulong],c.c_ulong),
 'XInternAtom': ([c.c_void_p,c.c_char_p,c.c_int],c.c_ulong),
 'XChangeProperty': ([c.c_void_p,c.c_ulong,c.c_ulong,c.c_ulong,c.c_int,c.c_int,c.c_void_p,c.c_int],c.c_int),
 'XStoreName': ([c.c_void_p,c.c_ulong,c.c_char_p],c.c_int),
 'XMapWindow': ([c.c_void_p,c.c_ulong],c.c_int), 'XFlush': ([c.c_void_p],c.c_int),
 'XSelectInput': ([c.c_void_p,c.c_ulong,c.c_long],c.c_int),
 'XNextEvent': ([c.c_void_p,c.c_void_p],c.c_int),
 'XCreateGC': ([c.c_void_p,c.c_ulong,c.c_ulong,c.c_void_p],c.c_void_p),
 'XSetForeground': ([c.c_void_p,c.c_void_p,c.c_ulong],c.c_int),
 'XDrawLine': ([c.c_void_p,c.c_ulong,c.c_void_p,c.c_int,c.c_int,c.c_int,c.c_int],c.c_int),
}
for name,(args,result) in specs.items():
 function=getattr(x,name); function.argtypes=args; function.restype=result
display=x.XOpenDisplay(None)
assert display
window=x.XCreateSimpleWindow(display,x.XDefaultRootWindow(display),1400,200,1569,941,3,0xffffff,0)
for name,kind,value in ((b'_NET_WM_PID',b'CARDINAL',os.getpid()),
                        (b'_NET_WM_WINDOW_TYPE',b'ATOM',x.XInternAtom(display,b'_NET_WM_WINDOW_TYPE_NORMAL',False))):
 data=(c.c_ulong*1)(value)
 x.XChangeProperty(display,window,x.XInternAtom(display,name,False),x.XInternAtom(display,kind,False),32,0,data,1)
x.XStoreName(display,window,b'Capture fixture, not a packaged application')
x.XSelectInput(display,window,1<<15)
x.XMapWindow(display,window); x.XFlush(display)
gc=x.XCreateGC(display,window,0,None)
rng=random.Random(42)
lines=[(rng.randrange(0xffffff),rng.randrange(1569),rng.randrange(941),rng.randrange(1569),rng.randrange(941)) for _ in range(1500)]
Path(sys.argv[-1]).write_text('ready',encoding='utf-8')
event=(c.c_long*24)()
while True:
 x.XNextEvent(display,c.byref(event))
 if c.cast(c.byref(event),c.POINTER(c.c_int))[0]==12:
  for color,x1,y1,x2,y2 in lines:
   x.XSetForeground(display,gc,color); x.XDrawLine(display,window,gc,x1,y1,x2,y2)
  x.XFlush(display)
'''
        with tempfile.TemporaryDirectory(prefix='actual-capture-') as directory:
            root = Path(directory); script = root/'window.py'; script.write_text(fixture, encoding='utf-8')
            prefix = root/'payload'; (prefix/'bin').mkdir(parents=True)
            (prefix/'bin/plotjuggler4').symlink_to(Path(sys.executable).resolve())
            profile = root/'isolated profile'; ready = root/'ready'; png = root/'gui.png'
            read_fd, write_fd = os.pipe()
            with (root/'xvfb.log').open('w') as log:
                server = subprocess.Popen([shutil.which('Xvfb'), '-displayfd', str(write_fd), '-screen', '0',
                                           '1920x1080x24', '-nolisten', 'tcp'], pass_fds=(write_fd,), stdout=log, stderr=log)
                os.close(write_fd); process = None
                try:
                    self.assertTrue(select.select([read_fd], [], [], 15)[0], 'Xvfb did not start')
                    display = os.read(read_fd, 64).strip().decode('ascii')
                    self.assertTrue(display.isdecimal())
                    with mock.patch.dict(os.environ, {'DISPLAY': ':'+display}):
                        # The shell wrapper keeps --profile-dir but has different
                        # image bytes; only the child owns the real X11 window.
                        process = subprocess.Popen(['/bin/sh', '-c', '"$@" & wait', 'capture-wrapper',
                                                    sys.executable, '-B', str(script), '--profile-dir', str(profile), str(ready)],
                                                   start_new_session=True, stdout=log, stderr=log)
                        deadline = time.monotonic()+15
                        while not ready.exists() and time.monotonic()<deadline and process.poll() is None:
                            time.sleep(0.05)
                        self.assertTrue(ready.exists(), 'Xlib fixture did not start')
                        result = module.capture_linux_gui(process, prefix, profile, png)
                    self.assertNotEqual(result['pid'], process.pid)
                    self.assertEqual(result['frame'], (8, 8, 1583, 955))
                    self.assertEqual(module.png_size(png), (1920, 1080))
                    self.assertFalse(result['occluded'])
                finally:
                    os.close(read_fd)
                    if process is not None:
                        try: os.killpg(process.pid, signal.SIGTERM)
                        except ProcessLookupError: pass
                        process.wait(timeout=10)
                    server.terminate(); server.wait(timeout=10)


if __name__ == '__main__':
    unittest.main()
