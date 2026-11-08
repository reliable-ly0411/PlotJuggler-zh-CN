#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Exercise the ELF export guard without Qt, Conan, or a full application build."""
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / 'pj_app/tests/check_exported_symbols.cmake'
CMAKE = shutil.which('cmake')
CRT_SYMBOLS = [('R', '_IO_stdin_used'), ('B', '__bss_start'),
               ('D', '_edata'), ('B', '_end')]


@unittest.skipUnless(os.name == 'posix' and CMAKE, 'ELF guard harness needs POSIX and CMake')
class ExportedSymbolsGuardTest(unittest.TestCase):
    """Check exact exceptions, failure propagation, and the unchanged leak ceiling."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.target = self.root / 'app'
        self.target.touch()
        self.nm = self.root / 'nm'

    def run_guard(self, *, target=None, nm=None, sanitizers=False):
        """Run the production CMake script, keeping both diagnostics for assertions."""
        return subprocess.run(
            [CMAKE, f'-DTARGET={target or self.target}', f'-DNM={nm or self.nm}',
             f'-DSANITIZERS_ACTIVE={"ON" if sanitizers else "OFF"}', '-P', str(GUARD)],
            capture_output=True, text=True, timeout=30)

    def mock_nm(self, symbols, *, exit_code=0):
        """Supply deterministic nm output while verifying its real invocation flags."""
        output = self.root / 'symbols.txt'
        output.write_text(''.join(f'0000000000001000 {kind} {name}\n'
                                  for kind, name in symbols), encoding='utf-8')
        self.nm.write_text(
            '#!/bin/sh\n'
            '[ "$1" = "-D" ] && [ "$2" = "--defined-only" ] && [ -f "$3" ] || exit 99\n'
            f'cat {shlex.quote(str(output))}\n'
            f'exit {exit_code}\n', encoding='utf-8')
        self.nm.chmod(0o755)

    def test_exact_crt_artifacts_and_existing_abi_data_pass(self):
        self.mock_nm(CRT_SYMBOLS + [('V', '_ZTV1A'), ('W', '_ZN1A1fEv'),
                                   ('B', 'stderr@GLIBC_2.2.5')])
        result = self.run_guard()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('7 exported symbol(s)', result.stdout)

    def test_plain_c_library_symbols_still_fail(self):
        for name in ['png_access_version_number', 'ZSTD_versionNumber', 'BZ2_bzCompress',
                     'lzma_code', 'LZ4_compress_default', 'Py_Initialize',
                     'unrecognized_library_api', '_private_library_api']:
            with self.subTest(name=name):
                self.mock_nm(CRT_SYMBOLS + [('T', name)])
                result = self.run_guard()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(name, result.stderr)
                self.assertIn('exports non-C++ symbol(s)', result.stderr)

    def test_crt_names_require_exact_data_types_and_no_suffix(self):
        for kind, name in CRT_SYMBOLS:
            for wrong_kind, wrong_name in [('T', name), ('W', name), ('A', name),
                                            (kind, name + '_extra'),
                                            (kind, name + '@LIBRARY_1.0')]:
                with self.subTest(kind=wrong_kind, name=wrong_name):
                    self.mock_nm([(wrong_kind, wrong_name)])
                    result = self.run_guard()
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(wrong_name, result.stderr)

    def test_nm_failure_is_fatal_even_with_valid_output(self):
        self.mock_nm(CRT_SYMBOLS, exit_code=7)
        result = self.run_guard()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('nm failed', result.stderr)

    def test_missing_nm_is_fatal(self):
        result = self.run_guard(nm=self.root / 'missing-nm')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('nm failed', result.stderr)

    def test_missing_target_is_fatal(self):
        result = self.run_guard(target=self.root / 'missing-app')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('no such file', result.stderr)

    def test_cpp_mass_leak_and_crt_symbols_count_toward_ceiling(self):
        for crt, count in [(0, 200), (0, 201), (4, 196), (4, 197)]:
            with self.subTest(crt=crt, cpp=count):
                self.mock_nm(CRT_SYMBOLS[:crt] + [('W', f'_Zfixture{i}') for i in range(count)])
                result = self.run_guard()
                if crt + count <= 200:
                    self.assertEqual(result.returncode, 0, result.stderr)
                else:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('200 ceiling', result.stderr)

    def test_sanitizer_exception_remains_instrumentation_only(self):
        self.mock_nm(CRT_SYMBOLS + [('B', '__asan_option_detect_stack_use_after_return')])
        self.assertNotEqual(self.run_guard().returncode, 0)
        result = self.run_guard(sanitizers=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('4 exported symbol(s)', result.stdout)

    @unittest.skipUnless(sys.platform.startswith('linux') and
                         all(shutil.which(tool) for tool in ['cc', 'ar', 'nm']),
                         'compiled ELF regression needs Linux C compiler and binutils')
    def test_real_archive_leak_with_and_without_exclude_libs(self):
        # DSO references make the CRT/linker markers dynamic exports, as can
        # happen with application dependencies; none is defined by the fixture.
        (self.root / 'shared.c').write_text(
            'extern const int _IO_stdin_used;\n'
            'extern char __bss_start, _edata, _end;\n'
            'static const void *markers[] = {&_IO_stdin_used, &__bss_start, &_edata, &_end};\n'
            'int crt_references(void) { return markers[_IO_stdin_used & 3] != 0; }\n', encoding='utf-8')
        (self.root / 'archive.c').write_text(
            'int png_access_version_number(void) { return 1; }\n', encoding='utf-8')
        (self.root / 'main.c').write_text(
            'extern int crt_references(void), png_access_version_number(void);\n'
            'int main(void) { return crt_references() + png_access_version_number(); }\n',
            encoding='utf-8')
        for args in [['cc', '-shared', '-fPIC', 'shared.c', '-o', 'libfixture.so'],
                     ['cc', '-c', 'archive.c', '-o', 'archive.o'],
                     ['ar', 'rcs', 'libfixture.a', 'archive.o']]:
            subprocess.run(args, cwd=self.root, check=True, capture_output=True, timeout=30)
        for protected in [True, False]:
            with self.subTest(protected=protected):
                flags = ['-Wl,--exclude-libs,ALL'] if protected else []
                subprocess.run(['cc', 'main.c', 'libfixture.a', './libfixture.so',
                                '-Wl,--export-dynamic-symbol=png_access_version_number',
                                *flags, '-o', str(self.target)], cwd=self.root,
                               check=True, capture_output=True, timeout=30)
                symbols = subprocess.check_output(
                    ['nm', '-D', '--defined-only', str(self.target)], text=True)
                for kind, name in CRT_SYMBOLS:
                    self.assertIn(f' {kind} {name}\n', symbols)
                result = self.run_guard(nm=shutil.which('nm'))
                if protected:
                    self.assertNotIn('png_access_version_number', symbols)
                    self.assertEqual(result.returncode, 0, result.stderr)
                else:
                    self.assertIn(' T png_access_version_number\n', symbols)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('png_access_version_number', result.stderr)


if __name__ == '__main__':
    unittest.main()
