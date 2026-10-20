#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Resolve an explicit, first-created promotion ref to one reviewed run attempt."""
import re
import sys

from version_map import versions


def resolve(ref_name, version):
    tag = versions(version)['tag']
    slug = tag.replace('.', '-')
    pattern = r'zh-CN-4\.x-ci/publish-accepted-' + re.escape(slug) + r'-run-([1-9][0-9]*)-attempt-([1-9][0-9]*)'
    match = re.fullmatch(pattern, ref_name)
    if not match:
        raise ValueError('Promotion ref must bind this exact version and a reviewed run/attempt')
    return {'RELEASE_TAG': tag, 'CANDIDATE_RUN': match[1], 'CANDIDATE_ATTEMPT': match[2]}


if __name__ == '__main__':
    for key, value in resolve(sys.argv[1], sys.argv[2]).items():
        print(f'{key}={value}')
