#!/usr/bin/env python3
"""Isolated actual locked graph experiment; no product build or publication."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
from pe_fixture_diagnostics import inspect_pe
from windows_conan_build_check import build_arguments, verify

ROOT=Path(__file__).resolve().parents[1]
PRODUCT_TARGETS = ('DataLoadParquet', 'ToolboxMosaico', 'ProtobufParser')


def ignored_option_warnings(output):
    """Separate OpenSSL's intentional GCC capability probes from ignored policy flags."""
    warnings=[]
    for line in output.decode('utf-8',errors='replace').splitlines():
        if 'D9002' not in line and 'LNK4044' not in line:continue
        match=re.fullmatch(r"cl : Command line warning D9002 : ignoring unknown option '(-x|/dev/null|-dM)'",line.strip())
        if not match:warnings.append(line)
    return warnings


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
    product=a.get('scope')=='three-product-plugins-diagnostic'
    if product != (b.get('scope')=='three-product-plugins-diagnostic'):raise ValueError('scope mismatch')
    expected='passed-plugin-privacy-not-release-approval' if product else 'passed-dll-privacy-not-product-approval'
    if product and (set(a.get('dlls',{})) != {t+'.dll' for t in PRODUCT_TARGETS} or set(b.get('dlls',{})) != {t+'.dll' for t in PRODUCT_TARGETS}):raise ValueError('product target inventory differs')
    if a.get('status')!=expected or b.get('status')!=expected:raise ValueError('both privacy audits must pass')
    if not a.get('dlls') or set(a['dlls'])!=set(b.get('dlls',{})):raise ValueError('DLL inventory differs')
    matches={k:a['dlls'][k]['sha256']==b['dlls'][k]['sha256'] for k in a['dlls']}
    return {'scope':'three product plugins only, not release approval' if product else 'actual dependency DLLs only, not product or static library approval',
            'raw_dlls_equal':all(matches.values()),'dll_matches':matches,'byte_rewriting':False}


def main():
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path);p.add_argument('--compare',nargs=2,type=Path);p.add_argument('--output',type=Path);p.add_argument('--product-plugins',action='store_true');a=p.parse_args()
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
        warnings=ignored_option_warnings(r.stdout+r.stderr)
        if warnings:report.setdefault('ignored_option_warnings',[]).extend(warnings)
        if r.returncode:raise RuntimeError(f'command failed (exit {r.returncode}); inspect commands.log')
        if warnings:raise RuntimeError('ignored compiler/linker option; inspect ignored_option_warnings')
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
        if a.product_plugins:
            # Keep the auxiliary-module failure visible, but measure the actual
            # product targets separately. No deployment or release follows.
            report['dependency_dlls']=report.pop('dlls')
            report['dependency_privacy_status']='failed' if any(v['forbidden_paths_found'] for v in binaries.values()) else 'passed'
            report['scope']='three-product-plugins-diagnostic'
            build=ROOT/'build-plugin-probe'
            if build.exists():raise ValueError('product probe build directory already exists')
            toolchain=base/'build/conan_toolchain.cmake'
            if not toolchain.is_file():raise ValueError('generated toolchain missing')
            run(['cmake','-S',ROOT,'-B',build,'-G','Visual Studio 17 2022','-A','x64',
                 '-DCMAKE_TOOLCHAIN_FILE='+str(toolchain),'-DCMAKE_BUILD_TYPE=Release',
                 '-DPJ_INSTALLATION=windows','-DPJ_PLUGINS_DIRECTORY=bin','-DBUILD_TESTING=OFF'])
            run(['cmake','--build',build,'--config','Release','--target',*PRODUCT_TARGETS,'--parallel','2'])
            product={}
            for target in PRODUCT_TARGETS:
                path=build/'bin/Release'/ (target+'.dll')
                if not path.is_file():raise ValueError('missing actual product target: '+target)
                product[path.name]=inspect_pe(path.read_bytes(),forbidden)
            report['dlls']=product
            if any(v['forbidden_paths_found'] for v in product.values()):raise ValueError('product DLL contains unmapped paths')
            report['status']='passed-plugin-privacy-not-release-approval'
            return
        if not binaries:raise ValueError('no actual dependency DLL evidence')
        if any(v['forbidden_paths_found'] for v in binaries.values()):raise ValueError('dependency DLL contains unmapped paths')
        report['status']='passed-dll-privacy-not-product-approval'
    except Exception as exc:
        report['error']=str(exc)
        raise
    finally:
        (base/'summary.json').write_text(json.dumps(report,indent=2),encoding='utf-8')

if __name__=='__main__':main()
