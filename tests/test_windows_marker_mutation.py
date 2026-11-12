# SPDX-License-Identifier: MPL-2.0
"""Pure mutation and XML controls, without executing Windows code."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('marker_mutation', ROOT / 'scripts/windows/native_marker_mutation.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


class MutationTests(unittest.TestCase):
    def test_mutant_changes_only_the_owned_clear_body(self):
        original = b'head\nvoid ActiveWidgetsMarker::clear() {\n  live_.clear();\n  QFile::remove(path_);\n}\nother\n'
        result = m.mutant(original)
        self.assertEqual(result, original.replace(b'QFile::remove(path_);', b'/* test-only mutation: preserve marker */'))
        self.assertEqual(m.mutant(original.replace(b'\n', b'\r\n')), result.replace(b'\n', b'\r\n'))
        for invalid in (b'missing', original + original):
            with self.assertRaises(m.MutationError): m.mutant(invalid)

    def test_mutant_must_fail_exact_marker_assertion_and_original_pass(self):
        def xml(failure=''):
            return ('<testsuites><testsuite><testcase name="' + m.CASE_NAME + '" classname="' + m.CASE_CLASS +
                    '" status="run">' + failure + '</testcase></testsuite></testsuites>')
        bad = '<failure message="Value of: QFile::exists(marker_path_)\nActual: true\nExpected: false\nclean-exit clear must remove an unowned record"/>'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'result.xml'; path.write_text(xml(bad), encoding='utf-8')
            m.check_case(path, 1, mutated=True)
            with self.assertRaises(m.MutationError): m.check_case(path, 1, mutated=False)
            path.write_text(xml('<failure message="unrelated"/>'), encoding='utf-8')
            with self.assertRaises(m.MutationError): m.check_case(path, 1, mutated=True)
            path.write_text(xml(), encoding='utf-8'); m.check_case(path, 0, mutated=False)
            with self.assertRaises(m.MutationError): m.check_case(path, 1, mutated=True)
            path.write_text(xml('<skipped/>'), encoding='utf-8')
            with self.assertRaises(m.MutationError): m.check_case(path, 0, mutated=False)

    def test_probe_token_must_match_current_ci_identity_including_session_zero(self):
        identity = {'pid': 41, 'sid': 'S-1-5-18', 'session': 0, 'integrity_rid': 16384,
                    'auth_luid': '00000000:000003e7', 'elevation_type': 'full'}
        proof = {'pid': 42, 'user_sid': 'S-1-5-18', 'session': 0, 'integrity_rid': 16384,
                 'auth_luid': '00000000:000003e7', 'elevation_type': 'full'}
        m.validate_probe_identity(proof, identity)
        for key, value in (('user_sid', 'S-1-5-19'), ('session', 1), ('integrity_rid', 8192),
                           ('auth_luid', '00000000:00000000'), ('elevation_type', 'limited'), ('pid', 0), ('session', False)):
            with self.subTest(key=key), self.assertRaises(m.MutationError):
                m.validate_probe_identity(dict(proof, **{key: value}), identity)
        child = dict(identity, pid=43)
        m.require_same_ci_identity(child, identity)
        with self.assertRaises(m.MutationError):
            m.require_same_ci_identity(dict(child, session=1), identity)

    def test_child_token_mismatch_terminates_and_records_uncertain(self):
        identity = {'pid': 41, 'sid': 'S-1-5-18', 'session': 0, 'integrity_rid': 16384,
                    'auth_luid': '00000000:000003e7', 'elevation_type': 'full'}
        child = mock.MagicMock(pid=55, _handle=123, returncode=1)
        child.__enter__.return_value = child; child.wait.return_value = 1
        reader = mock.Mock(); reader.process_identity.return_value = dict(identity, pid=55, session=1)
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(m.subprocess, 'Popen', return_value=child):
            root = Path(directory)
            with self.assertRaisesRegex(m.MutationError, 'child CI token'):
                m.run_recorded(['fake.exe'], root, {}, root, 'mutant-test', identity, reader)
            child.terminate.assert_called_once()
            import json
            record = json.loads((root / 'mutant-test.process.json').read_text(encoding='utf-8'))
            self.assertEqual(record['identity_status'], 'unverified')
            self.assertEqual(record['outcome'], 'uncertain')

    def test_build_must_show_the_recompiled_tu_and_relinked_runner(self):
        result = {'exit_code': 0}
        good = b'ActiveWidgetsMarker.cpp.obj\npj_runtime.lib\npj_app_gui_tests.exe\n'
        m.require_incremental_build(result, good)
        for bad in (b'pj_runtime.lib pj_app_gui_tests.exe', b'ActiveWidgetsMarker.cpp.obj pj_app_gui_tests.exe'):
            with self.assertRaises(m.MutationError): m.require_incremental_build(result, bad)
        with self.assertRaises(m.MutationError): m.require_incremental_build({'exit_code': 1}, good)


if __name__ == '__main__': unittest.main()
