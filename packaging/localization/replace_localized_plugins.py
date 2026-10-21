#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Replace only provenance-listed plugin directories in a disposable package stage."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def replace(extra, destination):
    extra, destination = extra.resolve(), destination.resolve()
    assert extra != destination and extra not in destination.parents and destination not in extra.parents
    record = json.loads((extra / 'share/plotjuggler4/release.json').read_text())
    for item in record['localized_plugin_rebuilds']:
        identifier = item['id']
        assert identifier in {'protobuf-parser', 'toolbox-assistant-agent',
                              'toolbox-transform-editor', 'webrtc-client'}
        relative = Path('lib/plotjuggler/plugins') / identifier
        source = extra / relative
        assert source.is_dir() and not source.is_symlink()
        for file in item['files']:
            path = Path(file['path'])
            assert not path.is_absolute() and '..' not in path.parts and path.is_relative_to(relative)
            assert hashlib.sha256((extra / path).read_bytes()).hexdigest() == file['sha256']
        target = destination / relative
        assert not target.is_symlink()
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--extra-prefix', type=Path, required=True)
    p.add_argument('--destination', type=Path, required=True)
    a = p.parse_args()
    replace(a.extra_prefix, a.destination)
