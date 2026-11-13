#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Verify artifact transfer and reviewed semantic records before native-kit staging."""
import argparse
from pathlib import Path
from generate_media_fixtures import verify_manifest


def main():
    """The caller obtains expected SHA from the trusted generation artifact record."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--expected-manifest-sha256', required=True)
    args = parser.parse_args()
    verify_manifest(args.directory, args.expected_manifest_sha256)
    print('Four synthetic media files verified; this is not a new decoder or live-MCAP test run.')


if __name__ == '__main__':
    if not __debug__:
        raise SystemExit('Do not disable fixture validation with Python -O')
    main()
