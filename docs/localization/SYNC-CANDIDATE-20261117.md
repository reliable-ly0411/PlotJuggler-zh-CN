# Independent 4.x synchronization candidate

This candidate preserves the development parent
`1613eaec28e7c4aee13f7efc72f5e2b2d73a35ae` and upstream parent
`5002da40a6499cb99c1073d5b8c611f1e825cb4b` in a normal merge on
`zh-CN-4.x-feat/upstream-main-audit-20261117`. It does not promote development or
stable, create a PR, change tags or publish a package. Authoritative source
metadata now records that upstream ancestry; the localization version remains
an explicit development version.

The 27 conflicts are resolved. Official SDK 1.0.1 sources, Conan revision,
archive and license hashes agree. Native CSV #397 and WASM-source CSV #397 / Log
#391 patches are consumed by the build with their original hashes/negative
guards. [The earlier exact-source report](SDK101-CANDIDATE-VALIDATION-20261117.md)
records passing targeted tests and the retained SDK 0.34.1 -O3/-Werror failure;
the -O2 pass is not a default-optimization or full-product acceptance result.

## Exact-head acceptance plan

- Push triggers the existing Linux/Windows source checks.
- Dispatch `zh-4x-packages.yml` on this branch: real Linux/Windows host builds and
  tests, localized CSV through FileLoader, applicable GUI/window/graphics checks,
  candidate package creation, then clean Linux 22.04/24.04 AppImage/Debian and
  Windows installer/portable checks with screenshots and exact source/package
  identity. This workflow produces Actions artifacts only. Its Linux capture
  prerequisites now precede the unchanged source preflight, so missing Xvfb
  cannot prevent reaching native validation.
- `zh-4x-wasm-candidate.yml` is a branch-scoped copy of the complete browser
  acceptance workflow using ordinary GitHub Ubuntu runners and two build workers.
  It keeps feature defaults, production and ingress builds, deterministic
  packaging, deployment/cold boot, capability probes, Chromium and Firefox tests.
  It does not deploy or publish. Each run records the actual checkout SHA.
- Its independent localized budget counts **every manifest file** using Brotli
  bytes, or identity bytes when Brotli is absent, including presets and Python
  stdlib: **26,000,000 B**. The existing upstream startup budget/script/workflow
  is unchanged. Independent builds now apply 16,932,000 B to the unlocalized
  upstream reference's startup set and 26,000,000 B to the complete localized
  package. Both actual startup and total measurements remain recorded for
  each artifact. This scope change is not a size reduction. No images are removed.

The older WASM candidates 80a97e12, d0734db9 and 54783848 remain preserved on their
branches. Their product changes and old test results are not substituted for
this candidate's tests. All 281 original image files remain byte-identical.

CI conclusions must identify the exact head and run/attempt. A queued or running
job is not a pass, and a dependency failure leaves downstream GUI/package jobs
unrun. Retain failures and artifacts before preparing any corrective commit;
ordinary follow-up commits require fresh checks for the new head. No stable or
development merge, release, tag change or publication is authorized by this plan.

## Retained first-run failure and follow-up

The first published merge `30f844942a2cb45983ec542b180dd360f1b09e71` reached the
WASM production configure in run `44055148511`, job `133942487025`. The unchanged
output-hash guard rejected `data_load_csv/CHANGELOG.md`: `git apply` had discovered
the enclosing host repository from the FetchContent subdirectory and skipped the
source-relative patch paths. This was reproduced in a nested Git checkout.

The follow-up stops Git discovery at the fetched source's parent and clears
inherited GIT_DIR/GIT_WORK_TREE/GIT_INDEX_FILE only for the patch commands. It
keeps every patch and output hash assertion. Real nested-checkout regression
checks cover correct destination/idempotence, corrupt output rejection and
patch-hash rejection; the actual upstream patches also apply with matching
output hashes in that layout. The original failed run remains evidence; only
new-head CI can establish the corrected candidate's result.

The first package run `44055174802` failed on both Linux and Windows in the
focused language build: the standalone profile test compiles `WidgetTuner.cpp`,
whose upstream SVG helper requires Qt Svg. The target now explicitly finds and
links `Qt6::Svg`; no production helper or test is removed.

Follow-up `0e397a325d959e4366b0ce6e3581358fe4575642` passed Linux source checks but
failed Windows source checks in run `44056066526`; package run `44056280554`
retains the corresponding Windows preflight failure and Linux SVG failure.
Git's Windows CRLF policy changed applied archive bytes and correctly tripped
the output-hash assertion. The same two failures were reproduced on Linux with
`core.autocrlf=true` / `core.eol=crlf`. Patch commands now explicitly preserve LF,
and a real Git/CMake regression checks exact bytes, host-file isolation and
idempotent reconfiguration under that policy. All hash assertions remain strict.
The failed package runs completed before cancellation; they were not canceled
or accepted. These corrections require fresh exact-head acceptance.

The full focused Qt 6.12 language build then exposed three stale test keys in
`reviewedTranslationBackport`: upstream's source/side-file replay generalized
the `Data source '%1' ...` diagnostics to `'%1' ...`. Production source and both
catalogs already match and extraction reports zero missing/stale messages.
The regression now asserts those actual live fingerprint/download keys and
their reviewed Chinese translations, plus the corresponding English fallback.
The original local `i18n-ctest.log` (25/26 suites passed) is retained.

## cdf40086 full-build findings and scoped follow-up

At `cdf40086ea732ad272b9d38e00dc2514ede85a1a`, source run `44058340269`
passed both platforms. Package run `44058381807` failed in Linux job
`133953757541` and Windows job `133953757941`: the actual ArduPilot/FileLoader
regression still called `DataReader::latestNumericAt`, removed by host commit
`8a483b49` (#1546). Windows initialization errors were consequences of that same
missing method. The test now obtains the catalog-selected column through
`DataReader::series` and `sampleAtOrBeforeTime`; it retains metadata time and
numeric equality checks and additionally checks the returned sample's time.
It compiles with the real SDK 1.0.1 / Qt 6.12 headers under strict GCC warnings.
This syntax check is not a linked FileLoader execution. The native workflow
builds and runs `ardupilot_import_test` first, then continues the full build and
all existing tests on that same head.

WASM run `44058340229`, job `133953776165`, successfully built and packaged the
production configuration, then failed both budgets. Actual manifest totals:
startup **51,911,378 B**, all localized files **52,668,600 B**. The WASM module
itself is 97,810,200 B identity / **51,665,386 B Brotli**. Browser tests were
skipped, not passed. Artifact `14319564844` preserves the exact commit/tree,
CMake cache and manifest; its ZIP SHA-256 is
`c7fa7f0e4664ef45457c94d3bd49ac0756c7c01477639e2210afa54508fa7610`.

The source chain had omitted reviewed work from the independent candidates:

- `d0734db9`: 31 quality-90 4:4:4 JPEG derivatives and their source/output
  manifest, with original PNG bytes and resource aliases retained. Each source
  PNG and copied JPEG hash was verified before reuse. Their raw source totals
  are 36,550,977 B PNG / 5,661,250 B JPEG; this is **not a new package result**.
- The same candidate's licensed browser CJK subset and regeneration/coverage
  scripts, adapted to keep upstream PlotJuggler Sans as the primary family.
  Both current catalogs are covered; OFL also enters third-party notices.
- `80a97e12`: only the deferred generic-object binding and empty-browser
  custom-widget restore fixes, with the uniqueness/source-identity regression.
  Explicit source qualifiers and exact transactional restore remain enforced.
- `54783848` and `d0734db9`: actual Qt JPEG/atlas painting, glyph shaping and
  real log drag/drop/layout probes, adapted to the current acceptance-only
  probe file. Existing Chromium/Firefox suites remain. Localized assertions,
  console logs and screenshots have their own artifact paths.

The original PNGs, English images, candidate branches, source hashes, licenses,
both budget values and all failure records remain. The former 23,941,450 B
candidate measurement does not validate the new build. Exact new-head native,
WASM size and browser results remain required before any promotion.

## b8ccc771 measured result and independent budget lanes

Run `44073814358`, job `134006521134`, built and deterministically packaged
`b8ccc7712cf2cfecfbc067a989f0ea295db19f0c`: startup 24,578,977 B, localized
total 25,336,199 B. The total passed its 26,000,000 B limit; the combined startup
gate failed by 7,646,977 B and all later browser jobs were skipped. Both sizes
fell by 27,332,401 B from cdf40086 under the same script. The failed run remains
evidence, not a pass retroactively granted by the new workflow.

The verified manifest artifact is `14325164626`, ZIP SHA-256
`fadb3d63de4a0cf66bc0bdacbf27b4dd0b94d95d165cae14bc8350169d1516a2`.
The manifest SHA-256 is
`33fcd52730f8f04714c394c0069e1bb9ab9246ed962e19d6f320ea319618ec81`.

The authorized independent localized budget is now implemented by two real
source builds, described in [the validation contract](WASM-DUAL-ARTIFACT-VALIDATION.md).
The unlocalized reference is pinned by `upstream-baseline.json`; localized
sources are the exact triggering commit. Receipts bind source/tree/controller,
feature configuration, production versus probe kind, and all delivered file
hashes. Browser jobs verify their own acceptance artifact before serving it.
No bytes are subtracted from a shared binary. All functional, serial and Firefox
suites remain, with localized image/font/log/layout probes on the localized lane.

Upstream run `44014675732` at exact `5002da40` measured production startup
15,065,038 B. Its source workflow had independently raised its threshold to
20,000,000 B; this fork keeps the stricter inherited 16,932,000 B threshold on
the new reference lane. Its Chromium functional suite passed 96 cases, but
serial anymal load/reopen failed: longest main-thread task 2403 ms versus the
unchanged 2000 ms assertion (layout restore itself 727 ms). This is a real
performance failure; its cause is not established by that log. The two-lane
workflow retains the assertion, exact serial console log and failure screenshots.

## Native b8 build and stale APBIN identity

Package run `44073828772` completed both actual host builds. The targeted
`ArduPilotFileLoaderTest` ran and passed on Linux (0.32 s, 11:45 UTC) and Windows
(0.57 s, 11:50 UTC), proving the retired DataReader call no longer blocks the
real DSO/FileLoader regression. Both jobs then failed `Prepare verified native
feedback inputs` before the full native suite or packaging: the fixed APBIN
source at `fc6065fd` declares `1.3.0-pj4.rc.1`, but the host baseline still said
`1.2.0-pj4.rc.1`. The generated identity check correctly rejected the mismatch.

The correction aligns the baseline and bundled display metadata with that same
fixed source; it does not change the plugin gitlink, SDK 1.0.1 host pin, license,
independent plugin SDK declaration, or any historical release record. Source
preflight now verifies initialized APBIN source commit/manifest hash, ID, version,
license and display metadata before dependencies and full compilation. The
original generated-manifest ID/version/license and input checksum/platform
checks remain. Native evidence now retains the generated and source manifests
and baseline to make subsequent identity failures directly inspectable.

The failed CI artifacts did not contain the generated manifest itself. A
configure-only replay using the exact SDK 1.0.1 `pj_configure_plugin` helper and
the fixed source manifest produces ID `ardupilot-dataflash`, version
`1.3.0-pj4.rc.1`, ABI major 5 and LGPL-3.0-only. Its SHA-256 is
`3a0ca55bc8d0c0f9b70632f9d601aae163528d886ee116c799f4ff69f64d98b3`.
This replay is not represented as downloaded CI bytes or as a new DSO run.
The two original failures and all downstream skipped GUI/package checks remain.

The APBIN source hash is checked against the exact pinned Git blob. A real
`core.autocrlf=true` clone reproduces Windows JSON newline conversion (23 CRLF
lines, checkout SHA-256 `2e12fb4a5615c723c0bd30d12715414870b8c0034cda4f2ad1cbcb3a226ce899`).
Preflight accepts only the original blob or its uniform LF-to-CRLF checkout;
the file CMake consumes must otherwise match exactly. Real Git fixture tests
cover both forms and reject changed identity bytes and a wrong source hash.
