#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Offline APBIN/FFT result gate. Never builds, launches a GUI or downloads.

This audits recorded evidence; it does not establish that a Windows build ran,
bind a report to source by itself, or replace screenshot pixel review.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import xml.etree.ElementTree as ET

LANGUAGES = ('en_US', 'zh_CN', 'zh_TW')
EXPECTED = {'PluginDisplayMetadataTest'} | {
    'PluginFeedbackMainWindow-' + language for language in LANGUAGES
}
STAGES = ('apbin', 'fft-menu', 'fft-initial', 'fft-computed', 'fft-exported', 'language-switch')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def audit_cases(root, allow_other_cases=False):
    cases = root.findall('.//testcase')
    names = [case.get('name') for case in cases]
    selected = [case for case in cases if case.get('name') in EXPECTED]
    require({case.get('name') for case in selected} == EXPECTED,
            'Missing required metadata or three-language host case')
    require(len(selected) == len(EXPECTED), 'Duplicate required test case')
    if not allow_other_cases:
        require(set(names) == EXPECTED and len(names) == len(EXPECTED),
                'Unexpected test selection; use the exact four-case CTest filter')
    result = []
    for case in selected:
        name = case.get('name')
        require(case.get('status', 'run') == 'run', name + ': not executed')
        require(not any(case.find(tag) is not None for tag in ('failure', 'error', 'skipped')),
                name + ': JUnit failure/error/skip')
        output = '\n'.join(case.findtext(tag) or '' for tag in ('system-out', 'system-err'))
        require(not re.search(r'(^|\n)\s*(?:SKIP\s*:|FAIL!\s*:|QFATAL\s*:|\[\s*SKIPPED\s*\])', output),
                name + ': underlying runner reports a skip/failure')
        totals = re.findall(r'Totals:\s*(\d+) passed,\s*(\d+) failed,\s*(\d+) skipped,\s*(\d+) blacklisted', output)
        require(len(totals) == 1, name + ': missing or ambiguous Qt result summary')
        passed, failed, skipped, blacklisted = map(int, totals[0])
        require(passed > 0 and failed == skipped == blacklisted == 0,
                name + ': nonzero failures/skips/blacklist')
        marker = ('PluginDisplayMetadataTest::installedApbin()' if name == 'PluginDisplayMetadataTest'
                  else 'PluginFeedbackTest::mainWindowFlow()')
        require(re.search(r'^PASS\s*:\s*' + re.escape(marker) + r'\s*$', output, re.M) is not None,
                name + ': actual installed-plugin flow did not pass')
        result.append({'name': name, 'qt_passed_including_init_cleanup': passed,
                       'qt_failed': failed, 'qt_skipped': skipped, 'qt_blacklisted': blacklisted})
    return sorted(result, key=lambda row: row['name'])


def audit_images(directory):
    records = []
    for language in LANGUAGES:
        for stage in STAGES:
            path = directory / f'full-{stage}-{language}.png'
            require(path.is_file(), 'Missing screenshot: ' + path.name)
            data = path.read_bytes()
            require(len(data) >= 33 and data[:8] == b'\x89PNG\r\n\x1a\n' and data[12:16] == b'IHDR',
                    'Invalid PNG header: ' + path.name)
            width, height = struct.unpack('>II', data[16:24])
            require(width > 0 and height > 0, 'Empty screenshot: ' + path.name)
            records.append({'name': path.name, 'width': width, 'height': height,
                            'sha256': hashlib.sha256(data).hexdigest()})
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ctest-list', type=Path)
    parser.add_argument('--junit', type=Path)
    parser.add_argument('--screenshots', type=Path)
    parser.add_argument('--allow-other-cases', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.ctest_list:
        listing = json.loads(args.ctest_list.read_text(encoding='utf-8'))
        names = [row['name'] for row in listing['tests']]
        require(set(names) == EXPECTED and len(names) == len(EXPECTED), 'Incomplete or unexpected feedback CTest selection')
        require(all(row.get('command') for row in listing['tests']), 'Missing native test executable')
        args.output.write_text(json.dumps({'result': 'PASS_CTEST_SELECTION_ONLY', 'tests': names}, indent=2)+'\n', encoding='utf-8')
        return
    if not args.junit or not args.screenshots:
        parser.error('--junit and --screenshots are required for recorded-result validation')
    rows = audit_cases(ET.parse(args.junit).getroot(), args.allow_other_cases)
    images = audit_images(args.screenshots)
    result = {'result': 'PASS_RECORDED_EVIDENCE_ONLY', 'required_ctest_cases': len(rows),
              'new_product_execution': False, 'windows_execution_established': False,
              'pixel_review_performed': False, 'junit_sha256': hashlib.sha256(args.junit.read_bytes()).hexdigest(),
              'scope': 'four APBIN/FFT native cases; separate full platform and final installed-package gates remain',
              'cases': rows, 'images': images}
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'result': result['result'], 'cases': len(rows), 'images': len(images)}))


if __name__ == '__main__':
    main()
