#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Optionally guard each real-App launch with an audited read-only Qt probe.

The unmodified default path uses subprocess.run. The native-kit launcher is
responsible for authenticating this module, the probe and expected identity.
Each successful probe is only a moment-in-time snapshot, not an OS sandbox.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import ntpath
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
import ctypes
from ctypes import wintypes


class GuardError(Exception):
    """A required app-launch safety snapshot did not establish its conditions."""


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def settings(env):
    flag = env.get('PJ_NATIVE_APP_GUARD_REQUIRED')
    if flag is None:
        return None
    if flag != '1':
        raise GuardError('invalid required-app-guard flag')
    keys = ('PROBE', 'PROBE_SHA256', 'QT_CORE', 'QT_CORE_SHA256', 'QT_VERSION', 'EXECUTABLE',
            'EXECUTABLE_SHA256', 'SID', 'SESSION', 'INTEGRITY_RID', 'AUTH_LUID', 'ELEVATION_TYPE', 'RUN_ROOT')
    values = {key: env.get('PJ_NATIVE_APP_' + key, '') for key in keys}
    if any(not value for value in values.values()):
        raise GuardError('required application guard inputs are missing')
    if (any(not re.fullmatch(r'[0-9a-f]{64}', values[key]) for key in ('PROBE_SHA256', 'QT_CORE_SHA256', 'EXECUTABLE_SHA256')) or
            not re.fullmatch(r'[0-9a-f]{8}:[0-9a-f]{8}', values['AUTH_LUID']) or
            values['ELEVATION_TYPE'] not in ('default', 'full', 'limited')):
        raise GuardError('invalid application guard identity')
    try:
        if int(values['SESSION']) <= 0 or int(values['INTEGRITY_RID']) <= 0:
            raise ValueError
    except ValueError:
        raise GuardError('invalid application guard session or integrity') from None
    probe, qt, executable, run_root = (Path(values[key]) for key in ('PROBE', 'QT_CORE', 'EXECUTABLE', 'RUN_ROOT'))
    if any(not path.is_absolute() for path in (probe, qt, executable, run_root)):
        raise GuardError('application guard paths must be absolute')
    for path in (probe, qt, executable, run_root):
        for part in (path, *path.parents):
            info = part.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                raise GuardError('application guard path contains a link or reparse point')
    if (not probe.is_file() or not qt.is_file() or not executable.is_file() or not run_root.is_dir() or
            digest(probe) != values['PROBE_SHA256'] or digest(qt) != values['QT_CORE_SHA256'] or
            digest(executable) != values['EXECUTABLE_SHA256']):
        raise GuardError('application guard executable, Qt or run root differs')
    expected_temp = (run_root / 'tmp').resolve(strict=True)
    for key in ('TEMP', 'TMP'):
        if not env.get(key) or Path(env[key]).resolve(strict=True) != expected_temp:
            raise GuardError('real-App TEMP/TMP is not the verified run directory')
    return values


def validate_snapshot(output, expected, started=None, finished=None):
    try:
        doc = json.loads(output.decode('utf-8'))
        token, qt = doc['token'], doc['qt']
        wanted = {'sid': expected['SID'], 'session': int(expected['SESSION']),
                  'process_session': int(expected['SESSION']), 'integrity_rid': int(expected['INTEGRITY_RID']),
                  'auth_luid': expected['AUTH_LUID'], 'elevation_type': expected['ELEVATION_TYPE']}
        if (doc.get('schema') != 'pj-native-app-marker-probe/v1' or doc.get('ok') is not True or
                type(doc.get('exit_code')) is not int or doc.get('exit_code') != 0 or
                doc.get('reason') != 'clean_snapshot' or doc.get('platform') != 'windows' or
                doc.get('marker_enumeration_ok') is not True or doc.get('process_enumeration_ok') is not True or
                type(doc.get('matching_marker_count')) is not int or doc.get('matching_marker_count') != 0 or
                type(doc.get('other_app_process_count')) is not int or doc.get('other_app_process_count') != 0 or
                not isinstance(doc.get('marker_directory_exists'), bool) or
                not isinstance(doc.get('marker_directory'), str) or not doc['marker_directory'] or
                not ntpath.isabs(doc['marker_directory']) or type(token.get('restricting_sid_count')) is not int or
                token.get('restricting_sid_count') != 0 or
                token.get('app_container') is not False or
                type(doc.get('probe_pid')) is not int or doc['probe_pid'] <= 0 or
                not doc.get('checked_at_utc') or not doc.get('completed_at_utc')):
            raise GuardError('app guard snapshot is incomplete or reports unsafe state')
        checked = datetime.fromisoformat(doc['checked_at_utc'].replace('Z', '+00:00'))
        completed = datetime.fromisoformat(doc['completed_at_utc'].replace('Z', '+00:00'))
        if (checked.utcoffset() != timedelta(0) or completed.utcoffset() != timedelta(0) or checked > completed or
                (started is not None and checked < started - timedelta(seconds=3)) or
                (finished is not None and completed > finished + timedelta(seconds=3))):
            raise GuardError('app guard snapshot timestamps are stale or inconsistent')
        for key, value in wanted.items():
            actual = token.get(key)
            if isinstance(value, str):
                if not isinstance(actual, str) or actual.casefold() != value.casefold():
                    raise GuardError('app guard token differs: ' + key)
            elif type(actual) is not int or actual != value:
                raise GuardError('app guard token differs: ' + key)
        if (qt.get('runtime_version') != expected['QT_VERSION'] or qt.get('compiled_version') != expected['QT_VERSION'] or
                os.path.normcase(os.path.normpath(qt.get('core_module_path', ''))) !=
                os.path.normcase(os.path.normpath(expected['QT_CORE']))):
            raise GuardError('app guard loaded an unexpected Qt runtime')
        return doc
    except (ValueError, UnicodeDecodeError, KeyError, TypeError, AttributeError) as exc:
        raise GuardError('invalid app guard snapshot: ' + str(exc)) from exc


def probe_command(values):
    return [values['PROBE'], '--expect-sid', values['SID'], '--expect-session', values['SESSION'],
            '--expect-integrity-rid', values['INTEGRITY_RID'], '--expect-auth-luid', values['AUTH_LUID'],
            '--expect-elevation-type', values['ELEVATION_TYPE'], '--expect-qt-core', values['QT_CORE']]


def snapshot(values, env, output, phase):
    cmd = probe_command(values)
    if digest(values['PROBE']) != values['PROBE_SHA256']:
        raise GuardError('application guard executable changed before ' + phase)
    started = datetime.now(timezone.utc)
    try:
        result = subprocess.run(cmd, env=env, capture_output=True, timeout=30)
    except subprocess.TimeoutExpired as exc:
        (output / (phase + '.stdout.bin')).write_bytes(exc.stdout or b'')
        (output / (phase + '.stderr.bin')).write_bytes(exc.stderr or b'')
        (output / (phase + '.process.json')).write_text(
            json.dumps({'argv': cmd, 'exit_code': None, 'status': 'timeout'}) + '\n', encoding='utf-8')
        raise GuardError('application guard timed out during ' + phase) from exc
    (output / (phase + '.stdout.bin')).write_bytes(result.stdout)
    (output / (phase + '.stderr.bin')).write_bytes(result.stderr)
    (output / (phase + '.process.json')).write_text(json.dumps({'argv': cmd, 'exit_code': result.returncode}, indent=2) + '\n', encoding='utf-8')
    if result.returncode != 0:
        raise GuardError('application guard rejected ' + phase + ' snapshot')
    return validate_snapshot(result.stdout, values, started, datetime.now(timezone.utc))


def loaded_qt_core(process, timeout=0.5):
    """Best-effort observation only; short-lived processes may exit first."""
    if sys.platform != 'win32':
        return {'status': 'not_observed', 'reason': 'not_windows'}
    system_root = os.environ.get('SystemRoot')
    if not system_root:
        return {'status': 'not_observed', 'reason': 'system_root_unavailable'}
    psapi = ctypes.WinDLL(str(Path(system_root) / 'System32/psapi.dll'), use_last_error=True)
    psapi.EnumProcessModulesEx.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.HMODULE), wintypes.DWORD,
                                           ctypes.POINTER(wintypes.DWORD), wintypes.DWORD]
    psapi.EnumProcessModulesEx.restype = wintypes.BOOL
    psapi.GetModuleFileNameExW.argtypes = [wintypes.HANDLE, wintypes.HMODULE, wintypes.LPWSTR, wintypes.DWORD]
    psapi.GetModuleFileNameExW.restype = wintypes.DWORD
    deadline = time.monotonic() + timeout
    last_reason = 'module_not_loaded_before_exit_or_timeout'
    while time.monotonic() <= deadline:
        modules = (wintypes.HMODULE * 4096)(); needed = wintypes.DWORD()
        if not psapi.EnumProcessModulesEx(int(process._handle), modules, ctypes.sizeof(modules), ctypes.byref(needed), 3):
            last_reason = 'module_enumeration_error_' + str(ctypes.get_last_error())
        elif needed.value > ctypes.sizeof(modules):
            return {'status': 'not_observed', 'reason': 'module_list_exceeds_bound'}
        else:
            for module in modules[:needed.value // ctypes.sizeof(wintypes.HMODULE)]:
                path = ctypes.create_unicode_buffer(32768)
                length = psapi.GetModuleFileNameExW(int(process._handle), module, path, len(path))
                if not length or length >= len(path):
                    return {'status': 'not_observed', 'reason': 'module_path_unavailable'}
                if ntpath.basename(path.value).casefold() == 'qt6core.dll':
                    return {'status': 'observed', 'path': path.value}
        if process.poll() is not None:
            break
        time.sleep(0.01)
    return {'status': 'not_observed', 'reason': last_reason}


def verified_app_process(command, kwargs, values, output):
    """Preserve the two test scripts' subprocess options and check child token."""
    options = dict(kwargs)
    timeout = options.pop('timeout', None)
    if options.pop('capture_output', False) is not True or set(options) - {'env', 'text', 'encoding', 'errors'}:
        raise GuardError('unsupported real-App subprocess options')
    spec = importlib.util.spec_from_file_location('native_token_verifier', Path(__file__).with_name('run_native_test_bundle.py'))
    launcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launcher)
    expected = {'sid': values['SID'], 'session': int(values['SESSION']),
                'integrity_rid': int(values['INTEGRITY_RID']), 'auth_luid': values['AUTH_LUID'],
                'elevation_type': values['ELEVATION_TYPE']}
    (output / 'app-start.json').write_text(json.dumps({'argv': [str(x) for x in command], 'cwd': os.getcwd(),
                                                       'started_utc': datetime.now(timezone.utc).isoformat(),
                                                       'outcome': 'uncertain until process and exit receipts exist'}) + '\n', encoding='utf-8')
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **options) as process:
        try:
            identity = launcher.process_identity(int(process._handle), process.pid)
        except Exception as exc:
            if process.poll() is not None:
                identity = None
            else:
                try:
                    process.terminate()
                except OSError:
                    pass
                raise GuardError('real-App child token was not verified; its outcome may be uncertain') from exc
        try:
            if identity is not None:
                launcher.require_identity(identity, expected)
        except Exception as exc:
            try:
                process.terminate()
            except OSError:
                pass
            raise GuardError('real-App child token mismatched; its outcome may be uncertain') from exc
        qt_evidence = loaded_qt_core(process)
        (output / 'app-process.json').write_text(json.dumps({'identity': identity,
            'identity_status': 'observed' if identity is not None else 'not_observed_process_exited',
            'qt_core': qt_evidence}, indent=2) + '\n', encoding='utf-8')
        if (qt_evidence['status'] == 'observed' and
                os.path.normcase(os.path.normpath(qt_evidence['path'])) !=
                os.path.normcase(os.path.normpath(values['QT_CORE']))):
            try:
                process.terminate()
            except OSError:
                pass
            raise GuardError('real-App loaded a different QtCore; process outcome may be uncertain')
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            process.kill()
            stdout, stderr = process.communicate()
            raise subprocess.TimeoutExpired(command, timeout, output=stdout, stderr=stderr) from exc
        return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)


def acquire_launch_lock(run_root, output):
    """One nonblocking lock per kit across cooperating launchers and runs.

    A stale lock is never removed automatically. It is evidence that an earlier
    launch may not have completed safely. This is not an OS-wide app sandbox.
    """
    shared = run_root.parent
    if (not shared.is_dir() or shared.is_symlink() or
            getattr(shared.lstat(), 'st_file_attributes', 0) & 0x400):
        raise GuardError('shared launch-lock directory is not an ordinary directory')
    lock = shared / '.native-app-launch.lock'
    identity = {'schema': 1, 'run_root': str(run_root), 'pid': os.getpid(),
                'nonce': uuid.uuid4().hex, 'evidence': str(output)}
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise GuardError('another guarded launch is active or a prior launch needs review') from exc
    except OSError as exc:
        raise GuardError('cannot acquire the shared launch lock') from exc
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
            json.dump(identity, stream, sort_keys=True)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        info = lock.lstat()
        if not stat.S_ISREG(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise GuardError('shared launch lock is not an ordinary file')
        return lock, identity, (info.st_dev, info.st_ino)
    except BaseException:
        # A partially established lock remains as an explicit fail-closed record.
        raise


def release_launch_lock(lock, identity, original_file):
    """Remove only the exact lock this process created, after a safe outcome."""
    info = lock.lstat()
    if (not stat.S_ISREG(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400 or
            (info.st_dev, info.st_ino) != original_file or
            json.loads(lock.read_text(encoding='utf-8')) != identity):
        raise GuardError('shared launch lock changed; it was retained for review')
    lock.unlink()


def run(command, *, guard_case=None, **kwargs):
    """Take a fresh before/after snapshot for this individual App process."""
    env = kwargs.get('env')
    if env is None:
        env = os.environ
    values = settings(env)
    if values is None:
        return subprocess.run(command, **kwargs)
    if guard_case not in ('ArduPilotLayoutRestoreTest', 'WindowsApplicationContract'):
        raise GuardError('an exact reviewed CTest case identity is required')
    run_root = Path(values['RUN_ROOT'])
    args = list(command)
    if (not args or Path(args[0]).resolve(strict=True) != Path(values['EXECUTABLE']).resolve(strict=True) or
            args.count('--profile-dir') != 1 or args.index('--profile-dir') + 1 >= len(args)):
        raise GuardError('real-App path or explicit profile argument differs')
    profile = Path(args[args.index('--profile-dir') + 1])
    temp = (run_root / 'tmp').resolve(strict=True)
    if not profile.is_absolute() or not profile.resolve().is_relative_to(temp):
        raise GuardError('real-App profile is outside the verified run temporary root')
    for part in (profile, *profile.parents):
        if part.exists() or part.is_symlink():
            info = part.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                raise GuardError('real-App profile contains a link or reparse point')
        if part == temp:
            break
    evidence_root = run_root / 'app-guard'
    if not evidence_root.is_dir() or evidence_root.is_symlink() or getattr(evidence_root.lstat(), 'st_file_attributes', 0) & 0x400:
        raise GuardError('application guard evidence root is not a verified directory')
    output = evidence_root / ('launch-' + uuid.uuid4().hex)
    output.mkdir()
    (output / 'app-argv.json').write_text(json.dumps({'case': guard_case, 'argv': [str(x) for x in command]}, indent=2) + '\n', encoding='utf-8')
    try:
        lock, lock_identity, lock_file = acquire_launch_lock(run_root, output)
    except BaseException as exc:
        (output / 'guard-status.json').write_text(json.dumps({'status': 'not_started',
            'reason': 'shared launch lock unavailable', 'exception_type': type(exc).__name__}) + '\n', encoding='utf-8')
        raise
    launched, safe_to_release = False, False
    try:
        try:
            snapshot(values, env, output, 'before')
        except BaseException:
            # No application was started and a completed snapshot was not asserted.
            safe_to_release = True
            raise
        launched = True
        result, error = None, None
        try:
            result = verified_app_process(command, kwargs, values, output)
            (output / 'app-exit.json').write_text(json.dumps({'exit_code': result.returncode,
                'completed_utc': datetime.now(timezone.utc).isoformat()}) + '\n', encoding='utf-8')
        except BaseException as exc:
            error = exc
            (output / 'app-exit.json').write_text(json.dumps({'exit_code': None, 'exception_type': type(exc).__name__,
                'completed_utc': datetime.now(timezone.utc).isoformat(), 'outcome': 'uncertain'}) + '\n', encoding='utf-8')
        try:
            snapshot(values, env, output, 'after')
        except Exception as exc:
            raise GuardError('application post-launch safety snapshot failed: ' + str(exc)) from exc
        if error is not None:
            raise error
        safe_to_release = True
        return result
    finally:
        if safe_to_release:
            try:
                release_launch_lock(lock, lock_identity, lock_file)
            except BaseException as exc:
                # An OS error may have an uncertain outcome; never claim the
                # lock was removed merely because releasing was attempted.
                (output / 'guard-status.json').write_text(json.dumps({'status': 'uncertain',
                    'lock_retained': None, 'lock_release_error': type(exc).__name__}) + '\n', encoding='utf-8')
                raise
            (output / 'guard-status.json').write_text(json.dumps({'status': 'completed' if launched else 'not_started',
                'lock_retained': False}) + '\n', encoding='utf-8')
        else:
            (output / 'guard-status.json').write_text(json.dumps({'status': 'uncertain', 'lock_retained': True}) + '\n', encoding='utf-8')
