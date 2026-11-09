#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Prepare pinned, portable Windows test tools in a fresh CI-only root.

The installer does not use the host's Python/CMake as test runtime. It downloads
only fixed HTTPS inputs, validates bytes before extraction/execution, and runs
on a disposable Windows build machine. It is not the target-host launcher.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import urllib.parse
import urllib.request
import zipfile

sys.dont_write_bytecode = True
audit_spec = importlib.util.spec_from_file_location('native_bundle_audit', Path(__file__).with_name('native_bundle_audit.py'))
bundle_audit = importlib.util.module_from_spec(audit_spec)
audit_spec.loader.exec_module(bundle_audit)

MAX_DOWNLOAD = 512 * 1024 * 1024
MAX_EXPANDED = 1024 * 1024 * 1024
CHUNK = 1024 * 1024


class ToolError(Exception):
    """A fixed tool input or extraction check failed."""


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for data in iter(lambda: stream.read(CHUNK), b''):
            digest.update(data)
    return digest.hexdigest()


def validate_pin(pin):
    if not isinstance(pin, dict) or any(not isinstance(pin.get(k), str) or not pin[k] for k in
                                        ('name', 'version', 'file', 'url', 'sha256', 'source')):
        raise ToolError('incomplete pinned tool record')
    if not re.fullmatch(r'[0-9a-f]{64}', pin['sha256']):
        raise ToolError('invalid pinned SHA-256')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', pin['file']):
        raise ToolError('invalid pinned file name')
    for key in ('url', 'source'):
        parsed = urllib.parse.urlsplit(pin[key])
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ToolError('tool URL must be HTTPS without credentials or query')
    if 'bytes' in pin and (not isinstance(pin['bytes'], int) or not 0 < pin['bytes'] <= MAX_DOWNLOAD):
        raise ToolError('invalid pinned byte count')


def download(pin, destination):
    """Stream a single fixed download to a new file and verify its exact bytes."""
    validate_pin(pin)
    destination = Path(destination)
    if destination.exists():
        raise ToolError('refusing to replace a pre-existing download')
    digest = hashlib.sha256()
    size = 0
    request = urllib.request.Request(pin['url'], headers={'User-Agent': 'PlotJuggler-native-test-tools/1'})
    with urllib.request.urlopen(request, timeout=120) as response, destination.open('xb') as stream:
        while True:
            chunk = response.read(CHUNK)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_DOWNLOAD:
                raise ToolError('tool download exceeds size ceiling')
            stream.write(chunk)
            digest.update(chunk)
    if digest.hexdigest() != pin['sha256'] or ('bytes' in pin and size != pin['bytes']):
        raise ToolError(f"downloaded bytes did not match official pin: {pin['name']}")
    return {'name': pin['name'], 'version': pin['version'], 'url': pin['url'],
            'sha256': pin['sha256'], 'bytes': size, 'source': pin['source']}


def extract_zip(archive, destination, prefix=''):
    """Extract an official ZIP without following links or ambiguous Windows names."""
    destination = Path(destination)
    if destination.exists():
        raise ToolError('refusing to replace a pre-existing extraction directory')
    destination.mkdir()
    seen, spellings, total = set(), {}, 0
    with zipfile.ZipFile(archive) as source:
        for info in source.infolist():
            name = info.filename
            if '\\' in name or not name.startswith(prefix):
                raise ToolError('ZIP member has an unexpected prefix or separator')
            name = name[len(prefix):]
            if not name:
                continue
            path = PurePosixPath(name)
            raw_parts = name.rstrip('/').split('/')
            if (path.is_absolute() or any(x in ('', '.', '..') or x.endswith((' ', '.')) or
                                         any(ord(c) < 32 or c in '<>:"|?*' for c in x) or bundle_audit.is_reserved_component(x)
                                         for x in raw_parts)):
                raise ToolError('unsafe ZIP member')
            for index in range(1, len(raw_parts) + 1):
                ancestor = '/'.join(raw_parts[:index])
                folded_ancestor = ancestor.casefold()
                if folded_ancestor in spellings and spellings[folded_ancestor] != ancestor:
                    raise ToolError('case-colliding ZIP parent or member')
                spellings[folded_ancestor] = ancestor
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise ToolError('ZIP symbolic links are not accepted')
            folded = str(path).casefold()
            if folded in seen:
                raise ToolError('case-colliding ZIP member')
            seen.add(folded)
            total += info.file_size
            if total > MAX_EXPANDED:
                raise ToolError('ZIP expands beyond the tool size ceiling')
            target = destination.joinpath(*path.parts)
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with source.open(info) as reader, target.open('xb') as writer:
                    shutil.copyfileobj(reader, writer, CHUNK)


def run_checked(args, *, env=None, timeout=300):
    result = subprocess.run([str(x) for x in args], env=env, capture_output=True, timeout=timeout)
    if result.returncode != 0:
        raise ToolError(f'{Path(args[0]).name} failed with exit code {result.returncode}')
    return result.stdout.decode('utf-8', errors='replace')


def find_one(root, name, parent=None):
    candidates = [p for p in Path(root).rglob(name) if p.is_file() and
                  (parent is None or p.parent.name.casefold() == parent.casefold())]
    if len(candidates) != 1:
        raise ToolError(f'expected exactly one {name} in the verified archive')
    return candidates[0]


def prepare(root, pins_file):
    if sys.platform != 'win32':
        raise ToolError('native test tool preparation requires Windows')
    root = Path(root).absolute()
    if not root.is_dir() or root.is_symlink():
        raise ToolError('CI root must be an existing, non-symlink directory')
    for path in (root, *root.parents):
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ToolError('CI root contains a symlink or reparse point')
    data = json.loads(Path(pins_file).read_text(encoding='utf-8'))
    if not isinstance(data, dict) or data.get('schema') != 1 or not isinstance(data.get('artifacts'), list):
        raise ToolError('invalid tool pin manifest')
    pins = {p.get('name'): p for p in data['artifacts'] if isinstance(p, dict)}
    if set(pins) != {'cmake', 'python', '7zr-bootstrap', '7z-extra', 'ifw'} or len(pins) != len(data['artifacts']):
        raise ToolError('missing, duplicate or unexpected tool pins')
    for pin in pins.values():
        validate_pin(pin)
    download_dir, tools = root / 'd', root / 't'
    if download_dir.exists() or tools.exists():
        raise ToolError('refusing to reuse tool or download directories')
    if shutil.disk_usage(root).free < 2 * 1024 ** 3:
        raise ToolError('insufficient CI free space for pinned tools and extraction')
    download_dir.mkdir(); tools.mkdir()
    records = []
    for pin in data['artifacts']:
        records.append(download(pin, download_dir / pin['file']))
    extract_zip(download_dir / pins['cmake']['file'], tools / 'cmake',
                'cmake-3.31.10-windows-x86_64/')
    extract_zip(download_dir / pins['python']['file'], tools / 'python')
    bootstrap = download_dir / pins['7zr-bootstrap']['file']
    extra_dir = download_dir / 'sevenzip-extra'
    run_checked([bootstrap, 'x', download_dir / pins['7z-extra']['file'], '-o' + str(extra_dir), '-y'])
    sevenzip_source = find_one(extra_dir, '7za.exe', parent='x64')
    license_source = find_one(extra_dir, 'License.txt')
    sevenzip = tools / '7z'; sevenzip.mkdir()
    shutil.copy2(sevenzip_source, sevenzip / '7za.exe')
    shutil.copy2(license_source, sevenzip / 'License.txt')
    ifw = tools / 'ifw'; ifw.mkdir()
    shutil.copy2(download_dir / pins['ifw']['file'], ifw / 'ifw.7z')
    if sha256(ifw / 'ifw.7z') != pins['ifw']['sha256']:
        raise ToolError('IFW archive changed while staging')
    # Full 7-Zip must really extract the exact IFW archive; checking --version
    # alone does not prove format support or the required executable payload.
    ifw_check = download_dir / 'ifw-check'
    run_checked([sevenzip / '7za.exe', 'x', ifw / 'ifw.7z', '-o' + str(ifw_check), '-y'], timeout=600)
    for name in ('binarycreator.exe', 'installerbase.exe', 'repogen.exe'):
        if not (ifw_check / 'bin' / name).is_file():
            raise ToolError(f'verified IFW archive is missing {name}')
    version = run_checked([ifw_check / 'bin/installerbase.exe', '--version'])
    if 'IFW Version: 4.10.0, built with Qt ' not in version:
        raise ToolError('unexpected IFW runtime version')
    notices = sorted(p for p in ifw_check.rglob('*') if p.is_file() and
                     re.search(r'license|licence|notice|copying', p.name, re.I))
    if not notices:
        raise ToolError('the IFW archive contains no identifiable license notice')
    for source in notices:
        target = ifw / 'notices' / source.relative_to(ifw_check)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    # The official embeddable interpreter uses isolated ._pth mode. Add only
    # explicit same-root script locations needed by the registered tests.
    pth = tools / 'python/python312._pth'
    existing = pth.read_text(encoding='utf-8')
    with pth.open('a', encoding='utf-8', newline='\n') as stream:
        if existing and not existing.endswith(('\n', '\r')):
            stream.write('\n')
        for relative in ('s', 's/scripts', 's/tests', 's/packaging/localization'):
            stream.write(str(root / relative) + '\n')
    cmake = tools / 'cmake/bin/cmake.exe'; ctest = tools / 'cmake/bin/ctest.exe'
    python = tools / 'python/python.exe'
    for required in (cmake, ctest, python, tools / 'python/LICENSE.txt',
                     tools / 'cmake/doc/cmake-3.31/Copyright.txt'):
        if not required.is_file():
            raise ToolError(f'missing required pinned tool file: {required.name}')
    system = os.environ.get('SystemRoot')
    if not system:
        raise ToolError('SystemRoot is required to validate the portable tools')
    clean_env = {'SystemRoot': system, 'WINDIR': system,
                 'PATH': os.pathsep.join((str(tools / 'python'), str(Path(system) / 'System32'), system))}
    check = ("import sys,ctypes,csv,hashlib,json,logging,math,pathlib,shutil,signal,socket,ssl,subprocess,tempfile,unittest,winreg,xml.etree.ElementTree,zipfile; "
             "assert sys.version_info[:3] == (3,12,10); print('driver modules OK')")
    run_checked([python, '-I', '-B', '-c', check], env=clean_env)
    if 'ctest version 3.31.10' not in run_checked([ctest, '--version'], env=clean_env).lower():
        raise ToolError('unexpected portable CTest version')
    record = {'schema': 1, 'distributions': records,
              'runtime_files': {'7za_sha256': sha256(sevenzip / '7za.exe'),
                                'ifw_sha256': sha256(ifw / 'ifw.7z'),
                                'python_pth_sha256': sha256(pth)}}
    (tools / 'tool-provenance.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--pins', type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.root, args.pins), ensure_ascii=False))
        return 0
    except (ToolError, OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired, zipfile.BadZipFile) as exc:
        print(f'native tool preparation failed: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
