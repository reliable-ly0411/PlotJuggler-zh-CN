#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Offline positive/negative tests; no publication or network writes."""
import copy
import hashlib
import json
import re
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packaging/localization'))
import recover_draft_442876072 as recovery
from release_assets import verify_release


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.head = 'a' * 40
        self.env = {'GITHUB_REPOSITORY': recovery.REPO, 'GITHUB_EVENT_NAME': 'push',
                    'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_REF': 'refs/heads/' + recovery.PREFIX + self.head,
                    'GITHUB_SHA': self.head}
        self.event = {'created': True, 'deleted': False, 'forced': False}
        self.changed = {name: 'A' for name in recovery.ALLOWED}
        self.draft = {'id': recovery.DRAFT, 'tag_name': recovery.TAG, 'draft': True,
                      'prerelease': False, 'published_at': None, 'assets': [],
                      'upload_url': f'https://uploads.github.com/repos/{recovery.REPO}/releases/{recovery.DRAFT}/assets{{?name,label}}'}
        self.run = {'id': recovery.CANDIDATE, 'head_sha': recovery.SOURCE, 'run_attempt': 1,
                    'status': 'completed', 'conclusion': 'success', 'event': 'workflow_dispatch',
                    'path': '.github/workflows/zh-4x-packages.yml', 'repository': {'full_name': recovery.REPO}}
        self.before = [dict(id=i, tag_name='v-old-' + str(i), assets=[dict(id=i * 100 + j,
                       name=f'old-{i}-{j}', size=3, digest='sha256:' + '1' * 64, state='uploaded', updated_at='old')
                       for j in range(10 if i == 1 else 5)]) for i in range(1, 9)] + [self.draft]

    def control(self, env=None, event=None, head=None, workflow=None, parents=None, changed=None):
        recovery.check_control(env or self.env, event or self.event, head or self.head,
                               workflow or self.head, parents if parents is not None else [recovery.SOURCE],
                               changed if changed is not None else self.changed)

    def test_exact_approved_control(self):
        self.control()

    def test_control_identity_and_trigger_rejections(self):
        for key, value in [('GITHUB_REPOSITORY', 'other/repo'), ('GITHUB_EVENT_NAME', 'workflow_dispatch'),
                           ('GITHUB_RUN_ATTEMPT', '2'), ('GITHUB_REF', 'refs/heads/arbitrary'),
                           ('GITHUB_SHA', 'b' * 40)]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.control(env=dict(self.env, **{key: value}))
        for key in ('created', 'deleted', 'forced'):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.control(event=dict(self.event, **{key: not self.event[key]}))
        for kwargs in [dict(workflow='b' * 40), dict(parents=[]), dict(parents=['b' * 40]),
                       dict(parents=[recovery.SOURCE, 'b' * 40]), dict(changed={}),
                       dict(changed=dict(self.changed, **{'CMakeLists.txt': 'M'})),
                       dict(changed={name: 'M' for name in self.changed})]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.control(**kwargs)

    def test_source_tree_tag_and_stable_bindings(self):
        refs = {'refs/heads/zh-CN-4.x': recovery.STABLE, 'refs/tags/' + recovery.TAG: recovery.SOURCE}
        recovery.check_refs(refs, recovery.TREE, recovery.TREE, True)
        for bad in [dict(refs, **{'refs/tags/' + recovery.TAG: 'b' * 40}),
                    dict(refs, **{'refs/heads/zh-CN-4.x': 'b' * 40}), {}]:
            with self.assertRaises(ValueError):
                recovery.check_refs(bad, recovery.TREE, recovery.TREE, True)
        for a, b, ancestor in [('b' * 40, recovery.TREE, True), (recovery.TREE, 'b' * 40, True),
                               (recovery.TREE, recovery.TREE, False)]:
            with self.assertRaises(ValueError):
                recovery.check_refs(refs, a, b, ancestor)

    def test_exact_candidate_and_failed_publish_runs(self):
        recovery.check_run(self.run, recovery.CANDIDATE, self.run['path'], 'success')
        failed = dict(self.run, id=recovery.FAILED_PUBLISH, conclusion='failure',
                      path='.github/workflows/zh-4x-publish.yml')
        recovery.check_run(failed, recovery.FAILED_PUBLISH, failed['path'], 'failure')

    def test_run_source_attempt_and_outcome_changed(self):
        for key, value in [('id', 1), ('head_sha', 'b' * 40), ('run_attempt', 2),
                           ('status', 'in_progress'), ('conclusion', 'failure'), ('event', 'pull_request'),
                           ('path', 'other.yml'), ('repository', {'full_name': 'other/repo'})]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                recovery.check_run(dict(self.run, **{key: value}), recovery.CANDIDATE, self.run['path'], 'success')

    def test_only_exact_empty_draft_admitted(self):
        recovery.check_draft(self.draft)
        for key, value in [('id', 1), ('tag_name', 'v-other'), ('draft', False), ('prerelease', True),
                           ('published_at', 'now'), ('assets', [{'id': 1}]), ('upload_url', 'https://example.com/')]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                recovery.check_draft(dict(self.draft, **{key: value}))

    def test_frozen_baseline_detects_changes_before_recovery(self):
        baseline = {'schema': 1, 'tags': {'refs/tags/old': 'a' * 40},
                    'previous_releases': [dict(id=r['id'], tag=r['tag_name'], draft=False, prerelease=True,
                        assets=[{key: a[key] for key in ('id', 'name', 'size', 'digest')} for a in r['assets']])
                        for r in self.before[:-1]]}
        rows = copy.deepcopy(self.before)
        for row in rows[:-1]:
            row.update(draft=False, prerelease=True)
        recovery.check_frozen(rows, baseline['tags'], baseline)
        for tags in [{}, dict(baseline['tags'], **{'refs/tags/new': 'b' * 40}), {'refs/tags/old': 'b' * 40}]:
            with self.assertRaises(ValueError):
                recovery.check_frozen(rows, tags, baseline)
        for mutate in [lambda x: x[0]['assets'][0].update(digest='changed'),
                       lambda x: x[0].update(tag_name='wrong'), lambda x: x[0].update(id=999),
                       lambda x: x.append({'id': 999})]:
            changed = copy.deepcopy(rows)
            mutate(changed)
            with self.assertRaises(ValueError):
                recovery.check_frozen(changed, baseline['tags'], baseline)

    def test_checked_in_frozen_baseline_retains_8_releases_and_45_assets(self):
        baseline = json.loads((ROOT / 'packaging/localization/recover-draft-442876072-baseline.json').read_text(encoding='utf-8'))
        self.assertEqual(len(baseline['previous_releases']), 8)
        self.assertEqual(sum(len(r['assets']) for r in baseline['previous_releases']), 45)
        self.assertEqual(baseline['tags']['refs/tags/' + recovery.TAG], recovery.SOURCE)

    def test_only_current_draft_can_change(self):
        recovery.check_older(self.before, self.before)
        after = copy.deepcopy(self.before)
        after[-1].update(draft=False, assets=[{'id': 123}])
        recovery.check_older(self.before, after)
        for mutate in [lambda rows: rows.pop(), lambda rows: rows.append({'id': 999}),
                       lambda rows: rows[0].update(body='changed'),
                       lambda rows: rows[0]['assets'][0].update(digest='changed'),
                       lambda rows: rows[0]['assets'][0].update(id=42),
                       lambda rows: rows[0]['assets'][0].update(name='renamed'),
                       lambda rows: rows[0]['assets'].pop()]:
            rows = copy.deepcopy(self.before)
            mutate(rows)
            with self.assertRaises(ValueError):
                recovery.check_older(self.before, rows)
        with self.assertRaises(ValueError):
            recovery.check_older(self.before[:-1], self.before[:-1])

    def test_original_upload_body_required_and_failures_not_retried(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            def failed(command, stdout, stderr, timeout):
                stdout.write(b'{"id":123}')
                stderr.write(b'uncertain write outcome')
                return mock.Mock(returncode=1)
            with mock.patch.object(recovery.subprocess, 'run', side_effect=failed) as run:
                with self.assertRaisesRegex(ValueError, 'do not retry'):
                    recovery.API(directory).call('example', 'upload', '--method', 'POST')
                self.assertEqual(run.call_count, 1)
                self.assertEqual((directory / '001-upload.json').read_bytes(), b'{"id":123}')

    def test_upload_name_digest_and_id_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'product+zh.1.zip'
            path.write_bytes(b'accepted')
            response = dict(id=1, name=path.name, size=8, state='uploaded',
                            digest='sha256:' + hashlib.sha256(b'accepted').hexdigest())
            recovery.check_upload(response, path, [])
            for key, value in [('name', 'product.zh.1.zip'), ('digest', None), ('size', 9),
                               ('id', 0), ('id', True), ('state', 'starter')]:
                with self.subTest(key=key), self.assertRaises(ValueError):
                    recovery.check_upload(dict(response, **{key: value}), path, [])
            with self.assertRaises(ValueError):
                recovery.check_upload(response, path, [response])

    def test_existing_source_verifier_rejects_inventory_as_receipt_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            names = ['product+zh.1.exe', 'product+zh.1.zip', 'product+zh.1.AppImage', 'product+zh.1.deb']
            for name in names:
                (directory / name).write_bytes(name.encode())
            sums = ''.join(hashlib.sha256((directory / name).read_bytes()).hexdigest() + '  ' + name + '\n'
                           for name in sorted(names))
            (directory / 'SHA256SUMS.txt').write_text(sums, encoding='utf-8')
            receipts = [dict(id=i + 1, name=p.name, size=p.stat().st_size, state='uploaded',
                        digest='sha256:' + hashlib.sha256(p.read_bytes()).hexdigest())
                        for i, p in enumerate(sorted(directory.iterdir()))]
            release = dict(self.draft, body='reviewed notes', assets=copy.deepcopy(receipts))
            verify_release(directory, release, receipts, recovery.TAG, True, 'reviewed notes', directory)
            release['assets'][0]['id'] = 777
            with self.assertRaisesRegex(ValueError, 'original upload IDs'):
                verify_release(directory, release, receipts, recovery.TAG, True, 'reviewed notes', directory)

    def test_original_staging_block_with_synthetic_bytes_and_real_source_metadata(self):
        # Exercise the unchanged accepted staging code; these tiny bytes are
        # explicitly synthetic and never uploaded or treated as product evidence.
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            (work / 'dist').mkdir()
            (work / 'acceptance').mkdir()
            version = recovery.TAG[1:]
            names = [f'PlotJuggler-{version}-Windows-x64-zh-CN.exe',
                     f'PlotJuggler-{version}-Windows-x64-portable-zh-CN.zip',
                     f'PlotJuggler-{version}-x86_64-zh-CN.AppImage',
                     f'plotjuggler4_{version}-1_amd64-zh-CN.deb']
            assets = []
            for name in names:
                data = ('synthetic ' + name).encode()
                (work / 'dist' / name).write_bytes(data)
                assets.append(dict(name=name, size=len(data), sha256=hashlib.sha256(data).hexdigest()))
            cases = [('windows-2022', 'ifw'), ('windows-2022', 'portable'),
                     ('ubuntu-22.04', 'appimage'), ('ubuntu-22.04', 'deb'),
                     ('ubuntu-24.04', 'appimage'), ('ubuntu-24.04', 'deb')]
            reports = [dict(platform=p, format=f, path=f'{p}/{f}/report.json') for p, f in cases]
            from verify_package import ACCEPTANCE_LANGUAGES
            screenshots = [dict(path=f'{p}/{f}/gui-{language}.png')
                           for p, f in cases for language in ACCEPTANCE_LANGUAGES]
            manifest = dict(schema_version=1, automated_acceptance='passed', source_commit=recovery.SOURCE,
                            workflow_sha=recovery.SOURCE, source_tree=recovery.TREE,
                            run_id=str(recovery.CANDIDATE), run_attempt='1', version=version, tag=recovery.TAG,
                            acceptance_reports=reports, screenshots=screenshots, assets=assets)
            (work / 'acceptance/release-manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
            env = dict(SOURCE_SHA=recovery.SOURCE, CANDIDATE_RUN=str(recovery.CANDIDATE),
                       CANDIDATE_ATTEMPT='1', RELEASE_TAG=recovery.TAG, GITHUB_REPOSITORY=recovery.REPO)
            with mock.patch.dict(recovery.os.environ, env):
                notes = recovery.prepare(ROOT, work, dict(self.run, html_url='https://example.test/synthetic'))
            self.assertEqual({p.name for p in (work / 'release-assets').iterdir()}, set(names) | {'SHA256SUMS.txt'})
            self.assertIn(recovery.SOURCE, notes)
            self.assertNotIn('@SOURCE_SHA@', notes)
            for name in names:
                self.assertEqual((work / 'release-assets' / name).read_bytes(), (work / 'dist' / name).read_bytes())

    def test_latest_absence_and_exact_identity(self):
        for code, data, expected in [(1, {'message': 'Not Found', 'status': '404'}, None),
                                     (1, {'message': 'Not Found', 'status': 404}, None),
                                     (0, {'id': recovery.DRAFT}, recovery.DRAFT)]:
            with tempfile.TemporaryDirectory() as temp:
                def fake(command, stdout, stderr, timeout):
                    stdout.write(json.dumps(data).encode())
                    return mock.Mock(returncode=code)
                with mock.patch.object(recovery.subprocess, 'run', side_effect=fake):
                    self.assertEqual(recovery.API(Path(temp)).latest('latest')['id'], expected)

    def test_latest_auth_network_and_ambiguous_404_fail_closed(self):
        cases = [(1, b'{"message":"Forbidden","status":403}'),
                 (1, b'{"message":"Not Found"}'), (1, b'{"status":404}'),
                 (1, b'HTTP 404'), (1, b''), (0, b'{"id":null}'), (0, b'not JSON')]
        for code, data in cases:
            with self.subTest(code=code, data=data), tempfile.TemporaryDirectory() as temp:
                def fake(command, stdout, stderr, timeout):
                    stdout.write(data)
                    return mock.Mock(returncode=code)
                with mock.patch.object(recovery.subprocess, 'run', side_effect=fake), self.assertRaises(ValueError):
                    recovery.API(Path(temp)).latest('latest')
        with tempfile.TemporaryDirectory() as temp:
            with mock.patch.object(recovery.subprocess, 'run', side_effect=TimeoutError('network')):
                with self.assertRaises(TimeoutError):
                    recovery.API(Path(temp)).latest('latest')

    def test_complete_offline_main_and_no_write_retry(self):
        # Full main orchestration with real API receipt files and real source
        # verifier. Only Git/gh and preparation inputs are explicit synthetic
        # fakes; the real original prepare block is exercised separately above.
        from urllib.parse import parse_qs, urlsplit
        import release_assets
        baseline = json.loads((ROOT / 'packaging/localization/recover-draft-442876072-baseline.json').read_text(encoding='utf-8'))
        for scenario in ('success', 'upload-error', 'latest-changed', 'tags-changed'):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as temp:
                directory = Path(temp)
                source = directory / 'source'
                source.mkdir()
                work = directory / 'work'
                event = directory / 'event.json'
                event.write_text(json.dumps(self.event), encoding='utf-8')
                env = dict(self.env, GITHUB_EVENT_PATH=str(event), GITHUB_WORKFLOW_SHA=self.head, GITHUB_RUN_ID='999')
                tags = '\n'.join(sha + '\t' + ref for ref, sha in sorted(baseline['tags'].items()))
                old = [dict(id=r['id'], tag_name=r['tag'], draft=r['draft'], prerelease=r['prerelease'],
                            assets=[dict(a, state='uploaded') for a in r['assets']])
                       for r in baseline['previous_releases']]
                draft = dict(self.draft, body='reviewed synthetic notes', assets=[])
                uploads, events = [], []
                state = {'published': False, 'latest_reads': 0, 'tag_reads': 0}
                real_verify = release_assets.verify_release

                def verifier(*args, **kwargs):
                    result = real_verify(*args, **kwargs)
                    downloads = args[6] if len(args) > 6 else kwargs.get('downloads')
                    if downloads is not None:
                        events.append('verified-' + ('draft' if args[4] else 'public') + '-downloads')
                    return result

                def fake_git(root, *args):
                    if args == ('rev-parse', 'HEAD'):
                        return self.head if Path(root) == ROOT else recovery.SOURCE
                    if args[:2] == ('diff', '--name-status'):
                        return '\n'.join('A\t' + name for name in sorted(recovery.ALLOWED))
                    if args[:2] == ('rev-list', '--parents'):
                        return self.head + ' ' + recovery.SOURCE
                    if args == ('status', '--porcelain'):
                        return ''
                    if args[0] == 'rev-parse' and args[1].endswith('^{tree}'):
                        return recovery.TREE
                    if args[:3] == ('ls-remote', '--tags', '--refs'):
                        state['tag_reads'] += 1
                        if scenario == 'tags-changed' and state['tag_reads'] > 1:
                            return tags + '\n' + 'b' * 40 + '\trefs/tags/unapproved'
                        return tags
                    if args[:2] == ('ls-remote', 'origin'):
                        return recovery.STABLE + '\trefs/heads/zh-CN-4.x\n' + recovery.SOURCE + '\trefs/tags/' + recovery.TAG
                    raise AssertionError(('unexpected git', args))

                def fake_prepare(source_path, stage, run):
                    self.assertEqual(source_path, source)
                    public = stage / 'release-assets'
                    public.mkdir()
                    names = ['synthetic+zh.1.exe', 'synthetic+zh.1.zip', 'synthetic+zh.1.AppImage', 'synthetic+zh.1.deb']
                    assets = []
                    for name in names:
                        data = ('SYNTHETIC ' + name).encode()
                        (public / name).write_bytes(data)
                        assets.append(dict(name=name, size=len(data), sha256=hashlib.sha256(data).hexdigest()))
                    sums = ''.join(a['sha256'] + '  ' + a['name'] + '\n' for a in sorted(assets, key=lambda a: a['name']))
                    (public / 'SHA256SUMS.txt').write_text(sums, encoding='utf-8')
                    (stage / 'public-asset-manifest.json').write_text(json.dumps({'assets': assets}), encoding='utf-8')
                    return draft['body']

                def fake_run(command, **kwargs):
                    if command[0] == 'git':
                        self.assertIn('--is-ancestor', command)
                        return mock.Mock(returncode=0)
                    if command[:3] == ['gh', 'run', 'download']:
                        destination = Path(command[command.index('-D') + 1])
                        destination.mkdir(parents=True)
                        return mock.Mock(returncode=0)
                    if command[0] == 'sha256sum':
                        return mock.Mock(returncode=0)
                    self.assertEqual(command[:2], ['gh', 'api'])
                    path = command[2]
                    method = command[command.index('--method') + 1] if '--method' in command else 'GET'
                    suffix = path.removeprefix('repos/' + recovery.REPO + '/')
                    code = 0
                    if method == 'POST':
                        self.assertTrue(path.startswith(f'https://uploads.github.com/repos/{recovery.REPO}/releases/{recovery.DRAFT}/assets?'))
                        name = parse_qs(urlsplit(path).query)['name'][0]
                        self.assertEqual(name, Path(command[command.index('--input') + 1]).name)
                        self.assertIn('%2B', path) if '+' in name else None
                        uploads.append(name)
                        events.append('POST')
                        if scenario == 'upload-error':
                            payload, code = {'message': 'simulated uncertain upload'}, 1
                        else:
                            data = (work / 'release-assets' / name).read_bytes()
                            payload = dict(id=1000 + len(uploads), name=name, size=len(data), state='uploaded',
                                           digest='sha256:' + hashlib.sha256(data).hexdigest())
                            draft['assets'].append(payload)
                    elif method == 'PATCH':
                        self.assertEqual(suffix, 'releases/' + str(recovery.DRAFT))
                        self.assertEqual(len(uploads), 5)
                        self.assertIn('verified-draft-downloads', events)
                        events.append('PATCH')
                        state['published'] = True
                        draft.update(draft=False, published_at='synthetic-now')
                        payload = draft
                    elif suffix == 'releases/latest':
                        state['latest_reads'] += 1
                        if state['published']:
                            payload = {'id': recovery.DRAFT}
                            events.append('verified-latest-request')
                        elif scenario == 'latest-changed' and state['latest_reads'] > 1:
                            payload = {'id': old[0]['id']}
                        else:
                            payload, code = {'message': 'Not Found', 'status': '404'}, 1
                    elif suffix == 'actions/runs/' + str(recovery.CANDIDATE):
                        payload = dict(self.run, html_url='https://example.test/synthetic')
                    elif suffix == 'actions/runs/' + str(recovery.FAILED_PUBLISH):
                        payload = dict(self.run, id=recovery.FAILED_PUBLISH, conclusion='failure',
                                       path='.github/workflows/zh-4x-publish.yml')
                    elif suffix == 'releases?per_page=100':
                        payload = [old + [draft]]
                    elif suffix.endswith('/assets?per_page=100'):
                        release_id = int(suffix.split('/')[1])
                        payload = [next(r['assets'] for r in old + [draft] if r['id'] == release_id)]
                    elif suffix == 'releases/' + str(recovery.DRAFT):
                        payload = draft
                    elif suffix.startswith('releases/assets/'):
                        asset = next(a for a in draft['assets'] if a['id'] == int(suffix.split('/')[-1]))
                        kwargs['stdout'].write((work / 'release-assets' / asset['name']).read_bytes())
                        return mock.Mock(returncode=0)
                    else:
                        raise AssertionError(('unexpected API', command))
                    kwargs['stdout'].write(json.dumps(payload).encode())
                    return mock.Mock(returncode=code)

                with mock.patch.dict(recovery.os.environ, env), \
                     mock.patch.object(recovery.sys, 'argv', ['recovery', str(ROOT), str(source), str(work)]), \
                     mock.patch.object(recovery, 'git', side_effect=fake_git), \
                     mock.patch.object(recovery, 'prepare', side_effect=fake_prepare), \
                     mock.patch.object(recovery.subprocess, 'run', side_effect=fake_run), \
                     mock.patch.object(release_assets, 'verify_release', side_effect=verifier):
                    if scenario == 'success':
                        recovery.main()
                    else:
                        with self.assertRaises(ValueError):
                            recovery.main()
                if scenario == 'success':
                    self.assertEqual(len(uploads), 5)
                    self.assertEqual(events.count('PATCH'), 1)
                    self.assertIn('verified-public-downloads', events)
                    self.assertIn('verified-latest-request', events)
                    self.assertTrue((work / 'evidence/SUCCESS.json').is_file())
                    receipts = [json.loads(p.read_text(encoding='utf-8')) for p in (work / 'evidence').glob('*.json')
                                if re.match(r'^\d+-upload-', p.name)]
                    self.assertEqual({p['id'] for p in receipts}, {a['id'] for a in draft['assets']})
                    self.assertEqual(len(receipts), 5)
                else:
                    self.assertNotIn('PATCH', events)
                    self.assertFalse((work / 'evidence/SUCCESS.json').exists())
                    self.assertEqual(len(uploads), 1 if scenario == 'upload-error' else 0)

    def test_workflow_is_additive_one_shot_and_uses_numeric_recovery(self):
        text = (ROOT / '.github/workflows/zh-4x-recover-draft-442876072.yml').read_text(encoding='utf-8')
        self.assertIn(recovery.PREFIX + '*', text)
        self.assertIn('github.event.created && github.run_attempt == 1', text)
        self.assertIn('ref: ' + recovery.SOURCE, text)
        self.assertIn('if: always()', text)
        self.assertLess(text.index('python3 control/tests/test_recover_draft_442876072.py -v'),
                        text.index('python3 control/packaging/localization/recover_draft_442876072.py'))
        script = (ROOT / 'packaging/localization/recover_draft_442876072.py').read_text(encoding='utf-8')
        self.assertNotIn('releases/tags/', script)
        self.assertNotIn("'DELETE'", script)
        self.assertNotIn('--clobber', script)
        self.assertIn("quote(path.name, safe='')", script)
        self.assertIn("from release_assets import verify_release", script)


if __name__ == '__main__':
    unittest.main()
