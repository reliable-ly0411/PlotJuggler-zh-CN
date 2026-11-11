#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Relay a fresh Qt text log to CTest without depending on the child's console.

This transports evidence only. Qt failures and timeouts still fail the process;
the separate result auditor checks actual flow markers, totals and internal skips.
"""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    """Use an invocation-owned log; a previous successful run cannot supply it."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--timeout', type=float, required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command or not 0 < args.timeout < float('inf'):
        parser.error('a command and a finite positive timeout are required')
    with tempfile.TemporaryDirectory(prefix='pj-qt-test-') as directory:
        log = Path(directory)/'result.txt'
        try:
            result = subprocess.run(command + ['-o', str(log) + ',txt'], timeout=args.timeout)
            code = result.returncode
        except subprocess.TimeoutExpired:
            # subprocess.run kills and waits for the direct child on timeout.
            print('Qt test exceeded its child deadline', file=sys.stderr)
            code = 124
        except OSError as error:
            print('Cannot launch Qt test: ' + str(error), file=sys.stderr)
            code = 1
        data = log.read_bytes() if log.is_file() else b''
        if data:
            sys.stdout.buffer.write(data)
            sys.stdout.buffer.flush()
        else:
            print('Qt test did not produce a nonempty text log', file=sys.stderr)
            code = code or 1
        if code:
            print(f'Qt test process failed with exit code {code}', file=sys.stderr)
        # Windows exception codes may exceed a portable shell exit status. Never
        # let integer truncation turn a failed child into a successful wrapper.
        return code if 0 <= code <= 255 else 1


if __name__ == '__main__':
    sys.exit(main())
