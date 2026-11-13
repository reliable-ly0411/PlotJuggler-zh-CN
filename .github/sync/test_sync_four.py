# SPDX-License-Identifier: MPL-2.0
"""Offline integration checks for source-only synchronization."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('sync_four', Path(__file__).with_name('sync_four.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
CONFIG = {'upstream_repository': 'PlotJuggler/PlotJuggler', 'upstream_branch': 'main',
          'sync_branch': 'zh-CN-4.x-dev'}

class SyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = Path.cwd()
        os.chdir(self.tmp.name)
        self.git('init', '-b', 'zh-CN-4.x-dev')
        self.git('config', 'user.name', 'Test')
        self.git('config', 'user.email', 'test@example.invalid')
        Path('.github').mkdir()
        Path('.github/workflow.yml').write_text('trusted')
        Path('source.txt').write_text('base')
        self.commit('base')
        self.base = self.git('rev-parse', 'HEAD')
        self.git('branch', 'official')
        self.commands = []
        real_git = module.git
        def fake_fetch(*args, **kwargs):
            self.commands.append(args)
            if args[0] == 'fetch':
                Path('.git/FETCH_HEAD').write_text(self.upstream + '\n')
                return subprocess.CompletedProcess(args, 0, '', '')
            return real_git(*args, **kwargs)
        self.fetch = patch.object(module, 'git', fake_fetch)
        self.fetch.start()

    def tearDown(self):
        self.fetch.stop()
        os.chdir(self.old)
        self.tmp.cleanup()

    def git(self, *args):
        return subprocess.check_output(['git', *args], text=True, stderr=subprocess.DEVNULL).strip()

    def commit(self, message):
        self.git('add', '.')
        self.git('commit', '-m', message)

    def advance(self, conflict=False):
        self.git('checkout', 'official')
        Path('source.txt').write_text('upstream')
        Path('.github/workflow.yml').write_text('unreviewed upstream automation')
        self.commit('upstream')
        self.upstream = self.git('rev-parse', 'HEAD')
        self.git('checkout', 'zh-CN-4.x-dev')
        if conflict:
            Path('source.txt').write_text('local change')
            self.commit('local')

    def test_noop(self):
        self.upstream = self.base
        self.assertFalse(module.sync(CONFIG)['changed'])
        self.assertIn(('fetch', '--no-recurse-submodules', '--no-tags',
                       'https://github.com/PlotJuggler/PlotJuggler.git', 'refs/heads/main'),
                      self.commands)
        self.assertFalse(any(c[0] == 'push' for c in self.commands))

    def test_dry_run_preserves_policy_and_ancestry(self):
        self.advance()
        result = module.sync(CONFIG)
        self.assertTrue(result['changed'])
        self.assertEqual(Path('source.txt').read_text(), 'upstream')
        self.assertEqual(Path('.github/workflow.yml').read_text(), 'trusted')
        self.assertEqual(self.git('rev-parse', 'HEAD^2'), self.upstream)
        self.assertFalse(any(c[0] == 'push' for c in self.commands))

    def test_push_updates_only_development_ref(self):
        self.advance()
        with tempfile.TemporaryDirectory() as remote:
            self.git('init', '--bare', remote)
            self.git('remote', 'add', 'origin', remote)
            module.sync(CONFIG, push=True)
            self.assertEqual(self.git('ls-remote', 'origin').split()[0], self.git('rev-parse', 'HEAD'))
            pushes = [c for c in self.commands if c[0] == 'push']
            self.assertEqual(pushes, [('push', 'origin', 'HEAD:refs/heads/zh-CN-4.x-dev')])

    def test_conflict_aborts_without_branch_movement(self):
        self.advance(conflict=True)
        before = self.git('rev-parse', 'HEAD')
        with self.assertRaises(RuntimeError):
            module.sync(CONFIG, push=True)
        self.assertEqual(before, self.git('rev-parse', 'HEAD'))
        self.assertEqual(self.git('status', '--porcelain'), '')
        self.assertFalse(any(c[0] == 'push' for c in self.commands))

    def test_dirty_tree_rejected(self):
        Path('source.txt').write_text('dirty')
        with self.assertRaises(RuntimeError):
            module.sync(CONFIG)

    def test_wrong_checkout_rejected(self):
        self.git('checkout', 'official')
        with self.assertRaises(RuntimeError):
            module.sync(CONFIG)

    def test_only_development_mapping_allowed(self):
        for key, value in [('sync_branch', 'zh-CN-4.x'), ('sync_branch', 'main'),
                           ('upstream_branch', 'main-4.x'), ('upstream_branch', 'main-3.x'), ('upstream_repository', 'other/repo')]:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                module.sync(dict(CONFIG, **{key: value}), push=True)

class WorkflowTests(unittest.TestCase):
    def test_entry_is_source_only(self):
        text = (ROOT / '.github/workflows/zh-source-sync.yml').read_text()
        self.assertIn("cron: '23 3 * * *'", text)
        self.assertIn('default: true', text)
        self.assertEqual(text.count("if: github.repository == 'reliable-ly0411/PlotJuggler-zh-CN'"), 2)
        self.assertEqual(text.count("github.event_name == 'schedule' || !inputs.dry_run"), 2)
        for forbidden in ['gh release', 'publish-accepted-', 'release-candidate', 'workflow_call:',
                          'policy.py prepare', 'zh-release.yml', 'force', 'pull_request_target:']:
            self.assertNotIn(forbidden, text)
        self.assertIn('group: zh-upstream-sync', text)
        self.assertIn('cancel-in-progress: false', text)
        self.assertIn('--upstream-ref main-3.x --validate', text)
        config = json.loads((ROOT / '.github/sync/pj4-sync.json').read_text())
        self.assertEqual(config, CONFIG)

if __name__ == '__main__':
    unittest.main()
