#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Fetch audited Linux packaging assets by identity, never by rolling tag."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request

LOCK = Path(__file__).with_name('linux-tools-lock.json')


def prepare_linux_tools(directory, verify_metadata=False):
    """Verify every download before writing or making it executable; fail closed."""
    tools = json.loads(LOCK.read_text(encoding='utf-8'))['tools']
    directory.mkdir(parents=True, exist_ok=True)
    for tool in tools:
        url = (f"https://api.github.com/repos/{tool['repository']}/releases/assets/"
               f"{tool['asset_id']}")
        if verify_metadata:
            request = urllib.request.Request(url, headers={'Accept': 'application/vnd.github+json'})
            with urllib.request.urlopen(request, timeout=180) as response:
                metadata = json.load(response)
            expected = {'id': tool['asset_id'], 'name': tool['name'], 'size': tool['size'],
                        'digest': 'sha256:' + tool['sha256'], 'state': 'uploaded'}
            if any(metadata.get(key) != value for key, value in expected.items()):
                raise ValueError(f'Linux packaging asset metadata mismatch: {url}')
        target = directory / tool['name']
        if target.is_file():
            data = target.read_bytes()
        else:
            request = urllib.request.Request(url, headers={'Accept': 'application/octet-stream'})
            with urllib.request.urlopen(request, timeout=180) as response:
                data = response.read()
        if len(data) != tool['size'] or hashlib.sha256(data).hexdigest() != tool['sha256']:
            raise ValueError(f'Linux packaging asset size/checksum mismatch: {url}')
        target.write_bytes(data)
        target.chmod(0o755)
    return tools


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    prepare_linux_tools(parser.parse_args().directory, verify_metadata=True)
