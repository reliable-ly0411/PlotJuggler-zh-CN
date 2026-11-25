# SPDX-License-Identifier: MPL-2.0
"""Synthetic guard orchestration, with no Windows process or user data."""
import hashlib
import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('app_guard', ROOT / 'scripts/windows/native_app_launch_guard.py')
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
launcher_spec = importlib.util.spec_from_file_location('guard_receipt_launcher', ROOT / 'scripts/windows/run_native_test_bundle.py')
launcher = importlib.util.module_from_spec(launcher_spec)
launcher_spec.loader.exec_module(launcher)


class AppGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.runroot = self.root / 'run'; (self.runroot / 'app-guard').mkdir(parents=True)
        (self.runroot / 'tmp').mkdir()
        self.probe = self.root / 'probe.exe'; self.probe.write_bytes(b'probe')
        self.qt = self.root / 'Qt6Core.dll'; self.qt.write_bytes(b'qt')
        self.app = self.root / 'app.exe'; self.app.write_bytes(b'app')
        self.command = [str(self.app), '--profile-dir', str(self.runroot / 'tmp/profile'), '--version']
        self.env = {'PJ_NATIVE_APP_GUARD_REQUIRED': '1', 'PJ_NATIVE_APP_PROBE': str(self.probe),
                    'PJ_NATIVE_APP_PROBE_SHA256': hashlib.sha256(b'probe').hexdigest(),
                    'PJ_NATIVE_APP_QT_CORE': str(self.qt), 'PJ_NATIVE_APP_QT_CORE_SHA256': hashlib.sha256(b'qt').hexdigest(),
                    'PJ_NATIVE_APP_EXECUTABLE': str(self.app), 'PJ_NATIVE_APP_EXECUTABLE_SHA256': hashlib.sha256(b'app').hexdigest(),
                    'PJ_NATIVE_APP_QT_VERSION': '6.12.0', 'TEMP': str(self.runroot / 'tmp'), 'TMP': str(self.runroot / 'tmp'),
                    'PJ_NATIVE_APP_SID': 'S-1-5-21-1-500', 'PJ_NATIVE_APP_SESSION': '1',
                    'PJ_NATIVE_APP_INTEGRITY_RID': '12288', 'PJ_NATIVE_APP_AUTH_LUID': '00000000:12345678',
                    'PJ_NATIVE_APP_ELEVATION_TYPE': 'full', 'PJ_NATIVE_APP_RUN_ROOT': str(self.runroot)}
        self.values = guard.settings(self.env)
        now = datetime.now(timezone.utc).isoformat()
        self.snapshot = {'schema': 'pj-native-app-marker-probe/v1', 'ok': True, 'exit_code': 0, 'reason': 'clean_snapshot',
                         'platform': 'windows', 'checked_at_utc': now, 'completed_at_utc': now, 'probe_pid': 10,
                         'marker_directory': r'C:\Users\User\AppData\Local\PlotJuggler\PlotJuggler4',
                         'marker_directory_exists': False, 'marker_enumeration_ok': True, 'matching_marker_count': 0,
                         'process_enumeration_ok': True, 'other_app_process_count': 0,
                         'token': {'sid': self.values['SID'], 'session': 1, 'process_session': 1, 'integrity_rid': 12288,
                                   'auth_luid': self.values['AUTH_LUID'], 'elevation_type': 'full',
                                   'restricting_sid_count': 0, 'app_container': False},
                         'qt': {'runtime_version': '6.12.0', 'compiled_version': '6.12.0', 'core_module_path': str(self.qt)}}

    def test_default_is_the_original_subprocess_call(self):
        with mock.patch.object(guard.subprocess, 'run', return_value='result') as child:
            self.assertEqual(guard.run(['app'], env={}, capture_output=True, timeout=4), 'result')
            child.assert_called_once_with(['app'], env={}, capture_output=True, timeout=4)

    def test_snapshot_checks_exact_identity_and_unsafe_or_incomplete_fields(self):
        valid = json.dumps(self.snapshot).encode()
        self.assertEqual(guard.validate_snapshot(valid, self.values)['matching_marker_count'], 0)
        for change in ('marker', 'processes', 'missing', 'auth', 'qt', 'restricted', 'session-bool', 'process-session-bool', 'integrity-bool'):
            item = json.loads(json.dumps(self.snapshot))
            if change == 'marker': item['matching_marker_count'] = 1
            elif change == 'processes': item['process_enumeration_ok'] = False
            elif change == 'missing': item['marker_directory_exists'] = None
            elif change == 'auth': item['token']['auth_luid'] = '00000000:00000000'
            elif change == 'qt': item['qt']['core_module_path'] = 'different'
            elif change == 'restricted': item['token']['restricting_sid_count'] = 1
            elif change == 'session-bool': item['token']['session'] = True
            elif change == 'process-session-bool': item['token']['process_session'] = True
            else: item['token']['integrity_rid'] = False
            with self.subTest(change=change), self.assertRaises(guard.GuardError):
                guard.validate_snapshot(json.dumps(item).encode(), self.values)

    def test_each_launch_has_before_and_after_and_failure_stops(self):
        calls = []
        def snapshot(values, env, output, phase): calls.append(phase)
        def child(command, kwargs, values, output):
            calls.append('app'); return subprocess.CompletedProcess(command, 0, b'ok', b'')
        with mock.patch.object(guard, 'snapshot', side_effect=snapshot), \
             mock.patch.object(guard, 'verified_app_process', side_effect=child):
            result = guard.run(self.command, guard_case='WindowsApplicationContract', env=self.env, capture_output=True, timeout=60)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(calls, ['before', 'app', 'after'])
        self.assertEqual(len(list((self.runroot / 'app-guard').iterdir())), 1)
        with mock.patch.object(guard, 'snapshot', side_effect=guard.GuardError('unsafe')), \
             mock.patch.object(guard, 'verified_app_process') as child:
            with self.assertRaises(guard.GuardError): guard.run(self.command, guard_case='WindowsApplicationContract', env=self.env, capture_output=True, timeout=60)
            child.assert_not_called()
        with mock.patch.object(guard, 'snapshot', side_effect=[None, guard.GuardError('changed')]), \
             mock.patch.object(guard, 'verified_app_process', side_effect=child):
            with self.assertRaisesRegex(guard.GuardError, 'post-launch'): guard.run(self.command, guard_case='WindowsApplicationContract', env=self.env, capture_output=True, timeout=60)

    def test_shared_launch_lock_blocks_concurrent_runs_and_uncertain_is_retained(self):
        entered, release = threading.Event(), threading.Event()
        other_root = self.root / 'other-run'
        (other_root / 'app-guard').mkdir(parents=True); (other_root / 'tmp').mkdir()
        other_env = dict(self.env, PJ_NATIVE_APP_RUN_ROOT=str(other_root),
                         TEMP=str(other_root / 'tmp'), TMP=str(other_root / 'tmp'))
        other_command = [str(self.app), '--profile-dir', str(other_root / 'tmp/profile'), '--version']
        errors = []
        def child(command, kwargs, values, output):
            entered.set()
            self.assertTrue(release.wait(5))
            return subprocess.CompletedProcess(command, 0, b'', b'')
        def first():
            try:
                guard.run(self.command, guard_case='WindowsApplicationContract', env=self.env, capture_output=True)
            except BaseException as exc:
                errors.append(exc)
        with mock.patch.object(guard, 'snapshot'), mock.patch.object(guard, 'verified_app_process', side_effect=child):
            thread = threading.Thread(target=first); thread.start()
            self.assertTrue(entered.wait(5))
            try:
                with self.assertRaisesRegex(guard.GuardError, 'another guarded launch'):
                    guard.run(other_command, guard_case='WindowsApplicationContract', env=other_env, capture_output=True)
            finally:
                release.set(); thread.join(5)
            self.assertFalse(thread.is_alive()); self.assertEqual(errors, [])
            self.assertFalse((self.root / '.native-app-launch.lock').exists())
        with mock.patch.object(guard, 'snapshot'), mock.patch.object(guard, 'verified_app_process', side_effect=OSError('unknown child outcome')):
            with self.assertRaises(OSError):
                guard.run(self.command, guard_case='WindowsApplicationContract', env=self.env, capture_output=True)
        self.assertTrue((self.root / '.native-app-launch.lock').is_file())
        statuses = [json.loads(path.read_text(encoding='utf-8')) for path in (self.runroot / 'app-guard').glob('*/guard-status.json')]
        self.assertTrue(any(x['status'] == 'uncertain' and x['lock_retained'] for x in statuses))
        with self.assertRaisesRegex(guard.GuardError, 'prior launch needs review'):
            guard.run(other_command, guard_case='WindowsApplicationContract', env=other_env, capture_output=True)

    def test_lock_release_error_cannot_claim_lock_was_removed(self):
        result = subprocess.CompletedProcess(self.command, 0, b'', b'')
        with mock.patch.object(guard, 'snapshot'), mock.patch.object(guard, 'verified_app_process', return_value=result), \
             mock.patch.object(guard, 'release_launch_lock', side_effect=PermissionError('denied')):
            with self.assertRaises(PermissionError):
                guard.run(self.command, guard_case='WindowsApplicationContract', env=self.env, capture_output=True)
        self.assertTrue((self.root / '.native-app-launch.lock').exists())
        status_file = next((self.runroot / 'app-guard').glob('*/guard-status.json'))
        status = json.loads(status_file.read_text(encoding='utf-8'))
        self.assertEqual(status['status'], 'uncertain')
        self.assertIsNone(status['lock_retained'])
        self.assertEqual(status['lock_release_error'], 'PermissionError')

    def test_changed_probe_and_output_directory_fail_closed(self):
        self.probe.write_bytes(b'changed')
        with self.assertRaises(guard.GuardError): guard.settings(self.env)
        self.probe.write_bytes(b'probe')
        self.env['PJ_NATIVE_APP_GUARD_REQUIRED'] = 'yes'
        with self.assertRaises(guard.GuardError): guard.settings(self.env)

    def test_actual_child_identity_is_checked_before_wait(self):
        identity = {'sid': self.values['SID'], 'session': 1, 'integrity_rid': 12288,
                    'auth_luid': self.values['AUTH_LUID'], 'elevation_type': 'full', 'pid': 33}
        verifier = mock.Mock(); verifier.process_identity.return_value = identity
        module_spec = mock.Mock(); process = mock.MagicMock(pid=33, _handle=99, returncode=0)
        process.__enter__.return_value = process; process.communicate.return_value = (b'out', b'err')
        output = self.runroot / 'app-guard' / 'case'; output.mkdir()
        with mock.patch.object(guard.importlib.util, 'spec_from_file_location', return_value=module_spec), \
             mock.patch.object(guard.importlib.util, 'module_from_spec', return_value=verifier), \
             mock.patch.object(guard.subprocess, 'Popen', return_value=process):
            result = guard.verified_app_process(['app'], {'capture_output': True, 'timeout': 60}, self.values, output)
        self.assertEqual(result.stdout, b'out')
        verifier.process_identity.assert_called_once_with(99, 33)
        verifier.require_identity.assert_called_once()
        self.assertTrue((output / 'app-start.json').is_file())
        self.assertEqual(json.loads((output / 'app-process.json').read_text(encoding='utf-8'))['identity'], identity)

    def test_token_mismatch_terminates_child_and_never_marks_it_verified(self):
        verifier = mock.Mock(); verifier.require_identity.side_effect = ValueError('wrong token')
        module_spec = mock.Mock(); process = mock.MagicMock(pid=33, _handle=99)
        process.__enter__.return_value = process
        output = self.runroot / 'app-guard' / 'wrong'; output.mkdir()
        with mock.patch.object(guard.importlib.util, 'spec_from_file_location', return_value=module_spec), \
             mock.patch.object(guard.importlib.util, 'module_from_spec', return_value=verifier), \
             mock.patch.object(guard.subprocess, 'Popen', return_value=process):
            with self.assertRaisesRegex(guard.GuardError, 'mismatched'):
                guard.verified_app_process(['app'], {'capture_output': True, 'timeout': 60}, self.values, output)
        process.terminate.assert_called_once()
        self.assertFalse((output / 'app-process.json').exists())

    def test_short_lived_child_token_unobserved_is_recorded_without_invented_identity(self):
        verifier = mock.Mock(); verifier.process_identity.side_effect = OSError('already exited')
        module_spec = mock.Mock(); process = mock.MagicMock(pid=33, _handle=99, returncode=0)
        process.__enter__.return_value = process; process.poll.return_value = 0
        process.communicate.return_value = (b'out', b'err')
        output = self.runroot / 'app-guard' / 'short'; output.mkdir()
        with mock.patch.object(guard.importlib.util, 'spec_from_file_location', return_value=module_spec), \
             mock.patch.object(guard.importlib.util, 'module_from_spec', return_value=verifier), \
             mock.patch.object(guard.subprocess, 'Popen', return_value=process), \
             mock.patch.object(guard, 'loaded_qt_core', return_value={'status': 'not_observed', 'reason': 'short_lived'}):
            result = guard.verified_app_process(['app'], {'capture_output': True, 'timeout': 60}, self.values, output)
        self.assertEqual(result.returncode, 0)
        record = json.loads((output / 'app-process.json').read_text(encoding='utf-8'))
        self.assertIsNone(record['identity'])
        self.assertEqual(record['identity_status'], 'not_observed_process_exited')
        process.terminate.assert_not_called()

    def test_receipts_distinguish_unobserved_app_qt_from_verified_execution(self):
        identity = {'sid': self.values['SID'], 'session': 1, 'integrity_rid': 12288,
                    'auth_luid': self.values['AUTH_LUID'], 'elevation_type': 'full', 'pid': 33}
        for number, option in enumerate(('--version', '--help')):
            output = self.runroot / 'app-guard' / ('launch-' + f'{number:032x}'); output.mkdir()
            command = [str(self.app), '--profile-dir', str(self.runroot / 'tmp' / option[2:]), option]
            (output / 'app-argv.json').write_text(json.dumps({'case': 'WindowsApplicationContract', 'argv': command}), encoding='utf-8')
            (output / 'guard-status.json').write_text(json.dumps({'status': 'completed', 'lock_retained': False}), encoding='utf-8')
            qt = {'status': 'observed', 'path': str(self.qt)} if number == 0 else {'status': 'not_observed', 'reason': 'short_lived'}
            (output / 'app-process.json').write_text(json.dumps({'identity': identity, 'identity_status': 'observed', 'qt_core': qt}), encoding='utf-8')
            now = datetime.now(timezone.utc)
            (output / 'app-start.json').write_text(json.dumps({'argv': command, 'cwd': str(self.root),
                                                              'started_utc': (now + timedelta(seconds=1)).isoformat()}), encoding='utf-8')
            (output / 'app-exit.json').write_text(json.dumps({'exit_code': 0,
                                                             'completed_utc': (now + timedelta(seconds=2)).isoformat()}), encoding='utf-8')
            for phase in ('before', 'after'):
                (output / (phase + '.process.json')).write_text(json.dumps({'argv': guard.probe_command(self.values), 'exit_code': 0}), encoding='utf-8')
                snapshot = dict(self.snapshot)
                when = now if phase == 'before' else now + timedelta(seconds=3)
                snapshot.update(checked_at_utc=when.isoformat(), completed_at_utc=when.isoformat())
                (output / (phase + '.stdout.bin')).write_text(json.dumps(snapshot), encoding='utf-8')
        with mock.patch.object(launcher, 'load_source_module', return_value=guard):
            records, issues = launcher.audit_app_guard_receipts(self.root, self.runroot, self.env, {'WindowsApplicationContract'}, set())
        self.assertEqual(len(records['WindowsApplicationContract']), 2)
        self.assertEqual(len(issues), 1)
        self.assertIn('not observed', issues[0])
        first = self.runroot / 'app-guard' / ('launch-' + '0' * 32) / 'guard-status.json'
        first.write_text(json.dumps({'status': 'uncertain', 'lock_retained': None}), encoding='utf-8')
        with mock.patch.object(launcher, 'load_source_module', return_value=guard):
            _, issues = launcher.audit_app_guard_receipts(self.root, self.runroot, self.env, {'WindowsApplicationContract'}, set())
        self.assertTrue(any('lock release was not confirmed' in issue for issue in issues))
        process_file = first.parent / 'app-process.json'
        process_evidence = json.loads(process_file.read_text(encoding='utf-8'))
        process_evidence['identity']['session'] = True
        process_file.write_text(json.dumps(process_evidence), encoding='utf-8')
        with mock.patch.object(launcher, 'load_source_module', return_value=guard), self.assertRaises(launcher.LauncherError):
            launcher.audit_app_guard_receipts(self.root, self.runroot, self.env, {'WindowsApplicationContract'}, set())


if __name__ == '__main__':
    unittest.main()
