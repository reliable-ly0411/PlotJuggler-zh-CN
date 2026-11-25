# SPDX-License-Identifier: MPL-2.0
"""Record the identities of both FFmpeg tools' resolved dynamic libraries."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys


HEADERS = ('/usr/bin/ffmpeg:', '/usr/bin/ffprobe:')


def dependency_paths(text):
    """Exclude only the two expected ldd input headers, retaining every path."""
    lines = text.splitlines()
    assert all(lines.count(header) == 1 for header in HEADERS), 'missing or repeated ldd input header'
    assert 'not found' not in text, 'ldd reported a missing dependency'
    text = '\n'.join(line for line in lines if line not in HEADERS)
    paths = sorted(set(re.findall(r'(?<![A-Za-z0-9_])(/[^\s()]+)', text)))
    assert paths, 'ldd did not report any absolute dynamic library paths'
    return paths


def record_paths(paths):
    """Hash every resolved file and retain the actual dpkg ownership response."""
    records = []
    for value in paths:
        path = Path(value)
        actual = path.resolve(strict=True)
        assert actual.is_file(), f'ldd path is not a regular file: {value}'
        with actual.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        package = subprocess.run(['dpkg-query', '-S', value], capture_output=True, text=True, check=False,
                                 env={**os.environ, 'LC_ALL': 'C'})
        records.append({'path': value, 'resolved_path': str(actual), 'sha256': digest,
                        'dpkg_query_exit': package.returncode, 'dpkg_query_stdout': package.stdout,
                        'dpkg_query_stderr': package.stderr})
    return records


def main(evidence):
    """Use the preserved raw ldd output and write deterministic path-ordered records."""
    text = (evidence / 'dynamic-libraries.txt').read_text(encoding='utf-8')
    records = record_paths(dependency_paths(text))
    (evidence / 'dynamic-library-identities.json').write_text(json.dumps(records, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    if not __debug__:
        raise SystemExit('Do not disable dynamic-library validation with Python -O')
    main(Path(sys.argv[1]))
