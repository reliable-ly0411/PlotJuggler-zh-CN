# SPDX-License-Identifier: MPL-2.0
"""Synthetic generated-media import; no live service or native run."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('media_import_planner', ROOT / 'scripts/windows/plan_native_stage.py')
planner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(planner)
NAMES = ('test_480p.mp4', 'test_1080p_bframes.mp4', 'test_images.mcap', 'potato.mcap')
PATHS = tuple('s/pj_scene2D/testdata/' + name for name in NAMES)

FAKE_CLOSURE = '''
import hashlib, json
from pathlib import Path
SYNTHETIC_MEDIA_NAMES = ('test_480p.mp4', 'test_1080p_bframes.mp4', 'test_images.mcap', 'potato.mcap')
SYNTHETIC_MEDIA_PATHS = tuple('s/pj_scene2D/testdata/' + x for x in SYNTHETIC_MEDIA_NAMES)
class ClosureError(Exception): pass
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def verify_generated_media(root, source_sha, source_tree, trusted_manifest_sha, manifest_files=None):
    root=Path(root); d=root/'b/native-kit/media-fixtures'; raw=(d/'manifest.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=trusted_manifest_sha: raise ClosureError('manifest hash')
    manifest=json.loads(raw); receipt=json.loads((d/'generation-receipt.json').read_text(encoding='utf-8'))
    if receipt['source_sha']!=source_sha or receipt['source_tree']!=source_tree or receipt['manifest_sha256']!=trusted_manifest_sha: raise ClosureError('identity')
    if set(receipt['files'])!=set(SYNTHETIC_MEDIA_PATHS): raise ClosureError('file set')
    for name,path in zip(SYNTHETIC_MEDIA_NAMES,SYNTHETIC_MEDIA_PATHS):
        item=receipt['files'][path]; actual=root/path
        if item!=manifest['files'][name] or not actual.is_file() or actual.stat().st_size!=item['bytes'] or sha(actual)!=item['sha256']: raise ClosureError('file hash')
    return {'manifest_sha256':trusted_manifest_sha,'files':receipt['files']}
def verify_generated_source_status(raw):
    expected={'?? '+x[2:] for x in SYNTHETIC_MEDIA_PATHS}
    if not raw.endswith('\\0') or set(raw[:-1].split('\\0'))!=expected or len(raw[:-1].split('\\0'))!=4: raise ClosureError('source status')
'''
FAKE_GENERATOR = '''
import hashlib,json
from pathlib import Path
def verify_manifest(directory, expected_sha):
    directory=Path(directory); raw=(directory/'manifest.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==expected_sha
    manifest=json.loads(raw); assert manifest['schema']==1 and manifest['synthetic'] is True
    assert manifest['semantics']['sentinel'] == 'synthetic checked'
    for name,record in manifest['files'].items():
        path=directory/name
        assert path.is_file() and not path.is_symlink() and path.stat().st_size==record['bytes']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==record['sha256']
    return manifest
'''


@unittest.skipUnless(shutil.which('git'), 'Git is required')
class GeneratedMediaImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='native-media-import-'); self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name); self.root = self.base / 'root'; self.source = self.root / 's'
        self.source.mkdir(parents=True); (self.root / 'b/native-kit').mkdir(parents=True); (self.root / 'i').mkdir()
        self.git('init', '-q'); self.write_source('LICENSE', b'project license')
        self.write_source('pj_scene2D/testdata/README.md', b'tracked readme')
        self.write_source('scripts/windows/verify_native_ci_closure.py', FAKE_CLOSURE.encode())
        self.write_source('scripts/native-fixtures/generate_media_fixtures.py', FAKE_GENERATOR.encode())
        self.write_source('scripts/native-fixtures/mcap_fixture_generator.cpp', b'synthetic source')
        self.license = b'synthetic license'; self.lock = {'version': 'synthetic', 'license_sha256': hashlib.sha256(self.license).hexdigest()}
        self.write_source('scripts/native-fixtures/mcap-source-lock.json', json.dumps(self.lock).encode())
        self.git('add', '.'); self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'source')
        self.refresh_identity()
        self.input = self.base / 'media'; self.input.mkdir(); (self.input / 'evidence').mkdir()
        (self.input / 'evidence/MCAP-LICENSE').write_bytes(self.license)
        self.content = {name: ('synthetic bytes for ' + name).encode() for name in NAMES}
        for name, value in self.content.items(): (self.input / name).write_bytes(value)
        self.manifest = {'schema': 1, 'synthetic': True, 'semantics': {'sentinel': 'synthetic checked'}, 'mcap_source': self.lock,
                         'files': {name: {'bytes': len(value), 'sha256': hashlib.sha256(value).hexdigest()}
                                   for name, value in self.content.items()},
                         'generator_sources': {name: planner.digest(self.source / 'scripts/native-fixtures' / name)
                                               for name in ('generate_media_fixtures.py', 'mcap_fixture_generator.cpp', 'mcap-source-lock.json')}}
        self.write_manifest()

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.source), *args], env=planner.git_environment()).decode('utf-8').strip()

    def refresh_identity(self):
        self.sha, self.tree = self.git('rev-parse', 'HEAD'), self.git('rev-parse', 'HEAD^{tree}')
        self.logical = 'C:\\Test Root\\n\\' + self.sha[:12]

    def write_source(self, relative, data):
        target = self.source / relative; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)

    def write_manifest(self):
        (self.input / 'manifest.json').write_text(json.dumps(self.manifest), encoding='utf-8')
        self.expected = planner.digest(self.input / 'manifest.json')

    def env(self):
        return mock.patch.dict(os.environ, {'PJ_MEDIA_MANIFEST_SHA256': self.expected,
                              'PJ_MEDIA_SOURCE_SHA': self.sha, 'PJ_MEDIA_SOURCE_TREE': self.tree})

    def run_import(self):
        return planner.import_generated_media(self.root, self.logical, self.sha, self.tree, self.input, self.expected)

    def test_exact_four_fixtures_are_imported_once_and_bound_to_source(self):
        with self.env():
            self.assertIsNone(planner.verified_source_state(self.root, self.logical, self.sha, self.tree, allow_initial_clean=True))
            with self.assertRaisesRegex(planner.PlanError, 'receipt is missing'):
                planner.verified_source_state(self.root, self.logical, self.sha, self.tree)
            receipt = self.run_import()
            self.assertEqual(set(receipt['files']), set(PATHS))
            verified = planner.verified_source_state(self.root, self.logical, self.sha, self.tree)
            self.assertEqual(verified['manifest_sha256'], self.expected)
            candidate = planner.Candidate(self.root, self.logical, self.sha, self.tree)
            selected = {item['destination'] for item in candidate.files.values()}
            self.assertTrue(set(PATHS) <= selected)
            self.assertTrue({'b/native-kit/media-fixtures/manifest.json',
                             'b/native-kit/media-fixtures/generation-receipt.json',
                             'b/native-kit/media-fixtures/MCAP-LICENSE'} <= selected)
            with self.assertRaises(planner.PlanError): self.run_import()
            extra = self.source / 'unrelated.txt'; extra.write_text('untracked', encoding='utf-8')
            with self.assertRaisesRegex(planner.PlanError, 'exact Git status'):
                planner.verified_source_state(self.root, self.logical, self.sha, self.tree)
            extra.unlink()
            (self.root / PATHS[0]).write_bytes(b'changed')
            with self.assertRaisesRegex(planner.PlanError, 'identity or exact Git status'):
                planner.verified_source_state(self.root, self.logical, self.sha, self.tree)

    def test_wrong_digest_or_generator_hash_fails_before_any_copy(self):
        with self.env():
            (self.input / 'manifest.json').write_bytes(b'tampered')
            with self.assertRaisesRegex(planner.PlanError, 'manifest differs'):
                self.run_import()
            self.assertFalse((self.root / PATHS[0]).exists())
        self.manifest['generator_sources']['mcap_fixture_generator.cpp'] = '0' * 64; self.write_manifest()
        with self.env(), self.assertRaisesRegex(planner.PlanError, 'generator source differs'):
            self.run_import()
        self.assertFalse((self.root / PATHS[0]).exists())

    def test_changed_bytes_and_wrong_semantics_fail_before_copy(self):
        (self.input / NAMES[0]).write_bytes(b'corrupt')
        with self.env(), self.assertRaisesRegex(planner.PlanError, 'semantic records failed'):
            self.run_import()
        self.assertFalse((self.root / PATHS[0]).exists())
        (self.input / NAMES[0]).write_bytes(self.content[NAMES[0]])
        self.manifest['semantics']['sentinel'] = 'invalid'; self.write_manifest()
        with self.env(), self.assertRaisesRegex(planner.PlanError, 'semantic records failed'):
            self.run_import()
        self.assertFalse((self.root / PATHS[0]).exists())

    def test_preexisting_or_tracked_target_is_never_overwritten(self):
        path = self.root / PATHS[0]; path.write_bytes(b'keep')
        with self.env(), self.assertRaisesRegex(planner.PlanError, 'initially clean'):
            self.run_import()
        self.assertEqual(path.read_bytes(), b'keep')
        self.git('add', PATHS[0][2:]); self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                                               'commit', '-qm', 'tracked target'); self.refresh_identity()
        with self.env(), self.assertRaisesRegex(planner.PlanError, 'Git-tracked'):
            self.run_import()
        self.assertEqual(path.read_bytes(), b'keep')


if __name__ == '__main__':
    unittest.main()
