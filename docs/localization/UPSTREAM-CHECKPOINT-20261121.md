# Development upstream checkpoint

This candidate has two parents: localized development `b5832136100b7b4ce15b5587a506ac69bfe335bb`
(including the #70 controller correction) and upstream `9671c907aa11210832987cb6eac5419b07c44b12`.
It is not a packaged release, official 4.1.0, or permission to publish. The release rules, previous
tags, localized 26,000,000-byte full-package ceiling and 16,932,000-byte upstream-reference
budget are unchanged.

## Why not the newest upstream tip

At the audit, upstream main was `55caa38bcfb19a9a9d1b8f92970981cd97c99686` with the theme tail
`e7a7d06a5` and `55caa38bc` after the checkpoint. The exact checkpoint passed upstream native
[Linux](https://github.com/PlotJuggler/PlotJuggler/actions/runs/44832355254) and
[Windows](https://github.com/PlotJuggler/PlotJuggler/actions/runs/44832355283) CI and all three
upstream packaging jobs. It did not produce an upstream WASM or macOS Metal fixture result
for this SHA. The latest tip failed exact-head
[Linux](https://github.com/PlotJuggler/PlotJuggler/actions/runs/44834994369),
[Windows](https://github.com/PlotJuggler/PlotJuggler/actions/runs/44834994371),
[macOS](https://github.com/PlotJuggler/PlotJuggler/actions/runs/44848089875),
[WASM](https://github.com/PlotJuggler/PlotJuggler/actions/runs/44864309053),
Pixi and sanitizer checks. The two later commits are not incorporated. Before merging this
candidate into a watched branch, the default scheduled source intake must not automatically
advance it to an unvalidated later commit.

## Compatibility

Native Log panels replace the default legacy official Log Viewer. Layout migration converts
only the known `log-widget/log_viewer` payload with valid saved inputs/settings. Topic identity,
supported filters, visibility and the future-entry mode carry over; old splitter/column
pixel widths do not. Unrecognized or malformed old payloads are retained untouched. Browser
layout apply can defer object binding for Logs and Custom Widgets; ordinary unresolved plots
retain the exact restore check and rollback behavior. Test both saved formats with a real
browser restart, delayed data, a real drop, and six epoch-timestamped entries. The merge
retains the previous QRhi canvas handoff order and upstream keyboard focus restoration.

Whole-app native, browser interaction, rendering and package budgets must be checked on
this exact candidate before promotion; a source-only validation result is not a pass.
