#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Offline transport retry and packaging import regressions."""
import http.client
import importlib.util
import io
from pathlib import Path
import socket
import ssl
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import call, patch
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'packaging/localization'
sys.path.insert(0, str(SCRIPTS))
import download_retry

URL = 'https://github.com/official/project/releases/download/locked/input.zip'


class DownloadRetryTests(unittest.TestCase):
    def test_retryable_http_statuses_use_same_request_and_timeout(self):
        for status in (500, 502, 503, 504):
            with self.subTest(status=status):
                error = urllib.error.HTTPError(URL, status, 'transient', {}, io.BytesIO())
                request = download_retry.urllib.request.Request(URL, headers={'Accept': 'application/octet-stream'})
                response = io.BytesIO(b'complete')
                with patch.object(download_retry.urllib.request, 'urlopen', side_effect=[error, response]) as fetch, \
                     patch.object(download_retry.time, 'sleep') as sleep:
                    self.assertEqual(download_retry.read_url(request, timeout=180), b'complete')
                self.assertEqual(fetch.call_args_list, [call(request, timeout=180)] * 2)
                sleep.assert_called_once_with(2)
                self.assertTrue(error.fp.closed)
                self.assertTrue(response.closed)

    def test_direct_and_wrapped_timeouts_are_retried(self):
        for error in (TimeoutError('read timed out'), urllib.error.URLError(socket.timeout('connect timed out'))):
            with self.subTest(error=error), \
                 patch.object(download_retry.urllib.request, 'urlopen', side_effect=[error, io.BytesIO(b'ok')]) as fetch, \
                 patch.object(download_retry.time, 'sleep') as sleep:
                self.assertEqual(download_retry.read_url(URL, timeout=120), b'ok')
                self.assertEqual(fetch.call_count, 2)
                sleep.assert_called_once_with(2)

    def test_partial_read_timeout_discards_response_and_preserves_read_limit(self):
        partial, complete = io.BytesIO(b'partial'), io.BytesIO(b'complete-and-more')
        with patch.object(partial, 'read', side_effect=TimeoutError('partial read')) as first_read, \
             patch.object(download_retry.urllib.request, 'urlopen', side_effect=[partial, complete]) as fetch, \
             patch.object(download_retry.time, 'sleep') as sleep:
            self.assertEqual(download_retry.read_url(URL, timeout=120, read_limit=8), b'complete')
        first_read.assert_called_once_with(8)
        self.assertEqual(fetch.call_args_list, [call(URL, timeout=120)] * 2)
        sleep.assert_called_once_with(2)
        self.assertTrue(partial.closed)
        self.assertTrue(complete.closed)

    def test_exhaustion_preserves_last_error_and_has_no_final_sleep(self):
        errors = [TimeoutError(str(i)) for i in range(3)]
        with patch.object(download_retry.urllib.request, 'urlopen', side_effect=errors) as fetch, \
             patch.object(download_retry.time, 'sleep') as sleep:
            with self.assertRaises(TimeoutError) as caught:
                download_retry.read_url(URL, timeout=120)
        self.assertIs(caught.exception, errors[-1])
        self.assertEqual(fetch.call_count, 3)
        self.assertEqual(sleep.call_args_list, [call(2), call(4)])

    def test_other_http_errors_fail_without_retry(self):
        for status in (400, 401, 403, 404, 408, 410, 429, 501, 505):
            error = urllib.error.HTTPError(URL, status, 'not retryable', {}, io.BytesIO())
            with self.subTest(status=status), \
                 patch.object(download_retry.urllib.request, 'urlopen', side_effect=error) as fetch, \
                 patch.object(download_retry.time, 'sleep') as sleep:
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    download_retry.read_url(URL, timeout=120)
                self.assertIs(caught.exception, error)
                fetch.assert_called_once_with(URL, timeout=120)
                sleep.assert_not_called()
                self.assertTrue(error.fp.closed)

    def test_tls_permission_and_other_errors_fail_without_retry(self):
        errors = [ssl.SSLCertVerificationError('certificate rejected'), ssl.SSLError('TLS failure'),
                  PermissionError('denied'), ConnectionResetError('reset'),
                  socket.gaierror('DNS failure'), http.client.IncompleteRead(b'partial'),
                  ValueError('invalid data'), urllib.error.URLError('timed out')]
        errors += [urllib.error.URLError(error) for error in errors[:5]]
        for error in errors:
            with self.subTest(error=error), \
                 patch.object(download_retry.urllib.request, 'urlopen', side_effect=error) as fetch, \
                 patch.object(download_retry.time, 'sleep') as sleep:
                with self.assertRaises(type(error)) as caught:
                    download_retry.read_url(URL, timeout=120)
                self.assertIs(caught.exception, error)
                fetch.assert_called_once_with(URL, timeout=120)
                sleep.assert_not_called()


class PackagingImportTests(unittest.TestCase):
    def test_script_entry_points_work_outside_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            for name in ('linux_tools', 'prepare_feedback_tests', 'prepare_payload'):
                with self.subTest(name=name):
                    result = subprocess.run([sys.executable, str(SCRIPTS / (name + '.py')), '--help'],
                                            cwd=directory, capture_output=True, text=True, timeout=15)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn('usage:', result.stdout)

    def test_existing_path_based_import_modes_resolve_shared_helper(self):
        for name in ('linux_tools', 'prepare_feedback_tests'):
            with self.subTest(name=name):
                spec = importlib.util.spec_from_file_location('retry_import_' + name, SCRIPTS / (name + '.py'))
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                self.assertIs(module.download_retry, download_retry)


if __name__ == '__main__':
    unittest.main()
