#!/usr/bin/env python3
"""Export the exact reviewed host SDK recipe before resolving the locked graph."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def verify_source(source, pin):
    """Check version and license provenance before executing the Conan recipe."""
    if (source / 'VERSION').read_text(encoding='utf-8').strip() != pin['version']:
        raise RuntimeError('Host SDK version mismatch')
    licenses = pin.get('license_files_sha256', {})
    if pin.get('license') != 'Apache-2.0' or set(licenses) != {'LICENSE', 'LICENSE-APACHE'}:
        raise RuntimeError('Host SDK license provenance missing')
    for name, digest in licenses.items():
        path = source / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise RuntimeError(f'Host SDK license mismatch: {name}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, help='Offline copy of the pinned archive')
    args = parser.parse_args()
    pin = json.loads((ROOT / 'cmake/host-sdk-source.json').read_text(encoding='utf-8'))
    expected = f"plotjuggler_sdk/{pin['version']}#{pin['recipe_revision']}"
    with tempfile.TemporaryDirectory(prefix='pj-host-sdk-') as temporary:
        work = Path(temporary)
        archive = work / 'sdk.tar.gz'
        if args.archive:
            data = args.archive.read_bytes()
        else:
            with urllib.request.urlopen(pin['archive_url'], timeout=120) as response:
                data = response.read()
        if hashlib.sha256(data).hexdigest() != pin['archive_sha256']:
            raise RuntimeError('Host SDK archive SHA256 mismatch')
        archive.write_bytes(data)
        source = work / 'source'
        source.mkdir()
        with tarfile.open(archive, 'r:gz') as bundle:
            for member in bundle.getmembers():
                parts = Path(member.name).parts
                if not parts or '..' in parts or Path(member.name).is_absolute():
                    raise RuntimeError('Unsafe SDK archive path')
                if len(parts) == 1:
                    continue
                target = source.joinpath(*parts[1:])
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                elif member.isfile():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with bundle.extractfile(member) as stream:
                        target.write_bytes(stream.read())
                else:
                    raise RuntimeError('Unexpected SDK archive entry type')
        verify_source(source, pin)
        result = subprocess.run(['conan', 'export', str(source), '--format=json'],
                                check=True, text=True, capture_output=True)
        actual = json.loads(result.stdout)['reference']
        if actual != expected:
            raise RuntimeError(f'Host SDK recipe mismatch: {actual}, expected {expected}')
        print(f'Exported verified host SDK {actual} from {pin["commit"]}')


if __name__ == '__main__':
    main()
