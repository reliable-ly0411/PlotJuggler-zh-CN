#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Offline regressions for exact-byte promotion and fail-closed draft publication."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('release_assets', ROOT / 'packaging/localization/release_assets.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
VERSION = '4.0.0-zh.1.rc.1'
DEB = 'plotjuggler4_4.0.0~zh.1~rc.1-1_amd64-zh-CN.deb'
PUBLIC_DEB = 'plotjuggler4_4.0.0.zh.1.rc.1-1_amd64-zh-CN.deb'
TAG = 'v' + VERSION
NOTES = '## Upstream notes (complete)\n\n**Full Changelog**: https://example.test/compare/base...release\n'


class ReleaseAssetsTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)
        self.source = self.work / 'candidate'
        self.source.mkdir()
        self.target = self.work / 'release-assets'
        names = [f'PlotJuggler-{VERSION}-Windows-x64-zh-CN.exe',
                 f'PlotJuggler-{VERSION}-x86_64-zh-CN.AppImage', DEB]
        self.assets = []
        for index, name in enumerate(names):
            path = self.source / name
            path.write_bytes(f'accepted package {index}\n'.encode())
            self.assets.append({'name': name, 'size': path.stat().st_size, 'sha256': module.sha256(path)})

    def stage(self):
        """Exercise the production staging and checksum generator together."""
        result = module.stage_public_assets(self.source, self.target, self.assets)
        subprocess.run([sys.executable, str(ROOT / 'packaging/localization/hash_packages.py'),
                        str(self.target), '--output', 'SHA256SUMS.txt'],
                       check=True, capture_output=True, text=True)
        self.release = {'tag_name': TAG, 'draft': True, 'prerelease': True, 'body': NOTES, 'assets': [
            {'name': path.name, 'id': index + 1, 'size': path.stat().st_size,
             'state': 'uploaded', 'digest': 'sha256:' + module.sha256(path)}
            for index, path in enumerate(sorted(self.target.iterdir()))]}
        self.responses = copy.deepcopy(self.release['assets'])
        return result

    def verify(self, **kwargs):
        module.verify_release(self.target, self.release, self.responses, TAG, True, NOTES, **kwargs)

    def test_tilde_mapping_preserves_candidate_names_bytes_and_manifest(self):
        original = copy.deepcopy(self.assets)
        rows = self.stage()
        self.assertEqual(self.assets, original)
        self.assertEqual(module.public_name(DEB), PUBLIC_DEB)
        self.assertEqual({p.name for p in self.source.iterdir()}, {a['name'] for a in original})
        for row in rows:
            self.assertEqual((self.source / row['candidate_name']).read_bytes(),
                             (self.target / row['name']).read_bytes())
            self.assertEqual(module.public_name(row['name']), row['name'])
        sums = (self.target / 'SHA256SUMS.txt').read_text()
        self.assertIn(PUBLIC_DEB, sums)
        self.assertNotIn('~', sums)
        self.verify()

    def test_unsupported_names_fail_closed(self):
        for name in ['../file.deb', 'file name.deb', 'x\n.deb', '.file.deb', 'file.deb.',
                     'file?.deb', 'file#.deb', 'dir/file.deb', 'dir\\file.deb', '中文.deb', '~file.deb']:
            with self.subTest(name=name), self.assertRaises(ValueError):
                module.public_name(name)

    def test_collision_duplicate_and_manifest_drift_fail_before_copy(self):
        for mutation in ['collision', 'duplicate', 'wrong_digest', 'wrong_size', 'missing', 'extra']:
            with self.subTest(mutation=mutation):
                assets = copy.deepcopy(self.assets)
                if mutation == 'collision':
                    assets.append(dict(assets[-1], name=PUBLIC_DEB))
                elif mutation == 'duplicate':
                    assets.append(assets[0])
                elif mutation == 'wrong_digest':
                    assets[0]['sha256'] = '0' * 64
                elif mutation == 'wrong_size':
                    assets[0]['size'] += 1
                elif mutation == 'missing':
                    assets.pop()
                else:
                    assets.append(dict(assets[0], name='extra.exe'))
                with self.assertRaises(ValueError):
                    module.stage_public_assets(self.source, self.target, assets)
                self.assertFalse(self.target.exists())

    def test_existing_destination_is_never_overwritten(self):
        self.target.mkdir()
        sentinel = self.target / 'keep'
        sentinel.write_bytes(b'existing')
        with self.assertRaises(FileExistsError):
            module.stage_public_assets(self.source, self.target, self.assets)
        self.assertEqual(sentinel.read_bytes(), b'existing')

    @unittest.skipUnless(shutil.which('dpkg-deb'), 'dpkg-deb is needed to inspect real Debian metadata')
    def test_real_deb_ordered_version_is_unchanged(self):
        package = self.work / 'package'
        (package / 'DEBIAN').mkdir(parents=True)
        (package / 'DEBIAN/control').write_text(
            'Package: plotjuggler4\nVersion: 4.0.0~zh.1~rc.1-1\nArchitecture: amd64\n'
            'Maintainer: Test <test@example.test>\nDescription: Filename regression fixture\n')
        subprocess.run(['dpkg-deb', '--build', str(package), str(self.source / DEB)],
                       check=True, capture_output=True)
        self.assets[-1].update(size=(self.source / DEB).stat().st_size, sha256=module.sha256(self.source / DEB))
        self.stage()
        self.assertEqual(subprocess.check_output(['dpkg-deb', '-f', str(self.target / PUBLIC_DEB), 'Version'],
                                                text=True).strip(), '4.0.0~zh.1~rc.1-1')
        self.assertEqual((self.source / DEB).read_bytes(), (self.target / PUBLIC_DEB).read_bytes())

    def test_original_tilde_checksum_mismatch_is_rejected(self):
        self.stage()
        sums = self.target / 'SHA256SUMS.txt'
        sums.write_text(sums.read_text().replace(PUBLIC_DEB, DEB))
        with self.assertRaisesRegex(ValueError, 'SHA256SUMS'):
            self.verify()

    def test_upload_and_inventory_names_must_both_match(self):
        self.stage()
        for target in [self.responses, self.release['assets']]:
            original = copy.deepcopy(target)
            target[0]['name'] = 'GitHub-renamed.exe'
            with self.assertRaisesRegex(ValueError, 'renamed assets'):
                self.verify()
            target[:] = original

    def test_missing_extra_duplicate_and_replaced_uploads_are_rejected(self):
        self.stage()
        original = copy.deepcopy(self.release['assets'])
        variants = [original[:-1], original + [dict(original[0], name='extra.exe', id=99)],
                    [original[0]] + original[:-1],
                    [dict(original[0], id=original[1]['id'])] + original[1:],
                    [dict(original[0], id=99)] + original[1:]]
        for assets in variants:
            with self.subTest(assets=assets), self.assertRaises(ValueError):
                self.release['assets'] = assets
                self.verify()

    def test_upload_state_size_and_server_digest_are_required(self):
        self.stage()
        for target in [self.release['assets'], self.responses]:
            original = target[0].copy()
            for changes in [{'state': 'starter'}, {'size': original['size'] + 1},
                            {'digest': None}, {'digest': 'sha256:' + '0' * 64}, {'id': 0}]:
                with self.subTest(changes=changes), self.assertRaises(ValueError):
                    target[0] = dict(original, **changes)
                    self.verify()
            target[0] = original.copy()
            del target[0]['digest']
            with self.assertRaises(ValueError):
                self.verify()
            target[0] = original

    def test_release_identity_state_and_complete_notes_are_required(self):
        self.stage()
        original = self.release.copy()
        for changes in [{'tag_name': 'v4.0.0-wrong'}, {'draft': False},
                        {'prerelease': False}, {'body': 'Only a link, not the full upstream notes'}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.release = dict(original, **changes)
                self.verify()
        self.release = original
        self.release['draft'] = False
        module.verify_release(self.target, self.release, self.responses, TAG, False, NOTES)

    def test_downloads_must_match_exact_names_and_all_bytes(self):
        self.stage()
        downloads = self.work / 'downloads'
        shutil.copytree(self.target, downloads)
        self.verify(downloads=downloads)
        package = downloads / PUBLIC_DEB
        original = package.read_bytes()
        package.write_bytes(b'x' * len(original))
        with self.assertRaisesRegex(ValueError, 'Downloaded bytes'):
            self.verify(downloads=downloads)
        package.write_bytes(original)
        package.rename(downloads / DEB)
        with self.assertRaisesRegex(ValueError, 'Downloaded asset names'):
            self.verify(downloads=downloads)
        (downloads / DEB).rename(package)
        (downloads / 'SHA256SUMS.txt').write_bytes(b'wrong checksum file')
        with self.assertRaisesRegex(ValueError, 'Downloaded bytes'):
            self.verify(downloads=downloads)

    def workflow_run(self, name):
        """Use the actual workflow shell blocks, not a duplicate publish sequence."""
        text = (ROOT / '.github/workflows/zh-4x-publish.yml').read_text()
        step = text.split('      - name: ' + name + '\n', 1)[1].split('\n      - ', 1)[0]
        return textwrap.dedent(step.split('        run: |\n', 1)[1])

    @unittest.skipUnless(shutil.which('bash') and shutil.which('sha256sum'), 'Workflow runs on Linux')
    def test_workflow_only_publishes_after_successful_draft_verification(self):
        """Reproduce GitHub's tilde rename with a mock API; no real network writes."""
        self.stage()
        (self.work / 'packaging').symlink_to(ROOT / 'packaging', target_is_directory=True)
        (self.work / 'release-notes.md').write_text(NOTES)
        mock_bin = self.work / 'mock-bin'
        mock_bin.mkdir()
        mock = mock_bin / 'gh'
        mock.write_text('#!' + sys.executable + '\n' + textwrap.dedent('''\
            import hashlib, json, os
            from pathlib import Path
            import shutil, sys
            args = sys.argv[1:]
            state = Path('mock-release.json')
            repo = os.environ['GITHUB_REPOSITORY']
            if args[:2] == ['release', 'create']:
                state.write_text(json.dumps({
                    'id': 123, 'tag_name': os.environ['RELEASE_TAG'], 'draft': True, 'prerelease': True,
                    'body': Path('release-notes.md').read_text(), 'assets': [],
                    'upload_url': f'https://uploads.github.com/repos/{repo}/releases/123/assets{{?name,label}}'}))
                Path('server-bytes').mkdir()
            elif args[:2] == ['release', 'download']:
                shutil.copytree('server-bytes', args[args.index('-D') + 1])
            elif args[:2] == ['release', 'edit']:
                Path('published').write_text('yes')
            elif args[0] == 'api':
                if any('/actions/runs/' in a for a in args):
                    print(os.environ['CANDIDATE_ATTEMPT'])
                elif '--input' in args:
                    path = Path(args[args.index('--input') + 1])
                    name = path.name.replace('~', '.')
                    if os.environ.get('MOCK_RENAME'):
                        name = 'unexpected-' + name
                    body = path.read_bytes()
                    r = json.loads(state.read_text())
                    asset = {'id': len(r['assets']) + 1, 'name': name, 'state': 'uploaded',
                             'size': len(body), 'digest': 'sha256:' + hashlib.sha256(body).hexdigest()}
                    r['assets'].append(asset)
                    state.write_text(json.dumps(r))
                    (Path('server-bytes') / name).write_bytes(body)
                    print(json.dumps(asset))
                elif '--method' in args:
                    print('{}')
                else:
                    print(state.read_text())
            else:
                raise SystemExit('Unexpected mock gh call: ' + str(args))
            '''))
        mock.chmod(0o755)
        script = '\n'.join(self.workflow_run(name) for name in [
            'Create immutable tag and upload the accepted bytes to a draft',
            'Verify actual draft names and bytes before publication',
            'Publish only the verified draft'])
        env = dict(os.environ, PATH=str(mock_bin) + os.pathsep + os.environ['PATH'],
                   GITHUB_REPOSITORY='reliable-ly0411/PlotJuggler-zh-CN', RELEASE_TAG=TAG,
                   SOURCE_SHA='a' * 40, CANDIDATE_RUN='12345', CANDIDATE_ATTEMPT='1')
        # The fixed public names pass upload responses, actual inventory, and
        # re-download verification before the workflow reaches draft=false.
        result = subprocess.run(['bash', '-c', script], cwd=self.work, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((self.work / 'published').exists())
        for directory in ['upload-responses', 'server-bytes', 'draft-check']:
            shutil.rmtree(self.work / directory)
        (self.work / 'published').unlink()
        # The original incident: candidate tilde names/checksums reach upload,
        # GitHub returns dotted names, and publication must never be attempted.
        (self.target / PUBLIC_DEB).rename(self.target / DEB)
        sums = self.target / 'SHA256SUMS.txt'
        sums.write_text(sums.read_text().replace(PUBLIC_DEB, DEB))
        result = subprocess.run(['bash', '-c', script], cwd=self.work, env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.work / 'published').exists())
        self.assertIn('public-safe asset', result.stderr)
        for directory in ['upload-responses', 'server-bytes']:
            shutil.rmtree(self.work / directory)
        (self.target / DEB).rename(self.target / PUBLIC_DEB)
        sums.write_text(sums.read_text().replace(DEB, PUBLIC_DEB))
        # Even a new, unanticipated server rename cannot silently pass.
        result = subprocess.run(['bash', '-c', script], cwd=self.work, env=dict(env, MOCK_RENAME='1'),
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.work / 'published').exists())
        self.assertIn('renamed assets', result.stderr)

    def test_workflow_does_not_bypass_or_reorder_the_draft_gate(self):
        workflow = (ROOT / '.github/workflows/zh-4x-publish.yml').read_text()
        self.assertEqual(workflow.count('--draft=false'), 1)
        self.assertLess(workflow.index('--downloads draft-check'), workflow.index('--draft=false'))
        self.assertNotIn('continue-on-error:', workflow)
        self.assertNotIn('--clobber', workflow)
        preparation = self.workflow_run('Download and verify the original accepted packages')
        self.assertLess(preparation.index('stage_public_assets(Path'), preparation.index('hash_packages.py'))
        self.assertIn("for a in public_assets", preparation)
        self.assertIn("body.replace('`' + asset['candidate_name'] + '`', '`' + asset['name'] + '`')", preparation)


if __name__ == '__main__':
    unittest.main()
