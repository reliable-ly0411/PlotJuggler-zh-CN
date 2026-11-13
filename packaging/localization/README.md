# Chinese 4.x candidate packaging

Read the repository's `RELEASING.md` before changing versions or publishing.
The build-only `zh-4x-packages.yml` uses the normal native CI dependency graph and
regressions, then packages a fixed source commit with upstream-compatible formats:
Windows IFW `.exe` and portable `.zip`, Linux `.AppImage` and `.deb`. It does not create a tag or Release.
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

## Windows software-renderer notices

The Windows payload retains the original Mesa 11.2.2 and LLVM 3.6.2 notices in
`share/licenses/Windows-Mesa-llvmpipe`. `windows-mesa-notices.json` binds this
material to the reviewed `opengl32sw.dll` size and SHA-256, immutable upstream
source revisions, and the byte count and SHA-256 of each retained source file.
The original HTML and source-file notices are copied byte for byte, not replaced
by generic license names or notices from a modern LLVM release. Reference source
files have a `.txt` suffix so they are not compiled; their contents are unchanged.
The source set includes directly related VMware Gallium/llvmpipe notices and the
LLVM Support notices named by its license. This is not a claim of a complete
linked-object audit or a redistributable SDK/source bundle.

Collection rejects unknown renderer bytes, missing/extra source notices and
changed notice bytes. Both Windows product formats use the same staged notices;
the installer staging check and clean-package verifier independently compare the
actual deployed DLL and notice inventory with the checked-in lock, not merely a
self-reported package hash manifest. Updating the renderer requires reviewing
its notices and lock together. Original notice files are exempt from whitespace
rewriting only; the tests still verify their complete source hashes.

### System D3D compiler proposal and validation boundary

Localized Qt 6.12 Windows products target x64 Windows 10 1809 (build 17763)
or newer, including Windows 11, matching Qt's supported-platform floor:
<https://doc.qt.io/qt-6/supported-platforms.html>. They depend on the operating
system's `d3dcompiler_47.dll` and its `D3DCompile` export. Windows 8.1/10 include
this DLL; this proposal does not extend support to older systems or promise that
a stripped/damaged Windows image will work. See Microsoft's redistributable
package guidance: <https://www.nuget.org/packages/Microsoft.DXSDK.D3DX/9.29.952.7>.

The localized installer uses the official `--no-system-d3d-compiler` option on
both windeployqt passes (application and plugins), not post-deployment deletion.
Other installer callers without `ExtraPrefix` retain their previous behavior.
The shared stage check and clean-package verifier reject any bundled
`d3dcompiler*.dll`, including nested/case-varied copies. Clean Windows acceptance
also enforces the OS build floor and resolves `D3DCompile` from compiler 47 with
`LOAD_LIBRARY_SEARCH_SYSTEM32`; it never falls back to PATH or a local copy.
The operating system supplies and services this dependency. No new Microsoft
SDK agreement or restrictive application terms are introduced by this proposal.

Fixed Qt 6.12 source evidence at commit
`025bdad181de241e81bf853c8a2d7bf3d19261a9`:

- [windeployqt option](https://github.com/qt/qtbase/blob/025bdad181de241e81bf853c8a2d7bf3d19261a9/src/tools/windeployqt/main.cpp)
- [RHI compiler resolution](https://github.com/qt/qtbase/blob/025bdad181de241e81bf853c8a2d7bf3d19261a9/src/gui/rhi/qrhid3dhelpers.cpp)
- [QSystemLibrary system-directory default](https://github.com/qt/qtbase/blob/025bdad181de241e81bf853c8a2d7bf3d19261a9/src/corelib/plugin/qsystemlibrary_p.h)

The original ce4 portable ZIP (SHA-256
`c8525c91a0114c49ba20693aabffa5fbda080b601bdc8fccec9e867675752628`)
was inspected read-only: 91 PE files, 968 ordinary import descriptors and eight
delay-import descriptors, with no parse errors and no D3DCompiler imports.
Compiler-name strings occurred only in Qt6Gui and the compiler DLL itself.
Combined with Qt's source, this supports preparing the change; static inspection
is not a substitute for runtime testing of the changed packages.

Application/Qt binary code and the optional standalone native test kit are not
modified. The new product packages have NOT yet been built or accepted. After
review and approval, a changed candidate must use the normal source-bound
package/native/clean-acceptance workflow, including Windows rendering and both
installer/portable checks. Old accepted binaries cannot be relabelled as a
new-source build. Existing publication and final visual-approval gates remain
unchanged. Removing the redistributed compiler from future products does not
retroactively establish that old ce4 packages met SDK downstream conditions.

## Linux packaging tool lock

`linux-tools-lock.json` records the official repository, release/asset IDs,
source commit, byte count and SHA-256 of all three x86_64 packaging tools.
Downloads use GitHub's numeric asset API with `Accept: application/octet-stream`,
not the moving `continuous` download URL. Asset IDs identify uploads, not an
upstream promise of permanent retention: deletion fails closed, with no rolling
fallback. Source commits describe official release provenance, not a claim of
reproducible builds from those commits.

The Linux candidate preflight checks official asset metadata and downloads all
three tools before dependency installation or application compilation. It does
not execute downloaded content. Payload staging rehashes the same local files
(including size), fails on tampering rather than replacing it, and records the
lock in `release.json`. The existing clean-source provenance gate is unchanged.
The shared `download_retry.py` reader makes at most three attempts for HTTP
500/502/503/504 or explicit connection/read timeouts, waiting 2 then 4 seconds.
This applies to both metadata and asset bytes. Other HTTP errors, TLS/permission
errors, invalid JSON, identity mismatches and size/checksum failures fail closed
without retries. Each attempt discards any partial response and starts a fresh
request to the same official URL; validation still precedes writing/chmod.
The unchanged 180-second urllib timeout applies to blocking socket operations,
not a strict whole-download deadline. A hard wall-clock limit requires a runner
step/job timeout; the retry count does not provide one.
To independently run the network preflight in an empty directory:

```sh
python3 packaging/localization/linux_tools.py --directory /tmp/pj-linux-tools
```

The 4.1.0 packaging repair updates two build tools whose rolling uploads no
longer matched the prior SHA-256 locks. The official releases list did not expose
an asset with either prior digest; existing historical release/package bytes are
not changed. The Qt plugin retains its original bytes.

- linuxdeploy: asset `699514588`, source
  `07333c6e942c7d71782b66be924c5d867f9dfdfc` (Update binutils to latest release).
- linuxdeploy-plugin-qt: asset `525032210`, source
  `9b9fca179e7312ae4a433ad6c3183d73c116180b` (Make qmlimportscanner more robust).
- appimagetool: asset `715388534`, source
  `11d54c9acc7f246df1398050a4b880314ac76862` (ELF section-header byte-order fix).

All three source SHAs were resolved through the official commit API; they are
not branch names inferred from `target_commitish`. Each downloaded asset's size
and SHA-256 matched the official asset metadata. The lock's release tag is audit
context only and is never used to select bytes. Updating this lock requires
reviewing the official release/source metadata and independently hashing all
new downloads; a checksum error is not permission to accept replacement bytes.
Upstream Docker/AppImage convenience download paths are unchanged; this fork's
candidate always stages the three checked files before calling the packager.

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

`verify_package.py` passes an explicit absolute `--profile-dir` beneath its
work directory (temporary by default) to every application process, including version, Python,
plugin, CSV, BIN and GUI capture launches. Each case has its own profile; Windows
registry settings are not isolated by HOME/XDG variables alone. The executor
controls the temporary-directory location through its normal TMP/TEMP settings.
For local verification, `--work-dir` selects an empty absolute directory beneath
an existing parent. It retains inputs, layouts and profiles on both success and
failure; the verifier never deletes that directory. Relative, nonempty, file,
root, parent-traversal, symbolic-link and junction paths are rejected. Omitting the option
keeps the automatically cleaned CI temporary directory.
Windows capture uses Pillow ImageGrab; it is not an application screenshot CLI.
Capture selects the launched process's unique main window, not a matching title.
Windows uses physical per-monitor coordinates, the taskbar-excluding work area,
and the window's actual minimum size before moving/resizing it. A window that
cannot fit, changes identity, or remains obscured fails acceptance; capture does
not change display modes, DPI scale, or application settings. Linux capture is
limited to the dedicated unmanaged 1920×1080 Xvfb display. It verifies the GUI's
isolated process session, exact profile argument and packaged executable bytes
(including an AppImage child PID), then moves the original-size window without
shrinking it. `xdotool` and `x11-utils` are required in the clean container.
Both platforms recheck geometry/visibility around the unscaled whole-desktop
screenshot and retain `gui-<language>.geometry.json` with its PNG hash. Missing
helpers, ambiguous windows, clipping, or inconsistent image dimensions fail
closed. These checks establish capture completeness, not full widget usability;
the original screenshots still require visual review.

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
FFT acquisition uses the same bounded retry policy as Linux packaging tools,
with the existing 120-second socket timeout and 32 MiB archive limit. Archive
validation and APBIN assembly still occur after compilation. `--fft-archive`
continues to verify a local archive without network requests or replacement.
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

## Forward-development dependency and renderer checks

Host dependency provenance comes from `host_versions.py`: Qt is read from
`versions.env`, and the host SDK from the exact `conanfile.txt` requirement.
Collection checks the selected Qt qconfig and resolved Conan host graph before
retaining notices. The retained host SDK source and exact recipe revision must agree with the
current host version; historical plugin SDK provenance remains independent.

Windows payloads must retain the original Mesa 11.2.2 and LLVM 3.6.2 notices in
`share/licenses/Windows-Mesa-llvmpipe`. The checked-in lock binds all original
notice bytes and the renderer DLL to exact sizes and SHA-256 values. Unknown
renderer bytes, missing or extra notices, and modified notices fail collection
and final-stage verification. The reference source files are not a complete
build-source or linked-object manifest. This forward-development checkout has
not yet verified the actual Qt 6.12 DLL or accepted a newly built product.

Both localized windeployqt passes use `--no-system-d3d-compiler`; no DLL is
silently deleted after deployment. Final Windows acceptance rejects bundled
`d3dcompiler*.dll`, requires Windows 10 1809 or newer, and resolves D3DCompile
from system32's d3dcompiler_47.dll only. Other installer callers without
`ExtraPrefix` retain their existing behavior. Offline unit tests do not replace
Windows rendering, installer/portable or final screenshot acceptance.

Historical candidate triggers are preserved unchanged from the development branch. No new development publication is admitted by forward integration; a new package candidate needs explicit version and trigger preparation. Four products require six clean format/OS reports and 18 screenshots; the development snapshot remains unaccepted until rebuilt and tested.
## Portable release acceptance

Candidate execution requires an explicitly admitted new candidate identity.
Historical 4.1.0 candidate entries and their evidence are not reusable acceptance
for this development source.
Windows packaging uses the upstream portable builder on the same staged payload as IFW, before
hashing both original assets. The ZIP extracts directly to `bin/`, `lib/` and
the packaged provenance/license directories.

`windows-portable-clean` is a separate Windows 2022 runner, with no native build
or IFW installation. `verify_windows.ps1 -Format portable` extracts the downloaded
original ZIP into a fresh unique directory and runs its PE/embedded-version,
19-plugin, Python, three-language CSV/BIN and captured GUI acceptance. Runtime
search paths exclude build Qt/Conan and test fonts. Both Windows assets must have
unique complete checksum entries matching their actual names and bytes before
and after acceptance; the tested format's integrity record binds those hashes
to its report. IFW installation/version/removal acceptance remains independent.

The manifest requires the exact six format/OS report paths: Windows IFW and
portable, plus AppImage and Debian on each of Ubuntu 22.04 and 24.04. Each report
has an explicit `platform` and `format` identity; missing, duplicate or extra
reports fail, even if their plugin counts happen to match. All 18 language
screenshots and all four original assets with complete unique checksums are
required. Automated acceptance does not replace visual review of screenshots.
Run `python3 tests/test_release_manifest.py -v` for offline coverage of these
gates; successful local tests are not a native package acceptance claim.

Host dependency provenance is read by `host_versions.py`: Qt comes only from
`PJ_QT_VERSION` in `versions.env`, and the host SDK from the exact
`plotjuggler_sdk` requirement in `conanfile.txt`. Payload staging records both in
`release.json`; clean acceptance compares them against the candidate's source.
License collection checks the selected Qt SDK's `mkspecs/qconfig.pri` and the
resolved Conan host graph before collecting notices. Its Qt notice directory and
source URL follow that Qt pin, while the unchanged checksum-locked generic
license texts retain their own source provenance. Independent plugin source/SDK
locks and historical BIN dependency notices do not become host-version claims.

## CSV runtime acceptance

Candidate gates include the real CSV ABI/runtime regressions and the
post-staging FileLoader gate. A new candidate needs all original package checks
and visual acceptance again; previous candidate evidence does not transfer.
See [the fixed source patch contract](plugin-patches/README.md#csv-utf-8-paths-and-runtime-display).
