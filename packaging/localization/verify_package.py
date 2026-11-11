#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Verify an extracted/installed final package, using only its shipped runtime."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import math
import os
import re
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET

ACCEPTANCE_LANGUAGES = ('zh_CN', 'zh_TW', 'en_US')

FONT_SHA = '2c76254f6fc379fddfce0a7e84fb5385bb135d3e399294f6eeb6680d0365b74b'
LOG_SHA = '28dcbac522ceb75eee10f6af37b0d6e342c1dc79e2be1a9f766fe18a14336766'


def acceptance_environment(environment):
    """Capture Qt logs through pipes without inheriting development runtimes."""
    env = environment.copy()
    for name in ['QT_PLUGIN_PATH', 'QML2_IMPORT_PATH', 'QT_QPA_FONTDIR', 'PYTHONHOME',
                 'PYTHONPATH', 'LD_LIBRARY_PATH']:
        env.pop(name, None)
    env['PJ_DISABLE_TELEMETRY'] = '1'
    env['QT_LOGGING_RULES'] = 'pj.runtime.ingest.info=true'
    # Windows Qt otherwise sends logs to OutputDebugString when no console is
    # attached; subprocess.PIPE alone does not make the BIN import observable.
    env['QT_FORCE_STDERR_LOGGING'] = '1'
    return env


@contextmanager
def acceptance_workspace(work_dir=None):
    """Clean up CI scratch space, but never delete caller-selected evidence."""
    if work_dir is None:
        with tempfile.TemporaryDirectory(prefix='pj4-package-') as temp:
            yield Path(temp).resolve()
        return
    path = Path(work_dir)
    if not path.is_absolute() or '..' in path.parts or path == Path(path.anchor):
        raise ValueError('--work-dir must be an absolute non-root path without parent traversal')
    if any(part.is_symlink() or (hasattr(part, 'is_junction') and part.is_junction())
           for part in (path, *path.parents)):
        raise ValueError('--work-dir must not use symbolic links or junctions')
    if path.exists():
        if not path.is_dir() or any(path.iterdir()):
            raise ValueError('--work-dir must be an empty directory')
    else:
        if not path.parent.is_dir():
            raise ValueError('--work-dir parent must already exist')
        path.mkdir()
    # Deliberately no cleanup, including when the acceptance body raises.
    yield path.resolve()


def application_command(executable, profile, args):
    """Keep every application launch off the real user's settings and caches."""
    assert not any(arg == '--profile-dir' or arg.startswith('--profile-dir=') for arg in args), \
        'Acceptance owns the isolated profile argument'
    return [str(executable), '--profile-dir', str(profile.resolve()), *args]


def windows_system_root(environment):
    """Windows environment keys are case-insensitive before copying to dict."""
    roots = [value for key, value in environment.items() if key.upper() == 'SYSTEMROOT']
    assert len(roots) == 1 and roots[0], 'missing or ambiguous Windows SystemRoot'
    return Path(roots[0])


def plugin_validation_arguments(prefix, expected):
    """Use a stable diagnostic language without changing per-language GUI tests."""
    args = ['--language', 'en_US', '--validate-plugins', str(prefix / 'lib/plotjuggler/plugins')]
    for spec in expected:
        args.extend(['--expect-plugin', spec])
    return args


def optional_ros_error(message):
    """Only the two known no-instance diagnostics belong to the ROS prerequisite."""
    return bool(re.fullmatch(
        r'.*[/\\]libros2_stream_plugin\.so: (?:plugin instance creation failed '
        r'\(create\(\) returned null\)|failed to load data_source plugin)', message))


def validate_plugin_result(returncode, combined, expected, allow_missing_ros):
    """Keep the complete whitelist strict, with one explicit external ROS prerequisite."""
    if returncode == 0:
        assert f'[plugin-validation] OK: loaded all {len(expected)} whitelisted plugin(s)' in combined
        assert '[plugin-validation][error]' not in combined
        return []
    optional = [spec for spec in expected if spec.startswith('ros2-topic-subscriber=')]
    assert allow_missing_ros and returncode == 1 and len(optional) == 1, combined
    assert '[ros2.proxy] ROS 2 not detected; source /opt/ros/<distro>/setup.bash before starting PlotJuggler.' in combined
    missing = re.findall(r'^\[plugin-validation\] expected plugin did not load: (.+)$', combined, re.M)
    assert missing == optional, missing
    errors = re.findall(r'^\[plugin-validation\]\[error\] ([^:]+): (.+)$', combined, re.M)
    assert combined.count('[plugin-validation][error]') == len(errors) == 2 and all(plugin == 'ros2-topic-subscriber' and optional_ros_error(message)
                                    for plugin, message in errors), errors
    loaded = re.findall(r'^\[plugin-validation\]\[info\] ([^:]+): Loaded ', combined, re.M)
    expected_ids = [spec.split('=', 1)[0] for spec in expected if spec != optional[0]]
    assert sorted(loaded) == sorted(expected_ids), loaded
    assert len(loaded) == len(set(loaded)), 'duplicate loaded plugin'
    allowed_summary = {
        '[plugin-validation] expected plugin did not load: ' + optional[0],
        f'[plugin-validation] FAILED: loaded {len(expected) - 1} plugin(s), expected {len(expected)}',
    }
    summaries = [line for line in combined.splitlines() if line.startswith('[plugin-validation] ')]
    assert len(summaries) == 2 and set(summaries) == allowed_summary, summaries
    return [{'id': 'ros2-topic-subscriber', 'version': optional[0].split('=', 1)[1],
             'status': 'not_tested_missing_external_dependency',
             'reason': 'ROS 2 is not installed in the clean acceptance image'}]


def validate_bin_plot_state(state):
    """Require real attached, visible samples, not merely an import message."""
    assert state['version'] == 1, 'unsupported plot snapshot schema'
    plots = [plot for plot in state['plots'] if plot['id'] == 'p1']
    assert len(plots) == 1, 'the expected BIN plot was not restored exactly once'
    plot = plots[0]
    curves = [curve for curve in plot['curves']
              if curve.get('topic') == '/RCOU' and curve.get('field') == 'C1\t[us]']
    assert len(curves) == len(plot['curves']) == 1, 'the exact BIN curve is not attached'
    curve = curves[0]
    assert curve['visible'] is True, 'the BIN curve is hidden'
    assert curve['sample_count'] == curve['finite_sample_count'] >= 100, 'missing real finite BIN samples'
    assert curve['finite_samples_in_view'] >= 100, 'the restored viewport does not show the BIN waveform'
    view, data = plot['viewport'], curve['sample_bounds']
    for bounds in [view, data]:
        assert all(isinstance(bounds[key], (int, float)) and math.isfinite(bounds[key])
                   for key in ['x_min', 'x_max', 'y_min', 'y_max']), bounds
        assert bounds['x_min'] < bounds['x_max'] and bounds['y_min'] < bounds['y_max'], bounds
    # The pinned real log's servo waveform spans about 53 s and 1000..1440 us.
    # Use broad physical bounds rather than pixel-dependent axis padding.
    assert 40 < data['x_max'] - data['x_min'] < 70, data
    assert 900 <= data['y_min'] <= 1050 and 1300 <= data['y_max'] <= 1600, data
    assert view['x_min'] <= data['x_min'] < data['x_max'] <= view['x_max'], (view, data)
    assert view['y_min'] <= data['y_min'] < data['y_max'] <= view['y_max'], (view, data)


def write_bin_layout(work, log):
    """Use the same Unicode-path real-data fixture in native and package checks."""
    shutil.copy2(log, work / '飞行日志.BIN')
    layout = work / '真实日志.pj4.xml'
    layout.write_text('''<root format="PlotJuggler" pj4_version="4" binding="source">
<tabbed_widget parent="main_window"><Tab id="t1" tab_name="BIN" containers="1">
<Container><DockArea id="a1" name="BIN"><plot id="p1" mode="TimeSeries">
<curve topic="/RCOU" field="C1&#9;[us]"/></plot></DockArea></Container></Tab></tabbed_widget>
<previouslyLoaded_Datafiles><fileInfo filename="飞行日志.BIN"><plugin ID="ArduPilot BIN"
manifest_id="ardupilot-dataflash" filepath_mode="source"><![CDATA[{}]]></plugin></fileInfo>
</previouslyLoaded_Datafiles></root>''', encoding='utf-8')
    return layout


def write_csv_layout(work, unicode_path):
    """Generate every byte; no user log or externally sourced fixture is used."""
    directory = work / ('csv-测试' if unicode_path else 'csv-ascii')
    directory.mkdir()
    source = directory / ('合成.csv' if unicode_path else 'synthetic.csv')
    source.write_bytes(b'sample_index,synthetic_signal\n0,-2\n1,3.5\n2,0\n')
    root = ET.Element('root', format='PlotJuggler', pj4_version='4', binding='source')
    widget = ET.SubElement(root, 'tabbed_widget', parent='main_window')
    tab = ET.SubElement(widget, 'Tab', id='csv-tab', tab_name='CSV', containers='1')
    area = ET.SubElement(ET.SubElement(tab, 'Container'), 'DockArea', id='csv-area', name='CSV')
    plot = ET.SubElement(area, 'plot', id='csv-plot', mode='TimeSeries')
    for field in ['sample_index', 'synthetic_signal']:
        ET.SubElement(plot, 'curve', topic=source.stem, field=field)
    file_info = ET.SubElement(ET.SubElement(root, 'previouslyLoaded_Datafiles'),
                              'fileInfo', filename=str(source.resolve()))
    plugin = ET.SubElement(file_info, 'plugin', ID='CSV Loader', manifest_id='csv-loader', filepath_mode='source')
    plugin.text = json.dumps({'filepath': str(source.resolve()), 'delimiter': ',',
                              'detect_delimiter': False, 'time_mode': 'row_number'})
    layout = directory / 'layout.pj4.xml'
    ET.ElementTree(root).write(layout, encoding='utf-8', xml_declaration=True)
    return layout, source.stem


def validate_csv_plot_state(state, topic):
    """Require the actual CSV adapters, samples and visible synthetic bounds."""
    assert state['version'] == 1, 'unsupported plot snapshot schema'
    plots = [plot for plot in state['plots'] if plot['id'] == 'csv-plot']
    assert len(plots) == 1, 'CSV plot missing or duplicated'
    plot = plots[0]
    expected = {'sample_index': (0.0, 2.0), 'synthetic_signal': (-2.0, 3.5)}
    assert len(plot['curves']) == len(expected), 'CSV curves missing or duplicated'
    assert {curve['field'] for curve in plot['curves']} == set(expected)
    for curve in plot['curves']:
        assert curve['topic'] == topic and curve['visible'] is True
        assert curve['sample_count'] == curve['finite_sample_count'] == curve['finite_samples_in_view'] == 3
        data, view = curve['sample_bounds'], plot['viewport']
        for bounds in [data, view]:
            assert all(type(bounds[key]) in (int, float) and math.isfinite(bounds[key])
                       for key in ['x_min', 'x_max', 'y_min', 'y_max'])
        assert math.isclose(data['x_min'], 0.0, abs_tol=1e-9)
        assert math.isclose(data['x_max'], 2.0, abs_tol=1e-9)
        low, high = expected[curve['field']]
        assert math.isclose(data['y_min'], low, abs_tol=1e-9)
        assert math.isclose(data['y_max'], high, abs_tol=1e-9)
        assert view['x_min'] <= data['x_min'] < data['x_max'] <= view['x_max']
        assert view['y_min'] <= data['y_min'] < data['y_max'] <= view['y_max']


def checked_rectangle(value):
    """Use physical, half-open pixel bounds, including negative monitor origins."""
    if (len(value) != 4 or any(type(part) is not int for part in value) or
            value[2] <= value[0] or value[3] <= value[1]):
        raise ValueError('invalid capture rectangle')
    return tuple(value)


def rectangle_contains(outer, inner):
    outer, inner = checked_rectangle(outer), checked_rectangle(inner)
    return outer[0] <= inner[0] < inner[2] <= outer[2] and outer[1] <= inner[1] < inner[3] <= outer[3]


def rectangles_overlap(first, second):
    first, second = checked_rectangle(first), checked_rectangle(second)
    return max(first[0], second[0]) < min(first[2], second[2]) and max(first[1], second[1]) < min(first[3], second[3])


def capture_target(window, work_area, minimum, resize):
    """Fit a real window, never below its platform-reported minimum size."""
    window, work_area = checked_rectangle(window), checked_rectangle(work_area)
    if len(minimum) != 2 or any(type(part) is not int or part <= 0 for part in minimum):
        raise ValueError('invalid capture minimum size')
    width, height = window[2] - window[0], window[3] - window[1]
    required = minimum if resize else (max(width, minimum[0]), max(height, minimum[1]))
    available = (work_area[2] - work_area[0], work_area[3] - work_area[1])
    if any(need > have for need, have in zip(required, available)):
        raise ValueError('available work area cannot contain the complete minimum-size window')
    margin = 8 if all(need + 16 <= have for need, have in zip(required, available)) else 0
    if resize:
        width, height = min(width, available[0] - 2 * margin), min(height, available[1] - 2 * margin)
    if width < minimum[0] or height < minimum[1]:
        raise ValueError('capture would shrink content below the window minimum')
    return (work_area[0] + margin, work_area[1] + margin,
            work_area[0] + margin + width, work_area[1] + margin + height)


def validate_capture_geometry(snapshot):
    """A desktop-sized image is insufficient unless the complete window fits."""
    if not rectangle_contains(snapshot['desktop'], snapshot['work_area']):
        raise ValueError('capture work area leaves the desktop')
    if not rectangle_contains(snapshot['work_area'], snapshot['frame']):
        raise ValueError('complete GUI frame is not inside the available work area')
    if snapshot.get('occluded'):
        raise ValueError('another visible window overlaps the packaged GUI')


def png_size(path):
    """Read only the original PNG dimensions; never crop or resample evidence."""
    import struct
    with Path(path).open('rb') as stream:
        header = stream.read(24)
    if len(header) != 24 or header[:8] != b'\x89PNG\r\n\x1a\n' or header[8:16] != b'\x00\x00\x00\rIHDR':
        raise ValueError('capture did not produce a PNG')
    return struct.unpack('>II', header[16:24])


def validate_capture_result(before, after, png):
    """Bind unchanged platform geometry to an unscaled full-desktop capture."""
    validate_capture_geometry(before)
    validate_capture_geometry(after)
    if before != after:
        raise ValueError('GUI identity or geometry changed during capture')
    desktop = before['desktop']
    if png_size(png) != (desktop[2] - desktop[0], desktop[3] - desktop[1]):
        raise ValueError('PNG dimensions do not match the measured desktop')
    if png.stat().st_size <= 10000:
        raise ValueError('empty GUI screenshot')



def windows_capture_main_window(windows, pid):
    """Select this release's standard main-window contract, including hidden candidates.

    Empty acceptance profiles use native chrome. A hidden main window must not
    be replaced by a visible dialog merely because both share the same PID.
    """
    selected = [window for window in windows if window['pid'] == pid and not window['owner'] and
                window['style'] & 0x00CF0000 == 0x00CF0000 and not window['style'] & 0xC0000000 and
                not window['extended_style'] & 0x81]
    # WS_OVERLAPPEDWINDOW requires caption/system menu/resize/min/max; reject
    # CHILD, POPUP, TOOLWINDOW and DLGMODALFRAME rather than matching a title.
    if len(selected) != 1:
        raise ValueError('expected one standard main window owned by the launched process')
    window = selected[0]
    if not window['visible'] or not window['enabled']:
        raise ValueError('packaged main window is hidden or disabled')
    return window['window_id']


def capture_windows_gui(process, executable, png):
    """Arrange only the launched process's main window using physical Win32 pixels."""
    import ctypes as ct
    from ctypes import wintypes as wt
    from PIL import ImageGrab

    user = ct.WinDLL('user32', use_last_error=True)
    kernel = ct.WinDLL('kernel32', use_last_error=True)
    dwm = ct.WinDLL('dwmapi', use_last_error=True)
    callback_type = ct.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    signatures = {
        'EnumWindows': ([callback_type, wt.LPARAM], wt.BOOL),
        'GetWindowThreadProcessId': ([wt.HWND, ct.POINTER(wt.DWORD)], wt.DWORD),
        'IsWindowVisible': ([wt.HWND], wt.BOOL), 'IsWindowEnabled': ([wt.HWND], wt.BOOL),
        'IsIconic': ([wt.HWND], wt.BOOL), 'GetWindow': ([wt.HWND, wt.UINT], wt.HWND),
        'GetWindowLongW': ([wt.HWND, ct.c_int], wt.LONG),
        'GetWindowRect': ([wt.HWND, ct.POINTER(wt.RECT)], wt.BOOL),
        'GetForegroundWindow': ([], wt.HWND), 'GetTopWindow': ([wt.HWND], wt.HWND),
        'GetSystemMetrics': ([ct.c_int], ct.c_int), 'GetDpiForWindow': ([wt.HWND], wt.UINT),
        'SetThreadDpiAwarenessContext': ([wt.HANDLE], wt.HANDLE),
        'MonitorFromWindow': ([wt.HWND, wt.DWORD], wt.HMONITOR),
        'GetMonitorInfoW': ([wt.HMONITOR, ct.c_void_p], wt.BOOL),
        'ShowWindow': ([wt.HWND, ct.c_int], wt.BOOL),
        'SetWindowPos': ([wt.HWND, wt.HWND, ct.c_int, ct.c_int, ct.c_int, ct.c_int, wt.UINT], wt.BOOL),
        'SetForegroundWindow': ([wt.HWND], wt.BOOL),
        'SendMessageTimeoutW': ([wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM, wt.UINT, wt.UINT,
                                ct.POINTER(ct.c_size_t)], ct.c_ssize_t),
    }
    for name, (arguments, result) in signatures.items():
        function = getattr(user, name); function.argtypes = arguments; function.restype = result
    kernel.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]; kernel.OpenProcess.restype = wt.HANDLE
    kernel.CloseHandle.argtypes = [wt.HANDLE]; kernel.CloseHandle.restype = wt.BOOL
    kernel.QueryFullProcessImageNameW.argtypes = [wt.HANDLE, wt.DWORD, wt.LPWSTR, ct.POINTER(wt.DWORD)]
    kernel.QueryFullProcessImageNameW.restype = wt.BOOL
    dwm.DwmGetWindowAttribute.argtypes = [wt.HWND, wt.DWORD, ct.c_void_p, wt.DWORD]
    dwm.DwmGetWindowAttribute.restype = wt.LONG

    class MonitorInfo(ct.Structure):
        _fields_ = [('size', wt.DWORD), ('monitor', wt.RECT), ('work', wt.RECT), ('flags', wt.DWORD)]

    class MinMaxInfo(ct.Structure):
        _fields_ = [('reserved', wt.POINT), ('maximum', wt.POINT), ('position', wt.POINT),
                    ('minimum_track', wt.POINT), ('maximum_track', wt.POINT)]

    def rect(value):
        return checked_rectangle((value.left, value.top, value.right, value.bottom))

    def visible_frame(hwnd):
        cloaked = wt.DWORD()
        if dwm.DwmGetWindowAttribute(hwnd, 14, ct.byref(cloaked), ct.sizeof(cloaked)) != 0:
            raise ValueError('cannot establish Windows window visibility')
        if cloaked.value or not user.IsWindowVisible(hwnd) or user.IsIconic(hwnd):
            return None
        value = wt.RECT()
        if dwm.DwmGetWindowAttribute(hwnd, 9, ct.byref(value), ct.sizeof(value)) != 0:
            raise ValueError('cannot measure the visible Windows frame')
        return rect(value)

    def selected_window():
        handles = []
        callback = callback_type(lambda hwnd, _: handles.append(hwnd) or True)
        if not user.EnumWindows(callback, 0):
            raise ValueError('cannot enumerate Windows GUI windows')
        windows = []
        for hwnd in handles:
            pid = wt.DWORD()
            user.GetWindowThreadProcessId(hwnd, ct.byref(pid))
            if pid.value == process.pid:
                windows.append({'window_id': hwnd, 'pid': pid.value, 'owner': user.GetWindow(hwnd, 4),
                                'style': user.GetWindowLongW(hwnd, -16),
                                'extended_style': user.GetWindowLongW(hwnd, -20),
                                'visible': bool(user.IsWindowVisible(hwnd)), 'enabled': bool(user.IsWindowEnabled(hwnd))})
        return windows_capture_main_window(windows, process.pid)

    def snapshot(hwnd, require_front=False):
        if process.poll() is not None or selected_window() != hwnd:
            raise ValueError('packaged GUI process/window identity changed')
        frame = visible_frame(hwnd)
        if frame is None:
            raise ValueError('packaged GUI is hidden or minimized')
        outer = wt.RECT()
        if not user.GetWindowRect(hwnd, ct.byref(outer)):
            raise ValueError('cannot measure Windows window bounds')
        monitor = MonitorInfo(); monitor.size = ct.sizeof(monitor)
        if not user.GetMonitorInfoW(user.MonitorFromWindow(hwnd, 2), ct.byref(monitor)):
            raise ValueError('cannot measure the Windows work area')
        limits = MinMaxInfo()
        limits.minimum_track = wt.POINT(user.GetSystemMetrics(34), user.GetSystemMetrics(35))
        result = ct.c_size_t()
        if not user.SendMessageTimeoutW(hwnd, 0x24, 0, ct.addressof(limits), 2, 2000, ct.byref(result)):
            raise ValueError('cannot query the actual GUI minimum size')
        minimum = (limits.minimum_track.x, limits.minimum_track.y)
        outer = rect(outer)
        if any(part <= 0 for part in minimum) or outer[2]-outer[0] < minimum[0] or outer[3]-outer[1] < minimum[1]:
            raise ValueError('GUI content minimum exceeds the actual window bounds')
        desktop = (user.GetSystemMetrics(76), user.GetSystemMetrics(77))
        desktop += (desktop[0]+user.GetSystemMetrics(78), desktop[1]+user.GetSystemMetrics(79))
        occluded = False
        if require_front:
            if user.GetForegroundWindow() != hwnd:
                raise ValueError('packaged GUI is not the foreground window')
            current, seen = user.GetTopWindow(None), set()
            while current and current != hwnd:
                if current in seen:
                    raise ValueError('Windows stacking order changed during capture')
                seen.add(current)
                if user.IsWindowVisible(current) and not user.IsIconic(current):
                    other = visible_frame(current)
                    occluded |= other is not None and rectangles_overlap(frame, other)
                current = user.GetWindow(current, 2)
            if current != hwnd:
                raise ValueError('packaged GUI disappeared from Windows stacking order')
        return {'backend': 'win32', 'window_id': int(hwnd), 'pid': process.pid, 'frame': frame,
                'outer': outer, 'minimum_size': minimum, 'work_area': rect(monitor.work),
                'desktop': checked_rectangle(desktop), 'dpi': user.GetDpiForWindow(hwnd), 'occluded': occluded}

    context = user.SetThreadDpiAwarenessContext(ct.c_void_p(-4))
    if not context:
        raise ValueError('physical per-monitor DPI coordinates are unavailable')
    try:
        handle = kernel.OpenProcess(0x1000, False, process.pid)
        if not handle:
            raise ValueError('cannot verify the launched Windows image')
        try:
            size = wt.DWORD(32768); path = ct.create_unicode_buffer(size.value)
            if not kernel.QueryFullProcessImageNameW(handle, 0, path, ct.byref(size)) or not os.path.samefile(path.value, executable):
                raise ValueError('Windows GUI image differs from the accepted executable')
        finally:
            kernel.CloseHandle(handle)
        hwnd = selected_window()
        user.ShowWindow(hwnd, 9)
        before = snapshot(hwnd)
        target = capture_target(before['outer'], before['work_area'], before['minimum_size'], resize=True)
        if not user.SetWindowPos(hwnd, None, target[0], target[1], target[2]-target[0], target[3]-target[1], 0x40):
            raise ValueError('cannot arrange the actual Windows GUI')
        if user.GetForegroundWindow() != hwnd and not user.SetForegroundWindow(hwnd):
            raise ValueError('cannot bring the packaged GUI to the foreground')
        time.sleep(1)
        ready = snapshot(hwnd, require_front=True)
        validate_capture_geometry(ready)
        ImageGrab.grab(include_layered_windows=True, all_screens=True).save(png)
        after = snapshot(hwnd, require_front=True)
        validate_capture_result(ready, after, png)
        return ready
    finally:
        user.SetThreadDpiAwarenessContext(context)


def linux_capture_processes(session_pid, profile, binary, proc_root=Path('/proc'), getsid=None):
    """Admit AppImage descendants only in this launch session with exact profile/image bytes."""
    getsid = getsid or os.getsid
    expected_hash = hashlib.sha256(binary.read_bytes()).hexdigest()
    expected_profile = os.fsencode(str(profile.resolve()))
    result = {}
    for entry in proc_root.iterdir():
        if not entry.name.isdecimal():
            continue
        pid = int(entry.name)
        try:
            if getsid(pid) != session_pid:
                continue
            args = (entry / 'cmdline').read_bytes().split(b'\0')
            indices = [index for index, value in enumerate(args) if value == b'--profile-dir']
            if len(indices) != 1 or indices[0] + 1 >= len(args) or args[indices[0]+1] != expected_profile:
                continue
            start = (entry / 'stat').read_text(encoding='utf-8').rsplit(')', 1)[1].split()[19]
            actual_hash = hashlib.sha256((entry / 'exe').read_bytes()).hexdigest()
            if actual_hash != expected_hash:
                # AppImage/AppRun wrappers retain the same arguments but do not
                # own the application window. They are not GUI candidates.
                continue
            result[pid] = {'start_ticks': int(start), 'image_sha256': actual_hash}
        except (FileNotFoundError, ProcessLookupError):
            continue
    if not result:
        raise ValueError('no exact packaged GUI process in the isolated launch session')
    return result


def x11_capture_tools():
    """Capture requires the declared X11 helpers, never a title-only fallback."""
    tools = {name: shutil.which(name) for name in ('xdotool', 'xprop', 'xwininfo', 'import')}
    if not all(tools.values()):
        raise ValueError('GUI capture requires xdotool, xprop, xwininfo and ImageMagick import')
    return tools


def x11_call(tools, name, *args, empty_ok=False):
    result = subprocess.run([tools[name], *map(str, args)], capture_output=True, text=True,
                            encoding='utf-8', errors='replace', timeout=15, env=dict(os.environ, LC_ALL='C'))
    if empty_ok and result.returncode == 1 and not result.stdout.strip() and not result.stderr.strip():
        return ''
    if result.returncode != 0:
        raise ValueError('required X11 capture helper failed: ' + name)
    return result.stdout


def x11_window_geometry(text):
    """Parse measured X11 client bounds, including its real border pixels."""
    def number(label):
        found = re.findall(r'^\s*' + re.escape(label) + r':\s*(-?\d+)\s*$', text, re.M)
        if len(found) != 1:
            raise ValueError('ambiguous X11 geometry')
        return int(found[0])
    x, y = number('Absolute upper-left X'), number('Absolute upper-left Y')
    width, height, border = number('Width'), number('Height'), number('Border width')
    if border < 0 or width <= 0 or height <= 0:
        raise ValueError('invalid X11 client size')
    states = re.findall(r'^\s*Map State:\s*(\w+)\s*$', text, re.M)
    classes = re.findall(r'^\s*Class:\s*(\w+)\s*$', text, re.M)
    if (len(states) != 1 or states[0] not in {'IsViewable', 'IsUnMapped', 'IsUnviewable'} or
            len(classes) != 1 or classes[0] not in {'InputOutput', 'InputOnly'}):
        raise ValueError('unknown X11 visibility or window class')
    return {'frame': checked_rectangle((x-border, y-border, x+width+border, y+height+border)),
            'visible': states[0] == 'IsViewable', 'input_output': classes[0] == 'InputOutput', 'border': border}


def linux_capture_snapshot(process, profile, binary, tools):
    """Support only the dedicated, un-managed Xvfb display used by clean acceptance."""
    if process.poll() is not None:
        raise ValueError('packaged GUI launcher exited early')
    wm = x11_call(tools, 'xprop', '-root', '_NET_SUPPORTING_WM_CHECK')
    if re.search(r'window id #|=\s*0x[0-9a-f]+', wm, re.I):
        raise ValueError('Linux package capture requires a dedicated X11 display without a window manager')
    if '_NET_SUPPORTING_WM_CHECK:' not in wm or not re.search(r'not found|no such atom', wm):
        raise ValueError('cannot prove the X11 display is unmanaged')
    root = x11_window_geometry(x11_call(tools, 'xwininfo', '-root', '-stats'))
    identities = linux_capture_processes(process.pid, profile, binary)
    candidates = []
    for pid in identities:
        windows = x11_call(tools, 'xdotool', 'search', '--onlyvisible', '--pid', pid, empty_ok=True)
        for raw in windows.split():
            if not raw.isdecimal():
                raise ValueError('invalid X11 window identity')
            window = int(raw)
            properties = x11_call(tools, 'xprop', '-notype', '-id', hex(window),
                                  '_NET_WM_PID', '_NET_WM_WINDOW_TYPE', 'WM_TRANSIENT_FOR')
            match = re.search(r'^_NET_WM_PID = (\d+)\s*$', properties, re.M)
            if not match or int(match[1]) != pid:
                raise ValueError('X11 window PID differs from its isolated GUI process')
            if re.search(r'^_NET_WM_WINDOW_TYPE = _NET_WM_WINDOW_TYPE_NORMAL\s*$', properties, re.M):
                if not re.search(r'^WM_TRANSIENT_FOR:\s*(?:not found|no such atom)', properties, re.M):
                    raise ValueError('normal GUI window has an unexpected transient owner')
                candidates.append((window, pid))
    if len(candidates) != 1:
        raise ValueError('expected exactly one normal main window in the isolated GUI session')
    window, pid = candidates[0]
    geometry = x11_window_geometry(x11_call(tools, 'xwininfo', '-id', hex(window), '-stats'))
    if not geometry['visible'] or not geometry['input_output']:
        raise ValueError('packaged X11 GUI is not viewable')
    children_text = x11_call(tools, 'xwininfo', '-root', '-children')
    children = [int(value, 16) for value in re.findall(r'^\s+(0x[0-9a-fA-F]+)\s', children_text, re.M)]
    if children.count(window) != 1:
        raise ValueError('packaged GUI is not an unambiguous root child')
    occluded = False
    for child in children:
        if child != window:
            other = x11_window_geometry(x11_call(tools, 'xwininfo', '-id', hex(child), '-stats'))
            occluded |= other['visible'] and other['input_output'] and rectangles_overlap(geometry['frame'], other['frame'])
    return {'backend': 'x11-unmanaged', 'window_id': window, 'pid': pid, 'launcher_pid': process.pid,
            'process_identity': identities[pid], 'frame': geometry['frame'], 'border': geometry['border'],
            'work_area': root['frame'], 'desktop': root['frame'], 'occluded': occluded}


def capture_linux_gui(process, prefix, profile, png):
    """Move the original-sized real GUI on Xvfb; never shrink its widget contents."""
    tools = x11_capture_tools()
    binary = prefix / 'bin/plotjuggler4'
    before = linux_capture_snapshot(process, profile, binary, tools)
    frame = before['frame']
    target = capture_target(frame, before['work_area'], (frame[2]-frame[0], frame[3]-frame[1]), resize=False)
    window = str(before['window_id'])
    x11_call(tools, 'xdotool', 'windowmove', window, target[0], target[1])
    x11_call(tools, 'xdotool', 'windowraise', window)
    x11_call(tools, 'xdotool', 'windowfocus', window)
    time.sleep(1)
    ready = linux_capture_snapshot(process, profile, binary, tools)
    if (ready['window_id'], ready['pid'], ready['process_identity']) != (before['window_id'], before['pid'], before['process_identity']):
        raise ValueError('packaged X11 GUI identity changed during arrangement')
    if (ready['frame'][2]-ready['frame'][0], ready['frame'][3]-ready['frame'][1]) != (frame[2]-frame[0], frame[3]-frame[1]):
        raise ValueError('X11 capture unexpectedly resized the real GUI')
    validate_capture_geometry(ready)
    focus = x11_call(tools, 'xdotool', 'getwindowfocus').strip()
    if not focus.isdecimal() or int(focus) != ready['window_id']:
        raise ValueError('packaged X11 GUI does not have input focus')
    x11_call(tools, 'import', '-window', 'root', png)
    after = linux_capture_snapshot(process, profile, binary, tools)
    validate_capture_result(ready, after, png)
    return ready


def capture_gui(process, prefix, executable, profile, png):
    """Keep original pixels plus explicit geometry, bound to this launch and PNG."""
    snapshot = (capture_windows_gui(process, executable, png) if os.name == 'nt' else
                capture_linux_gui(process, prefix, profile, png))
    record = dict(snapshot, schema=1, screenshot=png.name, sha256=hashlib.sha256(png.read_bytes()).hexdigest(),
                  capture='unscaled-full-desktop', complete_window_visible=True)
    png.with_suffix('.geometry.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    return record


def verify(prefix, executable, log, output, expected_source, expected_version, capture=False, work_dir=None):
    """Check provenance, plugins, Python and synthetic CSV/real BIN restoration."""
    from host_versions import read_host_versions
    host = read_host_versions(Path(__file__).resolve().parents[2])
    prefix, executable, output = prefix.resolve(), executable.resolve(), output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    record = json.loads((prefix / 'share/plotjuggler4/release.json').read_text(encoding='utf-8'))
    assert record['source_commit'] == expected_source, 'package source differs from candidate run'
    assert record['version'] == expected_version, 'package version differs from source version'
    assert record['qt_version'] == host['qt_version'], 'package Qt differs from source pin'
    assert record['sdk_version'] == host['sdk_version'], 'package host SDK differs from source pin'
    sdk_source = json.loads((Path(__file__).resolve().parents[2] / 'cmake/host-sdk-source.json').read_text(encoding='utf-8'))
    assert record.get('host_sdk_source') == sdk_source, 'package SDK snapshot provenance differs'
    assert json.loads((prefix / 'share/licenses/host-sdk-source.json').read_text(encoding='utf-8')) == sdk_source, 'SDK license provenance differs'
    font = prefix / 'bin/fonts/NotoSansCJKsc-Regular.otf'
    assert hashlib.sha256(font.read_bytes()).hexdigest() == FONT_SHA
    for name in ['ardupilot-dataflash/LICENSE', 'ardupilot-dataflash/COPYING.GPL3',
                 'ardupilot-dataflash/LICENSE.APACHE2', 'ardupilot-dataflash/UPSTREAM.md',
                 'NotoSansCJK-OFL.txt', 'PlotJuggler-MPL-2.0.txt', 'Qt-LGPL.txt', 'DEPENDENCIES.json',
                 f'Qt-{host["qt_version"]}/HPND-sell-variant.txt',
                 'ardupilot-dataflash/dependencies/fmt-12.1.0-LICENSE.txt',
                 'ardupilot-dataflash/dependencies/fast-float-8.1.0-LICENSE.txt',
                 'ardupilot-dataflash/dependencies/nlohmann-json-3.12.0-LICENSE.txt',
                 'ardupilot-dataflash/dependencies/plotjuggler-sdk-NOTICE.txt']:
        assert (prefix / 'share/licenses' / name).is_file(), name
    notices = json.loads((prefix / 'share/licenses/DEPENDENCIES.json').read_text(encoding='utf-8'))
    for item in notices['files']:
        assert hashlib.sha256((prefix / 'share/licenses' / item['path']).read_bytes()).hexdigest() == item['sha256']
    assert hashlib.sha256(log.read_bytes()).hexdigest() == LOG_SHA, 'unexpected real BIN fixture'
    rebuilt = record.get('localized_plugin_rebuilds', [])
    required_rebuilt = {'protobuf-parser', 'toolbox-transform-editor', 'webrtc-client', 'mcap-loader', 'csv-loader'}
    if os.name != 'nt':
        required_rebuilt.add('toolbox-assistant-agent')
    assert {item['id'] for item in rebuilt} == required_rebuilt, 'missing localized plugin provenance'
    for item in rebuilt:
        assert item['kind'] == 'fork-localized-rebuild-not-upstream-binary'
        actual_files = {p.relative_to(prefix).as_posix() for p in
                        (prefix / 'lib/plotjuggler/plugins' / item['id']).rglob('*') if p.is_file()}
        assert actual_files == {f['path'] for f in item['files']}, 'unexpected upstream/rebuilt plugin mixture'
        for entry in item['files']:
            assert hashlib.sha256((prefix / entry['path']).read_bytes()).hexdigest() == entry['sha256'], entry['path']

        for entry in item['license_files']:
            assert hashlib.sha256((prefix / entry['path']).read_bytes()).hexdigest() == entry['sha256'], entry['path']
    originals = record['preserved_upstream_plugins']
    assert len(originals) == 1 and originals[0]['id'] == 'toolbox-mosaico'
    assert originals[0]['kind'] == 'unmodified-upstream-binary'
    original_files = {p.relative_to(prefix).as_posix() for p in
                      (prefix / 'lib/plotjuggler/plugins/toolbox-mosaico').rglob('*') if p.is_file()}
    assert original_files == {entry['path'] for entry in originals[0]['files']}
    for entry in originals[0]['files']:
        assert hashlib.sha256((prefix / entry['path']).read_bytes()).hexdigest() == entry['sha256'], entry['path']
    manifests = sorted((prefix / 'lib/plotjuggler/plugins').glob('*/manifest.json'))
    plugin_records = [json.loads(p.read_text(encoding='utf-8')) for p in manifests]
    bin_manifest = next(m for m in plugin_records if m['id'] == 'ardupilot-dataflash')
    assert bin_manifest['license'] == record['bin_plugin_license'] == 'LGPL-3.0-only'
    expected = [f"{m['id']}={m['version']}" for m in plugin_records]
    assert f"ardupilot-dataflash={record['bin_plugin_version']}" in expected
    assert sorted(expected) == sorted(record['expected_plugins']), expected
    assert len(expected) == (19 if os.name == 'nt' else 21), expected
    env = acceptance_environment(os.environ)
    # Use the installed DLLs plus the operating system, never a Qt/Conan tree.
    if os.name == 'nt':
        system = windows_system_root(env)
        env['PATH'] = os.pathsep.join(map(str, [prefix / 'bin', system / 'System32', system]))
        for name in ['vcruntime140.dll', 'vcruntime140_1.dll', 'msvcp140.dll']:
            assert (prefix / 'bin' / name).is_file(), f'missing app-local VC runtime: {name}'
    def stop(process):
        # AppImage extract-and-run forks AppRun. Stop the whole isolated session
        # so a previous-language window cannot survive into the next capture.
        if os.name == 'nt':
            if process.poll() is None:
                process.terminate()
        else:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        try:
            process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            if os.name == 'nt':
                process.kill()
            else:
                os.killpg(process.pid, signal.SIGKILL)
            process.wait()
    def run(name, args, validate_plugins=False):
        process = subprocess.Popen(application_command(executable, work / 'profiles' / name, args), env=env, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace',
                                   start_new_session=os.name != 'nt')
        try:
            stdout, stderr = process.communicate(timeout=150)
        except subprocess.TimeoutExpired:
            stop(process)
            raise
        combined = stdout + stderr
        (output / f'{name}.log').write_text(combined, encoding='utf-8')
        print(combined)
        if validate_plugins:
            unavailable.extend(validate_plugin_result(process.returncode, combined, expected, os.name != 'nt'))
        else:
            assert process.returncode == 0, f'{name}: exit {process.returncode}'
        assert 'Failed to load bundled CJK fallback font' not in combined
        return combined
    with acceptance_workspace(work_dir) as work:
        env.update(HOME=str(work), XDG_CONFIG_HOME=str(work / 'config'),
                   XDG_DATA_HOME=str(work / 'data'), XDG_CACHE_HOME=str(work / 'cache'))
        version_text = run('version', ['--version'])
        assert any(line.strip() == 'PlotJuggler4 ' + expected_version for line in version_text.splitlines()), version_text
        assert '[selftest-python] OK' in run('python', ['--selftest-python'])
        args = plugin_validation_arguments(prefix, expected)
        unavailable = []
        run('plugins', args, validate_plugins=True)
        csv_cases = [(name, *write_csv_layout(work, unicode_path))
                     for name, unicode_path in [('ascii', False), ('unicode', True)]]
        for language in ACCEPTANCE_LANGUAGES:
            for name, csv_layout, topic in csv_cases:
                case = f'csv-{name}-{language}'
                diagnostics = output / f'{case}-diagnostics.json'
                plot_state = output / f'{case}-plot-state.json'
                text = run(case, ['--language', language, '--nosplash', '--layout', str(csv_layout),
                                 '--exit-after-layout', '--exit-after-layout-timeout', '90',
                                 '--dump-diagnostics', str(diagnostics), '--dump-plot-state', str(plot_state)])
                assert '[exit-after-layout] layout restore settled: success' in text
                validate_csv_plot_state(json.loads(plot_state.read_text(encoding='utf-8')), topic)
                records = json.loads(diagnostics.read_text(encoding='utf-8'))['records']
                rejected = [x for x in records if
                            (x['level'] in ['warning', 'error'] and not
                             (unavailable and x['id'] == 'ros2-topic-subscriber' and optional_ros_error(x['message']))) or
                            x['id'] in ['layout-import-unresolved-curves', 'layout-import-unresolved-curves-sync']]
                assert not rejected, rejected
        layout = write_bin_layout(work, log)
        captures = []
        for language in ACCEPTANCE_LANGUAGES:
            diagnostics = output / f'bin-{language}.json'
            plot_state = output / f'plot-state-{language}.json'
            text = run('bin-' + language, ['--language', language, '--nosplash', '--layout', str(layout),
                       '--exit-after-layout', '--exit-after-layout-timeout', '90', '--dump-diagnostics', str(diagnostics),
                       '--dump-plot-state', str(plot_state)])
            assert 'ArduPilot BIN: imported 1940 numeric series' in text
            validate_bin_plot_state(json.loads(plot_state.read_text(encoding='utf-8')))
            records = json.loads(diagnostics.read_text(encoding='utf-8'))['records']
            rejected = [x for x in records if
                        (x['level'] == 'error' and not (unavailable and x['id'] == 'ros2-topic-subscriber'
                                                       and optional_ros_error(x['message']))) or
                        x['id'] in ['layout-import-unresolved-curves', 'layout-import-unresolved-curves-sync']]
            assert not rejected, rejected
            if capture:
                with (output / f'gui-{language}.log').open('w', encoding='utf-8') as stream:
                    process = subprocess.Popen(application_command(
                        executable, work / 'profiles' / f'gui-{language}',
                        ['--language', language, '--nosplash', '--layout', str(layout)]), env=env, stdout=stream, stderr=stream,
                                                start_new_session=os.name != 'nt')
                    try:
                        time.sleep(12)
                        assert process.poll() is None, 'packaged GUI exited early'
                        png = output / f'gui-{language}.png'
                        captures.append(capture_gui(process, prefix, executable,
                                                    work / 'profiles' / f'gui-{language}', png))
                    finally:
                        stop(process)
    summary = {'status': 'automated_checks_passed', 'languages': list(ACCEPTANCE_LANGUAGES),
               'gui_captures': captures,
               'visual_review': 'required separately for the captured Simplified Chinese, Traditional Chinese and English screenshots', 'release': record, 'plugin_count': len(expected),
               'loaded_plugin_count': len(expected) - len(unavailable), 'unavailable_plugins': unavailable,
               'checks': ['embedded version', 'CJK font bytes', 'licenses', 'Python backend',
                          'bundled plugin inventory and explicit external dependency boundary', 'real BIN in Unicode path',
                          'synthetic CSV in ASCII and Unicode paths: both fields, all finite samples and visible bounds',
                          'Simplified Chinese, Traditional Chinese and English curve restoration with finite visible samples and non-default viewport']}
    (output / 'acceptance.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prefix', type=Path, required=True)
    p.add_argument('--executable', type=Path, required=True)
    p.add_argument('--real-bin', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--expected-source', required=True)
    p.add_argument('--expected-version', required=True)
    p.add_argument('--capture', action='store_true')
    p.add_argument('--work-dir', type=Path,
                   help='Empty absolute directory to retain layouts, inputs and profiles, including on failure')
    a = p.parse_args()
    verify(a.prefix, a.executable, a.real_bin, a.output, a.expected_source, a.expected_version, a.capture, a.work_dir)
