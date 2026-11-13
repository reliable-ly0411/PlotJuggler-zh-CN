# SPDX-License-Identifier: MPL-2.0
"""Opt-in Linux CMake 3.31.10 reproductions, not Windows/MSVC validation.

Set PJ_NATIVE_COMPILER_TEST_CMAKE and PJ_NATIVE_COMPILER_TEST_NINJA to existing
executables. Only tiny synthetic projects are configured and built; no install,
network, repository source build, or generated CMake compiler script execution
by the test harness is needed.
"""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('native_compiler_plan', ROOT / 'scripts/windows/plan_native_stage.py')
planner = importlib.util.module_from_spec(spec); spec.loader.exec_module(planner)


@unittest.skipUnless(os.name != 'nt' and os.environ.get('PJ_NATIVE_COMPILER_TEST_CMAKE'),
                     'opt-in Linux CMake reproduction, not a Windows/MSVC test')
class NativeCompilerCMakeTests(unittest.TestCase):
    def setUp(self):
        self.cmake = os.environ['PJ_NATIVE_COMPILER_TEST_CMAKE']
        self.ninja = os.environ.get('PJ_NATIVE_COMPILER_TEST_NINJA') or shutil.which('ninja')
        self.assertTrue(self.ninja, 'existing Ninja required')
        result = subprocess.run([self.cmake, '--version'], capture_output=True, text=True, check=True)
        self.assertTrue(result.stdout.startswith('cmake version 3.31.10\n'), result.stdout)
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.source = self.root / 'src'; self.source.mkdir()
        (self.source / 'CMakeLists.txt').write_text('cmake_minimum_required(VERSION 3.21)\nproject(compiler_probe LANGUAGES CXX)\nadd_executable(probe main.cpp)\n', encoding='utf-8')
        (self.source / 'main.cpp').write_text('int main() { return 0; }\n', encoding='utf-8')
        self.expected = shutil.which('g++'); self.other = shutil.which('gcc')
        self.assertTrue(self.expected and self.other, 'existing GNU C++ and C drivers required')
        self.client = 'client-native-compiler-main-' + '1' * 32

    def configure(self, name, toolchain=None, pin=None):
        """Return unmodified cache and File API bytes from a real configure/build."""
        build = self.root / name
        query = build / '.cmake/api/v1/query' / self.client / 'toolchains-v1'
        query.parent.mkdir(parents=True); query.write_bytes(b'')
        args = [self.cmake, '-S', str(self.source), '-B', str(build), '-G', 'Ninja Multi-Config',
                '-DCMAKE_MAKE_PROGRAM=' + self.ninja]
        if toolchain:
            path = self.root / (name + '.cmake'); path.write_text(toolchain, encoding='utf-8')
            args.append('-DCMAKE_TOOLCHAIN_FILE=' + str(path))
        if pin: args.append('-DCMAKE_CXX_COMPILER:FILEPATH=' + pin)
        result = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = subprocess.run([self.cmake, '--build', str(build), '--config', 'RelWithDebInfo', '--parallel', '2'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        cache = planner.cache_values((build / 'CMakeCache.txt').read_text(encoding='utf-8'))
        reply = build / '.cmake/api/v1/reply'
        indexes = list(reply.glob('index-*.json')); self.assertEqual(len(indexes), 1)
        index = json.loads(indexes[0].read_text(encoding='utf-8'))
        response = index['reply'][self.client]['toolchains-v1']
        self.assertEqual([obj for obj in index['objects'] if obj['kind'] == 'toolchains'], [response])
        model = json.loads((reply / response['jsonFile']).read_text(encoding='utf-8'))
        cxx = [row['compiler'] for row in model['toolchains'] if row['language'] == 'CXX']
        self.assertEqual(len(cxx), 1)
        return build, cache, cxx[0]

    def test_plain_and_noncache_relative_toolchain_with_and_without_pin(self):
        _, plain, plain_actual = self.configure('plain', pin=self.expected)
        self.assertEqual(plain['CMAKE_CXX_COMPILER'], self.expected)
        self.assertEqual(plain_actual['path'], self.expected)
        ordinary = 'set(CMAKE_CXX_COMPILER g++)\n'
        _, missing, actual = self.configure('normal', ordinary)
        self.assertNotIn('CMAKE_CXX_COMPILER', missing)
        self.assertEqual(actual['path'], self.expected)
        build, pinned, actual = self.configure('pinned', ordinary, self.expected)
        self.assertEqual(pinned['CMAKE_CXX_COMPILER'], self.expected)
        self.assertEqual(actual['path'], self.expected)
        self.assertEqual(actual['id'], 'GNU')
        # Real GNU replies must not be accepted as synthetic or actual MSVC.
        expectation = {'client': self.client, 'compiler': {'path': r'C:\VS\bin\cl.exe'},
                       'query': {'sha256': planner.hashlib.sha256(b'').hexdigest()}}
        with self.assertRaisesRegex(planner.PlanError, 'actual MSVC CXX'):
            planner.inspect_compiler_reply(self.root, r'C:\Tests\n\123456789abc', expectation,
                'pinned/.cmake/api/v1/reply', 'pinned/.cmake/api/v1/query/' + self.client + '/toolchains-v1')

    def test_absolute_toolchain_and_overridden_pin(self):
        _, cache, actual = self.configure('absolute', 'set(CMAKE_CXX_COMPILER "' + self.expected + '")\n', self.expected)
        self.assertEqual(cache['CMAKE_CXX_COMPILER'], actual['path'])
        self.assertEqual(actual['path'], self.expected)
        _, overridden, actual = self.configure('override', 'set(CMAKE_CXX_COMPILER gcc)\n', self.expected)
        self.assertEqual(overridden['CMAKE_CXX_COMPILER'], actual['path'])
        self.assertEqual(actual['path'], self.other)
        self.assertNotEqual(actual['path'], self.expected,
                            'cache-to-actual agreement alone cannot establish the requested compiler')


if __name__ == '__main__':
    unittest.main()
