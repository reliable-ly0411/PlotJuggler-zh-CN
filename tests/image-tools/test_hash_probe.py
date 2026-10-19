# SPDX-License-Identifier: MPL-2.0
"""Exercise compiled probes: logging must not turn a successful report into failure."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def check(buffer_probe, image_probe):
    fixture = bytes([17, 39, 82, 255, 92, 7, 121, 255,
                     9, 11, 241, 255, 187, 45, 13, 255])
    digest = hashlib.sha256(fixture).hexdigest()
    probes = [(Path(buffer_probe).resolve(), ('rows', 'offset', 'once')),
              (Path(image_probe).resolve(), ('image-direct', 'image-copy'))]
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        source = root / 'fixture.rgba'
        source.write_bytes(fixture)
        for executable, modes in probes:
            for mode in modes:
                for matches in (True, False):
                    output = root / f'{mode}-{matches}'
                    expected = digest if matches else '0' * 64
                    result = subprocess.run(
                        [str(executable), str(source), '2', '2', mode, '2', str(output), expected],
                        capture_output=True, text=True, timeout=30,
                        env={**os.environ, 'PJ_HASH_SECONDS': '5'},
                    )
                    wanted = 0 if matches else 15
                    if result.returncode != wanted:
                        raise RuntimeError(f'{mode} matches={matches}: expected exit {wanted}, '
                                           f'got {result.returncode}\n{result.stdout}\n{result.stderr}')
                    report = json.loads((output / 'report.json').read_text())
                    if report['fixture_final_sha256'] != digest:
                        raise RuntimeError(f'{mode}: source fixture changed')
                    if matches:
                        if report['failure'] or not result.stdout.startswith('PASS '):
                            raise RuntimeError(f'{mode}: incorrect successful report')
                    else:
                        if report['failure']['initial_sha256'] != digest:
                            raise RuntimeError(f'{mode}: mismatch evidence missing')
                        if not result.stdout.startswith('FAIL ') or (output / 'capture.rgba').read_bytes() != fixture:
                            raise RuntimeError(f'{mode}: mismatch capture missing or changed')
                    print(f'PASS {mode}: matches={matches}, exit={wanted}')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('usage: test_hash_probe.py <hash_buffer_probe> <hash_image_probe>')
    check(*sys.argv[1:])
