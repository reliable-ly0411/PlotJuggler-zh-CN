# Ubuntu 22.04 QtCore semaphore backport

This is a dependency repair, not a test-only preload or a forced-serial workaround.
The native hash diagnostic reproduces stack corruption with the original Ubuntu
`5.15.3+dfsg-2ubuntu0.2` QtCore when two threads concurrently release the image
conversion's stack-local semaphore. A clean Core-only hash, ASan or Valgrind run
does not clear this uninstrumented-library race.

Official fixes, preserved here verbatim with their authors and commit IDs:

* [QTBUG-92188 / 2d9cc639](https://github.com/qt/qtbase/commit/2d9cc639a4a7a5e97979a6034364bd67dfa10c23): do not mix futex and QAtomic writes. This change **alone is insufficient** in the local reproducer.
* [QTBUG-102484 / 830b1550](https://github.com/qt/qtbase/commit/830b1550de303dd59c29a87c28e44fa41112b8f4): atomically increment the count and reset the wake-all bit, preventing a releasing thread from accessing a semaphore already destroyed by the acquiring thread.

`SHA256SUMS` pins both patches. `scripts/build_qt5_core_backport.sh` pins the
Ubuntu source and Debian patch archives, applies **all** distro patches first,
and verifies the final semaphore source. Only QtCore is rebuilt; the distro's
QtGui, headers, qmake and other modules remain in use. Original versioned exports,
including the private ABI, must be retained. A runtime `QLibraryInfo` probe also
requires every installed path (including translations and settings) to match
the original distro library. A different installed Qt version
fails closed and requires reviewing the source pin rather than silently
reintroducing old security fixes or mixing unrelated Qt versions.

The original Qt sources retain their copyright and alternative commercial,
LGPLv3, GPLv2/GPLv3 terms. See `LICENSE*` in the source archive and the original
notice in `src/corelib/thread/qsemaphore.cpp`; the patches do not replace these
terms. Candidate AppImages include the exact corresponding source archives,
patches, build script, configuration and licenses under
`usr/share/qt5-core-backport`. This source must accompany any future binary
publication; temporary CI artifact retention is not a source-distribution plan.

To reproduce on Ubuntu 22.04 with the pinned Qt development packages, install
build-essential, cmake, curl, patch, perl, python3, dpkg-dev, qtbase5-dev,
libicu-dev, libglib2.0-dev, libpcre2-dev, libdouble-conversion-dev, zlib1g-dev and
libzstd-dev. Run `bash scripts/build_qt5_core_backport.sh /absolute/empty/output`.
The script stages files in that directory and never installs system libraries.
The corresponding-source bundle preserves the scripts/third_party layout; its
source archives may be copied into the output's `downloads/` directory first.

The Ubuntu22 diagnostic and corresponding AppImage build consume the same
staged library. Neither pixel/hash assertions nor memory-check exit codes are
relaxed. A separate two-thread stress profile covers the observed failure mode.
AppImage validation clears the builder's `LD_LIBRARY_PATH` and verifies the
QtCore `.text` in both AppDir and the final extracted image, because linuxdeploy
may strip debug information or rewrite RPATH.
