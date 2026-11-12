# Conan source backup

Repo-hosted mirror for third-party **source archives** whose upstream host is
unreachable from GitHub Actions runners. CI copies this directory into Conan's
source **download cache** (`core.sources:download_cache`), so a
`conan install --build=missing` is served locally and never depends on a
third-party download host being reachable from a datacenter IP.

## Safety net: ConanCenter's source mirror

CI also sets `core.sources:download_urls` to `["origin", <ConanCenter's
sha256-addressed source mirror>]`, so a recipe whose upstream host refuses a
datacenter IP is retried against the mirror instead of failing the build. That
is what unblocked `elfutils/0.190`, whose only URL, sourceware.org, answered 403
to a release runner.

**`"origin"` must stay first.** Conan treats the two list positions very
differently (`caching_file_downloader.py`): an *origin* failure of any kind is
caught and falls through to the next entry, whereas a *backup* entry that
answers 401/403 raises immediately — only its 404 falls through. A mirror-first
list therefore makes every cold `--build=missing`, on every platform, depend on
that one server staying up and anonymous. Origin-first costs nothing when
upstream is healthy: the mirror is not contacted at all.

Coverage is partial and not contractual: the mirror holds what ConanCenter's CI
happened to back up, which skews old (spot-checked 2026-09: `elfutils/0.190` and
`kissfft/131.1.0` present; `ffmpeg/9.0.1`, `openssl/3.6.4`, `assimp/6.0.5`
absent). So it is a safety net,
not a guarantee; this directory remains the answer whenever a source must be
under our control. The FFmpeg 9.0.1 source is now included here after a Windows
runner timed out connecting to ffmpeg.org and the mirror returned HTTP 401.

## Why this exists

`minizip/1.2.13` (a hard, unconditional requirement of `assimp`, which pj_scene3D
uses for URDF mesh loading) has no source of its own: its Conan recipe downloads
**zlib's** source tarball (minizip lives in zlib's `contrib/minizip/`) from a
single URL, `https://zlib.net/fossils/zlib-1.2.13.tar.gz` — and zlib.net rejects
GitHub-runner IPs with HTTP 415. Any cold Windows CI build was therefore a
lottery: runs could die mid-`conan install` before the missing binary package
was available in the PlotJuggler Conan repository.

The recipe for zlib itself carries a GitHub mirror URL and never fails; the
minizip recipe simply lacks one. An upstream PR adding the mirror to
conan-center's minizip recipe accompanies this change — **once that merges and
the pinned recipe revision picks it up, this directory can be retired.**

`mpdecimal/2.5.0` is the second entry. The `cpython` recipe pins it on macOS only (newer
versions break `_decimal` there), and bytereef.org no longer serves the 2.5.0 tarball:
it answers 404. The ConanCenter mirror answers 401 to anonymous requests. A cold macOS
`conan install` therefore cannot fetch it, and this copy is the only source. Retire it
when the `cpython` recipe moves macOS off 2.5.0.

## Contract

- Each backed-up source is stored as **two files**, exactly as Conan's source
  download-cache layout expects:
  - `<sha256>` — the archive itself, named by the sha256 of its contents. This
    is the same checksum the recipe's `conandata.yml` pins. Conan verifies network
    downloads, but Conan 2.34.0 does **not** rehash an existing local cache hit.
    The 4.x development and candidate-package CI verify all seed hashes
    before copying.
  - `<sha256>.json` — Conan's metadata sidecar (`{"references": {...}}`). Without
    it some Conan versions treat the blob as missing. Generate it with Conan's
    `source()` operation using `core.sources:download_cache=<dir>`, then copy
    the pair out of `<dir>/s/`. Conan 2.34.0 can generate it from a preverified
    blob when the recipe's original URL is used; do not record only a mirror
    URL because a subsequent original-URL request may then re-download.
- CI wires it up in the "Seed Conan source download cache" step of every
  workflow that runs Conan: copy both files into `<download_cache>/s/` and
  append `core.sources:download_cache=<dir>` (plus the mirror's
  `core.sources:download_urls=`) to `global.conf`. One lane escapes it: the
  MSan sanitizer lane switches to a dedicated `CONAN_HOME` (`build.sh`) after
  that step, and only rebuilds gtest + nanoarrow, both GitHub-hosted. A seeded source is
  served locally; anything not seeded falls through to the recipe's own URLs
  as usual. The `<dir>/s/` layout is Conan-internal but observed stable across
  Conan 2.x; if it ever changes, the seed simply misses and CI degrades to the
  old (network-dependent) behavior rather than breaking.

## Current contents

| File (sha256) | What it is | Consumed by |
|---|---|---|
| `b3a24de97a8fdb…` | `zlib-1.2.13.tar.gz` (byte-identical to the official release; also mirrored at `github.com/madler/zlib/releases/download/v1.2.13/`) | `minizip/1.2.13` ← `assimp` |
| `15417edc8e12a5…` | `mpdecimal-2.5.0.tar.gz` (sha256 pinned by the recipe; recovered from the Internet Archive's copy of the bytereef.org release) | `mpdecimal/2.5.0` ← `cpython`, macOS only |
| `cf38e0e28c7e5605…` | `ffmpeg-9.0.1.tar.xz` (12,036,420 bytes; unmodified official release mirrored by MacPorts) | `ffmpeg/9.0.1` |
| `1c0a0fced9b0d87c…` | `glm-1.0.3.zip` (6,112,835 bytes; unmodified official release) | `glm/1.0.3` |

## GLM 1.0.3 provenance

- Original release URL: <https://github.com/g-truc/glm/releases/download/1.0.3/glm-1.0.3.zip>.
- Retrieved without authentication from the same official GitHub release asset:
  <https://api.github.com/repos/g-truc/glm/releases/assets/339451752>, using
  `Accept: application/octet-stream` and the official redirect. The original
  download endpoint returned HTTP 504; the Conan backup returned HTTP 401.
- SHA256: `1c0a0fced9b0d87c7b7bc94e40be490cff6d4c83c25db8488d8f33754e7fdeb2`.
  This matches the Conan `glm/1.0.3` source declaration and the official
  [release asset digest](https://github.com/g-truc/glm/releases/tag/1.0.3).
- The ZIP is byte-identical to the verified source-cache archive. The existing
  Conan-generated metadata retains all original values, including the release
  URL; only a final newline is added to comply with repository formatting.
- The ZIP is unmodified, including `glm/copying.txt` (upstream MIT license).
  No dependency version, recipe revision, download routes, TLS verification,
  or repository permissions change.

## FFmpeg 9.0.1 provenance

- Original release URL: <https://ffmpeg.org/releases/ffmpeg-9.0.1.tar.xz>.
- Retrieved from the MacPorts project's distribution mirror:
  <https://distfiles.macports.org/ffmpeg/ffmpeg-9.0.1.tar.xz>.
- SHA256: `cf38e0e28c7e5605942c4a77755349b0145804a397af37eb1fb4c77cb237f635`.
  This matches the exact locked Conan recipe
  `ffmpeg/9.0.1#e1b7a11d16ed758bcbc0771208d32597`, the
  [ConanCenter source declaration](https://github.com/conan-io/conan-center-index/blob/597f2a3314af809b0be8aaf1f2c2b32c6080a09f/recipes/ffmpeg/all/conandata.yml),
  and the [MacPorts version and checksum record](https://github.com/macports/macports-ports/blob/60403e730a8bfa82bc823625e74ad12243b3506c/multimedia/ffmpeg/Portfile).
- Conan 2.34.0 generated the sidecar by running that locked recipe's `source()`
  against the preverified cache blob; the original source URL is preserved.
- The archive remains unmodified, including upstream licenses. No dependency
  version, recipe revision, TLS verification, or repository permissions change.

## Assimp 6.0.5 official prefetch

The 4.x development and candidate-package workflows additionally run
`scripts/prefetch_assimp_source.py` before dependency resolution, using the same
configured source cache. The existing repository-seed validation stays intact.
The helper fetches only
<https://codeload.github.com/assimp/assimp/tar.gz/refs/tags/v6.0.5>, with normal
TLS verification, no credentials and no redirects. This official archive is
152,371,278 bytes, with recipe-pinned SHA256
`edf3749559c2b7d1f758ffb66fc5bec62186221e623b7f2e8969f17ee46ecb6f`.
The lock remains `assimp/6.0.5#07e27ae90b945b44babfaeffffad5131`; metadata maps
`assimp/6.0.5` to the recipe's original URL,
<https://github.com/assimp/assimp/archive/refs/tags/v6.0.5.tar.gz>.
A new sidecar records acquisition time; reused sidecars retain their timestamp.

Every cache reuse checks size, hash and metadata. New files are downloaded in a
private temporary directory and published without overwriting existing files,
with the complete sidecar first and the verified archive last. Up to three
transport attempts use 30-second socket timeouts and a 180-second per-attempt
soft streaming deadline, with two/four-second retry delays. HTTP framing reads
can outlast that deadline while a peer trickles data; it is not a hard
wall-clock limit. Both workflows give only the source-preparation step a
12-minute timeout as the final cutoff, allowing three nominal attempts plus
setup/backoff overhead. Identity or metadata failures stop the step.

Run the helper before Conan in a job-private, existing absolute cache path.
Symlinks/reparse points, incomplete entries, Conan `.dirty` markers and
existing locks fail closed; unknown entries are never deleted or silently
repaired. A dirty marker would make Conan discard even a verified blob. The
lock serializes helper invocations, not unrelated Conan processes. If interrupted publication
leaves a sidecar or lock, inspect the failed job's cache before a fresh run; do
not remove another active process's files. Each published file is atomic, not
the pair. A failed preparation never proceeds to dependency resolution.

The 145.31 MiB archive is downloaded directly, not committed, split, mirrored
or put in LFS. Its bytes and all licenses remain unchanged. Assimp's top-level
license includes third-party notices and exceptions for `test/models-nonbsd`;
the whole tarball must not be described as exclusively BSD-3-Clause. No other
source URL, dependency pin, binary cache, Conan home, backup policy or release
gate is changed. Passing prefetch does not prove later dependency builds or
Windows package acceptance.

## Adding a new file

```bash
# 1. Fetch the tarball from any trustworthy mirror.
curl -LO <mirror-url>/<tarball>
# 2. Its sha256 MUST match the one pinned in the recipe's conandata.yml.
sha256sum <tarball>
# 3. Store it under that sha256 name, generate the .json via Conan's download
#    cache (see Contract above), commit both, and add a row to the table.
```
