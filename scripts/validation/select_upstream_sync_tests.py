#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Select file-loading and numeric-locale regressions for the November 14 sync."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

build, output = map(Path, sys.argv[1:])
data = json.loads(subprocess.check_output(
    ['ctest', '--test-dir', str(build), '-C', 'RelWithDebInfo', '--show-only=json-v1'], text=True))
names = [t['name'] for t in data['tests']]
patterns = {
    'file_loading': r'(FileLoaderTest|FileLoaderDrop|DialogShutdownTest)',
    'cancel_regression': r'DialogShutdownTest\.CancelThenRejectAtDialogDoesNotCancelTheNextLoad',
}
if os.name != 'nt':
    # This Linux-only executable includes McpBridgeDecimalCommaTest.FiltersAndScriptsCompile.
    patterns['numeric_locale'] = r'McpBridgeDecimalCommaTest\.FiltersAndScriptsCompile'
    patterns['mcp_bridge'] = r'^mcp_bridge_test[.$]'
selected = {group: [n for n in names if re.search(pattern, n)] for group, pattern in patterns.items()}
output.mkdir(exist_ok=True)
(output / 'selection.json').write_text(json.dumps(selected, indent=2) + '\n')
missing = [g for g, ns in selected.items() if not ns]
if missing:
    raise SystemExit('Missing registered targeted tests: ' + ', '.join(missing))
unique = sorted({n for ns in selected.values() for n in ns})
(output / 'test-names.txt').write_text('\n'.join(unique) + '\n')
print(f'Selected {len(unique)} targeted tests in {len(patterns)} risk groups')
