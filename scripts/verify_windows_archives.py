"""Verify stage, portable ZIP and final IFW EXE payload without running installer."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import tempfile
import zipfile
from windows_ifw_payload import checked_path, inventory
from private_build_roots import load_private_roots, contains_private_root, stage_inventory_sha256
from package_privacy import TASK_PRIVATE_ROOT

IFW47_DEVTOOL_SHA256 = 'a1c716966cb5b2c90814f5714d7e7e4549b105057e40e17d92f81595121e3f57'

def digest(path):
    with open(path, 'rb') as f:
        h = hashlib.sha256()
        for block in iter(lambda:f.read(1048576), b''): h.update(block)
    return h.hexdigest()

def root_hit(data, roots):
    views = (data.decode('latin1'), data.decode('utf-8', errors='replace'),
             data.decode('utf-16le', errors='ignore'), data[1:].decode('utf-16le', errors='ignore'))
    return contains_private_root(data, roots) or any(TASK_PRIVATE_ROOT.search(v) for v in views)

def verify_zip(archive, expected, roots):
    parents = set()
    for name in expected:
        parents.update(str(p) for p in PurePosixPath(name).parents if str(p) != '.')
    with zipfile.ZipFile(archive) as z:
        entries = z.infolist(); names = [x.filename.replace('\\', '/') for x in entries]
        if len(set(n.casefold() for n in names)) != len(names):
            raise ValueError('duplicate archive path')
        for item, name in zip(entries,names):
            if (name.startswith('/') or ':' in name or
                any(x in ('','.','..') for x in name.rstrip('/').split('/')) or
                stat.S_ISLNK((item.external_attr >> 16) & 0xffff) or
                (item.is_dir() and name.rstrip('/') not in parents)):
                raise ValueError('unsafe archive entry')
        files = [(x,n) for x,n in zip(entries,names) if not x.is_dir()]
        if len(files) != len(expected) or {n for _,n in files} != set(expected):
            raise ValueError('archive file set mismatch')
        for entry, name in files:
            h = hashlib.sha256(); content = bytearray()
            if entry.file_size != expected[name][0]: raise ValueError('archive size mismatch')
            with z.open(entry) as stream:
                for block in iter(lambda:stream.read(1048576), b''):
                    h.update(block); content.extend(block)
                    if len(content) > expected[name][0]: raise ValueError('archive size mismatch')
            if (len(content),h.hexdigest()) != expected[name]: raise ValueError('archive content mismatch')
            if root_hit(bytes(content), roots): raise ValueError('private build root in archive')
        return len(files)

def verify(stage, portable, exe, devtool, expected_exe_sha, roots, out):
    stage,portable,exe,devtool = (checked_path(x) for x in (stage,portable,exe,devtool))
    if not re.fullmatch(r'[0-9a-f]{64}',expected_exe_sha): raise ValueError('invalid installer hash')
    if digest(devtool) != IFW47_DEVTOOL_SHA256 or digest(exe) != expected_exe_sha:
        raise ValueError('tool or installer identity mismatch')
    if os.path.lexists(exe.parent / 'installer.dat'): raise ValueError('installer sidecar exists')
    if root_hit(exe.read_bytes(), roots): raise ValueError('private build root in installer raw bytes')
    expected = inventory(stage)
    for name, (length, sha) in expected.items():
        data = (stage/name).read_bytes()
        if len(data)!=length or hashlib.sha256(data).hexdigest()!=sha: raise ValueError('stage changed')
        if root_hit(data, roots): raise ValueError('private build root in stage')
    portable_before = digest(portable)
    n_zip = verify_zip(portable,expected,roots)
    with tempfile.TemporaryDirectory(prefix='pj-ifw-dump-') as parent:
        dump = Path(parent)/'dump'
        if os.path.lexists(dump): raise ValueError('dump is not fresh')
        run = subprocess.run([str(devtool),'dump',str(exe),str(dump)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if run.returncode: raise ValueError('devtool dump failed')
        if (os.path.lexists(exe.parent/'installer.dat') or digest(exe)!=expected_exe_sha or
            digest(devtool)!=IFW47_DEVTOOL_SHA256): raise ValueError('installer or tool changed')
        dump_files = inventory(checked_path(dump))
        for name in dump_files:
            if root_hit((dump/name).read_bytes(), roots):
                raise ValueError('private build root in dumped file raw bytes')
        metadata = checked_path(dump / 'metadata')
        if not metadata.is_dir(): raise ValueError('missing metadata')
        dirs = {p.name for p in metadata.iterdir() if p.is_dir()}
        # Fixed IFW configuration directories plus exactly one application component.
        if dirs != {'config', 'installer-config', 'io.plotjuggler.application'}:
            raise ValueError('unexpected metadata directory set')
        paths = list((metadata/'io.plotjuggler.application').glob('*payload.zip'))
        if len(paths)!=1 or paths[0].is_symlink() or not paths[0].is_file(): raise ValueError('invalid component payload')
        payload = checked_path(paths[0])
        dump_sha = digest(payload); n_exe = verify_zip(payload,expected,roots)
        if digest(payload) != dump_sha: raise ValueError('dump payload changed')
    if digest(portable)!=portable_before or inventory(stage)!=expected: raise ValueError('archive or stage changed')
    report = {'scope':'stage files, portable ZIP members, installer raw bytes, dump raw files and extracted application component ZIP members',
              'status':'passed', 'stage_files':len(expected), 'portable_files':n_zip, 'installer_files':n_exe,
              'stage_inventory_sha256': stage_inventory_sha256([{'path':n,'bytes':v[0],'sha256':v[1]} for n,v in expected.items()]),
              'portable_sha256':portable_before, 'installer_sha256':expected_exe_sha,
              'devtool_sha256':IFW47_DEVTOOL_SHA256, 'installer_payload_zip_sha256':dump_sha,
              'private_roots_manifest_sha256':roots['manifest_sha256'], 'private_root_count':roots['root_count']}
    with Path(out).open('x',encoding='utf-8') as f: json.dump(report,f,indent=2);f.write('\n')
    return report

def main():
    p=argparse.ArgumentParser()
    for name in ('stage','portable','exe','devtool','installer-sha','private-build-roots','out'):
        p.add_argument('--'+name,required=True)
    a=p.parse_args(); roots=load_private_roots(a.private_build_roots)
    verify(a.stage,a.portable,a.exe,a.devtool,a.installer_sha,roots,a.out)
    print('Windows archive and root checks passed')
if __name__=='__main__':
    try: main()
    except (OSError,ValueError,zipfile.BadZipFile,subprocess.SubprocessError):
        raise SystemExit('Windows archive and root checks failed') from None
