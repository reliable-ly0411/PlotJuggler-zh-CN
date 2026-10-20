#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Enforce the Linux package's declared glibc 2.35 floor."""
from pathlib import Path
import re
import subprocess
import sys

bad = []
for path in Path(sys.argv[1]).rglob('*'):
    if not path.is_file() or '/plugins/ros2-topic-subscriber/dist/' in path.as_posix():
        continue
    with path.open('rb') as stream:
        if stream.read(4) != b'\x7fELF':
            continue
    text = subprocess.check_output(['readelf', '-V', str(path)], text=True, stderr=subprocess.DEVNULL)
    versions = [int(x) for x in re.findall(r'GLIBC_2\.(\d+)', text)]
    if versions and max(versions) > 35:
        bad.append((str(path), max(versions)))
if bad:
    raise SystemExit(f'ELF exceeds glibc 2.35: {bad}')
print('Every non-ROS-inner ELF respects glibc 2.35')
