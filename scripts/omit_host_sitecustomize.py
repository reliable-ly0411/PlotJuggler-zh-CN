#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Omit only the verified optional Ubuntu host Apport hook from an AppImage.

Never copy arbitrary /etc customization into the distributable. The normal
stdlib, site module and sysconfig are retained and final audits remain enabled.
"""
import argparse
import hashlib
import json
from pathlib import Path
from normalize_python_config_link import check_plain_path

TARGET = '/etc/python3.10/sitecustomize.py'
TARGET_SHA256 = '82a38efc36075379bdddaabdb2a6d8e9835e1960b25977872532dc9c005e3223'
CONTENT_SHA256 = '43d81125d92376b1a69d53a71126a041cc9a18d8080e92dea0a2ae23be138b1e'

def omit(root):
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Invalid payload root')
    root = root.resolve(strict=True)
    link = root/'usr/lib/python3.10/sitecustomize.py'
    check_plain_path(link.parent, root)
    if not link.is_symlink():
        raise ValueError('Expected reviewed distro sitecustomize symlink')
    target = link.readlink().as_posix()
    if target != TARGET or hashlib.sha256(target.encode()).hexdigest() != TARGET_SHA256:
        raise ValueError('Unreviewed sitecustomize target')
    source = Path(TARGET)
    if source.is_symlink() or not source.is_file():
        raise ValueError('Expected real distro sitecustomize source')
    data = source.read_bytes()
    if hashlib.sha256(data).hexdigest() != CONTENT_SHA256:
        raise ValueError('Unreviewed sitecustomize content')
    link.unlink()
    return {'schema':1, 'path':link.relative_to(root).as_posix(), 'action':'omitted-host-apport-hook',
            'source_sha256':CONTENT_SHA256, 'target_sha256':TARGET_SHA256,
            'reason':'optional host crash reporting is not part of the embedded application runtime'}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True);p.add_argument('--report',type=Path,required=True)
    a=p.parse_args()
    if a.report.exists(): raise SystemExit('Refusing to overwrite receipt')
    result=omit(a.root)
    a.report.parent.mkdir(parents=True,exist_ok=True)
    with a.report.open('x') as f: json.dump(result,f,indent=2)
if __name__=='__main__':main()
