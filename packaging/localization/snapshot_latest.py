#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Record Latest identity, including a repository with only prereleases."""
import json
from pathlib import Path
import subprocess
import sys

result = subprocess.run(['gh', 'api', f'repos/{sys.argv[1]}/releases/latest'],
                        capture_output=True, text=True, encoding='utf-8', check=False)
data = json.loads(result.stdout)
if result.returncode:
    # Only a genuine no-Latest response is allowed. Auth/rate-limit/network
    # failures must not silently masquerade as an empty prior release state.
    assert data.get('message') == 'Not Found' and str(data.get('status')) == '404', result.stderr
    identity = None
else:
    identity = data['id']
    assert isinstance(identity, int) and identity > 0
Path(sys.argv[2]).write_text(json.dumps({'id': identity}) + '\n', encoding='utf-8')
