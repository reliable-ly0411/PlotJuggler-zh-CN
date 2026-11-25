#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Clone a clean CI checkout and its initialized submodules into the real root.

All clone traffic is local. The resulting Git directories are self-contained;
Git metadata is for the build only and must never be included in the test kit.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile
import urllib.parse


class SourceError(Exception):
    """The source checkout cannot be tied to the requested commit."""


def git(*args, cwd=None, env=None, binary=False):
    result = subprocess.run(['git', *map(str, args)], cwd=cwd, env=env, capture_output=True)
    if result.returncode:
        raise SourceError('git operation failed: ' + (str(args[0]) if args else '<missing>'))
    return result.stdout if binary else result.stdout.decode('utf-8', errors='strict').strip()


def environment(hooks):
    env = dict(os.environ)
    # No inherited Git variable may redirect repository, object database,
    # config, templates, hooks, commands, index or credentials.
    for key in list(env):
        if key.upper().startswith('GIT_'):
            env.pop(key, None)
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull, GIT_ATTR_NOSYSTEM='1',
               GIT_TERMINAL_PROMPT='0', GIT_CONFIG_COUNT='1', GIT_CONFIG_KEY_0='core.hooksPath',
               GIT_CONFIG_VALUE_0=str(hooks))
    return env


def safe_module_path(value):
    path = PurePosixPath(value)
    if (not value or path.is_absolute() or '\\' in value or
            any(x in ('', '.', '..') or ':' in x for x in value.split('/'))):
        raise SourceError('invalid submodule path')
    return path


def module_map(source, relative=PurePosixPath(), env=None):
    """Read exact initialized submodule roots and declared upstream URLs."""
    result = []
    directory = source.joinpath(*relative.parts)
    modules = directory / '.gitmodules'
    if not modules.is_file():
        return result
    raw = git('config', '-z', '-f', modules, '--get-regexp', r'^submodule\..*\.path$', cwd=directory, env=env, binary=True)
    for record in raw.split(b'\0'):
        if not record:
            continue
        key, value = record.decode('utf-8').split('\n', 1)
        path = safe_module_path(value)
        url = git('config', '-f', modules, '--get', key[:-5] + '.url', cwd=directory, env=env)
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise SourceError('submodule URL is not a clean HTTPS origin')
        child_relative = relative / path
        child = source.joinpath(*child_relative.parts)
        if not child.is_dir():
            raise SourceError('source submodule is not initialized')
        sha = git('rev-parse', 'HEAD', cwd=child, env=env)
        if not re.fullmatch(r'[0-9a-f]{40}', sha):
            raise SourceError('invalid submodule commit')
        if git('status', '--porcelain=v1', '--untracked-files=all', cwd=child, env=env):
            raise SourceError('source submodule has uncommitted or untracked files')
        result.append({'path': child_relative.as_posix(), 'url': url, 'sha': sha})
        result.extend(module_map(source, child_relative, env))
    return result


def validate_git_directory(repo, root, env):
    """Reject Git object alternates, external gitdirs and local credential config."""
    gitdir = Path(git('rev-parse', '--absolute-git-dir', cwd=repo, env=env)).resolve(strict=True)
    if not gitdir.is_relative_to((root / '.git').resolve(strict=True)):
        raise SourceError('clone Git metadata escapes the new source root')
    if (gitdir / 'objects/info/alternates').exists():
        raise SourceError('clone still uses external object alternates')
    raw = git('config', '--null', '--local', '--list', cwd=repo, env=env, binary=True)
    for item in raw.split(b'\0'):
        if not item:
            continue
        key = item.split(b'\n', 1)[0].decode('utf-8').casefold()
        if key.endswith('.extraheader') or 'credential' in key or key in ('core.sshcommand', 'include.path'):
            raise SourceError('clone contains disallowed local credential or include configuration')


def clone(source, destination, sha, remote):
    source, destination = Path(source).resolve(strict=True), Path(destination).absolute()
    if not re.fullmatch(r'[0-9a-f]{40}', sha):
        raise SourceError('source commit must be a full lower-case SHA')
    remote_parts = urllib.parse.urlsplit(remote)
    if remote_parts.scheme != 'https' or remote_parts.hostname != 'github.com' or remote_parts.username or remote_parts.password or remote_parts.query or remote_parts.fragment:
        raise SourceError('expected origin must be a clean GitHub HTTPS URL')
    if destination.exists() or not destination.parent.is_dir():
        raise SourceError('destination must be a new child of an existing directory')
    with tempfile.TemporaryDirectory(prefix='pj-git-control-', dir=destination.parent) as control:
        hooks, template = Path(control) / "hooks", Path(control) / "template"
        hooks.mkdir(); template.mkdir()
        env = environment(hooks)
        if git('rev-parse', 'HEAD', cwd=source, env=env) != sha:
            raise SourceError('CI checkout HEAD does not match the requested source commit')
        if git('status', '--porcelain=v1', '--untracked-files=all', cwd=source, env=env):
            raise SourceError('CI checkout contains uncommitted or untracked files')
        status = git('submodule', 'status', '--recursive', cwd=source, env=env)
        if any(line[:1] in ('-', '+', 'U') for line in status.splitlines()):
            raise SourceError('CI checkout has missing, divergent or conflicted submodules')
        modules = module_map(source, env=env)
        if len({item['url'] for item in modules}) != len(modules):
            raise SourceError('duplicate submodule origins need explicit review')
        git('clone', '--no-local', '--no-hardlinks', '--no-checkout', '--no-tags', '--template=' + str(template), '--', source, destination, env=env)
        git('checkout', '--detach', sha, cwd=destination, env=env)
        git('remote', 'set-url', 'origin', remote, cwd=destination, env=env)
        if modules:
            options = [('core.hooksPath', str(hooks)), ('protocol.file.allow', 'always')]
            for item in modules:
                local = source.joinpath(*PurePosixPath(item['path']).parts).as_uri()
                options.append((f'url.{local}.insteadOf', item['url']))
            env['GIT_CONFIG_COUNT'] = str(len(options))
            for i, (key, value) in enumerate(options):
                env[f'GIT_CONFIG_KEY_{i}'] = key
                env[f'GIT_CONFIG_VALUE_{i}'] = value
            git('submodule', 'update', '--init', '--recursive', cwd=destination, env=env)
            # The clone transport is local only during initialization. Keep the
            # documented upstream URL in the transient build-time Git metadata.
            for item in modules:
                child = destination.joinpath(*PurePosixPath(item['path']).parts)
                git('remote', 'set-url', 'origin', item['url'], cwd=child, env=env)
        if git('rev-parse', 'HEAD', cwd=destination, env=env) != sha:
            raise SourceError('new source HEAD differs from the requested commit')
        if git('status', '--porcelain=v1', '--untracked-files=all', cwd=destination, env=env):
            raise SourceError('new source checkout is not clean')
        validate_git_directory(destination, destination, env)
        for item in modules:
            child = destination.joinpath(*PurePosixPath(item['path']).parts)
            if git('rev-parse', 'HEAD', cwd=child, env=env) != item['sha']:
                raise SourceError('new source submodule commit differs')
            validate_git_directory(child, destination, env)
        return {'source_sha': sha, 'source_tree': git('rev-parse', 'HEAD^{tree}', cwd=destination, env=env),
                'submodules': {x['path']: x['sha'] for x in modules}, 'source_clean': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--sha', required=True)
    parser.add_argument('--remote', required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(clone(args.source, args.destination, args.sha, args.remote), ensure_ascii=False))
        return 0
    except (SourceError, OSError, ValueError, UnicodeError) as exc:
        print(f'native source preparation failed: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
