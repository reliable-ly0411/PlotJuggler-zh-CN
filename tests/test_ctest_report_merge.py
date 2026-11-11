# SPDX-License-Identifier: MPL-2.0
"""Fail-closed coverage and result preservation for split Windows CTest passes."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/ci/merge_ctest_reports.py'
spec = importlib.util.spec_from_file_location('merge_ctest_reports', SCRIPT)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def listing(names):
    return {'tests': [{'name': name, 'command': ['fixture', name]} for name in names]}


def report(names, status='run', tag=None):
    root = ET.Element('testsuite', tests=str(len(names)), failures=str(len(names) if tag in {'failure', 'error'} else 0),
                      skipped=str(len(names) if tag == 'skipped' else 0), disabled='0', time='0.25')
    for name in names:
        case = ET.SubElement(root, 'testcase', name=name, status=status, time='0.1')
        if tag:
            ET.SubElement(case, tag).text = 'original failure or skip reason'
        ET.SubElement(case, 'system-out').text = 'Original UTF-8: 中文\n[  PASSED  ] 1 test.\n'
        ET.SubElement(case, 'system-err').text = 'original stderr\n'
    return root


class CTestMergeTests(unittest.TestCase):
    def test_disjoint_reports_preserve_every_testcase_subtree(self):
        reports = [report(['one']), report(['two'], 'notrun', 'skipped'), report(['three'], 'fail', 'failure')]
        merged = gate.merge_reports(listing(['one', 'two', 'three']), reports)
        self.assertEqual(merged.get('tests'), '3')
        self.assertEqual(merged.get('failures'), '1')
        self.assertEqual(merged.get('skipped'), '1')
        for actual, original in zip(merged, (source[0] for source in reports)):
            self.assertEqual(ET.tostring(actual), ET.tostring(original))

    def test_missing_duplicate_or_unexpected_case_rejected(self):
        for reports in ([report(['one'])], [report(['one']), report(['one'])], [report(['one', 'other'])]):
            with self.subTest(reports=reports), self.assertRaises(ValueError):
                gate.merge_reports(listing(['one', 'two']), reports)

    def test_empty_duplicate_or_commandless_discovery_rejected(self):
        for value in (listing([]), listing(['one', 'one']), listing([None]), listing(['']),
                      {'tests': [{'name': 'one'}]}, {'tests': [{'name': 'one', 'command': 'not-a-list'}]},
                      {'tests': [{'name': 'one', 'command': [None]}]},
                      {'tests': [{'name': 'one', 'command': ['']}]}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                gate.merge_reports(value, [report(['one'])])

    def test_unknown_and_contradictory_status_rejected(self):
        for status, tag in (('fail', None), ('notrun', None), ('crashed', None),
                            ('run', 'failure'), ('run', 'skipped'), ('fail', 'skipped'), ('notrun', 'error')):
            with self.subTest(status=status, tag=tag), self.assertRaises(ValueError):
                gate.merge_reports(listing(['one']), [report(['one'], status, tag)])
        source = report(['one'], 'fail', 'failure')
        ET.SubElement(source[0], 'skipped')
        with self.assertRaises(ValueError):
            gate.merge_reports(listing(['one']), [source])

    def test_error_and_failure_both_remain_failures(self):
        for tag in ('error', 'failure'):
            with self.subTest(tag=tag):
                merged = gate.merge_reports(listing(['one']), [report(['one'], 'fail', tag)])
                self.assertEqual(merged.get('failures'), '1')
                self.assertIsNotNone(merged[0].find(tag))

    def test_report_count_mismatch_rejected(self):
        for key in ('tests', 'failures', 'disabled', 'skipped', 'errors'):
            source = report(['one'])
            source.set(key, '999')
            with self.subTest(key=key), self.assertRaises(ValueError):
                gate.merge_reports(listing(['one']), [source])

    def test_invalid_duration_rejected(self):
        for value in ('-1', 'NaN', 'Infinity'):
            for target in ('suite', 'case'):
                source = report(['one'])
                (source if target == 'suite' else source[0]).set('time', value)
                with self.subTest(value=value, target=target), self.assertRaises(ValueError):
                    gate.merge_reports(listing(['one']), [source])

    def test_missing_stdout_rejected_but_empty_captured_stdout_preserved(self):
        source = report(['one'])
        source[0].find('system-out').text = ''
        self.assertIsNotNone(gate.merge_reports(listing(['one']), [source])[0].find('system-out'))
        source[0].remove(source[0].find('system-out'))
        with self.assertRaisesRegex(ValueError, 'captured stdout'):
            gate.merge_reports(listing(['one']), [source])

    def test_native_portability_requires_exact_nine_real_passes(self):
        names = sorted(gate.NATIVE_CASES)
        gate.validate_native_regressions(listing(names), report(names))
        for source in (report(names[:-1]), report(names + [names[0]]),
                       report(names, 'notrun', 'skipped'), report(names, 'fail', 'failure')):
            with self.assertRaises(ValueError):
                gate.validate_native_regressions(listing(names), source)
        source = report(names)
        source[0].find('system-out').text = ''
        with self.assertRaisesRegex(ValueError, 'GTest pass evidence'):
            gate.validate_native_regressions(listing(names), source)

    def test_truncated_stdout_or_stderr_rejected(self):
        marker = '[This part of the test output was removed since it exceeds the threshold of 256 bytes.]'
        for stream in ('system-out', 'system-err'):
            for status, tag in (('run', None), ('fail', 'failure'), ('notrun', 'skipped')):
                source = report(['one'], status, tag)
                source[0].find(stream).text += marker
                with self.subTest(stream=stream, status=status), self.assertRaisesRegex(ValueError, 'Truncated'):
                    gate.merge_reports(listing(['one']), [source])

    @unittest.skipUnless(shutil.which('ctest'), 'CTest is required for its real truncation marker')
    def test_real_ctest_truncation_with_pass_prefix_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            python = Path(sys.executable).as_posix()
            names = sorted(gate.NATIVE_CASES)
            # Keep the success prefix while CTest removes the remaining evidence.
            code = "print('[  PASSED  ] 1 test.'); print('x' * 8192)"
            commands = [f'add_test({name} [==[{python}]==] -c [==[{code}]==])' for name in names]
            (root / 'CTestTestfile.cmake').write_text('\n'.join(commands) + '\n', encoding='utf-8')
            discovered = json.loads(subprocess.check_output(
                [shutil.which('ctest'), '--test-dir', str(root), '--show-only=json-v1'],
                text=True, encoding='utf-8'))
            result = subprocess.run(
                [shutil.which('ctest'), '--test-dir', str(root), '--output-junit', str(root / 'result.xml'),
                 '--test-output-size-passed', '256', '--test-output-truncation', 'tail'],
                capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            source = ET.parse(root / 'result.xml').getroot()
            self.assertEqual(source.get('tests'), '9')
            self.assertEqual(source.get('failures'), '0')
            for case in source.findall('testcase'):
                output = case.findtext('system-out') or ''
                self.assertIn('[  PASSED  ] 1 test.', output)
                self.assertIn('[This part of the test output was removed since it exceeds the threshold of 256 bytes.]',
                              output)
            with self.assertRaisesRegex(ValueError, 'Truncated'):
                gate.merge_reports(discovered, [source])
            with self.assertRaisesRegex(ValueError, 'Truncated'):
                gate.validate_native_regressions(discovered, source)
            (root / 'list.json').write_text(json.dumps(discovered), encoding='utf-8')
            rejected = subprocess.run(
                [sys.executable, str(SCRIPT), '--ctest-list', str(root / 'list.json'),
                 '--output', str(root / 'merged.xml'), str(root / 'result.xml')],
                capture_output=True, text=True, encoding='utf-8')
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn('Truncated CTest output', rejected.stderr)
            self.assertFalse((root / 'merged.xml').exists())

    @unittest.skipUnless(shutil.which('ctest'), 'CTest is required for its real result schema')
    def test_real_ctest_pass_fail_skip_and_disabled_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            python = Path(sys.executable).as_posix()
            commands = []
            for name, code in (('pass', 0), ('fail', 1), ('skip', 77), ('disabled', 0)):
                commands.append(f'add_test({name} [==[{python}]==] -c "raise SystemExit({code})")')
            commands.append(f'add_test(empty_arg [==[{python}]==] -c [==[import sys; assert sys.argv[1] == \"\"]==] \"\")')
            commands.extend(('set_tests_properties(skip PROPERTIES SKIP_RETURN_CODE 77)',
                             'set_tests_properties(disabled PROPERTIES DISABLED TRUE)'))
            (root / 'CTestTestfile.cmake').write_text('\n'.join(commands) + '\n', encoding='utf-8')
            discovered = subprocess.check_output([shutil.which('ctest'), '--test-dir', str(root),
                                                   '--show-only=json-v1'], text=True, encoding='utf-8')
            result = subprocess.run([shutil.which('ctest'), '--test-dir', str(root), '--output-junit',
                                     str(root / 'result.xml')], capture_output=True, text=True, encoding='utf-8')
            self.assertNotEqual(result.returncode, 0)
            merged = gate.merge_reports(json.loads(discovered), [ET.parse(root / 'result.xml').getroot()])
            self.assertEqual({key: merged.get(key) for key in ('tests', 'failures', 'skipped', 'disabled')},
                             {'tests': '5', 'failures': '1', 'skipped': '1', 'disabled': '1'})
            empty = next(row for row in json.loads(discovered)['tests'] if row['name'] == 'empty_arg')
            self.assertEqual(empty['command'][-1], '')

    def test_cli_failure_report_never_exits_success(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'list.json').write_text(json.dumps(listing(['one'])), encoding='utf-8')
            ET.ElementTree(report(['one'], 'fail', 'failure')).write(root / 'input.xml', encoding='utf-8')
            result = subprocess.run([sys.executable, str(SCRIPT), '--ctest-list', str(root / 'list.json'),
                                     '--output', str(root / 'output.xml'), str(root / 'input.xml')],
                                    capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(result.returncode, 1)
            self.assertEqual(ET.parse(root / 'output.xml').getroot().get('failures'), '1')


if __name__ == '__main__':
    unittest.main()
