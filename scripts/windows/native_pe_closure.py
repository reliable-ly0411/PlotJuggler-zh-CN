#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Conservative PE import inventory for an explicit native bundle stage plan.

This never executes a PE and does not prove dynamic LoadLibrary/GetProcAddress,
plugin discovery, sub-process, archive-extraction or host-system trust closure.
Those need reviewed evidence and a clean Windows execution independently.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import mmap
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import sys


class PEError(Exception):
    """Malformed PE or an unresolved import makes static closure uncertain."""


def imports(path, require_x64=False):
    """Read PE imports; a native-kit audit also requires AMD64 and PE32+."""
    with Path(path).open('rb') as f:
        if f.seek(0, 2) < 64:
            raise PEError('PE is too short')
        f.seek(0)
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as data:
            def unpack(fmt, at):
                size = struct.calcsize(fmt)
                if at < 0 or at + size > len(data):
                    raise PEError('PE structure lies outside file')
                return struct.unpack_from(fmt, data, at)
            if data[:2] != b'MZ':
                raise PEError('missing DOS signature')
            pe = unpack('<I', 0x3c)[0]
            if pe + 24 > len(data) or data[pe:pe + 4] != b'PE\0\0':
                raise PEError('missing PE signature')
            machine = unpack('<H', pe + 4)[0]
            sections = unpack('<H', pe + 6)[0]
            optional_size = unpack('<H', pe + 20)[0]
            optional = pe + 24
            magic = unpack('<H', optional)[0]
            if require_x64 and (machine != 0x8664 or magic != 0x20b):
                raise PEError('native kit PE is not AMD64 PE32+: machine=0x%04x magic=0x%04x' % (machine, magic))
            if magic == 0x20b:
                directory_offset, count_offset, base_offset, base_fmt = 112, 108, 24, '<Q'
            elif magic == 0x10b:
                directory_offset, count_offset, base_offset, base_fmt = 96, 92, 28, '<I'
            else:
                raise PEError('unsupported PE optional header')
            if not sections or sections > 96 or optional_size < directory_offset or optional + optional_size > len(data):
                raise PEError('invalid PE section or optional header size')
            image_base = unpack(base_fmt, optional + base_offset)[0]
            count = unpack('<I', optional + count_offset)[0]
            if count > 16 or directory_offset + count * 8 > optional_size:
                raise PEError('invalid PE data-directory count')
            section_table = optional + optional_size
            table = []
            for i in range(sections):
                pos = section_table + i * 40
                virtual_size, va, raw_size, raw = unpack('<IIII', pos + 8)
                if raw + raw_size > len(data):
                    raise PEError('PE section exceeds file')
                table.append((va, max(virtual_size, raw_size), raw, raw_size))
            def offset(rva, size):
                hits = [raw + rva - va for va, length, raw, raw_size in table
                        if va <= rva and rva + size <= va + length and rva - va + size <= raw_size]
                if len(hits) != 1:
                    raise PEError('PE RVA is missing, ambiguous or not backed by file bytes')
                return hits[0]
            def name(rva):
                start = offset(rva, 1)
                available = [raw_size - (rva - va) for va, length, raw, raw_size in table
                             if va <= rva and rva + 1 <= va + length and rva - va + 1 <= raw_size]
                if len(available) != 1:
                    raise PEError('ambiguous import-name section')
                end = data.find(b'\0', start, min(len(data), start + available[0], start + 260))
                if end < 0:
                    raise PEError('unterminated PE import name')
                try:
                    result = data[start:end].decode('ascii')
                except UnicodeDecodeError:
                    raise PEError('non-ASCII PE import name') from None
                if not re.fullmatch(r'[A-Za-z0-9_.+-]+\.dll', result, re.I):
                    raise PEError('PE import is not a simple DLL basename')
                return result
            def directory(index):
                return unpack('<II', optional + directory_offset + index * 8) if index < count else (0, 0)
            def descriptors(index, width, delayed):
                rva, size = directory(index)
                if not rva and not size:
                    return []
                if not rva or size < width or size > 64 * 1024 * 1024:
                    raise PEError('invalid PE import table size')
                start = offset(rva, size)
                names = []
                for pos in range(start, start + size - width + 1, width):
                    words = unpack('<' + 'I' * (width // 4), pos)
                    if not any(words):
                        return names
                    if delayed:
                        flags, dll = words[:2]
                        if flags & ~1:
                            raise PEError('unknown delay-import attributes')
                        if not flags & 1:
                            if dll < image_base:
                                raise PEError('invalid delay-import virtual address')
                            dll -= image_base
                    else:
                        dll = words[3]
                    if not dll:
                        raise PEError('empty DLL name in PE import table')
                    names.append(name(dll))
                raise PEError('unterminated PE import descriptor table')
            return {'normal': descriptors(1, 20, False), 'delay': descriptors(13, 32, True)}


def audit(plan, runtime_dirs, system_names):
    """Resolve static imports against named payload locations and declared OS DLLs."""
    if not isinstance(plan, dict) or not isinstance(plan.get('origins'), dict) or not isinstance(plan.get('files'), list):
        raise PEError('invalid explicit staging plan')
    if not isinstance(runtime_dirs, list) or not runtime_dirs or any(not isinstance(x, str) for x in runtime_dirs):
        raise PEError('explicit runtime directories are required')
    if not isinstance(system_names, list) or not system_names:
        raise PEError('individually declared host-system DLL names are required')
    def safe(value):
        return (isinstance(value, str) and value and '\\' not in value and
                all(x not in ('', '.', '..') and ':' not in x for x in value.split('/')))
    if not all(safe(x) for x in runtime_dirs):
        raise PEError('invalid runtime directory')
    if any(not isinstance(x, str) or not re.fullmatch(r'[A-Za-z0-9_.+-]+\.dll', x, re.I) for x in system_names):
        raise PEError('invalid host-system DLL basename')
    system = {name.casefold() for name in system_names}
    if len(system) != len(system_names):
        raise PEError('duplicate host-system DLL declaration')
    files, by_name = {}, {}
    for item in plan['files']:
        if not isinstance(item, dict) or item.get('origin') not in plan['origins']:
            raise PEError('invalid staging file origin')
        source, target, expected = (item.get(k) for k in ('source', 'destination', 'sha256'))
        if not safe(source) or not safe(target) or not re.fullmatch(r'[0-9a-f]{64}', str(expected)):
            raise PEError('invalid explicit file entry')
        origin = Path(plan['origins'][item['origin']]['root'])
        path = origin.joinpath(*source.split('/'))
        if not origin.is_absolute() or path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(origin.resolve()):
            raise PEError('invalid or external staging source')
        for part in (path, *path.parents):
            info = part.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                raise PEError('staging source contains a link or reparse point')
            if part == origin:
                break
        h = hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                h.update(chunk)
        if h.hexdigest() != expected:
            raise PEError('staging file hash changed: ' + target)
        key = target.casefold()
        if key in files:
            raise PEError('duplicate staging destination')
        files[key] = (target, path, expected)
        if PurePosixPath(target).suffix.casefold() == '.dll':
            by_name.setdefault(PurePosixPath(target).name.casefold(), []).append((target, expected))
    if system & by_name.keys():
        raise PEError('host and bundled DLL name collision requires explicit resolution')
    for name, rows in by_name.items():
        if len({item[1] for item in rows}) > 1:
            raise PEError('different DLL bytes share a basename: ' + name)
    dirs = {x.casefold().rstrip('/') for x in runtime_dirs}
    results = []
    for target, path, expected in files.values():
        if PurePosixPath(target).suffix.casefold() not in ('.dll', '.exe', '.pyd'):
            continue
        lists = imports(path, require_x64=True)
        dependencies = []
        for kind in ('normal', 'delay'):
            for dll in lists[kind]:
                key = dll.casefold()
                if key in system:
                    dependencies.append({'name': dll, 'kind': kind, 'source': 'declared-host-system'})
                    continue
                parent = str(PurePosixPath(target).parent).casefold()
                visible = [name for name, _ in by_name.get(key, [])
                           if str(PurePosixPath(name).parent).casefold() in dirs or
                           (target.casefold().endswith('.exe') and str(PurePosixPath(name).parent).casefold() == parent)]
                if not visible:
                    raise PEError(f'unresolved or non-searchable {kind} DLL {dll} imported by {target}')
                dependencies.append({'name': dll, 'kind': kind, 'source': sorted(visible)})
        results.append({'path': target, 'sha256': expected, 'machine': 'AMD64', 'bitness': 64, 'imports': dependencies})
    if not results:
        raise PEError('no PE payloads were audited')
    return {'schema': 1, 'scope': 'static normal/delay imports only; host trust and dynamic loading are not proven',
            'runtime_dirs': runtime_dirs, 'system_dlls': sorted(system), 'files': results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--runtime-dirs', type=Path, required=True)
    parser.add_argument('--system-dlls', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        values = [json.loads(p.read_text(encoding='utf-8')) for p in (args.plan, args.runtime_dirs, args.system_dlls)]
        result = audit(*values)
        with args.output.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, indent=2, sort_keys=True)
            stream.write('\n')
        return 0
    except (PEError, OSError, ValueError, KeyError, struct.error) as exc:
        print(f'native PE static audit stopped: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
