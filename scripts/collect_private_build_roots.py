"""Create a private manifest from explicit build roots and CMake cache; no path logs."""
import argparse
import json
import os
import re
from pathlib import Path
from private_build_roots import load_private_roots

def cmake_cache_roots(path):
    lines = Path(path).read_text(encoding='utf-8').splitlines()
    paths = []
    for line in lines:
        m = re.match(r'^(CPM_SOURCE_CACHE|FETCHCONTENT_BASE_DIR|FETCHCONTENT_SOURCE_DIR_[^:]+|CPM_PACKAGE_[^:]+_SOURCE_DIR):[^=]+=(.*)$', line)
        if m and m[2] and m[2].upper() not in ('OFF','FALSE','NOTFOUND') and not m[2].endswith('-NOTFOUND'):
            paths.append(m[2])
    return paths

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source', required=True, action='append')
    p.add_argument('--build', required=True, action='append')
    cache = p.add_mutually_exclusive_group(required=True)
    cache.add_argument('--cache', action='append')
    cache.add_argument('--no-cache', action='store_true')
    p.add_argument('--sdk', action='append', default=[])
    p.add_argument('--cmake-cache')
    p.add_argument('--out', required=True)
    a = p.parse_args()
    roots = {'source':a.source, 'build':a.build, 'cache':list(a.cache or []), 'sdk':a.sdk}
    if a.cmake_cache:
        roots['cache'].extend(cmake_cache_roots(a.cmake_cache))
    if not roots['cache']:
        if not a.no_cache:
            raise ValueError('cache missing')
        roots['cache'] = {'not_applicable':True}
    obj = {'schema':'private-build-roots/v1', 'platform':'windows' if os.name == 'nt' else 'unix', 'roots':roots}
    path = Path(a.out)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
            json.dump(obj, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        load_private_roots(path)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    print('Private build roots manifest created')

if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError):
        raise SystemExit('Private build roots collection failed') from None
