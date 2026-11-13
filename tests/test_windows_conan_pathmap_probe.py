"""Regression checks for fixture generation, not proof of MSVC repeatability."""
import importlib.util
import json
import struct
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('pathmap_probe', ROOT/'scripts/probe_windows_conan_pathmap.py')
probe = importlib.util.module_from_spec(spec)
with patch.object(sys, 'path', [str(ROOT/'scripts')] + sys.path):
    spec.loader.exec_module(probe)


def generated_include(package_folder, build_folder):
    """Execute the exact exported recipe's generate() with captured toolchain."""
    records = []
    class Toolchain:
        def __init__(self, recipe):
            self.variables = {}; records.append(self)
        def generate(self): pass
    mods = {name: ModuleType(name) for name in ('conan','conan.tools','conan.tools.cmake','conan.tools.files')}
    mods['conan'].ConanFile = object
    mods['conan.tools.cmake'].CMakeToolchain = Toolchain
    mods['conan.tools.cmake'].CMake = object
    mods['conan.tools.files'].copy = lambda *args: None
    namespace = {}
    with patch.dict(sys.modules, mods):
        exec(compile(probe.PROBE_RECIPE,'probe/conanfile.py','exec'),namespace)
        recipe = namespace['Probe']()
        recipe.dependencies = {'pjpathmapdep':SimpleNamespace(package_folder=package_folder)}
        recipe.build_folder = str(build_folder)
        recipe.conf = SimpleNamespace(get=lambda *args, **kwargs: ['/experimental:deterministic'])
        recipe.generate()
    return records[0].variables['DEP_INCLUDE']


class FixtureTests(unittest.TestCase):
    def test_ignored_compiler_option_invalidates_experiment(self):
        with tempfile.TemporaryDirectory() as td:
            result=SimpleNamespace(returncode=0,stdout=b'cl : warning D9002: ignoring unknown option',stderr=b'')
            with patch.object(probe.subprocess,'run',return_value=result):
                with self.assertRaisesRegex(RuntimeError,'ignored an unknown option'):
                    probe.run(['cl','/unsupported'],{},Path(td),Path(td)/'log')

    def test_diagnostic_modes_do_not_suppress_sections(self):
        self.assertIn('PRIVATE /Zi /Zf',probe.CMAKE)
        self.assertIn('PRIVATE /Z7',probe.CMAKE)
        self.assertIn('PRIVATE /Brepro',probe.CMAKE)
        self.assertIn('=Z:/pj-probe-objects/main.obj',probe.CMAKE)
        self.assertIn('Unknown diagnostic mode',probe.CMAKE)
        self.assertNotIn('/DEBUG:NONE',probe.CMAKE)
        self.assertNotIn('objcopy',probe.CMAKE)

    def test_windows_backslashes_normalized_in_exported_recipe(self):
        with tempfile.TemporaryDirectory() as td:
            actual=generated_include(r'D:\a\_temp\cache\p\b\package\p',Path(td))
            self.assertEqual(actual,'D:/a/_temp/cache/p/b/package/p/include')
            self.assertNotIn('\\',actual)
            self.assertTrue((Path(td)/'probe-flags.json').is_file())

    def test_forward_slashes_spaces_unicode_retained(self):
        with tempfile.TemporaryDirectory() as td:
            actual=generated_include('D:/a/space 源/package',Path(td))
            self.assertEqual(actual,'D:/a/space 源/package/include')

    def test_partial_success_and_raw_objects_survive_byte_mismatch(self):
        def obj(timestamp):
            header=struct.pack('<HHIIIHH',0x8664,1,timestamp,0,0,0,0)
            section=b'.text\0\0\0'+struct.pack('<IIIIIIHHI',0,0,3,60,0,0,0,0,0x60000020)
            return header+section+b'abc'
        calls=[]
        def fake_one(label,base,dep,recipe,enable,mode):
            calls.append(label)
            folder=base/'fixture-objects'/label;folder.mkdir(parents=True)
            raw=obj(1 if label=='cache-a' else 2)
            for name in ('main.obj','source.obj'):(folder/name).write_bytes(raw)
            return {'binaries':{'probe.dll':'same','probe.exe':'same'},'pe_inspections':{'probe.dll':{'forbidden_paths_found':[],'object_names_found':[]}},'refs':['fixture/1.0#'+'a'*32],
                    'output':['Z:/pj-conan-exact/path']*4 if enable else ['Z:/pj-conan/random']*4,
                    'objects':{name:probe.digest(folder/Path(name).name) for name in ('probe.dir/main.obj','probe.dir/source.obj')},
                    'build_folder':'D:/'+label+'/conan/p/b/'+label+'/b'}
        with tempfile.TemporaryDirectory() as td:
            base=Path(td)/'experiment'
            with patch.object(probe.sys,'platform','win32'), patch.object(probe.sys,'argv',['probe','--work',str(base)]), patch.object(probe,'one',side_effect=fake_one):
                with self.assertRaisesRegex(RuntimeError,'raw C/C[+]'):probe.main()
            summary=json.loads((base/'summary.json').read_text())
            self.assertEqual(calls,['cache-a','cache-b','root-only'])
            self.assertEqual(summary['status'],'failed')
            self.assertTrue(summary['runtime_paths_equal'])
            self.assertTrue(summary['different_cache_suffixes'])
            self.assertTrue(summary['negative_control_rejected'])
            self.assertFalse(summary['raw_objects_equal'])
            self.assertTrue(summary['raw_pe_equal'])
            self.assertTrue(summary['pe_privacy_clean'])
            self.assertTrue((base/'pe-comparison.json').is_file())
            self.assertEqual(set(summary['completed']),set(calls))
            comparison=json.loads((base/'coff-comparison.json').read_text())
            self.assertFalse(comparison['probe.dir/main.obj']['equal'])
            self.assertEqual((base/'fixture-objects/cache-a/main.obj').read_bytes(),obj(1))

    def test_real_cmake_config_accepts_fixed_fixture_rejects_original(self):
        self.assertIsNotNone(shutil.which("cmake"), "real CMake parser required")
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            original=r'D:\a\_temp\cache\p\b\package\p'
            normalized=generated_include(original,root)
            def configure(folder,value):
                source=root/folder;source.mkdir()
                # Same quoting form used for tc.variables by CMakeToolchain.
                (source/'fixture.cmake').write_text(
                    'set(DEP_INCLUDE "'+value+'" CACHE STRING "fixture")\n', encoding='utf-8')
                (source/'CMakeLists.txt').write_text(
                    'cmake_minimum_required(VERSION 3.20)\n'
                    'project(PathmapFixture NONE)\ninclude(fixture.cmake)\n'
                    'if(NOT DEP_INCLUDE STREQUAL "D:/a/_temp/cache/p/b/package/p/include")\n'
                    '  message(FATAL_ERROR "path changed")\nendif()\n',encoding='utf-8')
                return subprocess.run(['cmake','-S',str(source),'-B',str(source/'build')],
                                      capture_output=True,text=True)
            good=configure('fixed',normalized)
            self.assertEqual(good.returncode,0,good.stdout+good.stderr)
            bad=configure('original',original+'/include')
            self.assertNotEqual(bad.returncode,0)
            self.assertIn('Invalid character escape',bad.stdout+bad.stderr)
            self.assertIn(r'\a',bad.stdout+bad.stderr)

if __name__=='__main__': unittest.main()
