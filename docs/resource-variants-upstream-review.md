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

The pinned [4.x root CMake](https://github.com/PlotJuggler/PlotJuggler/blob/0345ec513bde7f05ad3148548ac30401f2b6f7a7/CMakeLists.txt)
uses C++20 and Qt6; [versions.env](https://github.com/PlotJuggler/PlotJuggler/blob/0345ec513bde7f05ad3148548ac30401f2b6f7a7/versions.env)
selects Qt 6.11.1. This fork uses C++17 and Qt5. The upstream application now
lives in `pj_app`, with an object-library shell and `pj_resources`; the fork's
application and resource targets live in `plotjuggler_app`.

## What can be proposed

| Change | Assessment | Minimum adjustment or boundary |
|---|---|---|
| `resource_image.h/.cpp` | Portable candidate; needs upstream integration | Copy the MPL-2.0 helper into the 4.x module layout and link Qt6 Core/Gui. It accepts a QImage plus a JSON description and has no Chinese, meme-ID, plugin, or ArduPilot dependency. No public plugin API changes are needed. Qt6 compilation remains unverified. |
| `resource_image_test.cpp` | Portable candidate; needs upstream integration | The focused regression now uses QGuiApplication and Qt Gui only. Adapt it to upstream's GTest/CMake conventions and run it on upstream's Qt6 platform matrix. Preserve invalid geometry, bounded image allocation, alpha, DPR, and atomic fallback tests. |
| Optional QRC and locale adapter | Needs redesign for 4.x | Upstream enumerates `:/resources/memes/*.jpg` in `Splashscreen.cpp`, rather than using the fork's indexed catalog wrapper. Connect the helper there only when a locale-specific variant exists. Keep original English/default splash behavior and the serious-splash option. The fork's Chinese-default policy must not be copied upstream. |
| Production exclusion of regression binaries | Already addressed differently upstream | The 4.x root and Linux release workflow disable PJ_BUILD_TESTS for packaging; the Windows installer explicitly stages the app and required helper. The fork's tests_bin fix addresses its legacy broad bin staging and should not be transplanted blindly. An upstream package inventory guard could be a separate small proposal if maintainers want one. |
| Chinese catalog/PNGs, fork version, ArduPilot integration and fork CI | Keep in this fork | These are not needed by the generic helper. Fork-specific release baselines, dependency hashes and privacy policy are also separate concerns. |

The relevant upstream integration points are the pinned
[Splashscreen.cpp](https://github.com/PlotJuggler/PlotJuggler/blob/0345ec513bde7f05ad3148548ac30401f2b6f7a7/pj_app/src/Splashscreen.cpp),
[app CMake and splash tests](https://github.com/PlotJuggler/PlotJuggler/blob/0345ec513bde7f05ad3148548ac30401f2b6f7a7/pj_app/CMakeLists.txt),
[resource target](https://github.com/PlotJuggler/PlotJuggler/blob/0345ec513bde7f05ad3148548ac30401f2b6f7a7/resources/CMakeLists.txt),
and [Windows staging script](https://github.com/PlotJuggler/PlotJuggler/blob/0345ec513bde7f05ad3148548ac30401f2b6f7a7/packaging/installer/build_windows_installer.ps1).
Upstream also targets WebAssembly; this fork has not tested that platform, macOS,
or Qt6. File/resource loading and maximum image memory should be tested there.

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

## Performance: measured and unmeasured

The resource audit measures actual binary RCC output using the same Qt5 RCC
5.15.13 default compression options: **7,898,721 bytes (zh.2), 160,704,011
(zh.3), and 56,042,296 (zh.4)**. The final Chinese source PNG/atlas payload is
48,103,702 bytes. Package reports separately record actual ZIP, IFW EXE,
AppImage and DEB bytes, SHA-256 and container compression. These are disk-size
measurements, not runtime speed measurements. Baseline and candidate must be
compared within the same package format; dependencies and debug policies must
also be checked before attributing the whole change to resources.

**Startup latency, first-image latency, repeated image-switch latency and peak
RAM have not been benchmarked.** CI UI/self-test durations include fixed timers,
exports and log loading, so they are not valid substitutes. No faster-startup,
lower-memory or smoother-switching claim follows from the smaller packages.

Source inspection suggests a tradeoff that needs measurement: an overlay call
decodes the original and atlas, creates a native-size canvas, composites patches,
then applies the existing final display scaling. The atlas QHash is scoped to
one call; it is not a persistent image cache. A whole-image load and Qt's pixmap
cache can have different warm behavior. This may add CPU or temporary memory,
even while reducing disk reads; the direction and magnitude are unmeasured.

A useful follow-up benchmark would compare pinned zh.3 and zh.4 production
builds on the same machine/Qt/compiler, with separate cold and warm runs,
identical image IDs and language settings, process-to-visible-window timing,
instrumented decode/composite/display timings, and peak working set/RSS.
Report samples and dispersion, exclude the intentional splash hold timer,
and include complete-image fallbacks as well as overlays.

The present conclusion is **a generic helper is a plausible upstream proposal
after adaptation and Qt6 validation; the complete fork branch and Chinese data
are not directly mergeable**. No upstream PR, release, or installation is made
by this assessment.
