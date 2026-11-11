#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Stage exactly two verified plugin inputs for native feedback tests, not a release."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import stat
import struct
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[2]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def binary_matches(data, platform):
    if platform == 'linux-x86_64':
        return len(data) >= 20 and data[:6] == b'\x7fELF\x02\x01' and struct.unpack_from('<H', data, 18)[0] == 62
    if len(data) < 64 or data[:2] != b'MZ':
        return False
    offset = struct.unpack_from('<I', data, 60)[0]
    return (offset + 6 <= len(data) and data[offset:offset+4] == b'PE\0\0'
            and struct.unpack_from('<H', data, offset+4)[0] == 0x8664)


def prepare(source, build, output, config, platform, archive=None):
    source, build, output = source.resolve(), build.resolve(), output.resolve()
    require(platform in ('linux-x86_64', 'windows-x86_64'), 'Unsupported native platform')
    require(not output.exists(), 'Require a new isolated fixture directory')
    require(not output.with_name(output.name+'-identity.json').exists(), 'Require a new isolated fixture identity')
    lock = json.loads((source/'packaging/localization/registry-lock.json').read_text(encoding='utf-8'))
    entries = [x for x in lock['extensions'] if x['id'] == 'toolbox-fft']
    require(len(entries) == 1 and entries[0]['version'] == '1.0.1', 'Unexpected locked FFT identity')
    spec = entries[0]['platforms'][platform]
    require(spec['url'].startswith('https://github.com/PlotJuggler/pj-official-plugins/releases/download/'),
            'FFT fixture must come from the locked official release')
    if archive is None:
        with urllib.request.urlopen(spec['url'], timeout=120) as response:
            raw = response.read(32*1024*1024+1)
    else:
        require(archive.stat().st_size <= 32*1024*1024, 'FFT archive is too large')
        raw = archive.read_bytes()
    require(len(raw) <= 32*1024*1024, 'FFT archive is too large')
    digest = hashlib.sha256(raw).hexdigest()
    require(spec['checksum'] == 'sha256:'+digest, 'FFT archive checksum mismatch')
    fft_files = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as zipped:
        require(sum(x.file_size for x in zipped.infolist()) <= 128*1024*1024, 'FFT extraction is too large')
        for item in zipped.infolist():
            path = PurePosixPath(item.filename)
            require(bool(path.parts) and not path.is_absolute() and '..' not in path.parts
                    and '\\' not in item.filename and ':' not in item.filename
                    and path.parts[0] == 'toolbox-fft',
                    'Unexpected FFT archive path')
            require(not stat.S_ISLNK(item.external_attr >> 16), 'Unexpected FFT symlink')
            if not item.is_dir():
                require(len(path.parts) == 2 and path.name not in fft_files, 'Unexpected nested/duplicate FFT file')
                fft_files[path.name] = zipped.read(item)
    fft_manifest = json.loads(fft_files['manifest.json'].decode('utf-8'))
    require(fft_manifest['id'] == 'toolbox-fft' and fft_manifest['version'] == '1.0.1', 'FFT manifest differs')
    suffix = '.dll' if platform == 'windows-x86_64' else '.so'
    fft_binaries = [name for name in fft_files if name.endswith(suffix)]
    require(len(fft_binaries) == 1 and binary_matches(fft_files[fft_binaries[0]], platform), 'Wrong FFT binary platform')
    selected = Path((build/f'ardupilot-package-path-{config}.txt').read_text(encoding='utf-8').strip())
    require(selected.is_file() and selected.suffix == suffix, 'Missing exact CMake-selected APBIN binary')
    apbin_bytes = selected.read_bytes()
    require(binary_matches(apbin_bytes, platform), 'Wrong APBIN binary platform')
    manifest_path = build/'ardupilot-dataflash/ardupilot_source_plugin.pjmanifest.json'
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes.decode('utf-8'))
    baseline = json.loads((source/'docs/localization/upstream-baseline.json').read_text(encoding='utf-8'))['ardupilot_plugin']
    require(manifest['id'] == 'ardupilot-dataflash' and manifest['version'] == baseline['version'], 'APBIN manifest differs')
    require(manifest['license'] == baseline['license'], 'APBIN license differs')
    output.mkdir(parents=True)
    for identifier, files in [('ardupilot-dataflash', {selected.name: apbin_bytes, 'manifest.json': manifest_bytes}),
                              ('toolbox-fft', fft_files)]:
        directory = output/identifier
        directory.mkdir()
        for name, data in files.items():
            (directory/name).write_bytes(data)
    records = [{'path': p.relative_to(output).as_posix(), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
               for p in sorted(output.rglob('*')) if p.is_file()]
    record = {'kind': 'native-test-inputs-only-not-release-payload', 'platform': platform,
              'fft_url': spec['url'], 'fft_archive_sha256': digest,
              'apbin_source_commit': baseline['commit'], 'apbin_version': manifest['version'], 'files': records}
    # Keep provenance outside the plugin root: exactly two inputs enter the test.
    output.with_name(output.name+'-identity.json').write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8')
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT)
    parser.add_argument('--build', type=Path, default=Path('build'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--config', default='RelWithDebInfo')
    parser.add_argument('--platform', choices=['linux-x86_64', 'windows-x86_64'],
                        default='windows-x86_64' if os.name == 'nt' else 'linux-x86_64')
    parser.add_argument('--fft-archive', type=Path, help='Use already verified input offline; otherwise download the locked official ZIP')
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.build, args.output, args.config, args.platform, args.fft_archive), indent=2))
