#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Pin ordering across candidate, stable and subsequent localization packages."""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

spec = importlib.util.spec_from_file_location('version_map', Path(__file__).resolve().parents[1] /
                                            'packaging/localization/version_map.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
sys.modules['version_map'] = module
promotion_spec = importlib.util.spec_from_file_location('resolve_promotion', Path(__file__).resolve().parents[1] /
                                                       'packaging/localization/resolve_promotion.py')
promotion = importlib.util.module_from_spec(promotion_spec)
promotion_spec.loader.exec_module(promotion)


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
                      '4.0.0-zh.1.dev.1', '3.18.0-zh.1', '4.00.0-zh.1.rc.1', '4.0.00-zh.1']:
            with self.assertRaises(ValueError):
                module.versions(value)


class ReleasePromotionTest(unittest.TestCase):
    def test_bind_exact_run_attempt(self):
        ref = 'zh-CN-4.x-ci/publish-accepted-v4-0-0-zh-1-rc-1-run-12345-attempt-2'
        self.assertEqual(promotion.resolve(ref, '4.0.0-zh.1.rc.1'),
                         {'RELEASE_TAG': 'v4.0.0-zh.1.rc.1', 'CANDIDATE_RUN': '12345',
                          'CANDIDATE_ATTEMPT': '2'})
        subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] /
                                            'scripts/check_branch_name.py'), ref], check=True)

    def test_reject_unbound_or_wrong_version(self):
        prefix = 'zh-CN-4.x-ci/publish-accepted-'
        for value in ['v4-0-0-zh-1-rc-1', 'v4-0-0-zh-1-rc-2-run-12345-attempt-1',
                      'v4.0.0-zh.1.rc.1-run-12345-attempt-1',
                      'v4-0-0-zh-1-rc-1-run-12345-attempt-0',
                      'v4-0-0-zh-1-rc-1-run-012345-attempt-1',
                      'v4-0-0-zh-1-rc-1-run-12345-attempt-1-extra']:
            with self.assertRaises(ValueError):
                promotion.resolve(prefix + value, '4.0.0-zh.1.rc.1')


if __name__ == '__main__':
    unittest.main()
