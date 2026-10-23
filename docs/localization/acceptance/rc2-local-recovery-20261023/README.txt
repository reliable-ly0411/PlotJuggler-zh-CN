RC2 local test recovery record

Historical application source: 6ddc44a4e4c59da374c3d11ea56825a9bc0590da,
fc1582c6938557a8366f8fb76b51944559939462, and
ba34808c6bab7f0f97b55d8d24454076aecec7c6 plus the archived diagnostic patch.
Production integration of that patch: 6a00435fb097f1baa61ebaef1ca3f72f5d245b68.
The integration commit records the original patch SHA256 and moves the identical
helper into pj_widgets while extending call-site coverage. This archive is
historical evidence, not a new product change, release or acceptance claim.

The browser regression was reproduced against the fc1582c6 Linux artifact from
run 39777837101 / artifact 12428247383. AppImage SHA256:
efd63d2f3554775276eec25f026b94a6884b0520f67f4e939304636621276ca7.
Host browser --version returned 0, polluted AppImage environment returned 127
with missing g_once_init_leave_pointer, and the production child-only recovery
returned 0 without changing the application environment. Six behavioral test
cases passed, eight Qt passes including init/cleanup, with Qt 6.11.1. Full
patched-package browser navigation was not part of that local validation.

Recovery inventory
- Original source worktrees and their uncommitted patch remain retained.
- Original AppImage/deb/installer archives remain retained separately; the
  extracted ci-appimage directories are reproducible from those archives.
- Qt 6.11.1 original archives and official checksum provenance remain retained.
- Conan 2.33.0 dependencies are reproducible from the source conan.lock with
  --lockfile-partial, the archived profile/settings and original public remotes.
  Prior libiconv source timeout and backup HTTP 401 remain unresolved historical
  limitations; this cleanup did not retry downloads or change authentication.
- Full source configuration needs SDK plotjuggler_sdk/0.34.1, C++20 and the
  source's documented compiler/options. Regenerate toolchains; never reuse
  absolute paths from these historical CMakeCache snapshots.
- The archived scripts are inert historical text. $TEST_ROOT, $USER_HOME and
  $USER_RUNTIME replace local paths. Recreate dedicated paths deliberately before
  any future use; do not execute the recorded stale-PID resource-control scripts.
- CTest temporary logs include their original failures as well as passes.
  They are not a fresh test run or a replacement for dated evidence files.
- Dependency caches and build binaries are disposable. Conan local metadata,
  profiles and configuration are retained locally. Authentication-capable
  databases, screenshots and personal configuration are excluded from upload.

Only text files listed in files.json and SHA256SUMS.txt belong to this archive.
