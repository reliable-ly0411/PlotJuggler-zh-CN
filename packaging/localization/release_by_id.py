#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Address a newly created release by its retained numeric ID, including drafts."""
import argparse
import json
from pathlib import Path
import re
import subprocess

from version_map import versions


def api(endpoint, output, payload=None, binary=False):
    """Retain the actual response once; never retry an uncertain write."""
    command = ['gh', 'api', endpoint]
    if binary:
        command += ['-H', 'Accept: application/octet-stream']
    if payload is not None:
        command += ['--method', 'POST' if endpoint.endswith('/releases') else 'PATCH', '--input', '-']
    with output.open('xb') as stream:
        subprocess.run(command, input=None if payload is None else json.dumps(payload).encode(),
                       stdout=stream, check=True)
    return None if binary else json.loads(output.read_text(encoding='utf-8'))


def identity(release, repo, tag, draft, expected_id=None):
    """Bind every response to the original ID, tag, state and upload destination."""
    number = release.get('id')
    if type(number) is not int or number <= 0 or (expected_id is not None and number != expected_id):
        raise ValueError('Unexpected release ID')
    if (release.get('tag_name') != tag or release.get('draft') is not draft
            or release.get('prerelease') is not versions(tag[1:])['prerelease']):
        raise ValueError('Unexpected release identity or state')
    if release.get('upload_url', '').split('{', 1)[0] != f'https://uploads.github.com/repos/{repo}/releases/{number}/assets':
        raise ValueError('Unexpected upload destination')
    return number


def execute(action, repo, tag, created, output, notes=None, source=None, title=None, inventory=None):
    """Keep transport separate from the workflow's exact-byte acceptance gates."""
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo) or not tag.startswith('v'):
        raise ValueError('Invalid repository or tag')
    policy = versions(tag[1:])
    endpoint = f'repos/{repo}/releases'
    if action == 'create':
        if not re.fullmatch(r'[0-9a-f]{40}', source or ''):
            raise ValueError('Invalid accepted source SHA')
        release = api(endpoint, created, {'tag_name': tag, 'target_commitish': source,
                      'name': title, 'body': notes.read_text(encoding='utf-8'),
                      'draft': True, 'prerelease': policy['prerelease'], 'make_latest': 'false'})
        identity(release, repo, tag, True)
        if release.get('assets') != []:
            raise ValueError('New draft is not empty')
        return
    original = json.loads(created.read_text(encoding='utf-8'))
    number = identity(original, repo, tag, True)
    endpoint += f'/{number}'
    if action in ('draft', 'published', 'publish'):
        payload = None if action != 'publish' else {'draft': False, 'prerelease': policy['prerelease'],
                                                   'make_latest': str(policy['latest']).lower()}
        release = api(endpoint, output, payload)
        identity(release, repo, tag, action == 'draft', number)
    elif action == 'download':
        release = json.loads(inventory.read_text(encoding='utf-8'))
        identity(release, repo, tag, release['draft'], number)
        assets = release['assets']
        ids, names = set(), set()
        for asset in assets:
            aid, name = asset.get('id'), asset.get('name')
            if (type(aid) is not int or aid <= 0 or aid in ids or not isinstance(name, str)
                    or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.+_-]*[A-Za-z0-9]', name) or name in names):
                raise ValueError('Invalid or duplicate asset ID/name')
            ids.add(aid)
            names.add(name)
        output.mkdir()
        for asset in assets:
            api(f'repos/{repo}/releases/assets/{asset["id"]}', output / asset['name'], binary=True)


def main():
    """Expose bounded ID transport operations; the workflow owns publication gates."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['create', 'draft', 'published', 'publish', 'download'])
    parser.add_argument('--repo', required=True)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--created', type=Path, default=Path('draft-created.json'))
    parser.add_argument('--output', type=Path)
    parser.add_argument('--notes', type=Path)
    parser.add_argument('--source')
    parser.add_argument('--title')
    parser.add_argument('--inventory', type=Path)
    execute(**vars(parser.parse_args()))


if __name__ == '__main__':
    main()
