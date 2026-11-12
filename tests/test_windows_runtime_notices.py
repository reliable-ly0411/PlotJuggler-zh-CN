# SPDX-License-Identifier: MPL-2.0
#!/usr/bin/env python3
"""Validate shipped notice integrity with isolated fixtures; no license-closure claim."""
import importlib.util, json, pathlib, shutil, subprocess, sys, tempfile, unittest

SOURCE = pathlib.Path(__file__).resolve().parents[1]

class NoticeIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='rc11-notice-fixture-')
        root = pathlib.Path(cls.tmp.name)
        shutil.copyfile(SOURCE / '.gitattributes', root / '.gitattributes')
        spec = importlib.util.spec_from_file_location('notice_integrity', SOURCE / 'scripts/stage_fork_notices.py')
        cls.mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(cls.mod)
        cls.root = root

    @classmethod
    def tearDownClass(cls): cls.tmp.cleanup()

    def setUp(self):
        self.case = tempfile.TemporaryDirectory(prefix='case-', dir=self.root)
        self.rootcase = pathlib.Path(self.case.name)
        (self.rootcase / 'licenses').mkdir()
        for name in ('windows-runtime-notices', 'ifw'):
            shutil.copytree(SOURCE / 'licenses' / name, self.rootcase / 'licenses' / name)
        self.metadata = self.rootcase / 'license_ifw.txt'
        shutil.copyfile(SOURCE / 'installer/io.plotjuggler.application/meta/license_ifw.txt', self.metadata)
        self.licenses = self.rootcase / 'licenses'
        self.qt = self.licenses / 'windows-runtime-notices'
        self.ifw = self.licenses / 'ifw'
        self.text = self.qt / json.loads((self.qt / 'upstream-text-manifest.json').read_text())['files'][0]['file']

    def tearDown(self): self.case.cleanup()
    def check(self): self.mod.validate_windows_runtime_materials(self.licenses, self.metadata)
    def test_valid_fixture(self): self.check()
    def test_missing_required_text(self):
        self.text.unlink()
        with self.assertRaises(RuntimeError): self.check()
    def test_changed_required_text(self):
        self.text.write_bytes(b'tampered')
        with self.assertRaises(RuntimeError): self.check()
    def test_empty_notices_directory(self):
        shutil.rmtree(self.qt); self.qt.mkdir()
        with self.assertRaises(RuntimeError): self.check()
    def test_changed_metadata_license(self):
        self.metadata.write_bytes(b'other license')
        with self.assertRaises(RuntimeError): self.check()
    def test_changed_manifest(self):
        with (self.qt / 'upstream-text-manifest.json').open('ab') as f: f.write(b' ')
        with self.assertRaises(RuntimeError): self.check()
    def test_missing_ifw_notice(self):
        (self.ifw / 'NOTICE.txt').unlink()
        with self.assertRaises(RuntimeError): self.check()
    def test_windows_autocrlf_checkout_preserves_pinned_bytes(self):
        repo = self.rootcase / 'repo'; repo.mkdir()
        subprocess.run(['git', 'init', '-q', str(repo)], check=True)
        shutil.copyfile(self.root / '.gitattributes', repo / '.gitattributes')
        shutil.copytree(self.licenses, repo / 'licenses')
        target = repo / 'installer/io.plotjuggler.application/meta/license_ifw.txt'
        target.parent.mkdir(parents=True)
        shutil.copyfile(self.metadata, target)
        subprocess.run(['git', '-C', str(repo), '-c', 'core.autocrlf=true', 'add', '.'], check=True, capture_output=True)
        checkout = self.rootcase / 'checkout'; checkout.mkdir()
        subprocess.run(['git', '-C', str(repo), '-c', 'core.autocrlf=true', 'checkout-index', '-a', '--prefix=' + str(checkout) + '/'], check=True)
        for src in self.licenses.rglob('*'):
            if src.is_file():
                self.assertEqual(src.read_bytes(), (checkout / 'licenses' / src.relative_to(self.licenses)).read_bytes())
        self.assertEqual(self.metadata.read_bytes(), (checkout / 'installer/io.plotjuggler.application/meta/license_ifw.txt').read_bytes())
        self.mod.validate_windows_runtime_materials(checkout / 'licenses', checkout / 'installer/io.plotjuggler.application/meta/license_ifw.txt')

    def test_changed_qt_notice(self):
        (self.qt / 'NOTICE.txt').write_text('different')
        with self.assertRaises(RuntimeError): self.check()

if __name__ == '__main__': unittest.main(verbosity=2)
