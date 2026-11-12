#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Normalize copied product ELFs; audit exact private build roots in staged ELFs.

Never mutates the build tree. Distributing separate debug files needs a separate
privacy review. Reports contain names and digests, not embedded path contents.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

SCRIPT = Path(__file__).with_name('change_linux_rpath.cmake')
DYNAMIC = re.compile(r'\((RPATH|RUNPATH)\).*?\[(.*?)\]')
NEEDED = re.compile(r'\(NEEDED\).*?\[(.*?)\]')
DEBUG = re.compile(r'\]\s+\.(?:z?debug_|gnu_debuglink)')
SYMTAB = re.compile(r'\]\s+\.symtab\s')


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()


def readelf(*args):
    return subprocess.check_output(['readelf','-W',*args],text=True,stderr=subprocess.PIPE)


def is_elf(path):
    with path.open('rb') as f: return f.read(4)==b'\x7fELF'


def contains(path, needle):
    keep=b''
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):
            part=keep+chunk
            if needle in part: return True
            keep=part[-max(0,len(needle)-1):]
    return False


def roots_from(args):
    values=list(args.private_root)
    additional=json.loads(os.environ.get('PJ_PRIVATE_BUILD_ROOTS_JSON','[]'))
    if not isinstance(additional,list) or not all(isinstance(x,str) for x in additional):
        raise ValueError('PJ_PRIVATE_BUILD_ROOTS_JSON must be a list of absolute roots')
    values.extend(additional)
    if not values: raise ValueError('at least one exact private build root is required')
    roots=[]
    for value in values:
        path=Path(value)
        if not path.is_absolute() or len(str(path))<5: raise ValueError('invalid private root')
        encoded=os.fsencode(str(path).rstrip('/'))
        if encoded not in roots: roots.append(encoded)
    return roots


def product_files(root):
    files=[root/'plotjuggler',root/'plotjuggler-launcher',*sorted(root.glob('*.so'))]
    if not all(p.is_file() and not p.is_symlink() and is_elf(p) for p in files):
        raise ValueError('missing or invalid product ELF')
    if len(files)<3: raise ValueError('no plugin ELF found')
    return files


def normalize(args):
    root=Path(args.root).resolve(strict=True)
    if not (root/'plotjuggler').is_file(): raise ValueError('root is not a staged product bin directory')
    # Require a distinct source bin and disallow normalizing build binaries.
    source=Path(args.build_bin).resolve(strict=True)
    if root==source or root.is_relative_to(source) or source.is_relative_to(root):
        raise ValueError('staging and build directories must be separate')
    target='$ORIGIN' if args.layout=='deb' else '$ORIGIN/../lib'
    rows=[]
    for path in product_files(root):
        source_file=source/path.name
        if source_file.exists() and os.path.samefile(path,source_file):
            raise ValueError('staged ELF aliases build file: '+path.name)
        before=digest(path); dyn=readelf('-d',str(path)); paths=DYNAMIC.findall(dyn); needed=NEEDED.findall(dyn)
        if len(paths)>1: raise ValueError('multiple ELF dynamic search paths: '+path.name)
        if not paths and args.layout=='appimage':
            raise ValueError('AppImage product ELF has no loader path: '+path.name)
        if paths and paths[0][1]!=target:
            subprocess.run(['cmake',f'-DELF_FILE={path}',f'-DOLD_RPATH={paths[0][1]}',
                            f'-DNEW_RPATH={target}','-P',str(SCRIPT)],check=True,stdout=subprocess.DEVNULL)
        sections=readelf('-S',str(path)); has_symtab=bool(SYMTAB.search(sections)); removed=bool(DEBUG.search(sections))
        if removed: subprocess.run(['objcopy','--strip-debug',str(path)],check=True)
        final_dyn=readelf('-d',str(path)); final_paths=DYNAMIC.findall(final_dyn)
        if NEEDED.findall(final_dyn)!=needed: raise ValueError('dynamic dependencies changed: '+path.name)
        if paths and (len(final_paths)!=1 or final_paths[0][1]!=target): raise ValueError('RPATH not normalized: '+path.name)
        after_sections=readelf('-S',str(path))
        if DEBUG.search(after_sections): raise ValueError('debug sections remain: '+path.name)
        if has_symtab and not SYMTAB.search(after_sections): raise ValueError('symbol table removed: '+path.name)
        rows.append({'file':path.name,'before_sha256':before,'after_sha256':digest(path),
                     'debug_removed':removed,'symbol_table_before':has_symtab,
                     'symbol_table_after':bool(SYMTAB.search(after_sections)),
                     'symbol_table_retained':has_symtab and bool(SYMTAB.search(after_sections)),
                     'dynamic_path':final_paths[0][1] if final_paths else None})
    Path(args.report).parent.mkdir(parents=True,exist_ok=True)
    Path(args.report).write_text(json.dumps({'layout':args.layout,'rows':rows,
        'debug_policy':'DWARF removed from staged binaries; original build retains unstripped symbols privately'},indent=2))


def audit(args):
    root=Path(args.root).resolve(strict=True); private=roots_from(args); failures=[]; count=0
    for path in sorted(root.rglob('*')):
        if path.is_symlink() or not path.is_file() or not is_elf(path): continue
        count+=1
        for index,needle in enumerate(private):
            if contains(path,needle): failures.append({'file':str(path.relative_to(root)),'root_index':index})
    report={'elf_count':count,'private_root_count':len(private),'violations':failures}
    Path(args.report).parent.mkdir(parents=True,exist_ok=True)
    Path(args.report).write_text(json.dumps(report,indent=2))
    if count==0 or failures: raise ValueError('private build path found or no ELF in payload')


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    n=sub.add_parser('normalize');n.add_argument('--root',required=True);n.add_argument('--build-bin',required=True)
    n.add_argument('--layout',choices=('deb','appimage'),required=True);n.add_argument('--report',required=True)
    a=sub.add_parser('audit');a.add_argument('--root',required=True);a.add_argument('--report',required=True)
    a.add_argument('--private-root',action='append',default=[])
    args=p.parse_args()
    try: normalize(args) if args.action=='normalize' else audit(args)
    except (OSError,ValueError,subprocess.CalledProcessError,json.JSONDecodeError) as e:
        print('ELF staging policy failed:',str(e),file=sys.stderr);return 1
    return 0
if __name__=='__main__': sys.exit(main())
