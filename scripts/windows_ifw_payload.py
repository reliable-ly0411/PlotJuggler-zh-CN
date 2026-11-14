#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Prepare an isolated IFW component whose single archive preserves nested ZIPs."""
import argparse
import hashlib
import os
import stat
from pathlib import Path
import shutil
import sys
import zipfile

COMPONENT = 'io.plotjuggler.application'


def reject_link(path):
    """Reject links and Windows reparse points without following them."""
    try:
        info = path.lstat()
    except FileNotFoundError:
        return
    if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
        raise ValueError(f'link or reparse point is not supported: {path}')


def checked_path(path):
    # abspath is lexical: resolve() would follow even a dangling output link.
    path = Path(os.path.abspath(path))
    for part in reversed((path, *path.parents)):
        reject_link(part)
    return path


def inventory(root):
    result = {}
    seen = set()
    for path in sorted(root.rglob('*')):
        reject_link(path)
        name = path.relative_to(root).as_posix()
        key = name.casefold()
        if key in seen:
            raise ValueError(f'case-insensitive name collision: {name}')
        seen.add(key)
        if path.is_dir():
            continue
        if not path.is_file():
            raise ValueError(f'not a regular file: {path}')
        result[name] = (path.stat().st_size, digest(path))
    if not result:
        raise ValueError(f'empty directory: {root}')
    return result


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def prepare(source, destination):
    source, destination = checked_path(source), checked_path(destination)
    if destination.exists():
        raise FileExistsError(f'destination already exists: {destination}')
    source, destination = source.resolve(), destination.resolve()
    if not source.is_dir():
        raise ValueError('source component must be a directory')
    if source == destination or source in destination.parents or destination in source.parents:
        raise ValueError('source and destination must be disjoint')
    data, meta = source / 'data', source / 'meta'
    reject_link(data)
    reject_link(meta)
    if not data.is_dir() or not meta.is_dir():
        raise ValueError('source must contain regular data and meta directories')
    before, meta_before = inventory(data), inventory(meta)
    destination.mkdir(parents=False, exist_ok=False)
    try:
        component = destination / COMPONENT
        (component / 'data').mkdir(parents=True)
        shutil.copytree(meta, component / 'meta')
        if inventory(meta) != meta_before or inventory(component / 'meta') != meta_before:
            raise ValueError('metadata changed during copy')
        archive = component / 'data' / 'payload.zip'
        with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, allowZip64=True) as z:
            for name in before:
                z.write(data / name, name)
        if inventory(data) != before:
            raise ValueError('payload changed during archive creation')
        with zipfile.ZipFile(archive) as z:
            if len(z.infolist()) != len(before) or set(z.namelist()) != set(before):
                raise ValueError('archive member list differs from source')
            for name, (size, expected) in before.items():
                h = hashlib.sha256()
                count = 0
                with z.open(name) as stream:
                    for block in iter(lambda: stream.read(1024 * 1024), b''):
                        count += len(block)
                        h.update(block)
                if count != size or h.hexdigest() != expected:
                    raise ValueError(f'archive content differs: {name}')
        print(f'Validated {len(before)} payload files in {archive}')
    except BaseException:
        shutil.rmtree(destination)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--component', required=True)
    parser.add_argument('--output', required=True, help='new package root; must not exist')
    args = parser.parse_args()
    try:
        prepare(args.component, args.output)
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f'IFW payload preparation failed: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
