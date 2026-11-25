#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Identify the actual isolated driver CPython and native modules, not the app CPython."""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import sys


class ProbeError(Exception):
    """The driver runtime differs from its authenticated same-root distribution."""


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def bound_file(root, entries, relative, actual):
    row = entries.get(relative.casefold())
    target = (root / relative).resolve(strict=True)
    if (not row or row['path'] != relative or Path(actual).resolve(strict=True) != target or
            not re.fullmatch(r'[0-9a-f]{64}', str(row.get('sha256', ''))) or digest(target) != row['sha256']):
        raise ProbeError('loaded or referenced file differs from the manifest: ' + relative)
    return {'path': relative, 'sha256': row['sha256']}


def module_path(kernel, name):
    handle = kernel.GetModuleHandleW(name)
    if not handle:
        raise ProbeError('required driver native library is not loaded: ' + name)
    text = ctypes.create_unicode_buffer(32768)
    length = kernel.GetModuleFileNameW(handle, text, len(text))
    if not length or length >= len(text):
        raise ProbeError('cannot identify the actual loaded driver library: ' + name)
    return text.value


def run(root, manifest_path, manifest_sha256):
    if sys.platform != 'win32' or not sys.flags.isolated or not sys.flags.dont_write_bytecode:
        raise ProbeError('the verified Windows driver must be started with -I -B')
    root = Path(root).resolve(strict=True)
    manifest_path = Path(manifest_path).resolve(strict=True)
    if manifest_path != root / '_bundle/manifest.json' or digest(manifest_path) != manifest_sha256:
        raise ProbeError('the driver manifest does not match its independently supplied digest')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    files = manifest.get('files') if isinstance(manifest, dict) else None
    if not isinstance(files, list) or any(not isinstance(item, dict) or not isinstance(item.get('path'), str) for item in files):
        raise ProbeError('driver manifest is malformed')
    entries = {item['path'].casefold(): item for item in files}
    if len(entries) != len(files):
        raise ProbeError('driver manifest has duplicate paths')
    pins_file = root / 's/.github/windows-native-kit/tool-pins.json'
    pins_row = bound_file(root, entries, 's/.github/windows-native-kit/tool-pins.json', pins_file)
    pins = json.loads(pins_file.read_text(encoding='utf-8'))
    candidates = [item for item in pins.get('artifacts', []) if isinstance(item, dict) and item.get('name') == 'python']
    if len(candidates) != 1 or not re.fullmatch(r'\d+\.\d+\.\d+', str(candidates[0].get('version', ''))):
        raise ProbeError('the official driver version is not uniquely pinned')
    version = tuple(int(x) for x in candidates[0]['version'].split('.'))
    if sys.version_info[:3] != version:
        raise ProbeError('actual driver version differs from its official pin')
    python_dir = (root / 't/python').resolve(strict=True)
    executable = bound_file(root, entries, 't/python/python.exe', sys.executable)
    if Path(sys.prefix).resolve(strict=True) != python_dir:
        raise ProbeError('driver sys.prefix is not its verified embedded directory')
    expected_paths = [python_dir / 'python312.zip', python_dir, root / 's', root / 's/scripts',
                      root / 's/tests', root / 's/packaging/localization']
    if [Path(value).resolve(strict=True) for value in sys.path] != [value.resolve(strict=True) for value in expected_paths]:
        raise ProbeError('driver import path differs from the authenticated isolated configuration')
    stdlib = bound_file(root, entries, 't/python/python312.zip', python_dir / 'python312.zip')
    # These imports exercise the native ffi, TLS/crypto and SQLite extensions;
    # they make no network connection or database and write no user data.
    import _ctypes
    import _ssl
    import _sqlite3
    native = [bound_file(root, entries, 't/python/' + name + '.pyd', module.__file__)
              for name, module in (('_ctypes', _ctypes), ('_ssl', _ssl), ('_sqlite3', _sqlite3))]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
    kernel.GetModuleHandleW.restype = ctypes.c_void_p
    kernel.GetModuleFileNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint32]
    kernel.GetModuleFileNameW.restype = ctypes.c_uint32
    dlls = [item['path'].rsplit('/', 1)[-1] for item in files
            if item['path'].startswith('t/python/') and item['path'].lower().endswith('.dll')]
    required = []
    for pattern in (r'python312\.dll', r'libcrypto[^/]*\.dll', r'libssl[^/]*\.dll',
                    r'libffi[^/]*\.dll', r'sqlite3\.dll'):
        matches = [name for name in dlls if re.fullmatch(pattern, name, re.IGNORECASE)]
        if len(matches) != 1:
            raise ProbeError('official Python distribution has no unique expected library: ' + pattern)
        required.append(matches[0])
    loaded = [bound_file(root, entries, 't/python/' + name, module_path(kernel, name)) for name in required]
    return {'schema': 1, 'scope': 'isolated-driver-python', 'pid': os.getpid(), 'version': candidates[0]['version'],
            'executable': executable, 'prefix': str(python_dir), 'stdlib': stdlib, 'modules': native,
            'loaded_dlls': loaded, 'tool_pins': pins_row, 'manifest_sha256': manifest_sha256}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--manifest-sha256', required=True)
    args = parser.parse_args()
    try:
        if not re.fullmatch(r'[0-9a-f]{64}', args.manifest_sha256):
            raise ProbeError('manifest digest is invalid')
        print(json.dumps(run(args.root, args.manifest, args.manifest_sha256), ensure_ascii=False, sort_keys=True))
        return 0
    except (ProbeError, OSError, ValueError, KeyError, TypeError, ImportError) as exc:
        print('driver Python identity probe failed: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
