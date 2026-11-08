# SPDX-License-Identifier: MPL-2.0
"""Exercise exact source identity, bounded transport and fail-closed publication."""
import hashlib
import http.client
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('assimp_prefetch', ROOT / 'scripts/prefetch_assimp_source.py')
prefetch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prefetch)


class Response(io.BytesIO):
    """A streaming HTTP fixture; tests never open a network connection."""

    def __init__(self, data, headers=None, status=200, url=prefetch.DOWNLOAD_URL):
        super().__init__(data)
        self.headers = headers or {}
        self.status = status
        self.url = url

    def geturl(self):
        return self.url


class AssimpPrefetchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.cache = self.root / 'cache'
        (self.cache / 's').mkdir(parents=True)
        self.data = b'synthetic Assimp source fixture\n'
        self.sha = hashlib.sha256(self.data).hexdigest()
        self.blob = self.cache / 's' / self.sha
        self.sidecar = self.blob.with_suffix('.json')
        self.metadata = {'references': {prefetch.REFERENCE: [prefetch.ORIGINAL_URL]}, 'timestamp': 1234567890}
        for name, value in [('SHA256', self.sha), ('SIZE', len(self.data))]:
            patcher = patch.object(prefetch, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.opener = Mock()
        self.opener.open.side_effect = lambda *a, **kw: Response(self.data)
        patcher = patch.object(prefetch.urllib.request, 'build_opener', return_value=self.opener)
        patcher.start()
        self.addCleanup(patcher.stop)
        sleeper = patch.object(prefetch.time, 'sleep')
        self.sleep = sleeper.start()
        self.addCleanup(sleeper.stop)

    def seed(self):
        self.blob.write_bytes(self.data)
        self.sidecar.write_text(json.dumps(self.metadata), encoding='utf-8')

    def assert_empty(self):
        self.assertEqual(list((self.cache / 's').iterdir()), [])
        self.assertFalse((self.cache / '.assimp-prefetch-lock').exists())

    def assert_transport_rejected(self, message):
        with self.assertRaisesRegex(prefetch.PrefetchError, message):
            prefetch.prefetch(self.cache)
        self.assert_empty()

    def test_verified_download_and_idempotent_reuse(self):
        prefetch.prefetch(self.cache)
        saved_metadata = self.sidecar.read_bytes()
        prefetch.prefetch(self.cache)
        self.assertEqual(self.blob.read_bytes(), self.data)
        self.assertEqual(self.sidecar.read_bytes(), saved_metadata)
        self.assertEqual(json.loads(saved_metadata)['references'], self.metadata['references'])
        self.opener.open.assert_called_once()
        request = self.opener.open.call_args.args[0]
        self.assertEqual(request.full_url, prefetch.DOWNLOAD_URL)
        self.assertEqual(self.opener.open.call_args.kwargs, {'timeout': 30})
        self.assertEqual(list(sorted(p.name for p in (self.cache / 's').iterdir())),
                         sorted([self.sha, self.sha + '.json']))

    def test_known_original_metadata_is_preserved_without_network(self):
        self.seed()
        before = self.sidecar.read_bytes()
        prefetch.prefetch(self.cache)
        self.assertEqual(self.sidecar.read_bytes(), before)
        self.opener.open.assert_not_called()

    def test_wrong_hash_is_not_published_or_retried(self):
        self.opener.open.side_effect = lambda *a, **kw: Response(b'x' * len(self.data))
        self.assert_transport_rejected('SHA256 mismatch')
        self.opener.open.assert_called_once()

    def test_truncated_response_is_not_published(self):
        self.opener.open.side_effect = lambda *a, **kw: Response(self.data[:-1])
        self.assert_transport_rejected('truncated response')

    def test_oversize_response_is_bounded_and_not_published(self):
        self.opener.open.side_effect = lambda *a, **kw: Response(self.data + b'extra')
        self.assert_transport_rejected('exceeds pinned size')

    def test_wrong_or_invalid_content_length_is_rejected(self):
        for length in ['0', str(len(self.data) + 1), 'invalid']:
            with self.subTest(length=length):
                self.opener.open.side_effect = lambda *a, **kw: Response(self.data, {'Content-Length': length})
                self.assert_transport_rejected('response size mismatch')

    def test_exact_content_length_is_accepted(self):
        self.opener.open.side_effect = lambda *a, **kw: Response(self.data, {'Content-Length': str(len(self.data))})
        prefetch.prefetch(self.cache)
        self.assertEqual(self.blob.read_bytes(), self.data)

    def test_changed_response_endpoint_status_or_encoding_is_rejected(self):
        responses = [dict(url='https://other.invalid/archive'), dict(status=206),
                     dict(headers={'Content-Encoding': 'gzip'})]
        for options in responses:
            with self.subTest(options=options):
                self.opener.open.side_effect = lambda *a, **kw: Response(self.data, **options)
                self.assert_transport_rejected('Unexpected Assimp source')

    def test_redirect_handler_blocks_even_another_official_url(self):
        handler = prefetch.NoRedirects()
        for target in [prefetch.ORIGINAL_URL, 'https://other.invalid/archive', 'http://codeload.github.com/archive']:
            with self.subTest(target=target), self.assertRaisesRegex(prefetch.PrefetchError, 'refuses redirects'):
                handler.redirect_request(None, None, 302, 'redirect', {}, target)

    def test_repeated_network_failure_is_bounded(self):
        self.opener.open.side_effect = urllib.error.URLError('fixture offline')
        self.assert_transport_rejected('failed after 3 attempts')
        self.assertEqual(self.opener.open.call_count, 3)
        self.assertEqual([call.args[0] for call in self.sleep.call_args_list], [2, 4])

    def test_transient_http_and_disconnect_retry_only_private_file(self):
        class Disconnected(Response):
            def read1(self, size=-1):
                if self.tell():
                    raise http.client.RemoteDisconnected('fixture disconnect')
                return super().read1(3)
        self.opener.open.side_effect = [
            urllib.error.HTTPError(prefetch.DOWNLOAD_URL, 503, 'temporary', {}, None),
            Disconnected(self.data), Response(self.data)]
        prefetch.prefetch(self.cache)
        self.assertEqual(self.blob.read_bytes(), self.data)
        self.assertEqual(self.opener.open.call_count, 3)
        self.assertEqual(len(list((self.cache / 's').iterdir())), 2)

    def test_permanent_http_error_is_not_retried(self):
        self.opener.open.side_effect = urllib.error.HTTPError(prefetch.DOWNLOAD_URL, 401, 'no access', {}, None)
        self.assert_transport_rejected('HTTP failure: 401')
        self.opener.open.assert_called_once()

    def test_streaming_deadline_is_bounded(self):
        with patch.object(prefetch.time, 'monotonic', side_effect=[0, 181, 200, 381, 400, 581]):
            self.assert_transport_rejected('failed after 3 attempts')
        self.assertEqual(self.opener.open.call_count, 3)

    def test_corrupt_existing_entry_is_preserved_and_not_refetched(self):
        for corrupted, message in [(b'wrong', 'size mismatch'), (b'x' * len(self.data), 'SHA256 mismatch')]:
            with self.subTest(message=message):
                self.seed()
                self.blob.write_bytes(corrupted)
                before = self.sidecar.read_bytes()
                with self.assertRaisesRegex(prefetch.PrefetchError, message):
                    prefetch.prefetch(self.cache)
                self.assertEqual(self.blob.read_bytes(), corrupted)
                self.assertEqual(self.sidecar.read_bytes(), before)
                self.opener.open.assert_not_called()

    def test_invalid_metadata_is_preserved_and_not_refetched(self):
        variants = ['not json', '[]', '{}', json.dumps({'references': {}}),
                    json.dumps(dict(self.metadata, timestamp=True)),
                    json.dumps(dict(self.metadata, references={prefetch.REFERENCE: [prefetch.DOWNLOAD_URL]})),
                    json.dumps(dict(self.metadata, references={'other/1': [prefetch.ORIGINAL_URL]})),
                    ' ' * 16385]
        self.seed()
        for content in variants:
            with self.subTest(content=content[:80]):
                self.sidecar.write_text(content, encoding='utf-8')
                with self.assertRaises(prefetch.PrefetchError):
                    prefetch.prefetch(self.cache)
                self.assertEqual(self.sidecar.read_text(encoding='utf-8'), content)
                self.assertEqual(self.blob.read_bytes(), self.data)
                self.opener.open.assert_not_called()

    def test_partial_final_entries_are_preserved(self):
        for missing in [self.blob, self.sidecar]:
            with self.subTest(missing=missing.name):
                self.seed()
                missing.unlink()
                present = self.sidecar if missing == self.blob else self.blob
                before = present.read_bytes()
                with self.assertRaisesRegex(prefetch.PrefetchError, 'Partial'):
                    prefetch.prefetch(self.cache)
                self.assertFalse(missing.exists())
                self.assertEqual(present.read_bytes(), before)
                self.opener.open.assert_not_called()

    def test_dirty_marker_only_is_preserved_without_download(self):
        marker = self.blob.with_name(self.blob.name + '.dirty')
        marker.write_bytes(b'interrupted Conan download')
        before = marker.read_bytes()
        with self.assertRaisesRegex(prefetch.PrefetchError, 'Dirty Assimp cache entry'):
            prefetch.prefetch(self.cache)
        self.assertEqual(marker.read_bytes(), before)
        self.assertFalse(self.blob.exists())
        self.assertFalse(self.sidecar.exists())
        self.assertEqual(list((self.cache / 's').iterdir()), [marker])
        self.assertFalse((self.cache / '.assimp-prefetch-lock').exists())
        self.opener.open.assert_not_called()

    def test_valid_pair_with_dirty_marker_is_preserved_without_download(self):
        self.seed()
        marker = self.blob.with_name(self.blob.name + '.dirty')
        marker.write_bytes(b'interrupted Conan download')
        before = {path: path.read_bytes() for path in (self.blob, self.sidecar, marker)}
        with self.assertRaisesRegex(prefetch.PrefetchError, 'Dirty Assimp cache entry'):
            prefetch.prefetch(self.cache)
        self.assertEqual({path: path.read_bytes() for path in before}, before)
        self.assertEqual(set((self.cache / 's').iterdir()), set(before))
        self.assertFalse((self.cache / '.assimp-prefetch-lock').exists())
        self.opener.open.assert_not_called()

    def test_unknown_and_stale_temporary_files_are_not_removed(self):
        unknown = self.cache / 's' / 'unknown'
        stale = self.cache / 's' / '.assimp-prefetch-interrupted'
        unknown.write_bytes(b'untouched')
        stale.mkdir()
        (stale / 'archive').write_bytes(b'partial')
        prefetch.prefetch(self.cache)
        self.assertEqual(unknown.read_bytes(), b'untouched')
        self.assertEqual((stale / 'archive').read_bytes(), b'partial')

    def test_existing_lock_is_not_removed(self):
        lock = self.cache / '.assimp-prefetch-lock'
        lock.mkdir()
        (lock / 'owner').write_text('other process', encoding='utf-8')
        with self.assertRaisesRegex(prefetch.PrefetchError, 'lock exists'):
            prefetch.prefetch(self.cache)
        self.assertEqual((lock / 'owner').read_text(encoding='utf-8'), 'other process')
        self.opener.open.assert_not_called()

    def test_second_invocation_cannot_publish_while_first_downloads(self):
        def response(*args, **kwargs):
            with self.assertRaisesRegex(prefetch.PrefetchError, 'lock exists'):
                prefetch.prefetch(self.cache)
            return Response(self.data)
        self.opener.open.side_effect = response
        prefetch.prefetch(self.cache)
        self.assertEqual(self.blob.read_bytes(), self.data)
        self.opener.open.assert_called_once()

    def test_no_overwrite_if_unrelated_writer_races_publication(self):
        original_link = os.link
        foreign = b'foreign bytes'
        def race(source, target):
            if Path(target) == self.blob:
                self.blob.write_bytes(foreign)
            original_link(source, target)
        with patch.object(prefetch.os, 'link', side_effect=race), self.assertRaises(FileExistsError):
            prefetch.prefetch(self.cache)
        self.assertEqual(self.blob.read_bytes(), foreign)
        prefetch.verify_metadata(self.sidecar)
        self.assertEqual(len(list((self.cache / 's').iterdir())), 2)
        self.assertFalse((self.cache / '.assimp-prefetch-lock').exists())

    def test_publication_failure_never_exposes_partial_blob(self):
        original_link = os.link
        def fail_blob(source, target):
            if Path(target) == self.blob:
                raise OSError('fixture full disk')
            original_link(source, target)
        with patch.object(prefetch.os, 'link', side_effect=fail_blob), self.assertRaisesRegex(OSError, 'full disk'):
            prefetch.prefetch(self.cache)
        self.assertFalse(self.blob.exists())
        prefetch.verify_metadata(self.sidecar)
        self.assertEqual(list((self.cache / 's').iterdir()), [self.sidecar])
        with self.assertRaisesRegex(prefetch.PrefetchError, 'Partial'):
            prefetch.prefetch(self.cache)

    def test_metadata_is_published_before_complete_verified_blob(self):
        original_link = os.link
        def inspect(source, target):
            if Path(target) == self.sidecar:
                self.assertFalse(self.blob.exists())
                prefetch.verify_metadata(Path(source))
            else:
                prefetch.verify_metadata(self.sidecar)
                prefetch.verify_blob(Path(source))
            original_link(source, target)
        with patch.object(prefetch.os, 'link', side_effect=inspect):
            prefetch.prefetch(self.cache)

    def test_relative_traversal_and_missing_cache_are_rejected(self):
        for path in [Path('relative'), self.root / '..' / self.root.name / 'cache', self.root / 'absent']:
            with self.subTest(path=path), self.assertRaises((prefetch.PrefetchError, FileNotFoundError)):
                prefetch.prefetch(path)
        self.opener.open.assert_not_called()
        self.assertFalse((self.root / 'absent').exists())

    def test_nonregular_cache_entry_is_rejected(self):
        self.blob.mkdir()
        self.sidecar.write_text(json.dumps(self.metadata), encoding='utf-8')
        with self.assertRaisesRegex(prefetch.PrefetchError, 'Unsafe cache path'):
            prefetch.prefetch(self.cache)
        self.assertTrue(self.blob.is_dir())
        self.opener.open.assert_not_called()

    def test_windows_reparse_points_are_rejected(self):
        info = Mock(st_mode=0o100644, st_file_attributes=0x400)
        with patch.object(Path, 'lstat', return_value=info), self.assertRaisesRegex(prefetch.PrefetchError, 'Unsafe'):
            prefetch.checked_stat(self.blob)

    def test_symlink_paths_and_entries_are_rejected(self):
        probe = self.root / 'probe'
        try:
            probe.symlink_to(self.cache, target_is_directory=True)
        except OSError as error:
            self.skipTest(f'Symlink creation unavailable: {error}')
        with self.assertRaisesRegex(prefetch.PrefetchError, 'Unsafe cache path'):
            prefetch.prefetch(probe)
        # A symlinked parent must fail too, not only the cache leaf.
        with self.assertRaisesRegex(prefetch.PrefetchError, 'Unsafe cache path'):
            prefetch.prefetch(probe / 's')
        self.seed()
        for entry in [self.blob, self.sidecar]:
            with self.subTest(entry=entry.name):
                saved = entry.read_bytes()
                entry.unlink()
                entry.symlink_to(self.root / 'nonexistent')
                with self.assertRaisesRegex(prefetch.PrefetchError, 'Unsafe cache path'):
                    prefetch.prefetch(self.cache)
                self.assertTrue(entry.is_symlink())
                entry.unlink()
                entry.write_bytes(saved)
        self.opener.open.assert_not_called()


class AssimpIntegrationContractTests(unittest.TestCase):
    def test_identity_matches_locked_recipe(self):
        self.assertEqual(prefetch.SHA256, 'edf3749559c2b7d1f758ffb66fc5bec62186221e623b7f2e8969f17ee46ecb6f')
        self.assertEqual(prefetch.SIZE, 152371278)
        self.assertEqual(prefetch.RECIPE, 'assimp/6.0.5#07e27ae90b945b44babfaeffffad5131')
        self.assertEqual(prefetch.ORIGINAL_URL, 'https://github.com/assimp/assimp/archive/refs/tags/v6.0.5.tar.gz')
        self.assertEqual(prefetch.DOWNLOAD_URL, 'https://codeload.github.com/assimp/assimp/tar.gz/refs/tags/v6.0.5')
        lock = json.loads((ROOT / 'conan.lock').read_text(encoding='utf-8'))
        self.assertIn(prefetch.RECIPE, [ref.split('%', 1)[0] for ref in lock['requires']])

    def test_both_workflows_prefetch_configured_cache_before_conan_install(self):
        command = 'python scripts/prefetch_assimp_source.py --cache-dir "$cache_dir"'
        for name in ['zh-4x-ci.yml', 'zh-4x-packages.yml']:
            with self.subTest(workflow=name):
                workflow = (ROOT / '.github/workflows' / name).read_text(encoding='utf-8')
                self.assertEqual(workflow.count(command), 1)
                prepare = workflow.split('      - name: Prepare Conan sources\n', 1)[1]
                block = prepare.split('\n      - ', 1)[0]
                self.assertIn('\n          PY\n          ' + command + '\n', block + '\n')
                self.assertLess(block.index('core.sources:download_cache={sys.argv[2]}'), block.index(command))
                self.assertLess(prepare.index(command), prepare.index('conan install .'))
                self.assertNotIn('continue-on-error', block)
                self.assertNotIn('|| true', block)
                self.assertIn("-m unittest discover -s tests -p ", workflow)

    def test_wall_clock_timeout_is_limited_to_source_preparation(self):
        expected_timeouts = {
            'zh-4x-ci.yml': [
                '    timeout-minutes: 10', '    timeout-minutes: 10',
                '    timeout-minutes: 180', '        timeout-minutes: 12'],
            'zh-4x-packages.yml': [
                '    timeout-minutes: 240', '        timeout-minutes: 12',
                '    timeout-minutes: 45', '    timeout-minutes: 45',
                '    timeout-minutes: 45', '    timeout-minutes: 15'],
        }
        for name, expected in expected_timeouts.items():
            with self.subTest(workflow=name):
                workflow = (ROOT / '.github/workflows' / name).read_text(encoding='utf-8')
                prepare = workflow.split('      - name: Prepare Conan sources\n', 1)[1]
                block = prepare.split('\n      - ', 1)[0]
                self.assertTrue(block.startswith('        timeout-minutes: 12\n        run: |\n'))
                # Job/native/acceptance limits retain their existing values.
                self.assertEqual([line for line in workflow.splitlines()
                                  if 'timeout-minutes:' in line], expected)
                self.assertNotIn('continue-on-error', block)

    def test_cli_has_no_source_override_and_fails_before_network_for_invalid_path(self):
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/prefetch_assimp_source.py'),
                                 '--cache-dir', 'relative'], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Cache path must be absolute', result.stderr)
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/prefetch_assimp_source.py'),
                                 '--cache-dir', 'relative', '--url', 'https://other.invalid'],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('unrecognized arguments', result.stderr)


if __name__ == '__main__':
    unittest.main()
