#!/usr/bin/env python3
"""Isolated real-MSVC/Conan experiment. Never builds or publishes the product.

Two positive cache roots plus a root-only negative control. Fail closed on any
missing path, flag, object, runtime output, or repeatability evidence.

Option boundaries (reviewed 2026-11-13):
- /Zf is documented for PDB throughput and requires /Zi or /ZI, NOT a path
  normalization contract: https://learn.microsoft.com/en-us/cpp/build/reference/zf
- /Z7 and /Zi select debug storage, not object-name normalization:
  https://learn.microsoft.com/en-us/cpp/build/reference/z7-zi-zi-debug-information-format
- /Fo controls the actual output file; documentation does not promise remapping
  S_OBJNAME: https://learn.microsoft.com/en-us/cpp/build/reference/fo-object-file-name
- /Brepro and explicit object /pathmap are empirical boundary probes here, not
  claims of documented MSVC S_OBJNAME support. Unknown-option warnings fail.
No variant deletes sections, changes acceptance masks, or authorizes production.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from coff_object_diagnostics import inspect_object, compare_objects
from pe_fixture_diagnostics import inspect_pe

ROOT = Path(__file__).resolve().parents[1]

DEP_RECIPE = '''from conan import ConanFile
from conan.tools.files import copy
class Dep(ConanFile):
    name = "pjpathmapdep"
    version = "1.0"
    package_type = "header-library"
    exports_sources = "dep.h"
    def package(self):
        copy(self, "dep.h", self.source_folder, self.package_folder + "/include")
'''
PROBE_RECIPE = '''from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import copy
import json, os, subprocess
from pathlib import Path
class Probe(ConanFile):
    name = "pjpathmapprobe"
    version = "1.0"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    requires = "pjpathmapdep/1.0"
    exports_sources = "CMakeLists.txt", "source files/*"
    def generate(self):
        tc = CMakeToolchain(self)
        # CMake quoted strings interpret backslash escapes in Windows paths.
        tc.variables["DEP_INCLUDE"] = self.dependencies["pjpathmapdep"].package_folder.replace(chr(92), "/") + "/include"
        tc.variables["PROBE_MODE"] = os.environ.get("PJ_PATHMAP_PROBE_MODE", "baseline")
        tc.generate()
        flags = {k: self.conf.get(k, check_type=list) for k in ("tools.build:cflags", "tools.build:cxxflags")}
        Path(self.build_folder, "probe-flags.json").write_text(json.dumps(flags), encoding="utf-8")
    def build(self):
        cmake = CMake(self); cmake.configure(); cmake.build()
        exes = list(Path(self.build_folder).glob("Release/probe_driver.exe"))
        if len(exes) != 1: raise RuntimeError("missing unique probe executable")
        result = subprocess.run([str(exes[0])], capture_output=True, check=True)
        Path(self.build_folder, "probe-output.txt").write_bytes(result.stdout)
    def package(self):
        copy(self, "*.obj", self.build_folder, self.package_folder + "/objects")
        copy(self, "*.dll", self.build_folder + "/Release", self.package_folder + "/pe")
        copy(self, "*.exe", self.build_folder + "/Release", self.package_folder + "/pe")
        copy(self, "probe-output.txt", self.build_folder, self.package_folder)
        copy(self, "probe-flags.json", self.build_folder, self.package_folder)
'''
CMAKE = '''cmake_minimum_required(VERSION 3.20)
project(PJPathmapProbe LANGUAGES C CXX)
file(MAKE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/generated files")
file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/generated files/generated.h" "static const char* generated_path() { return __FILE__; }\\n")
add_library(probe SHARED "source files/main.cpp" "source files/源.c")
add_executable(probe_driver "source files/driver.cpp")
target_link_libraries(probe_driver PRIVATE probe)
target_include_directories(probe PRIVATE "${DEP_INCLUDE}" "${CMAKE_CURRENT_BINARY_DIR}/generated files")
target_compile_options(probe PRIVATE /FC /utf-8)
set_target_properties(probe PROPERTIES CXX_STANDARD 17)
if(PROBE_MODE STREQUAL "brepro")
  target_compile_options(probe PRIVATE /Brepro)
elseif(PROBE_MODE STREQUAL "z7")
  target_compile_options(probe PRIVATE /Z7)
elseif(PROBE_MODE STREQUAL "zi-zf")
  target_compile_options(probe PRIVATE /Zi /Zf)
elseif(PROBE_MODE STREQUAL "object-pathmap")
  target_compile_options(probe PRIVATE
    "/pathmap:${CMAKE_CURRENT_BINARY_DIR}/probe.dir/Release/main.obj=Z:/pj-probe-objects/main.obj"
    "/pathmap:${CMAKE_CURRENT_BINARY_DIR}/probe.dir/Release/源.obj=Z:/pj-probe-objects/source.obj")
elseif(NOT PROBE_MODE STREQUAL "baseline")
  message(FATAL_ERROR "Unknown diagnostic mode")
endif()
'''
CPP = '''#include <cstdio>
#include "dep.h"
#include "generated.h"
extern "C" const char* c_path(void);
extern "C" __declspec(dllexport) void exported_paths() {
  std::puts(__FILE__); std::puts(c_path());
  std::puts(dep_path()); std::puts(generated_path());
}
'''


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args, env, cwd, log):
    result = subprocess.run([str(a) for a in args], env=env, cwd=cwd, capture_output=True)
    with log.open('ab') as f:
        f.write(('$ ' + ' '.join(str(a) for a in args) + '\n').encode('utf-8'))
        f.write(result.stdout); f.write(result.stderr)
    if b'D9002' in result.stdout + result.stderr:
        raise RuntimeError('MSVC ignored an unknown option; experiment is not valid')
    if result.returncode:
        raise RuntimeError(f'{args[0]} exited {result.returncode}; inspect {log.name}')
    return result.stdout


def export_ref(recipe, env, root, log):
    data=json.loads(run(['conan','export',recipe,'--format=json'],env,root,log))
    ref=data['reference']
    if '#' not in ref: raise RuntimeError('export omitted recipe revision')
    return ref


def one(label, base, dep, probe, enable, mode="baseline"):
    folder=base/label;folder.mkdir()
    cache=folder/'conan';cache.mkdir()
    env=os.environ.copy();env['CONAN_HOME']=str(cache)
    env['PJ_PATHMAP_PROBE_MODE']=mode
    log=base/f'{label}.log'
    run(['conan','profile','detect'],env,base,log)
    refs=[export_ref(dep,env,base,log),export_ref(probe,env,base,log)]
    refs_path=folder/'refs.json';refs_path.write_text(json.dumps(refs), encoding='utf-8')
    profile=folder/'profile'
    args=[sys.executable,ROOT/'scripts/windows_conan_pathmap.py','--source',ROOT,'--cache',cache,'--output',profile]
    if enable:
        args += ['--experimental-hook-refs',refs_path]
        hooks=cache/'extensions/hooks';hooks.mkdir(parents=True)
        shutil.copyfile(ROOT/'scripts/hook_windows_conan_pathmap.py',hooks/'hook_windows_conan_pathmap.py')
    run(args,env,base,log)
    data=json.loads(run(['conan','create',probe,'--no-remote','--build=*','-pr:h',profile,'-pr:b','default',
                         '-s','build_type=Release','-s','compiler.cppstd=17','--format=json'],env,base,log))
    nodes=list(data['graph']['nodes'].values())
    node=next(n for n in nodes if str(n.get('ref','')).startswith('pjpathmapprobe/1.0#'))
    package=Path(node['package_folder'])
    output=(package/'probe-output.txt').read_text(encoding='utf-8').splitlines()
    if len(output)!=4:raise RuntimeError('probe did not exercise all four source/header paths')
    flags=json.loads((package/'probe-flags.json').read_text(encoding='utf-8'))
    objects={}
    evidence=base/'fixture-objects'/label
    evidence.mkdir(parents=True)
    for path in (package/'objects').rglob('*.obj'):
        # CMake compiler detection objects are unrelated to this target.
        relative=path.relative_to(package/'objects').as_posix()
        if 'probe.dir/' in relative.casefold():
            if path.is_symlink() or not path.resolve().is_relative_to((package/'objects').resolve()):
                raise RuntimeError('unexpected object outside fixture package')
            raw=path.read_bytes()
            if len(raw)>20*1024*1024: raise RuntimeError('unexpected oversized fixture object')
            objects[relative]=digest(path)
            target=evidence/path.name
            if target.exists(): raise RuntimeError('duplicate fixture object basename')
            target.write_bytes(raw)
            try:
                inspection=inspect_object(raw)
            except ValueError as exc:
                inspection={'error':str(exc),'sha256':digest(path),'bytes':len(raw),'status':'unsupported-not-approved'}
            target.with_suffix('.obj.json').write_text(json.dumps(inspection,indent=2),encoding='utf-8')
    (evidence/'manifest.json').write_text(json.dumps({'scope':'REVIEW ONLY: locally authored fixture objects, not product assets',
        'label':label,'objects':objects,'byte_rewriting':False},indent=2),encoding='utf-8')
    if len(objects)!=2:raise RuntimeError(f'expected two target C/C++ objects, got {len(objects)}')
    for language in ('tools.build:cflags','tools.build:cxxflags'):
        if enable and not any(x.startswith('/pathmap:') and '=Z:/pj-conan-exact/' in x for x in flags[language]):
            raise RuntimeError('hook flags missing in recipe generate()')
    pe_evidence=base/'fixture-pe'/label
    pe_evidence.mkdir(parents=True)
    binaries={}
    inspections={}
    object_names=[]
    for obj in evidence.glob('*.obj.json'):
        # Exact S_OBJNAME strings are extracted without changing the object.
        info=json.loads(obj.read_text(encoding='utf-8'))
        def names(value):
            if isinstance(value,dict):
                for k,v in value.items():
                    if k=='object_name' and isinstance(v,str) and v.lower().endswith('.obj'): object_names.append(v)
                    else: names(v)
            elif isinstance(value,list):
                for v in value: names(v)
        names(info)
    if len(object_names)!=2: raise RuntimeError('missing two S_OBJNAME records for PE retention inspection')
    for name in ('probe.dll','probe_driver.exe'):
        path=package/'pe'/name
        raw=path.read_bytes()
        (pe_evidence/name).write_bytes(raw)
        inspections[name]=inspect_pe(raw,forbidden=(str(base),str(cache),node['build_folder']),object_names=object_names)
        binaries[name]=digest(path)
    (pe_evidence/'manifest.json').write_text(json.dumps(inspections,indent=2),encoding='utf-8')
    return {'binaries':binaries,'pe_inspections':inspections,'refs':refs,'output':output,'objects':objects,
            'package_id':node['package_id'],'build_folder':node['build_folder'],
            'flags':flags}


def main():
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True)
    p.add_argument('--mode',choices=('baseline','brepro','z7','zi-zf','object-pathmap'),default='baseline')
    args=p.parse_args()
    if sys.platform!='win32':p.error('requires native Windows MSVC runner')
    base=args.work.resolve();base.mkdir(exist_ok=False)
    report={'status':'failed','mode':args.mode,'scope':'experimental fixture only; NOT product approval'}
    try:
        dep=base/'dep';dep.mkdir();(dep/'conanfile.py').write_text(DEP_RECIPE, encoding='utf-8')
        (dep/'dep.h').write_text('static const char* dep_path() { return __FILE__; }\n', encoding='utf-8')
        probe=base/'probe';probe.mkdir();(probe/'conanfile.py').write_text(PROBE_RECIPE, encoding='utf-8')
        (probe/'CMakeLists.txt').write_text(CMAKE, encoding='utf-8')
        source=probe/'source files';source.mkdir()
        (source/'main.cpp').write_text(CPP, encoding='utf-8')
        (source/'driver.cpp').write_text('extern "C" __declspec(dllimport) void exported_paths();\nint main() { exported_paths(); }\n', encoding='utf-8')
        (source/'源.c').write_text('const char* c_path(void) { return __FILE__; }\n',encoding='utf-8')
        report['completed']={}
        a=one('cache-a',base,dep,probe,True,args.mode);report['completed']['cache-a']={'refs':a['refs'],'output':a['output'],'objects':a['objects']}
        b=one('cache-b',base,dep,probe,True,args.mode);report['completed']['cache-b']={'refs':b['refs'],'output':b['output'],'objects':b['objects']}
        negative=one('root-only',base,dep,probe,False,args.mode);report['completed']['root-only']={'refs':negative['refs'],'output':negative['output'],'objects':negative['objects']}
        if a['refs']!=b['refs']:raise RuntimeError('fixture recipe revisions differ')
        # Comparing cache-relative folders proves more than using two root names.
        cache_suffix=lambda x: x['build_folder'].replace('\\','/').split('/conan/',1)[1]
        if cache_suffix(a)==cache_suffix(b):raise RuntimeError('two real Conan cache suffixes unexpectedly identical')
        if a['output']!=b['output'] or any(not x.replace('\\','/').startswith('Z:/pj-conan-exact/') for x in a['output']):
            raise RuntimeError('runtime paths did not canonicalize equally across both caches')
        report.update(refs=a['refs'],runtime_paths=a['output'],different_cache_suffixes=True,runtime_paths_equal=True)
        comparisons={}
        for name in sorted(set(a['objects']) & set(b['objects'])):
            filename=Path(name).name
            comparisons[name]=compare_objects((base/'fixture-objects/cache-a'/filename).read_bytes(),(base/'fixture-objects/cache-b'/filename).read_bytes())
        (base/'coff-comparison.json').write_text(json.dumps(comparisons,indent=2),encoding='utf-8')
        report['raw_objects_equal']=a['objects']==b['objects']
        # Evaluate and retain the negative control even when byte equality fails.
        report['negative_control_rejected']=negative['output']!=a['output'] and not all(x.replace(chr(92),'/').startswith('Z:/pj-conan-exact/') for x in negative['output'])
        report['raw_pe_equal']=a['binaries']==b['binaries']
        report['pe_privacy_clean']=not any(v['forbidden_paths_found'] for v in a['pe_inspections'].values()) and not any(v['forbidden_paths_found'] for v in b['pe_inspections'].values())
        report['pe_object_names_retained']={label:{name:v['object_names_found'] for name,v in item['pe_inspections'].items()} for label,item in (('cache-a',a),('cache-b',b),('root-only',negative))}
        report['pe_section_equality']={name:{section['name']:section['sha256']==next((s['sha256'] for s in b['pe_inspections'][name].get('sections',[]) if s['name']==section['name']),None) for section in info.get('sections',[])} for name,info in a['pe_inspections'].items()}
        (base/'pe-comparison.json').write_text(json.dumps({'cache-a':a['pe_inspections'],'cache-b':b['pe_inspections'],'root-only':negative['pe_inspections'],'raw_equal':report['raw_pe_equal']},indent=2),encoding='utf-8')
        # Object mismatch remains a failure even if linked PE happens to match.
        if a['objects']!=b['objects']:raise RuntimeError('raw C/C++ object SHA256 differs across caches; see coff-comparison.json')
        if negative['output']==a['output'] or all(x.replace('\\','/').startswith('Z:/pj-conan-exact/') for x in negative['output']):
            raise RuntimeError('negative control did not detect disabled exact mappings')
        if not report['raw_pe_equal'] or not report['pe_privacy_clean']:raise RuntimeError('linked PE equality/privacy failed')
        report.update(status='passed',refs=a['refs'],objects=a['objects'],runtime_paths=a['output'],
                      different_cache_suffixes=True,negative_control_rejected=True)
    except Exception as exc:
        report['error'] = str(exc)
        raise
    finally:
        (base/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':main()
