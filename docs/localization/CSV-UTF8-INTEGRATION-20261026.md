# CSV UTF-8 path integration supplement — 2026-10-26

The reviewed CSV source fix is now consumed by the fork's actual plugin rebuild,
identity and package replacement chain. The Linux focused native build and
local full-host synthetic import checks pass. This supplement does not claim a
new release package or a native MSVC build.

The public source review, with unrelated environment-operation details omitted, is
[CSV-UTF8-SOURCE-REVIEW-20261026.txt](CSV-UTF8-SOURCE-REVIEW-20261026.txt),
SHA-256 `ba6a227fa86e061e5c32fe7aff83c16eb355672dade8819d767225e87bb95920`.
Its technical findings and historical evidence boundaries remain unchanged.

## Source and targets

- Fork: `reliable-ly0411/PlotJuggler-zh-CN`.
- Topic base/development head: `9f38ffd4bd625723ef96c8a49ad320846b98bc2b`
  (`zh-CN-4.x-dev`). Stable head: `057f707e017c4e296da93efc1272e932eb672738`
  (`zh-CN-4.x`). Both remote heads were rechecked on this date.
- Actual upstream source: `PlotJuggler/pj-official-plugins`, `data_load_csv`,
  baseline `ba6ee417d91a01aae778a0ec3a4443a024671123`, release tag
  `data_load_csv/v1.0.7`; annotated tag object
  `f6e50746f80b6c34450e12a443914135f07ebf3f`.
- Frozen four-file patch SHA-256:
  `00ecc1514fde0b6d8b97750a1cac1d2a251c0aa955c884e1dde7fa995f95c02c`.
  Its bytes are unchanged from the independent review.
- Observed upstream `main`: `37e1bde18b8a425b9b64d7fe54c165464942b5eb`.
  The source patch apply-check passed there; that newer base was not rebuilt.
- SDK 0.34.1 source: `4d59e7de81455afe73a77051075e8fb4b9f6b0fd`.
  Plugin ID/version, ABI and minimum SDK/host declarations are unchanged.

The root upstream `CLAUDE.md` requires C++20, its clang-format/warning policy,
SDK pin/feature-floor checks and Python script tests. No separate CONTRIBUTING
file was found at the reviewed plugin baseline. A future upstream contribution
belongs in the plugin repository, not the host or registry repository. Do not
invoke its release/tag script for a source fix contribution.

## What the fork consumes

1. `source-lock.json` adds `csv-loader` for Linux and Windows with the exact
   module, target, source commit, tag object, SDK and reviewed patch hash.
2. The real builder applies the patch, builds the real plugin and both CSV tests,
   asserts their CTest selection, verifies the embedded version, and creates its
   distribution with license/dependency notices and new content identities.
   CSV has a six-entry CTest allowlist: parser, path ABI test and four existing
   language-helper tests. The helper is not a translation of CSV input data.
3. The replacement allowlist includes CSV. The exact official 1.0.7 DSO hashes
   on each platform are added to the existing generic same-version seed policy.
   Unknown user-replaced binaries remain outside that audited predecessor set.
4. Package acceptance requires CSV rebuild provenance and exact payload hashes.
   It imports entirely generated CSVs using ASCII and Chinese paths in English
   and Chinese sessions, checking both fields, all finite samples, their bounds
   and the visible viewport. Existing BIN and plugin-count gates remain.
5. The existing Windows plugin preflight and Linux/Windows packaging workflows
   call this builder and consume the new lock. No new publication trigger or
   action permission is introduced. The existing package step consumes the full
   platform source lock, including the CSV repair.
6. Optional `--plugin csv-loader` is permitted only with `--preflight` and emits
   a preflight-only record. Normal package staging always builds the full
   platform lock; unknown IDs and partial-release requests fail before staging.

Official registry ZIP checksums are unchanged and continue to identify official
input archives. They are never assigned to rebuilt bytes. There are still 19
bundled plugins on Windows and 21 on Linux, including the existing BIN plugin.
Published rc.3 notes retain their five-plugin display rebuild scope; a regression
check distinguishes that historical scope from this new CSV source change.
No APBIN/FFT implementation change is part of this integration patch.

## Local integration results

Environment: Ubuntu x86_64, GCC 13.3.0, C++20 Release, Conan 2.33.0, two build jobs,
existing isolated project tools/cache. No global installation was changed.

| Check | Result and scope |
|---|---|
| Actual fork builder, CSV preflight | PASS; pinned checkout, patch hash, native build, manifest/version and distribution all verified |
| CSV parser | 49/49 PASS |
| Dynamic CSV path ABI tests | 12/12 PASS |
| Existing display-helper processes | 4/4 PASS (zh_CN, en_US, unknown, empty) |
| Native generic migration policy | 8/8 Qt checks PASS, including test lifecycle; 6 test bodies, with `-Werror` |
| Python host suite | 119 PASS, 5 Windows-only SKIPPED (124 total) |
| Release-policy suite | 4/4 PASS |
| Translation extraction | 1,968 active messages, zero missing/stale/unfinished; placeholders/plurals/rich text PASS |
| Branch and provenance checks | PASS |
| ELF boundary | All three required exports present; zero GNU UNIQUE symbols |
| Rebuilt distribution | Exact three-file set and hashes PASS; 16 notice/source files hashed and verified |
| Real official-to-rebuilt replacement | PASS using the downloaded, checksum-verified official Linux CSV ZIP |
| Full local host, generated CSVs | 6/6 PASS: ASCII/Chinese paths × en_US/zh_CN/zh_TW |

The last row uses the previously built complete `4.0.0-zh.1.rc.3` local host,
not a new build of this topic's host checkout or a final distributable package.
Each process used an isolated profile, the newly staged CSV plugin, software
rendering, telemetry disabled and no private input. Diagnostics confirmed the
staged plugin path. Both synthetic fields had three finite, visible samples,
exact expected time and value bounds, successful layout settlement, exit zero,
and no warning/error or unresolved-curve diagnostics. All six processes exited.
These host checks validate complete synthetic sample counts and bounds; the
plugin ABI tests separately compare each synthetic value and timestamp exactly.

The focused builder resolved this existing cached SDK package (not a newly
verified remote binary download):
`plotjuggler_sdk/0.34.1#57b2c19bd0f1e7f856176a4ee49f506c:31be5b2957860bdae222283bfeac3f19f40c3f4c#1bb462e3a7b5db335c167f68d969c864`.
The actual Conan graph and lock were retained locally. The builder's general
`sdk_acquisition` label describes the successful public-Conan probe route; this
supplement makes the cache provenance explicit. Native CSV dependencies include
JSON 3.12.0, GTest 1.17.0, date 3.0.4 and its curl/OpenSSL/zlib dependencies.
No SDK source or warning setting was changed in this integration build.

New Linux preflight payload SHA-256:

- `libcsv_source_plugin.so`:
  `3330d13b581ee5cbab451882ff00f3edb8b376bb9ca5ebe15dfe2fd021492e40`
- `manifest.json`:
  `f93c781567e6ff1465ab9aa168dc8d8643fe0ecdc32c19e78da0cf46fc5ebe9b`
- `.pj-localized-build.json`:
  `56caefcf4a05b102a289e7e5ebb526717c3409a18ec3df7346ccca14f0538baf`

This Ubuntu-built DSO is a local proof artifact, not a certified portable Linux
release. Final packages still use their configured release environment and
original-package acceptance gates.

## Reproduction without private data

Use a fresh writable work/prefix and an isolated Conan cache with an appropriate
native default profile. The existing project environment uses official
ConanCenter and PlotJuggler's anonymous Conan remote. After applying the complete
integration diff to the stated fork base:

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
python3 -m unittest discover -s .github/release_policy -p 'test_*.py'
python3 scripts/check_branch_name.py zh-CN-4.x-feat/csv-path-integration
python3 tests/check_localization_provenance.py
python3 tests/check_translations_4x.py --lupdate "$QT_PREFIX/bin/lupdate"
python3 packaging/localization/build_localized_plugins.py   --preflight --plugin csv-loader --work "$CSV_WORK" --prefix "$CSV_PREFIX"
cmake -S pj_runtime/tests/localized_seed -B "$SEED_BUILD"   -DCMAKE_PREFIX_PATH="$QT_PREFIX" -DCMAKE_BUILD_TYPE=Release
cmake --build "$SEED_BUILD" --parallel 2
ctest --test-dir "$SEED_BUILD" --output-on-failure
```

The package acceptance generator creates this entire fixture from scratch:

```csv
sample_index,synthetic_signal
0,-2
1,3.5
2,0
```

It uses generated `csv-ascii/synthetic.csv` and `csv-测试/合成.csv` names. No user
field, value, original path or data-derived fixture is needed. The upstream patch
contains additional generated path classes, including supplementary Unicode.

## Existing Windows evidence and remaining gates

The prior Windows proof used official LLVM-MinGW 20261020 (UCRT x64), clang
23.1.4, and the unchanged pinned SDK. Official toolchain source:
[release 20261020](https://github.com/mstorsjo/llvm-mingw/releases/tag/20261020),
archive `llvm-mingw-20261020-ucrt-ubuntu-22.04-x86_64.tar.xz`, SHA-256
`55064b60b991a1e1e8090b8c2f84e82b22cfe5903d12c159d65064cf5e8ae335`.
Fixed Windows DLL SHA-256:
`3145199ee19029129d37f51993926fa09cf304779580ff79c370a9695f77c387`.
The runtime was linked statically; no extra runtime DLL was deployed. An explicit
local definition file exported the existing ABI version symbol for MinGW. This
is not an SDK interface change or a production MSVC configuration change.

The official Windows 1.0.7 DLL failed six non-ASCII preview/import cases out of
12; the fixed DLL passed 12/12 across 20 runs, with 49 parser tests also passing.
The official 4.0.0 host imported the synthetic ASCII and Unicode cases with the
fixed DLL. Native MSVC was not needed for that observed host compatibility test,
but the fork's normal MSVC packaging chain has not been rerun with this change.
The independent cloud review did not independently repeat the Windows tests.
Its GCC 14 SDK warning workaround and absence of sanitizer/native-MSVC coverage
remain as documented in the preserved independent report.

All included reproduction inputs are synthetic. No private records or private
test artifacts are needed or included.

Independent focused integration review passed on both exact development and
stable baselines. The full report is
[CSV-UTF8-INTEGRATION-INDEPENDENT-REVIEW-20261026.txt](CSV-UTF8-INTEGRATION-INDEPENDENT-REVIEW-20261026.txt),
SHA-256 `9dc6ef519f733f572d15912a62dfef73b5b8ee86980d91a85a73862be2f5f0fb`.
Each baseline passed 119 Python tests with 5 Windows-only skips. The review also
passed the six Qt migration test bodies plus initialization/cleanup, four display
helper processes, release-policy, branch, provenance and translation checks,
and independently verified both platforms' official predecessor archive/DSO
hashes, the source tag and peeled commit, and the CSV CTest selection guard.
These are focused source/integration results, not a new complete package pass.

Remaining gates:
- No new complete Linux/Windows package, native MSVC CSV binary or clean-system
  package acceptance run has been produced for this topic. A worktree helper's
  shallow-submodule reference issue also means this topic has not had a new full
  host build; it did not affect the successful standalone CSV build.
- For source integration,
  retain one atomic CSV integration commit through normal topic-to-development
  and development-to-stable merge commits; do not squash or alter old releases.
  The upstream contribution is a separate CSV-only change in the plugin repo.
