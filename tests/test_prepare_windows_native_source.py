# SPDX-License-Identifier: MPL-2.0
"""Exercise source relocation with small local synthetic Git repositories."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('native_source', ROOT / 'scripts/windows/prepare_native_source.py')
source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source)


@unittest.skipUnless(shutil.which('git'), 'Git is unavailable')
class NativeSourceCopyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='native source with space ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.module = self.root / 'module'; self.module.mkdir()
        self.parent = self.root / 'checkout'; self.parent.mkdir()
        self.git('init', '-q', cwd=self.module)
        (self.module / 'fixture.txt').write_text('synthetic fixture', encoding='utf-8')
        self.git('add', 'fixture.txt', cwd=self.module)
        self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'synthetic module', cwd=self.module)
        self.git('init', '-q', cwd=self.parent)
        (self.parent / 'main.txt').write_text('synthetic source', encoding='utf-8')
        self.git('-c', 'protocol.file.allow=always', 'submodule', 'add', '-q', self.module.as_uri(), 'deps/module', cwd=self.parent)
        self.git('config', '-f', '.gitmodules', 'submodule.deps/module.url', 'https://github.com/example/module.git', cwd=self.parent)
        self.git('add', 'main.txt', '.gitmodules', 'deps/module', cwd=self.parent)
        self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'synthetic parent', cwd=self.parent)
        self.sha = self.git('rev-parse', 'HEAD', cwd=self.parent)
        self.destination = self.root / 'dest' / 's'; self.destination.parent.mkdir()

    def git(self, *args, cwd):
        proc = subprocess.run(['git', *map(str, args)], cwd=cwd, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return proc.stdout.strip()

    def test_exact_clone_has_self_contained_objects_and_submodule_gitdir(self):
        result = source.clone(self.parent, self.destination, self.sha, 'https://github.com/example/project.git')
        self.assertEqual(result['source_sha'], self.sha)
        self.assertEqual(result['source_tree'], self.git('rev-parse', 'HEAD^{tree}', cwd=self.parent))
        self.assertEqual(result['submodules']['deps/module'], self.git('rev-parse', 'HEAD', cwd=self.module))
        self.assertEqual((self.destination / 'deps/module/fixture.txt').read_text(encoding='utf-8'), 'synthetic fixture')
        self.assertEqual(self.git('remote', 'get-url', 'origin', cwd=self.destination), 'https://github.com/example/project.git')
        self.assertEqual(self.git('remote', 'get-url', 'origin', cwd=self.destination / 'deps/module'), 'https://github.com/example/module.git')
        gitdir = Path(self.git('rev-parse', '--absolute-git-dir', cwd=self.destination / 'deps/module')).resolve()
        self.assertTrue(gitdir.is_relative_to((self.destination / '.git').resolve()))
        self.assertFalse(any((self.destination / '.git').rglob('alternates')))
        self.assertEqual(self.git('status', '--porcelain=v1', '--untracked-files=all', cwd=self.destination), '')

    def test_wrong_or_dirty_source_and_existing_destination_fail(self):
        with self.assertRaises(source.SourceError): source.clone(self.parent, self.destination, '0' * 40, 'https://github.com/example/project.git')
        (self.parent / 'untracked').write_text('do not copy', encoding='utf-8')
        with self.assertRaises(source.SourceError): source.clone(self.parent, self.destination, self.sha, 'https://github.com/example/project.git')
        (self.parent / 'untracked').unlink()
        self.destination.mkdir()
        with self.assertRaises(source.SourceError): source.clone(self.parent, self.destination, self.sha, 'https://github.com/example/project.git')

    def test_submodule_dirty_and_credential_urls_fail(self):
        (self.parent / 'deps/module/fixture.txt').write_text('modified', encoding='utf-8')
        with self.assertRaises(source.SourceError): source.clone(self.parent, self.destination, self.sha, 'https://github.com/example/project.git')
        with self.assertRaises(source.SourceError): source.clone(self.parent, self.destination, self.sha, 'https://user:secret@github.com/example/project.git')

    def test_untrusted_git_environment_and_template_hooks_are_ignored(self):
        template = self.root / 'untrusted-template'; hooks = template / 'hooks'; hooks.mkdir(parents=True)
        marker = self.root / 'HOOK-MUST-NOT-RUN'
        hook = hooks / 'post-checkout'; hook.write_text('#!/bin/sh\necho unsafe > "' + str(marker) + '"\n', encoding='utf-8')
        hook.chmod(0o755)
        hostile = {'GIT_DIR': str(self.root / 'missing-git-dir'), 'GIT_COMMON_DIR': str(self.root / 'missing-common'),
                   'GIT_OBJECT_DIRECTORY': str(self.root / 'missing-objects'),
                   'GIT_ALTERNATE_OBJECT_DIRECTORIES': str(self.root / 'untrusted-objects'),
                   'GIT_INDEX_FILE': str(self.root / 'untrusted-index'), 'GIT_TEMPLATE_DIR': str(template),
                   'GIT_CONFIG_COUNT': '1', 'GIT_CONFIG_KEY_0': 'core.hooksPath', 'GIT_CONFIG_VALUE_0': str(hooks)}
        with mock.patch.dict(os.environ, hostile):
            source.clone(self.parent, self.destination, self.sha, 'https://github.com/example/project.git')
        self.assertFalse(marker.exists())
        self.assertFalse((self.destination / '.git/hooks/post-checkout').exists())
        self.assertFalse((self.destination / '.git/objects/info/alternates').exists())

    def test_checkout_auth_config_is_not_carried_to_clone_or_submodule(self):
        credentials = self.root / 'git-credentials-synthetic.config'
        credentials.write_text('[http "https://github.com/"]\n\textraheader = synthetic-secret\n', encoding='utf-8')
        global_config = self.root / 'pj-checkout.gitconfig'
        self.git('config', '--file', global_config, 'include.path', credentials, cwd=self.parent)
        self.git('config', '--local', 'includeIf.gitdir:' + (self.parent / '.git').as_posix() + '.path',
                 credentials, cwd=self.parent)
        with mock.patch.dict(os.environ, {'GIT_CONFIG_GLOBAL': str(global_config)}):
            source.clone(self.parent, self.destination, self.sha, 'https://github.com/example/project.git')
        for config in (self.destination / '.git/config', self.destination / '.git/modules/deps/module/config'):
            text = config.read_text(encoding='utf-8')
            self.assertNotIn('synthetic-secret', text)
            self.assertNotIn('git-credentials-synthetic.config', text)
            self.assertNotIn('includeIf', text)


if __name__ == '__main__':
    unittest.main()
