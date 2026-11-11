#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Combine disjoint CTest passes without losing cases, failures or captured output."""
import argparse
import copy
from decimal import Decimal
import json
from pathlib import Path
import xml.etree.ElementTree as ET


CTEST_TRUNCATION_MARKER = '[This part of the test output was removed'


NATIVE_CASES = {
    'pj_dialog_host_tests.WidgetBindingMarkdown.RendersGitHubMarkdownUnicodeAndBlocksEmbeddedResources',
    'pj_widgets_tests.FileDialogStartFolderTest.PersistedQtMemoryDropsLastVisitedAndDeadShortcuts',
    'pj_app_gui_tests.MainWindowFileDropTest.FileDragOverAnyDropTargetIsTakenAsACopy',
    'pj_app_gui_tests.MainWindowFileDropLoadingTest.MoveOnlyAndIgnoreActionRejectWithoutLoading',
    'pj_app_gui_tests.MainWindowFileDropLoadingTest.CopyActionRejectsNonFileUrlsAndTextWithoutLoading',
    'pj_app_gui_tests.MainWindowFileDropLoadingTest.CopyOnlyDropLoadsAndRetainsSourceBytes',
    'pj_app_gui_tests.MainWindowFileDropLoadingTest.ChinesePathDropLoadsAfterReturningAndRetainsSourceBytes',
    'pj_app_gui_tests.MainWindowFileDropLoadingTest.MultipleFilesAndRepeatedDropKeepValuesSeparateAndSourcesIntact',
    'pj_app_gui_tests.MainWindowFileDropLoadingTest.ClosingAndDestroyingWindowCancelsQueuedDrop',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def merge_reports(listing, reports):
    """Verify exact coverage of discovery, retaining each original testcase subtree."""
    names = [row['name'] for row in listing['tests']]
    require(names and all(isinstance(name, str) and name.strip() for name in names),
            'Missing or invalid CTest name')
    require(len(names) == len(set(names)), 'Empty or duplicate CTest discovery')
    require(all(isinstance(row.get('command'), list) and row['command'] and
                isinstance(row['command'][0], str) and row['command'][0].strip() and
                all(isinstance(part, str) for part in row['command']) for row in listing['tests']),
            'Missing or invalid discovered test command')
    expected = set(names)
    seen = set()
    merged = ET.Element('testsuite', name='Windows native tests')
    totals = {'tests': 0, 'failures': 0, 'disabled': 0, 'skipped': 0}
    duration = Decimal(0)
    for report in reports:
        require(report.tag == 'testsuite', 'Expected one CTest testsuite per report')
        cases = report.findall('testcase')
        require(cases, 'Empty CTest pass')
        require(int(report.get('tests', '-1')) == len(cases), 'Report test count differs from its cases')
        failures = skipped = disabled = 0
        for case in cases:
            name = case.get('name')
            require(isinstance(name, str) and name.strip(), 'Missing or invalid report test name')
            require(name in expected, f'Unexpected CTest case: {name}')
            require(name not in seen, f'Duplicate CTest case: {name}')
            seen.add(name)
            failed = case.find('failure') is not None or case.find('error') is not None
            skip = case.find('skipped') is not None
            status = case.get('status')
            require(status in {'run', 'fail', 'notrun', 'disabled'}, f'Unknown CTest status: {status}')
            require(not (failed and skip), f'Failure and skip coexist: {name}')
            require((status == 'fail') == failed, f'Failure/status mismatch: {name}')
            require((status == 'notrun') == skip, f'Skip/status mismatch: {name}')
            require(case.find('system-out') is not None, f'Missing captured stdout element: {name}')
            require(all(CTEST_TRUNCATION_MARKER not in (case.findtext(stream) or '')
                        for stream in ('system-out', 'system-err')), f'Truncated CTest output: {name}')
            case_time = Decimal(case.get('time', '0'))
            require(case_time.is_finite() and case_time >= 0, f'Invalid testcase time: {name}')
            failures += int(failed)
            skipped += int(skip)
            disabled += int(status == 'disabled')
            merged.append(copy.deepcopy(case))
        require(int(report.get('failures', '0')) == failures, 'Report failure count differs from its cases')
        if 'errors' in report.attrib:
            require(int(report.get('errors')) == sum(case.find('error') is not None for case in cases),
                    'Report error count differs from its cases')
        require(int(report.get('skipped', '0')) == skipped, 'Report skip count differs from its cases')
        require(int(report.get('disabled', '0')) == disabled, 'Report disabled count differs from its cases')
        totals['tests'] += len(cases)
        totals['failures'] += failures
        totals['skipped'] += skipped
        totals['disabled'] += disabled
        elapsed = Decimal(report.get('time', '0'))
        require(elapsed.is_finite() and elapsed >= 0, 'Invalid report time')
        duration += elapsed
    require(seen == expected, f'Missing CTest cases: {sorted(expected - seen)}')
    for key, value in totals.items():
        merged.set(key, str(value))
    merged.set('time', str(duration))
    return merged


def validate_native_regressions(listing, report):
    """Require all nine native portability cases, including both drop fixtures."""
    names = {row['name'] for row in listing['tests']}
    require(NATIVE_CASES <= names, 'Required native regressions missing from full discovery')
    focused = {'tests': [row for row in listing['tests'] if row['name'] in NATIVE_CASES]}
    checked = merge_reports(focused, [report])
    require(checked.get('failures') == checked.get('skipped') == checked.get('disabled') == '0',
            'Native portability regressions must all execute successfully')
    for case in checked.findall('testcase'):
        output = case.findtext('system-out') or ''
        require('[  PASSED  ] 1 test.' in output and '[  SKIPPED ]' not in output and
                '[  FAILED  ]' not in output, f'Missing native GTest pass evidence: {case.get("name")}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ctest-list', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--native-regressions', type=Path)
    parser.add_argument('reports', type=Path, nargs='+')
    args = parser.parse_args()
    listing = json.loads(args.ctest_list.read_text(encoding='utf-8'))
    merged = merge_reports(listing, [ET.parse(path).getroot() for path in args.reports])
    ET.ElementTree(merged).write(args.output, encoding='utf-8', xml_declaration=True)
    print(f"Combined {merged.get('tests')} unique tests: {merged.get('failures')} failures, "
          f"{merged.get('skipped')} skipped")
    if args.native_regressions:
        validate_native_regressions(listing, ET.parse(args.native_regressions).getroot())
    # Never turn failing CTest passes green merely because their coverage is complete.
    return 1 if int(merged.get('failures', '0')) else 0


if __name__ == '__main__':
    raise SystemExit(main())
