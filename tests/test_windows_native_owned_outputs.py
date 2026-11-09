# SPDX-License-Identifier: MPL-2.0
"""Synthetic source/CTest registration checks, not a Windows native run."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class OwnedOutputSourceTests(unittest.TestCase):
    def test_profile_helpers_are_identical_and_fail_closed(self):
        profile = ROOT / 'pj_app/tests/profile'
        marker = '#ifdef PJ_NATIVE_BUNDLE_MODE\n// This root'
        a = (profile / 'app_profile_test.cpp').read_text(encoding='utf-8')
        b = (profile / 'app_profile_services_test.cpp').read_text(encoding='utf-8')
        helpers = [a[a.index(marker):a.index('\n#endif\n\nQByteArray', a.index(marker))],
                   b[b.index(marker):b.index('\n#endif\n\nQString asQString', b.index(marker))]]
        self.assertEqual(*helpers)
        for part in ('PJ_NATIVE_OUTPUT_ROOT', 'PJ_NATIVE_BUNDLE_ROOT', 'profile-tests',
                     'isSymLink()', 'isJunction()', 'canonicalFilePath()',
                     'qEnvironmentVariable("TEMP")', 'qEnvironmentVariable("TMP")',
                     'QDir::tempPath()', '^(?:run|ci)-[0-9a-f]{32}$'):
            self.assertIn(part, helpers[0])
        for source in (a, b):
            self.assertIn('run.setAutoRemove(false)', source)
            self.assertIn('nativeBundleFixtureRoot(', source)

    def test_csv_has_separate_opt_in_and_preserves_default_evidence_contract(self):
        source = (ROOT / 'pj_app/CMakeLists.txt').read_text(encoding='utf-8')
        self.assertIn('option(PJ_NATIVE_BUNDLE_MODE', source)
        self.assertIn('set(csv_test_environment "PLOTJUGGLER_UI_LANGUAGE=${language};QT_QPA_PLATFORM=offscreen")', source)
        self.assertIn('PJ_CSV_DIAGNOSTIC_DIR=${CMAKE_BINARY_DIR}/csv-runtime-diagnostics', source)
        self.assertIn('foreach(language IN ITEMS zh_CN zh_TW en_US)', source)
        cases = (ROOT / 'pj_app/tests/csv_runtime_language_test.cpp').read_text(encoding='utf-8')
        self.assertEqual(cases.count('TEST_F(CsvRuntimeFileLoader,'), 7)

    @unittest.skipUnless(shutil.which('cmake') and shutil.which('ctest') and shutil.which('ninja'),
                         'CMake, CTest and Ninja are required')
    def test_ctest_registration_default_unchanged_and_opt_in_inherits_temp(self):
        # Minimal imported Qt targets permit configure/discovery without claiming
        # a Qt build or executing any test executable.
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp); fake = base / 'fake/lib/cmake/Qt6'; fake.mkdir(parents=True)
            (fake / 'Qt6ConfigVersion.cmake').write_text('set(PACKAGE_VERSION "6.12.0")\nset(PACKAGE_VERSION_COMPATIBLE TRUE)\nset(PACKAGE_VERSION_EXACT TRUE)\n', encoding='utf-8')
            (fake / 'Qt6Config.cmake').write_text('''set(Qt6_FOUND TRUE)
set(Qt6_VERSION 6.12.0)
set(Qt6Core_VERSION_MAJOR 6)
set(Qt6Core_VERSION_MINOR 12)
foreach(c Core Widgets Network)
 set(Qt6${c}_FOUND TRUE)
 if(NOT TARGET Qt6::${c})
  add_library(Qt6::${c} INTERFACE IMPORTED)
 endif()
endforeach()
if(NOT TARGET Qt6::moc)
 add_executable(Qt6::moc IMPORTED)
 set_target_properties(Qt6::moc PROPERTIES IMPORTED_LOCATION "${CMAKE_COMMAND}")
endif()
''', encoding='utf-8')
            for mode in ('OFF', 'ON'):
                build = base / mode
                subprocess.run(['cmake', '-S', str(ROOT / 'pj_app/tests/profile'), '-B', str(build), '-G', 'Ninja',
                                '-DCMAKE_PREFIX_PATH=' + str(base / 'fake'), '-DPJ_NATIVE_BUNDLE_MODE=' + mode],
                               check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                (build / ('app_profile_test.exe' if os.name == 'nt' else 'app_profile_test')).write_bytes(b'')
                doc = json.loads(subprocess.check_output(['ctest', '--test-dir', str(build), '--show-only=json-v1']))
                tests = doc['tests']
                self.assertGreaterEqual(len(tests), 13)
                for case in tests:
                    props = {p['name']: p['value'] for p in case['properties']}
                    env = props['ENVIRONMENT']
                    self.assertIn('QT_QPA_PLATFORM=offscreen', env)
                    self.assertEqual(props['TIMEOUT'], 30.0)
                    self.assertEqual(props['SKIP_RETURN_CODE'], 77)
                    keys = {item.split('=', 1)[0] for item in env}
                    override = {'TEMP', 'TMP', 'TMPDIR', 'XDG_CACHE_HOME'}
                    if mode == 'ON':
                        self.assertFalse(keys & override)
                        self.assertEqual(case['command'][-1], '--native-bundle-owned')
                    else:
                        self.assertTrue(override <= keys)
                        self.assertEqual(Path(case['command'][-1]), build / 'test-data')


if __name__ == '__main__':
    unittest.main()
