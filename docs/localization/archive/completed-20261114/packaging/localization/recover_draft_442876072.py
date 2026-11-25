#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""One-shot, fail-closed continuation of the empty 4.1.0 draft, not a rebuild."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

REPO = 'reliable-ly0411/PlotJuggler-zh-CN'
SOURCE = '0113492d7a7f96e486de1f9adcde6e43893ab630'
TREE = '2f5b79bda0002d960843c3f19b79208a4b14efef'
STABLE = '51b95566a9bc49c41b4407f2d87c9394d4a2a6ce'
TAG = 'v4.1.0+zh.1'
CANDIDATE = 43194300434
FAILED_PUBLISH = 43212512724
DRAFT = 442876072
PREFIX = 'recover-publish-v4-1-0-draft-442876072-'
ALLOWED = {'.github/workflows/zh-4x-recover-draft-442876072.yml',
           'packaging/localization/recover_draft_442876072.py',
           'tests/test_recover_draft_442876072.py',
           'packaging/localization/recover-draft-442876072-baseline.json'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def check_control(env, event, head, workflow, parents, changed):
    require(env['GITHUB_REPOSITORY'] == REPO, 'Wrong repository')
    require(re.fullmatch(r'[0-9a-f]{40}', head) is not None, 'Invalid control SHA')
    require(env['GITHUB_EVENT_NAME'] == 'push' and event.get('created') is True
            and not event.get('deleted') and not event.get('forced'), 'Not a first-created recovery ref')
    require(env['GITHUB_RUN_ATTEMPT'] == '1', 'Recovery reruns are forbidden')
    require(env['GITHUB_REF'] == 'refs/heads/' + PREFIX + head, 'Recovery ref must pin approved control SHA')
    require(env['GITHUB_SHA'] == head == workflow, 'Control/workflow SHA mismatch')
    require(parents == [SOURCE], 'Recovery control must have exactly the accepted source as parent')
    require(changed == {name: 'A' for name in ALLOWED}, 'Recovery diff is not the exact additions-only allowlist')


def check_run(run, run_id, path, conclusion):
    require(run['id'] == run_id and run['head_sha'] == SOURCE and run['run_attempt'] == 1,
            'Run/source/attempt changed')
    require(run['status'] == 'completed' and run['conclusion'] == conclusion, 'Unexpected run outcome')
    require(run['path'] == path and run['repository']['full_name'] == REPO,
            'Wrong run workflow or repository')
    require(run['event'] in ['push', 'workflow_dispatch'], 'Unexpected run event')


def check_refs(refs, source_tree, stable_tree, ancestor):
    require(refs == {'refs/heads/zh-CN-4.x': STABLE, 'refs/tags/' + TAG: SOURCE}, 'Stable or immutable tag changed')
    require(source_tree == stable_tree == TREE and ancestor, 'Accepted source/tree/ancestry mismatch')


def check_draft(release, empty=True):
    require(release['id'] == DRAFT and release['tag_name'] == TAG, 'Wrong draft ID or tag')
    require(release['draft'] is True and release['prerelease'] is False
            and release.get('published_at') is None, 'Draft already public or wrong release kind')
    require(release['upload_url'].split('{', 1)[0] ==
            f'https://uploads.github.com/repos/{REPO}/releases/{DRAFT}/assets', 'Wrong upload destination')
    if empty:
        require(release['assets'] == [], 'Draft is not empty; stop for receipt-aware investigation')


def check_upload(response, path, previous):
    """Stop immediately on a changed name, absent digest, or reused response ID."""
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    require(response.get('name') == path.name and response.get('state') == 'uploaded', 'Upload renamed or incomplete')
    require(type(response.get('id')) is int and response['id'] > 0
            and response['id'] not in {item['id'] for item in previous}, 'Invalid or duplicate upload ID')
    require(response.get('size') == path.stat().st_size and response.get('digest') == 'sha256:' + digest.hexdigest(),
            'Upload size or digest mismatch')


def immutable_release(release):
    fields = ('id', 'tag_name', 'name', 'body', 'draft', 'prerelease', 'created_at', 'published_at')
    asset_fields = ('id', 'name', 'size', 'digest', 'state', 'created_at', 'updated_at')
    result = {key: release.get(key) for key in fields}
    result['assets'] = sorted(({key: asset.get(key) for key in asset_fields}
                               for asset in release['assets']), key=lambda item: item['id'])
    return result


def check_frozen(releases, tags, baseline):
    """Bind old assets to the retained pre-publication evidence, not a new guess."""
    require(baseline['schema'] == 1 and tags == baseline['tags'], 'Frozen tag inventory changed')
    expected = baseline['previous_releases']
    require(len(expected) == 8 and sum(len(item['assets']) for item in expected) == 45, 'Invalid frozen baseline')
    require(len(releases) == 9 and {item['id'] for item in releases} == {item['id'] for item in expected} | {DRAFT},
            'Frozen release IDs changed')
    current = {item['id']: item for item in releases}
    for old in expected:
        new = current[old['id']]
        require(new['tag_name'] == old['tag'] and new['draft'] is old['draft']
                and new['prerelease'] is old['prerelease'], 'Frozen release identity changed')
        fields = ('id', 'name', 'size', 'digest')
        assets = [{key: item.get(key) for key in fields} for item in new['assets']]
        require(sorted(assets, key=lambda item: item['id']) == sorted(old['assets'], key=lambda item: item['id']),
                'Frozen old asset bytes or identity changed')


def check_older(before, after):
    require(len({r['id'] for r in before}) == len(before) == 9, 'Expected eight older releases and this draft')
    old = [r for r in before if r['id'] != DRAFT]
    require(len(old) == 8 and sum(len(r['assets']) for r in old) == 45, 'Older release/asset baseline changed')
    require(len({r['id'] for r in after}) == len(after) == len(before), 'Release inventory changed')
    current = {r['id']: r for r in after}
    require(set(current) == {r['id'] for r in before}, 'Missing or additional releases')
    for release in old:
        require(immutable_release(release) == immutable_release(current[release['id']]),
                'An older release or asset changed')


class API:
    """Retain each original API response before parsing; never retry a write."""
    def __init__(self, evidence):
        self.evidence = evidence
        self.counter = 0

    def call(self, path, label, *args, download=None, allow_no_latest=False):
        self.counter += 1
        output = download or self.evidence / f'{self.counter:03d}-{label}.json'
        error = self.evidence / f'{self.counter:03d}-{label}.stderr.txt'
        with output.open('wb') as stdout, error.open('wb') as stderr:
            result = subprocess.run(['gh', 'api', path, *args], stdout=stdout, stderr=stderr, timeout=1200)
        if allow_no_latest:
            require(path == f'repos/{REPO}/releases/latest' and not args and download is None,
                    'No-Latest exception is only for the read-only Latest endpoint')
            data = json.loads(output.read_text(encoding='utf-8'))
            if result.returncode:
                # Same strict semantics as SOURCE's snapshot_latest.py. Retain
                # the genuine response, never turn auth/network errors into None.
                require(data.get('message') == 'Not Found' and str(data.get('status')) == '404',
                        'Latest read failed without a genuine no-Latest response')
                return {'id': None}
            require(type(data.get('id')) is int and data['id'] > 0, 'Invalid Latest identity')
            return {'id': data['id']}
        require(result.returncode == 0, f'API {label} failed; outcome may be uncertain; do not retry writes')
        return None if download else json.loads(output.read_text(encoding='utf-8'))

    def latest(self, label):
        return self.repository('releases/latest', label, allow_no_latest=True)

    def repository(self, suffix, label, *args, **kwargs):
        return self.call(f'repos/{REPO}/{suffix}', label, *args, **kwargs)

    def releases(self, label):
        pages = self.repository('releases?per_page=100', label, '--paginate', '--slurp')
        releases = [item for page in pages for item in page]
        for release in releases:
            pages = self.repository(f'releases/{release["id"]}/assets?per_page=100',
                                    label + '-assets-' + str(release['id']), '--paginate', '--slurp')
            release['assets'] = [item for page in pages for item in page]
        return releases


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def prepare(source, work, run):
    """Execute the original accepted workflow's local manifest/notes staging block."""
    workflow = (source / '.github/workflows/zh-4x-publish.yml').read_text(encoding='utf-8')
    start = workflow.index('          from pathlib import Path\n', workflow.index('Download and verify'))
    end = workflow.index('          PY\n', start)
    original = ''.join(line[10:] for line in workflow[start:end].splitlines(keepends=True))
    # The unchanged block imports helpers relative to the accepted source root.
    (work / 'packaging').symlink_to(source / 'packaging', target_is_directory=True)
    (work / 'docs').symlink_to(source / 'docs', target_is_directory=True)
    write_json(work / 'run.json', run)
    env = dict(os.environ, GIT_DIR=git(source, 'rev-parse', '--absolute-git-dir'), GIT_WORK_TREE=str(source))
    subprocess.run([sys.executable, '-I', '-c', original], cwd=work, env=env, check=True)
    subprocess.run([sys.executable, str(source / 'packaging/localization/hash_packages.py'),
                    'release-assets', '--output', 'SHA256SUMS.txt'], cwd=work, check=True)
    return (work / 'release-notes.md').read_text(encoding='utf-8')


def main():
    control, source, work = [Path(arg).resolve() for arg in sys.argv[1:]]
    work.mkdir()  # No stale local files or receipt reuse.
    evidence = work / 'evidence'
    evidence.mkdir()
    event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text(encoding='utf-8'))
    head = git(control, 'rev-parse', 'HEAD')
    changes = git(control, 'diff', '--name-status', SOURCE, head).splitlines()
    changed = {line.split('\t')[1]: line.split('\t')[0] for line in changes}
    check_control(os.environ, event, head, os.environ['GITHUB_WORKFLOW_SHA'],
                  git(control, 'rev-list', '--parents', '-n', '1', head).split()[1:], changed)
    require(git(source, 'rev-parse', 'HEAD') == SOURCE and not git(source, 'status', '--porcelain'),
            'Accepted source checkout is not exact and clean')
    write_json(evidence / 'identities.json', {'product_source': SOURCE, 'product_tree': TREE,
               'control_sha': head, 'workflow_sha': os.environ['GITHUB_WORKFLOW_SHA'],
               'recovery_ref': os.environ['GITHUB_REF'], 'recovery_run': os.environ['GITHUB_RUN_ID'],
               'recovery_attempt': 1, 'candidate_run': CANDIDATE, 'candidate_attempt': 1,
               'failed_publish_run': FAILED_PUBLISH, 'draft_id': DRAFT, 'tag': TAG})
    api = API(evidence)
    baseline = json.loads((control / 'packaging/localization/recover-draft-442876072-baseline.json').read_text(encoding='utf-8'))
    write_json(evidence / 'frozen-baseline.json', baseline)

    def gates():
        rows = git(source, 'ls-remote', 'origin', 'refs/heads/zh-CN-4.x', 'refs/tags/' + TAG).splitlines()
        refs = {line.split()[1]: line.split()[0] for line in rows}
        check_refs(refs, git(source, 'rev-parse', SOURCE + '^{tree}'),
                   git(source, 'rev-parse', STABLE + '^{tree}'),
                   subprocess.run(['git', '-C', str(source), 'merge-base', '--is-ancestor', SOURCE, STABLE]).returncode == 0)
        candidate = api.repository(f'actions/runs/{CANDIDATE}', 'candidate')
        check_run(candidate, CANDIDATE, '.github/workflows/zh-4x-packages.yml', 'success')
        failed = api.repository(f'actions/runs/{FAILED_PUBLISH}', 'failed-publisher')
        check_run(failed, FAILED_PUBLISH, '.github/workflows/zh-4x-publish.yml', 'failure')
        return candidate

    run = gates()
    tags_before = git(source, 'ls-remote', '--tags', '--refs', 'origin')
    (evidence / 'tags-before.txt').write_text(tags_before + '\n', encoding='utf-8')
    before = api.releases('before')
    check_older(before, before)
    check_frozen(before, {line.split()[1]: line.split()[0] for line in tags_before.splitlines()}, baseline)
    draft = api.repository(f'releases/{DRAFT}', 'empty-draft')
    check_draft(draft)
    latest_before = api.latest('latest-before')
    require(latest_before['id'] == baseline['latest_before_id'] is None, 'Frozen no-Latest baseline changed')
    os.environ.update(SOURCE_SHA=SOURCE, CANDIDATE_RUN=str(CANDIDATE), CANDIDATE_ATTEMPT='1', RELEASE_TAG=TAG)
    for name, directory in [('zh4-candidate-Linux', 'candidate/zh4-candidate-Linux'),
                            ('zh4-candidate-Windows', 'candidate/zh4-candidate-Windows'),
                            ('zh4-release-manifest', 'acceptance')]:
        subprocess.run(['gh', 'run', 'download', str(CANDIDATE), '--repo', REPO,
                        '-n', name, '-D', str(work / directory)], check=True)
    for platform in ('Linux', 'Windows'):
        directory = work / 'candidate' / ('zh4-candidate-' + platform)
        subprocess.run(['sha256sum', '-c', 'SHA256SUMS-' + platform + '.txt'], cwd=directory, check=True)
    dist = work / 'dist'
    dist.mkdir()
    for directory in (work / 'candidate').iterdir():
        for path in directory.iterdir():
            if path.suffix in {'.AppImage', '.deb', '.exe', '.zip'}:
                require(not (dist / path.name).exists(), 'Duplicate candidate filename')
                shutil.copyfile(path, dist / path.name)
    notes = prepare(source, work, run)
    sys.path.insert(0, str(source / 'packaging/localization'))
    from release_assets import verify_release
    require(draft['body'].replace('\r\n', '\n').rstrip('\n') == notes.replace('\r\n', '\n').rstrip('\n'),
            'Existing draft notes differ from accepted rendered notes')
    gates()
    check_older(before, api.releases('pre-upload'))
    require(git(source, 'ls-remote', '--tags', '--refs', 'origin') == tags_before, 'Existing tags changed before upload')
    check_draft(api.repository(f'releases/{DRAFT}', 'still-empty'))
    require(api.latest('latest-pre-upload')['id'] == latest_before['id'], 'Latest changed')
    manifest = json.loads((work / 'public-asset-manifest.json').read_text(encoding='utf-8'))
    expected_names = {asset['name'] for asset in manifest['assets']} | {'SHA256SUMS.txt'}
    require(len(expected_names) == 5 and {path.name for path in (work / 'release-assets').iterdir()} == expected_names,
            'Expected exactly the four accepted products and checksum file before upload')
    responses = []
    from urllib.parse import quote
    for path in sorted((work / 'release-assets').iterdir()):
        response = api.call(f'https://uploads.github.com/repos/{REPO}/releases/{DRAFT}/assets?name=' + quote(path.name, safe=''),
                            'upload-' + path.name, '--method', 'POST', '-H', 'Content-Type: application/octet-stream', '--input', str(path))
        check_upload(response, path, responses)
        responses.append(response)  # Only original successful POST bodies, never inventory substitutes.
    draft = api.repository(f'releases/{DRAFT}', 'uploaded-draft')
    check_draft(draft, empty=False)
    verify_release(work / 'release-assets', draft, responses, TAG, True, notes)

    def download_and_verify(release, state, label):
        destination = work / label
        destination.mkdir()
        for asset in release['assets']:
            api.repository(f'releases/assets/{asset["id"]}', label + '-' + str(asset['id']),
                           '-H', 'Accept: application/octet-stream', download=destination / asset['name'])
        verify_release(work / 'release-assets', release, responses, TAG, state, notes, destination)

    download_and_verify(draft, True, 'draft-downloads')
    gates()
    check_older(before, api.releases('pre-publication'))
    require(git(source, 'ls-remote', '--tags', '--refs', 'origin') == tags_before, 'Existing tags changed')
    require(api.latest('latest-pre-publication')['id'] == latest_before['id'], 'Latest changed')
    draft = api.repository(f'releases/{DRAFT}', 'final-draft')
    check_draft(draft, empty=False)
    verify_release(work / 'release-assets', draft, responses, TAG, True, notes, work / 'draft-downloads')
    api.repository(f'releases/{DRAFT}', 'publish-response', '--method', 'PATCH', '-F', 'draft=false',
                   '-F', 'prerelease=false', '-f', 'make_latest=true')
    published = api.repository(f'releases/{DRAFT}', 'published')
    require(published['id'] == DRAFT, 'Published ID changed')
    verify_release(work / 'release-assets', published, responses, TAG, False, notes)
    download_and_verify(published, False, 'public-downloads')
    check_older(before, api.releases('after'))
    require(git(source, 'ls-remote', '--tags', '--refs', 'origin') == tags_before, 'Existing tags changed')
    require(api.latest('latest-after')['id'] == DRAFT, 'Latest is not the verified release')
    write_json(evidence / 'SUCCESS.json', {'release_id': DRAFT, 'tag': TAG, 'source': SOURCE, 'control': head})


if __name__ == '__main__':
    main()
