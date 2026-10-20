#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Stage accepted bytes under public filenames and fail closed on upload changes."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil


def sha256(path):
    """Hash without loading a release package into memory."""
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def public_name(name):
    """Map Debian tildes only; do not guess GitHub's general renaming algorithm."""
    result = name.replace('~', '.')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*[A-Za-z0-9]', result):
        raise ValueError(f'Unsupported public asset filename: {name!r}')
    return result


def stage_public_assets(source, destination, assets):
    """Copy only manifest-verified packages; leave candidate names/bytes untouched."""
    names = [asset['name'] for asset in assets]
    if len(names) != len(set(names)) or not names:
        raise ValueError('Candidate manifest has missing or duplicate assets')
    mapped = [public_name(name) for name in names]
    if len(mapped) != len(set(mapped)):
        raise ValueError('Public asset filename collision')
    if {path.name for path in source.iterdir()} != set(names):
        raise ValueError('Candidate directory does not match its manifest')
    result = []
    for asset, name in zip(assets, mapped):
        path = source / asset['name']
        if path.is_symlink() or not path.is_file() or path.suffix not in ['.exe', '.AppImage', '.deb']:
            raise ValueError(f'Not a regular candidate package: {path}')
        if path.stat().st_size != asset['size'] or sha256(path) != asset['sha256']:
            raise ValueError(f'Candidate bytes do not match the acceptance manifest: {path.name}')
        result.append(dict(asset, candidate_name=asset['name'], name=name))
    # An existing directory may contain stale bytes; never overwrite or merge it.
    destination.mkdir()
    for asset in result:
        target = destination / asset['name']
        shutil.copy2(source / asset['candidate_name'], target)
        if target.stat().st_size != asset['size'] or sha256(target) != asset['sha256']:
            raise ValueError(f'Publication copy differs from the accepted bytes: {target.name}')
    return result


def verify_release(directory, release, responses, tag, draft, notes, downloads=None):
    """Require exact names, upload IDs, server digests and optional downloaded bytes."""
    paths = sorted(directory.iterdir())
    if (len(paths) != 4 or sum(path.suffix in ['.exe', '.AppImage', '.deb'] for path in paths) != 3
            or not (directory / 'SHA256SUMS.txt').is_file()):
        raise ValueError('Require three final packages and SHA256SUMS.txt')
    expected = {}
    for path in paths:
        if path.is_symlink() or not path.is_file() or public_name(path.name) != path.name:
            raise ValueError(f'Not a regular, public-safe asset: {path.name}')
        expected[path.name] = {'size': path.stat().st_size, 'digest': 'sha256:' + sha256(path)}
    sums = ''.join(f'{expected[path.name]["digest"][7:]}  {path.name}\n'
                   for path in paths if path.name != 'SHA256SUMS.txt')
    if (directory / 'SHA256SUMS.txt').read_text(encoding='utf-8') != sums:
        raise ValueError('SHA256SUMS.txt does not match the exact public package names/bytes')
    if release['tag_name'] != tag or release['draft'] is not draft or release['prerelease'] is not True:
        raise ValueError('Unexpected release identity or publication state')
    if release['body'].replace('\r\n', '\n').rstrip('\n') != notes.replace('\r\n', '\n').rstrip('\n'):
        raise ValueError('Release notes differ from the reviewed full rendered notes')

    inventories = [('release inventory', release['assets']), ('upload responses', responses)]
    verified = []
    for label, assets in inventories:
        by_name = {asset['name']: asset for asset in assets}
        ids = [asset['id'] for asset in assets]
        if len(assets) != len(expected) or set(by_name) != set(expected) or len(set(ids)) != len(ids):
            raise ValueError(f'{label}: missing, extra, duplicate or renamed assets')
        for name, fingerprint in expected.items():
            asset = by_name[name]
            if asset['state'] != 'uploaded' or not isinstance(asset['id'], int) or asset['id'] <= 0:
                raise ValueError(f'{label}: incomplete upload: {name}')
            if any(asset.get(key) != value for key, value in fingerprint.items()):
                raise ValueError(f'{label}: wrong size or SHA-256 digest: {name}')
        verified.append(by_name)
    if any(verified[0][name]['id'] != verified[1][name]['id'] for name in expected):
        raise ValueError('Release inventory does not contain the original upload IDs')
    if downloads is not None:
        if {path.name for path in downloads.iterdir()} != set(expected):
            raise ValueError('Downloaded asset names do not match the public inventory')
        for name, fingerprint in expected.items():
            path = downloads / name
            if (path.is_symlink() or not path.is_file() or path.stat().st_size != fingerprint['size']
                    or 'sha256:' + sha256(path) != fingerprint['digest']):
                raise ValueError(f'Downloaded bytes differ from the accepted upload: {name}')


def main():
    """Verify captured API evidence without making any network or publish calls."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('release', type=Path)
    parser.add_argument('--upload-responses', type=Path, required=True)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--state', choices=['draft', 'published'], required=True)
    parser.add_argument('--notes', type=Path, required=True)
    parser.add_argument('--downloads', type=Path)
    args = parser.parse_args()
    responses = [json.loads(path.read_text(encoding='utf-8'))
                 for path in sorted(args.upload_responses.glob('*.json'))]
    verify_release(args.directory, json.loads(args.release.read_text(encoding='utf-8')),
                   responses, args.tag, args.state == 'draft',
                   args.notes.read_text(encoding='utf-8'), args.downloads)
    print(f'Verified exact {args.state} asset names, upload IDs, sizes and SHA-256 digests'
          + (' and downloaded bytes' if args.downloads else ''))


if __name__ == '__main__':
    main()
