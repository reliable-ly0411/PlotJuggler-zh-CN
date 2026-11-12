# SPDX-License-Identifier: MPL-2.0
"""Regression checks for evidence completeness in staged license inventories."""
import importlib.util
import json
from pathlib import Path, PurePosixPath
import subprocess
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NoticeInventoryTests(unittest.TestCase):
    def test_wasmer_attribution_copied_and_missing_is_error(self):
        module = load('stage_fork_notices')
        with tempfile.TemporaryDirectory() as tmp:
            root, dest = Path(tmp) / 'root', Path(tmp) / 'out'
            source = root / 'build/_deps/wasmer-src'
            source.mkdir(parents=True)
            (source / 'LICENSE').write_text('license')
            with self.assertRaisesRegex(RuntimeError, 'ATTRIBUTIONS'):
                module.stage_downloaded_notice(root, dest, 'wasmer')
            self.assertFalse((dest / 'Licenses/Downloaded/wasmer/LICENSE').exists())
            (source / 'ATTRIBUTIONS').write_text('original attribution')
            module.stage_downloaded_notice(root, dest, 'wasmer')
            self.assertEqual((dest / 'Licenses/Downloaded/wasmer/ATTRIBUTIONS').read_text(),
                             'original attribution')

    def test_dpkg_alias_and_architecture_ambiguity(self):
        module = load('stage_fork_notices')
        def run(command, **kwargs):
            if command[1] == '-S':
                output = 'libexample:amd64: /usr/lib/example.so\n' if command[2] == '/usr/lib/example.so' else ''
                return subprocess.CompletedProcess(command, 0 if output else 1, output, '')
            return subprocess.CompletedProcess(command, 0,
                'libexample:amd64\t1.0\nlibexample:i386\t1.0\n', '')
        with patch.object(module.subprocess, 'run', side_effect=run), \
             patch.object(module.Path, 'resolve', return_value=PurePosixPath('/usr/lib/example.so')):
            self.assertEqual(module.query_dpkg_owner('/lib/example.so'), 'libexample:amd64')
            self.assertIsNone(module.query_dpkg_version('libexample:amd64'))
        with patch.object(module.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0,
                          'libexample:amd64\t1.0\n', '')):
            self.assertEqual(module.query_dpkg_version('libexample:amd64'), '1.0')

    def test_unowned_and_missing_dependencies_are_recorded(self):
        module = load('stage_fork_notices')
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            (dest / 'app').write_bytes(b'\x7fELFfake')
            def run(command, **kwargs):
                if command[0] == 'ldd':
                    return subprocess.CompletedProcess(command, 0, 'libunknown.so => /private/libunknown.so (0x1)\nlibabsent.so => not found\n', '')
                return subprocess.CompletedProcess(command, 1, '', '')
            with patch.object(module.subprocess, 'run', side_effect=run), \
                 patch.object(module.shutil, 'copytree'):
                module.stage_distro_notices(dest)
            report = json.loads((dest / 'Licenses/Distro/manifest.json').read_text())
            self.assertEqual(report['status'], 'incomplete')
            self.assertEqual(report['unowned_library_names'], ['libunknown.so'])
            self.assertEqual(report['unresolved_library_names'], ['libabsent.so'])
            self.assertNotIn('/private/', json.dumps(report))

    def test_arrow_notice_is_version_scoped_and_not_autoapproved(self):
        module = load('conan_license_deployer')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dependencies = []
            for version, notice in [('21.0.0', False), ('26.0.1', True)]:
                folder = root / version
                (folder / 'licenses').mkdir(parents=True)
                (folder / 'licenses/LICENSE').write_text('license')
                if notice:
                    (folder / 'licenses/NOTICE.txt').write_text('notice')
                ref = type('Ref', (), {'name': 'arrow', 'version': version,
                                       '__str__': lambda self: 'arrow/' + self.version})()
                dependencies.append(types.SimpleNamespace(ref=ref, package_folder=str(folder)))
            host = {d.ref.version: d for d in dependencies}
            graph = types.SimpleNamespace(root=types.SimpleNamespace(conanfile=types.SimpleNamespace(
                dependencies=types.SimpleNamespace(host=host))))
            module.deploy(graph, root / 'out')
            records = json.loads((root / 'out/Conan/manifest.json').read_text())['dependencies']
            self.assertEqual([r['notice_evidence']['status'] for r in records], ['missing', 'packaged-unverified'])
            self.assertEqual(records[0]['notice_evidence']['paths'], [])
            self.assertEqual(records[1]['notice_evidence']['paths'], ['arrow-26.0.1/NOTICE.txt'])


if __name__ == '__main__':
    unittest.main()
