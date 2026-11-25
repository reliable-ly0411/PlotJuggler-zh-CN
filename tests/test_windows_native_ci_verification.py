# SPDX-License-Identifier: MPL-2.0
"""Synthetic CI policy checks; no Windows process or user VM is used."""
import importlib.util
import hashlib
import os
from pathlib import Path
import subprocess
import unittest
import tempfile
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('native_ci', ROOT / 'scripts/windows/run_native_ci_verification.py')
ci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ci)


def case(name, **props):
    return {'name': name, 'command': ['test.exe'],
            'properties': [{'name': key, 'value': value} for key, value in props.items()]}


def sample():
    discoveries = {'main': {'kind': 'ctestInfo', 'tests': [case('setup', FIXTURES_SETUP=['f']),
                   case('run', FIXTURES_REQUIRED=['f']), case('cleanup', FIXTURES_CLEANUP=['f']),
                   case('disabled', DISABLED=True)]}}
    def group(name, status, cases):
        return {'name': name, 'status': status, 'reason': 'source audit', 'evidence': ['s/audit.md'], 'cases': cases}
    policy = {'schema': 1, 'scope': 'github-hosted-windows-ci', 'source_sha': 'a' * 40,
              'source_tree': 'b' * 40, 'configuration': 'RelWithDebInfo',
              'suites': [{'id': 'main', 'groups': [group('safe', 'approved', ['setup', 'run', 'cleanup']),
                                                   group('disabled', 'disabled', ['disabled'])]}]}
    manifest = {'files': [{'path': 's/audit.md'}]}
    return discoveries, policy, manifest


class CIPolicyTests(unittest.TestCase):
    def verify(self, docs, policy, manifest):
        return ci.validate_policy(policy, docs, 'a' * 40, 'b' * 40, 'RelWithDebInfo', manifest)

    def test_complete_partition_and_fixture_closure(self):
        docs, policy, manifest = sample()
        decisions = self.verify(docs, policy, manifest)
        selected, unrun = ci.review.approved_selection(docs['main'], decisions['main'], 'reviewed-subset')
        self.assertEqual(selected, {'setup', 'run', 'cleanup'})
        self.assertEqual([(x['case'], x['status']) for x in unrun], [('disabled', 'disabled')])

    def test_missing_duplicate_unbound_or_disabled_approval_fails(self):
        for defect in ('source', 'missing', 'duplicate', 'evidence', 'disabled', 'status', 'scope'):
            docs, policy, manifest = sample(); groups = policy['suites'][0]['groups']
            if defect == 'source': policy['source_sha'] = 'f' * 40
            elif defect == 'missing': groups[0]['cases'].remove('run')
            elif defect == 'duplicate': groups[1]['cases'].append('run')
            elif defect == 'evidence': groups[0]['evidence'] = ['r/untrusted.txt']
            elif defect == 'disabled': groups[1]['status'] = 'approved'
            elif defect == 'status': groups[0]['status'] = 'passed'
            else: policy['scope'] = 'user-windows-vm'
            with self.subTest(defect=defect), self.assertRaises(ci.CIError): self.verify(docs, policy, manifest)

    def test_unapproved_fixture_refuses_that_group(self):
        docs, policy, manifest = sample(); groups = policy['suites'][0]['groups']
        groups[0]['cases'].remove('cleanup')
        groups.append({'name': 'unreviewed', 'status': 'safety_unreviewed', 'reason': 'not audited',
                       'evidence': ['s/audit.md'], 'cases': ['cleanup']})
        decisions = self.verify(docs, policy, manifest)
        with self.assertRaises(ci.review.ReviewError):
            ci.review.approved_selection(docs['main'], decisions['main'], 'reviewed-subset')

    def test_not_windows_or_not_hosted_ci_fails_before_process(self):
        with mock.patch.object(ci.sys, 'platform', 'linux'), mock.patch.object(ci.subprocess, 'Popen') as popen:
            with self.assertRaises(ci.CIError): ci.run(mock.Mock())
            popen.assert_not_called()

    def test_empty_run_or_silently_blocked_approved_group_cannot_pass(self):
        decisions = {'main': {'a': {'status': 'approved'}, 'b': {'status': 'condition_missing'}}}
        with self.assertRaises(ci.CIError):
            ci.validate_ci_selection({'main': {'selected': set(), 'unrun': [{'case': 'b'}]}}, decisions)
        with self.assertRaises(ci.CIError):
            ci.validate_ci_selection({'main': {'selected': {'b'}, 'unrun': [{'case': 'a'}]}}, decisions)
        ci.validate_ci_selection({'main': {'selected': {'a'}, 'unrun': [{'case': 'b'}]}}, decisions)

    def test_ci_temp_actual_token_and_qt_module_must_match(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / 'tmp').mkdir(); qt = root / 'Qt6Core.dll'; qt.write_bytes(b'qt')
            parent = {'sid': 'S-1-5-18', 'session': 0, 'integrity_rid': 16384,
                      'auth_luid': '00000000:000003e7', 'elevation_type': 'full'}
            evidence = {'scope': 'disposable-windows-ci-only', 'qt_version': '6.12.0', 'session': 0,
                        'integrity_rid': 16384, 'user_sid': 'S-1-5-18', 'pid': 10,
                        'auth_luid': '00000000:000003e7', 'elevation_type': 'full',
                        'run_root': str(root), 'qt_temp': str(root / 'tmp'), 'qt_core': str(qt)}
            ci.validate_ci_temp_evidence(evidence, parent, root, qt, '6.12.0')
            for key, wrong in (('scope', 'vm'), ('qt_version', '6.11.0'), ('session', 1),
                               ('user_sid', 'S-1-5-20'), ('session', False), ('auth_luid', '00000000:00000001'), ('elevation_type', 'limited'), ('qt_temp', str(root)), ('qt_core', str(root))):
                with self.subTest(key=key), self.assertRaises(ci.CIError):
                    ci.validate_ci_temp_evidence(dict(evidence, **{key: wrong}), parent, root, qt, '6.12.0')

    def test_only_real_untruncated_nonnested_passes_count(self):
        coverage = {'case_results': [{'test': 'pass', 'category': 'pass'}, {'test': 'nested', 'category': 'pass'},
                                     {'test': 'fail', 'category': 'failure'}, {'test': 'cut', 'category': 'pass'}],
                    'nested_skips': [{'test': 'nested', 'case': 'gtest:child'}], 'truncated_outputs': ['cut']}
        self.assertEqual(ci.real_pass_count(coverage), 1)

    def test_last_test_log_is_preserved_byte_for_byte_without_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); tree = root / 'tree'; output = root / 'output'
            (tree / 'Testing/Temporary').mkdir(parents=True); output.mkdir()
            self.assertIsNone(ci.preserve_ctest_last_log(tree, output))
            raw = b'\xff\x00test output\r\n'
            (tree / 'Testing/Temporary/LastTest.log').write_bytes(raw)
            result = ci.preserve_ctest_last_log(tree, output)
            self.assertEqual((output / 'LastTest.log').read_bytes(), raw)
            self.assertEqual(result['sha256'], hashlib.sha256(raw).hexdigest())
            with self.assertRaises(FileExistsError):
                ci.preserve_ctest_last_log(tree, output)

    def test_last_log_does_not_follow_linked_testing_or_output_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); tree = root / 'tree'; output = root / 'output'; outside = root / 'outside'
            tree.mkdir(); output.mkdir(); (outside / 'Temporary').mkdir(parents=True)
            (outside / 'Temporary/LastTest.log').write_bytes(b'not-owned-log')
            try:
                (tree / 'Testing').symlink_to(outside, target_is_directory=True)
            except OSError:
                self.skipTest('directory symlink creation is not available')
            with self.assertRaises((ci.CIError, ci.audit.AuditError)):
                ci.preserve_ctest_last_log(tree, output)
            self.assertFalse((output / 'LastTest.log').exists())
            (tree / 'Testing').unlink(); (tree / 'Testing').mkdir()
            (tree / 'Testing/Temporary').symlink_to(outside / 'Temporary', target_is_directory=True)
            with self.assertRaises((ci.CIError, ci.audit.AuditError)):
                ci.preserve_ctest_last_log(tree, output)
            self.assertFalse((output / 'LastTest.log').exists())
            (tree / 'Testing/Temporary').unlink(); (tree / 'Testing/Temporary').mkdir()
            (tree / 'Testing/Temporary/LastTest.log').write_bytes(b'own-log')
            output_link = root / 'output-link'
            output_link.symlink_to(outside, target_is_directory=True)
            with self.assertRaises((ci.CIError, ci.audit.AuditError)):
                ci.preserve_ctest_last_log(tree, output_link)
            self.assertFalse((outside / 'LastTest.log').exists())

    def test_last_log_open_identity_is_rechecked_before_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); tree = root / 'tree'; output = root / 'output'
            (tree / 'Testing/Temporary').mkdir(parents=True); output.mkdir()
            (tree / 'Testing/Temporary/LastTest.log').write_bytes(b'not-copied')
            real_fstat = os.fstat
            def changed(fd):
                value = real_fstat(fd)
                return mock.Mock(st_dev=value.st_dev, st_ino=value.st_ino, st_size=value.st_size,
                                 st_mtime_ns=value.st_mtime_ns + 1)
            with mock.patch.object(ci.os, 'fstat', side_effect=changed), self.assertRaises(ci.CIError):
                ci.preserve_ctest_last_log(tree, output)
            self.assertEqual((output / 'LastTest.log').read_bytes(), b'')

    @unittest.skipUnless(os.name == 'nt', 'Actual NTFS junction control requires Windows')
    def test_last_log_rejects_owned_windows_junction(self):
        with tempfile.TemporaryDirectory(prefix='pj-log-junction-') as directory:
            root = Path(directory); tree = root / 'tree'; output = root / 'output'; outside = root / 'outside'
            tree.mkdir(); output.mkdir(); (outside / 'Temporary').mkdir(parents=True)
            (outside / 'Temporary/LastTest.log').write_bytes(b'not-owned-log')
            shell = os.environ.get('COMSPEC', 'cmd.exe')
            result = subprocess.run([shell, '/d', '/c', 'mklink', '/J', str(tree / 'Testing'), str(outside)],
                                    capture_output=True, timeout=60)
            if result.returncode != 0:
                self.skipTest('cannot create an owned NTFS junction fixture')
            with self.assertRaises((ci.CIError, ci.audit.AuditError)):
                ci.preserve_ctest_last_log(tree, output)
            self.assertFalse((output / 'LastTest.log').exists())


if __name__ == '__main__':
    unittest.main()
