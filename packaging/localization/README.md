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
real app `--version`, Python, and every expected plugin/version. It then restores
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
