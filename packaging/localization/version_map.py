#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Map the fork's SemVer to ordered platform package versions."""
import argparse
import json
import re


def versions(value):
    """IFW is numeric; dpkg uses tilde to keep each prerelease below its final."""
    core_pattern = r'(4\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*))'
    stable = re.fullmatch(core_pattern + r'\+zh\.([1-9][0-9]*)', value)
    if stable:
        core, revision = stable.groups()
        return {'semver': value, 'tag': 'v' + value,
                'deb': value + '-1', 'ifw': f'{core}.{revision}.1.0',
                'prerelease': False, 'latest': True}
    match = re.fullmatch(core_pattern + r'-zh\.([1-9][0-9]*)(?:\.rc\.([1-9][0-9]*))?', value)
    if not match:
        raise ValueError(f'Not a release-ready Chinese 4.x SemVer: {value}')
    core, revision, candidate = match.groups()
    # The historical -zh.N shape remains a SemVer prerelease, even without rc.
    return {'semver': value, 'tag': 'v' + value,
            'deb': f'{core}~zh.{revision}' + (f'~rc.{candidate}' if candidate else '') + '-1',
            'ifw': f'{core}.{revision}.' + (f'0.{candidate}' if candidate else '1.0'),
            'prerelease': True, 'latest': False}



if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('version')
    p.add_argument('--format', choices=['semver', 'tag', 'deb', 'ifw', 'prerelease', 'latest'])
    a = p.parse_args()
    v = versions(a.version)
    print(json.dumps(v[a.format]) if a.format in ['prerelease', 'latest'] else v[a.format] if a.format else json.dumps(v))
