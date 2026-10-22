# SPDX-License-Identifier: MPL-2.0
"""Isolated synthetic IFW install -> production replacement slot -> uninstall.

Not a full application acceptance test. Never point this at an existing install.
Failures retain the unique fixture root; no manual target deletion or retry.
"""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import uuid
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
UUID_RE = r'\{[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\}'
REGISTRY_ROOT = 'Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\'


def registrations(identifier):
    """Read only this exact test UUID, never a DisplayName/product search."""
    import winreg
    if not re.fullmatch(UUID_RE, identifier):
        raise AssertionError('Invalid fixture UUID')
    results = []
    scopes = [(winreg.HKEY_CURRENT_USER, 0, 'user')]
    scopes += [(winreg.HKEY_LOCAL_MACHINE, view, name) for view, name in
               ((winreg.KEY_WOW64_64KEY, 'machine64'), (winreg.KEY_WOW64_32KEY, 'machine32'))]
    for hive, view, name in scopes:
        try:
            key = winreg.OpenKey(hive, REGISTRY_ROOT + identifier, 0, winreg.KEY_READ | view)
        except FileNotFoundError:
            continue
        with key:
            results.append(dict(scope=name, location=winreg.QueryValueEx(key, 'InstallLocation')[0],
                                uninstall=winreg.QueryValueEx(key, 'UninstallString')[0]))
    return results


def validate_registration(rows, target, parse_argv=None):
    from windows_installer_live import normalized, windows_argv
    parse_argv = parse_argv or windows_argv
    if len(rows) != 1 or rows[0]['scope'] != 'user':
        raise AssertionError('Fixture UUID is missing, ambiguous or not current-user')
    if normalized(rows[0]['location']) != normalized(target):
        raise AssertionError('Fixture UUID target identity mismatch')
    argv = parse_argv(rows[0]['uninstall'])
    if len(argv) != 2 or argv[1] != '--start-uninstaller' or normalized(argv[0]) != normalized(Path(target) / 'maintenancetool.exe'):
        raise AssertionError('Fixture UUID maintenance-tool identity mismatch')


def create_duplicate(identifier, row):
    """Atomic new key, known fresh UUID only; used solely for a refusal control."""
    import winreg
    if registrations(identifier):
        raise AssertionError('Duplicate-control UUID already exists')
    api = ctypes.WinDLL('advapi32', use_last_error=True)
    api.RegCreateKeyExW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint,
        ctypes.c_wchar_p, ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_uint)]
    api.RegCreateKeyExW.restype = ctypes.c_long
    api.RegCloseKey.argtypes = [ctypes.c_void_p]
    with winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER) as base:
        handle, disposition = ctypes.c_void_p(), ctypes.c_uint()
        status = api.RegCreateKeyExW(int(base), REGISTRY_ROOT + identifier, 0, None, 0,
                                    winreg.KEY_SET_VALUE, None, ctypes.byref(handle), ctypes.byref(disposition))
        if status:
            raise AssertionError('Could not create isolated negative-control UUID')
        api.RegCloseKey(handle)
        if disposition.value != 1:  # REG_CREATED_NEW_KEY, never adopt existing data.
            raise AssertionError('Negative-control UUID collision')
        with winreg.OpenKey(base, REGISTRY_ROOT + identifier, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, 'InstallLocation', 0, winreg.REG_SZ, row['location'])
            winreg.SetValueEx(key, 'UninstallString', 0, winreg.REG_SZ, row['uninstall'])


def delete_duplicate(identifier, expected):
    import winreg
    if registrations(identifier) != [expected]:
        raise AssertionError('Negative-control UUID changed; refusing to remove it')
    winreg.DeleteKey(winreg.HKEY_CURRENT_USER, REGISTRY_ROOT + identifier)


def fixture_values(paths, identifier):
    # Both Start Menu roots must be overridden before IFW constructs its pages.
    return ['TargetDir=' + str(paths['target']), 'ProductUUID=' + identifier,
            'UserStartMenuProgramsPath=' + str(paths['userMenu']),
            'AllUsersStartMenuProgramsPath=' + str(paths['allMenu']),
            'StartMenuDir=' + paths['group'], 'DesktopDir=' + str(paths['desktop']),
            'AllUsers=false', 'RunProgram=']


def checked_process(argv, output, environment, timeout=180, allowed=(0,)):
    # No subprocess.run timeout kill: a running uninstaller must finish naturally.
    # On timeout the independent root is retained and no installation follows.
    with output.open('wb') as stream:
        try:
            process = subprocess.Popen(list(map(str, argv)), stdout=stream, stderr=subprocess.STDOUT, env=environment)
        except OSError:
            raise AssertionError('Synthetic process could not start: ' + output.stem) from None
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            raise AssertionError('Synthetic process timed out; fixture retained, no retry: ' + output.stem) from None
    content = output.read_text(encoding='utf-8', errors='replace')
    # Fixed phase names and error categories only, never raw argv or host data.
    print('UPGRADE_PROCESS:' + output.stem + ':exit=' + str(code), flush=True)
    for marker in re.findall(r'\b(?:UPGRADE_CONTROLLER:(?:guard-failed|introduction|target|components|start-menu|ready|installed|finished)|PJ_REPLACEMENT_(?:VERIFIED|BLOCKED:(?:identity|start|wait|residual|supervisor-result)))\b', content):
        print(marker, flush=True)
    if code not in allowed:
        raise AssertionError('Synthetic process returned an unexpected exit status: ' + output.stem)
    return content


def build_fixture(stage, label, creator, translations, environment, stage_inputs):
    stage.mkdir()
    config, packages, meta, _, _ = stage_inputs(ROOT, stage)
    config_xml = ET.parse(config)
    config_xml.getroot().find('Version').text = '0.0.' + ('1' if label == 'old' else '2')
    config_xml.getroot().find('RunProgram').text = ''
    config_xml.write(config, encoding='utf-8', xml_declaration=True)
    package = ET.parse(meta / 'package.xml')
    package.getroot().find('Version').text = config_xml.getroot().findtext('Version')
    licenses = package.getroot().find('Licenses')
    if licenses is not None:
        package.getroot().remove(licenses)  # Only our inert synthetic data, no license acceptance.
    package.write(meta / 'package.xml', encoding='utf-8', xml_declaration=True)
    data = meta.parent / 'data'
    (data / 'SYNTHETIC-NOT-AN-APPLICATION.txt').unlink()
    (data / 'FIXTURE-RECEIPT.txt').write_text('PJ-SYNTHETIC-' + label.upper(), encoding='utf-8')
    (data / 'bin').mkdir()
    # Inert text, NOT a PE executable. A bad RunProgram override cannot run an app.
    (data / 'bin/PlotJuggler4.exe').write_text('NOT AN EXECUTABLE: synthetic shortcut target only', encoding='ascii')
    fixture = stage / ('SYNTHETIC-' + label.upper() + '-FIXTURE.exe')
    checked_process([creator, '--offline-only', '-r', translations, '-c', config, '-p', packages, fixture],
                    stage / 'build.log', environment)
    return fixture.resolve(strict=True)


def validate_records(records, config, fixture, controller, parse_argv=None, refused=False):
    from windows_installer_live import normalized, windows_argv
    parse_argv = parse_argv or windows_argv
    expected = ['introduction', 'target', 'components', 'start-menu', 'ready', 'installed', 'finished']
    kinds = [row['kind'] for row in records]
    if refused:
        if not kinds or kinds[0] != 'introduction' or 'target' not in kinds or any(kind not in expected[:3] for kind in kinds):
            raise AssertionError('Refused replacement reached an unexpected page')
    elif kinds != expected:
        raise AssertionError('Unexpected synthetic upgrade page/finish sequence')
    if len({row['pid'] for row in records}) != 1:
        raise AssertionError('Upgrade observer changed installer process')
    for row in records:
        if normalized(Path(row['executable']).resolve()) != normalized(Path(fixture).resolve()):
            raise AssertionError('Upgrade observer is not a child of the exact fixture')
        for name in ('target', 'userMenu', 'allMenu', 'desktop'):
            if normalized(row[name]) != normalized(config[name]):
                raise AssertionError('Upgrade location escaped its fixture')
        for name in ('TEMP', 'TMP'):
            if normalized(row[name]) != normalized(config['temporary']):
                raise AssertionError('Upgrade temporary environment escaped its fixture')
        if row['uuid'] != config['newUuid'] or row['allUsers'] != 'false' or row['runProgram'] != '':
            raise AssertionError('Upgrade UUID/user scope/RunProgram changed')
        argv = parse_argv(row['commandLine'])
        for flag, value in (('--script', controller), ('--cache-path', config['cache'])):
            if argv.count(flag) != 1 or normalized(argv[argv.index(flag) + 1]) != normalized(value):
                raise AssertionError('Upgrade controller or cache argument missing')
    if refused:
        return
    ready = records[4]
    if ready['targetPresent'] or ready['toolPresent'] or ready['oldKeyPresent']:
        raise AssertionError('Old target/tool/UUID not gone before new installation')
    if normalized(ready['menu']) != normalized(Path(config['userMenu']) / config['group']):
        raise AssertionError('Start Menu resolved outside the fixture')
    if any(row['status'] != 0 for row in records[-2:]):
        raise AssertionError('Synthetic install did not report success')


def probe_upgrade(creator, translations, powershell, stage_inputs):
    if os.name != 'nt':
        raise RuntimeError('Synthetic upgrade integration requires Windows')
    # Independent from the non-installing language probe's TemporaryDirectory.
    # Retain this root on every failure, including a late asynchronous purge.
    root = Path(tempfile.mkdtemp(prefix='pj isolated upgrade fixture ')).resolve()
    complete = False
    paths = {name: root / name for name in ('target', 'userMenu', 'allMenu', 'desktop', 'temporary')}
    paths['group'] = 'SyntheticFixtureGroup'
    identifiers = ['{' + str(uuid.uuid4()) + '}' for _ in range(3)]
    old_uuid, new_uuid, duplicate_uuid = identifiers
    for identifier in identifiers:
        if registrations(identifier):
            raise AssertionError('Fixture UUID collision before installation')
    for name in ('userMenu', 'allMenu', 'desktop', 'temporary'):
        paths[name].mkdir()
    environment = dict(os.environ)
    environment.update(TEMP=str(paths['temporary']), TMP=str(paths['temporary']), QT_QPA_PLATFORM='windows')
    for name in ('QT_PLUGIN_PATH', 'QT_QPA_PLATFORM_PLUGIN_PATH', 'QML2_IMPORT_PATH'):
        environment.pop(name, None)
    config = {key: str(value) for key, value in paths.items()}
    config.update(oldUuid=old_uuid, newUuid=new_uuid, tool=str(paths['target'] / 'maintenancetool.exe'),
                  receipt=str(paths['target'] / 'FIXTURE-RECEIPT.txt'), powershell=str(powershell),
                  oldReceipt='PJ-SYNTHETIC-OLD', newReceipt='PJ-SYNTHETIC-NEW', cache=str(paths['temporary'] / 'new-cache'))
    try:
        old = build_fixture(root / 'old-build', 'old', creator, translations, environment, stage_inputs)
        new = build_fixture(root / 'new-build', 'new', creator, translations, environment, stage_inputs)
        if paths['target'].exists():
            raise AssertionError('Old fixture target unexpectedly exists before installation')
        checked_process([old, '--root', paths['target'], '--cache-path', paths['temporary'] / 'old-cache',
                         '--confirm-command', 'install', *fixture_values(paths, old_uuid)], root / 'old-install.log', environment)
        receipt = Path(config['receipt'])
        baseline = registrations(old_uuid)
        validate_registration(baseline, paths['target'])
        if receipt.read_text(encoding='utf-8') != config['oldReceipt']:
            raise AssertionError('Old synthetic receipt missing')
        if not (paths['temporary'] / 'old-cache').is_dir():
            raise AssertionError('Explicit old fixture cache was not created')
        baseline_hash = hashlib.sha256(Path(config['tool']).read_bytes()).hexdigest()
        print('UPGRADE: old synthetic receipt and exact current-user UUID/tool identity verified', flush=True)
        template = (ROOT / 'scripts/windows_installer_upgrade.qs.in').read_text(encoding='utf-8')
        for mode in ('refuse-duplicate', 'replace'):
            if mode == 'refuse-duplicate':
                create_duplicate(duplicate_uuid, baseline[0])
            elif registrations(old_uuid) != baseline or registrations(new_uuid):
                raise AssertionError('Fixture identities changed before positive replacement')
            controller = root / (mode + '.qs')
            log = root / (mode + '.jsonl')
            run_config = dict(config, mode=mode, log=str(log))
            controller.write_text(template.replace('__UPGRADE_CONFIG__', json.dumps(run_config, ensure_ascii=True)), encoding='utf-8')
            output = checked_process([new, '--verbose', '--lang', 'en_US', '--cache-path', config['cache'],
                                      '--script', controller, *fixture_values(paths, new_uuid)],
                                     root / (mode + '.log'), environment, allowed=(0, 1, 3) if mode == 'refuse-duplicate' else (0,))
            records = [json.loads(line) for line in log.read_text(encoding='utf-8-sig').splitlines() if line]
            if mode == 'refuse-duplicate':
                if 'PJ_REPLACEMENT_BLOCKED:identity' not in output or 'PJ_REPLACEMENT_VERIFIED' in output:
                    raise AssertionError('Ambiguous UUID did not fail closed in the production slot')
                validate_records(records, run_config, new, controller, refused=True)
                if (registrations(old_uuid) != baseline or registrations(new_uuid) or
                    receipt.read_text(encoding='utf-8') != config['oldReceipt'] or
                    hashlib.sha256(Path(config['tool']).read_bytes()).hexdigest() != baseline_hash):
                    raise AssertionError('Refused replacement modified the old fixture')
                delete_duplicate(duplicate_uuid, baseline[0])
                print('UPGRADE: real production slot rejected ambiguous UUID and preserved old fixture', flush=True)
            else:
                if output.count('PJ_REPLACEMENT_VERIFIED') != 1 or 'PJ_REPLACEMENT_BLOCKED' in output:
                    raise AssertionError('Production replacement supervisor did not verify cleanup')
                validate_records(records, run_config, new, controller)
        if not Path(config['cache']).is_dir():
            raise AssertionError('Explicit new fixture cache was not created')
        if registrations(old_uuid) or registrations(duplicate_uuid):
            raise AssertionError('Old or negative-control UUID survived replacement')
        validate_registration(registrations(new_uuid), paths['target'])
        if receipt.read_text(encoding='utf-8') != config['newReceipt']:
            raise AssertionError('New synthetic receipt missing')
        expected_links = [paths['userMenu'] / paths['group'] / 'PlotJuggler 4 zh-CN.lnk',
                          paths['desktop'] / 'PlotJuggler 4 zh-CN.lnk']
        if not all(link.is_file() for link in expected_links) or list(paths['allMenu'].rglob('*.lnk')):
            raise AssertionError('Synthetic shortcuts did not stay in current-user fixture roots')
        print('UPGRADE: production purge/contained cleanup preceded new receipt, UUID and isolated shortcuts', flush=True)
        # Final cleanup only, never before the production replacement slot.
        output = checked_process([powershell, '-NoProfile', '-NonInteractive', '-File',
                                  ROOT / 'packaging/installer/replacement_guard.ps1', '-TargetPath', paths['target']],
                                 root / 'final-uninstall.log', environment)
        if output.strip() != 'PJ_REPLACEMENT_OK' or paths['target'].exists() or any(registrations(i) for i in identifiers):
            raise AssertionError('Final synthetic uninstall did not fully complete')
        if any(link.exists() for link in expected_links):
            raise AssertionError('Synthetic shortcuts survived final uninstall')
        complete = True
        print('PASS: synthetic IFW continuous replacement and cleanup only; full application acceptance remains separate', flush=True)
    finally:
        if complete:
            shutil.rmtree(root)  # All installation processes and their jobs finished naturally.
        else:
            print('FAIL: isolated upgrade fixture retained; no manual target deletion, retry or broad process kill', flush=True)
