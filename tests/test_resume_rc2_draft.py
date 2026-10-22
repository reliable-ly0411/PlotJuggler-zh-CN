#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
import copy
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

location = Path(__file__).with_name('resume_rc2_draft.py')
if not location.exists():
    location = Path(__file__).parents[1] / 'packaging/localization/resume_rc2_draft.py'
spec = importlib.util.spec_from_file_location('recovery', location)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class RecoveryGuardTests(unittest.TestCase):
    def setUp(self):
        self.notes = '固定原包说明 %1 中文\n'
        self.release = dict(id=m.DRAFT_ID, tag_name=m.TAG, draft=True, prerelease=True,
            published_at=None, assets=[], name=m.TITLE, body=self.notes,
            author={'login': 'github-actions[bot]'},
            upload_url=f'https://uploads.github.com/repos/{m.REPOSITORY}/releases/{m.DRAFT_ID}/assets{{?name,label}}')
        self.tag = {'ref': 'refs/tags/' + m.TAG, 'object': {'type': 'commit', 'sha': m.SOURCE}}
        self.run = dict(id=m.FAILED_RUN, run_attempt=1, status='completed', conclusion='failure',
            head_sha=m.SOURCE, path='.github/workflows/zh-4x-publish.yml', repository={'full_name': m.REPOSITORY})

    def test_exact_empty_draft(self):
        m.validate_empty_draft(self.release, [self.release], self.notes)
        m.validate_tag(self.tag)
        m.validate_failed_run(self.run)

    def test_every_identity_and_empty_gate_fails_closed(self):
        changes = {'id': 420226108, 'tag_name': 'v4.0.0-zh.1.rc.1', 'draft': False,
            'prerelease': False, 'published_at': '2026-10-22', 'assets': [{'id': 1}],
            'name': 'different', 'body': self.notes + 'changed', 'author': {'login': 'other'},
            'upload_url': 'https://uploads.github.com/repos/other/repo/releases/1/assets{?name,label}'}
        for key, value in changes.items():
            with self.subTest(key=key):
                altered = dict(self.release, **{key: value})
                with self.assertRaises(ValueError): m.validate_empty_draft(altered, [altered], self.notes)
        for key in self.release:
            with self.subTest(missing=key):
                altered = dict(self.release); del altered[key]
                with self.assertRaises(ValueError): m.validate_empty_draft(altered, [altered], self.notes)

    def test_unique_and_consistent_list(self):
        for listed in [[], [self.release, self.release], [dict(self.release, assets=[{'id': 1}])]]:
            with self.assertRaises(ValueError): m.validate_empty_draft(self.release, listed, self.notes)

    def test_tag_never_moves_or_changes_kind(self):
        for tag in [{**self.tag, 'ref': 'refs/tags/other'},
                    {**self.tag, 'object': {'type': 'tag', 'sha': m.SOURCE}},
                    {**self.tag, 'object': {'type': 'commit', 'sha': '0' * 40}}]:
            with self.assertRaises(ValueError): m.validate_tag(tag)

    def test_failed_run_identity(self):
        for key, value in [('id', 1), ('run_attempt', 2), ('status', 'in_progress'),
                           ('conclusion', 'success'), ('head_sha', '0' * 40),
                           ('path', '.github/workflows/other.yml'), ('repository', {'full_name': 'other/repo'})]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                m.validate_failed_run(dict(self.run, **{key: value}))

    def test_download_only_reads_exact_asset_ids(self):
        release = dict(self.release, assets=[{'name': name, 'id': index + 1}
            for index, name in enumerate(['a.exe', 'a.AppImage', 'a.deb', 'SHA256SUMS.txt'])])
        with tempfile.TemporaryDirectory() as tmp, patch.object(m.subprocess, 'run') as run:
            path = Path(tmp) / 'fresh'
            m.download_draft(release, path)
            self.assertEqual(run.call_count, 4)
            for call, asset in zip(run.call_args_list, release['assets']):
                self.assertEqual(call.args[0], ['gh', 'api', '-H', 'Accept: application/octet-stream',
                    f'repos/{m.REPOSITORY}/releases/assets/{asset["id"]}'])
            with self.assertRaises(FileExistsError): m.download_draft(release, path)

    def test_download_rejects_wrong_or_unsafe_inventory(self):
        good = [{'name': name, 'id': i + 1} for i, name in enumerate(['a.exe', 'a.AppImage', 'a.deb', 'SHA256SUMS.txt'])]
        for assets in [[], good[:3], [good[0]] * 4,
                       [{**a, 'name': '../bad'} if i == 0 else a for i, a in enumerate(good)],
                       [{**a, 'id': True} if i == 0 else a for i, a in enumerate(good)]]:
            with tempfile.TemporaryDirectory() as tmp, patch.object(m.subprocess, 'run') as run:
                with self.assertRaises(ValueError): m.download_draft(dict(self.release, assets=assets), Path(tmp)/'new')
                run.assert_not_called()

    def test_exact_creation_trigger_and_no_general_retry(self):
        workflow = Path(__file__).with_name('zh-4x-resume-rc2.yml')
        if not workflow.exists():
            workflow = Path(__file__).parents[1] / '.github/workflows/zh-4x-resume-rc2.yml'
        text = workflow.read_text(encoding='utf-8')
        branch = 'zh-CN-4.x-ci/resume-rc2-draft-420226107'
        self.assertIn("branches: ['" + branch + "']", text)
        condition = next(line.strip() for line in text.splitlines() if line.strip().startswith('if: '))
        self.assertEqual(condition, "if: github.repository == 'reliable-ly0411/PlotJuggler-zh-CN' && github.event_name == 'push' && github.event.created && github.ref == 'refs/heads/" + branch + "'")
        for forbidden in ['workflow_dispatch:', '--clobber', 'gh release create', '--method DELETE', '-X DELETE', 'git push', 'gh release edit']:
            self.assertNotIn(forbidden, text)
        self.assertEqual(text.count('--method PATCH'), 1)
        self.assertIn('gh api --method PATCH "repos/$GITHUB_REPOSITORY/releases/420226107"', text)
        self.assertIn('-F draft=false -F prerelease=true -f make_latest=false', text)
        self.assertIn('ref: ' + m.SOURCE, text)
        self.assertIn('path: accepted', text)
        self.assertIn('working-directory: accepted', text)
        self.assertIn('assert old_tags == new_tags', text)
        self.assertIn("if old['id'] != 420226107: assert current[old['id']] == inventory(old)", text)

    def test_candidate_staging_is_the_original_frozen_recipe(self):
        workflow = Path(__file__).with_name('zh-4x-resume-rc2.yml')
        original = Path(os.environ.get('PJ_RECOVERY_BASE_REPO', str(Path(__file__).parents[1]))) / '.github/workflows/zh-4x-publish.yml'
        if not workflow.exists():
            original = Path(__file__).parents[1] / '.github/workflows/zh-4x-publish.yml'
            workflow = original.with_name('zh-4x-resume-rc2.yml')
        def block(path):
            text = path.read_text(encoding='utf-8')
            start = text.index('      - name: Download and verify the original accepted packages')
            end = text.index('\n      - name:', start + 1)
            return text[start:end]
        self.assertEqual(block(original), block(workflow))


if __name__ == '__main__': unittest.main()
