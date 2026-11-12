#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Offline checks for draft-safe numeric ID transport and retained responses."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packaging/localization'))
import release_by_id as module


class NumericReleaseTest(unittest.TestCase):
    """Transport must fail closed without tag lookup fallback or write retries."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo, self.tag = 'owner/repo', 'v4.0.0-zh.1.rc.1'
        self.release = {'id': 42, 'tag_name': self.tag, 'draft': True, 'prerelease': True,
                        'upload_url': 'https://uploads.github.com/repos/owner/repo/releases/42/assets{?name,label}',
                        'assets': [{'id': 73, 'name': 'package+zh.1.zip'}]}
        self.created = self.root / 'created.json'
        self.created.write_text(json.dumps(self.release), encoding='utf-8')

    def run_action(self, action, **kwargs):
        module.execute(action, self.repo, self.tag, self.created, self.root / 'out', **kwargs)

    def test_numeric_snapshot(self):
        with patch.object(module, 'api', return_value=self.release) as api:
            self.run_action('draft')
        self.assertEqual(api.call_args.args[0], 'repos/owner/repo/releases/42')

    def test_wrong_identity_fails(self):
        for changes in ({'id': True}, {'id': 0}, {'id': 43}, {'tag_name': 'wrong'},
                        {'draft': False}, {'prerelease': False}, {'upload_url': 'https://evil.test'}):
            with self.subTest(changes=changes), patch.object(module, 'api', return_value=dict(self.release, **changes)):
                with self.assertRaises(ValueError):
                    self.run_action('draft')

    def test_download_numeric_asset_and_preserve_plus(self):
        with patch.object(module, 'api') as api:
            self.run_action('download', inventory=self.created)
        self.assertEqual(api.call_args.args[0], 'repos/owner/repo/releases/assets/73')
        self.assertEqual(api.call_args.args[1].name, 'package+zh.1.zip')
        self.assertTrue(api.call_args.kwargs['binary'])

    def test_download_rejects_unsafe_duplicate_ids_names_before_io(self):
        for assets in ([{'id': True, 'name': 'safe.zip'}], [{'id': 73, 'name': '../bad.zip'}],
                       self.release['assets'] * 2, [{'id': 73, 'name': 'safe.zip'}, {'id': 74, 'name': 'safe.zip'}]):
            with self.subTest(assets=assets), patch.object(module, 'api') as api:
                self.created.write_text(json.dumps(dict(self.release, assets=assets)), encoding='utf-8')
                with self.assertRaises(ValueError):
                    self.run_action('download', inventory=self.created)
                api.assert_not_called()

    def test_publish_uses_numeric_patch_and_policy(self):
        with patch.object(module, 'api', return_value=dict(self.release, draft=False)) as api:
            self.run_action('publish')
        self.assertEqual(api.call_args.args[0], 'repos/owner/repo/releases/42')
        self.assertEqual(api.call_args.args[2], {'draft': False, 'prerelease': True, 'make_latest': 'false'})

    def test_raw_response_retained_before_parse_and_no_overwrite(self):
        target = self.root / 'response.json'
        def fake(command, **kwargs):
            kwargs['stdout'].write(b'not-json-original-response')
        with patch.object(module.subprocess, 'run', side_effect=fake) as run:
            with self.assertRaises(json.JSONDecodeError):
                module.api('repos/owner/repo/releases', target, {'draft': True})
            self.assertEqual(target.read_bytes(), b'not-json-original-response')
            with self.assertRaises(FileExistsError):
                module.api('repos/owner/repo/releases', target, {'draft': True})
            self.assertEqual(run.call_count, 1)
            self.assertIn('POST', run.call_args.args[0])

    def test_failed_write_not_retried(self):
        with patch.object(module.subprocess, 'run', side_effect=subprocess.CalledProcessError(1, 'gh')) as run:
            with self.assertRaises(subprocess.CalledProcessError):
                module.api('repos/owner/repo/releases/42', self.root / 'response', {'draft': False})
            self.assertEqual(run.call_count, 1)
            self.assertIn('PATCH', run.call_args.args[0])

    def test_create_retains_identity_without_tag_lookup(self):
        self.created.unlink()
        notes = self.root / 'notes'
        notes.write_text('Reviewed notes', encoding='utf-8')
        with patch.object(module, 'api', return_value=dict(self.release, assets=[])) as api:
            self.run_action('create', notes=notes, source='a'*40, title='title')
        self.assertEqual(api.call_args.args[0], 'repos/owner/repo/releases')
        self.assertEqual(api.call_args.args[1], self.created)
        self.assertTrue(api.call_args.args[2]['draft'])
        self.assertEqual(api.call_args.args[2]['make_latest'], 'false')

    def test_transport_full_sequence_retains_all_responses(self):
        self.created.unlink()
        notes = self.root / 'notes'
        notes.write_text('Reviewed notes', encoding='utf-8')
        calls = []
        def fake(command, **kwargs):
            calls.append(command)
            endpoint = command[2]
            if '/assets/' in endpoint:
                kwargs['stdout'].write(b'original-package')
                return
            payload = json.loads(kwargs['input']) if kwargs.get('input') else None
            release = dict(self.release)
            if payload and payload.get('draft') is True:
                release['assets'] = []
            elif (payload and payload.get('draft') is False) or len(calls) > 4:
                release['draft'] = False
            kwargs['stdout'].write(json.dumps(release).encode())
        with patch.object(module.subprocess, 'run', side_effect=fake):
            module.execute('create', self.repo, self.tag, self.created, None,
                           notes=notes, source='a'*40, title='title')
            draft = self.root / 'draft.json'
            module.execute('draft', self.repo, self.tag, self.created, draft)
            module.execute('download', self.repo, self.tag, self.created, self.root / 'draft-bytes', inventory=draft)
            module.execute('publish', self.repo, self.tag, self.created, self.root / 'patch.json')
            public = self.root / 'public.json'
            module.execute('published', self.repo, self.tag, self.created, public)
            module.execute('download', self.repo, self.tag, self.created, self.root / 'public-bytes', inventory=public)
        self.assertEqual(len(calls), 6)
        self.assertTrue(json.loads(self.created.read_text(encoding='utf-8'))['draft'])
        self.assertFalse(json.loads(public.read_text(encoding='utf-8'))['draft'])
        self.assertEqual((self.root / 'public-bytes/package+zh.1.zip').read_bytes(), b'original-package')
        self.assertFalse(any('/tags/' in command[2] for command in calls))

    def test_workflow_keeps_gates_and_never_uses_draft_tag_lookups(self):
        workflow = (ROOT / '.github/workflows/zh-4x-publish.yml').read_text(encoding='utf-8')
        self.assertNotIn('releases/tags/', workflow)
        self.assertNotIn('gh release download', workflow)
        self.assertNotIn('gh release edit', workflow)
        for gate in ['--upload-responses upload-responses', '--downloads draft-check', '--downloads public-check',
                     'latest-before.json', 'latest-after.json', 'tags-before.txt', 'tags-after.txt',
                     'draft-rechecked.json', 'published-response.json', '--state draft', '--state published']:
            self.assertIn(gate, workflow)
        self.assertLess(workflow.index('--downloads draft-check'), workflow.index('release_by_id.py publish '))


if __name__ == '__main__':
    unittest.main()
