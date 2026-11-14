#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Relocate only verified Jammy Python 3.10 config links after linuxdeploy.

The config tree is retained; the linked ELF remains subject to the full package
inventory and privacy audit. Unknown layouts are errors, not exclusions.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

LAYOUTS = {
    'x86_64-linux-gnu': (62, '718acec35666b1145fb54d9de024f4a55462fd71404b781a0aaf8d428e0f06b1'),
    'aarch64-linux-gnu': (183, '964da948e65ded0cce4de62f6ad1c31c88990c33995122c2b4a7b6c01edf14a9'),
}
NEW_LINK = '../../libpython3.10.so.1.0'
LIBRARY = 'libpython3.10.so.1.0'

def check_plain_path(path, root):
    if not path.is_relative_to(root):
        raise ValueError('Path outside payload')
    for item in (path, *path.parents):
        if item == root:
            break
        if item.is_symlink():
            raise ValueError('Unexpected symlink in library or config parent')

def verify_elf(path, machine):
    header = path.read_bytes()[:20]
    if (len(header) != 20 or header[:7] != b'\x7fELF\x02\x01\x01'
            or int.from_bytes(header[16:18], 'little') != 3
            or int.from_bytes(header[18:20], 'little') != machine):
        raise ValueError('Expected matching ELF64 little-endian shared library')
    dynamic = subprocess.check_output(['readelf', '-d', str(path)], text=True)
    sonames = re.findall(r'\(SONAME\).*?\[([^\]]+)\]', dynamic)
    if sonames != [LIBRARY]:
        raise ValueError('Unexpected Python library SONAME')

def normalize(root):
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Invalid payload root')
    root = root.resolve(strict=True)
    stdlib = root/'usr/lib/python3.10'
    check_plain_path(stdlib, root)
    links = sorted(stdlib.glob('config-*/libpython*.so'))
    if len(links) != 1:
        raise ValueError('Expected exactly one known Python config link')
    link = links[0]
    check_plain_path(link.parent, root)
    triple = link.parent.name.removeprefix('config-3.10-')
    if triple not in LAYOUTS or link.name != 'libpython3.10.so' or not link.is_symlink():
        raise ValueError('Unknown Python config layout')
    old = link.readlink().as_posix()
    machine, expected_hash = LAYOUTS[triple]
    if old != NEW_LINK and (old != f'../../{triple}/libpython3.10.so.1'
                           or hashlib.sha256(old.encode()).hexdigest() != expected_hash):
        raise ValueError('Unknown Python config link target')
    target = root/'usr/lib'/LIBRARY
    check_plain_path(target, root)
    if not target.is_file():
        raise ValueError('Python runtime library missing')
    verify_elf(target, machine)
    target_hash = hashlib.sha256(target.read_bytes()).hexdigest()
    if old != NEW_LINK:
        link.unlink()
        link.symlink_to(NEW_LINK)
    if link.resolve(strict=True) != target:
        raise ValueError('Normalized link does not resolve to verified library')
    return {'schema': 1, 'path': link.relative_to(root).as_posix(),
            'old_target': old, 'new_target': NEW_LINK, 'changed': old != NEW_LINK,
            'library': target.relative_to(root).as_posix(), 'library_sha256': target_hash,
            'machine': machine, 'soname': LIBRARY}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--report', type=Path, required=True)
    a=p.parse_args()
    if a.report.exists():
        raise SystemExit('Refusing to overwrite normalization receipt')
    result=normalize(a.root)
    a.report.parent.mkdir(parents=True, exist_ok=True)
    with a.report.open('x') as f: json.dump(result, f, indent=2)

if __name__ == '__main__': main()
