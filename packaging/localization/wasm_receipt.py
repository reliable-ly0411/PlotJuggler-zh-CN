#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Bind a WASM validation artifact to its source, lane and production/probe kind."""

import argparse
import hashlib
import json
import os
import pathlib
import subprocess


def sha256(path):
    """Hash large WASM representations without loading them into memory."""
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def git(root, *args):
    """Query the exact checkout used by this validation job."""
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def safe_path(root, relative):
    """Reject manifest paths escaping the artifact, including symlinks."""
    path = pathlib.PurePosixPath(relative)
    if path.is_absolute() or '..' in path.parts or '\\' in relative:
        raise ValueError(f'Unsafe artifact path: {relative}')
    result = root / relative
    if not result.resolve().is_relative_to(root.resolve()) or result.is_symlink():
        raise ValueError(f'Unsafe artifact path: {relative}')
    return result


def package_record(root):
    """Verify every manifest representation and inventory every delivered file."""
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    if manifest['format'] != 'org.plotjuggler.wasm-deployment.v1' or not manifest['files']:
        raise ValueError('Invalid or empty deployment manifest')
    startup = total = 0
    logical_paths = set()
    for item in manifest['files']:
        if item['path'] in logical_paths:
            raise ValueError('Duplicate manifest file')
        logical_paths.add(item['path'])
        for representation in item['representations'].values():
            path = safe_path(root, representation['path'])
            if path.stat().st_size != representation['bytes'] or sha256(path) != representation['sha256']:
                raise ValueError(f'Manifest representation mismatch: {path}')
        size = item['representations'].get('br', item['representations']['identity'])['bytes']
        total += size
        if not item['path'].startswith('presets/') and not item['path'].endswith('/python_stdlib.zip'):
            startup += size
    files = {}
    for path in sorted(root.rglob('*')):
        if path.is_file():
            relative = path.relative_to(root).as_posix()
            safe_path(root, relative)
            files[relative] = {'bytes': path.stat().st_size, 'sha256': sha256(path)}
    return {'bundle_id': manifest['bundleId'], 'version': manifest['version'],
            'packaging_runtime': manifest['packagingRuntime'], 'files': files,
            'startup_bytes': startup, 'total_bytes': total}


def identity(args):
    """Require full immutable SHAs and independently verify both checkouts."""
    for root, expected in [(args.source_root, args.source_sha), (args.controller_root, args.controller_sha)]:
        if len(expected) != 40 or any(c not in '0123456789abcdef' for c in expected):
            raise ValueError('A full immutable commit SHA is required')
        if git(root, 'rev-parse', 'HEAD') != expected:
            raise ValueError('Checkout SHA does not match requested identity')
    baseline = json.loads((args.controller_root / 'docs/localization/upstream-baseline.json').read_text(encoding='utf-8'))
    if args.role == 'upstream':
        if args.source_sha != baseline['upstream_commit'] or args.source_repository != 'PlotJuggler/PlotJuggler':
            raise ValueError('Upstream lane does not match the recorded upstream source')
    elif args.source_sha != args.controller_sha:
        raise ValueError('Localized lane must build the exact controller commit')
    return {'role': args.role, 'kind': args.kind, 'source_repository': args.source_repository,
            'source_sha': args.source_sha, 'source_tree': git(args.source_root, 'rev-parse', 'HEAD^{tree}'),
            'controller_sha': args.controller_sha}


def run(args):
    """Capture a checked artifact or reject a mismatched download before serving it."""
    expected = identity(args)
    if args.mode == 'identity':
        print(json.dumps(expected))
        return
    if not args.package or args.output is None:
        raise ValueError('Capture and verify require packages and an output receipt')
    packages = {path: package_record(safe_path(args.source_root, path)) for path in args.package}
    extras = {}
    for pattern in getattr(args, 'extra', []):
        matches = sorted(args.source_root.glob(pattern))
        if not matches:
            raise ValueError(f'Missing acceptance support files: {pattern}')
        for path in matches:
            relative = path.relative_to(args.source_root).as_posix()
            safe_path(args.source_root, relative)
            extras[relative] = {'bytes': path.stat().st_size, 'sha256': sha256(path)}
    if args.mode == 'verify':
        receipt = json.loads(args.output.read_text(encoding='utf-8'))
        if (receipt['format'] != 'org.plotjuggler.wasm-validation.v1' or
                receipt['identity'] != expected or receipt['packages'] != packages or receipt['extras'] != extras):
            raise ValueError('Artifact receipt identity or bytes do not match')
    else:
        cache = args.cache.read_text(encoding='utf-8')
        expected_probe = 'ON' if args.kind == 'acceptance' else 'OFF'
        if f'PJ_WASM_ENABLE_INGRESS_PROBE:BOOL={expected_probe}\n' not in cache:
            raise ValueError('CMake probe configuration does not match artifact kind')
        for feature in ['SCENE2D', 'SCENE3D', 'PYTHON']:
            if f'PJ_WASM_WITH_{feature}:BOOL=ON\n' not in cache:
                raise ValueError(f'Required shipped feature disabled: {feature}')
        if git(args.source_root, 'diff', '--name-only', 'HEAD'):
            raise ValueError('Tracked source changed during validation')
        receipt = {'format': 'org.plotjuggler.wasm-validation.v1', 'identity': expected,
                   'packages': packages, 'extras': extras, 'cmake_cache_sha256': sha256(args.cache),
                   'configuration': [line for line in cache.splitlines() if line.startswith(('PJ_', 'CMAKE_BUILD_TYPE:', 'CMAKE_CXX_FLAGS'))],
                   'submodules': git(args.source_root, 'submodule', 'status', '--recursive'),
                   'versions_env_sha256': sha256(args.source_root / 'versions.env'),
                   'versions_env': (args.source_root / 'versions.env').read_text(encoding='utf-8'),
                   'validation_run': {'id': os.environ.get('GITHUB_RUN_ID'), 'attempt': os.environ.get('GITHUB_RUN_ATTEMPT')},
                   'startup_budget_script_sha256': sha256(args.source_root / 'scripts/wasm_size_budget.mjs'),
                   'budget_scope': 'reference startup <= 16932000' if args.role == 'upstream' else 'localized total <= 26000000; startup observed only'}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    for path, package in packages.items():
        print(json.dumps({'identity': expected, 'package': path,
                          'startup_bytes': package['startup_bytes'], 'total_bytes': package['total_bytes']}))


def main():
    """Parse explicit lane and checkout identity; never infer them from filenames."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['identity', 'capture', 'verify'])
    parser.add_argument('--role', choices=['upstream', 'localized'], required=True)
    parser.add_argument('--kind', choices=['production', 'acceptance'], required=True)
    parser.add_argument('--source-repository', required=True)
    parser.add_argument('--source-sha', required=True)
    parser.add_argument('--controller-sha', required=True)
    parser.add_argument('--source-root', type=pathlib.Path, default=pathlib.Path('.'))
    parser.add_argument('--controller-root', type=pathlib.Path, default=pathlib.Path('.ci-controller'))
    parser.add_argument('--cache', type=pathlib.Path)
    parser.add_argument('--package', action='append', default=[])
    parser.add_argument('--extra', action='append', default=[])
    parser.add_argument('--output', type=pathlib.Path)
    run(parser.parse_args())


if __name__ == '__main__':
    main()
