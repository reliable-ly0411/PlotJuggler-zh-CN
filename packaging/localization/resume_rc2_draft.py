#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Fail-closed recovery for the one empty draft left by publish run 39707711333.

This controller is NOT application source. It cannot create, delete, retag, or
publish a release. The reviewed one-shot workflow performs those allowed upload
and publish operations only after validating the accepted source independently.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess

REPOSITORY = 'reliable-ly0411/PlotJuggler-zh-CN'
SOURCE = '09487081b7dc144c1bfaf674c4a08769e12538ad'
TREE = '8b02ded99c1d29d45eff59ded6181ab154352787'
TAG = 'v4.0.0-zh.1.rc.2'
DRAFT_ID = 420226107
FAILED_RUN = 39707711333
TITLE = 'PlotJuggler 4.0.0-zh.1.rc.2 · 简体中文 + ArduPilot BIN（预发布）'


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def validate_tag(tag):
    require(tag.get('ref') == 'refs/tags/' + TAG, 'Wrong tag')
    require(tag.get('object', {}).get('type') == 'commit', 'Tag must remain the existing lightweight tag')
    require(tag['object'].get('sha') == SOURCE, 'Existing tag points at another source')


def validate_failed_run(run):
    require(run.get('id') == FAILED_RUN and run.get('run_attempt') == 1, 'Wrong failed publication attempt')
    require(run.get('status') == 'completed' and run.get('conclusion') == 'failure', 'Previous publisher is not a terminal failure')
    require(run.get('head_sha') == SOURCE and run.get('path') == '.github/workflows/zh-4x-publish.yml', 'Wrong failed publisher source or recipe')
    require(run.get('repository', {}).get('full_name') == REPOSITORY, 'Wrong repository')


def validate_empty_draft(release, listed, notes):
    require(type(release.get('id')) is int and release['id'] == DRAFT_ID, 'Wrong draft ID')
    require(release.get('tag_name') == TAG, 'Wrong release tag')
    require(release.get('draft') is True and release.get('prerelease') is True, 'Not the pending prerelease draft')
    require('published_at' in release and release['published_at'] is None, 'Draft was already published')
    require(release.get('assets') == [], 'Refuse nonempty or partial draft: inspect before any further upload')
    require(release.get('name') == TITLE, 'Draft title changed')
    require(release.get('author', {}).get('login') == 'github-actions[bot]', 'Unexpected draft creator')
    require(release.get('body') == notes, 'Draft body differs from the frozen rendered source')
    require(release.get('upload_url') == f'https://uploads.github.com/repos/{REPOSITORY}/releases/{DRAFT_ID}/assets{{?name,label}}', 'Unexpected upload destination')
    matches = [item for item in listed if item.get('tag_name') == TAG or item.get('id') == DRAFT_ID]
    require(len(matches) == 1 and matches[0] == release, 'Release list must identify the same unique empty draft')


def download_draft(release, destination):
    require(release.get('id') == DRAFT_ID and release.get('tag_name') == TAG, 'Wrong download release')
    require(release.get('draft') is True and release.get('prerelease') is True, 'Not a draft prerelease')
    assets = release.get('assets', [])
    require(len(assets) == 4, 'Require three packages and checksum file')
    names = [a.get('name', '') for a in assets]
    ids = [a.get('id') for a in assets]
    require(len(set(names)) == 4 and len(set(ids)) == 4, 'Duplicate assets')
    require(all(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*[A-Za-z0-9]', n) for n in names), 'Unsafe asset name')
    require(all(type(i) is int and i > 0 for i in ids), 'Invalid asset ID')
    destination.mkdir()  # No existing downloads and no overwrite.
    for asset in assets:
        with (destination / asset['name']).open('xb') as output:
            subprocess.run(['gh', 'api', '-H', 'Accept: application/octet-stream',
                            f'repos/{REPOSITORY}/releases/assets/{asset["id"]}'],
                           stdout=output, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['empty', 'download'])
    parser.add_argument('release', type=Path)
    parser.add_argument('extra', type=Path, nargs='+')
    args = parser.parse_args()
    release = json.loads(args.release.read_text(encoding='utf-8'))
    if args.mode == 'empty':
        require(len(args.extra) == 4, 'Need release list, rendered notes, tag, failed run')
        listed, notes, tag, failed = args.extra
        validate_tag(json.loads(tag.read_text(encoding='utf-8')))
        validate_failed_run(json.loads(failed.read_text(encoding='utf-8')))
        validate_empty_draft(release, json.loads(listed.read_text(encoding='utf-8')),
                             notes.read_text(encoding='utf-8'))
        print('Verified the unique empty draft, original tag/source, failed attempt and exact frozen body')
    else:
        require(len(args.extra) == 1, 'Need one new download directory')
        download_draft(release, args.extra[0])


if __name__ == '__main__':
    main()
