# Native regression follow-up, 2026-11-17

The input is candidate `3c471fc572bb77d06d43f0f77cd3a27bb6338a0d`,
packaging run [44098684851](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/actions/runs/44098684851).
Both platforms built the application, ran the real ArduPilot import regression,
and passed `Prepare verified native feedback inputs`. Neither produced an
accepted package: native regression failures stopped the later packaging gates.

The fixes are based on `2459f63bf38dc0b7eddc2e8588197672afdd0ad8`, which also
contains the separately reviewed browser language assertions. No production
source, SDK/plugin pin, resource, budget, or workflow assertion changes here.

## Original failures and decisions

| Test | Linux | Windows | Resolution |
| --- | --- | --- | --- |
| `PluginDisplayMetadataTest::installedApbin` | failed | failed | Compare the admitted DSO version with the locked baseline, retaining fixed ID, author, license, repository, website and all three display languages. |
| `ScrubberBase.ReturnCommitsAndClosesEditorWithoutReopening` | failed | passed | Wait for the exposed window to become active before sending keyboard input. Require initial focus as well as all original commit, close, focus-return and reopen assertions. |
| `PreferencesLanguageTest.MinimumSizeKeepsTranslatedAppearanceControlsReachable` | failed | failed | Test the actual minimum width introduced by upstream `18ff9b061a59f3dc7dfe5af8290f6bf0986ffaa5`; retain the 420 px lower bound, 300 px height, scrolling, label/field geometry and English/Simplified/Traditional coverage. |
| `SplashMemePool.EmptyPoolFallsBackToTheSeriousSplash` | failed | failed | Check the actual English image pool, not all files including `zh_CN.json`. Explicitly request memes in English, check the nonempty serious fallback and its dimensions, then verify the original pool is restored. Use private settings. |
| `RecipeGraphTest.PythonScriptIsCompiledOncePerRevision` | passed | failed | Retain shared ownership of the original compiled handle across replacements. Comparing a freed raw address allowed allocator reuse to look like an unchanged handle. Revision, same-input reuse, changed-input identity and compile-event assertions remain. |

Linux: 6,257 CTest entries, four failed. Windows base suite: 5,743 entries,
four failed; later QRhi 217, native-window 2, widget-regression 9 and
range-slider 4 entries passed. The latter subsets are not an additional count
of unique tests. Linux X11/Wayland lifetime and all package/clean-package gates
after the failed step were not executed.

The generated APBIN identity is `ardupilot-dataflash` / `1.3.0-pj4.rc.1`,
matching `upstream-baseline.json` and source pin
`fc6065fd64305479946552a757d78e6afdd2c506`. The failed metadata assertion alone
still expected `1.2.0-pj4.rc.1`. The Linux feedback receipt binds the actual DSO
to SHA-256 `6af38f2c259f8d9bdbf00e471a64e3d545a6a277c13b49001a68610199f831c6`.

## Local verification and limits

Cloud-only focused builds use Qt 6.12.0 and SDK 1.0.1 source
`ffd749ab343c3211b5100f124f6c873667b82629`, with `-Wall -Wextra -Werror`.
The metadata/SDK harness uses `-O2 -DNDEBUG`; it does not reinterpret the
previous unrelated old-SDK `-O3` diagnostic as a passed check.

- Real APBIN DSO plus marketplace admission/UI: original assertion reproduced
  the exact version mismatch; repaired suite passed 28/28, with no skips.
- Actual splash sources/resources: original suite 9 passed / 1 failed;
  repaired suite 10/10. No image file or QRC entry was removed.
- Actual scrubber implementation: original isolated X11 case failed both
  Return and Enter focus checks; repaired case passed. Offscreen before/after
  both passed; the repaired full scrubber suite passed 8/8. This distinction
  matters: offscreen alone did not reproduce the CI failure.
- Modified recipe test translation unit compiled with the real SDK headers
  and `PJ_PYTHON_TEST_PROBE`; this is compilation, not execution of embedded
  Python. Full runtime execution and the actual Preferences dialog regression
  require the next native CI run.
- Python source suite: 801 discovered, 31 skipped, initially one environment
  error. `dpkg-deb` rejected a temporary `DEBIAN` directory created with mode
  0700 under process umask 077. The unchanged failing test passed under umask
  022. The original failure and focused replay are retained separately.
- Pre-commit checks and `git diff --check` passed after formatting.

Evidence is retained under cloud scratch
`/workspace/scratch/pj-sdk101-validation/native-regressions/`, with original
CI reports in `native3c-linux-reports/` and `native3c-windows-reports/`.
Downloaded report ZIPs were verified against the GitHub artifact digests:

- Linux `14339594584`: `c31f3cb177bd9a8d694bf1fa0b07c7b33ac72ab9ed5d234c6b139641035c1a57`.
- Windows `14340889854`: `81f019f7ac367fa41343f6d864bd621e8b908f84d82242590ed0c3ec4472f9ff`.

These focused results do not establish full native, browser, GUI, installer,
marketplace-installation or final-package acceptance. Stable/development
promotion, publication and tag changes remain outside this candidate step.

## Exact-head 1b9 preflight failure and catalog repair

The five native changes above were published in commit
`e407a6b2e72f5986723e4e33152df96ba75eb4c6`, followed by the browser console
framing/split-menu probe repair in candidate
`1b9af0c7b675c53b5a2b2967f1e500aff5495773`. Source run 44118271684 passed
on Linux and Windows. Its catalog-only validation did not check source drift.

Native run [44118377038](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/actions/runs/44118377038)
failed on both platforms before application configuration: full Qt extraction
reported `QObject / Reselect source` and `QObject / Select source ` as stale
active entries in each catalog. The old probe references had been removed.
The earlier local extraction also returned 1; zero missing translations was
incorrectly treated as success at that checkpoint. Both full CI logs and the
original local failure log remain preserved. None of the five repaired native
regressions ran on this head; they remain unverified in full native CI.

The minimal repair marks those four catalog records `vanished`, preserving
their translated text and history. Production `PJ::MainWindow` source-selection
translations remain active. No checker or assertion was changed. From this
isolated worktree, pinned Qt 6.12.0 full extraction now exits 0 with 2,151/2,151
active messages per language, zero missing and zero stale. The unchanged
translation-checker regression suite passes 11/11. A fresh standalone i18n
build compiles the actual language loader, catalogs, resource linkage, bundled
plugin UI mappings, splash and related fixtures; CTest passes **26/26**, exit 0.
This is a focused language/runtime verification, not a full application build.

At 2026-11-17 15:58 UTC, dual WASM run 44118271359 still builds exact 1b9.
No run has been cancelled or duplicated. The catalog correction is retained
on the isolated native-regressions branch pending grouped publication after
that existing run finishes; stable/development still point to
`1613eaec28e7c4aee13f7efc72f5e2b2d73a35ae`.

## Exact-head 318 native execution and development-package identity

Candidate `31804af17641e54ebfc17ac27691f0cfc37b74ed`, native run
[44125850938](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/actions/runs/44125850938),
built both full applications and passed all executed native tests. CTest's
100% success summary includes skipped entries; downloaded JUnit gives:

- Linux: 6,257 main entries, 6,154 passed and 103 skipped; independent X11
  and Wayland window lifetime runs each passed 2/2.
- Windows: 5,743 base entries, 5,643 passed and 100 skipped; QRhi 217 entries,
  214 passed and 3 skipped; native windows 2/2. The combined report has
  5,962 entries, 5,859 passed and 103 skipped. Separate widget 9/9 and
  file-dialog 4/4 runs overlap existing cases and are not extra unique tests.
- Both platforms passed full-source Qt language extraction and 26 language
  CTests, and the actual ArduPilot import 1/1 before the full build completed.
- All five previously failing cases executed successfully on both platforms.
  Embedded output confirms `installedApbin()` and
  `SplashMemePool.EmptyPoolFallsBackToTheSeriousSplash`; the recipe, scrubber
  and preferences entries have no skip, failure or error records.

Both jobs then failed `Validate release identity`: the strict release mapper
rejects the actual application version `4.1.0-zh.1.dev.3`. No original package,
clean installation acceptance or final manifest was produced. This is not
whole-package acceptance. The strict release rejection remains appropriate;
the build-only candidate workflow needs explicit development package mapping,
with no tag and `publishable=false`, as documented in `RELEASING.md`.

Verified report ZIPs (full logs and extracted JUnit retained in cloud scratch):

- Linux `14354037464`: `6a51367e5c9b12b3561b64a0d482cf8ec4cd7e9dd978acc8523f3af6dbb46568`.
- Windows `14353272383`: `e6a4f788976ff4ab7734bbc2092a5d65ec6813327900989e88986533cb1ec93d`.

Development mapping validation covers explicit opt-in, unchanged release
mappings, rejection by release promotion, dpkg ordering and a real generated
Debian control field/file name. Synthetic final manifests retain all six
report, eighteen screenshot, four artifact and byte-integrity gates for both
release and development inputs. Actual IFW construction, staged payload and
clean-package acceptance remain to be run on the new exact commit.

## Exact 2627 Linux font-notice staging failure

Native run [44141874689](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/actions/runs/44141874689),
Linux job 134246539597, finished its application build and native checks.
The downloaded JUnit artifact (ID 14359338470, ZIP SHA-256
`e85e888f91461e6445d8de048edf31943e5a8dd1d066fed092afd4542f7ea642`)
records **6,154 passed, 103 skipped, zero failures/errors** across 6,257
entries. ArduPilot's early import regression passed **1/1**; the complete
log also records X11 and Wayland checks **2/2 each**. These are exact-head
results, not reuse of the preceding candidate's native tests.

At 19:00:40 UTC, `prepare_payload.py` failed copying
`resources/fonts/NotoSans/OFL.txt`. Upstream now embeds the two
`resources/fonts/PlotJugglerSans/` faces. The prior development-version
mapping gate was crossed; the next failure is this stale font-license path.
No original installer or clean-install acceptance ran after it.

The fix stages the current UI font's complete OFL and README under its real
family name. Clean-package verification explicitly requires both, and the
existing dependency file manifest continues to hash their full bytes. The
separately pinned Noto CJK fallback, its font/license hashes, all source-image
resources, application tests and package gates remain intact.

A regression exercises staging against the real tracked resource/QRC tree,
with a synthetic APBIN payload and an explicit stop before remote downloads.
It reproduced the same missing old path before the fix, then verified both
complete notices byte-for-byte after it. The four relevant offline acceptance/
version/manifest suites pass **105/105**, with no skips, including the real
Xvfb capture mechanics check. The initial local invocation lacked Xvfb in
PATH; the next had the existing tools but missed the test-module import path.
Both nonzero logs are retained. The final invocation uses the already installed
cloud tools and correct test import path; no test was disabled. Pre-commit
and whitespace checks pass. This targeted result does not certify a complete
installer. Windows remains on its existing run at this checkpoint.

Windows job 134246540331 subsequently completed with the same stale
`NotoSans/OFL.txt` copy failure at 19:25:15 UTC. Its verified report artifact
(ID 14362820935, ZIP SHA-256
`64ee6fac29eb27c745a93685600e8387c629c9376c668473237d14ac5b9481ce`)
records **5,859 passed, 103 skipped, zero failures/errors** in the combined
5,962-entry native report. The constituent headless 5,743 and QRhi 217 reports
are not added again to that total. The extra widget and file-dialog checks
passed **9/9** and **4/4**, and the early ArduPilot import passed **1/1**.
All five previously failing native regressions appear as executed passes in
both platforms' JUnit output. Both platform builds and the standalone language
checks completed successfully.

The workflow ended failed; `linux-clean`, `windows-clean`,
`windows-portable-clean` and `release-manifest` were explicitly skipped.
Neither platform produced accepted original packages in this run. The same
font-notice fix covers both failures. At local commit
`9a90f32e90d0985a160b334c6b6ee12ce7ae4eef`, the complete source preflight
ran 807 entries: **776 passed, 31 platform/environment skips**, zero failures
or errors. The focused 105-case result above is a subset, not an additional
105 unique tests. Provenance and both translation catalogs also pass; the
local catalog-only command does not claim fresh lupdate coverage.

## ca245298 source-only checkout regression

Source run 44158751589 failed on Linux job 134306517146 (807 entries, one
error, 24 skips) and Windows job 134306516805 (805 entries, one error,
33 skips). The new font regression tried to read the APBIN submodule's
manifest, while these source-only jobs deliberately do not initialize
submodules. The real native workflow does initialize them and crossed its
lightweight preflight; its application and package checks were still running.
This source-test failure is separate from the fixed production OFL path.

The test now isolates its unrelated APBIN input/notice copies in an explicitly
synthetic temporary source tree. It still copies the actual tracked UI fonts,
complete OFL, README, QRC and host-version inputs, exercises the real staging
function, and preserves every font/QRC assertion. Real native plugin identity,
license, hash and source assertions are unchanged. No missing dependency is
converted into a skip, and no additional checkout/download is required.

A source archive without any initialized submodule first reproduced the error.
After the test repair, the same check passes there. Reintroducing the old
`resources/fonts/NotoSans` staging path in that isolated snapshot still fails,
showing that the original font regression remains detected. The full local
source preflight then passes 807 entries (776 passes, 31 platform/environment
skips); pre-commit and whitespace checks pass. Both original CI logs and the
three isolated-check logs are retained under the cloud validation scratch
root. Existing ca245298 native and WASM runs were not cancelled or repeated.
## Firefox editor evidence after ca245298

WASM run `44158751480` reports success because its existing Firefox editor step
is non-blocking. Its full logs still contain two real failures:

- Localized job `134315471373`: the transform completed, but the maximum browser
  heartbeat gap was `206.4200000000019 ms`, exceeding the unchanged `100 ms` bound
  at `editors.spec.js:575`. Assertions after that point did not execute.
- Upstream job `134318627239`: materialization remained pending through the
  unchanged `60,000 ms` poll at `editors.spec.js:565`. Heartbeat and final-series
  assertions after that point did not execute.

Both Firefox functional shards passed (50 and 42 tests, with seven existing skips
in shard two). Chromium passed 96 functional and five serial tests in each lane.
These successes do not erase either editor failure or historical Anymal/Python
performance failures.

The result probe reads transform recipe metadata and custom-tree coordinates; it
does not traverse the 30,000 samples. This rules out the suggested full-series
scan in that probe, but does not identify the failing main-thread work. No CPU
trace was retained for those failed editor measurements. The local pinned
Firefox attempt stopped before app launch (`Sandbox: writing /proc/self/uid_map:
EROFS`); no sandbox relaxation is part of this investigation.

The prepared diagnostic keeps the original editor run, JSON report, exit status,
assertions and timeouts. Only a failed/timed-out original Firefox transform admits
a separate replay of that lane's own test and already-verified acceptance package.
The derivative adds phase marks and failure-safe console/heartbeat retention; it
does not substitute the controller's product tests into the upstream lane.
Firefox startup sampling uses Mozilla's documented `MOZ_PROFILER_STARTUP`,
`MOZ_PROFILER_STARTUP_FILTERS` and `MOZ_PROFILER_SHUTDOWN` variables
([Mozilla documentation](https://firefox-source-docs.mozilla.org/networking/http/logging.html#capturing-a-profile-with-logs-at-startup)).
No symbol download, fixture fetch, rebuild, sandbox override or credential fallback
is added. Sampling perturbs timing; replay results cannot replace original failed
acceptance. Missing profile output is a diagnostic failure, not success.

Local checks cover failure-only admission, byte-for-byte retention of each lane's
original spec after removing diagnostic additions, drift rejection, failed-page
evidence retention, and child-process exit/identity preservation with a stand-in
launcher. This is not a Firefox runtime/profile validation. Actual Gecko profile
capture and root-cause attribution remain unverified; the prepared diagnostic is
not present in the already-running `f4f0fcb0` jobs.

## ca245298 Linux CSV warning expectation drift

Native job `134306726219` in run `44158806003` passed 6,154 native tests
(103 additional entries skipped), the early ArduPilot import and both two-case
X11/Wayland lifetime suites. Font/license staging and the pinned official plugin
rebuilds then passed. The following real FileLoader gate failed all three language
CTest entries: each passed four cases and failed the three short-warning
Continue/Abort/Close cases, at the exact body equality assertion on line 114.

The #397 compatibility patch already uses the generic skipped-row introductory
sentence in both the actual CSV DSO and its independent DSO language tests. The
host's FileLoader test still expected the column-count-only introduction. Its
English, Simplified Chinese and Traditional Chinese expected strings are now
aligned with the pinned `csv-loader.patch`. The exact full-body comparison,
title/buttons, long-body checks, cancellation paths, data values and time axis
remain unchanged. No plugin implementation or source/SDK pin changes here.

The actual affected C++ test translation unit compiles with Qt 6.12.0, SDK 1.0.1
headers and `-Wall -Wextra -Werror`; the CSV acceptance/owned-output Python subset
passes 10 tests. This local check is compilation and validation-harness coverage,
not a linked real FileLoader rerun. The original package and clean-install steps
were skipped after the CSV gate failure and still require exact-head CI.

## f4f0fcb0 results and retained Firefox sampling

Source run `44166438824` passed on both platforms. Dual-WASM run `44166437653`
completed under the existing non-blocking Firefox-editor policy, not whole-suite
acceptance. The localized lane passed 96 Chromium functional cases, five serial
cases, five layout/glyph cases, the 64-image JPEG case, and four cases in each of
English/Simplified/Traditional Chinese. Its Firefox shards passed 50 and 42 cases
(seven existing skips), both editor cases and each four-case language group.
The upstream lane passed the same functional/serial suites, but its first Firefox
shard's transform heartbeat measured `179.34000000000015 ms` against `100 ms`.
That failure remains part of the result despite the green job conclusion.

The actual upstream production startup is `15,064,879 B` against `16,932,000 B`.
The localized production startup is `24,580,257 B`; its full package is
`25,337,479 B` against the separate `26,000,000 B` limit. Forty delivered files in
each production package were rehashed against its receipt. Both actual notices
contain the PlotJuggler Sans OFL. This does not establish native clean-install
acceptance or erase earlier Anymal/Python/editor failures.

The preceding ca245298 Windows job `134306725599` subsequently completed: its
combined native report contains 5,962 entries, 5,859 passes, 103 skips and no
failures. Font/license staging and official-plugin rebuilds passed, followed by
the same three-language CSV short-warning expectation failure as Linux. Each
language passed four cases and failed Continue/Abort/Close at the exact body
comparison; long warnings and empty input passed. Neither platform reached
original-package or clean-install validation. CSV fix `453c3a81` is required on
the next candidate; the already-running f4f0fcb0 native jobs cannot include it.

Independent diagnostic run `44175824162`, controller
`82b5a916011543048434fa40d293e3f1745ba66e`, reused the retained upstream f4 and
localized ca acceptance artifacts without rebuilding the application. Original
archive hashes, source/controller identities and acceptance receipts passed
before replay. Both sampled replays failed the unchanged 60-second pending poll
and wrote real Gecko profiles, console records and heartbeat histories. The
diagnostic archive SHA-256 values are:

- Localized artifact `14368933562`:
  `44dfc45b87fea8198309d929d2b8ca837160cb6d9788117cf864e255ecfb2a05`.
- Upstream artifact `14369672846`:
  `9062b19b934f3a163d618d81a70dd490609680efdedde85bc0cf17e6693dd0eb`.

Each page's phase mark was aligned with the same UserTiming marker in its own
Gecko process. The localized maximum gap was `258.72 ms` (255/258 samples contain
WASM frames); the upstream maximum was `239.62 ms` (238/240). After the first
three seconds until failure, 56,041/56,951 localized and 56,135/57,062 upstream
main-thread samples contained `PollWrapper`, while only 69 and 68 respectively
contained WASM frames. Both pages continued heartbeat and status reporting,
reported `materializing=1`, and recorded no page error.

Thus these sampled timeouts do not show a continuously busy replay for all
60 seconds. Initial WASM work and later pending-without-progress need separate
diagnosis. The source arms a zero-interval Qt materialization timer; whether that
timer fires, stops, or loses delivery is not exposed by the retained observation.
The stripped WASM indices do not identify exact C++ hot functions without the
same binary's symbol map. No timer or runtime behavior is changed on this basis.
Sampling changes timing and cannot replace the original 179.34/206.42 ms failures
or the original unsampled pending timeout. Future failure-only diagnostics retain
the original JSON result and all assertions before the separate sampled replay.

## Isolated WASM zero-timer follow-up

The pinned Qt 6.12.0 sources expose a concrete continuation hazard:
`QTimerInfoList::activateTimers()` delivers a zero-interval callback but excludes
it from its returned activation count. `QEventDispatcherWasm::sendTimerEvents()`
rearms its native timer only when that count is positive. A native executable
linked to the actual Qt 6.12.0 private timer-list implementation, with the same
WASM rearm predicate, measured:

- 0 ms: one callback, returned count zero, timer still pending, no rearm; the
  three-callback progress assertion failed with exit 1.
- 1 ms: three callbacks, returned count one, timer pending and rearmed; the same
  progress assertion passed with exit 0.

This is a native mechanism probe, not a compiled-WASM/browser reproduction.
The isolated change gives only the WASM materialization timer a positive 1 ms
interval. It does not alter per-slice budgets, data, notification intervals or
the existing 100 ms/60-second browser assertions. The native unit test explicitly
pumps `processEvents`, so its success alone cannot cover the browser's need to
rearm a native wakeup. The initial >100 ms WASM work remains a separate issue.

The timer probe compiled with `-Wall -Wextra -Werror`. A separate strict syntax
attempt for both branches of the whole `DataProcessorService.cpp` stopped on
its pre-existing `Dependent::transform_key` missing-field-initializer warning
at the unchanged processor-removal code. That failure is retained, not suppressed;
it is not evidence of a successful whole-file compile or browser validation.
Pre-commit passes. The isolated change is not in published candidate e44a1a53
or its running CI and still requires exact-head browser validation.

The strict compile blocker is resolved separately by explicitly initializing the
filter-dependent record's unused `transform_key` to its existing empty value.
Both native and `PJ_TARGET_WASM` branches of the actual full translation unit now
compile with `-Wall -Wextra -Werror`; no warning flag was disabled. These are
native-compiler object checks, not an Emscripten link or runtime result. The first
strict failure log is retained alongside the passing compile log.

The independent `zh-4x-wasm-timer-validation.yml` entry builds this branch as one
complete localized source/controller identity through the existing reusable
WASM lane. It preserves the production total budget, production cold boot,
acceptance probes, Chromium serial/functional cases and Firefox suites, including
the existing editor failure reporting and failure-only sampling. It neither
patches the upstream reference checkout nor cancels the e44a1a53 candidate runs.
This isolates the product change while the baseline candidate continues. Browser
results must be read from the new exact run; the timer probe does not establish
that the 100 ms first-task gate passes.

## Exact timer candidate browser result and remaining long task

Independent source `19cd52c895203e8ae3618dfe578f2e0758771348` passed both
source-check platforms in run `44179927537`. WASM run `44179927751` rebuilt
`DataProcessorService.cpp` in both production and acceptance configurations.
Its production receipt and all 40 actual package files were rehashed: startup
24,580,407 B, complete total 25,337,629 B below 26,000,000 B. The full UI font
OFL is present. This does not replace the separate upstream startup gate.

Chromium passed 96 functional, five layout/glyph, one 64-image JPEG, five serial
and four cases in each of English, Simplified and Traditional Chinese. Anymal
load/reopen longest tasks were 1,313/1,375 ms, below the unchanged 2,000 ms limit.
Firefox passed 50/42 functional cases (seven existing skips) and four cases per
language. The editor suite passed one and failed one: the transform completed
within its existing deadline but its heartbeat gap was **194.78 ms**, above the
unchanged 100 ms bound. Its later full-output assertions were therefore not
executed. The workflow's success conclusion reflects its existing non-blocking
editor policy and is not whole-suite acceptance.

Failure-only sampling on the same acceptance package also completed the replay:
the before-OK/materialized marks were 1,011.98 ms apart, with a 234.52 ms maximum
heartbeat gap. Of 233 samples in that gap, 231 contain WASM frames. This is no
longer evidence of a pending replay idling for 60 seconds. The stripped binary
contains no function-name section, so the sampled indices do not yet identify
the responsible C++ functions. Original and diagnostic failures remain separate.
The Firefox evidence ZIP has SHA-256
`9d029610d2a65b4516ae7628b28b9a402c2ca3446bb672734211d49b32588d76`.

The independent timer workflow opts into an acceptance-only Emscripten
`--emit-symbol-map` link. Production configuration and both budget scripts are
unchanged. The sidecar is retained outside deployed packages, hashed with the
exact acceptance binary in the receipt, checked after download in every browser
job, and preserved with Firefox evidence. Missing or changed maps fail receipt
validation. This is diagnostic evidence, not a performance fix or a deduction
from measured package sizes. Pinned Emscripten 5.0.5 supports the option in
[`emcc.py`](https://github.com/emscripten-core/emscripten/blob/5.0.5/emcc.py) and
emits the final function-index map in
[`tools/link.py`](https://github.com/emscripten-core/emscripten/blob/5.0.5/tools/link.py).

Candidate `e44a1a53` remains unchanged. Its native run `44178541842` has started
on both platforms; new-head CSV FileLoader and clean-install results are still
pending. Previous f4 native run `44166480802` ended with zero native XML failures
(Linux 6,154 passed/103 skipped; Windows 5,859 passed/103 skipped), then failed
both real CSV validation steps on the old warning introduction. Both original
package and clean-install stages were skipped. That old failure is preserved;
e44 contains the exact three-language expectation correction, awaiting execution.


## Retained symbolized replay and panel parsing candidate

WASM run `44193448684` at 31746852 passed Chromium 96 functional/five serial,
five layout/glyph, one JPEG64 and four cases per language, plus Firefox 50/42
functional, two editors and four cases per language. Original Anymal load/reopen
longest tasks were 1,305/1,279 ms. The original editor JSON and byte hashes are
retained; the failure-only profile correctly skipped this passed suite.

Independent diagnostic controller `ced01083af7316e93a10158c0cac72de9d989fc5`
(run `44200970606`, job `134454623588`) reused the exact 31746852 acceptance
archive and original passed report, verifying archive and per-file receipt hashes
before serving. Its explicitly labeled single sampled replay failed the unchanged
100 ms heartbeat assertion at **158.78 ms**, after materialization completed.
This diagnostic does not replace the normal run or erase prior 19cd52c8 failures.
Its archive SHA-256 is
`a5c3c854972ac562be8e354692d66920907c0402fa79e5ba9cfe9ad81aa0b62e`.

The exact receipt-bound symbol map resolves 155 samples in the longest gap:
92 include `PanelEngine::Impl::runTick`, 63 include `applyAndDiff`, 36 include
`QWidgetRepaintManager::paintAndFlush`, and 16 include incremental materialization.
These inclusive stack counts are not disjoint timings. Parsing stacks in
`applyAndDiff` reach nlohmann's number lexer and libc's `strtod`/`__floatscan`.
The positive materialization timer fixed the observed pending-replay symptom;
this evidence identifies additional panel/paint work on the same main-thread task.

The host-only candidate reuses SDK 1.0.1's existing `WidgetDataView::raw()` tree
for the owned diff copy instead of parsing a complete numeric preview twice.
Malformed data still returns without replacing the previous typed view: only the
SDK's ambiguous empty-object fallback needs a separate validity check. The diff
copy can consume commands without changing the full typed view. SDK pin, plugin
ABI, every preview sample, one-shot handling, tick intervals and budgets remain
unchanged. Other painting and parsing costs remain to be measured on the new head.

Four focused native tests pass: malformed inputs (including numeric overflow),
valid empty/non-object JSON, command/view independence, and all 2,000 preview
samples with exact integer-range preservation. Both actual `panel_engine.cpp`
conditional branches compile with `-Wall -Wextra -Werror`. These are native GCC
object builds with/without `PJ_TARGET_WASM`, not an Emscripten link or a full GUI
runner pass. The first local focused build stopped because its scratch CMake
harness linked an undefined gtest_main target; its failure log is retained. The
corrected harness uses the installed pinned gtest archive and passes. Browser
performance and the complete panel GUI suite remain unverified for this fix.
