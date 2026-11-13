#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Select explicit changed-surface regression cases, never the full CTest suite."""
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
    'mcp': r'Mcp(Envelope|HttpAccess|HttpParsing|Lifecycle|Owners|ServerTest|QueuedLoadTest|EndpointTest)',
    'mcp_bridge': r'^mcp_bridge_test[.$]',
    'file_selection': r'FileSelectionServiceTest',
    'file_loading': r'(FileLoaderTest|FileLoaderDrop|MainWindowFileDrop)',
    'main_window_rhi': r'MainWindowRhiWindowTest',
    'curve_timeline': r'(CurveListPanelTest|TimelineWidgetTest)',
    'legend_tabs': r'(PlotWidgetLegendToggle|TabbedWidgetTab|TabbedPlotDuplicate)',
    'mixed_rhi': r'^rhi_mixed_dock_test\.opengl$',
    'model_cache': r'^scene3d_rhi_model_cache_test\.opengl$',
}
if os.name == 'nt':
    patterns.pop('mcp_bridge')  # CMake defines this end-to-end target on Linux only.
    patterns['mixed_rhi'] = r'^rhi_mixed_dock_test\.d3d11$'
    patterns['model_cache'] = r'^scene3d_rhi_model_cache_test\.d3d11$'
selected = {group: [n for n in names if re.search(pattern, n)]
            for group, pattern in patterns.items()}
output.mkdir(exist_ok=True)
(output / 'selection.json').write_text(json.dumps(selected, indent=2) + '\n')
missing = [g for g, ns in selected.items() if not ns]
if missing:
    raise SystemExit('Missing registered targeted tests: ' + ', '.join(missing))
unique = sorted({n for ns in selected.values() for n in ns})
if len(unique) == len(names):
    raise SystemExit('Refusing accidental full-suite selection')
(output / 'test-names.txt').write_text('\n'.join(unique) + '\n')
print(f'Selected {len(unique)} of {len(names)} registered tests in {len(patterns)} risk groups')
