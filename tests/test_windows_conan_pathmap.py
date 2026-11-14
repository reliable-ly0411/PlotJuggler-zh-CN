import ast
import importlib.util
import pathlib
import subprocess
import sys
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / 'scripts/windows_conan_pathmap.py'
spec = importlib.util.spec_from_file_location('pathmap', SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class ProfileTests(unittest.TestCase):
    def test_flags_and_id(self):
        text = m.render(r'D:\work\project', r'C:\runner\conan')
        lines = dict(line.split('=', 1) for line in text.splitlines() if '=' in line)
        c = ast.literal_eval(lines['tools.build:cflags'])
        self.assertEqual(c, ast.literal_eval(lines['tools.build:cxxflags']))
        self.assertEqual(c, ['/experimental:deterministic', '/pathmap:D:/work/project=Z:/pj-source', '/pathmap:C:/runner/conan=Z:/pj-conan'])
        self.assertEqual(ast.literal_eval(lines['tools.info.package_id:confs']), ['tools.build:cflags', 'tools.build:cxxflags'])
        self.assertNotEqual(text, m.render(r'D:\work\project', r'C:\runner\other'))

    def test_forward_slash_profile_is_perl_safe(self):
        text = m.render(r'D:\work\project', r'C:\runner\conan')
        lines = dict(line.split('=', 1) for line in text.splitlines() if '=' in line)
        flags = ast.literal_eval(lines['tools.build:cflags'])
        self.assertEqual(flags, ['/experimental:deterministic', '/pathmap:D:/work/project=Z:/pj-source', '/pathmap:C:/runner/conan=Z:/pj-conan'])
        self.assertTrue(all('\\' not in flag for flag in flags))

    def test_opt_in_policy_digest_is_in_package_identity(self):
        refs = ['fixture/1.0#' + 'a'*32]
        text = m.render(r'D:\work\project', r'C:\runner\conan', experimental_refs=refs)
        lines = dict(line.split('=', 1) for line in text.splitlines() if '=' in line)
        self.assertEqual(ast.literal_eval(lines['user.plotjuggler:pathmap_refs']), refs)
        self.assertEqual(len(lines['user.plotjuggler:pathmap_policy']), 64)
        confs = ast.literal_eval(lines['tools.info.package_id:confs'])
        self.assertIn('user.plotjuggler:pathmap_policy', confs)
        self.assertIn('user.plotjuggler:pathmap_refs', confs)
        self.assertNotIn('user.plotjuggler', m.render(r'D:\work\project', r'C:\runner\conan'))
        for invalid in ([], [refs[0], refs[0]], [None], 'not-a-list'):
            with self.assertRaises(ValueError):
                m.render(r'D:\work\project', r'C:\runner\conan', experimental_refs=invalid)

    def test_unsafe_roots_rejected(self):
        for source, cache in [(r'D:\work\..\bad', r'C:\cache'), (r'D:\work with space', r'C:\cache'), (r'D:\work', r'd:\WORK\cache'), ('D:relative', r'C:\cache'), (r'D:\work', r'C:\cache&bad'), (r'D:\work', r'D:\WORK')]:
            with self.subTest(source=source, cache=cache), self.assertRaises(ValueError):
                m.render(source, cache)

    def test_explicit_base_profile_and_invalid_base(self):
        with tempfile.TemporaryDirectory() as td:
            base = pathlib.Path(td) / 'host-profile'
            base.write_text('[settings]\nos=Windows\n')
            out = pathlib.Path(td) / 'new-profile'
            args = [sys.executable, str(SCRIPT), '--source', r'D:\work', '--cache', r'C:\cache', '--output', str(out), '--base-profile', str(base)]
            result = subprocess.run(args, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(out.read_text().startswith(f'include({base.resolve().as_posix()})\n'))
            out.unlink()
            base.unlink()
            self.assertNotEqual(subprocess.run(args, capture_output=True).returncode, 0)
            self.assertFalse(out.exists())
            with self.assertRaises(ValueError):
                m.render(r'D:\work', r'C:\cache', 'bad)\n[conf]')

    def test_existing_profile_not_overwritten(self):
        with tempfile.TemporaryDirectory() as td:
            out = pathlib.Path(td) / 'profile'
            out.write_text('untouched')
            result = subprocess.run([sys.executable, str(SCRIPT), '--source', r'D:\work', '--cache', r'C:\cache', '--output', str(out)], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(out.read_text(), 'untouched')

if __name__ == '__main__':
    unittest.main()
