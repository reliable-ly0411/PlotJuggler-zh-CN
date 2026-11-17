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
removing their probe-only references. Catalog text has been preserved.
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
