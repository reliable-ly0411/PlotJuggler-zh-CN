# SPDX-License-Identifier: MPL-2.0
"""Synthetic identity receipts and source contracts, not a Windows execution."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('native_python_launcher', ROOT / 'scripts/windows/run_native_test_bundle.py')
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


class PythonIdentityTests(unittest.TestCase):
    def test_native_scripting_probe_is_opt_in_and_binds_the_actual_module_and_home(self):
        cmake = (ROOT / 'pj_scripting/CMakeLists.txt').read_text(encoding='utf-8')
        source = (ROOT / 'pj_scripting/tests/python_runtime_identity_win_test.cpp').read_text(encoding='utf-8')
        self.assertIn('if(WIN32 AND PJ_NATIVE_BUNDLE_MODE)', cmake)
        self.assertIn('python_runtime_identity_win_test.cpp', cmake)
        self.assertIn('PJ_NATIVE_EXPECTED_PYTHON_HOME="${_pj_python_home_define}"', cmake)
        for required in ('GetModuleHandleW', 'GetModuleFileNameW', 'Py_GetVersion()', 'PY_VERSION',
                         'ensureInterpreter()', 'attr("prefix")', 'import("math")', 'std::filesystem::equivalent'):
            self.assertIn(required, source)
        self.assertNotIn('3.12.7', source)

    def test_driver_receipt_rejects_wrong_pid_version_modules_or_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / 't/python').mkdir(parents=True)
            paths = ['t/python/python.exe', 't/python/python312.zip', 's/.github/windows-native-kit/tool-pins.json',
                     *['t/python/' + x + '.pyd' for x in ('_ctypes', '_ssl', '_sqlite3')],
                     *['t/python/' + x for x in ('python312.dll', 'libcrypto-3.dll', 'libssl-3.dll',
                                                 'libffi-8.dll', 'sqlite3.dll')]]
            rows = [{'path': p, 'sha256': 'a' * 64} for p in paths]
            manifest = {'files': rows, 'provenance': {'tools': [{'name': 'python', 'version': '3.12.10'}]}}
            row = lambda path: {'path': path, 'sha256': 'a' * 64}
            receipt = {'schema': 1, 'scope': 'isolated-driver-python', 'pid': 42, 'version': '3.12.10',
                       'manifest_sha256': 'b' * 64, 'prefix': str(root / 't/python'),
                       'executable': row(paths[0]), 'stdlib': row(paths[1]), 'tool_pins': row(paths[2]),
                       'modules': [row(p) for p in paths[3:6]], 'loaded_dlls': [row(p) for p in paths[6:]]}
            process = {'identity': {'pid': 42}}
            launcher.validate_driver_probe(receipt, manifest, root, 'b' * 64, process)
            variants = [dict(receipt, schema=True), dict(receipt, pid=True), dict(receipt, pid=43),
                        dict(receipt, version='3.12.7'), dict(receipt, manifest_sha256='c' * 64),
                        dict(receipt, modules=receipt['modules'][:-1]),
                        dict(receipt, modules=receipt['modules'] + receipt['modules'][:1]),
                        dict(receipt, loaded_dlls=receipt['loaded_dlls'][:-1]),
                        dict(receipt, loaded_dlls=receipt['loaded_dlls'] + receipt['loaded_dlls'][:1])]
            for index, variant in enumerate(variants):
                with self.subTest(variant=index), self.assertRaises(launcher.LauncherError):
                    launcher.validate_driver_probe(variant, manifest, root, 'b' * 64, process)
            with self.assertRaises(launcher.LauncherError):
                launcher.validate_driver_probe(receipt, manifest, root, 'b' * 64, {'identity': {'pid': True}})
            wrong = dict(receipt, loaded_dlls=[dict(item) for item in receipt['loaded_dlls']])
            wrong['loaded_dlls'][0]['sha256'] = 'f' * 64
            with self.assertRaises(launcher.LauncherError):
                launcher.validate_driver_probe(wrong, manifest, root, 'b' * 64, process)

    def test_cng_object_buffer_outlives_the_hash_handle(self):
        source = (ROOT / 'pj_scripting/tests/python_runtime_identity_win_test.cpp').read_text(encoding='utf-8')
        sha256 = source.split('std::optional<std::string> sha256(', 1)[1].split('\nbool within(', 1)[0]
        self.assertLess(sha256.index('std::vector<UCHAR> object;'), sha256.index('} handles;'))
        self.assertLess(sha256.index('} handles;'), sha256.index('object.resize(object_size);'))
        self.assertLess(sha256.index('object.resize(object_size);'), sha256.index('BCryptCreateHash('))
        self.assertEqual(sha256.count('object.resize('), 1)
        self.assertIn('BCryptDestroyHash(hash)', sha256)

    def test_driver_probe_requires_isolated_mode_and_actual_loaded_modules(self):
        source = (ROOT / 'scripts/windows/native_driver_python_probe.py').read_text(encoding='utf-8')
        for fragment in ('sys.flags.isolated', 'sys.flags.dont_write_bytecode', 'sys.version_info',
                         'GetModuleHandleW', 'GetModuleFileNameW', "import _ctypes", 'import _ssl',
                         'import _sqlite3', 'manifest_sha256'):
            self.assertIn(fragment, source)


if __name__ == '__main__':
    unittest.main()
