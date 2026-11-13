# SPDX-License-Identifier: MPL-2.0
"""Unit-test PE inspection; native CI separately checks the actual linked binary."""
import importlib.util
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('windows_pe', ROOT / 'scripts/verify_windows_application.py')
pe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pe)


class WindowsApplicationTest(unittest.TestCase):
    def fixture(self, subsystem=2, types=(3, 14, 16, 24)):
        data = bytearray(1024)
        data[:2] = b'MZ'
        struct.pack_into('<I', data, 0x3c, 128)
        data[128:132] = b'PE\0\0'
        struct.pack_into('<H', data, 134, 1)
        struct.pack_into('<H', data, 148, 240)
        struct.pack_into('<H', data, 152, 0x20b)
        struct.pack_into('<H', data, 220, subsystem)
        struct.pack_into('<II', data, 280, 0x1000, 100)
        struct.pack_into('<IIII', data, 400, 512, 0x1000, 512, 512)
        struct.pack_into('<HH', data, 524, 0, len(types))
        for index, kind in enumerate(types):
            struct.pack_into('<II', data, 528 + index * 8, kind, 0x80000000)
        return data

    def test_gui_with_icons_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            exe = Path(directory) / 'app.exe'
            exe.write_bytes(self.fixture())
            pe.verify(exe)

    def test_console_and_missing_icons_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            exe = Path(directory) / 'app.exe'
            for image in [self.fixture(3), self.fixture(types=(16, 24)), self.fixture(types=(3, 14, 24))]:
                exe.write_bytes(image)
                with self.assertRaises(AssertionError):
                    pe.verify(exe)

    def test_icon_has_multiple_sizes(self):
        data = (ROOT / 'resources/plotjuggler.ico').read_bytes()
        reserved, kind, count = struct.unpack_from('<HHH', data)
        self.assertEqual((reserved, kind), (0, 1))
        self.assertGreaterEqual(count, 5)
        sizes = {data[6 + i * 16] or 256 for i in range(count)}
        self.assertTrue({16, 32, 48, 256} <= sizes)

    def test_full_version_strings_match(self):
        with tempfile.TemporaryDirectory() as directory:
            exe = Path(directory) / 'app.exe'
            exe.write_bytes(self.fixture())
            version = '9.8.7-zh.2.dev.3'
            values = {'FileVersion': version, 'ProductVersion': version}
            with mock.patch.object(pe, 'version_strings', return_value=values):
                pe.verify(exe, expected_version=version)
                with self.assertRaises(AssertionError):
                    pe.verify(exe, expected_version='9.8.7')

    def test_single_resource_and_cxx_only_warning_flags(self):
        cmake = (ROOT / 'pj_app/CMakeLists.txt').read_text(encoding='utf-8')
        self.assertEqual(cmake.count('WIN32_EXECUTABLE TRUE'), 1)
        self.assertEqual(cmake.count('target_sources(pj_app PRIVATE ${CMAKE_CURRENT_BINARY_DIR}/plotjuggler.rc)'), 1)
        self.assertNotIn('resources/windows/plotjuggler.rc', cmake)
        self.assertIn('"$<$<COMPILE_LANGUAGE:CXX>:${PJ_WARNING_FLAGS}>"', cmake)
        resource = (ROOT / 'pj_app/plotjuggler.rc.in').read_text(encoding='utf-8')
        for key in ('FileVersion', 'ProductVersion'):
            self.assertIn(f'VALUE "{key}", "@PJ_VERSION@"', resource)

    def test_runtime_cli_uses_separate_private_profiles(self):
        with tempfile.TemporaryDirectory(prefix='windows app test with spaces ') as directory:
            exe = Path(directory) / 'app.exe'
            exe.write_bytes(self.fixture())
            calls = []
            def run(command, **kwargs):
                calls.append((command, kwargs))
                stdout = b'PlotJuggler4 4.1.0' if command[-1] == '--version' else b'Usage: --language'
                return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr=b'')
            with mock.patch.object(pe.subprocess, 'run', side_effect=run):
                pe.verify(exe, runtime=True)
            self.assertEqual(len(calls), 2)
            profiles = []
            for (command, kwargs), option in zip(calls, ('--version', '--help')):
                self.assertEqual(command[0], str(exe.resolve()))
                self.assertEqual(command[1], '--profile-dir')
                profile = Path(command[2])
                self.assertTrue(profile.is_absolute())
                self.assertEqual(profile.name, option[2:])
                self.assertEqual(command[3], option)
                self.assertEqual(kwargs, {'capture_output': True, 'timeout': 60})
                profiles.append(profile)
            self.assertEqual(len(set(profiles)), 2)
            self.assertEqual(profiles[0].parent, profiles[1].parent)

    def test_runtime_cli_failure_stops_immediately(self):
        with tempfile.TemporaryDirectory() as directory:
            exe = Path(directory) / 'app.exe'
            exe.write_bytes(self.fixture())
            with mock.patch.object(pe.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, stdout=b'', stderr=b'error')) as run:
                with self.assertRaises(AssertionError):
                    pe.verify(exe, runtime=True)
            self.assertEqual(run.call_count, 1)

    def test_both_cli_calls_use_per_launch_guard_entry(self):
        with tempfile.TemporaryDirectory() as directory:
            exe = Path(directory) / 'app.exe'; exe.write_bytes(self.fixture())
            def run(command, **kwargs):
                output = b'PlotJuggler4 4.1.0' if command[-1] == '--version' else b'Usage: --language'
                return subprocess.CompletedProcess(command, 0, stdout=output, stderr=b'')
            with mock.patch.object(pe, 'launch_app', side_effect=run) as launch:
                pe.verify(exe, runtime=True)
            self.assertEqual([call.args[0][-1] for call in launch.call_args_list], ['--version', '--help'])

    def test_console_handler_preserves_core_only_runs(self):
        source = (ROOT / 'pj_app/src/main.cpp').read_text(encoding='utf-8')
        self.assertEqual(source.count('PJ::attachParentConsoleStreams();'), 1)
        self.assertNotIn('void attachParentConsole()', source)
        self.assertIn('qobject_cast<QApplication*>(QCoreApplication::instance())', source)
        self.assertIn('SetConsoleCtrlHandler(onConsoleInterrupt, TRUE)', source)


if __name__ == '__main__':
    unittest.main()
