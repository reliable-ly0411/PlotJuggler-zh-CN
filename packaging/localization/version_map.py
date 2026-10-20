#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Map the fork's SemVer to ordered platform package versions."""
import argparse
import json
import re


def versions(value):
    """IFW is numeric; dpkg uses tilde to keep each prerelease below its final."""
    match = re.fullmatch(r'(4\.\d+\.\d+)-zh\.([1-9]\d*)(?:\.rc\.([1-9]\d*))?', value)
    if not match:
        raise ValueError(f'Not a release-ready Chinese 4.x SemVer: {value}')
    core, revision, candidate = match.groups()
    return {'semver': value, 'tag': 'v' + value,
            'deb': f'{core}~zh.{revision}' + (f'~rc.{candidate}' if candidate else '') + '-1',
            'ifw': f'{core}.{revision}.' + (f'0.{candidate}' if candidate else '1.0')}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('version')
    p.add_argument('--format', choices=['semver', 'tag', 'deb', 'ifw'])
    a = p.parse_args()
    v = versions(a.version)
    print(v[a.format] if a.format else json.dumps(v))
