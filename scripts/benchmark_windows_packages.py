# SPDX-License-Identifier: MPL-2.0
"""Observe only task-owned processes on a private, never-activated Windows desktop."""
import argparse
import ctypes as C
from ctypes import wintypes as W
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import time

p = argparse.ArgumentParser()
p.add_argument('--baseline', required=True)
p.add_argument('--candidate', required=True)
p.add_argument('--out', required=True)
p.add_argument('--samples', type=int, default=8)
p.add_argument('--pilot', action='store_true')
p.add_argument('--installed', help='Optional existing installation to hash before/after')
a = p.parse_args()
out = Path(a.out).resolve()
out.mkdir(parents=True, exist_ok=True)
payloads = {'zh3': Path(a.baseline).resolve(), 'zh4': Path(a.candidate).resolve()}
user32 = C.WinDLL('user32', use_last_error=True)
kernel = C.WinDLL('kernel32', use_last_error=True)
psapi = C.WinDLL('psapi', use_last_error=True)

class STARTUPINFO(C.Structure):
    _fields_ = [('cb', W.DWORD), ('lpReserved', W.LPWSTR), ('lpDesktop', W.LPWSTR),
                ('lpTitle', W.LPWSTR), ('dwX', W.DWORD), ('dwY', W.DWORD),
                ('dwXSize', W.DWORD), ('dwYSize', W.DWORD), ('dwXCountChars', W.DWORD),
                ('dwYCountChars', W.DWORD), ('dwFillAttribute', W.DWORD),
                ('dwFlags', W.DWORD), ('wShowWindow', W.WORD), ('cbReserved2', W.WORD),
                ('lpReserved2', C.POINTER(C.c_byte)), ('hStdInput', W.HANDLE),
                ('hStdOutput', W.HANDLE), ('hStdError', W.HANDLE)]

class PROCESSINFO(C.Structure):
    _fields_ = [('hProcess', W.HANDLE), ('hThread', W.HANDLE),
                ('dwProcessId', W.DWORD), ('dwThreadId', W.DWORD)]

class MEMORY(C.Structure):
    _fields_ = [('cb', W.DWORD), ('PageFaultCount', W.DWORD)] + [
        (x, C.c_size_t) for x in ('PeakWorkingSetSize', 'WorkingSetSize', 'QuotaPeakPagedPoolUsage',
        'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage', 'QuotaNonPagedPoolUsage',
        'PagefileUsage', 'PeakPagefileUsage', 'PrivateUsage')]

ENUM = C.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)
user32.CreateDesktopW.argtypes = [W.LPCWSTR, W.LPCWSTR, C.c_void_p, W.DWORD, W.DWORD, C.c_void_p]
user32.CreateDesktopW.restype = W.HANDLE
user32.CloseDesktop.argtypes = [W.HANDLE]
user32.EnumDesktopWindows.argtypes = [W.HANDLE, ENUM, W.LPARAM]
user32.GetWindowThreadProcessId.argtypes = [W.HWND, C.POINTER(W.DWORD)]
user32.IsWindowVisible.argtypes = [W.HWND]
user32.GetWindowTextW.argtypes = [W.HWND, W.LPWSTR, C.c_int]
user32.GetClassNameW.argtypes = [W.HWND, W.LPWSTR, C.c_int]
user32.GetWindowRect.argtypes = [W.HWND, C.POINTER(W.RECT)]
kernel.CreateProcessW.argtypes = [W.LPCWSTR, W.LPWSTR, C.c_void_p, C.c_void_p, W.BOOL,
                                W.DWORD, C.c_void_p, W.LPCWSTR,
                                C.POINTER(STARTUPINFO), C.POINTER(PROCESSINFO)]
kernel.CreateProcessW.restype = W.BOOL
kernel.WaitForSingleObject.argtypes = [W.HANDLE, W.DWORD]
kernel.GetExitCodeProcess.argtypes = [W.HANDLE, C.POINTER(W.DWORD)]
kernel.TerminateProcess.argtypes = [W.HANDLE, W.UINT]
kernel.CloseHandle.argtypes = [W.HANDLE]
psapi.GetProcessMemoryInfo.argtypes = [W.HANDLE, C.POINTER(MEMORY), W.DWORD]

desktop_name = 'PJPerf_' + str(os.getpid())
desktop = user32.CreateDesktopW(desktop_name, None, None, 0, 0x10000000, None)
if not desktop:
    raise C.WinError(C.get_last_error())
# Do not call SwitchDesktop or SetThreadDesktop: the user's desktop stays active.
installed = Path(a.installed) if a.installed else None
guard = {n: hashlib.sha256((installed/n).read_bytes()).hexdigest()
         for n in ('plotjuggler.exe', 'BUILD-INFO.json')} if installed else {}
settings_root = Path(os.environ['APPDATA'])/'PlotJuggler'
settings_guard = {f: hashlib.sha256(f.read_bytes()).digest() for f in settings_root.rglob('*.ini')}
infos = {v: json.loads((r/'BUILD-INFO.json').read_text(encoding='utf-8-sig')) for v,r in payloads.items()}
qt_hashes = {v: {n:hashlib.sha256((r/n).read_bytes()).hexdigest()
                 for n in ('Qt5Core.dll','Qt5Gui.dll','Qt5Widgets.dll','python312.dll','python312.zip')}
             for v,r in payloads.items()}
assert qt_hashes['zh3'] == qt_hashes['zh4'], 'Runtime dependency mismatch would confound comparison'
env = dict(os.environ)
for key in list(env):
    if key.upper() in {'PYTHONHOME','PYTHONPATH','QT_PLUGIN_PATH','QT_QPA_PLATFORM_PLUGIN_PATH',
                       'QML2_IMPORT_PATH','QML_IMPORT_PATH','QT_QPA_PLATFORM'}:
        env.pop(key)
env['QT_QPA_PLATFORM'] = 'windows'
system = Path(os.environ.get('SystemRoot','C:/Windows'))
samples = []

def run(label, mode, number, meme_id, prime=False):
    directory = out/(('prime-' if prime else '')+f'{mode}-{number:02d}-{label}')
    directory.mkdir(exist_ok=True)
    config = directory/'settings/PlotJuggler/io.plotjuggler.PlotJuggler.zh-CN.ini'
    config.parent.mkdir(parents=True, exist_ok=True)
    blocked = ', '.join(str(i) for i in range(106) if i != meme_id)
    config.write_text('[General]\npreviousFunnyMemesList='+blocked+'\n', encoding='utf-8')
    title = 'PJPerf_'+label+'_'+mode+'_'+str(number)
    args = [str(payloads[label]/'plotjuggler.exe'),'--disable_opengl','--language','zh_CN',
            '--self-test-ui',str(directory),'--window_title',title,'--test']
    if mode == 'no-splash':
        args.append('-n')
    task_env = dict(env)
    task_env['PATH'] = str(payloads[label])+os.pathsep+str(system/'System32')+os.pathsep+str(system)
    block = C.create_unicode_buffer('\0'.join(k+'='+v for k,v in sorted(task_env.items()))+'\0\0')
    startup = STARTUPINFO()
    startup.cb = C.sizeof(startup)
    startup.lpDesktop = 'winsta0\\'+desktop_name
    proc = PROCESSINFO()
    command = C.create_unicode_buffer(subprocess.list2cmdline(args))
    first_splash = None
    first_main = None
    windows = []
    peak_before_main = 0
    peak_until_exit = 0
    started = time.perf_counter_ns()
    if not kernel.CreateProcessW(None,command,None,None,False,0x08000400,block,
                                  str(payloads[label]),C.byref(startup),C.byref(proc)):
        raise C.WinError(C.get_last_error())
    @ENUM
    def observe(hwnd, _):
        nonlocal first_splash, first_main
        owner = W.DWORD()
        user32.GetWindowThreadProcessId(hwnd,C.byref(owner))
        if owner.value != proc.dwProcessId or not user32.IsWindowVisible(hwnd):
            return True
        rect = W.RECT()
        user32.GetWindowRect(hwnd,C.byref(rect))
        if rect.right-rect.left < 100 or rect.bottom-rect.top < 100:
            return True
        text = C.create_unicode_buffer(512)
        cls = C.create_unicode_buffer(128)
        user32.GetWindowTextW(hwnd,text,len(text))
        user32.GetClassNameW(hwnd,cls,len(cls))
        ms = (time.perf_counter_ns()-started)/1e6
        if title in text.value and first_main is None:
            first_main = ms
            windows.append({'kind':'main','class':cls.value,'observed_ms':ms})
        elif first_main is None and first_splash is None:
            first_splash = ms
            windows.append({'kind':'splash','class':cls.value,'observed_ms':ms,
                            'width':rect.right-rect.left,'height':rect.bottom-rect.top})
        return True
    try:
        while kernel.WaitForSingleObject(proc.hProcess,0) == 258:
            user32.EnumDesktopWindows(desktop,observe,0)
            memory = MEMORY()
            memory.cb = C.sizeof(memory)
            if psapi.GetProcessMemoryInfo(proc.hProcess,C.byref(memory),C.sizeof(memory)):
                peak_until_exit = max(peak_until_exit,memory.PeakWorkingSetSize)
                if first_main is None:
                    peak_before_main = max(peak_before_main,memory.PeakWorkingSetSize)
            if (time.perf_counter_ns()-started)/1e9 > 35:
                kernel.TerminateProcess(proc.hProcess,98)
                raise TimeoutError(f'Task-owned {label} benchmark process exceeded 35s')
            time.sleep(0.002)
        code = W.DWORD()
        kernel.GetExitCodeProcess(proc.hProcess,C.byref(code))
        report = json.loads((directory/'ui.json').read_text(encoding='utf-8'))
        assert code.value == 0 and first_main is not None and report['language_ok'] and report['data_ok'], (code.value,windows)
        if mode == 'splash':
            assert first_splash is not None, windows
        result = {'version':label,'mode':mode,'sample':number,'meme_id':meme_id,
                  'condition':'unmeasured prime' if prime else 'fresh process after one prime; OS cache not flushed',
                  'first_splash_window_visible_ms':first_splash,
                  'main_window_visible_ms':first_main,
                  'peak_working_set_before_main_bytes':peak_before_main,
                  'peak_working_set_through_acceptance_bytes':peak_until_exit,
                  'numeric_series':report['numeric_series'],'windows':windows,'exit_code':code.value}
        if not prime:
            samples.append(result)
            (out/'samples-partial.json').write_text(json.dumps(samples,indent=2),encoding='utf-8')
        print(json.dumps({k:v for k,v in result.items() if k not in ('windows','condition')},ensure_ascii=True),flush=True)
        return result
    finally:
        kernel.CloseHandle(proc.hThread)
        kernel.CloseHandle(proc.hProcess)

try:
    if a.pilot:
        run('zh4','splash',0,1)
    else:
        for mode in ('no-splash','splash'):
            for label in ('zh3','zh4'):
                run(label,mode,0,1,prime=True)
            for i in range(a.samples):
                # Counterbalance order, rather than running every baseline first.
                for label in (('zh3','zh4') if i%2 == 0 else ('zh4','zh3')):
                    run(label,mode,i,[1,26,52,93][i%4])
finally:
    user32.CloseDesktop(desktop)
assert all(hashlib.sha256((installed/n).read_bytes()).hexdigest()==v for n,v in guard.items())
assert all(hashlib.sha256(f.read_bytes()).digest()==v for f,v in settings_guard.items())
summary = {'protocol':'Win32 first-visible window state on a private desktop; never activated',
           'sources':{v:i['commit'] for v,i in infos.items()},'matching_runtime_hashes':qt_hashes['zh3'],
           'samples':samples,'installation_guard_checked':bool(installed),
           'installed_zh3_unchanged':True if installed else None,'user_settings_unchanged':True,
           'limitations':['2ms polling plus scheduler error; visible state is not photon/presentation timing',
                          'No OS cache flush or reboot; fresh processes and primed file cache',
                          'Splash main-window timing includes intentional 500ms + 3000ms holds',
                          'Through-exit memory includes UI acceptance captures after the 1500ms timer',
                          'Private inactive desktop; no user desktop activation or hardware identity collected']}
(out/'production-summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print('Production benchmark complete; user settings unchanged; installation guard checked='+str(bool(installed)),flush=True)
