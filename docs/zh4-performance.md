# zh.4 performance measurements (2026-10-16 UTC)

These are same-machine measurements, separate from package-size measurements.
No hardware identity, flight log, GPS data, user settings or private path is
included in the published data. The installed zh.3 and its settings were checked
before/after and remained unchanged. No desktop switch or visible benchmark
window was made on the user's desktop.

## Production packages

Baseline: released zh.3 Windows ZIP, source `3117288ce8d710bde4f7a86ca5ed5240ebb1c301`,
359,724,860 bytes, SHA-256 `afe4f9ae76b77d5304e928d4e3969652e770f14cd618436268f16a355a430957`.
Candidate: CI zh.4 Windows ZIP at `eb7ff9d1f50c43fc1c95516667d2ea770e2059ff`,
122,292,028 bytes, SHA-256 `29100247bd7188ad5e4ad715b1b618c1fc31d5984b8769fe84bdbbfb64c9062f`.
Both archives were fully hash/CRC verified and extracted into separate folders.
Qt5 Core/Gui/Widgets and Python DLL/stdlib ZIP hashes match between packages.
Subsequent commits add development tools, tests, policy and documentation;
application/plugin/image source files remain identical to the measured candidate.

`scripts/benchmark_windows_packages.py` starts fresh processes on a newly created,
never-activated Windows desktop. It observes only its own process's windows,
polling visible state at about 2 ms, and reads Windows peak working-set counters.
Each mode/version receives one unmeasured prime and eight measured fresh starts,
alternating AB/BA order. Settings are isolated by the existing UI self-test
argument. `--test` generates 116 numeric test curves; this is not a DataFlash
loading benchmark. Splash IDs rotate through 1, 26, 52 and 93.

| Median, 8 samples per cell | zh.3 | zh.4 |
|---|---:|---:|
| Main window visible, splash disabled | 880.57 ms | 858.55 ms |
| First splash window visible | 227.72 ms | 228.68 ms |
| Main window visible with splash | 4412.62 ms | 4380.77 ms |
| Peak working set through UI acceptance, no splash | 75.56 MiB | 75.41 MiB |
| Peak working set through UI acceptance, with splash | 87.27 MiB | 80.71 MiB |

The first-splash difference is below the polling interval. The small main-window
differences and overlapping samples do not establish a general startup speedup.
The splash path deliberately holds for 500 + up to 3000 ms; that hold remains
included, not silently subtracted. Through-exit peaks include UI captures after
the self-test's 1500 ms timer; before-main counters are also retained separately.

## Direct image rendering

The standalone tools are built from exact pinned zh.3 and candidate
`a5ca274dbc5f82c2df4dbf230e4e1757ff68533b` localizedMeme implementations and
image bytes, using the same MSVC Release/C++17/Qt5.15.2 configuration. They load
the same verified production Qt5 runtime on this machine. No widget, plugin,
PNG export, file encoding or display-presentation time is included in a timed
render call: it measures loading, compositing and final scaling.

`scripts/benchmark_image_tools.py` runs 32 fresh processes: both languages,
both cache conditions, four rotations of the same IDs, and both implementations
in counterbalanced order. Each process primes its four IDs and then measures
12 rounds. This yields 1536 render samples, 48 per image/version/language/cache
cell. ID 1 is an unchanged technical-label control, 26 uses overlays, and 52/93
are complete-image fallbacks.

| Chinese render median, 48 samples/cell | zh.3 | zh.4 |
|---|---:|---:|
| ID 26, primed round-robin | 30.951 ms | 10.979 ms |
| ID 26, Qt cache cleared each image | 31.139 ms | 14.482 ms |
| ID 52, primed round-robin | 31.020 ms | 24.279 ms |
| ID 93, primed round-robin | 28.412 ms | 24.366 ms |

Across the four equally weighted IDs and both cache modes, first-render
medians in fresh processes are 36.651 / 28.705 ms (Chinese) and 6.851 / 8.210 ms
(English), zh.3 / zh.4 respectively. The English first-render increase is
reported rather than hidden. Repeated English images are approximately
0.004 ms when primed; cleared-cache medians are about 1.95–4.24 ms in either
version. The isolated harness peak working set is about 45.4 MiB in both, and
must not be substituted for full-application memory.

## Conditions, limits and reproduction

No OS file cache was flushed and the machine was not rebooted. Every first
image uses a fresh process/Qt cache, while filesystem pages are generally warm
after verification and priming. The clear mode clears QPixmapCache, not Windows'
file cache; the primed round-robin mode can still experience Qt cache eviction.
No power-policy or background-task controls were imposed. An inactive desktop's
window-visible state is not photon/monitor presentation timing. Results apply
to these IDs, runtimes and this machine; they are not a universal speed claim.

The raw samples and n/min/max/p10/median/p90 are in
`benchmarks/zh4-production-samples.json`, `benchmarks/zh4-render-samples.json`,
and `benchmarks/zh4-performance-summary.json`. No outliers were removed from
the measured samples. The initial timed-out harness launch had a missing Qt
plugin search path and produced no sample; the published runner explicitly
selects the isolated runtime's platform/image plugins.

Rebuild the isolated Qt5 tools with `scripts/prepare_image_benchmarks.py` and
`tests/image-tools/CMakeLists.txt` (PJ_IMAGE_TOOLS_QT_MAJOR=5,
PJ_BUILD_IMAGE_BENCHMARKS=ON). The separate `zh-image-tools.yml` CI publishes
them. Pass the extracted tool artifact and a verified Qt5 portable runtime to
the image runner; pass the two extracted production packages to the startup
observer. All paths are caller-supplied and nothing is installed by either tool.
