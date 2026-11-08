#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""All package application launches must use an explicit temporary profile."""
import ast
import importlib.util
from pathlib import Path
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'packaging/localization/verify_package.py'
spec = importlib.util.spec_from_file_location('profile_acceptance', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PackageProfileIsolationTests(unittest.TestCase):
    def test_every_command_kind_gets_an_absolute_temporary_profile(self):
        cases = {
            'version': ['--version'], 'python': ['--selftest-python'],
            'plugins': ['--validate-plugins', 'bundled'],
            'csv-ascii': ['--layout', 'ascii.xml', '--exit-after-layout'],
            'csv-unicode': ['--layout', '中文.xml', '--exit-after-layout'],
            'bin': ['--layout', '真实日志.pj4.xml', '--exit-after-layout'],
            'capture': ['--language', 'zh_TW', '--layout', '真实日志.pj4.xml'],
        }
        with tempfile.TemporaryDirectory(prefix='pj4-profile-test-') as temp:
            work = Path(temp).resolve()
            for name, args in cases.items():
                with self.subTest(name=name):
                    command = module.application_command(Path('app.exe'), work / 'profiles' / name, args)
                    self.assertEqual(command[:2], ['app.exe', '--profile-dir'])
                    self.assertEqual(Path(command[2]), work / 'profiles' / name)
                    self.assertTrue(Path(command[2]).is_absolute())
                    self.assertEqual(command[3:], args)
                    self.assertNotIn('--profile-dir', args)
        self.assertFalse(work.exists())

    def test_profile_override_is_rejected(self):
        for args in [['--profile-dir', 'real-user'], ['--profile-dir=real-user']]:
            with self.assertRaises(AssertionError):
                module.application_command(Path('app.exe'), Path('temporary'), args)

    def test_both_application_spawn_sites_use_profile_builder(self):
        tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
        spawns = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
                  and isinstance(node.func, ast.Attribute) and node.func.attr == 'Popen']
        self.assertEqual(len(spawns), 2, 'Review any new application launch path for isolation')
        for spawn in spawns:
            command = spawn.args[0]
            self.assertIsInstance(command, ast.Call)
            self.assertIsInstance(command.func, ast.Name)
            self.assertEqual(command.func.id, 'application_command')
            profile = ast.unparse(command.args[1])
            self.assertIn('work /', profile)
            self.assertIn("'profiles'", profile)
        text = SOURCE.read_text(encoding='utf-8')
        self.assertIn("with tempfile.TemporaryDirectory(prefix='pj4-package-') as temp:", text)
        self.assertIn('work = Path(temp).resolve()', text)


if __name__ == '__main__':
    unittest.main()
