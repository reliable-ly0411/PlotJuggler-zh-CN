# SPDX-License-Identifier: MPL-2.0
"""Compile and exercise the actual Qt parent/child ownership helper.

Set PJ_QT_PREFIX to a Qt installation with pkg-config metadata. This focused
cross-platform contract is not a substitute for Windows pinned-DLL acceptance.
"""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

SOURCE = r'''
#include "pj_test_child_cleanup.h"
#include <QThread>
#include <cstdio>
#include <csignal>
int main(int argc, char** argv) {
  if (auto result = pjRunWithChildCleanup(argc, argv, 200)) return *result;
  QCoreApplication app(argc, argv);
  const QString mode = app.arguments().at(1);
  PjTestOwnedDirectory fixture(PjTestOwnedDirectory::Cleanup::AfterChildExit);
  QFile out(fixture.path() + "/loaded-image.dll");
  if (!out.open(QIODevice::WriteOnly) || out.write("fixture") != 7) return 9;
  out.close();
  std::printf("CHILD=%s\n", qPrintable(fixture.path())); std::fflush(stdout);
  if (mode == "fail") return 7;
  if (mode == "crash") std::raise(SIGTERM);
  if (mode == "timeout") QThread::sleep(2);
  if (mode == "parent_tamper") QFile::remove(qEnvironmentVariable("PJ_TEST_PARENT_TREE") + "/.pj-test-owner");
  if (mode == "tamper") QFile::remove(fixture.path() + "/.pj-test-owner");
  if (mode == "link") QFile::link(qEnvironmentVariable("OUTSIDE"), fixture.path() + "/foreign");
  return 0;
}
'''

@unittest.skipUnless(os.environ.get('PJ_QT_PREFIX') and shutil.which('g++'), 'PJ_QT_PREFIX and g++ required')
class ChildCleanupContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build = tempfile.TemporaryDirectory(prefix='pj-child-contract-build-')
        source = Path(cls.build.name)/'probe.cpp'
        source.write_text(SOURCE)
        cls.exe = Path(cls.build.name)/'probe'
        env = dict(os.environ, PKG_CONFIG_PATH=str(Path(os.environ['PJ_QT_PREFIX'])/'lib/pkgconfig'))
        flags = subprocess.check_output(['pkg-config', '--cflags', '--libs', 'Qt6Core'], env=env, text=True).split()
        subprocess.run(['g++', '-std=c++20', '-fPIC', str(source), '-I'+str(ROOT/'cmake/test_mains'),
                        '-Wl,-rpath,'+str(Path(os.environ['PJ_QT_PREFIX'])/'lib'), '-o', str(cls.exe), *flags], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.build.cleanup()

    def run_mode(self, mode, extra=None, flags=None):
        directory = tempfile.TemporaryDirectory(prefix='pj-child-contract-case-')
        self.addCleanup(directory.cleanup)
        env = dict(os.environ, TMPDIR=directory.name, TEMP=directory.name, TMP=directory.name)
        env.pop('PJ_TEST_PARENT_TREE', None)
        env.pop('PJ_TEST_PARENT_TOKEN', None)
        if extra: env.update(extra)
        result = subprocess.run([str(self.exe), mode, *(flags or ['--gtest_filter=WidgetCatalogTest.Probe'])],
                                env=env, capture_output=True, text=True, timeout=10)
        return result, Path(directory.name)

    def test_success_parent_removes_retained_child_tree(self):
        result, path = self.run_mode('ok')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('CHILD=', result.stdout)
        self.assertEqual(list(path.iterdir()), [])

    def test_repeated_filters_do_not_bypass_parent(self):
        result, path = self.run_mode('ok', flags=['--gtest_filter=Other.Exact', '--gtest_filter=WidgetCatalogTest.Probe'])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('CHILD=', result.stdout)
        self.assertEqual(list(path.iterdir()), [])

    def test_failure_is_not_hidden_and_is_cleaned(self):
        result, path = self.run_mode('fail')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(path.iterdir()), [])

    def test_timeout_kills_child_before_cleanup(self):
        result, path = self.run_mode('timeout')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('timed out', result.stderr)
        self.assertEqual(list(path.iterdir()), [])

    def test_crash_is_not_hidden_and_is_cleaned(self):
        result, path = self.run_mode('crash')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(path.iterdir()), [])

    def test_missing_marker_refuses_child(self):
        result, _ = self.run_mode('tamper')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Refusing unsafe', result.stderr)

    def test_parent_marker_tamper_refuses_cleanup(self):
        result, path = self.run_mode('parent_tamper')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Refusing unsafe', result.stderr)
        self.assertTrue(list(path.iterdir()))

    def test_forged_parent_lease_refuses_execution(self):
        result, _ = self.run_mode('ok', {'PJ_TEST_PARENT_TREE': '/tmp', 'PJ_TEST_PARENT_TOKEN': 'bad'})
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('CHILD=', result.stdout)

    @unittest.skipIf(os.name == 'nt', 'QFile::link is a Windows shortcut, not a symlink')
    def test_symlink_refuses_cleanup_without_touching_outside(self):
        with tempfile.TemporaryDirectory(prefix='pj-child-outside-') as outside:
            sentinel = Path(outside)/'sentinel'
            sentinel.write_text('keep')
            result, path = self.run_mode('link', {'OUTSIDE': str(sentinel)})
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Refusing unsafe', result.stderr)
            self.assertEqual(sentinel.read_text(), 'keep')
            self.assertTrue(list(path.iterdir()))

if __name__ == '__main__':
    unittest.main()
