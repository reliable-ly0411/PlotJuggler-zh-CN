# Chinese 4.x candidate packaging

Read the repository's `RELEASING.md` before changing versions or publishing.
The build-only `zh-4x-packages.yml` uses the normal native CI dependency graph and
regressions, then packages a fixed source commit with upstream-compatible formats:
Windows IFW `.exe`, Linux `.AppImage` and `.deb`. It does not create a tag or Release.
The upstream Depot workflows are not used by the Chinese fork.

`prepare_payload.py` obtains the CMake-generated exact BIN plugin path rather than
finding an arbitrary stale DLL, copies its manifest and licenses, and stages a
SHA-256-pinned Noto CJK font with its OFL. Dependency notices are collected
from this build's exact Conan graph, vendored sources and Qt SPDX records. The application registers this font from
its own `bin/fonts` directory. A test runner's installed font is not a substitute.
The official registry snapshot and its artifact checksums are frozen in
`registry-lock.json`; admission is checked against the packaged host's SDK/ABI.
The Linux-only ROS distro-specific binaries keep their upstream external-runtime
contract. The optional GPL retro game payload is not included in this candidate.

`version_map.py` owns the platform metadata mapping. Application and tag retain
SemVer; `4.0.0-zh.1.rc.1` maps to IFW `4.0.0.1.0.1` and Debian
`4.0.0~zh.1~rc.1-1`. Tests cover rc.1, rc.2, final, the next Chinese revision and
the next patch release. Final IFW for the first Chinese revision is
`4.0.0.1.1.0`, so no released candidate is offered as a downgrade.

`verify_linux.sh` runs in bare Ubuntu 22.04 and 24.04 containers. It checks the
original hashes, upstream dependency/install/remove smoke, then installs that
same `.deb` and extracts that same AppImage for static inspection while launching the original
AppImage with its own runtime for `verify_package.py`. No build
Qt/Conan directory or system CJK font package is supplied to these containers.

`verify_windows.ps1` installs the downloaded IFW executable into a fresh directory,
verifies IFW metadata, checks the installed application with development paths
removed, then uninstalls it. MSVC CRT DLLs are explicitly supplied app-local;
the runner's existing VC installation is not used as proof that they shipped.

`verify_package.py` checks package provenance, CJK font bytes, legal texts, the
real app `--version`, Python, and every expected plugin/version. It restores
entirely generated CSVs from ASCII and Chinese paths in English and Chinese
sessions, requiring both fields, all three finite samples, exact synthetic
bounds and a viewport containing those samples. It then restores
a real BIN from a Chinese path in each language, requiring a successful exit,
1,940 imported numeric series, and no unresolved-curve or error diagnostic.
The opt-in `--dump-plot-state` snapshot reads the actual attached Qwt adapters
after layout settlement, without invalidating caches, reattaching curves, or
changing the viewport. Acceptance additionally requires the exact `/RCOU`
`C1\t[us]` curve to contain at least 100 finite samples in view, a non-default
viewport enclosing the waveform, and the pinned log's expected physical range.
An import message, resolved catalog key, or attached-but-empty curve cannot
satisfy this gate. `ArduPilotLayoutRestoreTest` applies the same fixture and
state checks to each native build in both languages.
Acceptance processes set `QT_FORCE_STDERR_LOGGING=1` so Qt's Windows debugger
sink cannot hide import messages from the captured stdout/stderr pipes. This
changes only the test process's log destination, not the import requirements.
Screenshots of the installed/extracted app remain separate required
visual-review evidence; sample-state assertions do not replace visual review.
The real upstream log contains a truncated tail warning; that is not hidden.
Hashes are rechecked afterwards. Reports and screenshots remain CI artifacts,
not Release download attachments.

Publication must promote the already accepted bytes. Never trigger a fresh build
from a tag and assume it equals the candidate. Record source commit/tree, workflow
commit, run URL, exact test outcomes and final public asset sizes/SHA-256. Ordinary
merges preserve the candidate as an ancestor; a release tag anchors the exact
accepted source commit, not an untested version bump. Old tags/assets stay intact.

`release_assets.py` verifies each original candidate against its acceptance
manifest before making publication-only copies. It maps `~` to `.` in download
filenames, so the Debian download uses `plotjuggler4_4.0.0.zh.1.rc.1-1_amd64-zh-CN.deb`
while its internal version remains `4.0.0~zh.1~rc.1-1`. No package is rebuilt or
modified. Candidate manifests/checksums keep their original names; the public
checksum list and release-note table are generated from the mapped copies.
Only ASCII letters, digits, dots, underscores and hyphens are accepted, with
alphanumeric ends; unknown characters and name collisions fail closed.

[GitHub documents that release uploads can rename filenames](https://docs.github.com/en/rest/releases/assets#upload-a-release-asset).
The publisher captures each upload response and checks the actual draft asset
names, unique upload IDs, sizes, uploaded state and server SHA-256 digests,
including `SHA256SUMS.txt`. It re-downloads all draft assets and verifies their
bytes and checksum list before changing `draft` to false, then repeats the
checks after publication. Unexpected renaming or missing digests stop the job
with the draft unpublished; it never rewrites the checksum list to accept an
unexpected upload, deletes assets, or retries with clobber. A failed draft/tag
requires explicit review, not automatic reuse. Evidence stays in CI artifacts,
not in the Release download area. Run `python3 tests/test_release_assets.py -v`
for the offline regression, also required by the source-checks job.

The explicit publication entry is the `zh-CN-4.x-ci/publish-accepted-v4-0-0-zh-1-rc-1-run-RUN-attempt-ATTEMPT` ref. Only
create it for the first time to the accepted source after final screenshot review
and ordinary stable promotion. Its push is the visual-review confirmation; it
must never be part of candidate generation. The publisher accepts only the explicitly named run ID and attempt for that exact SHA and promotes only its original assets after validating
its release manifest. Each version uses a new ref; never reuse or force-update a
previous promotion ref. Only its first creation triggers publication. This
keeps the default 3.x branch independent of the 4.x publication mechanism.

## rc.3 candidate

The first creation of `zh-CN-4.x-ci/release-candidate-rc3-final1` requests new
rc.3 packages from the exact promoted stable commit. It runs both native suites,
all original-package clean acceptance jobs and the release-manifest gate.
Ordinary updates to the ref do not rebuild. Publication uses a separate new
version/run/attempt-bound promotion ref after reviewing those final screenshots;
no rc.1 or rc.2 tag, promotion ref or asset is reused.


## rc.2 fixed-plugin display rebuilds

The candidate packages rebuild the five scoped plugins documented in
[plugin-patches/README.md](plugin-patches/README.md). Mosaico remains its original official package; issue #20 records its English exception. The explicit native entry
also permits the first creation of `zh-CN-4.x-ci/release-candidate-rc2-final8`;
ordinary subsequent pushes and merges still skip heavy packaging. No candidate
branch creation publishes a release. rc.2 uses its own accepted-run promotion
ref and never reuses or overwrites rc.1.

## CSV path repair integration

The pinned rebuild chain additionally consumes `csv-loader.patch` on Linux and
Windows. Source/tag/SDK and patch hashes, native CSV parser/path test selection,
MIT and dependency notices, rebuilt payload hashes and exact predecessor seed
identities are recorded by the same builder. Replacement removes the official
CSV directory before copying and verifying the rebuilt files; it does not change
the number of bundled plugins or relabel an upstream download checksum.

The normal package workflow builds the complete lock. The optional
`--preflight --plugin csv-loader` isolates this plugin for local review and emits
a preflight-only record, never an accepted release. Existing Windows preflight
and package workflows consume the new lock and tests without a new publication
trigger. See [the scoped results and remaining gates](../../docs/localization/CSV-UTF8-INTEGRATION-20261026.md).

## Native feedback and three-language acceptance

The native workflows explicitly enable `PJ_PLUGIN_FEEDBACK_ACCEPTANCE` and stage
exactly two isolated inputs with `prepare_feedback_tests.py`: the APBIN binary
selected by this build's generated path file, and the platform-matching official
FFT ZIP verified against the locked registry hash. This is test input only;
FFT is not added to the release's 19/21 bundled-plugin inventory.
CTest selection must contain all three `PluginFeedbackMainWindow-*` cases plus
the metadata case. `audit_feedback_results.py` rejects missing cases, JUnit and
Qt-level skips/errors/blacklists, or absent actual APBIN/host-flow PASS markers.
The 24 PNG files must exist, including computed/exported FFT at 1500×830 and
1280×720 host sizes in all three languages. The host checks full action geometry
and real mouse clicks without enlarging the input splitter. This structural
check does not replace pixel review.

Final-package CSV/BIN runs, screenshots and report aggregation cover `zh_CN`,
`zh_TW` and `en_US`. This remains separate from native MainWindow feedback tests:
an installed-host APBIN/FFT UI acceptance run is still required for that claim.
IFW wizard languages and the original Mosaico exception remain unchanged.
Release payload staging refuses dirty or uncommitted source before copying or
downloading anything. The existing workflows' generated `build-i18n/` and
`.conan-source-cache/` directories are explicitly ignored; other untracked source
remains a refusal. A local feedback tree must not masquerade as its HEAD.
These changes require new native/package execution; historical reports do not
become three-language package passes merely by rerunning the report generator.
