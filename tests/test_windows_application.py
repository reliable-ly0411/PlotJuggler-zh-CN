# SPDX-License-Identifier: MPL-2.0
"""Unit-test PE inspection; native CI separately checks the actual linked binary."""
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('windows_pe', ROOT / 'scripts/verify_windows_application.py')
pe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pe)


class WindowsApplicationTest(unittest.TestCase):
    def fixture(self, subsystem=2, types=(3, 14, 24)):
        data = bytearray(1024)
        data[:2] = b'MZ'
        struct.pack_into('<I', data, 0x3c, 128)
        data[128:132] = b'PE\0\0'
        struct.pack_into('<H', data, 134, 1)
        struct.pack_into('<H', data, 148, 240)
        struct.pack_into('<H', data, 152, 0x20b)
        struct.pack_into('<H', data, 220, subsystem)
        struct.pack_into('<II', data, 280, 0x1000, 100)
        struct.pack_into('<IIII', data, 400, 512, 0x1000, 512, 512)
        struct.pack_into('<HH', data, 524, 0, len(types))
        for index, kind in enumerate(types):
            struct.pack_into('<II', data, 528 + index * 8, kind, 0x80000000)
        return data

    def test_gui_with_icons_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            exe = Path(directory) / 'app.exe'
            exe.write_bytes(self.fixture())
            pe.verify(exe)

    def test_console_and_missing_icons_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            exe = Path(directory) / 'app.exe'
            for image in [self.fixture(3), self.fixture(types=(24,))]:
                exe.write_bytes(image)
                with self.assertRaises(AssertionError):
                    pe.verify(exe)

    def test_icon_has_multiple_sizes(self):
        data = (ROOT / 'resources/windows/plotjuggler.ico').read_bytes()
        reserved, kind, count = struct.unpack_from('<HHH', data)
        self.assertEqual((reserved, kind), (0, 1))
        self.assertGreaterEqual(count, 5)
        sizes = {data[6 + i * 16] or 256 for i in range(count)}
        self.assertTrue({16, 32, 48, 256} <= sizes)


if __name__ == '__main__':
    unittest.main()
