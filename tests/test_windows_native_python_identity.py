# SPDX-License-Identifier: MPL-2.0
"""Synthetic identity receipts and source contracts, not a Windows execution."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
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
                         'ensureInterpreter()', 'attr("prefix")', 'import("unicodedata")', 'std::filesystem::equivalent'):
            self.assertIn(required, source)
        self.assertNotIn('3.12.7', source)
        self.assertLess(source.index('#include <windows.h>'), source.index('#include <bcrypt.h>'))
        for required in ('DLLs/unicodedata.pyd', '_pj_expected_unicodedata_sha256',
                         'PJ_NATIVE_EXPECTED_UNICODEDATA_SHA256'):
            self.assertIn(required, cmake)
        for required in ('ASSERT_TRUE(within(unicodedata, home))',
                         'std::filesystem::equivalent(unicodedata, home / "DLLs" / "unicodedata.pyd", error)',
                         'ASSERT_EQ(*unicodedata_sha256, PJ_NATIVE_EXPECTED_UNICODEDATA_SHA256)'):
            self.assertIn(required, source)
        self.assertNotIn('DLLs/math.pyd', cmake)
        self.assertNotIn('PJ_NATIVE_EXPECTED_MATH_SHA256', cmake + source)

    @unittest.skipUnless(shutil.which('cmake'), 'CMake is unavailable')
    def test_cmake_gate_requires_the_real_windows_extension_and_hashes_its_bytes(self):
        # Exercise the source's file/hash gate without configuring native targets.
        cmake = (ROOT / 'pj_scripting/CMakeLists.txt').read_text(encoding='utf-8')
        gate = cmake.split('if(WIN32 AND PJ_NATIVE_BUNDLE_MODE)', 1)[1].split('target_sources(', 1)[0]
        for defect in (None, 'missing-extension', 'math-only', 'not-conan', 'missing-runtime'):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as directory:
                home = Path(directory) / 'runtime'; (home / 'DLLs').mkdir(parents=True)
                runtime = home / 'python312.dll'; runtime.write_bytes(b'locked runtime')
                extension = home / 'DLLs/unicodedata.pyd'; extension.write_bytes(b'locked unicodedata')
                if defect in ('missing-extension', 'math-only'):
                    extension.unlink()
                if defect == 'math-only':
                    (home / 'DLLs/math.pyd').write_bytes(b'not a Windows stdlib extension')
                if defect == 'missing-runtime':
                    runtime.unlink()
                conan = 'FALSE' if defect == 'not-conan' else 'TRUE'
                script = Path(directory) / 'gate.cmake'
                script.write_text(f'set(_pj_python_home_is_conan {conan})\n'
                                  f'set(_pj_python_home_define "{home.as_posix()}")\n' + gate +
                                  '\nmessage(STATUS "dll=${_pj_expected_python_sha256}")\n'
                                  'message(STATUS "extension=${_pj_expected_unicodedata_sha256}")\n',
                                  encoding='utf-8')
                result = subprocess.run([shutil.which('cmake'), '-P', str(script)], capture_output=True,
                                        text=True, encoding='utf-8', timeout=15)
                if defect is None:
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertFalse((home / 'DLLs/math.pyd').exists())
                    for payload in (b'locked runtime', b'locked unicodedata'):
                        self.assertIn(hashlib.sha256(payload).hexdigest(), result.stdout)
                else:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('Native test kit requires its locked Conan CPython runtime', result.stderr)

    def test_runtime_identity_policy_keeps_the_extension_mandatory_and_sources_pinned(self):
        policy = json.loads((ROOT / '.github/windows-native-kit/ci-closure-policy.json').read_text(encoding='utf-8'))
        rule = next(row for row in policy['approved_cases'] if row['case'] ==
                    'pj_scripting_python_tests.WindowsPythonRuntimeIdentity.ConanLibraryAndStdlibAreActuallyLoaded')
        self.assertEqual(rule['dynamic_files'], [
            {'selector': 'locked-cpython', 'artifact': 'runtime-dll', 'role': 'runtime-module'},
            {'selector': 'locked-cpython', 'artifact': 'unicodedata-extension', 'role': 'runtime-module'},
            {'selector': 'locked-cpython', 'artifact': 'stdlib-encodings', 'role': 'data'},
            {'selector': 'locked-cpython', 'artifact': 'stdlib-os', 'role': 'data'},
        ])
        pending = policy.get('approval_status') == 'pending-modern-native-review'
        if pending:
            spec = importlib.util.spec_from_file_location('identity_closure', ROOT / 'scripts/windows/verify_native_ci_closure.py')
            closure = importlib.util.module_from_spec(spec); spec.loader.exec_module(closure)
            with self.assertRaisesRegex(closure.ClosureError, 'pending-modern-native-review'):
                closure.require_reviewed_policy(policy)
        for source in ('pj_scripting/CMakeLists.txt', 'pj_scripting/tests/python_runtime_identity_win_test.cpp'):
            self.assertIn('s/' + source, rule['source_files'])
            # Git checkouts may use CRLF, but reviewed pins describe repository bytes.
            content = (ROOT / source).read_bytes().replace(b'\r\n', b'\n')
            if not pending:
                self.assertEqual(policy['reviewed_source_sha256']['s/' + source], hashlib.sha256(content).hexdigest())
            else:
                self.assertRegex(policy['reviewed_source_sha256']['s/' + source], r'^[0-9a-f]{64}$')

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
