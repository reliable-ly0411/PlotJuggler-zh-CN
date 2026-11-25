#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Real-process checks for console-independent, invocation-owned Qt evidence."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest

WRAPPER = Path(__file__).resolve().parents[1]/'cmake/run_qt_test.py'
TEXT = 'PASS   : SyntheticTest::flow()\r\nTotals: 3 passed, 0 failed, 0 skipped, 0 blacklisted, 1ms\r\n'


class QtTestLogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='Qt log with spaces ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.runner = self.root/'file_logger.py'
        self.receipt = self.root/'receipt.json'
        self.runner.write_text(textwrap.dedent('''\
            import json
            import os
            from pathlib import Path
            import sys
            import time
            log = Path(sys.argv[sys.argv.index('-o') + 1].removesuffix(',txt'))
            assert not log.exists(), 'Cannot reuse a previous log'
            Path(os.environ['RECEIPT']).write_text(json.dumps({
                'log': str(log), 'cwd': os.getcwd(), 'pid': os.getpid()}), encoding='utf-8')
            mode = os.environ['MODE']
            if mode == 'missing':
                raise SystemExit(0)
            log.write_bytes(b'' if mode == 'empty' else os.environ['TEXT'].encode('utf-8'))
            if mode == 'timeout':
                time.sleep(30)
            raise SystemExit(7 if mode == 'failure' else 0)
            '''), encoding='utf-8')

    def run_wrapper(self, mode='pass', timeout=10, executable=None):
        """Launch a real child which writes a file but has no console output."""
        return subprocess.run([sys.executable, str(WRAPPER), '--timeout', str(timeout), '--',
                               executable or sys.executable, str(self.runner)],
                              cwd=self.root,
                              env={**os.environ, 'MODE': mode, 'TEXT': TEXT, 'RECEIPT': str(self.receipt)},
                              capture_output=True, timeout=15)

    def test_exact_bytes_cwd_and_fresh_log_on_repeated_runs(self):
        paths = []
        for _ in range(2):
            result = self.run_wrapper()
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, TEXT.encode('utf-8'))
            receipt = json.loads(self.receipt.read_text(encoding='utf-8'))
            self.assertEqual(Path(receipt['cwd']), self.root)
            paths.append(receipt['log'])
            self.assertFalse(Path(receipt['log']).parent.exists())
        self.assertNotEqual(*paths)

    def test_child_failure_cannot_be_overridden_by_a_successful_log(self):
        result = self.run_wrapper('failure')
        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertEqual(result.stdout, TEXT.encode('utf-8'))

    def test_missing_or_empty_log_rejects_success_exit_and_stale_cwd_log(self):
        (self.root/'result.txt').write_text(TEXT, encoding='utf-8')
        for mode in ('missing', 'empty'):
            with self.subTest(mode=mode):
                result = self.run_wrapper(mode)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, b'')
                self.assertIn(b'nonempty text log', result.stderr)

    def test_timeout_fails_and_retains_partial_log(self):
        result = self.run_wrapper('timeout', timeout=1)
        self.assertEqual(result.returncode, 124, result.stderr)
        self.assertEqual(result.stdout, TEXT.encode('utf-8'))
        if os.name == 'posix':
            pid = json.loads(self.receipt.read_text(encoding='utf-8'))['pid']
            with self.assertRaises(ProcessLookupError):
                os.kill(pid, 0)

    def test_missing_executable_fails(self):
        result = self.run_wrapper(executable=str(self.root/'missing-executable'))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'Cannot launch Qt test', result.stderr)


if __name__ == '__main__':
    unittest.main()
