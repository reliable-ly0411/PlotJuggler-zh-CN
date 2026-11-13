#!/usr/bin/env python3
"""Isolated actual locked graph experiment; no product build or publication."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from pe_fixture_diagnostics import inspect_pe
from windows_conan_build_check import build_arguments, verify

ROOT=Path(__file__).resolve().parents[1]


def check_graph(data):
    verify(data)  # Original 22 compiled Build audit, unchanged.
    lock=json.loads((ROOT/'cmake/conan/windows-msvc194.lock').read_text())
    mapping=json.loads((ROOT/'scripts/windows_conan_mapping_refs.json').read_text())
    if len(mapping)!=24 or set(mapping)!=set(lock['requires']):raise ValueError('mapping lock mismatch')
    nodes=data['graph']['nodes'];nodes=list(nodes.values()) if isinstance(nodes,dict) else nodes
    host=set()
    for n in nodes:
        ref=n.get('ref')
        if n.get('id')=='0' and n.get('recipe')=='Consumer' and n.get('context')=='host' and ref=='conanfile':continue
        if not ref:raise ValueError('unidentified non-consumer node')
        context=n.get('context')
        if context=='host':
            if ref not in mapping:raise ValueError('unknown host mapping ref')
            host.add(ref)
        elif context=='build':
            if ref not in lock['build_requires']:raise ValueError('unknown build-context ref')
        else:raise ValueError('unknown graph context')
    if host!=set(mapping):raise ValueError('host closure incomplete')
    return nodes


def compare_reports(a,b):
    expected='passed-dll-privacy-not-product-approval'
    if a.get('status')!=expected or b.get('status')!=expected:raise ValueError('both privacy audits must pass')
    if not a.get('dlls') or set(a['dlls'])!=set(b.get('dlls',{})):raise ValueError('DLL inventory differs')
    matches={k:a['dlls'][k]['sha256']==b['dlls'][k]['sha256'] for k in a['dlls']}
    return {'scope':'actual dependency DLLs only, not product or static library approval',
            'raw_dlls_equal':all(matches.values()),'dll_matches':matches,'byte_rewriting':False}


def main():
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path);p.add_argument('--compare',nargs=2,type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    if a.compare:
        result=compare_reports(*(json.loads(f.read_text(encoding='utf-8')) for f in a.compare))
        if a.output:a.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
        if not result['raw_dlls_equal']:raise ValueError('actual DLL raw SHA mismatch')
        return
    if not a.work:p.error('--work required')
    if sys.platform!='win32':p.error('native Windows required')
    base=a.work.resolve();base.mkdir(exist_ok=False);cache=base/'conan';cache.mkdir()
    env=os.environ.copy();env['CONAN_HOME']=str(cache)
    report={'scope':'diagnostic only; no product identity approval','status':'failed'}
    def run(args):
        r=subprocess.run([str(x) for x in args],cwd=ROOT,env=env,capture_output=True)
        with (base/'commands.log').open('ab') as f:f.write((' '.join(map(str,args))+'\n').encode());f.write(r.stdout+r.stderr)
        if b'D9002' in r.stdout+r.stderr or b'LNK4044' in r.stdout+r.stderr:raise RuntimeError('ignored compiler/linker option')
        if r.returncode:raise RuntimeError('command failed; inspect commands.log')
        return r.stdout
    try:
        run(['conan','profile','detect'])
        hooks=cache/'extensions/hooks';hooks.mkdir(parents=True)
        shutil.copyfile(ROOT/'scripts/hook_windows_conan_pathmap.py',hooks/'hook_windows_conan_pathmap.py')
        profile=base/'profile'
        run([sys.executable,ROOT/'scripts/windows_conan_pathmap.py','--source',ROOT,'--cache',cache,'--output',profile,
             '--experimental-hook-refs',ROOT/'scripts/windows_conan_mapping_refs.json','--experimental-link-brepro'])
        export=json.loads(run(['conan','export','cmake/conan/openssl-overlay','--name=openssl','--version=3.6.5','--user=plotjuggler','--channel=stable','--format=json']))
        if export['reference'] not in json.loads((ROOT/'scripts/windows_conan_host_refs.json').read_text()):raise ValueError('overlay revision mismatch')
        flags=build_arguments()+['--lockfile','cmake/conan/windows-msvc194.lock','-pr:h',profile,'-pr:h','cmake/conan/openssl-overlay.profile','-pr:b','default','-s','build_type=Release','-s','compiler.cppstd=17']
        plan=json.loads(run(['conan','graph','info','.']+flags+['--format=json']))
        (base/'graph-plan.json').write_text(json.dumps(plan),encoding='utf-8');check_graph(plan)
        result=json.loads(run(['conan','install','.','-of',base/'build']+flags+['--format=json']))
        nodes=check_graph(result);(base/'graph-result.json').write_text(json.dumps(result),encoding='utf-8')
        forbidden=[str(ROOT),str(base),str(cache),'Z:/pj-conan/p/b','Z:/pj-conan/p/']
        forbidden += [n[k] for n in nodes for k in ('source_folder','build_folder','package_folder') if n.get(k)]
        binaries={};libs={}
        for n in nodes:
            if n.get('context')!='host' or not n.get('package_folder'):continue
            folder=Path(n['package_folder'])
            for path in sorted(folder.rglob('*')):
                if path.suffix.lower() not in ('.dll','.lib') or not path.is_file():continue
                if path.is_symlink() or not path.resolve().is_relative_to(folder.resolve()):raise ValueError('escaped package file')
                key=n['ref']+'::'+path.relative_to(folder).as_posix();raw=path.read_bytes()
                if path.suffix.lower()=='.dll':binaries[key]=inspect_pe(raw,forbidden)
                else:libs[key]=hashlib.sha256(raw).hexdigest()
        report.update(dlls=binaries,static_or_import_libs=libs,host_compiled_count=22,mapping_ref_count=24,
                      build_context_policy='only lock-pinned tools; no exact hook applied to build context; final DLL privacy still required')
        if not binaries:raise ValueError('no actual dependency DLL evidence')
        if any(v['forbidden_paths_found'] for v in binaries.values()):raise ValueError('dependency DLL contains unmapped paths')
        report['status']='passed-dll-privacy-not-product-approval'
    except Exception as exc:
        report['error']=str(exc)
        raise
    finally:
        (base/'summary.json').write_text(json.dumps(report,indent=2),encoding='utf-8')

if __name__=='__main__':main()
