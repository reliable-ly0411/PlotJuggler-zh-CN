#!/usr/bin/env python3
"""Verify linuxdeploy did not replace the backport with distro QtCore.

ELF .text is compared because bundlers may legitimately strip or rewrite RPATH.
"""
import argparse
import hashlib
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser()
p.add_argument('expected', type=Path)
p.add_argument('actual', type=Path)
a = p.parse_args()

def text_digest(path):
    with tempfile.TemporaryDirectory() as tmp:
        section = Path(tmp) / 'text'
        subprocess.run(['objcopy', '--dump-section', f'.text={section}', str(path)], check=True)
        return hashlib.sha256(section.read_bytes()).hexdigest()

expected = text_digest(a.expected)
actual = text_digest(a.actual)
assert expected == actual, f'Packaged QtCore is not the backport: {a.actual}'
print(f'QtCore backport .text sha256={actual}: {a.actual}')
