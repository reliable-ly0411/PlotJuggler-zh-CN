#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Hash final release artifacts without including reports or prior hash lists."""
import argparse
import hashlib
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('directory', type=Path)
p.add_argument('--output', required=True)
a = p.parse_args()
files = sorted(x for x in a.directory.iterdir() if x.suffix in ['.exe', '.AppImage', '.deb'])
assert files, 'No final packages found'
lines = []
for path in files:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(8 * 1024 * 1024):
            digest.update(chunk)
    lines.append(f'{digest.hexdigest()}  {path.name}')
(a.directory / a.output).write_text('\n'.join(lines) + '\n')
print('\n'.join(lines))
