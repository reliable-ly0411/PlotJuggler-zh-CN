#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Pin ordering across candidate, stable and subsequent localization packages."""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import unittest

spec = importlib.util.spec_from_file_location('version_map', Path(__file__).resolve().parents[1] /
                                            'packaging/localization/version_map.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ReleaseVersionsTest(unittest.TestCase):
    def test_exact_candidate(self):
        v = module.versions('4.0.0-zh.1.rc.1')
        self.assertEqual(v['tag'], 'v4.0.0-zh.1.rc.1')
        self.assertEqual(v['deb'], '4.0.0~zh.1~rc.1-1')
        self.assertEqual(v['ifw'], '4.0.0.1.0.1')

    def test_monotonic_sequence(self):
        sequence = ['4.0.0-zh.1.rc.1', '4.0.0-zh.1.rc.2', '4.0.0-zh.1',
                    '4.0.0-zh.2.rc.1', '4.0.0-zh.2', '4.0.1-zh.1.rc.1']
        mapped = list(map(module.versions, sequence))
        for a, b in zip(mapped, mapped[1:]):
            self.assertLess(tuple(map(int, a['ifw'].split('.'))), tuple(map(int, b['ifw'].split('.'))))
            if shutil.which('dpkg'):
                subprocess.run(['dpkg', '--compare-versions', a['deb'], 'lt', b['deb']], check=True)

    def test_reject_invalid(self):
        for value in ['4.0.0', 'v4.0.0-zh.1', '4.0.0-zh.01.rc.1', '4.0.0-zh.1.rc.01',
                      '4.0.0-zh.1.dev.1', '3.18.0-zh.1']:
            with self.assertRaises(ValueError):
                module.versions(value)


if __name__ == '__main__':
    unittest.main()
