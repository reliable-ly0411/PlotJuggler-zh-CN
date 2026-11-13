#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Boundary checks for the explicitly enabled launcher acceptance hook."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

LAUNCHER = Path(sys.argv.pop(1)).resolve()

class AcceptanceBoundary(unittest.TestCase):
    def test_rejected_options_and_existing_output_do_not_touch_settings(self):
        with tempfile.TemporaryDirectory(prefix='launcher 边界 ') as name:
            root = Path(name)
            config = root / 'config'
            ini = config / 'PlotJuggler/io.plotjuggler.PlotJuggler.zh-CN.ini'
            ini.parent.mkdir(parents=True)
            ini.write_text('[General]\nAcceptanceSentinel=untouched\n', encoding='utf-8')
            before = hashlib.sha256(ini.read_bytes()).hexdigest()
            nonce = 'a' * 64
            (root / 'launcher-acceptance.json').write_text(json.dumps({'schema': 1, 'purpose': 'launcher-gui-acceptance', 'nonce': nonce, 'ini': 'PlotJuggler/io.plotjuggler.PlotJuggler.zh-CN.ini', 'before_sha256': before}), encoding='utf-8')
            output = root / 'case-existing'
            output.mkdir()
            for index, variation in enumerate(('existing', 'launch', 'duplicate', 'missing', 'invalid', 'nonce', 'unknown', 'equals', 'hash')):
                candidate = output if variation == 'existing' else root / ('case-' + str(index))
                args = ['--config-dir', str(config), '--self-test-launcher-ui', str(candidate), '--launcher-test-scenario', 'start', '--launcher-test-nonce', nonce]
                if variation == 'launch': args += ['--launch']
                if variation == 'duplicate': args += ['--launcher-test-scenario', 'start']
                if variation == 'missing': args.pop()
                if variation == 'invalid': args[5] = 'invalid'
                if variation == 'nonce': args[-1] = 'Z' * 64
                if variation == 'unknown': args += ['--launcher-test-unknown']
                if variation == 'equals': args += ['--self-test-launcher-ui=bad']
                if variation == 'hash':
                    marker = json.loads((root / 'launcher-acceptance.json').read_text())
                    marker['before_sha256'] = '0' * 64
                    (root / 'launcher-acceptance.json').write_text(json.dumps(marker))
                result = subprocess.run([str(LAUNCHER), *args], env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen'}, capture_output=True, timeout=10)
                self.assertNotEqual(result.returncode, 0, args)
                self.assertEqual(hashlib.sha256(ini.read_bytes()).hexdigest(), before)
                if variation == 'existing': self.assertEqual(list(output.iterdir()), [])
                else: self.assertFalse(candidate.exists(), args)


if __name__ == '__main__':
    unittest.main()
