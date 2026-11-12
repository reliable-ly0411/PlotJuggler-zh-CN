#!/usr/bin/env python3
"""Create an isolated Conan profile for experimental MSVC path mapping.

The destination is intentionally newly created; never overwrite a profile used
by another build. This script does not assert that recipes consumed these flags.
"""
import argparse
import ntpath
import re
from pathlib import Path


def validate_root(root):
    # Restrict to simple local paths until compiler/toolchain quoting is proven.
    if not re.fullmatch(r'[A-Za-z]:\\[A-Za-z0-9_.\\-]+', root):
        raise ValueError('root must be an absolute local Windows path without spaces or metacharacters')
    normalized = ntpath.normpath(root)
    if normalized != root or any(x in ('.', '..') for x in root.split('\\')):
        raise ValueError('root must be normalized')
    return normalized


def render(source, cache, base_profile="default"):
    source, cache = map(validate_root, (source, cache))
    if base_profile != 'default' and not re.fullmatch(r'[A-Za-z0-9_./:\-]+', base_profile):
        raise ValueError('base profile path contains unsupported characters')
    s, c = source.casefold(), cache.casefold()
    if s == c or s.startswith(c + '\\') or c.startswith(s + '\\'):
        raise ValueError('source and cache roots must be distinct and non-overlapping')
    flags = ['/experimental:deterministic',
             f'/pathmap:{source}=Z:\\pj-source',
             f'/pathmap:{cache}=Z:\\pj-conan']
    # Forward slashes avoid OpenSSL's Perl double-quoted configuration escaping;
    # MSVC 19.44 dual-root C/C++ probes verified this spelling; actual builds still need verification.
    flags = [flag.replace('\\', '/') for flag in flags]
    # Profile conf syntax supports Python list literals; backslashes must be escaped.
    encoded = repr(flags)
    return (f'include({base_profile})\n\n[conf]\n'
            f'tools.build:cflags={encoded}\n'
            f'tools.build:cxxflags={encoded}\n'
            "tools.info.package_id:confs=['tools.build:cflags', 'tools.build:cxxflags']\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--cache', required=True)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--base-profile', type=Path, help='existing host profile file; default: Conan default profile')
    args = parser.parse_args()
    try:
        base = 'default'
        if args.base_profile is not None:
            resolved = args.base_profile.resolve(strict=True)
            if not resolved.is_file():
                raise ValueError('base profile must be an existing regular file')
            base = resolved.as_posix()
        profile = render(args.source, args.cache, base)
        with args.output.open('x', encoding='utf-8', newline='\n') as f:
            f.write(profile)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    main()
