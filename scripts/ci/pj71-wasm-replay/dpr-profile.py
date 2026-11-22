#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Analyze only the overlapping worst heartbeat window in each separately profiled run."""

import collections
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys

PUBLIC = Path('replay-evidence/pj71-dpr-sanitized.json')
SYMBOLS = Path('build-wasm-probe/pj_app/plotjuggler4.js.symbols')
SYMBOL_SHA = '3a69d1ba88590d2b1212c6e88c8b87b6a66f551eb117e46c77287568ebd71c99'
THREADS = {'GeckoMain', 'Renderer', 'RenderBackend', 'Compositor', 'CanvasRenderer'}
PATTERNS = [
    ('upload', re.compile(r'tex(?:Sub)?Image[23]D|Tex(?:Sub)?Image[23]D|'
                          r'Texture(?:Host|Source)::Upload|UploadTexture|glBufferSubData')),
    ('qt_draw', re.compile(r'QRaster|QPainter|paintEvent|drawPixmap|rectfill|spanfill|'
                           r'QBlendFunctions|QBackingStore::beginPaint')),
    ('gecko_composite', re.compile(r'Compositor(?:OGL|Bridge)|RenderCompositor|'
                                   r'WebRender|SwComposite|wr::(?:renderer|composite)')),
    ('qt_present', re.compile(r'QWasmCompositor|QWasmBackingStore::flush|QRhi.*::endFrame')),
    ('producer', re.compile(r'PanelEngine::Impl::(?:runTick|applyAndDiff)|nlohmann|'
                            r'WidgetEvent::WidgetEvent|luau_execute|LuaSisoTransform|'
                            r'LuauInstance|IncrementalEngine::materializeStep|runSisoIncremental')),
    ('teardown', re.compile(r'teardownToolbox|ToolboxPresenter::(?:teardown|release)')),
]
WASM = re.compile(r'wasm-function\[(\d+)\]')
MARKS = ('pj-dpr-heartbeat-start', 'pj-dpr-heartbeat-done')


def processes(profile):
    yield profile
    for child in profile.get('processes', []):
        yield from processes(child)


def timing_marks(thread):
    markers = thread['markers']
    s = markers['schema']
    for row in markers['data']:
        payload = row[s['data']] if len(row) > s['data'] else None
        if isinstance(payload, dict) and payload.get('type') == 'UserTiming':
            n = payload.get('name')
            if n in MARKS and payload.get('entryType') == 'mark':
                yield n, row[s['startTime']], payload.get('innerWindowID')


def samples_in(thread, proc_start, start, end, symbols):
    samples, table, frames = (thread[k] for k in ('samples', 'stackTable', 'frameTable'))
    strings = thread['stringTable']
    ti, sti = (samples['schema'][k] for k in ('time', 'stack'))
    fi, pi = (table['schema'][k] for k in ('frame', 'prefix'))
    li = frames['schema']['location']
    counts = collections.Counter()
    wasm_frames = missing_wasm_frames = 0
    for row in samples['data']:
        if not start <= proc_start + row[ti] < end:
            continue
        index = row[sti]
        names = []
        while index is not None:
            stack = table['data'][index]
            name = strings[frames['data'][stack[fi]][li]]
            m = WASM.match(name)
            if m:
                wasm_frames += 1
                name = symbols.get(m[1], name)
                if name == m.string:
                    missing_wasm_frames += 1
            names.append(name)
            index = stack[pi]
        # Nearest identifiable frame from leaf wins. Qt present is intentionally separate:
        # seeing a QWasm compositor label alone does not establish actual upload time.
        category = next((tag for name in names for tag, rx in PATTERNS if rx.search(name)), 'unknown')
        counts[category] += 1
    return dict(thread=thread['name'], total=sum(counts.values()), exclusive=dict(counts),
                wasmFrames=wasm_frames, unresolvedWasmFrames=missing_wasm_frames)


def lanes(profile, d, symbols):
    by_thread = [(p['meta']['startTime'], t) for p in processes(profile)
                 for t in p.get('threads', []) if t['name'] in THREADS]
    candidates = [(start, t, list(timing_marks(t))) for start, t in by_thread if t['name'] == 'GeckoMain']
    candidates = [q for q in candidates if q[2]]
    if len(candidates) != 1:
        raise ValueError('expected exactly one content process containing heartbeat marks')
    proc_start, app, got = candidates[0]
    if [m[0] for m in got] != list(MARKS) or got[0][2] != got[1][2] or not got[0][2]:
        raise ValueError('invalid or mismatched heartbeat UserTiming marks')
    origin = d['pageOrigin']
    # Align browser performance.now() to Gecko schema and confirm both ends.
    align = [proc_start + m[1] - (origin + d[key]) for m, key in zip(got, ('startMark', 'stopMark'))]
    if any(not math.isfinite(x) or abs(x) > 5 for x in align):
        raise ValueError(f'Gecko/page clocks do not align within 5 ms: {align}')
    points = [d['started'], *d['ticks'], d['finished']]
    gap, lo, hi = max((b-a, a, b) for a, b in zip(points, points[1:]))
    if abs(gap - d['maxGapMs']) > 1e-6 or not d['startMark'] <= lo < hi <= d['stopMark']:
        raise ValueError('measurement does not contain exact worst gap')
    start = origin + lo
    end = origin + hi
    content = samples_in(app, proc_start, start, end, symbols)
    if content['total'] < 40 or not content['wasmFrames'] or (
            content['unresolvedWasmFrames'] * 3 > content['wasmFrames']):
        raise ValueError('insufficient aligned or symbolized content samples')
    if sum(content['exclusive'].get(k, 0) for k in ('qt_draw', 'qt_present', 'upload', 'producer')) < 10:
        raise ValueError('insufficient recognizable draw/upload/producer stacks')
    supporting = [samples_in(t, pstart, start, end, symbols) for pstart, t in by_thread
                  if t['name'] != 'GeckoMain']
    return dict(alignmentMs=align, profiledWorstGapMs=gap, boundsPageMs=[lo,hi], content=content,
                supportingThreads=[t for t in supporting if t['total']])


def geometry(d):
    g = d['dprGeometry']
    # No IDs or UA strings: permit only shaped, finite numeric fields.
    vp = [g['width'], g['height']]
    if vp != [1280, 720] or g['pixelRatio'] not in (1, 2):
        raise ValueError('unexpected geometry')
    canvases = []
    for c in g['canvas']:
        values = [c['css'], c['pixels']]
        if any(len(x) != 2 or any(type(n) not in (int, float) or not math.isfinite(n) or n <= 0
                                 for n in x) for x in values):
            raise ValueError('invalid canvas sizes')
        canvases.append(dict(css=values[0], pixels=values[1]))
    return dict(viewport=vp, canvases=canvases)


def main():
    runner_temp = Path(os.environ['RUNNER_TEMP']).resolve()
    checkout = Path.cwd().resolve()
    if runner_temp == checkout or runner_temp.is_relative_to(checkout):
        raise ValueError('profile scratch cannot overlap upload paths')
    root = runner_temp / 'pj71-dpr-profile-raw'
    data = json.loads((root / 'summary.json').read_text())
    if not (data.get('profilePerturbsTiming') and data.get('sameInputs') and
            data.get('order') == [1, 2, 2, 1] and len(data.get('measured', [])) == 4 and
            data.get('source', {}).get('source_sha') == '2e9235ef1575551f4fa14c84ce150301e4022bcd'):
        raise ValueError('expected exact four-trial profile identity')
    s = SYMBOLS.read_bytes()
    if hashlib.sha256(s).hexdigest() != SYMBOL_SHA:
        raise ValueError('symbol map differs from verified D artifact')
    symbols = dict(line.split(':', 1) for line in s.decode().splitlines() if ':' in line)
    out = []
    for i, trial in enumerate(data['measured'], 1):
        ratio = data['order'][i-1]
        try:
            if not trial.get('valid') or ratio != trial['ratio']:
                raise ValueError('diagnostic trial invalid')
            dimensions = geometry(trial['data'])
            f = root / f'trial-{i}-dpr{ratio}' / 'gecko-profile.json'
            with f.open() as p:
                result = dict(geometry=dimensions, **lanes(json.load(p), trial['data'], symbols))
        except (KeyError, TypeError, ValueError, OSError, IndexError):
            # Never pass raw parser/OS/browser strings into the public summary.
            result = {'inconclusive': 'profile_missing_or_identity_window_or_sample_check_failed'}
        out.append({'trial': i, 'DPR': ratio, **result})
    missing = any('inconclusive' in a for a in out)
    result = dict(diagnosticOnly=True, profiledTimingNotAcceptance=True,
                  independentUnprofiledRun='45000112754/14745552347',
                  candidate='2e9235ef1575551f4fa14c84ce150301e4022bcd',
                  attribution=('inconclusive: one or more trials missing evidence' if missing else
                               'matched window samples available; counts differ from CPU or GPU duration'),
                  note=('Unknown native stacks remain unknown; no inference of zero GPU/compositor work. '
                        'No profile timings are compared to the product <100 ms gate.'), trials=out)
    with PUBLIC.open('x') as f:
        json.dump(result, f, indent=2, allow_nan=False)
        f.write("\n")
    print(result['attribution'])
    for a in out:
        c = a.get('content', {})
        print('trial', a['trial'], 'DPR', a['DPR'], 'content', c.get('exclusive', a.get('inconclusive')))
    return int(missing)


if __name__ == '__main__':
    sys.exit(main())
