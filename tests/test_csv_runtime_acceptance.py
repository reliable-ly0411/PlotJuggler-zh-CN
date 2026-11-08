#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('csv_acceptance', ROOT / 'packaging/localization/run_csv_runtime_acceptance.py')
acceptance = importlib.util.module_from_spec(spec)
spec.loader.exec_module(acceptance)


class CsvRuntimeAcceptanceTest(unittest.TestCase):
    def junit(self, destination):
        root = ET.Element('testsuite', tests='3', failures='0', disabled='0', skipped='0')
        for language in sorted(acceptance.EXPECTED):
            case = ET.SubElement(root, 'testcase', name=language, status='run')
            output = ''.join(f'[ RUN      ] {name}\n[       OK ] {name} (0 ms)\n' for name in sorted(acceptance.CASES))
            ET.SubElement(case, 'system-out').text = output + '[  PASSED  ] 7 tests.\n'
        destination.parent.mkdir(parents=True, exist_ok=True)
        ET.ElementTree(root).write(destination, encoding='utf-8', xml_declaration=True)
        return root

    def test_actual_results_reject_partial_skipped_or_truncated_success(self):
        for defect in ['disabled', 'skipped', 'failure', 'error', 'empty', 'truncated', 'missing', 'duplicate', 'filtered', 'wrong-count', 'missing-case', 'skipped-marker']:
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as tmp:
                report = Path(tmp) / 'results.xml'
                root = self.junit(report)
                self.assertEqual(acceptance.audit_results(report), sorted(acceptance.EXPECTED))
                case = list(root)[1]
                output = case.find('system-out')
                if defect == 'disabled':
                    case.set('status', 'notrun')
                elif defect in ['skipped', 'failure', 'error']:
                    ET.SubElement(case, defect)
                elif defect == 'empty':
                    output.text = ''
                elif defect == 'truncated':
                    output.text += '[This part of the test output was removed since it exceeds the threshold]'
                elif defect == 'missing':
                    root.remove(case)
                elif defect == 'duplicate':
                    case.set('name', list(root)[0].get('name'))
                elif defect == 'missing-case':
                    output.text = '\n'.join(output.text.splitlines()[2:])
                elif defect == 'skipped-marker':
                    output.text += '[  SKIPPED ] CsvRuntimeFileLoader.ShortWarningClose\n'
                elif defect == 'filtered':
                    output.text += 'Note: Google Test filter = CsvRuntimeFileLoader.*'
                else:
                    output.text = output.text.replace('[  PASSED  ] 7 tests.', '[  PASSED  ] 6 tests.')
                ET.ElementTree(root).write(report, encoding='utf-8', xml_declaration=True)
                with self.assertRaises(ValueError):
                    acceptance.audit_results(report)

    def stage(self, root):
        lock = json.loads((ROOT / 'packaging/localization/plugin-patches/source-lock.json').read_text(encoding='utf-8'))
        record = dict(next(item for item in lock['plugins'] if item['id'] == 'csv-loader'))
        binary = root / 'lib/plotjuggler/plugins/csv-loader/csv_source_plugin.dll'
        binary.parent.mkdir(parents=True)
        binary.write_bytes(b'synthetic-test-only')
        record['files'] = [{'path': binary.relative_to(root).as_posix(),
                            'sha256': hashlib.sha256(binary.read_bytes()).hexdigest()}]
        manifest = root / 'share/plotjuggler4/release.json'
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({'localized_plugin_rebuilds': [record]}), encoding='utf-8')
        return binary, manifest, record

    def test_staged_plugin_must_match_current_source_and_bytes(self):
        for field in ['version', 'commit', 'sdk', 'patch_sha256', 'binary', 'duplicate', 'path', 'escape']:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / 'staged'
                root.mkdir()
                # Exercise equivalent path spellings even without Windows 8.3 aliases.
                root = root / '..' / 'staged'
                binary, manifest, record = self.stage(root)
                self.assertEqual(acceptance.staged_csv(root), binary.resolve())
                records = [record]
                if field == 'binary':
                    binary.write_bytes(b'tampered')
                elif field == 'duplicate':
                    records.append(record)
                elif field in ['path', 'escape']:
                    record['files'][0]['path'] = ('other/' if field == 'path' else '../outside/') + 'csv_source_plugin.dll'
                    outside = root / record['files'][0]['path']
                    outside.parent.mkdir(parents=True)
                    outside.write_bytes(binary.read_bytes())  # Valid bytes cannot authorize the wrong location.
                else:
                    record[field] = 'not-the-locked-value'
                manifest.write_text(json.dumps({'localized_plugin_rebuilds': records}), encoding='utf-8')
                with self.assertRaises(AssertionError):
                    acceptance.staged_csv(root)

    def test_missing_or_extra_language_never_runs_an_incomplete_gate(self):
        for selected in [acceptance.EXPECTED - {'CsvRuntimeFileLoader_zh_TW'},
                         acceptance.EXPECTED | {'CsvRuntimeFileLoader_unknown'}]:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.stage(root)
                listing = json.dumps({'tests': [{'name': name} for name in selected]})
                with mock.patch.object(sys, 'argv', ['gate', '--build', str(root / 'build'), '--prefix', str(root)]), \
                     mock.patch.object(acceptance.subprocess, 'run') as run, \
                     mock.patch.object(acceptance.subprocess, 'check_output', return_value=listing):
                    with self.assertRaises(AssertionError):
                        acceptance.main()
                    self.assertEqual(run.call_count, 2)  # Configure/build only, never a partial ctest.

    def test_complete_gate_builds_and_runs_without_skip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.stage(root)
            listing = json.dumps({'tests': [{'name': name} for name in acceptance.EXPECTED]})
            self.junit(root / 'build/csv-runtime.xml')
            with mock.patch.object(sys, 'argv', ['gate', '--build', str(root / 'build'), '--prefix', str(root)]), \
                 mock.patch.object(acceptance.subprocess, 'run') as run, \
                 mock.patch.object(acceptance.subprocess, 'check_output', return_value=listing):
                acceptance.main()
                self.assertEqual(run.call_count, 3)
                self.assertIn('--no-tests=error', run.call_args.args[0])
                self.assertIn('--output-junit', run.call_args.args[0])


if __name__ == '__main__':
    unittest.main()
