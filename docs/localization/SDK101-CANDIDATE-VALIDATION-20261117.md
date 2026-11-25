# Actual compatibility-patch validation — 2026-11-17

> Historical pre-commit validation record. The subsequent independent candidate and CI plan
> are recorded in [SYNC-CANDIDATE-20261117.md](SYNC-CANDIDATE-20261117.md); statements
> about an uncommitted worktree below describe that earlier stage.

The local branch `zh-CN-4.x-feat/upstream-main-audit-20261117` has all 27 textual
conflicts resolved. Its HEAD remains `1613eaec28e7c4aee13f7efc72f5e2b2d73a35ae`,
with pending MERGE_HEAD `5002da40a6499cb99c1073d5b8c611f1e825cb4b`.
There is no new merge commit, push, PR, release or stable-line change.

## Exact SDK identity

The local CMake source URL and `cmake/host-sdk-source.json` now use official SDK
commit `ffd749ab343c3211b5100f124f6c873667b82629`, VERSION **1.0.1**.

| Item | Verified value |
|---|---|
| Commit archive SHA-256 | `d1570047d98d5e582f51cacf354e0072a668c93711abe5e7246ffcb62c079610` |
| Conan export | `plotjuggler_sdk/1.0.1#5d48da533fc9b2250fb4c682e3d6cf25` |
| LICENSE SHA-256 | `d982c2f8dce28e500f42757cdaf17640e3b0e2c1b8f16a1c5814b890c863e55f` |
| LICENSE-APACHE SHA-256 | `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30` |

The actual commit archive was downloaded, extracted and compiled. The unchanged
`scripts/bootstrap_host_sdk.py --archive .../sdk.tar.gz` verified archive,
VERSION, license bytes and the real Conan-export reference successfully. The
Conan requirement and lock, CMake URL/hash, host source record and provenance
guards were changed together. All license/hash assertions remain enforced.
The upstream tag-archive hash `71c108...` is not interchangeable with this
commit-archive hash. No package was uploaded.

## Inputs and executed tests

All builds use GCC 14.2, real SDK libraries, C++20 and warnings as errors. Selected
plugin subdirectories are built through the audit harness from official-plugin
review commit `add9fb325ef346329c379cae1b0bfe1dcd22c228`, with its small local
adaptation to include `widget_log` and the real Qt tests. This is not an aggregate
plugin or PlotJuggler application build. Dependencies: SDK Conan graph JSON 3.12.0,
fmt 12.1.0, fast_float 8.1.0, GTest 1.17.0; date source
`f94b8f36c6180be0021876c4a397a054fe50c6f2`, timezone library OFF.

| Exact source combination | Build/test result |
|---|---|
| Native CSV `ba6ee417d91a01aae778a0ec3a4443a024671123` + original localization patch + `native-csv397-after-localization.patch`, SDK 1.0.1 | Release `-O3 -Werror`; 8/8 CTest, **128/128** cases PASS |
| WASM-source snapshot `598e966243ef6e75b29cadd5d145559d3eb504c2` + `wasm-csv397.patch` + `wasm-log391.patch`, compiled as native DSOs with SDK 1.0.1 / official Qt 6.12.0 | Release `-O3 -Werror`; 7/7 CTest, **138/138** cases PASS |
| Same localized CSV candidate, independent SDK 0.34.1 source `4d59e7de81455afe73a77051075e8fb4b9f6b0fd` | Release `-O2 -Werror`; 8/8 CTest, **128/128** cases PASS; see initial failure below |

The 128 CSV cases are parser 49, real DSO path tests 12, real DSO runtime language
13 in each of five fresh processes (zh_CN, zh_TW, en_US, unknown, empty), and #397
source tests 2. All-invalid input fails without Continue or committed rows;
mixed input preserves the Continue/Abort path and corrected prompt.

The 138 cases are CSV paths 12, parser 56, source 2; Log core 39, model 4, real
Qt Widget DSO load/panel tests 20; and SDK null-sample view tests 5. Log tests use
`PJ::WidgetLibrary`, real SDK service bridges and Qt's offscreen platform. The
widget-host callbacks are a test host, not the full PlotJuggler runtime. All
required DSO exports passed the ELF guard, with zero GNU UNIQUE symbol leaks.

The SDK 0.34.1 **initial `-O3 -Werror` build failed** in its existing
`pj_base/src/parser_module_abi.cpp`: GCC 14 emitted `-Wfree-nonheap-object` through
an inlined vector allocation/deallocation path. The secondary `-O2` build kept
warnings fatal and passed; the failed log is retained. This does not establish
that the original `-O3` package build passes. No warning suppression or SDK source
patch was applied. Its SDK pin remains separate from the host's 1.0.1 pin.

## Additional independent APBIN evidence

The independent APBIN audit reported these completed results (not rerun
by this worktree): under SDK 1.0.1, registry 1.2 original ZIPs each passed 102
checks on Linux/Windows; #339 draft 1.3 original ZIPs each passed 121 checks on
both platforms. Their hashes matched registry, release assets and SHA256SUMS.
Source candidate `90afd65ca21c452d1c1ab87e19d4057f9dfe60e8` passed the two-platform
run `44049992795`. Full GUI/marketplace installation remains untested. These
results support the host dependency decision but do not change the existing
APBIN gitlink, standalone SDK pin or historical archive identities.

## Production consumption and integrity checks

- Native `csv-loader.patch` is now the combined patch; SHA-256
  `6b4d6bbb54c6ecec4c3a2b20d86a5228954db8fb1f0ffa06323f48c939324a01`.
  Source-lock and localization provenance agree. All four changed output-file
  hashes match the tested candidate. The builder's exact test allowlist now
  requires `csv_source_test`; missing that test fails the gate.
- WASM fetch still pins the exact 598e9662 archive. The CMake compatibility step
  applies only the two recorded patches, validates their hashes and each changed
  output file, and runs before plugin definitions are included. An actual clean
  source application and a second idempotent invocation passed. A deliberately
  corrupted source was rejected. The result bytes match the DSO-tested source.
- Original PNG and all other resource image bytes remain unchanged (281 files).
  The upstream budget is 16,932,000 B; the separate localized allowance remains
  26,000,000 B. No package-size result is claimed.

## Source checks and remaining acceptance

- Python suite: **777 tests, 53 skipped, zero failures/errors**. The previous five
  failures/errors were resolved; Xvfb/X11 tools were extracted into the cloud
  scratch directory, with no user desktop interaction. The package-capture
  tests use a synthetic window and do not establish final-package acceptance.
- Host source/provenance and branch checks PASS. Exact prerelease validation was
  reused from #70, without changing its branch or discarding its negative tests.
- Qt 6.12 lupdate full extraction PASS: zh_CN and zh_TW each 2154/2154, no missing,
  stale or unfinished entries; placeholders/plurals/rich-text assertions pass.
- Full host build, its real FileLoader/history integration tests, Windows, macOS,
  WebAssembly, heavy official plugins and final-package acceptance are **unrun**.
  The older SDK `-O3` failure remains open as described above.

The pending merge must not be committed/promoted or released as accepted on this
basis. Before completing that merge, update the authoritative upstream-baseline
parent/commit fields to the actual integration result; `pending_sync` currently
records the target while the committed ancestry remains unchanged.

## Reproduction evidence

Cloud directory: `/workspace/scratch/pj-sdk101-validation/`. It contains the exact
source archives, prepared plugin trees, Conan graph and exported SDK, audit
CMake harnesses, Qt kit, dependency sources and build trees. Main logs:

- `bootstrap-host-sdk.log`, `sdk-export.log`, `conan-install.log`
- `configure-native.log`, `build-native.log`, `ctest-native.log`
- `configure-wasm-native.log`, `build-wasm-native.log`, `ctest-wasm-native.log`
- `build-native0341.log` (failed -O3), `configure-native0341-o2.log`,
  `build-native0341-o2.log`, `ctest-native0341-o2.log`
- `compat-application.log`, `python-final.log`, `package-acceptance.log`,
  `translations-final.log`

The `build` directory was reused sequentially: it currently contains the
SDK 1.0.1 WASM-source-native DSO run; `build0341` holds the independent native CSV
run. The native SDK 1.0.1 test output is retained in `ctest-native.log`.
