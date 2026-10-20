#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Exercise initial layout restoration through the real native application."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile

spec = importlib.util.spec_from_file_location(
    'verify_package', Path(__file__).parents[1] / 'packaging/localization/verify_package.py')
acceptance = importlib.util.module_from_spec(spec)
spec.loader.exec_module(acceptance)


def check(app, plugins, log):
    """No curve reattachment, zoom command, or cache invalidation is injected."""
    assert hashlib.sha256(log.read_bytes()).hexdigest() == acceptance.LOG_SHA
    with tempfile.TemporaryDirectory(prefix='pj4-bin-layout-') as directory:
        work = Path(directory)
        layout = acceptance.write_bin_layout(work, log)
        # A native build needs its development DLL paths; only final-package
        # verification strips those paths. Keep the publication regression separate.
        env = os.environ.copy()
        env.update(HOME=str(work), XDG_CONFIG_HOME=str(work / 'config'),
                   XDG_DATA_HOME=str(work / 'data'), XDG_CACHE_HOME=str(work / 'cache'),
                   QT_FORCE_STDERR_LOGGING='1', QT_LOGGING_RULES='pj.runtime.ingest.info=true',
                   PJ_DISABLE_TELEMETRY='1')
        for language in ['zh_CN', 'en_US']:
            state = work / f'plot-{language}.json'
            command = [str(app), '--plugin-dir', str(plugins), '--language', language, '--nosplash',
                       '--disable-opengl', '--layout', str(layout), '--exit-after-layout',
                       '--exit-after-layout-timeout', '60', '--dump-plot-state', str(state)]
            result = subprocess.run(command, env=env, capture_output=True, text=True,
                                    encoding='utf-8', errors='replace', timeout=80)
            print(result.stdout + result.stderr)
            assert result.returncode == 0, f'{language}: app exit {result.returncode}'
            acceptance.validate_bin_plot_state(json.loads(state.read_text(encoding='utf-8')))
            print(f'{language}: initial restored BIN curve has finite visible samples')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', type=Path, required=True)
    parser.add_argument('--plugins', type=Path, required=True)
    parser.add_argument('--real-bin', type=Path, required=True)
    args = parser.parse_args()
    check(args.app.resolve(), args.plugins.resolve(), args.real_bin.resolve())
