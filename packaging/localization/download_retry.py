# SPDX-License-Identifier: MPL-2.0
"""Retry only transient transport failures; callers still validate every byte."""
import sys
import time
import urllib.error
import urllib.request


def read_url(request, *, timeout, read_limit=None):
    """Read a fresh response on each of at most three attempts, without writing.

    Only HTTP 500/502/503/504 and explicit socket/connect/read timeouts qualify.
    urllib's timeout bounds blocking socket operations, not total wall-clock time.
    JSON, identity and integrity validation belong outside this retry boundary.
    """
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read() if read_limit is None else response.read(read_limit)
        except (urllib.error.URLError, TimeoutError) as error:
            if isinstance(error, urllib.error.HTTPError):
                retryable = error.code in (500, 502, 503, 504)
                error.close()
            else:
                reason = error.reason if isinstance(error, urllib.error.URLError) else error
                retryable = isinstance(reason, TimeoutError)
            if not retryable or attempt == 3:
                raise
            delay = 2 ** attempt
            print(f'Transient download failure ({type(error).__name__}); '
                  f'retrying attempt {attempt + 1}/3 in {delay}s', file=sys.stderr)
            time.sleep(delay)
