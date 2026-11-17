# 4.x WASM language-dependent acceptance audit — 2026-11-17

Base candidate: `3c471fc572bb77d06d43f0f77cd3a27bb6338a0d`.
Archived binary replayed: localized acceptance artifact from controller
`55cff6d20b721ef9b4fdcf9f5ad01f7a5687cf2a`, run
[44082994661](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/actions/runs/44082994661).
The artifact ZIP SHA-256 is
`a41f668abbe2746f55a22a12b071eeb2c0f49d39e6ac866339442c0b732b99bb`.
No application rebuild was used for these browser diagnostics.

## Failure classification

The localized Chromium run had 17 functional failures and two serial failures.
Their first failing checks were:

- Eight menu/picker selectors: Preferences, Remove, Apply Filter, source-layout
  side-file selection, Remove All, Zoom Out, plot split, Scene2D split.
- Six displayed-text expectations: missing layout sources, wrong source file,
  duplicate XY name, streaming connection failure, local URDF permission,
  and Dummy Streamer display name.
- Five readiness predicates: Python error prefix; ANYmal meshes in the
  functional and both serial cases; URL robot failed-mesh status.

This classifies the first barrier, not all downstream application behavior.
The Firefox failures show the same translated text and selector dependencies.
No separate theme defect was established by those logs: a missing menu action
can prevent a later plot/theme assertion from running. Plot pixel, scene,
state, rollback, source-identity and numeric assertions remain in place.

The patch uses existing QAction object names for Preferences/Quit and existing
MessageBox roles for primary/cancel source decisions. Actions without existing
IDs use their exact production translation context/source, with mnemonic
normalization on both sides. UI text expectations select one exact catalog
mapping from the *observed application language*, not an OR of languages.
A source test verifies the mappings against both finished TS catalogs.

Readiness still requires equal loaded/total mesh counts, original live/draw/
placeholder counts and rendered frames. The Python case still requires its
exact derived vertex count, one warning, the translated error prefix and
`SyntaxError`. Streaming identities and serialized paths are not translated.

## Replayed checks

Cloud Linux Chromium `156.0.8078.79`, pinned Playwright `1.61.1`, loopback-only
fixture server and unchanged offline browser resolver rules:

| Complete original functional scenario with mapped UI expectations | English | Simplified | Traditional |
| --- | --- | --- | --- |
| Dataset Cancel/Remove and dataset counts | pass | pass | pass |
| XY duplicate dialog, alias retention, swap and cancel rollback | pass | pass | pass |
| Local URDF render, save, restore and browser file-access restriction | pass | pass | pass |

The original English four-case baseline, including Preferences, passed 4/4.
Before the mapping changes, the corresponding Simplified and Traditional
four-case runs each failed 4/4 at their language-dependent first checks.

Additional complete Simplified scenarios passed against the same binary:

- Layout transaction, exact round trip, failed-download tripwire and clearing
  recent layouts. Follow-up replay exposed and fixed the later `Save Layout`,
  ephemeral-path and `Clear recent layouts` English expectations.
- Multi-source duplicate-basename transaction and exact timeline restore.
  The expected saved slot is `pj4-sources/0/duplicate.csv`, not its basename.
- On-demand Python recipes: valid point output and invalid recipe warning.
- URL/package robot meshes: one success, two failures, exact placeholders,
  request paths and retained workspace checks.

The Dummy Streamer case passed its display/data/plot/pause/resume/stop assertions
and reached its final Quit action. It remains **failed** on the archived binary:
that binary still has the English-only Quit probe. Its shutdown assertion has
not yet run with the new probe.

The six actual menu-probe functions were extracted without modification from
this worktree and compiled with pinned native Qt `6.12.0`, `-Wall -Wextra -Werror`.
For each of three languages, visible menu actions were found and hidden menu
actions were rejected: 18 positive and 18 negative checks passed. This is not
an Emscripten build or browser validation of the changed C++ probe. Source
selection roles were checked against MainWindow and MessageBox production code.

The focused Python WASM source suite passed 15/15. Both translation catalogs
remain 2153/2153 translated with zero missing source messages; the source check
reports two stale QObject entries (`Reselect source`, `Select source `) after
removing their probe-only references and exits **1 (failure)**. Zero missing
messages did not make the full source check pass. Catalog text was preserved;
the stale active status is corrected in the follow-up below.
Changed JavaScript syntax and collection of 202 browser tests passed.
Pre-commit and branch-name checks passed.

To replay the same three scenarios in each language against an acceptance server:

```sh
cd tests/wasm
for language in en_US zh_CN zh_TW; do
  PJ_WASM_TEST_LANGUAGE="$language" npx playwright test \
    dialogs.spec.js plotting.spec.js scene3d_models.spec.js \
    --project=chromium --workers=1 \
    --grep 'dataset removal|right-drag creates XY|a local URDF renders'
done
```

The language fixture checks Qt's actual language after boot. Include
`Preferences opens` once validating a newly compiled probe. The dedicated
language probe reads only an application property; it avoids font/render work
before the unchanged performance measurement. The old read-only probe remains
a diagnostic fallback for archived acceptance binaries.

## Independent unresolved failures and remaining validation

Unmodified upstream `5002da40a6499cb99c1073d5b8c611f1e825cb4b` Chromium had
96/96 functional passes, but ANYmal load measured **2459 ms** against the
unchanged **2000 ms** longest-main-thread-task gate (restore 755 ms, frame gap
2483 ms). A previous run on the same upstream also measured 2403 ms. A call-stack
cause has not been demonstrated. The local CPU-profile attempt was blocked by
HTTP 403 from `assets.plotjuggler.io`; no permission change or bypass was used.
It still needs a CPU trace using the exact upstream artifact and hash-verified
sample assets, distinguishing application restore from software rendering.
The threshold, serial execution and assertions were not relaxed.

Upstream Firefox shard 1 was job-green but its explicitly non-blocking editor
step contained a separate 60-second Transform Editor materialization failure.
That is not explained by Chinese translation and remains unresolved.

New C++ probes still need a real Emscripten build and full Chromium/Firefox
replay. The cloud diagnostic environment has no Firefox/Xvfb setup, so no local
Firefox pass is claimed. The HTTPS robot deployment case, source-side-file
picker and complete preset scenarios have not been replayed with the new
checks. New first-failure barriers may expose further product defects.

The original CI logs, failed screenshots, all 12 artifact ZIP digests, and
individual local JSON results remain in the cloud evidence workspace under
`/workspace/scratch/pj-sdk101-validation/`. Failed local attempts are retained as
separate JSON reports; subsequent successful attempts do not replace them.

This patch does not change production images, original PNGs, budgets, SDK pins,
workflow gates or the dual-artifact receipt scheme. The last measured 55 build
remains: upstream startup 15,065,341 B against 16,932,000 B; localized startup
24,579,178 B and full package 25,336,400 B against the independent 26,000,000 B
full-package gate. Those measurements do not certify a later head.


## Follow-up: exact 3c run and validation plan

Run `44098646743` at controller/source candidate `3c471fc5` ended with the same
localized 17 functional and two serial Chromium failures; the additional
log/layout/glyph (5) and JPEG pixel (1) scenarios passed. Localized Firefox
remained 75 functional passes, 17 failures and seven existing skips; its
non-blocking editor suite was one pass and one menu-selector failure.

The unchanged upstream source `5002da40` had 96 Chromium functional passes and
five serial passes this time. ANYmal longest tasks were 1314 ms (load) and
1333 ms (reopen), below the unchanged 2000 ms gate. This successful observation
does not erase the previous 2459 ms failure or establish its cause.
Upstream Firefox had 92 functional passes and seven existing skips. Its
non-blocking Transform Editor now completed materialization but failed the
unchanged 100 ms heartbeat bound at 166.98 ms. Thus the earlier materialization
timeout and current responsiveness failure must be investigated independently
of UI translation.

A cloud-only Firefox 151.0 / Playwright 1.61.1 replay was attempted against the
archived upstream binary, with a private Xvfb and the original test. Firefox
failed before application startup: browser launch timed out after 180 seconds,
reporting a read-only `/proc/self/uid_map` sandbox error and SWGL framebuffer
mapping failure. No application assertion ran. No sandbox disable flag or
permission bypass was used. The full launch error is retained separately from
CI's actual application failures.

Source inspection identifies the next profiling boundaries, not a proven
fix: `DataProcessorService::installTransform` runs an initial 8 ms
`materializeStep`; a zero-interval Qt timer calls `stepMaterialization` for later
slices. Failure reporting, dependent/output bookkeeping, catalog notifications
and synchronous UI/render work are outside the inner datastore slice deadline.
Measure those spans and the browser event-loop/graphics work separately before
changing scheduling. Neither the 100 ms heartbeat nor 60-second completion
assertion has been widened.

The next localized candidate adds the same four functional scenarios in all
three languages to both Chromium and Firefox shard 1. Each language gets its
own output directory/log, every language is attempted even if another fails,
and any failure fails the step. Existing full suites, serial bounds, upstream
source builds, budgets, image assertions and the original non-blocking editor
policy remain intact. This adds browser checks, not another full build.


The candidate worktree was fast-forwarded through the reviewed language change
and the three-language CI step. Integrated source validation passed **801 tests,
31 skipped**, with no failures. At that integration checkpoint, the original `3c471fc5` native run
`44098684851` was still compiling. Its final failures and isolated fixes are now
recorded in [the native regression audit](NATIVE-REGRESSION-AUDIT-20261117.md).

`pj_datastore/src/incremental_engine.cpp` owns the slice implementation (not the
SDK ABI layer). The main-thread complete-read barrier can also call
`finishPendingMaterialization` with an effectively unbounded deadline. That
path and UI/render notifications should be included in a timing trace; source
inspection alone does not establish that either caused the observed Firefox
failure.


## Exact 2459f63b final run and follow-up

[Run 44108777625](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/actions/runs/44108777625)
completed against controller/localized source
`2459f63bf38dc0b7eddc2e8588197672afdd0ad8` and the unchanged upstream
`5002da40a6499cb99c1073d5b8c611f1e825cb4b`. Source CI
[44108777769](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/actions/runs/44108777769)
passed on Linux (801 tests, 24 skipped) and Windows (799 tests, 32 skipped).

| Actual production measurement | Upstream | Localized |
| --- | ---: | ---: |
| Startup Brotli bytes | 15,064,636 | 24,578,988 |
| Complete download bytes | 15,821,858 | 25,336,210 |
| Applicable unchanged gate | 16,932,000 startup | 26,000,000 total |

Both production and acceptance archives for each role were downloaded and
checked against GitHub SHA-256 digests. Every receipt file entry, extra support
file, source SHA and source tree was independently verified locally. The
[package evidence](WASM-2459-PACKAGE-EVIDENCE.json) records exact archive and
receipt hashes. All twelve run artifacts and complete browser/build logs are
retained in cloud scratch under `dual2459-artifacts/` and `2459-*.log`.

Final browser results, without collapsing non-blocking failures into green jobs:

- Upstream Chromium: functional 96 passed; serial 5 passed. Anymal longest
  load/reopen tasks were 1,096/1,060 ms. The earlier 2,459 ms failure remains
  unresolved evidence; unchanged-source passes do not establish a repair.
- Upstream Firefox: shard 1 functional 50 passed; shard 2 42 passed / 7 skipped.
  The non-blocking editor step was 1 passed / 1 failed: the large Luau series
  still reported materializing after the original 60-second deadline.
- Localized Chromium: functional 85 passed / 11 failed; serial 3 passed / 2
  failed; log/layout/glyph 5 passed; JPEG pixel-drawing 1 passed (64 images).
- Localized Firefox: shard 1 functional 46 passed / 4 failed; shard 2 34 passed /
  8 failed / 7 skipped. Non-blocking editors: 1 passed / 1 failed, with a
  185.06 ms heartbeat gap against the unchanged 100 ms gate.
- All twelve additional language cases failed in each browser on the same
  console-framing defect before their functional assertions could execute.

The localized functional failures divide into two concrete probe defects:

1. Emscripten's dedicated language probe emits a trailing newline. Splitting
   only on a space retained `zh_CN\n` (or the other requested language), which
   the strict language allowlist correctly rejected. Trim console framing and
   split whitespace; retain exact supported-language and requested-language
   equality. Five Node regressions cover English, LF, CRLF, archived multi-field
   output and rejection of an unsupported language.
2. The populated PlotWidget menu uses `PJ::PlotWidget / Split &Horizontally`;
   the empty dock uses `PJ::DockWidget / Split Horizontally`. Match those two
   exact translated action labels, normalizing accelerators on both sides.
   No UI action is triggered by the probe and no alternative language is
   accepted. The actual split behavior, curves and tracker assertions remain.

Focused follow-up, without rebuilding the archived WASM binary:

- Chromium 156 / Playwright 1.61.1, actual 2459 acceptance bytes and corrected
  JavaScript: English, Simplified and Traditional functional cases 4/4 each.
- Five additional cases passed: transactional layout save/restore, multi-source
  duplicate basenames/timeline, valid and invalid Python layout recipes, URL
  model meshes, and the complete dummy-stream lifecycle including Quit.
- Actual extracted menu-probe functions against Qt 6.12 and both production
  catalogs: the original fails on the populated Chinese plot menu; corrected
  functions pass 21 visible and 21 hidden checks across seven menu identities
  and three languages. This is not an Emscripten link/browser pass for the new
  C++ probe; the next exact-head WASM run must provide that evidence.
- Packaging/JS tests 40/40; focused Python source/receipt tests 15/15; full Qt
  extraction still reports 2,153/2,153 translated entries per catalog, zero
  missing source messages and the two retained probe-only stale entries. This
  command returned **1**, so the full extraction check failed; the earlier
  checkpoint did not distinguish this correctly from catalog-only success.

The first local replay used an obsolete `/plotjuggler4.html` URL and encountered
404 before boot; it was stopped and its output retained separately. The passes
above use the receipt's real `index.html` entrypoint at `/`. No GitHub run was
cancelled or retried for this local invocation error.

Anymal hosted-asset profiling remains blocked by the recorded HTTP 403;
Firefox local profiling remains blocked before app startup by its sandbox
launch failure. Neither was bypassed or retried. The 8 ms datastore slicing,
notifications/render work and whole-series completion barrier remain profiling
boundaries, not a proven diagnosis. All original timeouts, budgets and other
assertions remain active, including the existing non-blocking editor policy.

## Catalog-state follow-up after exact-head native preflight

Candidate `1b9af0c7b675c53b5a2b2967f1e500aff5495773` passed both source CI
jobs in run 44118271684, whose translation invocation is catalog-only. Native
run [44118377038](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/actions/runs/44118377038)
failed full Qt extraction on Linux job 134162629205 and Windows job
134162628823: both found the same two stale active QObject entries. Application
build, native regression, packaging and clean-package checks were skipped.

The follow-up marks only these no-longer-extracted probe entries `vanished` in
both catalogs, retaining their text/history. The real `PJ::MainWindow` messages
remain active, including `Reselect source`, `Select source 1 of %1`, and
`Select source %1 of %2`. No guard, identity, image, budget or functional
assertion changes. Full Qt 6.12 extraction now exits **0**: each catalog has
2,151/2,151 translated active messages, zero missing and zero stale; placeholders,
plurals, rich text and source contexts all pass. The original nonzero local log
and both complete CI failure logs are preserved in cloud scratch. This result
does not replace exact-head native or browser acceptance.

The repaired catalogs were also rebuilt through the standalone Qt 6.12 i18n
project: 26/26 CTest entries passed, plus 11/11 unchanged checker unit tests.
No current WASM run was cancelled or repeated for this follow-up.

## Exact-head 1b9 packaging-test dependency failure

In run [44118271359](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/actions/runs/44118271359),
localized build job 134162410862 compiled the production application, then
failed `Package production build and verify packaging scripts`: the added
`ui_language.test.cjs` imports `@playwright/test`, but `npm ci` was scheduled
later in the browser-install step. The local replay had an existing dependency
installation and therefore did not expose the clean-runner ordering defect.
The failure is `Cannot find module '@playwright/test'`; it is not a compile
error, budget failure or observed browser failure. Production receipt/size
measurement, budget checks, acceptance build and both localized browser jobs
were skipped. No new localized size or functional pass can be claimed here.

Both WASM build workflows now install the unchanged lockfile's dependencies
before `test:package`, reusing that installation for the later browser setup.
Separate Chromium/Firefox jobs keep their own installations. All 40 packaging
and language unit tests, browser installation, source offers, licenses, budget
scripts and thresholds are retained. A clean scratch replay first reproduced
the missing-module failure; after pinned `npm ci` the five language cases pass.
A fresh dependency installation in the isolated worktree then passes all
**40/40** package tests. One local install initially failed because the default
`/home/agent/.npm` cache was unavailable; using a writable temporary cache
succeeded. Both logs are retained.

Actionlint passes with the existing Depot runner label declared in a temporary
local configuration; without that declaration it reports the three pre-existing
unknown-label diagnostics. No repository lint policy or runner was changed.
The complete failed localized job log is retained as
`/workspace/scratch/pj-sdk101-validation/1b9-wasm-localized-build.log`.
The upstream lane of this same run remains active; it has not been cancelled
or repeated. Grouped publication of these local follow-ups waits for that run.

## CPU diagnostics after a failed serial acceptance result

The ordinary serial suite remains unprofiled and keeps its 2,000 ms Chromium
long-task limit. Its line log and JSON report are retained separately. Only
an actual failed/timed-out Anymal Chromium result admits the diagnostic
replay; an absent, duplicated or Firefox-only result is rejected. A passing
replay cannot change the first step's failure or replace its evidence.

The replay uses the same job's existing acceptance package and fixture mirror.
It performs no compilation, fixture download, credential change or network
fallback. Each lane derives the diagnostic from its own original Anymal
test, with every original assertion retained; unknown test shapes stop
before substitution. This avoids introducing localized probe requirements
into the upstream binary. Every existing mirrored file must match that
source checkout's pinned size and SHA-256. Missing files stop the diagnostic. The browser
keeps the existing offline rules. This does not enable a local replay where
hosted fixtures were previously refused with HTTP 403.

Retained diagnostic output contains CPU samples, a Chromium timeline,
Long Tasks entries with their time origin, timed application console events,
load/model-ready marks, browser/CPU metadata and source/controller/package/
fixture identities, plus hashes and copies of the original and derived specs.
Profiling perturbs timing, so these outputs explain work
and cannot certify the original performance gate. Stripped WASM has no source
names section; some sampled frames may require additional symbol mapping.

The capture path was tested with real headless Chromium on a synthetic local
page, including a deliberately failing DOM-click workload: both original
and replay exited 1, the original report hash stayed unchanged, and the
351 ms synthetic long task appeared alongside 456 CPU samples and timeline
marks. A second source-derived synthetic replay also preserved both original
spec and report hashes, retained exit 1 and captured 432 samples plus the
351 ms task. Five admission/derivation guards and all 45 package-script tests
passed. Both upstream and localized original test derivatives parse and
retain the complete assertion sequences. A
CDP-evaluated busy loop produced samples but no Long Tasks entry, so it was
replaced with a real DOM event for this tool calibration. None of these
synthetic results is an Anymal application performance measurement.
