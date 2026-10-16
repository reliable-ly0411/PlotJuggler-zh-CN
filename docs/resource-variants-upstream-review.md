# Upstream feasibility and performance assessment

Observed 2026-10-16 UTC. This is a source review, not an upstream submission or
a claim that PlotJuggler 4 has been built with this patch.

## Exact baselines

The official repository is [PlotJuggler/PlotJuggler](https://github.com/PlotJuggler/PlotJuggler),
licensed under MPL-2.0. Its current default branch is `main-4.x`, pinned here at
[`0345ec513bde7f05ad3148548ac30401f2b6f7a7`](https://github.com/PlotJuggler/PlotJuggler/tree/0345ec513bde7f05ad3148548ac30401f2b6f7a7).
The latest stable release is [4.0.0](https://github.com/PlotJuggler/PlotJuggler/releases/tag/4.0.0),
published 2026-09-21, at `d278b1fe98f699d27b820867f454a697e50def2e`.

The fork's version baseline remains the official 3.17.2 tag,
`034a5cc919909aebb124e0dc1abbe2029c3eed0f`. The reviewed zh.4 image commit
`eb7ff9d1f50c43fc1c95516667d2ea770e2059ff` is 23 commits ahead of that tag.
It also contains all four subsequent commits of the official legacy `main`
head, `3458f7827732d28db341833fb973612b0c2e3de2`; that head is an ancestor,
not an outstanding merge. GitHub's compare API reports **no common ancestor**
between the 3.17.2 history and the current `main-4.x` head. A conventional merge
of this feature branch into the default upstream branch is therefore unsuitable.

This is not a shallow-clone artifact. A separate bare repository fetched the
official `main`, `main-4.x`, `3.17.2` and `4.0.0` refs with full commit history
(`--filter=tree:0`, no depth limit). It reports shallow=false, 2835/620 reachable
commits on the two branches, and distinct roots
`fad0cdf47616857ff8f5cc5377763f3df84d4ac5` /
`7ace14a581abebddb72c530d97ca3a708d081071`.
Both 3.17.2-to-4.0.0 and 3.17.2-to-main-4.x merge-base return exit 1;
3.17.2-to-legacy-main returns the 3.17.2 commit. The stable 4.0.0 tag is an
ancestor of main-4.x. Commands, refs and exact outputs are retained in
`benchmarks/upstream-full-history.json`; GitHub's full-server comparisons agree.

The pinned [4.x root CMake](https://github.com/PlotJuggler/PlotJuggler/blob/0345ec513bde7f05ad3148548ac30401f2b6f7a7/CMakeLists.txt)
uses C++20 and Qt6; [versions.env](https://github.com/PlotJuggler/PlotJuggler/blob/0345ec513bde7f05ad3148548ac30401f2b6f7a7/versions.env)
selects Qt 6.11.1. This fork uses C++17 and Qt5. The upstream application now
lives in `pj_app`, with an object-library shell and `pj_resources`; the fork's
application and resource targets live in `plotjuggler_app`.

## What can be proposed

| Change | Assessment | Minimum adjustment or boundary |
|---|---|---|
| `resource_image.h/.cpp` | Portable candidate; needs upstream integration | Copy the MPL-2.0 helper into the 4.x module layout and link Qt6 Core/Gui. It accepts a QImage plus a JSON description and has no Chinese, meme-ID, plugin, or ArduPilot dependency. No public plugin API changes are needed. Its isolated Qt6.11.1/C++20 compilation and regression test passed on Ubuntu. |
| `resource_image_test.cpp` | Portable candidate; needs upstream integration | The focused regression now uses QGuiApplication and Qt Gui only. Adapt it to upstream's GTest/CMake conventions and run it on upstream's Qt6 platform matrix. Preserve invalid geometry, bounded image allocation, alpha, DPR, and atomic fallback tests. |
| Optional QRC and locale adapter | Needs redesign for 4.x | Upstream enumerates `:/resources/memes/*.jpg` in `Splashscreen.cpp`, rather than using the fork's indexed catalog wrapper. Connect the helper there only when a locale-specific variant exists. Keep original English/default splash behavior and the serious-splash option. The fork's Chinese-default policy must not be copied upstream. |
| Production exclusion of regression binaries | Already addressed differently upstream | The 4.x root and Linux release workflow disable PJ_BUILD_TESTS for packaging; the Windows installer explicitly stages the app and required helper. The fork's tests_bin fix addresses its legacy broad bin staging and should not be transplanted blindly. An upstream package inventory guard could be a separate small proposal if maintainers want one. |
| Chinese catalog/PNGs, fork version, ArduPilot integration and fork CI | Keep in this fork | These are not needed by the generic helper. Fork-specific release baselines, dependency hashes and privacy policy are also separate concerns. |

The relevant upstream integration points are the pinned
[Splashscreen.cpp](https://github.com/PlotJuggler/PlotJuggler/blob/0345ec513bde7f05ad3148548ac30401f2b6f7a7/pj_app/src/Splashscreen.cpp),
[app CMake and splash tests](https://github.com/PlotJuggler/PlotJuggler/blob/0345ec513bde7f05ad3148548ac30401f2b6f7a7/pj_app/CMakeLists.txt),
[resource target](https://github.com/PlotJuggler/PlotJuggler/blob/0345ec513bde7f05ad3148548ac30401f2b6f7a7/resources/CMakeLists.txt),
and [Windows staging script](https://github.com/PlotJuggler/PlotJuggler/blob/0345ec513bde7f05ad3148548ac30401f2b6f7a7/packaging/installer/build_windows_installer.ps1).
The pinned 4.x tree contains 37 meme JPEGs, rather than the fork's indexed 106;
its pool and locale adapter must be reviewed independently. Upstream also targets
WebAssembly; this fork has not tested that platform, macOS, or Windows Qt6.
File/resource loading and maximum image memory should be tested there.

`scripts/export_generic_resource_patch.py` exports exactly four additive MPL-2.0
files under pj_app: the Core/Gui helper, its synthetic regression and a separate
Qt6/C++20 test CMake project. No application source, root target, English image,
QRC, default locale, serious-splash option or plugin is changed by this patch.
The isolated CI additionally applies it to the real pinned upstream index and
builds that separate target; its green result is required before describing that
application check as passed. It does not build or validate the complete 4.x app.

No current commit is a clean upstream cherry-pick: the first feature commit
mixes the generic helper, fork adapter, Chinese assets, tests and packaging.
The smallest useful submission would be (1) helper plus Core/Gui tests,
(2) optional 4.x resource/locale plumbing with unchanged default behavior,
and, only if warranted, (3) a package-content regression guard. Each should be
rebuilt on the pinned upstream rather than merged with unrelated histories.

The helper and new tests retain MPL-2.0 headers. Existing English JPEG bytes,
visible credits and aspect ratios are preserved. The catalog records immutable
source and pixel hashes for derivatives. Repository licensing and retained
credits alone do not establish redistribution rights for every underlying
third-party meme/photo; an upstream data submission still needs provenance and
maintainer rights review. No new AI generation is involved in this optimization.

## Performance measurements and limits

The resource audit measures actual binary RCC output using the same Qt5 RCC
5.15.13 default compression options: **7,898,721 bytes (zh.2), 160,704,011
(zh.3), and 56,042,296 (zh.4)**. The final Chinese source PNG/atlas payload is
48,103,702 bytes. Package reports separately record actual ZIP, IFW EXE,
AppImage and DEB bytes, SHA-256 and container compression. These are disk-size
measurements, not runtime speed measurements. Baseline and candidate must be
compared within the same package format; dependencies and debug policies must
also be checked before attributing the whole change to resources.

Same-machine measurements now include eight fresh production-package processes
per version/mode and 1536 direct render samples from the pinned implementations,
using identical Qt5.15.2 DLLs. Full methods, raw data, percentiles and limits are
in [zh4-performance.md](zh4-performance.md). No OS cache was flushed. Production
visible-state timings were observed on a private inactive desktop, and direct
render timing excludes widget presentation and PNG export. Intentional splash
holds remain included and explicitly identified.

First-splash visible-state medians are 227.72/228.68 ms (zh.3/zh.4), within the
2 ms polling interval; these do not establish a startup speedup. The overlay
example 26 renders in 30.951/10.979 ms in primed round-robin tests, but this is
one image and one cache condition. English fresh-process first-render medians
increase from 6.851 to 8.210 ms and are also reported. The one-call atlas QHash
is still not a persistent cache. Disk savings, sample render results and full
application memory are separate measurements.

The present conclusion is **a generic helper is a plausible upstream proposal
after integration and broader platform validation; the complete fork branch and Chinese data
are not directly mergeable**. No upstream PR, release, or installation is made
by this assessment.
