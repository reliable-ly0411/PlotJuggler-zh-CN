# SPDX-License-Identifier: MPL-2.0
import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'windows_ifw_payload.py'
spec = importlib.util.spec_from_file_location('windows_ifw_payload', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PayloadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'source'
        (self.source / 'data' / 'nested').mkdir(parents=True)
        (self.source / 'meta').mkdir()
        (self.source / 'meta' / 'package.xml').write_text('<Package/>')
        with zipfile.ZipFile(self.source / 'data' / 'python312.zip', 'w') as z:
            z.writestr('stdlib.py', 'pass')
        (self.source / 'data' / 'nested' / 'x.dll').write_bytes(b'abc')
        self.output = self.root / 'packages'

    def test_nested_zip_is_a_file_and_original_is_unchanged(self):
        original = (self.source / 'data' / 'python312.zip').read_bytes()
        module.prepare(self.source, self.output)
        with zipfile.ZipFile(self.output / module.COMPONENT / 'data' / 'payload.zip') as z:
            self.assertEqual(set(z.namelist()), {'python312.zip', 'nested/x.dll'})
            self.assertEqual(z.read('python312.zip'), original)
            self.assertEqual(z.read('nested/x.dll'), b'abc')
        self.assertEqual((self.source / 'data' / 'python312.zip').read_bytes(), original)
        self.assertEqual((self.output / module.COMPONENT / 'meta' / 'package.xml').read_text(), '<Package/>')

    def test_existing_destination_is_never_overwritten(self):
        self.output.mkdir()
        (self.output / 'sentinel').write_text('keep')
        with self.assertRaises(FileExistsError):
            module.prepare(self.source, self.output)
        self.assertEqual((self.output / 'sentinel').read_text(), 'keep')

    def test_rejects_symlink_and_case_collisions(self):
        link = self.source / 'data' / 'link'
        try:
            link.symlink_to(self.source / 'data' / 'python312.zip')
        except OSError:
            self.skipTest('symlinks unavailable')
        with self.assertRaises(ValueError):
            module.prepare(self.source, self.output)
        link.unlink()
        if (self.source / 'data' / 'NESTED').exists():
            self.skipTest('case-insensitive filesystem')
        (self.source / 'data' / 'NESTED').mkdir()
        (self.source / 'data' / 'NESTED' / 'X.dll').write_text('collision')
        with self.assertRaises(ValueError):
            module.prepare(self.source, self.output)

    def test_dangling_output_link_never_creates_target(self):
        target = self.root / 'missing-target'
        sentinel = self.root / 'sentinel'
        sentinel.write_text('keep')
        try:
            self.output.symlink_to(target, target_is_directory=True)
        except OSError:
            self.skipTest('symlinks unavailable')
        with self.assertRaises(ValueError):
            module.prepare(self.source, self.output)
        self.assertFalse(target.exists())
        self.assertTrue(self.output.is_symlink())
        self.assertEqual(sentinel.read_text(), 'keep')

    def test_rejects_symlink_ancestors_on_both_paths(self):
        alias = self.root / 'alias'
        try:
            alias.symlink_to(self.root, target_is_directory=True)
        except OSError:
            self.skipTest('symlinks unavailable')
        with self.assertRaises(ValueError):
            module.prepare(alias / 'source', self.output)
        with self.assertRaises(ValueError):
            module.prepare(self.source, alias / 'packages')
        self.assertFalse(self.output.exists())

    def test_unicode_spaces_and_empty_file_are_preserved(self):
        data = self.source / 'data'
        name = '中文 文件/空 文件.txt'
        (data / '中文 文件').mkdir()
        (data / name).write_bytes(b'')
        (data / '中文 文件' / '数据.bin').write_bytes(bytes(range(256)))
        module.prepare(self.source, self.output)
        with zipfile.ZipFile(self.output / module.COMPONENT / 'data' / 'payload.zip') as z:
            self.assertEqual(z.read(name), b'')
            self.assertEqual(z.read('中文 文件/数据.bin'), bytes(range(256)))

    def test_rejects_case_insensitive_file_directory_collision(self):
        # This collision can only be created on a case-sensitive filesystem.
        if (self.source / 'data' / 'NESTED').exists():
            self.skipTest('case-insensitive filesystem')
        (self.source / 'data' / 'NESTED').write_bytes(b'file')
        with self.assertRaises(ValueError):
            module.prepare(self.source, self.output)
        self.assertFalse(self.output.exists())

    def test_rejects_nested_destination(self):
        with self.assertRaises(ValueError):
            module.prepare(self.source, self.source / 'data' / 'out')


if __name__ == '__main__':
    unittest.main()
