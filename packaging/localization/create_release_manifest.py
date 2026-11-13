#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Bind the exact original packages to all completed clean acceptance reports."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

from version_map import versions
from verify_package import ACCEPTANCE_LANGUAGES


def sha256(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


# Artifact names are fixed by separate clean jobs; a count cannot prove coverage.
REPORT_IDENTITIES = {
    'zh4-final-Windows/runtime/acceptance.json': ('windows-2022', 'ifw'),
    'zh4-final-Windows-portable/runtime/acceptance.json': ('windows-2022', 'portable'),
    **{f'zh4-final-linux-{index}/{kind}/acceptance.json': (f'ubuntu-{version}', kind)
       for index, version in enumerate(('22.04', '24.04')) for kind in ('appimage', 'deb')},
}


def report_identities(reports, root):
    """Reject missing, duplicate and unexpected format/OS evidence."""
    names = [path.relative_to(root).as_posix() for path in reports]
    assert len(names) == len(set(names)), 'Duplicate acceptance report'
    assert set(names) == set(REPORT_IDENTITIES), 'Require exact six clean format/OS reports'
    return [REPORT_IDENTITIES[name] for name in names]


def verify_checksums(root, files):
    """Require exactly one matching checksum for every original package."""
    expected = {path.resolve(): sha256(path) for path in files}
    found = {}
    for sums in root.rglob('SHA256SUMS-*.txt'):
        for line in sums.read_text(encoding='utf-8').splitlines():
            digest, name = line.split('  ', 1)
            assert Path(name).name == name and '/' not in name and '\\' not in name
            path = (sums.parent / name).resolve()
            assert path in expected and path not in found, 'Unknown or duplicate checksum'
            assert digest == expected[path], 'Original package checksum mismatch'
            found[path] = digest
    assert found == expected, 'Missing original package checksum'


def main():
    source = os.environ['GITHUB_SHA']
    tree = subprocess.check_output(['git', 'rev-parse', 'HEAD^{tree}'], text=True).strip()
    values = dict(line.split('=', 1) for line in Path('versions.env').read_text(encoding='utf-8').splitlines()
                  if line and not line.startswith('#'))
    version = values['PJ_APP_VERSION']
    reports = sorted(Path('reports').rglob('acceptance.json'))
    identities = report_identities(reports, Path('reports'))
    accepted, screenshots = [], []
    for path, (platform, kind) in zip(reports, identities):
        report = json.loads(path.read_text(encoding='utf-8'))
        assert report['status'] == 'automated_checks_passed'
        assert report.get('languages') == list(ACCEPTANCE_LANGUAGES), 'Incomplete language acceptance'
        assert report['release']['source_commit'] == source
        assert report['release']['source_tree'] == tree
        assert report['release']['version'] == version
        assert report['plugin_count'] == (19 if platform == 'windows-2022' else 21)
        if report['plugin_count'] == 19:
            assert report['loaded_plugin_count'] == 19 and report['unavailable_plugins'] == []
        else:
            assert report['loaded_plugin_count'] == 20
            assert len(report['unavailable_plugins']) == 1
            unavailable = report['unavailable_plugins'][0]
            assert unavailable['id'] == 'ros2-topic-subscriber'
            assert unavailable['status'] == 'not_tested_missing_external_dependency'
        accepted.append({'path': path.as_posix(), 'platform': platform, 'format': kind, 'sha256': sha256(path),
                         'plugin_count': report['plugin_count'], 'loaded_plugin_count': report['loaded_plugin_count'],
                         'unavailable_plugins': report['unavailable_plugins'], 'checks': report['checks']})
        for language in ACCEPTANCE_LANGUAGES:
            png = path.parent / f'gui-{language}.png'
            assert png.stat().st_size > 10000
            screenshots.append({'path': png.as_posix(), 'sha256': sha256(png), 'size': png.stat().st_size})
    assert sorted(x['plugin_count'] for x in accepted) == [19, 19, 21, 21, 21, 21]
    expected = {f'PlotJuggler-{version}-Windows-x64-zh-CN.exe',
                f'PlotJuggler-{version}-Windows-x64-portable-zh-CN.zip',
                f'PlotJuggler-{version}-x86_64-zh-CN.AppImage',
                f'plotjuggler4_{versions(version)["deb"]}_amd64-zh-CN.deb'}
    files = sorted(p for p in Path('candidate').rglob('*') if p.suffix in ['.exe', '.zip', '.AppImage', '.deb'])
    assert len(files) == 4 and {p.name for p in files} == expected
    verify_checksums(Path('candidate'), files)
    assets = {p.name: sha256(p) for p in files}
    for path, (platform, kind) in zip(reports, identities):
        if platform == 'windows-2022':
            integrity = json.loads((path.parent / 'package-integrity.json').read_text(encoding='utf-8-sig'))
            name = (f'PlotJuggler-{version}-Windows-x64-portable-zh-CN.zip' if kind == 'portable'
                    else f'PlotJuggler-{version}-Windows-x64-zh-CN.exe')
            assert integrity['format'] == kind and integrity['name'] == name
            assert integrity['before'] == integrity['after'] == assets[name]
    assert len(screenshots) == 18

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
