#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Bind the bundled Windows software renderer to unchanged upstream notices."""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
from urllib.parse import urlsplit

DIRECTORY = 'Windows-Mesa-llvmpipe'
LOCK = 'windows-mesa-notices.json'


def _regular(path):
    """Require package-owned ordinary bytes, not a link to external material."""
    if path.is_symlink() or not path.is_file():
        raise ValueError(f'Not a regular notice or renderer file: {path}')
    for parent in path.parents:
        if parent.is_symlink() or getattr(parent, 'is_junction', lambda: False)():
            raise ValueError(f'Linked notice or renderer parent: {parent}')
    return path


def _matches(path, expected):
    """Check the size and complete digest before copying or trusting a file."""
    data = _regular(path).read_bytes()
    if len(data) != expected['bytes'] or hashlib.sha256(data).hexdigest() != expected['sha256']:
        raise ValueError(f'Windows Mesa bytes differ from reviewed lock: {path.name}')


def read_lock(root):
    """Read a finite, source-reviewed notice set with immutable upstream URLs."""
    lock = json.loads((root / 'packaging/localization' / LOCK).read_text(encoding='utf-8'))
    binary = lock.get('binary', {})
    if lock.get('schema') != 1 or binary.get('path') != 'bin/opengl32sw.dll':
        raise ValueError('Unexpected Windows Mesa lock schema or binary path')
    files = lock.get('files', [])
    if not isinstance(files, list) or any(not isinstance(item, dict) for item in files):
        raise ValueError('Malformed Windows Mesa notice set')
    names = [item.get('file', '') for item in files]
    if (not files or any(not isinstance(name, str) for name in names)):
        raise ValueError('Malformed Windows Mesa notice names')
    if (len({name.casefold() for name in names}) != len(names) or
            any(not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]+', name) for name in names) or
            any(name.casefold() == 'source.json' for name in names)):
        raise ValueError('Missing, duplicate or unsafe Windows Mesa notice names')
    for item in [binary, *files]:
        if (type(item.get('bytes')) is not int or not 0 < item['bytes'] <= 64 * 1024**2 or
                not re.fullmatch(r'[0-9a-f]{64}', str(item.get('sha256', '')))):
            raise ValueError('Invalid Windows Mesa size or digest')
    for item in files:
        url = urlsplit(item.get('url', ''))
        if (url.scheme != 'https' or url.netloc not in {'raw.githubusercontent.com', 'gitlab.freedesktop.org'} or
                url.query or url.fragment or not re.search(r'/[0-9a-f]{40}/', url.path)):
            raise ValueError('Windows Mesa notice source is not an immutable official URL')
    return lock


def component(lock):
    """Record the actual renderer and the complete notice source manifest."""
    return {'component': lock['component'], 'binary': lock['binary'],
            'notices': DIRECTORY, 'source_manifest': DIRECTORY + '/SOURCE.json'}


def collect_windows_mesa_notices(root, qt, licenses):
    """Copy the checked notices without modifying any SDK or application bytes."""
    lock = read_lock(root)
    _matches(qt / lock['binary']['path'], lock['binary'])
    source = root / 'packaging/localization/windows-mesa-notices'
    if source.is_symlink() or not source.is_dir():
        raise ValueError('Missing or linked Windows Mesa notice sources')
    if {path.name for path in source.iterdir()} != {item['file'] for item in lock['files']}:
        raise ValueError('Windows Mesa notice source set differs from reviewed lock')
    for item in lock['files']:
        _matches(source / item['file'], item)
    destination = licenses / DIRECTORY
    destination.mkdir()  # Never silently reuse old or partially copied notices.
    for item in lock['files']:
        shutil.copyfile(source / item['file'], destination / item['file'])
    (destination / 'SOURCE.json').write_text(json.dumps(lock, indent=2) + '\n', encoding='utf-8')
    return component(lock)


def verify_no_bundled_d3dcompiler(prefix):
    """Reject accidental reintroduction anywhere in the complete product stage."""
    for path in prefix.rglob('*'):
        if re.fullmatch(r'd3dcompiler.*\.dll', path.name, flags=re.IGNORECASE):
            raise ValueError(f'Product must use the Windows system D3D compiler: {path}')


def verify_system_d3dcompiler():
    """Clean Windows acceptance must exercise the supported system dependency."""
    version = sys.getwindowsversion()
    if version.major < 10 or version.build < 17763:
        raise ValueError('Qt 6.12 products require Windows 10 1809 (build 17763) or newer')
    # LOAD_LIBRARY_SEARCH_SYSTEM32, matching Qt QSystemLibrary's system-only load.
    # Do not fall back to the working directory, PATH, or an application-local DLL.
    try:
        library = ctypes.WinDLL('d3dcompiler_47.dll', winmode=0x00000800)
        getattr(library, 'D3DCompile')
    except (OSError, AttributeError) as error:
        raise ValueError('System D3DCompiler_47 with D3DCompile is required') from error


def verify_windows_mesa_notices(root, prefix):
    """Independently verify final deployed bytes and notices against source pins."""
    verify_no_bundled_d3dcompiler(prefix)
    lock = read_lock(root)
    _matches(prefix / lock['binary']['path'], lock['binary'])
    licenses = prefix / 'share/licenses'
    directory = licenses / DIRECTORY
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError('Missing or linked Windows Mesa notices')
    expected = {item['file'] for item in lock['files']} | {'SOURCE.json'}
    if {path.name for path in directory.iterdir()} != expected:
        raise ValueError('Windows Mesa notice inventory differs from reviewed lock')
    if json.loads(_regular(directory / 'SOURCE.json').read_text(encoding='utf-8')) != lock:
        raise ValueError('Windows Mesa notice provenance differs from reviewed source')
    for item in lock['files']:
        _matches(directory / item['file'], item)
    manifest = json.loads((licenses / 'DEPENDENCIES.json').read_text(encoding='utf-8'))
    if manifest['components'].count(component(lock)) != 1:
        raise ValueError('Windows Mesa component provenance missing or duplicated')
    for name in expected:
        relative = DIRECTORY + '/' + name
        records = [entry for entry in manifest['files'] if entry['path'] == relative]
        actual = hashlib.sha256((directory / name).read_bytes()).hexdigest()
        if len(records) != 1 or records[0]['sha256'] != actual:
            raise ValueError('Windows Mesa notice missing or mismatched in dependency manifest')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefix', type=Path, required=True)
    args = parser.parse_args()
    verify_windows_mesa_notices(Path(__file__).resolve().parents[2], args.prefix.resolve())
    print('Verified deployed Windows Mesa renderer and pinned original notices')
