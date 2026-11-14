#!/usr/bin/env python3
"""Exercise the actual shell -> qmake -> make -> GCC path-map boundary."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/build_qt5_core_backport.sh'

class PathMapTest(unittest.TestCase):
    def flags(self, path, check=True):
        return subprocess.run(['bash', str(SCRIPT), str(path), '--print-pathmap-flags'],
                              text=True, capture_output=True, check=check)

    def test_reject_expression_characters(self):
        for suffix in ['$bad', '(bad)', 'bad,part', 'bad#part', 'bad=part', 'bad\npart', "bad'part", 'bad"part', 'bad\\part']:
            with self.subTest(suffix=suffix):
                self.assertNotEqual(self.flags('/tmp/' + suffix, False).returncode, 0)

    def test_qmake_real_c_and_cpp_compile(self):
        qmake = os.environ.get('PJ_TEST_QMAKE', 'qmake')
        try:
            subprocess.run([qmake, '-v'], check=True, capture_output=True)
        except (OSError, subprocess.CalledProcessError):
            self.fail('working qmake required; set PJ_TEST_QMAKE')
        with tempfile.TemporaryDirectory(prefix='qt-pathmap-') as tmp:
            source = Path(tmp) / '中文 source space'
            source.mkdir()
            build = Path(tmp) / 'build'
            build.mkdir()
            (source / 'cpart.c').write_text('#line 1 "' + str(source / 'cpart.c') + '"\nconst char *cpath(void) { return __FILE__; }\n')
            (source / 'main.cpp').write_text('#line 1 "' + str(source / 'main.cpp') + '"\n#include <cstdio>\nextern "C" const char *cpath(void);\nint main(){puts(__FILE__); puts(cpath());}\n')
            project = build / 'probe.pro'
            project.write_text('TEMPLATE = app\nTARGET = probe\nCONFIG -= qt\nSOURCES = "' + str(source / 'main.cpp') + '" "' + str(source / 'cpart.c') + '"\n')
            flags = self.flags(source).stdout.strip()
            subprocess.run([qmake, str(project), 'QMAKE_CFLAGS+=' + flags,
                            'QMAKE_CXXFLAGS+=' + flags], cwd=build, check=True, capture_output=True)
            subprocess.run(['make'], cwd=build, check=True, capture_output=True)
            result = subprocess.check_output([str(build / 'probe')], text=True)
            self.assertEqual(result.splitlines(), ['/usr/src/qt5-core-backport/main.cpp', '/usr/src/qt5-core-backport/cpart.c'])
            self.assertNotIn(str(source).encode(), (build / 'probe').read_bytes())

if __name__ == '__main__':
    unittest.main()
