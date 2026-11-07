#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Check the actual Windows PE GUI subsystem, resources and redirected CLI."""
import argparse
import ctypes
from ctypes import wintypes
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


def version_strings(path):
    """Read the application resource's English/Unicode version strings on Windows."""
    api = ctypes.WinDLL('version', use_last_error=True)
    api.GetFileVersionInfoSizeW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(wintypes.DWORD)]
    api.GetFileVersionInfoSizeW.restype = wintypes.DWORD
    api.GetFileVersionInfoW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID]
    api.GetFileVersionInfoW.restype = wintypes.BOOL
    api.VerQueryValueW.argtypes = [wintypes.LPCVOID, wintypes.LPCWSTR,
                                 ctypes.POINTER(wintypes.LPVOID), ctypes.POINTER(wintypes.UINT)]
    api.VerQueryValueW.restype = wintypes.BOOL
    filename = str(Path(path).resolve())
    size = api.GetFileVersionInfoSizeW(filename, None)
    if not size:
        raise ctypes.WinError(ctypes.get_last_error())
    data = ctypes.create_string_buffer(size)
    if not api.GetFileVersionInfoW(filename, 0, size, data):
        raise ctypes.WinError(ctypes.get_last_error())
    result = {}
    for key in ('FileVersion', 'ProductVersion'):
        value = wintypes.LPVOID()
        length = wintypes.UINT()
        if not api.VerQueryValueW(data, '\\StringFileInfo\\040904B0\\' + key,
                                 ctypes.byref(value), ctypes.byref(length)):
            raise AssertionError(f'missing VERSIONINFO string: {key}')
        result[key] = ctypes.wstring_at(value, length.value).rstrip('\0')
    return result


def verify(path, runtime=False, expected_version=None):
    subsystem, resource_types = inspect_pe(path)
    assert subsystem == 2, f'expected WINDOWS_GUI (2), got {subsystem}'
    assert {3, 14} <= resource_types, f'missing RT_ICON / RT_GROUP_ICON: {resource_types}'
    assert 16 in resource_types, f'missing RT_VERSION: {resource_types}'
    if expected_version is not None:
        values = version_strings(path)
        for key in ('FileVersion', 'ProductVersion'):
            assert values[key] == expected_version, (key, values[key], expected_version)
    if runtime:
        for option, expected in [('--version', b'PlotJuggler4 '), ('--help', b'--language')]:
            result = subprocess.run([str(Path(path).resolve()), option], capture_output=True, timeout=60)
            assert result.returncode == 0, (option, result.returncode, result.stderr)
            assert expected in result.stdout, (option, result.stdout, result.stderr)
    print('Windows executable bytes:', Path(path).stat().st_size)
    print('Windows PE: GUI subsystem, embedded icon groups and version; redirected CLI:', runtime)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--runtime', action='store_true')
    parser.add_argument('--expected-version')
    args = parser.parse_args()
    verify(args.executable, args.runtime, args.expected_version)
