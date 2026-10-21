#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Exercise real ELF dependency discovery and generated Debian control fields."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(all(shutil.which(x) for x in ('gcc', 'dpkg-deb', 'readelf', 'file')),
                     'Linux packaging tools required')
class DebDependenciesTest(unittest.TestCase):
    def build_fixture(self, directory, soname):
        root = Path(directory)
        app = root / 'AppDir'
        for sub in ('bin', 'lib', 'share/applications', 'share/icons/hicolor/256x256/apps',
                    'share/icons/hicolor/scalable/apps'):
            (app / 'usr' / sub).mkdir(parents=True, exist_ok=True)
        shutil.copy2('/bin/true', app / 'usr/bin/plotjuggler4')
        for filename in ('share/applications/plotjuggler4.desktop',
                         'share/icons/hicolor/256x256/apps/plotjuggler4.png',
                         'share/icons/hicolor/scalable/apps/plotjuggler4.svg'):
            (app / 'usr' / filename).write_text('fixture\n', encoding='utf-8')
        provider = root / 'provider.c'
        provider.write_text('int dependency(void) { return 1; }\n', encoding='utf-8')
        consumer = root / 'consumer.c'
        consumer.write_text('extern int dependency(void); int call(void) { return dependency(); }\n', encoding='utf-8')
        subprocess.run(['gcc', '-shared', '-fPIC', str(provider), '-Wl,-soname,' + soname,
                        '-o', str(root / soname)], check=True)
        subprocess.run(['gcc', '-shared', '-fPIC', str(consumer), '-L' + str(root),
                        '-l:' + soname, '-o', str(app / 'usr/lib/consumer.so')], check=True)
        return subprocess.run(['bash', str(ROOT / 'packaging/deb/build_deb.sh'),
                               '--appdir', str(app), '--output-dir', str(root / 'out')],
                              text=True, capture_output=True)

    def test_readline_dependency_preserves_alternative(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.build_fixture(tmp, 'libreadline.so.8')
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            package = next((Path(tmp) / 'out').glob('*.deb'))
            depends = subprocess.check_output(['dpkg-deb', '-f', str(package), 'Depends'], text=True)
            self.assertIn('libreadline8 | libreadline8t64', depends)
            self.assertNotIn(', |,', depends)

    def test_unknown_dependency_remains_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.build_fixture(tmp, 'libunmapped_fixture.so.1')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('libunmapped_fixture.so.1', result.stderr)
            self.assertFalse((Path(tmp) / 'out').exists())


if __name__ == '__main__':
    unittest.main()
