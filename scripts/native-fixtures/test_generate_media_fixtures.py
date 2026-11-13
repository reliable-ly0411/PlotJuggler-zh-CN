# SPDX-License-Identifier: MPL-2.0
"""Offline negative contract tests; no tool installation or fixture overwrite."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('media', Path(__file__).with_name('generate_media_fixtures.py'))
MEDIA = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MEDIA)


class FixtureContractTest(unittest.TestCase):
    """Reject wrong dimensions, truncated media and unverified source/tool bytes."""

    def setUp(self):
        self.probe = {'streams': [{'codec_name': 'h264', 'pix_fmt': 'yuv420p', 'width': 640,
                                  'height': 480, 'avg_frame_rate': '30/1', 'nb_read_frames': '120',
                                  'duration': '4.000000', 'has_b_frames': 2}]}

    def test_valid_video(self):
        MEDIA.verify_probe(self.probe, 640, 480, True)

    def test_reject_each_invalid_video_contract(self):
        for field, value in [('codec_name', 'hevc'), ('pix_fmt', 'rgb24'), ('width', 854),
                             ('height', 360), ('avg_frame_rate', '25/1'), ('nb_read_frames', '119'),
                             ('duration', '3.0'), ('has_b_frames', 0)]:
            with self.subTest(field=field):
                probe = copy.deepcopy(self.probe)
                probe['streams'][0][field] = value
                with self.assertRaises(AssertionError):
                    MEDIA.verify_probe(probe, 640, 480, True)

    def test_reject_extra_video_stream(self):
        self.probe['streams'] *= 2
        with self.assertRaises(AssertionError):
            MEDIA.verify_probe(self.probe, 640, 480, False)

    def test_reject_missing_mcap_headers(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(AssertionError):
                MEDIA.verify_headers(Path(directory))

    def test_reject_wrong_package_hash_before_executing_tools(self):
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / 'tool.deb'
            metadata = Path(directory) / 'provenance.json'
            package.write_bytes(b'incorrect package')
            metadata.write_text('{"sha256":"incorrect"}')
            with patch.object(MEDIA.subprocess, 'Popen') as popen:
                with self.assertRaises(AssertionError):
                    MEDIA.package_identity(package, metadata, {})
                popen.assert_not_called()

    def test_timed_out_generation_preserves_partial_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            code = ("import sys,time,subprocess; sys.stdout.buffer.write(b'partial-out\\x00'); "
                    "sys.stdout.flush(); sys.stderr.buffer.write(b'partial-err\\xff'); "
                    "sys.stderr.flush(); subprocess.Popen([sys.executable,'-c','import time; time.sleep(5)']); "
                    "time.sleep(5)")
            with self.assertRaises(subprocess.TimeoutExpired):
                MEDIA.run_logged([sys.executable, '-u', '-c', code], root, root, 'timeout', timeout=0.3)
            self.assertEqual((root / 'timeout.stdout').read_bytes(), b'partial-out\x00')
            self.assertEqual((root / 'timeout.stderr').read_bytes(), b'partial-err\xff')

    def test_logged_success_and_failure_keep_both_streams(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            command = [sys.executable, '-c', "import sys; print('out'); print('err', file=sys.stderr)"]
            self.assertEqual(MEDIA.run_logged(command, root, root, 'success'), b'out\n')
            self.assertEqual((root / 'success.stderr').read_bytes(), b'err\n')
            failure = [sys.executable, '-c', "import sys; print('bad'); print('why', file=sys.stderr); sys.exit(4)"]
            with self.assertRaisesRegex(AssertionError, 'exited 4'):
                MEDIA.run_logged(failure, root, root, 'failure')
            self.assertEqual((root / 'failure.stdout').read_bytes(), b'bad\n')
            self.assertEqual((root / 'failure.stderr').read_bytes(), b'why\n')

    def test_package_field_timeout_is_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / 'tool.deb'
            package.write_bytes(b'archive')
            metadata = root / 'provenance.json'
            metadata.write_text(json.dumps({'sha256': MEDIA.digest(package)}))
            with patch.object(MEDIA.subprocess, 'check_output',
                              side_effect=subprocess.TimeoutExpired('dpkg-deb', 0.3)) as check, \
                    patch.object(MEDIA.subprocess, 'Popen') as popen:
                with self.assertRaises(subprocess.TimeoutExpired):
                    MEDIA.package_identity(package, metadata, {}, timeout=0.3)
                self.assertEqual(check.call_args.kwargs['timeout'], 0.3)
                popen.assert_not_called()

    def test_package_stream_timeout_stops_owned_process_group(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / 'tool.deb'
            package.write_bytes(b'archive')
            metadata = root / 'provenance.json'
            metadata.write_text(json.dumps({'sha256': MEDIA.digest(package), 'package': 'ffmpeg',
                                            'version': '1', 'url': 'https://deb.debian.org/a.deb',
                                            'apt_signature_evidence': 'CI must verify'}))
            real_popen = subprocess.Popen
            spawned = []

            def blocked_stream(*_args, **kwargs):
                self.assertTrue(kwargs.pop('start_new_session'))
                child = real_popen([sys.executable, '-c', 'import time; time.sleep(5)'],
                                   start_new_session=True, **kwargs)
                spawned.append(child)
                return child

            with patch.object(MEDIA.subprocess, 'check_output', side_effect=['ffmpeg\n', '1\n']), \
                    patch.object(MEDIA.subprocess, 'Popen', side_effect=blocked_stream):
                with self.assertRaises(subprocess.TimeoutExpired):
                    MEDIA.package_identity(package, metadata, {}, timeout=0.3)
            self.assertEqual(len(spawned), 1)
            self.assertIsNotNone(spawned[0].poll())

    def test_existing_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            sentinel = output / 'manifest.json'
            sentinel.write_text('keep this evidence')
            argv = ['generator', '--output', directory, '--mcap-include', directory,
                    '--mcap-license', '/unused', '--ffmpeg', '/unused', '--ffprobe', '/unused', '--cxx', '/unused',
                    '--tool-package', '/unused', '--tool-provenance', '/unused']
            with patch.object(sys, 'argv', argv), patch.object(MEDIA, 'verify_headers', return_value={'license_sha256': 'locked'}), \
                    patch.object(MEDIA, 'digest', return_value='locked'), \
                    patch.object(MEDIA, 'package_identity'):
                with self.assertRaises(AssertionError):
                    MEDIA.main()
            self.assertEqual(sentinel.read_text(), 'keep this evidence')

    def test_bad_media_count_and_manifest_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in MEDIA.FILES:
                (root / name).write_bytes(b'synthetic test placeholder')
            video = copy.deepcopy(self.probe['streams'][0])
            large = dict(video, width=1920, height=1080)
            manifest = {'schema': 1, 'synthetic': True,
                        'files': {name: {'bytes': (root / name).stat().st_size,
                                         'sha256': MEDIA.digest(root / name)} for name in MEDIA.FILES},
                        'semantics': {'video': {MEDIA.FILES[0]: video, MEDIA.FILES[1]: large},
                                      'mcap': {MEDIA.FILES[2]: {'channels': 1, 'messages_per_channel': 90,
                                                'all_payloads_timestamps_sequences_validated': True},
                                               MEDIA.FILES[3]: {'channels': 4, 'messages_per_channel': 8400,
                                                'all_payloads_timestamps_sequences_validated': True}}}}
            path = root / 'manifest.json'
            path.write_text(json.dumps(manifest))
            original = MEDIA.digest(path)
            MEDIA.verify_manifest(root, original)
            (root / MEDIA.FILES[0]).write_bytes(b'corrupt media')
            with self.assertRaises(AssertionError):
                MEDIA.verify_manifest(root, original)
            (root / MEDIA.FILES[0]).write_bytes(b'synthetic test placeholder')
            manifest['semantics']['mcap'][MEDIA.FILES[2]]['messages_per_channel'] = 89
            path.write_text(json.dumps(manifest))
            with self.assertRaises(AssertionError):
                MEDIA.verify_manifest(root)
            with self.assertRaises(AssertionError):
                MEDIA.verify_manifest(root, original)

    def test_optimized_python_is_rejected(self):
        result = subprocess.run([sys.executable, '-O', str(Path(MEDIA.__file__)), '--help'],
                                capture_output=True, text=True, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Do not disable fixture validation', result.stderr)


if __name__ == '__main__':
    unittest.main()
