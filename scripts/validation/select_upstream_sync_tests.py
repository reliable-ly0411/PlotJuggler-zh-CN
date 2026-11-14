#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Select changed-surface regressions for the SDK dev2 / mesh-map sync."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

if len(sys.argv) == 3 and sys.argv[1] == '--verify-log':
    log = Path(sys.argv[2]).read_text(encoding='utf-8', errors='replace')
    required = 'DialogShutdownTest.CancelThenRejectAtDialogDoesNotCancelTheNextLoad'
    if not re.search(r'\[\s*OK\s*\]\s+' + re.escape(required) + r'\b', log):
        raise SystemExit('Required FileLoader regression did not pass')
    parent = 'FileLoaderShutdownProgressRegression.QueuedProgressAfterJoinMustNotAccessDestroyedContext'
    if not re.search(r'\[\s*OK\s*\]\s+' + re.escape(parent) + r'\b', log):
        raise SystemExit('Required subprocess-owning regression did not pass')
    if re.search(r'\[\s*SKIPPED\s*\]', log):
        raise SystemExit('GTest reported skipped coverage')
    print('Required FileLoader regression passed without GTest skips')
    raise SystemExit(0)

build, output = map(Path, sys.argv[1:])
data = json.loads(subprocess.check_output(
    ['ctest', '--test-dir', str(build), '-C', 'RelWithDebInfo', '--show-only=json-v1'], text=True))
names = [t['name'] for t in data['tests']]
# FileLoaderTest is a single CTest registration containing multiple GTest cases.
# Check the built runner's list, rather than expecting a per-case CTest name.
loader = next((t for t in data['tests'] if t['name'] == 'FileLoaderTest'), None)
if not loader or not loader.get('command'):
    raise SystemExit('Missing built FileLoaderTest command')
listing = subprocess.check_output(
    [*loader['command'], '--gtest_list_tests'], text=True,
    env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen'})
suite = ''
cases = set()
for line in listing.splitlines():
    if line and not line[0].isspace() and line.rstrip().endswith('.'):
        suite = line.strip()
    elif line.startswith('  '):
        cases.add(suite + line.strip().split(' #', 1)[0])
required = 'DialogShutdownTest.CancelThenRejectAtDialogDoesNotCancelTheNextLoad'
if required not in cases:
    raise SystemExit('Missing built GTest case: ' + required)
patterns = {
    'file_loading': r'^FileLoaderTest$',
    'mcp_null_samples': r'^pj_app_gui_tests[.]McpServerTest[.]ANullSampleIsNotReadAsZero$',
    'mcp_export': r'^pj_app_gui_tests[.]McpServerTest[.]Export',
    'mesh_core': r'^pj_scene3d_core_tests[.]MeshMap',
    'mesh_grid_ui': r'^pj_scene3d_widget_tests[.](MeshMap|GridMap)',
    'process_isolation': r'^pj_app_gui_tests[.]TestProcessIsolationTest[.]',
    'preferences_languages': r'^pj_app_gui_tests[.]PreferencesLanguageTest[.]',
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
