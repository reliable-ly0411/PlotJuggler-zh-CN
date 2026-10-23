#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Write content identities for safe, one-time same-version localized plugin seeds."""
import hashlib
import json
from pathlib import Path

MARKER = '.pj-localized-build.json'
LOCK = Path(__file__).with_name('localized-plugin-legacy-builds.json')


def write_identity(destination, item, platform):
    """Bind one newly built DSO and audited same-version predecessors, never broad IDs."""
    destination = Path(destination)
    binaries = [p for p in destination.rglob('*') if p.suffix in ('.so', '.dll')]
    if len(binaries) != 1 or binaries[0].is_symlink():
        raise ValueError('Localized seed identity requires exactly one regular plugin DSO')
    binary = binaries[0]
    platform_key = {'Windows': 'windows-x86_64', 'Linux': 'linux-x86_64'}[platform]
    legacy = json.loads(LOCK.read_text(encoding='utf-8'))['builds']
    hashes = sorted({file['sha256'] for entry in legacy
                     if (entry['id'], entry['version'], entry['platform']) ==
                        (item['id'], item['version'], platform_key)
                     for file in entry['files']})
    identity = {
        'schema': 1, 'kind': 'fork-localized-rebuild',
        'id': item['id'], 'version': item['version'],
        'dso': binary.relative_to(destination).as_posix(),
        'sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
        'legacy_sha256': hashes,
    }
    (destination / MARKER).write_text(json.dumps(identity, indent=2) + '\n', encoding='utf-8')
    return identity
