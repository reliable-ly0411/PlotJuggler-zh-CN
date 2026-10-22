#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Check the actual Windows PE GUI subsystem, embedded icons and redirected CLI."""
import argparse
from pathlib import Path
import struct
import subprocess


def inspect_pe(path):
    data = Path(path).read_bytes()
    assert data[:2] == b'MZ', 'not a DOS/PE image'
    pe = struct.unpack_from('<I', data, 0x3c)[0]
    assert data[pe:pe + 4] == b'PE\0\0', 'not a PE image'
    count = struct.unpack_from('<H', data, pe + 6)[0]
    optional_size = struct.unpack_from('<H', data, pe + 20)[0]
    optional = pe + 24
    magic = struct.unpack_from('<H', data, optional)[0]
    assert magic in (0x10b, 0x20b)
    subsystem = struct.unpack_from('<H', data, optional + 68)[0]
    dirs = optional + (112 if magic == 0x20b else 96)
    resource_rva, resource_size = struct.unpack_from('<II', data, dirs + 16)
    sections = optional + optional_size

    def offset(rva):
        for index in range(count):
            section = sections + 40 * index
            size, address, raw_size, raw = struct.unpack_from('<IIII', data, section + 8)
            if address <= rva < address + max(size, raw_size):
                return raw + rva - address
        raise AssertionError('resource RVA has no section')

    types = set()
    if resource_rva and resource_size:
        root = offset(resource_rva)
        named, ids = struct.unpack_from('<HH', data, root + 12)
        for index in range(named + ids):
            name, child = struct.unpack_from('<II', data, root + 16 + index * 8)
            if not name & 0x80000000:
                types.add(name)
    return subsystem, types


def verify(path, runtime=False):
    subsystem, resource_types = inspect_pe(path)
    assert subsystem == 2, f'expected WINDOWS_GUI (2), got {subsystem}'
    assert {3, 14} <= resource_types, f'missing RT_ICON / RT_GROUP_ICON: {resource_types}'
    if runtime:
        for option, expected in [('--version', b'PlotJuggler4 '), ('--help', b'--language')]:
            result = subprocess.run([str(Path(path).resolve()), option], capture_output=True, timeout=60)
            assert result.returncode == 0, (option, result.returncode, result.stderr)
            assert expected in result.stdout, (option, result.stdout, result.stderr)
    print('Windows PE: GUI subsystem, embedded icon groups; redirected CLI:', runtime)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--runtime', action='store_true')
    args = parser.parse_args()
    verify(args.executable, args.runtime)
