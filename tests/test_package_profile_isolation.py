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
        self.assertIn('with acceptance_workspace(work_dir) as work:', text)


class AcceptanceWorkspaceTests(unittest.TestCase):
    def test_default_workspace_is_removed_on_success_and_failure(self):
        for fail in (False, True):
            try:
                with module.acceptance_workspace() as work:
                    self.assertTrue(work.is_absolute())
                    (work / 'evidence').write_bytes(b'CI scratch')
                    if fail:
                        raise RuntimeError('synthetic acceptance failure')
            except RuntimeError:
                self.assertTrue(fail)
            self.assertFalse(work.exists())

    def test_explicit_workspace_is_retained_on_success_and_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            for existing in (False, True):
                for fail in (False, True):
                    path = Path(temp).resolve() / f'case-{existing}-{fail}'
                    if existing:
                        path.mkdir()
                    try:
                        with module.acceptance_workspace(path) as work:
                            self.assertEqual(work, path)
                            (work / 'evidence').write_bytes(b'preserve inputs and profiles')
                            if fail:
                                raise RuntimeError('synthetic acceptance failure')
                    except RuntimeError:
                        self.assertTrue(fail)
                    self.assertEqual((path / 'evidence').read_bytes(), b'preserve inputs and profiles')

    def test_unsuitable_workspaces_fail_without_mutation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            occupied = root / 'occupied'
            occupied.mkdir()
            evidence = occupied / 'evidence'
            evidence.write_bytes(b'untouched')
            file = root / 'file'
            file.write_bytes(b'untouched file')
            paths = [Path('relative'), Path(''), Path(root.anchor), occupied, file,
                     root / 'absent-parent' / 'child', root / '..' / 'traversal']
            for path in paths:
                with self.subTest(path=path), self.assertRaises(ValueError):
                    with module.acceptance_workspace(path):
                        self.fail('Invalid workspace accepted')
            self.assertEqual(evidence.read_bytes(), b'untouched')
            self.assertEqual(file.read_bytes(), b'untouched file')
            self.assertFalse((root / 'absent-parent').exists())

    def test_symlink_workspace_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            target = root / 'target'
            target.mkdir()
            link = root / 'link'
            try:
                link.symlink_to(target, target_is_directory=True)
            except OSError:
                self.skipTest('Creating directory symlinks is not permitted on this runner')
            for path in (link, link / 'child'):
                with self.assertRaises(ValueError):
                    with module.acceptance_workspace(path):
                        self.fail('Symbolic-link workspace accepted')
            self.assertEqual(list(target.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
