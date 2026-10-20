#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Bind the exact original packages to all completed clean acceptance reports."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

from version_map import versions


def sha256(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def main():
    source = os.environ['GITHUB_SHA']
    tree = subprocess.check_output(['git', 'rev-parse', 'HEAD^{tree}'], text=True).strip()
    values = dict(line.split('=', 1) for line in Path('versions.env').read_text().splitlines()
                  if line and not line.startswith('#'))
    version = values['PJ_APP_VERSION']
    reports = sorted(Path('reports').rglob('acceptance.json'))
    assert len(reports) == 5, 'Require Windows plus AppImage/DEB on both Ubuntu versions'
    accepted, screenshots = [], []
    for path in reports:
        report = json.loads(path.read_text(encoding='utf-8'))
        assert report['status'] == 'automated_checks_passed'
        assert report['release']['source_commit'] == source
        assert report['release']['source_tree'] == tree
        assert report['release']['version'] == version
        assert report['plugin_count'] in [19, 21]
        if report['plugin_count'] == 19:
            assert report['loaded_plugin_count'] == 19 and report['unavailable_plugins'] == []
        else:
            assert report['loaded_plugin_count'] == 20
            assert len(report['unavailable_plugins']) == 1
            unavailable = report['unavailable_plugins'][0]
            assert unavailable['id'] == 'ros2-topic-subscriber'
            assert unavailable['status'] == 'not_tested_missing_external_dependency'
        accepted.append({'path': path.as_posix(), 'sha256': sha256(path),
                         'plugin_count': report['plugin_count'], 'loaded_plugin_count': report['loaded_plugin_count'],
                         'unavailable_plugins': report['unavailable_plugins'], 'checks': report['checks']})
        for language in ['zh_CN', 'en_US']:
            png = path.parent / f'gui-{language}.png'
            assert png.stat().st_size > 10000
            screenshots.append({'path': png.as_posix(), 'sha256': sha256(png), 'size': png.stat().st_size})
    assert sorted(x['plugin_count'] for x in accepted) == [19, 21, 21, 21, 21]
    expected = {f'PlotJuggler-{version}-Windows-x64-zh-CN.exe',
                f'PlotJuggler-{version}-x86_64-zh-CN.AppImage',
                f'plotjuggler4_{versions(version)["deb"]}_amd64-zh-CN.deb'}
    files = sorted(p for p in Path('candidate').rglob('*') if p.suffix in ['.exe', '.AppImage', '.deb'])
    assert len(files) == 3 and {p.name for p in files} == expected
    for sums in Path('candidate').rglob('SHA256SUMS-*.txt'):
        subprocess.run(['sha256sum', '-c', sums.name], cwd=sums.parent, check=True)
    result = {'schema_version': 1, 'source_commit': source, 'source_tree': tree,
              'workflow_sha': os.environ['GITHUB_WORKFLOW_SHA'], 'run_id': os.environ['GITHUB_RUN_ID'],
              'run_attempt': os.environ['GITHUB_RUN_ATTEMPT'],
              'version': version, 'tag': 'v' + version, 'automated_acceptance': 'passed',
              'visual_review': 'required before creating the version-specific promotion ref',
              'assets': [{'name': p.name, 'size': p.stat().st_size, 'sha256': sha256(p)} for p in files],
              'acceptance_reports': accepted, 'screenshots': screenshots}
    Path('release-manifest.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
