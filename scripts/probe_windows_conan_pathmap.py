#!/usr/bin/env python3
"""Isolated real-MSVC/Conan experiment. Never builds or publishes the product.

Two positive cache roots plus a root-only negative control. Fail closed on any
missing path, flag, object, runtime output, or repeatability evidence.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

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
        tc.variables["DEP_INCLUDE"] = self.dependencies["pjpathmapdep"].package_folder + "/include"
        tc.generate()
        flags = {k: self.conf.get(k, check_type=list) for k in ("tools.build:cflags", "tools.build:cxxflags")}
        Path(self.build_folder, "probe-flags.json").write_text(json.dumps(flags), encoding="utf-8")
    def build(self):
        cmake = CMake(self); cmake.configure(); cmake.build()
        exes = list(Path(self.build_folder).glob("Release/probe.exe"))
        if len(exes) != 1: raise RuntimeError("missing unique probe executable")
        result = subprocess.run([str(exes[0])], capture_output=True, check=True)
        Path(self.build_folder, "probe-output.txt").write_bytes(result.stdout)
    def package(self):
        copy(self, "*.obj", self.build_folder, self.package_folder + "/objects")
        copy(self, "probe-output.txt", self.build_folder, self.package_folder)
        copy(self, "probe-flags.json", self.build_folder, self.package_folder)
'''
CMAKE = '''cmake_minimum_required(VERSION 3.20)
project(PJPathmapProbe LANGUAGES C CXX)
file(MAKE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/generated files")
file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/generated files/generated.h" "static const char* generated_path() { return __FILE__; }\\n")
add_executable(probe "source files/main.cpp" "source files/源.c")
target_include_directories(probe PRIVATE "${DEP_INCLUDE}" "${CMAKE_CURRENT_BINARY_DIR}/generated files")
target_compile_options(probe PRIVATE /FC /utf-8)
set_target_properties(probe PROPERTIES CXX_STANDARD 17)
'''
CPP = '''#include <cstdio>
#include "dep.h"
#include "generated.h"
extern "C" const char* c_path(void);
int main() {
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
    if result.returncode:
        raise RuntimeError(f'{args[0]} exited {result.returncode}; inspect {log.name}')
    return result.stdout


def export_ref(recipe, env, root, log):
    data=json.loads(run(['conan','export',recipe,'--format=json'],env,root,log))
    ref=data['reference']
    if '#' not in ref: raise RuntimeError('export omitted recipe revision')
    return ref


def one(label, base, dep, probe, enable):
    folder=base/label;folder.mkdir()
    cache=folder/'conan';cache.mkdir()
    env=os.environ.copy();env['CONAN_HOME']=str(cache)
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
    for path in (package/'objects').rglob('*.obj'):
        # CMake compiler detection objects are unrelated to this target.
        relative=path.relative_to(package/'objects').as_posix()
        if 'probe.dir/' in relative.casefold():
            objects[relative]=digest(path)
    if len(objects)!=2:raise RuntimeError(f'expected two target C/C++ objects, got {len(objects)}')
    for language in ('tools.build:cflags','tools.build:cxxflags'):
        if enable and not any(x.startswith('/pathmap:') and '=Z:/pj-conan-exact/' in x for x in flags[language]):
            raise RuntimeError('hook flags missing in recipe generate()')
    return {'refs':refs,'output':output,'objects':objects,
            'package_id':node['package_id'],'build_folder':node['build_folder'],
            'flags':flags}


def main():
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);args=p.parse_args()
    if sys.platform!='win32':p.error('requires native Windows MSVC runner')
    base=args.work.resolve();base.mkdir(exist_ok=False)
    report={'status':'failed','scope':'experimental fixture only; NOT product approval'}
    try:
        dep=base/'dep';dep.mkdir();(dep/'conanfile.py').write_text(DEP_RECIPE, encoding='utf-8')
        (dep/'dep.h').write_text('static const char* dep_path() { return __FILE__; }\n', encoding='utf-8')
        probe=base/'probe';probe.mkdir();(probe/'conanfile.py').write_text(PROBE_RECIPE, encoding='utf-8')
        (probe/'CMakeLists.txt').write_text(CMAKE, encoding='utf-8')
        source=probe/'source files';source.mkdir()
        (source/'main.cpp').write_text(CPP, encoding='utf-8')
        (source/'源.c').write_text('const char* c_path(void) { return __FILE__; }\n',encoding='utf-8')
        a=one('cache-a',base,dep,probe,True);b=one('cache-b',base,dep,probe,True)
        negative=one('root-only',base,dep,probe,False)
        if a['refs']!=b['refs']:raise RuntimeError('fixture recipe revisions differ')
        # Comparing cache-relative folders proves more than using two root names.
        cache_suffix=lambda x: x['build_folder'].replace('\\','/').split('/conan/',1)[1]
        if cache_suffix(a)==cache_suffix(b):raise RuntimeError('two real Conan cache suffixes unexpectedly identical')
        if a['output']!=b['output'] or any(not x.replace('\\','/').startswith('Z:/pj-conan-exact/') for x in a['output']):
            raise RuntimeError('runtime paths did not canonicalize equally across both caches')
        if a['objects']!=b['objects']:raise RuntimeError('raw C/C++ object SHA256 differs across caches')
        if negative['output']==a['output'] or all(x.replace('\\','/').startswith('Z:/pj-conan-exact/') for x in negative['output']):
            raise RuntimeError('negative control did not detect disabled exact mappings')
        report.update(status='passed',refs=a['refs'],objects=a['objects'],runtime_paths=a['output'],
                      different_cache_suffixes=True,negative_control_rejected=True)
    except Exception as exc:
        report['error'] = str(exc)
        raise
    finally:
        (base/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':main()
