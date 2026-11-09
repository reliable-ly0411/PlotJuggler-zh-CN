# SPDX-License-Identifier: MPL-2.0
"""Exercise the media job's ldd parsing and recorded dependency identities."""
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    'record_dynamic_libraries', ROOT / 'scripts/native-fixtures/record_dynamic_libraries.py')
LD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LD)


class LddProvenanceTests(unittest.TestCase):
    def test_workflow_runs_missing_dependency_gate_before_identity_capture(self):
        workflow = (ROOT / '.github/workflows/zh-4x-ci.yml').read_text(encoding='utf-8')
        media = workflow.split('  windows-native-media:\n', 1)[1].split('\n  windows-native-test-build:', 1)[0]
        ldd = 'LC_ALL=C ldd /usr/bin/ffmpeg /usr/bin/ffprobe'
        missing_gate = "! grep -F 'not found'"
        identities = 'python3 scripts/native-fixtures/record_dynamic_libraries.py "$evidence"'
        self.assertLess(media.index(ldd), media.index(missing_gate))
        self.assertLess(media.index(missing_gate), media.index(identities))
        self.assertLess(media.index(identities), media.index("'tool-provenance.json'"))

    def test_two_inputs_deduplicate_dependencies_and_keep_loader(self):
        output = '''/usr/bin/ffmpeg:
\tlinux-vdso.so.1 (0x00007fff00000000)
\tlibav.so.1 => /usr/lib/libav.so.1 (0x00007fff00000000)
\t/lib64/ld-linux-x86-64.so.2 (0x00007fff00000000)
/usr/bin/ffprobe:
\tlinux-vdso.so.1 (0x00007fff00000000)
\tlibav.so.1 => /usr/lib/libav.so.1 (0x00007fff00000000)
\tlibother.so.2 => /usr/lib/libother.so.2 (0x00007fff00000000)
\t/lib64/ld-linux-x86-64.so.2 (0x00007fff00000000)
'''
        self.assertEqual(LD.dependency_paths(output), [
            '/lib64/ld-linux-x86-64.so.2', '/usr/lib/libav.so.1', '/usr/lib/libother.so.2'])

    def test_missing_dependency_missing_or_duplicate_headers_and_no_paths_fail(self):
        outputs = [
            '/usr/bin/ffmpeg:\n\tlibmissing.so => not found\n/usr/bin/ffprobe:\n\t/lib64/ld.so (0x1)\n',
            '/usr/bin/ffmpeg:\n\t/lib64/ld.so (0x1)\n',
            '/usr/bin/ffmpeg:\n/usr/bin/ffmpeg:\n/usr/bin/ffprobe:\n\t/lib64/ld.so (0x1)\n',
            '/usr/bin/ffmpeg:\n\tlinux-vdso.so.1 (0x1)\n/usr/bin/ffprobe:\n\tlinux-vdso.so.1 (0x1)\n',
        ]
        for output in outputs:
            with self.subTest(output=output), self.assertRaises(AssertionError):
                LD.dependency_paths(output)

    def test_records_hash_real_files_and_preserve_package_query_results(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / 'a.so'; first.write_bytes(b'first library')
            second = root / 'b.so'; second.write_bytes(b'second library')
            paths = sorted(map(str, (second, first)))

            def query(command, **kwargs):
                self.assertEqual(command[:2], ['dpkg-query', '-S'])
                self.assertEqual(kwargs['env']['LC_ALL'], 'C')
                self.assertFalse(kwargs['check'])
                if command[2] == str(first):
                    return subprocess.CompletedProcess(command, 0, 'pkg-a: ' + command[2] + '\n', '')
                return subprocess.CompletedProcess(command, 1, '', 'no owning package\n')

            with patch.object(LD.subprocess, 'run', side_effect=query) as run:
                records = LD.record_paths(paths)
            self.assertEqual(run.call_count, 2)
            self.assertEqual([record['path'] for record in records], paths)
            for record in records:
                path = Path(record['path'])
                self.assertEqual(record['resolved_path'], str(path.resolve(strict=True)))
                self.assertEqual(record['sha256'], hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertEqual(records[0]['dpkg_query_stdout'], 'pkg-a: ' + str(first) + '\n')
            self.assertEqual(records[1]['dpkg_query_exit'], 1)
            self.assertEqual(records[1]['dpkg_query_stderr'], 'no owning package\n')

    def test_missing_file_and_directory_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                LD.record_paths([str(Path(directory) / 'missing.so')])
            with self.assertRaises(AssertionError):
                LD.record_paths([directory])

    def test_unknown_header_is_not_silently_dropped(self):
        output = ('/usr/bin/ffmpeg:\n/usr/bin/ffprobe:\n'
                  '/unexpected-tool-that-does-not-exist:\n\t/lib64/ld.so (0x1)\n')
        paths = LD.dependency_paths(output)
        self.assertIn('/unexpected-tool-that-does-not-exist:', paths)
        with self.assertRaises(FileNotFoundError):
            LD.record_paths(['/unexpected-tool-that-does-not-exist:'])

    def test_optimized_python_is_rejected(self):
        result = subprocess.run([sys.executable, '-O', str(Path(LD.__file__))], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Do not disable dynamic-library validation', result.stderr)

    @unittest.skipUnless(os.name == 'posix' and shutil.which('ldd') and
                         Path('/usr/bin/ffmpeg').is_file() and Path('/usr/bin/ffprobe').is_file(),
                         'real multi-input FFmpeg ldd requires Linux tools')
    def test_real_multi_input_ldd(self):
        output = subprocess.check_output(['ldd', '/usr/bin/ffmpeg', '/usr/bin/ffprobe'],
                                         text=True, env={**os.environ, 'LC_ALL': 'C'})
        self.assertIn('/usr/bin/ffmpeg:\n', output)
        self.assertIn('/usr/bin/ffprobe:\n', output)
        paths = LD.dependency_paths(output)
        without_headers = '\n'.join(line for line in output.splitlines() if line not in LD.HEADERS)
        expected = sorted(set(re.findall(r'(?<![A-Za-z0-9_])(/[^\s()]+)', without_headers)))
        self.assertEqual(paths, expected)
        self.assertTrue(any('ld-linux' in path for path in paths))
        self.assertTrue(all(Path(path).resolve(strict=True).is_file() for path in paths))


if __name__ == '__main__':
    unittest.main()
