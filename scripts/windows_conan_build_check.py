#!/usr/bin/env python3
"""Force and verify the reviewed Windows host graph's compiled packages."""
import argparse
import json
from pathlib import Path

REFS = Path(__file__).with_name('windows_conan_host_refs.json')
LOCK = Path(__file__).resolve().parents[1] / 'cmake/conan/windows-msvc194.lock'


def references():
    refs = json.loads(REFS.read_text(encoding='utf-8'))
    if len(refs) != 22 or len(set(refs)) != 22 or any('#' not in r for r in refs):
        raise ValueError('invalid reviewed host reference list')
    lock = json.loads(LOCK.read_text(encoding='utf-8'))
    if lock.get('version') != '0.5' or not set(refs).issubset(set(lock.get('requires', []))):
        raise ValueError('reviewed host references are not pinned by the Windows lockfile')
    return refs


def build_arguments():
    # Conan build patterns match reference names in both contexts; protobuf and
    # zlib build requirements can therefore be forced in addition to host libs.
    return ['--build=missing'] + ['--build=' + r.split('#', 1)[0] for r in references()]


def verify(graph):
    nodes = graph['graph']['nodes']
    nodes = nodes.values() if isinstance(nodes, dict) else nodes
    host = [n for n in nodes if n.get('context') == 'host' and
            n.get('package_type') in ('static-library', 'shared-library')]
    actual = [n['ref'] for n in host]
    if sorted(actual) != sorted(references()):
        raise ValueError('host compiled reference/revision set differs from reviewed graph')
    if any(n.get('binary') != 'Build' or not n.get('package_id') for n in host):
        raise ValueError('every reviewed host compiled package must have a package ID and Build status')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=('arguments', 'verify'))
    p.add_argument('graph', nargs='?', type=Path)
    args = p.parse_args()
    try:
        if args.action == 'arguments':
            if args.graph:
                p.error('arguments does not accept a graph')
            print('\n'.join(build_arguments()))
        else:
            if not args.graph:
                p.error('verify requires a graph')
            verify(json.loads(args.graph.read_text(encoding='utf-8-sig')))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        p.error(str(exc))

if __name__ == '__main__':
    main()
