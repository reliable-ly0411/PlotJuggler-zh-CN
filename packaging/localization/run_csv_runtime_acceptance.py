#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Run real CSV/FileLoader regressions only after the verified rebuilt DSO is staged."""
import argparse
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
EXPECTED = {'CsvRuntimeFileLoader_' + language for language in ['zh_CN', 'zh_TW', 'en_US']}
CASES = {'CsvRuntimeFileLoader.' + name for name in [
    'EmptyCsvWritesTranslatedPrefixedDiagnosticJson', 'ShortWarningContinue', 'ShortWarningAbort',
    'ShortWarningClose', 'LongWarningContinue', 'LongWarningAbort', 'LongWarningClose']}


def audit_results(report):
    """Reject partial CTest success and filtered/skipped/truncated underlying GTests."""
    root = ET.parse(report).getroot()
    totals = {'tests': '3', 'failures': '0', 'disabled': '0', 'skipped': '0'}
    if root.tag != 'testsuite' or any(root.get(key) != value for key, value in totals.items()) or root.get('errors', '0') != '0':
        raise ValueError('CSV runtime suite must contain exactly three executed successful language tests')
    cases = list(root.iter('testcase'))
    if len(cases) != 3 or {case.get('name') for case in cases} != EXPECTED:
        raise ValueError('CSV runtime languages are missing, duplicated or unexpected')
    for case in cases:
        output = '\n'.join(node.text or '' for node in case.findall('system-out'))
        started = re.findall(r'^\[ RUN      \] (\S+)\r?$', output, re.M)
        passed = re.findall(r'^\[       OK \] (\S+) \(\d+ ms\)\r?$', output, re.M)
        if (case.get('status') != 'run'
                or any(case.find(tag) is not None for tag in ('failure', 'error', 'skipped'))
                or len(started) != 7 or set(started) != CASES or len(passed) != 7 or set(passed) != CASES
                or len(re.findall(r'^\[  PASSED  \] 7 tests\.\r?$', output, re.M)) != 1
                or re.search(r'\[\s*(?:SKIPPED|FAILED)\s*\]|DISABLED TEST|Google Test filter|truncat|test output was removed|exceeds the threshold', output, re.I)):
            raise ValueError('Incomplete CSV runtime evidence: ' + str(case.get('name')))
    return sorted(EXPECTED)



def staged_csv(prefix):
    """Fail closed on missing, ambiguous, altered or unlocked staged plugin bytes."""
    record = json.loads((prefix / 'share/plotjuggler4/release.json').read_text(encoding='utf-8'))
    lock = json.loads((ROOT / 'packaging/localization/plugin-patches/source-lock.json').read_text(encoding='utf-8'))
    source = next(item for item in lock['plugins'] if item['id'] == 'csv-loader')
    matches = [item for item in record['localized_plugin_rebuilds'] if item['id'] == source['id']]
    assert len(matches) == 1, 'exactly one rebuilt CSV record is required'
    item = matches[0]
    for field in ['version', 'commit', 'sdk', 'patch_sha256']:
        assert item[field] == source[field], 'staged CSV source identity differs: ' + field
    binaries = [entry for entry in item['files'] if Path(entry['path']).suffix in ('.so', '.dll')]
    assert len(binaries) == 1, 'exactly one rebuilt CSV binary is required'
    entry = binaries[0]
    binary = (prefix / entry['path']).resolve()
    assert binary.parent == (prefix / 'lib/plotjuggler/plugins/csv-loader').resolve()
    assert hashlib.sha256(binary.read_bytes()).hexdigest() == entry['sha256'], 'staged CSV binary hash differs'
    return binary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--prefix', type=Path, required=True)
    args = parser.parse_args()
    build, prefix = args.build.resolve(), args.prefix.resolve()
    binary = staged_csv(prefix)
    subprocess.run(['cmake', '-S', str(ROOT), '-B', str(build),
                    '-DPJ_CSV_RUNTIME_PLUGIN=' + binary.as_posix()], check=True)
    subprocess.run(['cmake', '--build', str(build), '--config', 'RelWithDebInfo',
                    '--target', 'csv_runtime_file_loader_test', '--parallel', '2'], check=True)
    selection = ['-R', '^CsvRuntimeFileLoader_']
    listing = subprocess.check_output(['ctest', '--test-dir', str(build), '-C', 'RelWithDebInfo',
                                       '--show-only=json-v1', *selection], text=True, encoding='utf-8')
    selected = {test['name'] for test in json.loads(listing)['tests']}
    assert selected == EXPECTED, (selected, EXPECTED)
    subprocess.run(['ctest', '--test-dir', str(build), '-C', 'RelWithDebInfo', '--no-tests=error',
                    '--output-on-failure', '--timeout', '120', '--test-output-size-passed', '262144',
                    '--output-junit', str(build / 'csv-runtime.xml'),
                    *selection], check=True)
    audit_results(build / 'csv-runtime.xml')


if __name__ == '__main__':
    main()
