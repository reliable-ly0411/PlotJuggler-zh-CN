#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Require complete, non-skipped evidence for the native file-picker regressions."""
import argparse
from pathlib import Path
import re
import xml.etree.ElementTree as ET

PREFIX = 'pj_widgets_tests.FileDialogStartFolderTest.'
CASES = {
    PREFIX + name for name in (
        'ReachableFolderIsUsedAndNoticeHidden',
        'SlowFolderFallsBackToHomeWithoutBlocking',
        'MissingFolderThatAnswersFastKeepsNoticeHidden',
        'PersistedQtMemoryDropsLastVisitedAndDeadShortcuts',
    )
}


def audit(report):
    """Reject missing, duplicate, skipped, failed or truncated CTest records."""
    root = ET.parse(report).getroot()
    expected = {'tests': '4', 'failures': '0', 'disabled': '0', 'skipped': '0'}
    if root.tag != 'testsuite' or any(root.get(k) != v for k, v in expected.items()):
        raise ValueError('File-dialog suite must contain exactly four successful tests')
    if root.get('errors', '0') != '0':
        raise ValueError('File-dialog suite reports errors')
    cases = list(root.iter('testcase'))
    if len(cases) != 4 or {c.get('name') for c in cases} != CASES:
        raise ValueError('File-dialog cases are missing, duplicated or unexpected')
    for case in cases:
        name = case.get('name')
        output = '\n'.join(node.text or '' for node in case.findall('system-out'))
        ok_marker = '[       OK ] ' + name.removeprefix('pj_widgets_tests.')
        if (case.get('status') != 'run'
                or any(case.find(tag) is not None for tag in ('failure', 'error', 'skipped'))
                or '[  PASSED  ] 1 test.' not in output or ok_marker not in output
                or re.search(r'\[\s*(?:SKIPPED|FAILED)\s*\]|truncat|test output was removed|exceeds the threshold', output, re.IGNORECASE)):
            raise ValueError(f'Incomplete or unsuccessful file-dialog evidence: {name}')
    return sorted(CASES)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--junit', type=Path, required=True)
    print('\n'.join(audit(parser.parse_args().junit)))
