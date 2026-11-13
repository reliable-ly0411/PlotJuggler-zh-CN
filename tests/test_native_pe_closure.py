# SPDX-License-Identifier: MPL-2.0
"""Synthetic PE descriptors only, not Windows loader or dependency proof."""
import hashlib
import importlib.util
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('native_pe_closure', ROOT / 'scripts/windows/native_pe_closure.py')
pe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pe)


def fixture(normal=('KERNEL32.dll',), delay=('plugin.dll',)):
    data = bytearray(0x800)
    def put(fmt, at, *values): struct.pack_into(fmt, data, at, *values)
    data[:2] = b'MZ'; put('<I', 0x3c, 0x80); data[0x80:0x84] = b'PE\0\0'
    put('<H', 0x84, 0x8664); put('<H', 0x86, 1); put('<H', 0x94, 240)
    opt = 0x98; put('<H', opt, 0x20b); put('<Q', opt + 24, 0x140000000); put('<I', opt + 108, 16)
    section = opt + 240
    put('<IIII', section + 8, 0x600, 0x1000, 0x600, 0x200)
    if normal:
        put('<II', opt + 112 + 8, 0x1000, 20 * (len(normal) + 1))
    if delay:
        put('<II', opt + 112 + 13 * 8, 0x1100, 32 * (len(delay) + 1))
    name_offset = 0x1400
    for index, name in enumerate(normal):
        put('<IIIII', 0x200 + index * 20, 1, 0, 0, name_offset, 0)
        pos = 0x200 + name_offset - 0x1000
        encoded = name.encode('ascii') + b'\0'; data[pos:pos + len(encoded)] = encoded
        name_offset += len(encoded)
    for index, name in enumerate(delay):
        put('<IIIIIIII', 0x300 + index * 32, 1, name_offset, 0, 0, 0, 0, 0, 0)
        pos = 0x200 + name_offset - 0x1000
        encoded = name.encode('ascii') + b'\0'; data[pos:pos + len(encoded)] = encoded
        name_offset += len(encoded)
    return data


class PETests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.exe = self.root / 'test.exe'; self.exe.write_bytes(fixture())

    def test_extracts_normal_and_delay_names_without_execution(self):
        self.assertEqual(pe.imports(self.exe), {'normal': ['KERNEL32.dll'], 'delay': ['plugin.dll']})

    def test_corrupt_signature_table_and_path_names_fail(self):
        for defect in ('signature', 'bounds', 'unterminated', 'unsafe-name'):
            data = fixture()
            if defect == 'signature': data[:2] = b'ZZ'
            elif defect == 'bounds': struct.pack_into('<II', data, 0x98 + 112 + 8, 0x9000, 40)
            elif defect == 'unterminated': data[0x200 + 20:0x200 + 40] = b'\xff' * 20
            else: data[0x600:0x60d] = b'../evil.dll\0\0'
            self.exe.write_bytes(data)
            with self.subTest(defect=defect), self.assertRaises(pe.PEError): pe.imports(self.exe)

    def test_native_audit_rejects_wrong_machine_or_optional_header(self):
        for machine, magic in ((0, 0x20b), (0x14c, 0x20b), (0xaa64, 0x20b), (0x8664, 0x10b)):
            data = fixture(); struct.pack_into('<H', data, 0x84, machine); struct.pack_into('<H', data, 0x98, magic)
            self.exe.write_bytes(data)
            with self.subTest(machine=machine, magic=magic), self.assertRaisesRegex(pe.PEError, 'not AMD64'):
                pe.imports(self.exe, require_x64=True)
        self.exe.write_bytes(fixture())
        self.assertTrue(pe.imports(self.exe, require_x64=True)['normal'])

    def test_closure_requires_declared_host_and_searchable_bundle(self):
        plugin = self.root / 'plugin.dll'; plugin.write_bytes(fixture(normal=(), delay=()))
        def entry(path, dest):
            return {'origin': 'build', 'source': path.name, 'destination': dest,
                    'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        plan = {'origins': {'build': {'root': str(self.root)}},
                'files': [entry(self.exe, 'b/test.exe'), entry(plugin, 'c/runtime/plugin.dll')]}
        result = pe.audit(plan, ['c/runtime'], ['kernel32.dll'])
        self.assertEqual(len(result['files']), 2)
        for runtime, system in ((['different'], ['kernel32.dll']), (['c/runtime'], ['user32.dll'])):
            with self.subTest(runtime=runtime, system=system), self.assertRaises(pe.PEError):
                pe.audit(plan, runtime, system)
        self.exe.write_bytes(b'tampered')
        with self.assertRaises(pe.PEError): pe.audit(plan, ['c/runtime'], ['kernel32.dll'])

    def test_rejects_host_bundle_collision_and_different_duplicate_dll_bytes(self):
        one = self.root / 'one'; two = self.root / 'two'; one.mkdir(); two.mkdir()
        (one / 'plugin.dll').write_bytes(fixture(normal=(), delay=()))
        data = fixture(normal=(), delay=()); data[-1] = 1; (two / 'plugin.dll').write_bytes(data)
        def entry(source, dest):
            return {'origin': 'root', 'source': source, 'destination': dest,
                    'sha256': hashlib.sha256((self.root / source).read_bytes()).hexdigest()}
        plan = {'origins': {'root': {'root': str(self.root)}}, 'files': [entry('test.exe', 'b/test.exe'),
                 entry('one/plugin.dll', 'c/a/plugin.dll'), entry('two/plugin.dll', 'c/b/plugin.dll')]}
        with self.assertRaisesRegex(pe.PEError, 'different DLL'): pe.audit(plan, ['c/a', 'c/b'], ['kernel32.dll'])
        plan['files'].pop()
        with self.assertRaisesRegex(pe.PEError, 'collision'): pe.audit(plan, ['c/a'], ['kernel32.dll', 'plugin.dll'])

    @unittest.skipUnless(shutil.which('objdump'), 'GNU objdump is unavailable')
    def test_existing_real_pip_launchers_match_objdump_normal_imports(self):
        try:
            import pip._vendor.distlib as distlib
        except ImportError:
            self.skipTest('the locally installed pip has no distlib launcher')
        directory = Path(distlib.__file__).parent
        targets = [directory / name for name in ('w32.exe', 'w64.exe') if (directory / name).is_file()]
        if not targets:
            self.skipTest('locally installed pip contains no PE launcher')
        for target in targets:
            with self.subTest(target=target.name):
                result = subprocess.run([shutil.which('objdump'), '-p', str(target)], capture_output=True, text=True)
                if result.returncode:
                    self.skipTest('the local objdump cannot inspect this PE')
                expected = re.findall(r'DLL Name:\s*(\S+)', result.stdout)
                self.assertTrue(expected)
                self.assertEqual(pe.imports(target)['normal'], expected)


if __name__ == '__main__':
    unittest.main()
