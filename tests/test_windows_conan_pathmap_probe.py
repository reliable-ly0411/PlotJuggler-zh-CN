"""Regression checks for fixture generation, not proof of MSVC repeatability."""
import importlib.util
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
probe = importlib.util.module_from_spec(spec); spec.loader.exec_module(probe)


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
