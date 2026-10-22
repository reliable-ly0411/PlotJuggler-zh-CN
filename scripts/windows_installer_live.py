# SPDX-License-Identifier: MPL-2.0
"""Windows-only synthetic installer GUI mechanism probe; never installs payload."""
import ctypes
import json
import os
import ntpath
from pathlib import Path
import subprocess
import time


def windows_argv(command):
    shell = ctypes.WinDLL('shell32', use_last_error=True)
    shell.CommandLineToArgvW.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_int)]
    shell.CommandLineToArgvW.restype = ctypes.POINTER(ctypes.c_wchar_p)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    count = ctypes.c_int()
    result = shell.CommandLineToArgvW(command, ctypes.byref(count))
    if not result:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return [result[i] for i in range(count.value)]
    finally:
        kernel.LocalFree(result)


def normalized(path):
    return ntpath.normcase(ntpath.abspath(str(path)))


def validate_records(records, fixture, controller, targets, parse_argv=windows_argv):
    expected = ['introduction', 'target-before-edit', 'target-edited', 'before-switch',
                'introduction', 'target-before-edit', 'target-edited', 'before-switch',
                'introduction', 'finished']
    if [r['kind'] for r in records] != expected:
        raise AssertionError('Unexpected controller event sequence')
    intros = [r for r in records if r['kind'] == 'introduction']
    if len({r['pid'] for r in intros}) != 3:
        raise AssertionError('Expected three distinct real installer processes')
    for i, row in enumerate(intros):
        language = ['zh_CN', 'en_US', 'zh_CN'][i]
        if row['language'] != language or normalized(row['target']) != normalized(targets[i]):
            raise AssertionError('Restart language/TargetDir not preserved')
        # Python's Windows temp root can be RUNNER~1 while CIM returns its
        # long form. Resolve existing files, without weakening path identity.
        if normalized(Path(row['executable']).resolve()) != normalized(Path(fixture).resolve()):
            raise AssertionError('Observer was not a child of the exact fixture')
        if row['liveFixturePids'] != [row['pid']]:
            raise AssertionError('A previous fixture did not exit naturally before its successor')
        argv = parse_argv(row['commandLine'])
        cache = Path(controller).parent / 'tmp' / 'ifw-cache'
        if argv.count('--cache-path') != 1 or normalized(argv[argv.index('--cache-path') + 1]) != normalized(cache):
            raise AssertionError('Explicit IFW cache path not preserved through restart')
        if 'PJProbeMarker=中文 space user@example.test' not in argv:
            raise AssertionError('Unicode/space/@ startup marker not preserved')
        for variable in ('TEMP', 'TMP'):
            if normalized(row[variable]) != normalized(cache.parent):
                raise AssertionError('IFW temporary environment escaped the fixture')
        if argv[argv.index('--script') + 1] != str(controller):
            raise AssertionError('--script not preserved through restart')
        if normalized(argv[argv.index('--root') + 1]) != normalized(targets[i]):
            raise AssertionError('--root does not reflect current edited TargetDir')
        positional = [arg.split('=', 1)[1] for arg in argv if arg.startswith('TargetDir=')]
        if len(positional) != 1 or normalized(positional[0]) != normalized(targets[i]):
            raise AssertionError('Current TargetDir positional value missing')
        if language == 'zh_CN':
            if '欢迎' not in row['title'] or row['message'] != '欢迎使用 PlotJuggler 4 zh-CN 安装向导。':
                raise AssertionError('Live standard IFW welcome text is not Chinese')
            if '下一步' not in row['nextButton'] or '取消' not in row['cancelButton']:
                raise AssertionError('Live QWizard standard-button defaults are not Chinese')
        else:
            if 'Welcome' not in row['title'] or row['message'] != 'Welcome to the PlotJuggler 4 zh-CN Setup.':
                raise AssertionError('Live standard IFW welcome text is not English')
            if 'Next' not in row['nextButton'] or 'Cancel' not in row['cancelButton']:
                raise AssertionError('Live QWizard standard-button defaults are not English')
    for i, row in enumerate(r for r in records if r['kind'] == 'target-before-edit'):
        title = ['选择安装目录', 'Choose Installation Directory'][i]
        description = ['请选择 PlotJuggler 4 的安装位置：', 'Please select where PlotJuggler 4 will be installed:'][i]
        if row['title'] != title or row['description'] != description:
            raise AssertionError('Live custom TargetWidget title/description translation mismatch')
        print('LIVE CUSTOM UI:', json.dumps({key: row[key] for key in ('language', 'title', 'description')}, ensure_ascii=True))
        if normalized(row['field']) != normalized(targets[i]):
            raise AssertionError('Custom target field did not initialize from restored TargetDir')
    for i, row in enumerate(r for r in records if r['kind'] == 'target-edited'):
        if normalized(row['field']) != normalized(targets[i + 1]) or normalized(row['target']) != normalized(targets[i + 1]):
            raise AssertionError('Real target field signal did not update TargetDir')
    # Print only scoped UI/state evidence. Do not dump host paths/command lines.
    for row in intros:
        print('LIVE STANDARD UI:', json.dumps({key: row[key] for key in
              ('language', 'title', 'message', 'nextButton', 'cancelButton')}, ensure_ascii=True))
    print('PASS: real zh_CN -> en_US -> zh_CN restarts; three PIDs; --script, --root and edited TargetDir preserved.')


def fixture_arguments(fixture, controller, target):
    # IFW 4.10 --root is CLI-only. GUI consumes positional userArguments.
    # Retain --root solely to exercise production restart argv preservation;
    # TargetDir is the authoritative GUI value, including the first process.
    return [str(fixture), '--verbose', '--lang', 'zh_CN',
            '--cache-path', str(Path(controller).parent / 'tmp' / 'ifw-cache'),
            'PJProbeMarker=中文 space user@example.test', '--script', str(controller),
            '--root', str(target), 'TargetDir=' + str(target)]


def probe_gui(fixture, temporary, powershell, template):
    log = temporary / 'live-results.jsonl'
    controller = temporary / 'live controller.qs'
    targets = [temporary / 'unused initial target', temporary / 'edited target 中文 one',
               temporary / "edited target 中文 two's"]
    if any(target.exists() for target in targets):
        raise AssertionError('Synthetic fixture targets must not already exist')
    config = dict(log=str(log), powershell=str(powershell), targets=list(map(str, targets)),
                  changedTargets=list(map(str, targets[1:])))
    controller.write_text(template.read_text(encoding='utf-8').replace('__PROBE_CONFIG__',
                          json.dumps(config, ensure_ascii=True)), encoding='utf-8')
    output = temporary / 'fixture-output.txt'
    escaped = str(fixture.resolve()).replace("'", "''")
    query = "@(Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -and " + \
        "[String]::Equals([IO.Path]::GetFullPath($_.ExecutablePath), '" + escaped + \
        "', [StringComparison]::OrdinalIgnoreCase) })"
    started = time.monotonic()
    finished = False
    records = []
    environment = dict(os.environ)
    cache = temporary / 'tmp' / 'ifw-cache'
    cache.mkdir(parents=True, exist_ok=False)
    environment.update(TEMP=str(cache.parent), TMP=str(cache.parent))
    # Probe the real Windows platform, never an inherited offscreen backend or
    # plugins from the application's different Qt kit. IFW is self-contained.
    environment['QT_QPA_PLATFORM'] = 'windows'
    environment.pop('QT_PLUGIN_PATH', None)
    environment.pop('QT_QPA_PLATFORM_PLUGIN_PATH', None)
    with output.open('wb') as stream:
        child = subprocess.Popen(fixture_arguments(fixture, controller, targets[0]), stdout=stream, stderr=stream,
                                 cwd=temporary, env=environment)
        try:
            while time.monotonic() - started < 100:
                if b'PJ_LANGUAGE_RESTART_FAILED:' in output.read_bytes():
                    raise AssertionError('Production language restart reported failure; see diagnostic stage')
                if log.exists():
                    try:
                        records = [json.loads(line) for line in log.read_text(encoding='utf-8-sig').splitlines() if line]
                    except (ValueError, OSError):
                        time.sleep(.2)
                        continue
                    if any(row.get('kind') == 'finished' for row in records):
                        validate_records(records, fixture, controller, targets)
                        # No forced termination may turn a broken final reject
                        # into a passing result. Previous exits are proven by
                        # each successor's liveFixturePids observation.
                        wait_exit = "$end=(Get-Date).AddSeconds(5); do { $live=" + query + "; if (!$live.Count) { exit 0 }; Start-Sleep -Milliseconds 200 } while ((Get-Date) -lt $end); throw 'Final fixture did not quit naturally'"
                        subprocess.run([str(powershell), '-NoProfile', '-NonInteractive', '-Command', wait_exit],
                                       check=True, capture_output=True, timeout=15)
                        diagnostic = output.read_text(encoding='utf-8', errors='replace')
                        cache_lines = [line.split('Using metadata cache from ', 1)[1].strip().strip(chr(34))
                                       for line in diagnostic.splitlines() if 'Using metadata cache from ' in line]
                        if not cache_lines or any(normalized(Path(path).resolve()) != normalized(cache.resolve())
                                                  for path in cache_lines):
                            raise AssertionError('Observed IFW metadata cache escaped explicit cache path')
                        if not cache.is_dir():
                            raise AssertionError('Explicit metadata cache directory disappeared')
                        print('PASS: explicit metadata cache observed; cache argv and TEMP/TMP preserved in all three processes.')
                        finished = True
                        break
                    if any(row.get('kind', '').startswith('unexpected-') for row in records):
                        raise AssertionError('Fixture reached a forbidden page or target')
                time.sleep(.2)
            else:
                raise TimeoutError('Live GUI language/restart smoke did not finish within 100 seconds')
        except Exception:
            # Only the bounded synthetic fixture diagnostic stream; never host env.
            # The IFW verbose 'Language:' line prints the OS locale, not
            # selected UILanguage. Surface actual controller observations.
            for row in records[-10:]:
                print('LIVE PROBE OBSERVATION:', json.dumps({key: row[key] for key in
                      ('kind', 'language', 'title', 'message', 'nextButton', 'cancelButton') if key in row},
                      ensure_ascii=True), flush=True)
            stream.flush()
            diagnostic = output.read_bytes()[-12000:].decode('utf-8', errors='replace')
            print('SYNTHETIC FIXTURE DIAGNOSTIC TAIL:',
                  diagnostic.encode('ascii', errors='backslashreplace').decode('ascii'), flush=True)
            raise
        finally:
            # The restart helper waits for a fixture to exit (at most 30s), then
            # may start its successor. Reap exact unique fixture paths across
            # that window, never global image names or arbitrary process trees.
            escaped = str(fixture.resolve()).replace("'", "''")
            duration = 2 if finished else 35
            cleanup = "$end=(Get-Date).AddSeconds(" + str(duration) + "); do { " + \
                "$matches=Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -and " + \
                "[String]::Equals([IO.Path]::GetFullPath($_.ExecutablePath), '" + escaped + \
                "', [StringComparison]::OrdinalIgnoreCase) }; " + \
                "$matches | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; " + \
                "Start-Sleep -Milliseconds 250 } while ((Get-Date) -lt $end); " + \
                "$left=Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -and " + \
                "[String]::Equals([IO.Path]::GetFullPath($_.ExecutablePath), '" + escaped + \
                "', [StringComparison]::OrdinalIgnoreCase) }; if ($left) { throw 'Synthetic fixture cleanup left a process running' }"
            subprocess.run([str(powershell), '-NoProfile', '-NonInteractive', '-Command', cleanup],
                           check=True, capture_output=True, timeout=45)
            child.wait(timeout=5)
    if any(target.exists() for target in targets):
        raise AssertionError('Synthetic smoke unexpectedly created an installation target')
