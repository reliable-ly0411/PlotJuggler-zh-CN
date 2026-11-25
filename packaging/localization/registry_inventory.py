#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Validate the mixed immutable registry snapshots and their retained notices."""
import hashlib
import json
from pathlib import Path
import shutil


def read_inventory(root):
    """Reject changed, missing or multiply attributed entries before staging."""
    base = root / 'packaging/localization'
    registry = json.loads((base / 'registry-lock.json').read_text(encoding='utf-8'))
    provenance = json.loads((base / 'registry-provenance.json').read_text(encoding='utf-8'))
    expected = {}
    for source in provenance['sources']:
        for identifier, digest in source['entries'].items():
            if identifier in expected:
                raise ValueError('Duplicate registry provenance: ' + identifier)
            expected[identifier] = digest
    actual = {}
    for entry in registry['extensions']:
        identifier = entry['id']
        if identifier in actual:
            raise ValueError('Duplicate locked registry entry: ' + identifier)
        encoded = json.dumps(entry, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
        actual[identifier] = hashlib.sha256(encoded).hexdigest()
    if actual != expected:
        raise ValueError('Locked registry entries differ from pinned provenance')
    for notice in provenance['supplement_notices']:
        path = Path(notice['path'])
        if path.is_absolute() or '..' in path.parts or notice['id'] not in actual:
            raise ValueError('Invalid registry notice identity or path')
        if hashlib.sha256((root / path).read_bytes()).hexdigest() != notice['sha256']:
            raise ValueError('Registry notice hash differs: ' + notice['id'])
    return registry, provenance


def stage_notices(root, licenses, *, plugin_ids=None):
    """Retain complete source notices and provenance alongside the original DSOs."""
    _, provenance = read_inventory(root)
    components = []
    for notice in provenance['supplement_notices']:
        if plugin_ids is not None and notice['id'] not in plugin_ids:
            continue
        relative = Path('registry-plugins') / notice['id']
        target = licenses / relative
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / notice['path'], target / 'LICENSE')
        components.append({'component': notice['id'], 'source': notice, 'notices': relative.as_posix()})
    (licenses / 'registry-provenance.json').write_text(json.dumps(provenance, indent=2) + '\n', encoding='utf-8')
    return components
