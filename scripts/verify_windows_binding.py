"""Bind the Windows archive/root check to the independently audited stage."""
import argparse
import json
from pathlib import Path

def verify(audit, binding):
    root = audit['private_build_root_scan']
    if (audit['privacy_scan'] != 'passed' or root['status'] != 'passed' or binding['status'] != 'passed' or
        root['manifest_sha256'] != binding['private_roots_manifest_sha256'] or
        root['stage_inventory_sha256'] != binding['stage_inventory_sha256'] or
        root['scanned_files'] != binding['stage_files'] or
        binding['portable_files'] != binding['stage_files'] or binding['installer_files'] != binding['stage_files']):
        raise ValueError('stage or private-root scan mismatch')
    packages = {p['name']:p['sha256'] for p in audit['packages']}
    zips = [v for k,v in packages.items() if k.endswith('-Windows-x64.zip')]
    exes = [v for k,v in packages.items() if k.endswith('-Windows-x64.exe')]
    if zips != [binding['portable_sha256']] or exes != [binding['installer_sha256']]:
        raise ValueError('archive hash mismatch')

if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--audit',required=True);p.add_argument('--binding',required=True);a=p.parse_args()
    try:
        verify(json.loads(Path(a.audit).read_text(encoding='utf8')),json.loads(Path(a.binding).read_text(encoding='utf8')))
        print('Windows stage, archive and audit binding passed')
    except (OSError,ValueError,KeyError,TypeError):
        raise SystemExit('Windows stage, archive and audit binding failed') from None
