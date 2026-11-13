#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Prefetch one exact official Assimp archive into the configured Conan cache.

Run before Conan consumers, in a job-private cache. The lock serializes this
helper, not arbitrary Conan writers. Unknown, partial or corrupt entries fail
closed and are never repaired or removed automatically. The CI preparation
step supplies the final wall-clock timeout beyond the soft streaming deadline.
"""
import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import stat
import tempfile
import time
import urllib.error
import urllib.request

REFERENCE = 'assimp/6.0.5'
RECIPE = REFERENCE + '#07e27ae90b945b44babfaeffffad5131'
ORIGINAL_URL = 'https://github.com/assimp/assimp/archive/refs/tags/v6.0.5.tar.gz'
DOWNLOAD_URL = 'https://codeload.github.com/assimp/assimp/tar.gz/refs/tags/v6.0.5'
SHA256 = 'edf3749559c2b7d1f758ffb66fc5bec62186221e623b7f2e8969f17ee46ecb6f'
SIZE = 152371278
ATTEMPTS = 3
SOCKET_TIMEOUT = 30
ATTEMPT_SECONDS = 180
CHUNK_SIZE = 1024 * 1024


class PrefetchError(RuntimeError):
    """Fail preparation rather than let Conan trust an unverified cache hit."""


class NoRedirects(urllib.request.HTTPRedirectHandler):
    """The single approved endpoint must serve the bytes itself."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise PrefetchError('Assimp prefetch refuses redirects')


def checked_stat(path, directory=False):
    """Reject symlinks, Windows reparse points and non-regular entries."""
    info = path.lstat()
    if (stat.S_ISLNK(info.st_mode)
            or getattr(info, 'st_file_attributes', 0) & 0x400
            or not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))):
        raise PrefetchError(f'Unsafe cache path: {path}')
    return info


def cache_paths(cache):
    """Require the existing, absolute cache prepared by the preceding CI step."""
    if not cache.is_absolute() or '..' in cache.parts:
        raise PrefetchError('Cache path must be absolute, without parent traversal')
    for path in (*reversed(cache.parents), cache, cache / 's'):
        checked_stat(path, directory=True)
    return cache / 's' / SHA256, cache / 's' / (SHA256 + '.json')


def verify_blob(path):
    """Conan does not rehash cache hits, so verify every reuse here."""
    if checked_stat(path).st_size != SIZE:
        raise PrefetchError('Assimp source size mismatch')
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(CHUNK_SIZE), b''):
            digest.update(chunk)
    if digest.hexdigest() != SHA256:
        raise PrefetchError('Assimp source SHA256 mismatch')


def verify_metadata(path):
    """Require the recipe's original URL; a codeload-only entry misses Conan."""
    if checked_stat(path).st_size > 16384:
        raise PrefetchError('Assimp metadata is too large')
    try:
        metadata = json.loads(path.read_text(encoding='utf-8'))
        valid = (isinstance(metadata, dict)
                 and metadata.get('references') == {REFERENCE: [ORIGINAL_URL]}
                 and type(metadata.get('timestamp')) is int
                 and metadata['timestamp'] > 0)
    except (ValueError, UnicodeError):
        valid = False
    if not valid:
        raise PrefetchError('Invalid Assimp source metadata')


def download_once(path, opener):
    """Bound response size with a soft streaming deadline; never redirect."""
    deadline = time.monotonic() + ATTEMPT_SECONDS
    request = urllib.request.Request(DOWNLOAD_URL, headers={
        'Accept-Encoding': 'identity', 'User-Agent': 'PlotJuggler-source-prefetch'})
    with opener.open(request, timeout=SOCKET_TIMEOUT) as response:
        if response.status != 200 or response.geturl() != DOWNLOAD_URL:
            raise PrefetchError('Unexpected Assimp source response')
        length = response.headers.get('Content-Length')
        if length is not None and length != str(SIZE):
            raise PrefetchError('Assimp response size mismatch')
        if response.headers.get('Content-Encoding', 'identity') != 'identity':
            raise PrefetchError('Unexpected Assimp source encoding')
        digest = hashlib.sha256()
        total = 0
        with path.open('xb') as target:
            while True:
                if time.monotonic() >= deadline:
                    raise TimeoutError('Assimp download deadline exceeded')
                # read1 avoids waiting to fill our buffer, but chunk headers
                # can still trickle past the soft deadline inside HTTP parsing.
                # The CI step timeout provides the final wall-clock cutoff.
                chunk = response.read1(min(CHUNK_SIZE, SIZE - total + 1))
                if time.monotonic() >= deadline:
                    raise TimeoutError('Assimp download deadline exceeded')
                if not chunk:
                    break
                total += len(chunk)
                if total > SIZE:
                    raise PrefetchError('Assimp response exceeds pinned size')
                digest.update(chunk)
                target.write(chunk)
            if total != SIZE:
                raise PrefetchError('Assimp source size mismatch (truncated response)')
            if digest.hexdigest() != SHA256:
                raise PrefetchError('Assimp source SHA256 mismatch')
            target.flush()
            os.fsync(target.fileno())


def download(path):
    """Retry only bounded transient transport failures, not identity failures."""
    opener = urllib.request.build_opener(NoRedirects())
    for attempt in range(1, ATTEMPTS + 1):
        try:
            download_once(path, opener)
            return
        except (urllib.error.URLError, TimeoutError, ConnectionError, http.client.HTTPException) as error:
            if isinstance(error, urllib.error.HTTPError) and error.code not in (408, 429, 500, 502, 503, 504):
                raise PrefetchError(f'Assimp HTTP failure: {error.code}') from error
            if attempt == ATTEMPTS:
                raise PrefetchError(f'Assimp download failed after {ATTEMPTS} attempts: {error}') from error
            print(f'Assimp download attempt {attempt}/{ATTEMPTS} failed: {error}', flush=True)
            # This file is private to this invocation, never a cache key.
            path.unlink(missing_ok=True)
            time.sleep(2 * attempt)


def prefetch(cache):
    """Publish complete files without replacing another writer's entries."""
    blob, metadata = cache_paths(cache)
    lock = cache / '.assimp-prefetch-lock'
    try:
        lock.mkdir()
    except FileExistsError as error:
        raise PrefetchError('Assimp prefetch lock exists; another run or interrupted run needs review') from error
    try:
        # Conan removes dirty blobs before lookup, even after our verification.
        if os.path.lexists(blob.with_name(blob.name + '.dirty')):
            raise PrefetchError('Dirty Assimp cache entry; preserve it for review')
        present = [os.path.lexists(path) for path in (blob, metadata)]
        if any(present):
            if not all(present):
                raise PrefetchError('Partial Assimp cache entry; preserve it for review')
            verify_metadata(metadata)
            verify_blob(blob)
            result = 'reused'
        else:
            with tempfile.TemporaryDirectory(prefix='.assimp-prefetch-', dir=cache / 's') as temporary:
                staged = Path(temporary)
                source = staged / 'archive'
                download(source)
                verify_blob(source)
                sidecar = staged / 'metadata'
                with sidecar.open('x', encoding='utf-8') as target:
                    json.dump({'references': {REFERENCE: [ORIGINAL_URL]},
                               'timestamp': int(time.time())}, target)
                    target.write('\n')
                    target.flush()
                    os.fsync(target.fileno())
                verify_metadata(sidecar)
                # Same-filesystem hard links atomically expose only completed
                # bytes and fail if a destination exists. Metadata goes first;
                # interruption cannot expose an unverified blob. A sidecar left
                # by interrupted publication is retained for manual review.
                os.link(sidecar, metadata)
                os.link(source, blob)
                verify_metadata(metadata)
                verify_blob(blob)
            result = 'downloaded'
        print(f'Assimp source {result}: {REFERENCE}, {SIZE} bytes, SHA256 {SHA256}', flush=True)
    finally:
        # Only the empty directory created by this invocation is removed.
        lock.rmdir()


def main():
    """The CLI deliberately has no URL/hash override or Conan-home mutation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache-dir', type=Path, required=True)
    args = parser.parse_args()
    try:
        lock = json.loads((Path(__file__).resolve().parents[1] / 'conan.lock').read_text(encoding='utf-8'))
        if not any(ref.split('%', 1)[0] == RECIPE for ref in lock['requires']):
            raise PrefetchError('Assimp recipe lock differs from the reviewed source identity')
        prefetch(args.cache_dir)
    except (OSError, ValueError, KeyError, PrefetchError) as error:
        parser.exit(1, f'Assimp source prefetch failed: {error}\n')


if __name__ == '__main__':
    main()
