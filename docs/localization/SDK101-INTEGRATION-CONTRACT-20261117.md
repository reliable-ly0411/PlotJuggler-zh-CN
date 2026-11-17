# SDK 1.0.1 integration contract — 2026-11-17

> Historical pre-commit validation record. The subsequent independent candidate and CI plan
> are recorded in [SYNC-CANDIDATE-20261117.md](SYNC-CANDIDATE-20261117.md); statements
> about an uncommitted worktree below describe that earlier stage.

This is a dependency handoff for the uncommitted product-sync worktree. The local
host tuple now records official SDK **1.0.1**, commit
`ffd749ab343c3211b5100f124f6c873667b82629`; both build/lock conflicts are resolved.
The actual three candidate patches passed native DSO checks and are consumed by
the local build paths. See [fresh validation and exact hashes](SDK101-CANDIDATE-VALIDATION-20261117.md).
No merged/published application acceptance follows from those checks.

## Exact external evidence and dependencies

- [APBIN review](https://github.com/reliable-ly0411/plotjuggler-apbin-plugins/blob/90afd65ca21c452d1c1ab87e19d4057f9dfe60e8/sdk4/docs/SDK_1_0_1_COMPATIBILITY.md):
  candidate `90afd65ca21c452d1c1ab87e19d4057f9dfe60e8`, SDK
  `ffd749ab343c3211b5100f124f6c873667b82629` (1.0.1). Reported parser 2147,
  ABI 121, strict sanitizer and both directions of SDK 0.34.1/1.0.1 loading passed;
  real BIN has 1940 series / 444443 samples. Bootstrap ABI is 5 and data-source
  protocol is 4. The standalone installed-SDK default remains EXACT 0.34.1;
  a host-created `plotjuggler_sdk::plugin_sdk` target is a separate build route.
- [Official-plugin review](https://github.com/reliable-ly0411/pj-official-plugins/blob/add9fb325ef346329c379cae1b0bfe1dcd22c228/compat/sdk101/REPORT.md):
  report `add9fb325ef346329c379cae1b0bfe1dcd22c228` tested official plugin
  `5b6cc5c1e55afe4695e5ac58ef5f835bcc52e5a9` against that exact SDK.
  Six lightweight plugins built; 11 CTest / 218 cases passed. The static
  feature-floor audit covered 35 manifests, not 35 runtime-tested plugins.
- SDK 1.0.0 `f9390f7a5d94c377247e38680a6dbd52b43319f2` to 1.0.1 has no
  header/runtime change according to that independent audit. SDK #226 is included.
  The fresh worktree checks additionally passed five real SDK null-sample tests
  and verified archive/VERSION/licenses/Conan export. Full current-host tool
  behavior still needs its native integration tests.
- Host target is `5002da40a6499cb99c1073d5b8c611f1e825cb4b`; its SDK update is
  `057df4ba9bfd9a9459f89fc6289a294c5887c39c` (#1589), and history count fix is `652b0726d16aad0de8bb0c494da474eb92bc3465` (#1556).
- Official CSV UTF-8 paths: `4d223f6948fcabe18ad07afcd453a0f84d823de8` (#369).
  CSV empty import: `bae7e986a7bae7a9ac7d029fcd806e2b9c8c892b` (#397).
  Log append: `66d6e544c74b9499f31527b7a79ea8ab3c148770` (#391; Log 1.0.1).
  Official SDK migration: `71511521dea2cbd615908c68dcfcf0f707e92719` (#389).
  A CSV 1.0.9 source snapshot is not evidence of a verified release tag.

The incoming host WASM snapshot `598e966243ef6e75b29cadd5d145559d3eb504c2`
does **not** include #391 or #397 (both ancestry checks failed). The previous
WASM source was `7ed9067d003fdf8f15decf5995651488d8bb937f`.
The native CSV source remains `ba6ee417d91a01aae778a0ec3a4443a024671123`
plus localized patch SHA-256
`0f0b6ceaca36e914d8beb458156aeb6c07e87ebe5668d517b1f8d1e69597a442`.
The independent replay found two CSV #397 failures and eight of 39 Log core
failures on old sources. Merely changing the SDK cannot repair these source bugs.

## Required runtime contracts

`pj.widget_host.v1` / `WidgetHistoryQuery` must return total matching entries
before the delivery cap, including entries whose object payload cannot decode.
A full read and a probe/decimated read must agree on that total. Sink delivery
count may be smaller, including after the sink stops. Bounds are inclusive;
display-time conversion must round-trip to the same sample even at epoch-scale
timestamps and integer limits. Shared timestamps need stable rank-based
selection. The host must release store locks before invoking the sink. The Log
append loader depends on these semantics to avoid refetching all history or
losing equal-timestamp entries. The merged host source contains #1556, but its
native tests have not run in this worktree.

CSV #397 must fail an all-invalid import before registering/committing an empty
dataset or presenting Continue; a mixed valid/invalid import still asks the
existing Continue/Abort question. Preserve previous data on failed refill,
canonical numeric parsing, raw invalid values and translated diagnostics.
Unicode file paths need to survive both the plugin DSO and real host loader.

Widget plugin acceptance also requires the exact host Qt major.minor (currently
6.12), compiler family, architecture and DSO lifetime/cleanup rules. Qt-free Log
core results do not validate Qt widget DSO loading. No fake SDK headers may
substitute for the selected SDK in ABI tests.

## Candidate changes ready for dependency consumers

[`compatibility-candidates`](../../packaging/localization/plugin-patches/compatibility-candidates/README.md)
contains the three isolated, source-hashed patches and current test identities.
The WASM pair is now applied and hash-checked by the local CMake build. The native
additive fix is combined into the production CSV patch, with source-lock hash
updated and the exact preflight allowlist extended. Real SDK 1.0.1 tests passed
128 native CSV cases and 138 WASM-source-native CSV/Log/SDK cases, including actual
Qt 6.12 widget DSO loading. No unrelated plugin snapshot upgrade was made.
Standalone SDK 0.34.1 CSV passed at -O2; its -O3 warning failure remains recorded.

## Minimum validation before completing integration

Steps 1 and the selected CSV/Log DSO parts of 3–4 have fresh local evidence; the
full-host/platform/package portions remain required. The independent APBIN audit also reported
 original-ZIP Linux/Windows checks (registry 1.2: 102 each;
#339 draft 1.3: 121 each) and source run 44049992795 success at 90afd65. None
replaces full GUI/marketplace acceptance.


1. Choose one source tuple and update Conan requirement/revision/lock, CMake
   archive URL/hash, `cmake/host-sdk-source.json`, licenses, provenance tests and
   packaging identities together. Preserve exact-version and hash assertions;
   inherit #70's prerelease validation fix through real branch history.
2. Build the actual APBIN candidate through this host target on Linux and Windows.
   Run parser 2147, ABI 121, real BIN metrics, strict sanitizer and both-direction
   loading. Retain the independent 0.34.1 build and manifest minimum separately.
3. Build localized CSV with the real selected SDK: `csv_parser_test`,
   `csv_file_paths_test`, `csv_source_test`, and every `CsvRuntimeLanguage_*`
   process (zh_CN, zh_TW, en_US, unknown, empty). Require #397's two cases and
   the new all-invalid language case; replay #369 Chinese paths.
4. Run `log_viewer_core_test` (39 regression cases) on the patched source, then
   the Qt table/model/viewer DSO suites. Run host `widget_runtime_host_test`,
   especially `AnEntryThatDoesNotDecodeIsCountedLikeADecimatedReadCountsIt`,
   shared timestamps, inclusive boundaries, epoch times and sink cancellation.
   Recheck layout/source-qualified binding restoration from candidate 80a97e12.
5. With `ctest --show-only=json-v1`, select current FileLoader, extension catalog,
   dialog bindings, resource/font/splash and layout tests; execute native
   Linux/Windows variants, including Chinese paths and DLL cleanup. Run full
   Qt 6.12 translation extraction and source/provenance gates on the exact head.
6. Build WASM only after that tuple is coherent. Verify symbols, actual plugin
   registration, notices/source offer, CSV empty/mixed loads, incremental logs,
   persisted layouts, and original/localized image rendering. Keep upstream
   budget checks and a separate localized total budget of 26,000,000 B. Reuse
   54783848 visual assertions only with fresh actual image readback evidence.

Full application, Windows, WASM, heavy official plugins and final package remain
outside the independent SDK acceptance. No stable promotion or release follows
from this document or the completed source-only checks.
