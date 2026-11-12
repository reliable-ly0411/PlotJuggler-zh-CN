#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Read host build pins without conflating independently pinned plugin SDKs."""
import configparser
import re


def read_host_versions(root):
    """Require exact host pins from the application's authoritative inputs."""
    values = {}
    for line in (root / 'versions.env').read_text(encoding='utf-8').splitlines():
        line = line.split('#', 1)[0].strip()
        if not line:
            continue
        key, value = line.split('=', 1)
        if key in values:
            raise ValueError(f'Duplicate version key: {key}')
        values[key] = value
    qt = values['PJ_QT_VERSION']
    if not re.fullmatch(r'\d+\.\d+\.\d+', qt):
        raise ValueError('Require an exact Qt version')
    conan = configparser.ConfigParser(delimiters=('=',), allow_no_value=True, inline_comment_prefixes=('#',), strict=True)
    conan.read(root / 'conanfile.txt', encoding='utf-8')
    sdk = [ref.split('/', 1)[1] for ref in conan['requires'] if ref.startswith('plotjuggler_sdk/')]
    if len(sdk) != 1 or not re.fullmatch(r'\d+\.\d+\.\d+', sdk[0]):
        raise ValueError('Require exactly one pinned host SDK')
    return {'version': values['PJ_APP_VERSION'], 'qt_version': qt, 'sdk_version': sdk[0]}
