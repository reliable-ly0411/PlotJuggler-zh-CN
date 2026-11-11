# Windows native test bundle design

This is a test-only preparation, not a package or a successful native test run.
The bundle build workflow, complete dependency selection, session launcher,
media fixtures and target-host safety review are not yet complete. No workflow
should publish or transfer a test kit until those gates have been implemented
and checked against the exact new source tree. Existing release assets and
release permissions are not changed.

## Build and identity

Build on a Windows MSVC runner at the exact absolute path that will later be
used on the test machine. The caller supplies and verifies that path; a drive
alias, rewritten binary path or a different extraction location does not satisfy
this contract. Use short fixed children for source, build, Qt, Conan runtime and
test tools. Set the test-driving Python executable and Conan home before the
first CMake configure. Establish both `TEMP` and `TMP` in the owned test root
before starting CTest **or any discovery**: some test programs create temporary
directories in static initialization before `main`. Environment variables alone
are not proof of Qt's actual temporary path: on Windows Qt 6.12 can use
`GetTempPath2W`, and a SYSTEM token may select `C:\Windows\SystemTemp`
regardless of `TEMP`/`TMP`. From the eventual interactive user token, run a
small real Qt Core probe that only prints `QDir::tempPath()` and verify its
canonical path lies under the new owned run root *before* any discovery. The
probe itself must not construct a global `QTemporaryDir` or write test data.
`scripts/windows/native_temp_probe` is a standalone Qt Core probe that checks
an independently expected exact temp directory, Qt version and loaded Qt Core
module path, interactive session, user SID and integrity RID, and refuses
session zero or system/service SIDs. Verify the probe, Qt Core and their full
loader dependency hashes with an already trusted system tool before executing
them. A separate CI-only probe checks the actual disposable hosted-runner token
and Qt temp path before any producer or clean-job CTest discovery. It may report
session zero and is never evidence of the VM interactive session. Build the
probe from the same source and Qt identity as the kit. Its Windows binary and
actual session behavior still require verification; a non-Windows build fails
closed and cannot validate a Windows token. Do not change SystemTemp, ACLs,
security settings or accounts to make it pass.

Record the full source commit, tree, recursive submodule commits, workflow
commit, configuration, actual compiler/toolset and SDK, Qt version, Conan graph
package IDs and revisions, exact tool versions, verified source URLs and SHA-256
values. The Conan lock alone is not a complete binary identity. The driver
Python is separate from the Conan CPython runtime and its native modules. Do not
put an embedded-runtime `PYTHONHOME` into the driver interpreter's environment.
Pin a portable CMake/CTest distribution and any required Python, 7z and other
tools to verified official sources and hashes. Keep tool licenses and applicable
third-party notices. Official redistributable release MSVC runtime files may be
needed; MSVC debug runtimes must not be redistributed.

For each main and standalone i18n configure, resolve the activated environment's
real `cl.exe` within the active MSVC toolset, rejecting PATH/CWD shadowing.
Freeze its canonical path and SHA-256 before CMake runs; both roles must match
the same independently established producer compiler identity. Initialize both compiler cache entries with absolute `FILEPATH` options. A
non-cache compiler assignment in a Conan toolchain is not itself a cache entry,
and a toolchain can override the requested compiler. Immediately after configure
and before either build, require the strict existing cache contract and exactly
one MSVC CXX compiler in a fresh nonce-bound File API `toolchains-v1` response.
Both must match the independently recorded compiler, including its current bytes.
Retain only the relevant query, index and toolchains bytes and hashes, bound to
the source commit, tree and build role. Revalidate this preflight evidence and
capture the final configure evidence for identity and staging checks; do not
execute generated compiler `.cmake` files or package raw CMake caches. The nonce
query prevents a prior configure's response from satisfying a fresh role.
Linux tiny-project tests exercise CMake cache/File API behavior, not MSVC or
Windows runner acceptance.

The exact CTest command is also a dependency. In this project `PRE_TEST`
discovery can launch test runners for `ctest --show-only=json-v1`. Generate the
complete JSON under the configured runtime environment in CI and retain names,
commands, properties, working directories, configuration and their source
identity. It is not safe to execute discovery on the target until the fixture
and session-safety gates are closed. Do not assume a previous source tree's
case count still applies.

For a failed producer step, `collect_failed_config_diagnostics.py` retains only
fixed configure categories, counts and file digests. Its existing `phase`,
`binding` and `exit_code` describe configure evidence only. The separate
`build_binding` and optional `build_exit_code` describe a completed build
receipt independently matched to the expected source commit and tree.
`phase_boundary` distinguishes an observed configure failure, successful
configure with no observed build, build failure, and failure after successful
configure/build exits. The boundary requires completed schema-1 receipts;
missing configure or contradictory receipts leave it `not-established`.
Missing or oversized build receipts remain unverified. A successful build exit
does not identify the later failing operation, prove kit completion, or
establish test or package acceptance.
Raw output, arguments, environment and paths are not copied into this report.

## Explicit inputs and offline IFW test

The new test-only CMake options are `PJ_IFW_TEST_ARCHIVE`,
`PJ_IFW_TEST_EXTRACTOR` and `PJ_IFW_TEST_EXTRACTOR_SHA256`. Pass all three as
absolute inputs when configuring both the main build and standalone i18n build.
Partial values are an error. The synthetic IFW test hashes the pinned official
archive and the supplied extractor before using 7z; it does not fall back to a
download after an offline-input failure. The extractor itself must come from a
verified official distribution, with its origin, hash and license in the kit.
Without these options the existing CI download behavior is unchanged. Qt's
`lrelease`, `lupdate`, `rcc` and `qtbase_zh_CN.qm` are all required. This tests
synthetic installers only; it is not final application installation acceptance.

A clean source checkout lacks four native test inputs under
`pj_scene2D/testdata`: `test_480p.mp4`, `test_1080p_bframes.mp4`,
`test_images.mcap` and `potato.mcap`. Produce and validate suitable synthetic
fixtures only for tests whose contracts permit synthetic inputs; record the
producer, commands, provenance and resulting hashes. Follow the test assertions
rather than assuming the README's video dimensions are correct. Do not replace
tests requiring canonical vectors, real production inputs or the separate
cloud/plugin E2E environment with synthetic substitutes. Record each condition
that remains unavailable as uncovered.

The allowlist must cover the recursive tracked source and submodule files used
at runtime, every generated CTest include/discovery file, test executable,
helper, mock and real plugin, generated fixture and sidecar, Qt plugins and
translations, Noto test font, FFmpeg and Conan CPython dependencies, native
Python extension modules and necessary licenses. Compiler-produced absolute
fixture and plugin path constants also have to resolve. Recursively check both
normal and delay imports, and explicitly seed dynamic plugin, Python and Qt
loads. An import-table scan or PATH alone is insufficient; some helper/plugin
loads search the loading executable's directory. Exclude Git metadata,
credentials, Conan configuration or arbitrary cache/build contents, object and
static library files, PDBs and prior test reports. Never substitute an old
build or old reports for the new source.

## Auditing a curated staging directory

`scripts/windows/native_bundle_audit.py` is a fail-closed *component*, not an
automated dependency-closure proof. Its `stage` operation accepts only an
explicit JSON list of individual source files and expected hashes. Each file
has an origin, and each origin declares a full revision and bundled license
paths. It records sanitized origin information without storing physical source
roots. It does not infer which files the real tests dynamically load or decide
whether an asserted license is sufficient. Staging must start in a new empty
directory; do not stage over the build or an existing user directory.

The staging-plan structure is an object with `origins`, `directories` and
`files`. Each origin has an absolute CI-only `root`, a `description`, a full
40-digit Git revision or 64-digit distribution SHA-256 in `revision`, and a
non-empty `license_files` list of destination-relative paths. Each file has an
`origin` key, an exact relative `source`, relative `destination` and `sha256`.
The optional `directories` list includes any empty working directories. No
wildcards are expanded. Build the list from the actual new source, dependency
graph and reviewed runtime closure rather than a prior run.

The provenance input used by `capture` requires full `source_sha`,
`source_tree`, `workflow_sha`, `source_clean`, `configuration`, `qt`, `sdk`,
`windows_sdk`, `compiler`, `generator`, `runner_image`, `conan_lock_sha256`,
`conan_graph_sha256`, `submodules` and `tools`. Each tool requires a name,
version, verified origin and distribution SHA-256. The required names include
`cmake`, `ctest`, `python`, `embedded-cpython`, `lrelease`, `lupdate`, `rcc`,
`ifw` and `7z`. These values are declarations to verify against independent CI
evidence, not a substitute for it.

`discovery` audits obvious absolute paths in each CTest command and property,
requires the expected configuration, command and working directory, and rejects external paths.
The optional missing-output exceptions are exact, per-test paths and must be
reviewed; unused exceptions fail. Relative path references, binary constants,
runtime DLLs and arbitrary subprocess behavior still need separate analysis.
The scan never executes CTest or a test program.

`capture` records every staged file's size, SHA-256 and modification time plus
all directories, including empty working directories. The optional internal
manifest is exactly `_bundle/manifest.json`; its own digest must be recorded
independently, since a file cannot contain its own hash. `verify` requires that
digest, independently expected source commit/tree/configuration and the approved
logical root. On Windows, verification also requires the physical extraction path to
match the logical root. It rejects extra/missing files or directories, changed
bytes, reparse points, hard-linked staged files, case collisions, illegal or
excessively long Windows paths and known cache/credential or debug-CRT names.
The tool checks known failure modes but is not a substitute for the review of the
allowlist and source provenance. Strict `verify` checks the complete pre-run
snapshot; it is not a post-run classifier for intentional new test outputs.

File timestamps can affect CTest's PRE_TEST rediscovery. A file hash match does
not itself prove discovery will be reused. The clean-runner verification must
bind the original discovery result, test binaries, CTest include files, source,
properties and actual timestamp ordering. If an archive changes timestamps,
restore only the original recorded timestamps after all relevant bytes and
identity are verified, then verify the ordering and run controlled rediscovery
in the clean CI job. Never invent timestamps to conceal stale or mismatched
discovery; if the same evidence cannot be established, fail the kit. A local
launcher implements the preliminary restoration and comparison but has not
yet been validated in a real Windows clean runner or the target session.

`results` compares a new JUnit file to the exact discovery names and separately
reports top-level skips, failures, nested GoogleTest/Qt skips and known CTest
output-removal markers. It cannot by itself establish that untruncated per-case
stdout and stderr were saved. Reconcile an internally skipped child with its
separately supervised execution only using explicit fresh evidence. Distinguish
pass, fail, platform-inapplicable and unmet-condition cases. A zero CTest exit
or absence of a parser error is not an all-tests-passed claim.

`space` requires measured archive and unpacked bytes, current free bytes on
both sides, expected simultaneous host copies, run-time growth and explicit
reserves. It includes one archive plus unpacked kit and run-time growth on the
Windows side. Account separately for the artifact downloader's outer ZIP,
transport buffers and any second copy. Disk estimates made before the first
real build are planning assumptions, not measured bundle sizes. Recheck both
filesystems immediately before transfer, never treat two paths on the same
filesystem as independent capacity, and fail if the measured peak plus reserve
does not fit.

## Required clean-runner and host gates

1. In a separate clean Windows CI job, unpack the single official test artifact
   at the same absolute path, verify its independent artifact/manifest digests,
   source identity, tools, licenses, manifest and all runtime dependencies.
   Use a restricted explicit environment rather than the builder's PATH. Verify
   both build trees and compare the fresh full discovery with CI's recorded
   manifest. Run the selected suite and keep complete CTest output, its original
   log and JUnit evidence. CTest combines child stdout and stderr, so the
   original separate child streams are not available. Fail on
   missing dependencies, stale discovery, missing output or altered identity.
2. Before any target run, finish the dedicated native fixture audit. In
   particular, a private application profile does not isolate every Qt or OS
   path. Real GUI startup still reaches the platform-specific active-widget
   recovery marker, and a separate review is needed for Qt file-dialog state,
   installer registrations, child processes, local network use and shared
   registry data. The separate Windows CI guard smoke must also establish owned
   key cleanup, behavior of static `QSettings` writes after `main` and a denied
   cleanup failure. It is not evidence for real app CLI or IFW isolation. No
   security settings, accounts or drive mappings are changed.
3. Launch in the intended interactive user session, not a SYSTEM/service
   session. Record the actual session, token identity/integrity, exact command,
   CWD, a whitelist of needed environment values, raw untruncated stdout/stderr,
   process exit values and per-case outcomes. Keep all test inputs and owned
   outputs under the approved test root. A two-stage launcher records the
   CTest process's own stdout/stderr as raw bytes and CTest's merged per-case
   output. The launcher and probe still need real interactive-session validation.
4. Preserve each test's platform semantics; do not globally force a Qt platform
   plugin. Prove the graphics backend and actual adapter used by relevant tests,
   rather than inferring GPU use from the presence of a GPU. Run supported
   opt-in lanes separately. Recheck immutable input hashes after the run without
   confusing intentional owned outputs with changes to source or dependencies.

The synthetic Python tests for the audit components run as part of the existing
source-check discovery. Passing them neither creates a kit nor runs the native
Windows tests.

## Safety review and configuration limits

The launcher defaults to a preflight that starts only a hash-verified QtCore
probe. It creates an owned temporary directory and records the actual token and
Qt temporary path before a reviewer binds source/tree, manifest, preflight,
probe, token and per-group evidence. A matching process token alone does not
prove an active interactive desktop: an independently reviewed session/desktop
evidence file is also required, and the code cannot validate its factual
quality merely from its hash. Every approved group also needs a separate
evidence-backed review of argv, working directory, relative or unknown path
arguments and dynamic dependencies. The syntactic path scanner is only a
conservative filter; it cannot establish that those dependencies are closed.
CTest discovery itself can execute static
initializers and requires a separate full-tree discovery review. Full mode
refuses unclosed cases. Explicit reviewed-subset mode records every omitted case
and only selects groups whose complete transitive DEPENDS and fixture
setup/cleanup closure is independently approved. It checks selected metadata
again with the original CTest before execution; it does not weaken properties.
These mechanisms are local prototypes, not evidence of a completed Windows run.

The launcher refuses the real-app ArduPilot layout and Windows application
contract cases unless actual same-source Windows probe validation is present
in the authenticated manifest and the independent group/session reviews are
complete. For every application spawn, the test-only helper checks the exact
Qt KnownFolder marker location and other PlotJuggler processes before and after,
requires an isolated profile and temporary root, and records the child token.
No marker contents are read or removed. Cooperating launchers for the same kit
hold a shared nonblocking lock from the first snapshot through the last; a
failed or uncertain launch leaves that lock for review. Other applications and
noncooperating processes remain outside this lock, so the snapshots do not
eliminate races with them. If a short-
lived app exits before its token or actual QtCore module path can be observed,
its assertion may have run but that identity or loader condition is reported
unverified. Full mode fails when cases are unclosed; reviewed subsets record the
unrun cases and can continue other safe groups. The required Windows probe
negative-control tests and the complete runtime path have not yet run.
Between discovery and suites, the launcher re-inventories every immutable
directory and permits only explicit CTest bookkeeping files. This does not
prevent a test from altering a search path during its own suite; source review
of each group's process creation and writes remains a prerequisite.

Before running any bundle Python, probe or other executable, an independently
trusted host mechanism must first verify the artifact and manifest hashes, the
driver, launcher, all imported code and the entire interpreter loader/runtime
against that manifest. In-process verification cannot establish the prior
trustworthiness of the Python interpreter or modules it already loaded. The
host bootstrap itself needs independent verification and must not bypass
execution policy. The independently launched system PowerShell must inherit a
previously verified, empty `bootstrap-temp/<source-prefix>` directory as both
TEMP and TMP before it starts; CodeDom is also directed there. Actual Windows
file-access tracing remains needed because this does not prove all OS writes
are confined. The embedded Python `._pth` file is authenticated and its actual
startup import paths must match the explicit same-root list. Neither Windows
bootstrap nor clean-job verification has yet been established by the Linux
tests in this preparation layer.

The producer also runs a disposable-Windows-only private HKCU lifecycle smoke.
It checks normal and late-static cleanup and an injected cleanup failure, and
removes only the two exact UUID keys created by that failed run. Ambiguous
identity or cleanup fails the job; this is not a blanket registry sandbox. A
linked surviving-root MainWindow negative control and the actual native suite
remain separate evidence requirements.

The synthetic installer case invokes Windows PowerShell. It may use only the
independently reviewed Microsoft system executable at its standard System32
location, whose exact SHA-256 is passed into and bound to both preflight and
execution. If its presence, source and policy are not established, mark those
cases condition-missing. The launcher does not change execution policy or add
an execution-policy bypass. The CTest and probe process tokens are recorded;
that alone does not record every short-lived descendant process's token.

The planned RelWithDebInfo Windows kit does not cover Debug-only or `!NDEBUG`
branches and is not an all-configurations result. Do not redistribute MSVC
Debug CRT files. A possible later, distinctly labeled lane would rebuild the
application, tests and SDK consistently with assertions enabled while using the
release CRT; it would not be equivalent to full Debug. It needs its own same-
source configuration, compatibility checks, licensing and actual execution.
