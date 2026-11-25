# SPDX-License-Identifier: MPL-2.0
"""Run a tiny local CTest fixture to exercise the unmodified executor protocol."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('native_launcher_protocol', ROOT / 'scripts/windows/run_native_test_bundle.py')
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


@unittest.skipUnless(all(shutil.which(x) for x in ('cmake', 'ctest', 'ninja')), 'CMake, CTest and Ninja are required')
class CTestProtocolTest(unittest.TestCase):
    def test_real_ctest_classifies_fail_skip_disabled_and_missing_executable(self):
        with tempfile.TemporaryDirectory(prefix='ctest status ') as directory:
            root = Path(directory); source = root / 'src'; source.mkdir(); build = root / 'b'
            (source / 'CMakeLists.txt').write_text(f'''cmake_minimum_required(VERSION 3.22)
project(CTestStatuses NONE)
enable_testing()
add_test(NAME passed COMMAND [==[{sys.executable}]==] -c "pass")
add_test(NAME failed COMMAND [==[{sys.executable}]==] -c "raise SystemExit(1)")
add_test(NAME conditional COMMAND [==[{sys.executable}]==] -c "raise SystemExit(4)")
set_tests_properties(conditional PROPERTIES SKIP_RETURN_CODE 4)
add_test(NAME missing COMMAND [==[{(root / 'missing-executable').as_posix()}]==])
add_test(NAME disabled COMMAND [==[{sys.executable}]==] -c "pass")
set_tests_properties(disabled PROPERTIES DISABLED TRUE)
''', encoding='utf-8')
            subprocess.run([shutil.which('cmake'), '-G', 'Ninja', '-S', str(source), '-B', str(build)], check=True, capture_output=True)
            base = [shutil.which('ctest'), '--test-dir', str(build)]
            listing = root / 'listing.json'; listing.write_bytes(subprocess.check_output(base + ['--show-only=json-v1']))
            result = subprocess.run(base + ['--output-junit', str(root / 'junit.xml')], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            evidence = launcher.audit.audit_results(listing, root / 'junit.xml')
            by_name = {item['test']: item for item in evidence['case_results']}
            self.assertEqual({name: row['category'] for name, row in by_name.items()},
                             {'passed': 'pass', 'failed': 'failure', 'conditional': 'conditional_skip',
                              'missing': 'not_run', 'disabled': 'disabled'})
            self.assertIn('Unable to find executable', by_name['missing']['reason'])
            self.assertEqual(by_name['conditional']['reason'], 'SKIP_RETURN_CODE=4')
            self.assertFalse(evidence['complete_without_skips_or_failures'])

    def test_real_ctest_preserves_fixture_properties_and_complete_stream(self):
        with tempfile.TemporaryDirectory(prefix='synthetic ctest ') as directory:
            root = Path(directory); source = root / 'src'; source.mkdir(); build = root / 'b'
            marker = root / 'fixture.txt'
            runner = source / 'runner.py'
            runner.write_text('''import pathlib,sys\np=pathlib.Path(sys.argv[2])\nmode=sys.argv[1]\nif mode == "setup": p.write_text("ready")\nelif mode == "case":\n assert p.read_text() == "ready"\n print("child stdout marker", flush=True)\n print("child stderr marker", file=sys.stderr, flush=True)\nelif mode == "cleanup": p.unlink()\n''', encoding='utf-8')
            (source / 'CMakeLists.txt').write_text(f'''cmake_minimum_required(VERSION 3.22)
project(SyntheticCTest NONE)
enable_testing()
add_test(NAME setup COMMAND [==[{sys.executable}]==] [==[{runner}]==] setup [==[{marker}]==])
set_tests_properties(setup PROPERTIES FIXTURES_SETUP example)
add_test(NAME prior COMMAND [==[{sys.executable}]==] -c "pass")
add_test(NAME case COMMAND [==[{sys.executable}]==] [==[{runner}]==] case [==[{marker}]==])
set_tests_properties(case PROPERTIES FIXTURES_REQUIRED example DEPENDS prior ENVIRONMENT "FIXTURE_ONLY=1" TIMEOUT 10)
add_test(NAME cleanup COMMAND [==[{sys.executable}]==] [==[{runner}]==] cleanup [==[{marker}]==])
set_tests_properties(cleanup PROPERTIES FIXTURES_CLEANUP example)
add_test(NAME intentional-disabled COMMAND [==[{sys.executable}]==] -c "raise SystemExit(1)")
set_tests_properties(intentional-disabled PROPERTIES DISABLED TRUE)
''', encoding='utf-8')
            subprocess.run([shutil.which('cmake'), '-G', 'Ninja', '-S', str(source), '-B', str(build)], check=True, capture_output=True)
            command = [shutil.which('ctest'), '--test-dir', str(build), '--show-only=json-v1']
            expected_doc = json.loads(subprocess.check_output(command))
            setup_only = root / 'setup-only.txt'; setup_only.write_text('setup\n', encoding='utf-8')
            setup_doc = json.loads(subprocess.check_output(command + ['--tests-from-file', str(setup_only)]))
            self.assertEqual({x['name'] for x in setup_doc['tests']}, {'setup'})
            self.assertIn('cleanup', launcher.review.selection_closure(expected_doc, {'setup'}))
            selected = root / 'selected.txt'; selected.write_text('case\n', encoding='utf-8')
            selected_doc = json.loads(subprocess.check_output(command + ['--tests-from-file', str(selected)]))
            self.assertEqual({x['name'] for x in selected_doc['tests']}, {'setup', 'case', 'cleanup'})
            closed = launcher.review.selection_closure(expected_doc, {'case'})
            self.assertEqual(closed, {'setup', 'prior', 'case', 'cleanup'})
            selected.write_text('\n'.join(sorted(closed)) + '\n', encoding='utf-8')
            closed_doc = json.loads(subprocess.check_output(command + ['--tests-from-file', str(selected)]))
            launcher.same_discovery(launcher.selected_document(expected_doc, closed), closed_doc)
            expected = {'session': 1, 'sid': 'S-1-5-21-100-500', 'integrity_rid': 12288}
            real_popen = subprocess.Popen
            class Proxy:
                def __init__(self, *args, **kwargs):
                    self.process = real_popen(*args, **kwargs)
                    self.pid = self.process.pid
                    self._handle = self.pid
                def wait(self, *args, **kwargs): return self.process.wait(*args, **kwargs)
                def terminate(self): return self.process.terminate()
            with mock.patch.object(launcher.subprocess, 'Popen', side_effect=Proxy), \
                 mock.patch.object(launcher, 'process_identity', side_effect=lambda handle, pid: dict(expected, pid=pid)):
                discovery = launcher.run_process(command, root, dict(os.environ), root / 'discovery.out', root / 'discovery.err', expected, 30)
                self.assertEqual(discovery['exit_code'], 0)
                launcher.same_discovery(expected_doc, json.loads((root / 'discovery.out').read_text(encoding='utf-8')))
                report = root / 'junit.xml'
                run = launcher.run_process([shutil.which('ctest'), '--test-dir', str(build), '--no-tests=error', '--verbose',
                                            '--test-output-size-passed', '1073741824', '--test-output-size-failed', '1073741824',
                                            '--output-junit', str(report)], root, dict(os.environ), root / 'run.out', root / 'run.err', expected, 30)
            self.assertEqual(run['exit_code'], 0)
            self.assertFalse(marker.exists())  # setup, dependent test and cleanup actually ran.
            output = (root / 'run.out').read_bytes()
            self.assertIn(b'child stdout marker', output)
            self.assertIn(b'child stderr marker', output)  # CTest has combined child streams.
            cases = list(ET.parse(report).getroot().iter('testcase'))
            self.assertEqual({c.get('name') for c in cases}, {'setup', 'prior', 'case', 'cleanup', 'intentional-disabled'})
            disabled = next(c for c in cases if c.get('name') == 'intentional-disabled')
            self.assertEqual(disabled.get('status'), 'disabled')
            discovery_path = root / 'baseline.json'
            discovery_path.write_text(json.dumps(expected_doc), encoding='utf-8')
            review = launcher.audit.audit_results(discovery_path, report)
            self.assertEqual(review['top_level_skips'], ['intentional-disabled'])
            self.assertFalse(review['complete_without_skips_or_failures'])


if __name__ == '__main__':
    unittest.main()
