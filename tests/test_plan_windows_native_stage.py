# SPDX-License-Identifier: MPL-2.0
"""Small independent Git/CTest fixtures for the native staging candidate."""
import importlib.util
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('native_stage_plan', ROOT / 'scripts/windows/plan_native_stage.py')
planner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(planner)
pe_fixture_spec = importlib.util.spec_from_file_location('pe_stage_fixture', ROOT / 'tests/test_native_pe_closure.py')
pe_fixture = importlib.util.module_from_spec(pe_fixture_spec)
pe_fixture_spec.loader.exec_module(pe_fixture)
audit_fixture_spec = importlib.util.spec_from_file_location('audit_stage_fixture', ROOT / 'tests/test_windows_native_bundle_audit.py')
audit_fixture = importlib.util.module_from_spec(audit_fixture_spec)
audit_fixture_spec.loader.exec_module(audit_fixture)


class HostedPESearchPathTests(unittest.TestCase):
    """Do not treat non-PATH reviewed directories as reachable providers."""
    def test_only_actual_ci_search_directories_are_resolved_in_order(self):
        paths = {'qt': 'q/6.12.0/msvc2022_64', 'ctest': 't/cmake/bin/ctest.exe'}
        runtime = ['c/conan/bin', 'q/6.12.0/msvc2022_64/bin']
        expected = ['q/6.12.0/msvc2022_64/bin', 't/cmake/bin', 'c/conan/bin']
        self.assertEqual(planner.ci_pe_search_directories(paths, runtime, {}, audit_fixture.ROOT), expected)
        self.assertEqual(planner.ci_pe_search_directories(paths, runtime, {'loader_extra_dirs': []},
                                                          audit_fixture.ROOT), expected)
        for extra in (['b/unreachable'], 'b/unreachable', None):
            with self.subTest(extra=extra), self.assertRaisesRegex(planner.PlanError, 'not part of the hosted CI PATH'):
                planner.ci_pe_search_directories(paths, runtime, {'loader_extra_dirs': extra}, audit_fixture.ROOT)


class CapturedArchiveTests(unittest.TestCase):
    """Synthetic byte-level checks, not a Windows bootstrap or safety review."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='native-zip-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.stage = self.base / 'stage'
        (self.stage / 's').mkdir(parents=True)
        (self.stage / 'r').mkdir()
        (self.stage / 's/LICENSE').write_bytes(b'license')
        (self.stage / 's/input.txt').write_bytes(b'captured input')
        # NTFS records are 100-nanosecond aligned; POSIX filesystems need not be.
        for path in (self.stage / 's').iterdir():
            t = path.stat().st_mtime_ns // 100 * 100
            os.utime(path, ns=(t, t))
        metadata = self.base / 'provenance.json'
        metadata.write_text(json.dumps(audit_fixture.provenance()), encoding='utf-8')
        captured = planner.audit.create_manifest(self.stage, audit_fixture.ROOT, metadata,
                                                  self.stage / '_bundle/manifest.json')
        self.manifest_sha = captured['manifest_sha256']
        self.archive = self.base / 'native-kit.zip'

    def pack(self):
        with mock.patch.object(planner.shutil, 'disk_usage', return_value=mock.Mock(free=64 * 1024**3)):
            return planner.archive_captured_stage(self.stage, audit_fixture.ROOT, self.archive, self.manifest_sha)

    def test_exact_manifest_members_and_empty_directories_are_archived(self):
        receipt = self.pack()
        self.assertEqual(receipt['archive_sha256'], hashlib.sha256(self.archive.read_bytes()).hexdigest())
        with zipfile.ZipFile(self.archive) as archive:
            self.assertEqual(set(archive.namelist()), {'s/', 'r/', '_bundle/', 's/LICENSE',
                                                       's/input.txt', '_bundle/manifest.json'})
            self.assertEqual(archive.comment, b'')
            self.assertEqual(archive.read('s/input.txt'), b'captured input')
            self.assertTrue(all(x.compress_type == (zipfile.ZIP_STORED if x.is_dir() else zipfile.ZIP_DEFLATED)
                                for x in archive.infolist()))

    def test_changed_file_manifest_or_unlisted_file_never_produce_zip(self):
        (self.stage / 's/input.txt').write_bytes(b'tampered')
        with self.assertRaises(planner.PlanError): self.pack()
        self.assertFalse(self.archive.exists())
        (self.stage / 's/input.txt').write_bytes(b'captured input')
        (self.stage / 's/extra').write_bytes(b'unlisted')
        with self.assertRaises(planner.PlanError): self.pack()
        self.assertFalse(self.archive.exists())
        with self.assertRaises(planner.PlanError):
            planner.archive_captured_stage(self.stage, audit_fixture.ROOT, self.archive, '0' * 64)

    def test_insufficient_disk_and_existing_output_fail_before_write(self):
        with mock.patch.object(planner.shutil, 'disk_usage', return_value=mock.Mock(free=0)):
            with self.assertRaises(planner.PlanError):
                planner.archive_captured_stage(self.stage, audit_fixture.ROOT, self.archive, self.manifest_sha)
        self.assertFalse(self.archive.exists())
        self.archive.write_bytes(b'unchanged')
        with self.assertRaises(planner.PlanError): self.pack()
        self.assertEqual(self.archive.read_bytes(), b'unchanged')


class PeSubsetTests(unittest.TestCase):
    def setUp(self):
        self.logical = r'C:\Test\n\123456789abc'
        self.paths = ['t/python/python.exe', 't/python/python3.dll', 't/python/python312.dll',
                      't/python/_ssl.pyd', 't/python/libcrypto-3.dll', 't/python/sqlite3.dll',
                      't/cmake/bin/ctest.exe', 'b/selected.exe', 'b/unselected.exe',
                      'b/ci-temp-probe/RelWithDebInfo/pj_native_ci_temp_probe.exe',
                      'i/temp-probe/RelWithDebInfo/pj_native_temp_probe.exe',
                      'c/runtime/needed.dll', 'c/runtime/visible-other.dll', 'b/plugins/observed.dll',
                      'b/plugins/unobserved.dll']
        self.plan = {'origins': {'fixture': {'root': '/fixture'}},
                     'files': [{'origin': 'fixture', 'source': x, 'destination': x, 'sha256': 'a' * 64}
                               for x in self.paths]}
        self.docs = {'main': {'tests': [{'name': 'Selected.case',
                                        'command': [self.logical + r'\b\selected.exe']}]}}

    def test_subset_seeds_reviewed_modules_but_not_unrelated_binaries(self):
        plan = planner.selected_pe_plan(self.plan, ['c/runtime'], {('main', 'Selected.case')}, self.docs,
                                        self.logical, ['b/plugins/observed.dll'])
        files = {x['destination'] for x in plan['files']}
        self.assertIn('b/selected.exe', files)
        self.assertIn('b/plugins/observed.dll', files)
        self.assertTrue({'t/python/_ssl.pyd', 't/python/libcrypto-3.dll', 't/python/sqlite3.dll'} <= files)
        self.assertNotIn('c/runtime/needed.dll', files)
        self.assertNotIn('c/runtime/visible-other.dll', files)
        self.assertNotIn('b/unselected.exe', files)
        self.assertNotIn('b/plugins/unobserved.dll', files)

    def test_unobserved_or_missing_selected_inputs_cannot_be_synthesized(self):
        for values in ([], ['b/plugins/missing.dll'], ['b/plugins/observed.dll', 'b/plugins/observed.dll']):
            with self.subTest(values=values), self.assertRaises(planner.PlanError):
                planner.selected_pe_plan(self.plan, ['c/runtime'], {('main', 'Selected.case')}, self.docs,
                                         self.logical, values)
        self.docs['main']['tests'][0]['command'][0] = r'C:\Elsewhere\runner.exe'
        with self.assertRaises(planner.PlanError):
            planner.selected_pe_plan(self.plan, ['c/runtime'], {('main', 'Selected.case')}, self.docs,
                                     self.logical, ['b/plugins/observed.dll'])


class DynamicInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='dynamic-inventory-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.logical = r'C:\Test\n\123456789abc'
        self.sha = '123456789abc' + '0' * 28
        self.tree = 'a' * 40
        contents = {'s/test.cpp': b'source', 'b/runner.exe': b'runner',
                    'q/plugins/example.dll': b'plugin', 't/tools/helper.exe': b'child'}
        entries = []
        for name, data in contents.items():
            path = self.root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
            entries.append({'origin': 'root', 'source': name, 'destination': name, 'sha256': planner.digest(path)})
        self.plan = {'origins': {'root': {'root': str(self.root)}}, 'files': entries}
        item = lambda name: {'path': name, 'sha256': planner.digest(self.root / name)}
        self.inventory = {'schema': 1, 'basis': 'source-analysis', 'source_sha': self.sha, 'source_tree': self.tree,
                          'configuration': 'RelWithDebInfo', 'scopes': [{'suite': 'main', 'cases': ['Case.one'],
                          'runner': item('b/runner.exe'), 'source_files': [item('s/test.cpp')],
                          'dynamic_files': [{**item('q/plugins/example.dll'), 'role': 'Qt plugin'}],
                          'subprocesses': [item('t/tools/helper.exe')], 'reason': 'reviewed source paths'}]}
        self.docs = {'main': {'tests': [{'name': 'Case.one', 'command': [self.logical + r'\b\runner.exe']}]}}

    def check(self):
        return planner.validate_dynamic_inventory(self.plan, self.inventory, {('main', 'Case.one')},
                                                  self.docs, self.logical, self.sha, self.tree)

    def test_source_analysis_binds_all_reviewed_pe_bytes(self):
        self.assertEqual(set(self.check()), {'b/runner.exe', 'q/plugins/example.dll', 't/tools/helper.exe'})

    def test_extra_or_wrong_case_runner_path_hash_and_basis_are_refused(self):
        original = json.loads(json.dumps(self.inventory))
        changes = [lambda x: x.update(basis='observed-trace'),
                   lambda x: x['scopes'][0]['cases'].append('Case.extra'),
                   lambda x: x['scopes'][0]['runner'].update(path='b/other.exe'),
                   lambda x: x['scopes'][0]['dynamic_files'][0].update(sha256='0' * 64),
                   lambda x: x['scopes'][0]['source_files'][0].update(path='q/plugins/example.dll')]
        for change in changes:
            self.inventory = json.loads(json.dumps(original)); change(self.inventory)
            with self.subTest(inventory=self.inventory), self.assertRaises(planner.PlanError): self.check()
        self.inventory = original
        (self.root / 'q/plugins/example.dll').write_bytes(b'tampered')
        with self.assertRaisesRegex(planner.PlanError, 'bytes changed'): self.check()


class ReachablePeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='reachable-pe-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.origins = {'test': {'root': str(self.root)}}
        self.entries = []

    def add(self, name, data):
        path = self.root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
        entry = {'origin': 'test', 'source': name, 'destination': name, 'sha256': planner.digest(path)}
        self.entries.append(entry)
        return entry

    def test_embedded_python_normal_delay_imports_require_unambiguous_provider(self):
        driver = self.add('t/python/python.exe', pe_fixture.fixture(normal=('python312.dll',), delay=()))
        python = self.add('t/python/python312.dll', pe_fixture.fixture(normal=('KERNEL32.dll',), delay=()))
        module = self.add('t/python/_ssl.pyd', pe_fixture.fixture(normal=('libcrypto-3.dll',), delay=('sqlite3.dll',)))
        crypto = self.add('t/python/libcrypto-3.dll', pe_fixture.fixture(normal=('KERNEL32.dll',), delay=()))
        sqlite = self.add('t/python/sqlite3.dll', pe_fixture.fixture(normal=('KERNEL32.dll',), delay=()))
        plan = {'origins': self.origins, 'files': self.entries}
        seeds = {'files': [driver, module]}
        resolved = planner.resolve_selected_pe_plan(plan, seeds, ['t/python'], ['kernel32.dll'])
        self.assertEqual({row['destination'] for row in resolved['files']},
                         {x['destination'] for x in (driver, python, module, crypto, sqlite)})
        planner.pe_helper.audit(resolved, ['t/python'], ['kernel32.dll'])
        self.entries.remove(sqlite)
        with self.assertRaisesRegex(planner.PlanError, 'unresolved selected delay import sqlite3.dll'):
            planner.resolve_selected_pe_plan(plan, seeds, ['t/python'], ['kernel32.dll'])
        self.entries.append(sqlite)
        self.add('c/runtime/libcrypto-3.dll', pe_fixture.fixture(normal=('OTHER.dll',), delay=()))
        with self.assertRaisesRegex(planner.PlanError, 'different visible DLLs collide'):
            planner.resolve_selected_pe_plan(plan, seeds, ['t/python', 'c/runtime'], ['kernel32.dll'])

    def test_only_reachable_dlls_are_audited_but_ambiguous_used_names_fail(self):
        runner = self.add('b/runner.exe', pe_fixture.fixture(normal=('KERNEL32.dll', 'needed.dll'), delay=()))
        needed = self.add('c/runtime/needed.dll', pe_fixture.fixture(normal=('KERNEL32.dll',), delay=()))
        self.add('c/runtime/unrelated.dll', pe_fixture.fixture(normal=('missing.dll',), delay=()))
        plan = {'origins': self.origins, 'files': self.entries}
        resolved = planner.resolve_selected_pe_plan(plan, {'files': [runner]}, ['c/runtime'], ['kernel32.dll'])
        self.assertEqual({x['destination'] for x in resolved['files']}, {'b/runner.exe', 'c/runtime/needed.dll'})
        planner.pe_helper.audit(resolved, ['c/runtime'], ['kernel32.dll'])
        self.add('c/other/needed.dll', pe_fixture.fixture(normal=('other.dll',), delay=()))
        with self.assertRaisesRegex(planner.PlanError, 'different visible DLLs collide'):
            planner.resolve_selected_pe_plan(plan, {'files': [runner]}, ['c/runtime', 'c/other'], ['kernel32.dll'])
        (self.root / 'c/runtime/needed.dll').write_bytes(b'changed')
        with self.assertRaisesRegex(planner.PlanError, 'selected PE bytes changed'):
            planner.resolve_selected_pe_plan(plan, {'files': [needed]}, ['c/runtime'], ['kernel32.dll'])


@unittest.skipUnless(shutil.which('git'), 'Git is required')
class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='native plan ')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / 'root'; self.root.mkdir()
        self.source = self.root / 's'; self.source.mkdir()
        self.git('init', '-q')
        # Match the isolated verifier's Git configuration even when the host
        # globally enables CRLF conversion for this synthetic repository.
        self.git('config', '--local', 'core.autocrlf', 'false')
        (self.source / 'LICENSE').write_text('source license', encoding='utf-8')
        (self.source / 'fixture.txt').write_text('tracked test fixture', encoding='utf-8')
        self.git('add', 'LICENSE', 'fixture.txt')
        self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'fixture')
        self.sha = self.git('rev-parse', 'HEAD')
        self.tree = self.git('rev-parse', 'HEAD^{tree}')
        self.place_identity_root()
        self.build = self.root / 'b'; self.build.mkdir()
        self.i18n = self.root / 'i'; self.i18n.mkdir()
        for directory in (self.build, self.i18n):
            (directory / 'CTestTestfile.cmake').write_text('# synthetic CTest metadata\n', encoding='utf-8')
        (self.build / 'RelWithDebInfo').mkdir()
        (self.build / 'RelWithDebInfo/runner.exe').write_bytes(b'synthetic executable')
        (self.build / 'secret.obj').write_bytes(b'not a runtime input')
        (self.build / '_deps/sdk-build').mkdir(parents=True)
        (self.build / '_deps/sdk-build/CTestTestfile.cmake').write_text('# SDK tests', encoding='utf-8')
        (self.build / 'csv-plugin-work/unrelated').mkdir(parents=True)
        (self.build / 'csv-plugin-work/unrelated/CTestTestfile.cmake').write_text('# unrelated build', encoding='utf-8')

    def place_identity_root(self):
        # A real Windows run must exercise the strict build-root check. Move the
        # disposable fixture whenever its synthetic commit changes.
        root = self.base / 'n' / self.sha[:12]
        root.parent.mkdir(exist_ok=True)
        if self.root != root:
            self.root.rename(root)
        self.root, self.source = root, root / 's'
        if hasattr(self, 'build'):
            self.build, self.i18n = root / 'b', root / 'i'
        self.logical = str(root) if os.name == 'nt' else 'C:\\Test Root\\n\\' + self.sha[:12]

    def git(self, *args):
        result = subprocess.run(['git', '-C', str(self.source), *map(str, args)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def candidate(self, declarations=None):
        return planner.Candidate(self.root, self.logical, self.sha, self.tree, declarations)

    def test_fixture_autocrlf_does_not_mask_changed_source(self):
        inherited = self.base / 'global.gitconfig'
        inherited.write_text('[core]\n    autocrlf = true\n', encoding='utf-8')
        content = b'print(1)\r\nprint(2)\r\n'
        source = self.source / 'crlf-fixture.py'; source.write_bytes(content)
        with mock.patch.dict(os.environ, {'GIT_CONFIG_GLOBAL': str(inherited), 'GIT_CONFIG_NOSYSTEM': '1'}):
            self.git('add', 'crlf-fixture.py')
            self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'CRLF fixture')
            self.sha, self.tree = self.git('rev-parse', 'HEAD'), self.git('rev-parse', 'HEAD^{tree}')
            self.place_identity_root()
            source = self.source / 'crlf-fixture.py'
            info = source.stat()
            os.utime(source, ns=(info.st_atime_ns, info.st_mtime_ns + 2_000_000_000))
            blob = subprocess.check_output(['git', '-C', str(self.source), 'show', 'HEAD:crlf-fixture.py'],
                                           env=planner.git_environment())
            self.assertEqual(blob, content)
            self.candidate()
            source.write_bytes(b'print(9)\r\nprint(2)\r\n')
            with self.assertRaisesRegex(planner.PlanError, 'source checkout is not clean'):
                self.candidate()

    def listing(self, name='Fixture.works', executable='b/RelWithDebInfo/runner.exe'):
        def winpath(relative):
            return self.logical + '\\' + relative.replace('/', '\\')
        return {'kind': 'ctestInfo', 'tests': [{'name': name, 'config': 'RelWithDebInfo',
                 'command': [winpath(executable), winpath('s/fixture.txt')],
                 'properties': [{'name': 'WORKING_DIRECTORY', 'value': winpath('s')}]}],
                'backtraceGraph': {'files': [winpath('s/fixture.txt')]}}

    def test_explicit_hashed_plan_stages_only_enumerated_files_and_preserves_paths(self):
        candidate = self.candidate()
        names = candidate.add_discovery('main', self.listing())
        candidate.add_ctest_metadata()
        plan, report = candidate.finish({'main': names})
        files = {entry['destination'] for entry in plan['files']}
        self.assertTrue({'s/LICENSE', 's/fixture.txt', 'b/RelWithDebInfo/runner.exe',
                         'b/CTestTestfile.cmake', 'i/CTestTestfile.cmake', 'b/_deps/sdk-build/CTestTestfile.cmake'} <= files)
        self.assertNotIn('b/secret.obj', files)
        self.assertNotIn('b/csv-plugin-work/unrelated/CTestTestfile.cmake', files)
        self.assertFalse(any('/.git/' in name for name in files))
        self.assertEqual(report['status'], 'candidate-only-not-uploadable')
        self.assertIn('missing-discovery', {x['code'] for x in report['blockers']})
        self.assertIn('dynamic-dependencies-unreviewed', {x['code'] for x in report['blockers']})
        self.assertEqual(report['coverage'][0]['case'], 'Fixture.works')
        self.assertEqual(report['coverage'][0]['status'], 'safety_unreviewed')
        path = self.base / 'plan.json'; path.write_text(json.dumps(plan), encoding='utf-8')
        stage = self.base / 'stage'
        planner.audit.stage_allowlisted(path, stage, self.logical)
        self.assertEqual((stage / 'b/RelWithDebInfo/runner.exe').read_bytes(), b'synthetic executable')
        self.assertFalse((stage / 'b/secret.obj').exists())
        self.assertTrue((stage / 'r').is_dir())

    def test_packaging_fails_before_stage_without_reviewed_closure_inputs(self):
        plan, report = self.candidate().finish({})
        plan_path = self.base / 'candidate.json'; plan_path.write_text(json.dumps(plan), encoding='utf-8')
        report_path = self.base / 'gaps.json'; report_path.write_text(json.dumps(report), encoding='utf-8')
        stage, archive = self.base / 'new-stage', self.base / 'native-kit.zip'
        with self.assertRaisesRegex(planner.PlanError, 'source-reviewed closure input is missing'):
            planner.package_candidate(self.root, self.logical, self.sha, self.tree, plan_path, report_path, stage, archive)
        self.assertFalse(stage.exists())
        self.assertFalse(archive.exists())

    def test_packaging_refuses_an_unpinned_source_verifier(self):
        scripts = self.source / 'scripts/windows'; scripts.mkdir(parents=True)
        (scripts / 'verify_native_ci_closure.py').write_text('print("synthetic")\n', encoding='utf-8')
        (scripts / 'run_native_ci_verification.py').write_text('# synthetic\n', encoding='utf-8')
        policy = self.source / '.github/windows-native-kit/ci-closure-policy.json'; policy.parent.mkdir(parents=True)
        policy.write_text(json.dumps({'schema': 1, 'verifier_sha256': '0' * 64}), encoding='utf-8')
        self.git('add', '.')
        self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'synthetic review')
        self.sha, self.tree = self.git('rev-parse', 'HEAD'), self.git('rev-parse', 'HEAD^{tree}')
        self.place_identity_root()
        plan, report = self.candidate().finish({})
        plan_path = self.base / 'candidate.json'; plan_path.write_text(json.dumps(plan), encoding='utf-8')
        report_path = self.base / 'gaps.json'; report_path.write_text(json.dumps(report), encoding='utf-8')
        with self.assertRaisesRegex(planner.PlanError, 'does not pin the actual verifier'):
            planner.package_candidate(self.root, self.logical, self.sha, self.tree, plan_path, report_path,
                                      self.base / 'stage', self.base / 'native-kit.zip')
        self.assertFalse((self.base / 'stage').exists())

    def test_packaging_uses_reviewed_evidence_and_capture_in_synthetic_fixture(self):
        """Exercise wiring only: fabricated inventory and PE audit prove no real closure."""
        import types
        scripts = self.source / 'scripts/windows'; scripts.mkdir(parents=True)
        verifier = scripts / 'verify_native_ci_closure.py'; verifier.write_text('# synthetic verifier\n', encoding='utf-8')
        (scripts / 'run_native_ci_verification.py').write_text('# synthetic CI verifier\n', encoding='utf-8')
        (scripts / 'native_marker_mutation.py').write_text('# synthetic mutation controller\n', encoding='utf-8')
        marker_source = self.source / 'pj_runtime/src/ActiveWidgetsMarker.cpp'; marker_source.parent.mkdir(parents=True)
        marker_source.write_bytes(b'synthetic marker source')
        (self.source / 'conan.lock').write_text('{}\n', encoding='utf-8')
        pin_path = self.source / '.github/windows-native-kit/tool-pins.json'; pin_path.parent.mkdir(parents=True)
        pins = [{'name': name, 'version': '1', 'url': 'https://example.invalid/official', 'sha256': 'c' * 64}
                for name in ('cmake', 'python', '7z-extra', 'ifw')]
        pin_path.write_text(json.dumps({'artifacts': pins}), encoding='utf-8')
        group = {'name': 'synthetic', 'status': 'approved', 'reason': 'synthetic test only',
                 'evidence': ['s/fixture.txt'], 'cases': ['Fixture.works']}
        suites = [{'id': 'main', 'groups': [group]}]
        reviewed_path = pin_path.parent / 'ci-closure-policy.json'
        reviewed_path.write_text('{}', encoding='utf-8')
        source_files = sorted('s/' + x.relative_to(self.source).as_posix() for x in self.source.rglob('*')
                              if x.is_file() and '.git' not in x.parts)
        reviewed_path.write_text(json.dumps({'schema': 2, 'verifier_sha256': planner.digest(verifier)}), encoding='utf-8')
        self.git('add', '.')
        self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'synthetic policy')
        self.sha, self.tree = self.git('rev-parse', 'HEAD'), self.git('rev-parse', 'HEAD^{tree}')
        self.place_identity_root()
        marker_source = self.source / 'pj_runtime/src/ActiveWidgetsMarker.cpp'
        kit = self.build / 'native-kit'; kit.mkdir()
        graph = self.build / 'conan-install-graph.json'; graph.write_text('{}', encoding='utf-8')
        doc = self.listing(executable='t/python/python.exe')
        (kit / 'discovery.json').write_text(json.dumps(doc), encoding='utf-8')
        (kit / 'run-plan.json').write_text('{}', encoding='utf-8')
        for name in ('python/python.exe', 'python/python3.dll', 'python/python312.dll', 'cmake/bin/ctest.exe'):
            path = self.root / 't' / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b'synthetic PE')
        for name in ('b/ci-temp-probe/RelWithDebInfo/pj_native_ci_temp_probe.exe',
                     'i/temp-probe/RelWithDebInfo/pj_native_temp_probe.exe',
                     'b/pj_app/RelWithDebInfo/pj_app_gui_tests.exe'):
            path = self.root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b'synthetic PE')
        for relative in planner.PRODUCER_EVIDENCE_FILES:
            path = self.build / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b'synthetic producer evidence')
        mutation = {'schema': 1, 'complete': True, 'scope': 'disposable-windows-ci-only',
                    'source_sha': self.sha, 'source_tree': self.tree,
                    'case': 'MainWindowCustomWidgetTest.WindowCloseClearsAnOrphanRecordInsideTheSurvivingFixtureRoot',
                    'original_source_sha256': planner.digest(marker_source), 'baseline_runner_sha256': '3' * 64,
                    'mutated_source_sha256': '1' * 64,
                    'restored_runner_sha256': planner.digest(self.build / 'pj_app/RelWithDebInfo/pj_app_gui_tests.exe'),
                    'mutant_runner_sha256': '2' * 64,
                    'qt_preflight_sha256': planner.digest(self.build / 'native-kit/ci-temp-probe-evidence/before-marker-mutation.stdout.bin')}
        (self.build / 'native-kit/marker-mutation-evidence/receipt.json').write_text(json.dumps(mutation), encoding='utf-8')
        origins = {'project': {'root': str(self.source), 'description': 'Synthetic project', 'revision': self.sha,
                               'license_files': ['s/LICENSE']},
                   'main-build': {'root': str(self.build), 'description': 'Synthetic build', 'revision': self.sha,
                                  'license_files': ['s/LICENSE']},
                   'i18n-build': {'root': str(self.i18n), 'description': 'Synthetic language build', 'revision': self.sha,
                                  'license_files': ['s/LICENSE']},
                   'runtime': {'root': str(self.root / 't'), 'description': 'Synthetic runtime', 'revision': 'c' * 64,
                               'license_files': ['s/LICENSE']}}
        entries = []
        for origin, prefix, paths in [('project', 's', source_files),
                                      ('main-build', 'b', ['b/conan-install-graph.json', 'b/native-kit/discovery.json',
                                                           'b/native-kit/run-plan.json',
                                                           'b/ci-temp-probe/RelWithDebInfo/pj_native_ci_temp_probe.exe',
                                                           'b/pj_app/RelWithDebInfo/pj_app_gui_tests.exe'] +
                                       ['b/' + x for x in planner.PRODUCER_EVIDENCE_FILES]),
                                      ('i18n-build', 'i', ['i/temp-probe/RelWithDebInfo/pj_native_temp_probe.exe']),
                                      ('runtime', 't', ['t/python/python.exe', 't/python/python3.dll',
                                                        't/python/python312.dll', 't/cmake/bin/ctest.exe'])]:
            for dest in paths:
                relative = dest[len(prefix) + 1:]
                entries.append({'origin': origin, 'source': relative, 'destination': dest,
                                'sha256': planner.digest(Path(origins[origin]['root']) / relative)})
        plan = {'origins': origins, 'directories': ['r'], 'files': entries}
        report = {'source_sha': self.sha, 'source_tree': self.tree, 'logical_root': self.logical,
                  'configuration': 'RelWithDebInfo', 'blockers': [], 'coverage': []}
        plan_path = self.base / 'candidate.json'; plan_path.write_text(json.dumps(plan), encoding='utf-8')
        report_path = self.base / 'report.json'; report_path.write_text(json.dumps(report), encoding='utf-8')
        suite = {'id': 'main', 'kind': 'ctest', 'tree': 'b', 'discovery': 'b/native-kit/discovery.json',
                 'full_discovery': 'b/native-kit/discovery.json'}
        ci = planner.load_module('synthetic_ci_contract', 'run_native_ci_verification.py')
        launcher = planner.load_module('synthetic_launcher_contract', 'run_native_test_bundle.py')
        state = {'mode': ''}
        expected_policy = {'schema': 1, 'scope': 'github-hosted-windows-ci', 'source_sha': self.sha,
                           'source_tree': self.tree, 'configuration': 'RelWithDebInfo', 'suites': suites}
        def expected_inventory():
            return {'schema': 1, 'basis': 'source-analysis', 'source_sha': self.sha, 'source_tree': self.tree,
                    'configuration': 'RelWithDebInfo', 'scopes': [{'suite': 'main', 'cases': ['Fixture.works'],
                    'runner': {'path': 't/python/python.exe', 'sha256': planner.digest(self.root / 't/python/python.exe')},
                    'source_files': [{'path': 's/fixture.txt', 'sha256': planner.digest(self.source / 'fixture.txt')}],
                    'dynamic_files': [], 'subprocesses': [], 'reason': 'synthetic source analysis'}]}
        class FakeClosure:
            class ClosureError(Exception): pass
            @staticmethod
            def source_paths_match(tracked, destinations, generated=()):
                if sorted(['s/' + x for x in tracked] + list(generated)) != sorted(x for x in destinations if x.startswith('s/')):
                    raise FakeClosure.ClosureError('synthetic tracked paths differ')
            @staticmethod
            def derive_partition(*args): return expected_policy
            @staticmethod
            def derive_dynamic_inventory(*args): return expected_inventory()
            @staticmethod
            def verify_dynamic_inventory(actual, expected):
                if actual != expected: raise FakeClosure.ClosureError('synthetic inventory differs')
            @staticmethod
            def derive_verified_python_pair(root, files, source_sha, source_tree, logical_root):
                return {'driver': 't/python/python312.dll', 'conan': 'c/runtime/python312.dll'}
            @staticmethod
            def derive_pe_processes(suites, prepared, docs, inventory, files, logical_root):
                return [{'executable': 't/python/python.exe', 'working_directory': '.', 'modules': []}]
            @staticmethod
            def windows_system_resolver(name, allow_not_found=False):
                return {'requested': name, 'source': 'synthetic'}
            @staticmethod
            def resolve_candidate_pe_imports(plan, processes, dirs, system_root, resolver, python_pair=None):
                if dirs != ['q/qt/bin', 't/cmake/bin', 'c/runtime'] or system_root != r'C:\Windows':
                    raise FakeClosure.ClosureError('wrong process PATH or system root')
                if python_pair != {'driver': 't/python/python312.dll', 'conan': 'c/runtime/python312.dll'}:
                    raise FakeClosure.ClosureError('wrong verified Python pair')
                if resolver('KERNEL32.dll') != {'requested': 'KERNEL32.dll', 'source': 'synthetic'}:
                    raise FakeClosure.ClosureError('wrong resolver')
                return {'schema': 1, 'scope': 'synthetic PE', 'plan': plan, 'system_imports': [], 'legacy_checks': []}
        def synthetic_verifier(verifier_path, root, source, candidate, candidate_report, reviewed, output):
            kinds = ('qt-origin-extraction', 'conan-origin-license', 'host-system-resolution',
                     'dynamic-dependency-inventory', 'case-source-review', 'private-registry-lifecycle', 'ci-temp-safety',
                     'linked-marker-mutation', 'bootstrap-adversarial')
            evidence = []
            for index, kind in enumerate(kinds):
                file = output / (str(index) + '.json')
                if kind == 'dynamic-dependency-inventory':
                    inventory = expected_inventory()
                    if state['mode'] == 'wrong-case': inventory['scopes'][0]['cases'] = ['Different.case']
                    file.write_text(json.dumps(inventory), encoding='utf-8')
                elif kind == 'host-system-resolution':
                    host = {'schema': 1, 'scope': 'synthetic PE', 'system_imports': [], 'legacy_checks': []}
                    if state['mode'] == 'wrong-host': host['scope'] = 'fabricated host'
                    file.write_text(json.dumps(host), encoding='utf-8')
                else:
                    file.write_bytes(b'synthetic evidence: no actual Windows execution')
                item = {'path': file.relative_to(self.root).as_posix(), 'sha256': planner.digest(file), 'kind': kind}
                if kind == 'case-source-review':
                    item['cases'] = [{'suite': 'main', 'case': 'Fixture.works'}]
                evidence.append(item)
            for name, source_input in (('candidate-plan.json', candidate), ('candidate-report.json', candidate_report)):
                file = output / name; file.write_bytes(source_input.read_bytes())
                evidence.append({'path': file.relative_to(self.root).as_posix(), 'sha256': planner.digest(file),
                                 'kind': 'candidate-input'})
            (output / 'ci-policy.json').write_text(json.dumps(expected_policy), encoding='utf-8')
            provenance = audit_fixture.provenance()
            provenance.update(source_sha=self.sha, source_tree=self.tree,
                              conan_lock_sha256=planner.digest(source / 'conan.lock'), conan_graph_sha256=planner.digest(graph))
            (output / 'provenance.json').write_text(json.dumps(provenance), encoding='utf-8')
            receipt = {'schema': 1, 'source_sha': self.sha, 'source_tree': self.tree, 'configuration': 'RelWithDebInfo',
                       'candidate_plan_sha256': planner.digest(candidate), 'candidate_report_sha256': planner.digest(candidate_report),
                       'reviewed_policy_sha256': planner.digest(reviewed), 'verifier_sha256': planner.digest(verifier_path),
                       'runtime_dirs': ['q/qt/bin', 't/cmake/bin', 'c/runtime'], 'evidence': evidence}
            (output / 'receipt.json').write_text(json.dumps(receipt), encoding='utf-8')
            if state['mode'] == 'changed-inventory':
                (output / '3.json').write_bytes(b'changed after receipt')
            return 0
        def fake_archive(stage, logical, output, manifest_sha):
            Path(output).write_bytes(b'synthetic archive')
            return {'archive_sha256': planner.digest(output), 'manifest_sha256': manifest_sha, 'archive_bytes': 17,
                    'expanded_bytes': 42, 'files': 1, 'directories': 1}
        def modules(name, filename):
            return ci if filename == 'run_native_ci_verification.py' else launcher
        with mock.patch.object(planner, 'run_reviewed_verifier', side_effect=synthetic_verifier), \
             mock.patch.object(planner, 'load_reviewed_verifier', return_value=FakeClosure), \
             mock.patch.object(planner, 'load_module', side_effect=modules), \
             mock.patch.object(launcher, 'validate_plan', return_value=({'qt': 'q/qt', 'python': 't/python/python.exe',
                                                                          'ctest': 't/cmake/bin/ctest.exe'}, ['c/runtime'], [suite])), \
             mock.patch.object(planner, 'archive_captured_stage', side_effect=fake_archive), \
             mock.patch.object(planner.shutil, 'disk_usage', return_value=types.SimpleNamespace(free=64 * 1024**3)), \
             mock.patch.dict(os.environ, {'GITHUB_WORKFLOW_SHA': 'd' * 40, 'SystemRoot': r'C:\Windows'}):
            for mode, error in (('changed-inventory', 'empty or changed'),
                                ('wrong-case', 'differs from the source-reviewed runtime rules'),
                                ('wrong-host', 'System32 imports differ')):
                state['mode'] = mode
                with self.subTest(mode=mode), self.assertRaisesRegex(planner.PlanError, error):
                    planner.package_candidate(self.root, self.logical, self.sha, self.tree, plan_path, report_path,
                                              self.base / 'stage', self.base / 'native-kit.zip')
                self.assertFalse((self.base / 'stage').exists())
                self.assertFalse((self.base / 'native-kit.zip').exists())
                self.assertTrue((kit / 'closure-evidence/receipt.json').is_file())
                shutil.rmtree(kit / 'closure-evidence')
            state['mode'] = ''
            result = planner.package_candidate(self.root, self.logical, self.sha, self.tree, plan_path, report_path,
                                               self.base / 'stage', self.base / 'native-kit.zip')
        self.assertEqual(result['status'], 'staged-awaiting-independent-ci')
        self.assertTrue((self.base / 'stage/_bundle/manifest.json').is_file())
        self.assertTrue((self.base / 'stage/b/native-kit/closure-evidence/receipt.json').is_file())

    def test_missing_command_and_outside_root_are_reported_per_case(self):
        candidate = self.candidate()
        listing = self.listing(executable='b/RelWithDebInfo/missing.exe')
        listing['tests'][0]['command'].append(r'C:\Windows\System32\cmd.exe')
        candidate.add_discovery('main', listing)
        by_code = {x['code']: x for x in candidate.blockers}
        self.assertEqual(by_code['missing-referenced-file']['case'], 'Fixture.works')
        self.assertEqual(by_code['missing-referenced-file']['detail'], 'b/RelWithDebInfo/missing.exe')
        self.assertEqual(by_code['outside-root']['case'], 'Fixture.works')

    def test_qttest_output_exception_is_exact_per_tree_and_case(self):
        for suite, tree in (('main', 'b'), ('i18n', 'i')):
            runner = self.root / tree / 'RelWithDebInfo/pj_bundled_translations_test.exe'
            runner.parent.mkdir(parents=True, exist_ok=True); runner.write_bytes(b'synthetic QtTest')
            expected = self.logical + '\\' + tree + r'\Testing\Temporary\bundled-translations.txt'
            doc = self.listing(name='pj_bundled_translations_test')
            doc['tests'][0]['command'] = [self.logical + '\\' + tree + r'\RelWithDebInfo\pj_bundled_translations_test.exe',
                                           '-o', '-,txt', '-o', expected.replace('\\', '/') + ',txt']
            candidate = self.candidate(); candidate.add_discovery(suite, doc)
            self.assertEqual(candidate.allowed_outputs[suite], {'pj_bundled_translations_test': [expected]})
            self.assertFalse(any(x['case'] == 'pj_bundled_translations_test' and x['code'] == 'missing-referenced-file'
                                 for x in candidate.blockers))
            for bad in (expected + ',xml', expected.replace('bundled-translations.txt', 'other.txt') + ',txt',
                        self.logical + r'\outside\bundled-translations.txt,txt'):
                bad_doc = json.loads(json.dumps(doc)); bad_doc['tests'][0]['command'][-1] = bad
                with self.subTest(suite=suite, bad=bad), self.assertRaises(planner.PlanError):
                    self.candidate().add_discovery(suite, bad_doc)

    def test_same_root_declared_tools_become_individual_file_entries(self):
        origin = self.root / 't/python'; origin.mkdir(parents=True)
        (origin / 'LICENSE.txt').write_bytes(b'python license')
        (origin / 'python.exe').write_bytes(b'python executable')
        declaration = {'schema': 1, 'origins': {'driver-python': {
            'root': 't/python', 'description': 'Pinned Python distribution', 'revision': 'a' * 64,
            'license_files': ['t/python/LICENSE.txt']}},
            'files': [{'origin': 'driver-python', 'source': 'LICENSE.txt'},
                      {'origin': 'driver-python', 'source': 'python.exe'}]}
        candidate = self.candidate(declaration)
        plan, _ = candidate.finish({})
        python = next(x for x in plan['files'] if x['destination'] == 't/python/python.exe')
        self.assertEqual(python['source'], 'python.exe')
        self.assertEqual(python['origin'], 'driver-python')
        path = self.base / 'plan.json'; path.write_text(json.dumps(plan), encoding='utf-8')
        planner.audit.stage_allowlisted(path, self.base / 'stage', self.logical)

    def seed_verified_tools(self):
        downloads = self.root / 'd'; downloads.mkdir()
        python_files = {'python.exe': b'python', 'python3.dll': b'python3', 'python312.dll': b'python312',
                        'python312.zip': b'stdlib', 'python312._pth': b'original paths',
                        'LICENSE.txt': b'python license', '_socket.pyd': b'socket extension',
                        'libcrypto-3.dll': b'crypto', 'libssl-3.dll': b'ssl', 'libffi-8.dll': b'ffi',
                        'sqlite3.dll': b'sqlite', 'vcruntime140.dll': b'vc runtime'}
        cmake_files = {'bin/cmake.exe': b'cmake', 'bin/ctest.exe': b'ctest',
                       'doc/cmake-3.31/Copyright.txt': b'cmake license',
                       'share/cmake-3.31/Modules/GoogleTestAddTests.cmake': b'ctest script'}
        for filename, prefix, values in [('python.zip', '', python_files),
                                         ('cmake.zip', 'cmake-3.31.10-windows-x86_64/', cmake_files)]:
            with zipfile.ZipFile(downloads / filename, 'w') as archive:
                for name, data in values.items(): archive.writestr(prefix + name, data)
        for name, content in [('bootstrap.exe', b'bootstrap'), ('extra.7z', b'extra'), ('ifw.7z', b'ifw')]:
            (downloads / name).write_bytes(content)
        pins = []
        for name, filename in [('cmake', 'cmake.zip'), ('python', 'python.zip'), ('7zr-bootstrap', 'bootstrap.exe'),
                               ('7z-extra', 'extra.7z'), ('ifw', 'ifw.7z')]:
            content = (downloads / filename).read_bytes()
            pins.append({'name': name, 'version': '1.0', 'file': filename,
                         'url': 'https://example.invalid/' + filename, 'source': 'https://example.invalid/source',
                         'sha256': hashlib.sha256(content).hexdigest(), 'bytes': len(content)})
        manifest = self.source / '.github/windows-native-kit/tool-pins.json'; manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({'schema': 1, 'artifacts': pins}), encoding='utf-8')
        self.git('add', '.github/windows-native-kit/tool-pins.json')
        self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'tool pins')
        self.sha, self.tree = self.git('rev-parse', 'HEAD'), self.git('rev-parse', 'HEAD^{tree}')
        self.place_identity_root()
        for name, values in [('python', python_files), ('cmake', cmake_files)]:
            for path, data in values.items():
                target = self.root / 't' / name / path; target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data if path != 'python312._pth' else b'original paths\nvalidated extra paths')
        for path, data in [('7z/7za.exe', b'7za'), ('7z/License.txt', b'7z license'),
                           ('ifw/ifw.7z', b'ifw'), ('ifw/notices/LICENSE', b'ifw license')]:
            target = self.root / 't' / path; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
        def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
        runtime = {'7za_sha256': sha(self.root / 't/7z/7za.exe'), 'ifw_sha256': sha(self.root / 't/ifw/ifw.7z'),
                   'python_pth_sha256': sha(self.root / 't/python/python312._pth')}
        records = [{key: pin[key] for key in ('name', 'version', 'url', 'sha256', 'source', 'bytes')} for pin in pins]
        (self.root / 't/tool-provenance.json').write_text(json.dumps({'schema': 1, 'distributions': records,
                                                                     'runtime_files': runtime}), encoding='utf-8')

    def test_official_tool_inputs_are_enumerated_with_archive_and_license_identity(self):
        self.seed_verified_tools()
        candidate = self.candidate()
        plan, _ = candidate.finish({})
        files = {item['destination'] for item in plan['files']}
        self.assertTrue({'t/python/python.exe', 't/python/_socket.pyd', 't/python/LICENSE.txt',
                         't/python/libcrypto-3.dll', 't/python/libssl-3.dll', 't/python/libffi-8.dll',
                         't/python/sqlite3.dll', 't/python/vcruntime140.dll', 't/cmake/bin/ctest.exe', 't/cmake/share/cmake-3.31/Modules/GoogleTestAddTests.cmake',
                         't/7z/7za.exe', 't/ifw/ifw.7z', 't/ifw/notices/LICENSE',
                         't/tool-provenance.json'} <= files)
        self.assertNotIn('d/python.zip', files)
        path = self.base / 'plan.json'; path.write_text(json.dumps(plan), encoding='utf-8')
        planner.audit.stage_allowlisted(path, self.base / 'stage', self.logical)

    def test_tampered_extracted_tool_or_distribution_fails_closed(self):
        self.seed_verified_tools()
        for path in (self.root / 't/cmake/bin/cmake.exe', self.root / 't/python/python312._pth',
                     self.root / 't/python/libssl-3.dll', self.root / 'd/ifw.7z'):
            original = path.read_bytes(); path.write_bytes(original + b'tampered')
            with self.subTest(path=path), self.assertRaises(planner.PlanError):
                self.candidate()
            path.write_bytes(original)

    def test_embedded_python_rejects_missing_extra_and_case_colliding_dlls(self):
        self.seed_verified_tools()
        sqlite = self.root / 't/python/sqlite3.dll'; original = sqlite.read_bytes(); sqlite.unlink()
        with self.assertRaisesRegex(planner.PlanError, 'runtime is missing'):
            self.candidate()
        sqlite.write_bytes(original)
        extra = self.root / 't/python/not-in-official-zip.dll'; extra.write_bytes(b'unreviewed')
        with self.assertRaisesRegex(planner.PlanError, 'unexpected or case-colliding'):
            self.candidate()
        extra.unlink()
        collision = self.root / 't/python/SQLITE3.DLL'
        if not collision.exists():
            collision.write_bytes(b'different case spelling')
            with self.assertRaisesRegex(planner.PlanError, 'unexpected or case-colliding'):
                self.candidate()

    def test_embedded_python_zip_refuses_missing_or_colliding_members(self):
        archive = self.base / 'malformed-python.zip'
        required = ['python.exe', 'python3.dll', 'python312.dll', 'python312.zip', 'python312._pth', 'LICENSE.txt']
        with zipfile.ZipFile(archive, 'w') as output:
            for name in required[:-1]: output.writestr(name, b'x')
        with self.assertRaisesRegex(planner.PlanError, 'lacks required'):
            planner.embedded_python_archive_members(archive, self.logical)
        with zipfile.ZipFile(archive, 'w') as output:
            for name in required: output.writestr(name, b'x')
            output.writestr('sqlite3.dll', b'one'); output.writestr('SQLITE3.DLL', b'two')
        with self.assertRaisesRegex(planner.PlanError, 'case-colliding'):
            planner.embedded_python_archive_members(archive, self.logical)

    def seed_conan_cpython(self):
        package = self.root / 'c/p/cpython-test/p'
        values = {'licenses/LICENSE': b'Python license', 'bin/python312.dll': b'embedded python',
                  'bin/DLLs/_socket.pyd': b'embedded socket', 'bin/Lib/json/__init__.py': b'json module',
                  'bin/Lib/test/ignored.py': b'test-only data'}
        for relative, data in values.items():
            path = package / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
        lines = ['123456'] + [name + ': ' + hashlib.md5(data, usedforsecurity=False).hexdigest()
                              for name, data in sorted(values.items())]
        (package / 'conanmanifest.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
        logical_package = self.logical + r'\c\p\cpython-test\p'
        node = {'context': 'host', 'package_folder': logical_package, 'ref': 'cpython/3.12.7#' + 'c' * 32,
                'package_id': 'a' * 40, 'prev': 'b' * 32}
        (self.build / 'conan-install-graph.json').write_text(json.dumps({'graph': {'nodes': {'1': node}}}), encoding='utf-8')
        for name in ('pj_ffmpeg_bin_dirs.txt', 'pj_python_bin_dirs.txt'):
            (self.build / name).write_text(logical_package + '\\bin\n', encoding='utf-8')
        (self.build / 'native-kit').mkdir()
        return package

    def test_conan_runtime_files_licenses_and_package_revision_are_bound(self):
        self.seed_conan_cpython()
        candidate = self.candidate()
        plan, report = candidate.finish({})
        files = {item['destination'] for item in plan['files']}
        for name in ('conanmanifest.txt', 'licenses/LICENSE', 'bin/python312.dll',
                     'bin/DLLs/_socket.pyd', 'bin/Lib/json/__init__.py'):
            self.assertIn('c/p/cpython-test/p/' + name, files)
        self.assertNotIn('c/p/cpython-test/p/bin/Lib/test/ignored.py', files)
        self.assertIn('b/native-kit/conan-runtime-identity.json', files)
        identity = json.loads((self.build / 'native-kit/conan-runtime-identity.json').read_text(encoding='utf-8'))
        self.assertEqual(identity['packages'][0]['package_id'], 'a' * 40)
        self.assertEqual(identity['packages'][0]['prev'], 'b' * 32)
        self.assertIn('dynamic-dependencies-unreviewed', {item['code'] for item in report['blockers']})
        path = self.base / 'plan.json'; path.write_text(json.dumps(plan), encoding='utf-8')
        planner.audit.stage_allowlisted(path, self.base / 'stage', self.logical)

    def test_locked_sdk_stages_only_reviewed_helper_sources_with_package_manifest(self):
        import types
        contract = planner.load_module('test_sdk_fixture_contract', 'verify_native_ci_closure.py')
        refs = ['cpython/3.12.7#' + 'c' * 32, 'plotjuggler_sdk/0.39.0#' + 'd' * 32]
        lock = self.source / 'conan.lock'
        lock.write_text(json.dumps({'requires': refs}), encoding='utf-8')
        self.git('add', 'conan.lock')
        self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'SDK lock')
        self.sha, self.tree = self.git('rev-parse', 'HEAD'), self.git('rev-parse', 'HEAD^{tree}')
        self.place_identity_root()
        self.seed_conan_cpython()
        package = self.root / 'c/p/sdk-test/p'
        data = {name: ('synthetic fixture ' + name).encode() for name in contract.SDK_FIXTURE_FILES}
        data.update({'licenses/LICENSE': b'SDK license', 'lib/unselected.lib': b'unselected static bytes'})
        for relative, value in data.items():
            path = package / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(value)
        (package / 'conanmanifest.txt').write_text('123456\n' + ''.join(
            name + ': ' + hashlib.md5(value, usedforsecurity=False).hexdigest() + '\n'
            for name, value in sorted(data.items())), encoding='utf-8')
        graph_path = self.build / 'conan-install-graph.json'
        graph = json.loads(graph_path.read_text(encoding='utf-8'))
        graph['graph']['nodes']['2'] = {'context': 'host', 'package_folder': self.logical + r'\c\p\sdk-test\p',
                                         'ref': refs[1], 'rrev': 'd' * 32,
                                         'package_id': 'e' * 40, 'prev': 'f' * 32}
        graph_path.write_text(json.dumps(graph), encoding='utf-8')
        fake = types.SimpleNamespace(SDK_FIXTURE_FILES={name: hashlib.sha256(data[name]).hexdigest()
                                                        for name in contract.SDK_FIXTURE_FILES},
                                     CODEMODEL_RULES=contract.CODEMODEL_RULES,
                                     CODEMODEL_PLUGIN_SOURCES=contract.CODEMODEL_PLUGIN_SOURCES)
        load = planner.load_module
        def modules(name, filename):
            return fake if filename == 'verify_native_ci_closure.py' else load(name, filename)
        with mock.patch.object(planner, 'load_module', side_effect=modules):
            candidate = self.candidate()
            selected = {item['destination'] for item in candidate.files.values()}
            self.assertTrue({'c/p/sdk-test/p/' + name for name in fake.SDK_FIXTURE_FILES} <= selected)
            self.assertIn('c/p/sdk-test/p/conanmanifest.txt', selected)
            self.assertIn('c/p/sdk-test/p/licenses/LICENSE', selected)
            self.assertIn('c/p/sdk-test/p/licenses/LICENSE', candidate.origins['main-build']['license_files'])
            self.assertNotIn('c/p/sdk-test/p/lib/unselected.lib', selected)
            identity = self.build / 'native-kit/conan-runtime-identity.json'; identity.unlink()
            manifest = package / 'conanmanifest.txt'; raw_manifest = manifest.read_text(encoding='utf-8')
            fixture = next(iter(fake.SDK_FIXTURE_FILES))
            old_md5 = hashlib.md5(data[fixture], usedforsecurity=False).hexdigest()
            manifest.write_text(raw_manifest.replace(fixture + ': ' + old_md5, fixture + ': ' + '0' * 32), encoding='utf-8')
            with self.assertRaisesRegex(planner.PlanError, 'differs from its manifest'):
                self.candidate()
            manifest.write_text(raw_manifest, encoding='utf-8')
            changed = package / fixture; changed.write_bytes(b'changed')
            with self.assertRaisesRegex(planner.PlanError, 'SDK fixture differs'):
                self.candidate()

    def test_conan_package_root_and_bin_are_both_resolved(self):
        self.seed_conan_cpython()
        logical_package = self.logical + r'\c\p\cpython-test\p'
        (self.build / 'pj_python_bin_dirs.txt').write_text(logical_package + '\n' + logical_package + r'\bin' + '\n', encoding='utf-8')
        candidate = self.candidate()
        self.assertEqual(set(candidate.runtime_dirs), {'c/p/cpython-test/p', 'c/p/cpython-test/p/bin'})
        self.assertNotIn('unresolved-conan-runtime-directory', {item['code'] for item in candidate.blockers})
        self.assertIn('c/p/cpython-test/p/bin/python312.dll', {item['destination'] for item in candidate.files.values()})

    def test_conan_runtime_ambiguous_graph_and_external_paths_fail_closed(self):
        self.seed_conan_cpython()
        graph_path = self.build / 'conan-install-graph.json'
        graph = json.loads(graph_path.read_text(encoding='utf-8'))
        graph['graph']['nodes']['2'] = dict(graph['graph']['nodes']['1'], ref='other/1.0#' + 'd' * 32)
        graph_path.write_text(json.dumps(graph), encoding='utf-8')
        candidate = self.candidate()
        self.assertIn('unresolved-conan-runtime-directory', {item['code'] for item in candidate.blockers})
        (self.build / 'pj_python_bin_dirs.txt').write_text('C:\\outside\\python\n', encoding='utf-8')
        with self.assertRaisesRegex(planner.PlanError, 'outside|leaves'):
            self.candidate()

    def test_all_host_package_notices_and_recipe_revisions_are_bound_without_static_libs(self):
        self.seed_conan_cpython()
        static = self.root / 'c/p/static-package/p'
        static_files = {'licenses/LICENSE': b'synthetic dependency license', 'lib/dependency.lib': b'static bytes'}
        for relative, data in static_files.items():
            target = static / relative; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
        (static / 'conanmanifest.txt').write_text('123456\n' + ''.join(name + ': ' + hashlib.md5(data, usedforsecurity=False).hexdigest() + '\n'
            for name, data in sorted(static_files.items())), encoding='utf-8')
        refs = ['cpython/3.12.7#' + 'c' * 32, 'dependency/1.0#' + 'd' * 32]
        (self.source / 'conan.lock').write_text(json.dumps({'requires': [refs[0] + '%123.0', refs[1]]}), encoding='utf-8')
        self.git('add', 'conan.lock')
        self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'synthetic Conan lock')
        self.sha, self.tree = self.git('rev-parse', 'HEAD'), self.git('rev-parse', 'HEAD^{tree}')
        self.place_identity_root()
        python_root = self.logical + r'\c\p\cpython-test\p'
        node1 = {'context': 'host', 'package_folder': python_root, 'ref': refs[0], 'rrev': 'c' * 32,
                 'package_id': 'a' * 40, 'prev': 'b' * 32}
        node2 = {'context': 'host', 'package_folder': self.logical + r'\c\p\static-package\p',
                 'ref': refs[1], 'rrev': 'd' * 32, 'package_id': 'e' * 40, 'prev': 'f' * 32}
        graph = {'graph': {'nodes': {'1': node1, '2': node2}}}
        graph_path = self.build / 'conan-install-graph.json'; graph_path.write_text(json.dumps(graph), encoding='utf-8')
        for name in ('pj_ffmpeg_bin_dirs.txt', 'pj_python_bin_dirs.txt'):
            (self.build / name).write_text(python_root + r'\bin' + '\n', encoding='utf-8')
        candidate = self.candidate()
        paths = {x['destination'] for x in candidate.files.values()}
        self.assertIn('b/conan-install-graph.json', paths)
        self.assertIn('c/p/static-package/p/conanmanifest.txt', paths)
        self.assertIn('c/p/static-package/p/licenses/LICENSE', paths)
        self.assertNotIn('c/p/static-package/p/lib/dependency.lib', paths)
        self.assertFalse({'conan-host-recipe-not-locked', 'missing-conan-lock'} & {x['code'] for x in candidate.blockers})
        identity = json.loads((self.build / 'native-kit/conan-runtime-identity.json').read_text(encoding='utf-8'))
        self.assertEqual({x['rrev'] for x in identity['packages']}, {'c' * 32, 'd' * 32})
        self.assertEqual(next(x for x in identity['packages'] if x['ref'] == refs[1])['runtime_dirs'], [])
        (self.build / 'native-kit/conan-runtime-identity.json').unlink()
        graph['graph']['nodes']['2']['rrev'] = '0' * 32
        graph_path.write_text(json.dumps(graph), encoding='utf-8')
        self.assertIn('incomplete-conan-package-identity', {x['code'] for x in self.candidate().blockers})

    def test_conan_files_must_match_the_installed_package_manifest(self):
        package = self.seed_conan_cpython()
        (package / 'bin/python312.dll').write_bytes(b'changed')
        with self.assertRaisesRegex(planner.PlanError, 'differs from its manifest'):
            self.candidate()

    def test_conan_manifest_may_list_unstaged_libs_but_rejects_unsafe_names(self):
        self.assertEqual(planner.safe_conan_manifest_name('lib/dependency.lib'), 'lib/dependency.lib')
        for value in ('../outside.lib', '/absolute.lib', 'lib/file.dll:stream', 'lib/../bad', 'lib/NUL.txt'):
            with self.subTest(value=value), self.assertRaises(planner.PlanError):
                planner.safe_conan_manifest_name(value)

    def test_conan_package_with_missing_revision_is_reported_not_accepted(self):
        self.seed_conan_cpython()
        graph_path = self.build / 'conan-install-graph.json'
        graph = json.loads(graph_path.read_text(encoding='utf-8')); graph['graph']['nodes']['1']['prev'] = None
        graph_path.write_text(json.dumps(graph), encoding='utf-8')
        candidate = self.candidate()
        plan, report = candidate.finish({})
        self.assertIn('incomplete-conan-package-identity', {item['code'] for item in report['blockers']})
        self.assertFalse(any(item['destination'].startswith('c/p/cpython-test/') for item in plan['files']))

    def seed_test_inputs(self):
        def sha(value): return hashlib.sha256(value).hexdigest()
        font, font_license = b'synthetic font', b'synthetic font license'
        source_files = {
            'packaging/localization/prepare_payload.py':
                f"FONT_SHA = '{sha(font)}'\nFONT_LICENSE_SHA = '{sha(font_license)}'\n".encode(),
            'packaging/localization/plugin-patches/source-lock.json': json.dumps({'plugins': [{
                'id': 'csv-loader', 'version': '1.0.7', 'commit': 'd' * 40, 'sdk': '0.34.1',
                'patch_sha256': 'e' * 64}]}).encode(),
            'docs/localization/upstream-baseline.json': json.dumps({'ardupilot_plugin': {
                'commit': 'f' * 40, 'version': '1.2'}}).encode(),
            'packaging/localization/registry-lock.json': json.dumps({'extensions': [{
                'id': 'toolbox-fft', 'platforms': {'windows-x86_64': {
                    'url': 'https://example.invalid/fft.zip', 'checksum': 'sha256:' + 'a' * 64}}}]}).encode(),
            '3rdparty/plotjuggler-apbin-plugins/sdk4/LICENSE': b'apbin license',
            '3rdparty/plotjuggler-apbin-plugins/sdk4/COPYING.GPL3': b'GPL',
            '3rdparty/plotjuggler-apbin-plugins/sdk4/LICENSE.APACHE2': b'Apache',
        }
        for relative, data in source_files.items():
            path = self.source / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
        self.git('add', *source_files)
        self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'locked inputs')
        self.sha, self.tree = self.git('rev-parse', 'HEAD'), self.git('rev-parse', 'HEAD^{tree}')
        self.place_identity_root()
        for path, data in [('b/ci-fonts/NotoSansCJKsc-Regular.otf', font), ('b/ci-fonts/LICENSE', font_license),
                           ('b/csv-prefix/lib/plotjuggler/plugins/csv-loader/csv.dll', b'csv plugin'),
                           ('b/csv-prefix/share/licenses/localized-plugins/csv-loader/LICENSE', b'csv license'),
                           ('b/feedback-plugins/ardupilot-dataflash/apbin.dll', b'apbin'),
                           ('b/feedback-plugins/ardupilot-dataflash/manifest.json', b'{}'),
                           ('b/feedback-plugins/toolbox-fft/fft.dll', b'fft')]:
            target = self.root / path; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
        lock = source_files['packaging/localization/plugin-patches/source-lock.json']
        prefix = self.root / 'b/csv-prefix'
        lock_copy = prefix / 'share/plotjuggler4/localized-plugin-sources.json'
        lock_copy.parent.mkdir(parents=True, exist_ok=True); lock_copy.write_bytes(lock)
        csv = {'id': 'csv-loader', 'version': '1.0.7', 'commit': 'd' * 40, 'sdk': '0.34.1', 'patch_sha256': 'e' * 64,
               'files': [{'path': 'lib/plotjuggler/plugins/csv-loader/csv.dll', 'sha256': sha(b'csv plugin')}],
               'license_files': [{'path': 'share/licenses/localized-plugins/csv-loader/LICENSE', 'sha256': sha(b'csv license')}]}
        (prefix / 'share/plotjuggler4/release.json').write_text(json.dumps({'localized_plugin_rebuilds': [csv]}), encoding='utf-8')
        feedback = {'platform': 'windows-x86_64', 'apbin_source_commit': 'f' * 40, 'apbin_version': '1.2',
                    'fft_url': 'https://example.invalid/fft.zip', 'fft_archive_sha256': 'a' * 64,
                    'files': [{'path': 'ardupilot-dataflash/apbin.dll', 'sha256': sha(b'apbin')},
                              {'path': 'ardupilot-dataflash/manifest.json', 'sha256': sha(b'{}')},
                              {'path': 'toolbox-fft/fft.dll', 'sha256': sha(b'fft')}]}
        (self.build / 'feedback-plugins-identity.json').write_text(json.dumps(feedback), encoding='utf-8')

    def test_locked_csv_font_and_apbin_are_selected_but_fft_license_gap_remains(self):
        self.seed_test_inputs()
        candidate = self.candidate()
        plan, report = candidate.finish({})
        files = {item['destination'] for item in plan['files']}
        self.assertIn('b/ci-fonts/NotoSansCJKsc-Regular.otf', files)
        self.assertIn('b/csv-prefix/lib/plotjuggler/plugins/csv-loader/csv.dll', files)
        self.assertIn('b/feedback-plugins/ardupilot-dataflash/apbin.dll', files)
        self.assertNotIn('b/feedback-plugins/toolbox-fft/fft.dll', files)
        self.assertNotIn('missing-fft-license-evidence', {item['code'] for item in report['blockers']})
        self.assertTrue(any('FFT exact-source license' in item[2] for item in candidate.condition_patterns))
        path = self.base / 'plan.json'; path.write_text(json.dumps(plan), encoding='utf-8')
        planner.audit.stage_allowlisted(path, self.base / 'stage', self.logical)

    def test_tampered_csv_or_font_is_not_admitted(self):
        self.seed_test_inputs()
        for path in (self.root / 'b/ci-fonts/NotoSansCJKsc-Regular.otf',
                     self.root / 'b/csv-prefix/lib/plotjuggler/plugins/csv-loader/csv.dll',
                     self.root / 'b/feedback-plugins/ardupilot-dataflash/apbin.dll'):
            original = path.read_bytes(); path.write_bytes(original + b'bad')
            with self.subTest(path=path), self.assertRaises(planner.PlanError):
                self.candidate()
            path.write_bytes(original)

    def test_fft_source_license_and_locked_binary_are_separate_from_missing_dependency_notices(self):
        self.seed_test_inputs()
        license_path = self.build / 'feedback-fft-notices/LICENSE'; license_path.parent.mkdir(); license_path.write_bytes(b'MIT fixture')
        fft_manifest = self.build / 'feedback-plugins/toolbox-fft/manifest.json'; fft_manifest.write_bytes(b'{}')
        feedback_path = self.build / 'feedback-plugins-identity.json'
        feedback = json.loads(feedback_path.read_text(encoding='utf-8'))
        feedback['files'].append({'path': 'toolbox-fft/manifest.json', 'sha256': hashlib.sha256(b'{}').hexdigest()})
        feedback_path.write_text(json.dumps(feedback), encoding='utf-8')
        with mock.patch.object(planner, 'FFT_LICENSE_SHA256', hashlib.sha256(b'MIT fixture').hexdigest()):
            candidate = self.candidate()
            plan, report = candidate.finish({})
        files = {item['destination'] for item in plan['files']}
        self.assertIn('b/feedback-fft-notices/LICENSE', files)
        self.assertIn('b/feedback-plugins/toolbox-fft/fft.dll', files)
        self.assertTrue(any('static dependency notices' in item[2] for item in candidate.condition_patterns))
        path = self.base / 'plan.json'; path.write_text(json.dumps(plan), encoding='utf-8')
        planner.audit.stage_allowlisted(path, self.base / 'stage', self.logical)

    def test_unavailable_fft_and_media_are_case_conditions_not_global_blockers(self):
        self.seed_test_inputs()
        candidate = self.candidate()
        first = self.listing(name='PluginFeedbackMainWindow-zh_CN')
        second = self.listing(name='dual_store_test')
        first['tests'] += second['tests']
        names = candidate.add_discovery('main', first)
        _, report = candidate.finish({'main': names})
        cases = {item['case']: item for item in report['coverage'] if item['case']}
        self.assertEqual(cases['PluginFeedbackMainWindow-zh_CN']['status'], 'condition_missing')
        self.assertIn('FFT exact-source license', cases['PluginFeedbackMainWindow-zh_CN']['reason'])
        self.assertEqual(cases['dual_store_test']['status'], 'condition_missing')
        self.assertIn('potato.mcap', cases['dual_store_test']['reason'])
        self.assertNotIn('missing-fft-license-evidence', {item['code'] for item in report['blockers']})

    def test_pe_inventory_reports_each_unresolved_import_without_trusting_host_names(self):
        runner = self.build / 'RelWithDebInfo/runner.exe'
        runner.write_bytes(pe_fixture.fixture(normal=('KERNEL32.dll', 'plugin.dll'), delay=('missing.dll',)))
        plugin = self.build / 'RelWithDebInfo/plugin.dll'; plugin.write_bytes(pe_fixture.fixture(normal=(), delay=()))
        candidate = self.candidate()
        names = candidate.add_discovery('main', self.listing())
        candidate.add('main-build', 'RelWithDebInfo/plugin.dll')
        _, report = candidate.finish({'main': names})
        imports = next(item for item in report['pe_inventory'] if item['path'] == 'b/RelWithDebInfo/runner.exe')['imports']
        self.assertEqual({item['name'] for item in imports}, {'KERNEL32.dll', 'plugin.dll', 'missing.dll'})
        self.assertEqual(next(item for item in imports if item['name'] == 'plugin.dll')['candidate_files'],
                         ['b/RelWithDebInfo/plugin.dll'])
        unresolved = [item['detail'] for item in report['blockers'] if item['code'] == 'pe-import-needs-resolution']
        self.assertTrue(any('normal KERNEL32.dll' in item for item in unresolved))
        self.assertTrue(any('delay missing.dll' in item for item in unresolved))
        self.assertFalse(any('plugin.dll' in item for item in unresolved))

    def test_run_plan_is_derived_from_two_real_discoveries_and_bound_csv_bytes(self):
        self.seed_test_inputs()
        additions = {
            'versions.env': b'PJ_APP_VERSION=4.1.0+zh.1\nPJ_QT_VERSION=6.12.0\n',
            'conanfile.txt': b'[requires]\nplotjuggler_sdk/0.39.0\n',
            'packaging/localization/host_versions.py': (ROOT / 'packaging/localization/host_versions.py').read_bytes(),
            'packaging/localization/audit_file_dialog_results.py': (ROOT / 'packaging/localization/audit_file_dialog_results.py').read_bytes(),
        }
        for relative, data in additions.items():
            path = self.source / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
        self.git('add', *additions)
        self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'run plan sources')
        self.sha, self.tree = self.git('rev-parse', 'HEAD'), self.git('rev-parse', 'HEAD^{tree}')
        self.place_identity_root()
        self.seed_conan_cpython()
        (self.i18n / 'native-kit').mkdir()
        plugin_rel = 'b/csv-prefix/lib/plotjuggler/plugins/csv-loader/csv.dll'
        plugin_win = self.logical + '\\' + plugin_rel.replace('/', '\\')
        runner_rel = 'b/RelWithDebInfo/csv_runtime_file_loader_test.exe'
        runner = self.root / runner_rel
        runner.write_bytes(b'synthetic exe\0' + plugin_win.replace('\\', '/').encode() + b'\0')
        for relative, data in [('q/6.12.0/msvc2022_64/bin/Qt6Core.dll', b'qt core'),
                               ('t/cmake/bin/ctest.exe', b'ctest'),
                               ('i/temp-probe/RelWithDebInfo/pj_native_temp_probe.exe', b'probe'),
                               ('b/ci-temp-probe/RelWithDebInfo/pj_native_ci_temp_probe.exe', b'CI probe'),
                               ('b/RelWithDebInfo/pj_bundled_translations_test.exe', b'QtTest main'),
                               ('i/RelWithDebInfo/pj_bundled_translations_test.exe', b'QtTest i18n')]:
            path = self.root / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
        windows = lambda relative: self.logical + '\\' + relative.replace('/', '\\')
        identity = {'schema': 1, 'source_sha': self.sha, 'source_tree': self.tree, 'configuration': 'RelWithDebInfo',
                    'qt_version': '6.12.0', 'host_sdk': '0.39.0', 'plugin_sdk': '0.34.1'}
        for key, relative in [('runner', runner_rel), ('plugin', plugin_rel),
                              ('qt_core', 'q/6.12.0/msvc2022_64/bin/Qt6Core.dll'), ('ctest', 't/cmake/bin/ctest.exe')]:
            identity[key] = windows(relative)
            identity[key + '_sha256'] = hashlib.sha256((self.root / relative).read_bytes()).hexdigest()
        (self.build / 'native-kit/csv-prebuilt.json').write_text(json.dumps(identity), encoding='utf-8')
        cache_fixture = BuildIdentityCacheTests(); cache_fixture.setUp(); cache_fixture.logical = self.logical
        for role, tree, source_dir in [('main', self.build, 's'), ('i18n', self.i18n, 's/pj_app/tests/i18n')]:
            values = cache_fixture.cache(role)
            cache = ''.join(key + ':STRING=' + value + '\n' for key, value in values.items()).encode()
            (tree / 'CMakeCache.txt').write_bytes(cache)
            record = {'schema': 1, 'role': role, 'source_sha': self.sha, 'source_tree': self.tree,
                      'configuration': 'RelWithDebInfo', 'source_dir': source_dir, 'build_tree': tree.name,
                      'native_bundle_mode': True, 'cmake_cache_sha256': hashlib.sha256(cache).hexdigest()}
            (tree / 'native-kit/build_identity.json').write_text(json.dumps(record), encoding='utf-8')
        dialog = importlib.util.spec_from_file_location('dialog_test_contract', self.source / 'packaging/localization/audit_file_dialog_results.py')
        dialog_module = importlib.util.module_from_spec(dialog); dialog.loader.exec_module(dialog_module)
        names = sorted(dialog_module.CASES)
        full = self.listing(name=names[0]); full['tests'] = [self.listing(name=name)['tests'][0] for name in names]
        for language in ('en_US', 'zh_CN', 'zh_TW'):
            case = self.listing(name='CsvRuntimeFileLoader_' + language)['tests'][0]
            case['command'] = [windows(runner_rel)]
            case['properties'].append({'name': 'ENVIRONMENT', 'value': ['PLOTJUGGLER_UI_LANGUAGE=' + language,
                                                                        'QT_QPA_PLATFORM=offscreen']})
            full['tests'].append(case)
        i18n = self.listing(name='LanguageSmoke')
        for doc, tree in ((full, 'b'), (i18n, 'i')):
            case = self.listing(name='pj_bundled_translations_test')['tests'][0]
            case['command'] = [windows(tree + '/RelWithDebInfo/pj_bundled_translations_test.exe'), '-o', '-,txt', '-o',
                               windows(tree + '/Testing/Temporary/bundled-translations.txt') + ',txt']
            doc['tests'].append(case)
        (self.build / 'native-kit/discovery.json').write_text(json.dumps(full), encoding='utf-8')
        (self.i18n / 'native-kit/discovery.json').write_text(json.dumps(i18n), encoding='utf-8')
        candidate = self.candidate()
        main_names = candidate.add_discovery('main', full); i18n_names = candidate.add_discovery('i18n', i18n)
        candidate.add_ctest_metadata()
        plan, report = candidate.finish({'main': main_names, 'i18n': i18n_names})
        run_plan = json.loads((self.build / 'native-kit/run-plan.json').read_text(encoding='utf-8'))
        launcher = planner.load_module('test_derived_launcher', 'run_native_test_bundle.py')
        launcher.validate_plan(run_plan, self.sha, self.tree, 'RelWithDebInfo')
        suites = {suite['id']: suite for suite in run_plan['suites']}
        self.assertNotEqual(suites['main']['tree'], suites['i18n']['tree'])
        self.assertEqual(suites['csv-runtime']['full_discovery'], suites['main']['full_discovery'])
        for suite, tree in (('main', 'b'), ('i18n', 'i')):
            allowed = json.loads((self.root / tree / 'native-kit/allowed-outputs.json').read_text(encoding='utf-8'))
            self.assertEqual(allowed, {'pj_bundled_translations_test': [windows(tree + '/Testing/Temporary/bundled-translations.txt')]})
            self.assertEqual(suites[suite]['allowed_outputs'], tree + '/native-kit/allowed-outputs.json')
        csv = json.loads((self.build / 'native-kit/csv-discovery.json').read_text(encoding='utf-8'))
        self.assertEqual({item['name'] for item in csv['tests']}, {'CsvRuntimeFileLoader_' + x for x in ('en_US', 'zh_CN', 'zh_TW')})
        self.assertIn('b/native-kit/run-plan.json', {item['destination'] for item in plan['files']})
        self.assertEqual(report['status'], 'candidate-only-not-uploadable')
        for name in ('file-dialog-discovery.json', 'csv-discovery.json', 'run-plan.json', 'allowed-outputs.json'):
            (self.build / 'native-kit' / name).unlink()
        (self.i18n / 'native-kit/allowed-outputs.json').unlink()
        for path in (runner, self.build / 'CMakeCache.txt'):
            original = path.read_bytes(); path.write_bytes(original + b'tampered')
            with self.subTest(path=path), self.assertRaises(planner.PlanError):
                candidate.add_run_plan_candidate()
            self.assertFalse((self.build / 'native-kit/run-plan.json').exists())
            path.write_bytes(original)

    def test_rejects_dirty_checkout_and_wrong_source_or_tree(self):
        with self.assertRaisesRegex(planner.PlanError, 'prefix'):
            planner.Candidate(self.root, self.logical, 'f' * 40, self.tree)
        with self.assertRaisesRegex(planner.PlanError, 'tree differs'):
            planner.Candidate(self.root, self.logical, self.sha, 'f' * 40)
        (self.source / 'fixture.txt').write_text('modified', encoding='utf-8')
        with self.assertRaisesRegex(planner.PlanError, 'not clean'):
            self.candidate()

    def test_rejects_traversal_wildcards_and_renamed_destinations(self):
        base = {'schema': 1, 'origins': {'bad': {
            'root': '../outside', 'description': 'bad', 'revision': 'a' * 64, 'license_files': ['s/LICENSE']}},
            'files': []}
        with self.assertRaises(planner.PlanError):
            self.candidate(base)
        base['origins']['bad']['root'] = 'b'
        for entry in ({'origin': 'bad', 'source': '*.exe'}, {'origin': 'bad', 'source': '../s/LICENSE'},
                      {'origin': 'bad', 'source': 'CTestTestfile.cmake', 'destination': 'b/other'}):
            base['files'] = [entry]
            with self.subTest(entry=entry), self.assertRaises(planner.PlanError):
                self.candidate(base)

    def test_does_not_follow_symlinked_candidate(self):
        link = self.build / 'linked.exe'
        try:
            link.symlink_to(self.build / 'RelWithDebInfo/runner.exe')
        except OSError as error:
            self.skipTest('symlink unavailable: ' + str(error))
        candidate = self.candidate()
        candidate.add_discovery('main', self.listing(executable='b/linked.exe'))
        self.assertIn('unsafe-referenced-file', {x['code'] for x in candidate.blockers})

    def test_duplicate_names_and_malformed_properties_are_not_silently_accepted(self):
        candidate = self.candidate()
        listing = self.listing(); listing['tests'].append(dict(listing['tests'][0]))
        with self.assertRaisesRegex(planner.PlanError, 'duplicate'):
            candidate.add_discovery('main', listing)
        listing = self.listing(); listing['tests'][0]['properties'] = []
        with self.assertRaisesRegex(planner.PlanError, 'working directory'):
            self.candidate().add_discovery('main', listing)

    def test_cli_writes_candidate_and_detailed_gaps_but_returns_not_ready(self):
        listing = self.base / 'main.json'; listing.write_text(json.dumps(self.listing()), encoding='utf-8')
        plan, report = self.base / 'candidate.json', self.base / 'report.json'
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/windows/plan_native_stage.py'),
                                 '--root', str(self.root), '--logical-root', self.logical,
                                 '--source-sha', self.sha, '--source-tree', self.tree,
                                 '--discovery', 'main=' + str(listing), '--output', str(plan), '--report', str(report)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertTrue(plan.is_file())
        self.assertEqual(json.loads(report.read_text(encoding='utf-8'))['status'], 'candidate-only-not-uploadable')
        original = plan.read_bytes()
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/windows/plan_native_stage.py'),
                                 '--root', str(self.root), '--logical-root', self.logical,
                                 '--source-sha', self.sha, '--source-tree', self.tree,
                                 '--output', str(plan), '--report', str(report)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(plan.read_bytes(), original)



class CMakeFileApiCandidateTests(unittest.TestCase):
    """Synthetic File API replies only; no Windows build or dynamic-load claim."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.sha = '1' * 40; self.tree = '2' * 40
        self.root = Path(self.tmp.name).resolve() / 'n' / self.sha[:12]
        self.root.mkdir(parents=True)
        self.logical = str(self.root) if os.name == 'nt' else 'C:\\Testing\\n\\' + self.sha[:12]
        (self.root / 's').mkdir()
        self.reply = self.root / 'b/.cmake/api/v1/reply'; self.reply.mkdir(parents=True)
        self.query = self.root / 'b/.cmake/api/v1/query/codemodel-v2'; self.query.parent.mkdir(parents=True)
        self.query.write_bytes(b'')
        (self.root / 'b/native-kit/codemodel').mkdir(parents=True)
        self.contract = planner.load_module('test_file_api_contract', 'verify_native_ci_closure.py')
        rules = self.contract.CODEMODEL_RULES
        runners = {rule['target']: rule['runner'] for rule in rules.values()}
        plugins = {name for rule in rules.values() for name in rule['definitions'].values()}
        self.refs = []
        for name in sorted(set(runners) | plugins):
            is_runner = name in runners
            path = runners.get(name, 'b/fixtures/RelWithDebInfo/' + name + '.dll')
            artifact = self.root / path; artifact.parent.mkdir(parents=True, exist_ok=True); artifact.write_bytes(name.encode())
            filename = 'target-' + name + '.json'; target_id = name + '::@test'
            self.refs.append({'name': name, 'id': target_id, 'jsonFile': filename})
            self.put(filename, {'name': name, 'id': target_id, 'type': 'EXECUTABLE' if is_runner else 'SHARED_LIBRARY',
                                'artifacts': [{'path': path[2:]}]})
        self.put('codemodel-v2-abc.json', {'kind': 'codemodel', 'version': {'major': 2, 'minor': 8},
                 'paths': {'source': self.logical + '\\s', 'build': self.logical + '\\b'},
                 'configurations': [{'name': 'RelWithDebInfo', 'targets': self.refs}]})
        self.put('index-2026-01-01T01-02-03-001.json',
                 {'cmake': {'generator': {'name': 'Ninja Multi-Config', 'multiConfig': True}},
                  'reply': {'codemodel-v2': {'kind': 'codemodel', 'version': {'major': 2},
                                             'jsonFile': 'codemodel-v2-abc.json'}}})
        self.git_patch = mock.patch.object(planner, 'git', side_effect=self.fake_git)
        self.git_patch.start(); self.addCleanup(self.git_patch.stop)

    def fake_git(self, source, *args, **kwargs):
        if args[:2] == ('rev-parse', 'HEAD'): return self.sha
        if args[:2] == ('rev-parse', 'HEAD^{tree}'): return self.tree
        if args and args[0] == 'status': return ''
        raise AssertionError(args)

    def put(self, name, value):
        (self.reply / name).write_text(json.dumps(value), encoding='utf-8')

    def capture(self):
        result = planner.capture_codemodel(self.root, self.logical, self.sha, self.tree)
        planner.write_new(self.root / 'b/native-kit/codemodel/capture.json', result)
        return result

    def candidate(self):
        candidate = planner.Candidate.__new__(planner.Candidate)
        candidate.root, candidate.logical_root = self.root, self.logical
        candidate.source_sha, candidate.source_tree = self.sha, self.tree
        candidate.origins = {'main-build': {'root': str(self.root / 'b')}}
        candidate.origin_prefixes = {'main-build': 'b'}
        candidate.files, candidate.blockers, candidate.condition_patterns = {}, [], []
        return candidate

    def test_captures_original_reply_and_stages_exact_sixteen_artifacts(self):
        extra = self.reply / 'target-unreviewed.json'; extra.write_bytes(b'not selected')
        record = self.capture()
        self.assertEqual(len(record['targets']), 16)
        self.assertEqual(sum(row['type'] == 'SHARED_LIBRARY' for row in record['targets']), 14)
        self.assertEqual(len(record['bindings']), 15)
        shared = [row for row in record['bindings'] if row['target'] == 'pj_sdk_fixture_mock_data_source']
        self.assertEqual({row['definition'] for row in shared}, {'PJ_LANGUAGE_SOURCE_PATH', 'PJ_MOCK_DATA_SOURCE_PLUGIN_PATH'})
        self.assertEqual(len({row['path'] for row in shared}), 1)
        self.assertEqual(len(record['reply_files']), 18)
        retained = self.root / 'b/native-kit/codemodel/reply'
        self.assertFalse((retained / extra.name).exists())
        for item in record['reply_files']:
            self.assertEqual((self.root / item['path']).read_bytes(), (self.reply / Path(item['path']).name).read_bytes())
        candidate = self.candidate(); candidate.add_codemodel_candidates()
        selected = {row['destination'] for row in candidate.files.values()}
        self.assertTrue({row['path'] for row in record['targets']} <= selected)
        self.assertIn('b/native-kit/codemodel/query/codemodel-v2', selected)
        self.assertNotIn('b/native-kit/codemodel/reply/target-unreviewed.json', selected)
        changed = self.root / record['targets'][0]['path']; changed.write_bytes(b'tamper')
        with self.assertRaisesRegex(planner.PlanError, 'changed'):
            self.candidate().add_codemodel_candidates()

    def test_rejects_ambiguous_index_target_paths_and_changed_query(self):
        model = self.reply / 'codemodel-v2-abc.json'
        target = self.reply / self.refs[0]['jsonFile']
        original_model, original_target = model.read_bytes(), target.read_bytes()
        for defect in ('two-indexes', 'duplicate-target', 'outside', 'traversal', 'duplicate-json', 'query'):
            model.write_bytes(original_model); target.write_bytes(original_target); self.query.write_bytes(b'')
            second = self.reply / 'index-extra.json'
            if second.exists(): second.unlink()
            if defect == 'two-indexes': second.write_text('{}', encoding='utf-8')
            elif defect == 'query': self.query.write_bytes(b'not empty')
            elif defect in ('missing-target', 'duplicate-target'):
                obj = json.loads(original_model); refs = obj['configurations'][0]['targets']
                refs.pop() if defect == 'missing-target' else refs.append(dict(refs[0]))
                model.write_text(json.dumps(obj), encoding='utf-8')
            elif defect == 'duplicate-json': target.write_text('{"name":"a","name":"b"}', encoding='utf-8')
            else:
                obj = json.loads(original_target)
                extension = '.exe' if obj['type'] == 'EXECUTABLE' else '.dll'
                obj['artifacts'] = [{'path': ('C:/outside/file' if defect == 'outside' else '../escape/file') + extension}]
                target.write_text(json.dumps(obj), encoding='utf-8')
            with self.subTest(defect=defect), self.assertRaises((planner.PlanError, planner.audit.AuditError)):
                planner.capture_codemodel(self.root, self.logical, self.sha, self.tree)
            self.assertFalse((self.root / 'b/native-kit/codemodel/reply').exists())

    def test_missing_unselected_rule_is_reported_without_inventing_an_artifact(self):
        model_path = self.reply / 'codemodel-v2-abc.json'
        model = json.loads(model_path.read_text(encoding='utf-8'))
        missing = 'mock_data_source_newer_sdk_plugin'
        model['configurations'][0]['targets'] = [x for x in model['configurations'][0]['targets'] if x['name'] != missing]
        model_path.write_text(json.dumps(model), encoding='utf-8')
        record = self.capture()
        rules = {x['rule']: x for x in record['rule_coverage']}
        self.assertEqual(rules['runtime-catalog-language']['status'], 'available')
        self.assertEqual(rules['extension-manager']['status'], 'condition_missing')
        self.assertEqual(rules['extension-manager']['missing'][0]['target'], missing)
        self.assertFalse(any(x['target'] == missing for x in record['targets']))
        bindings = [x for x in record['bindings'] if x['target'] == missing]
        self.assertEqual(len(bindings), 1); self.assertEqual(bindings[0]['status'], 'condition_missing')
        candidate = self.candidate(); candidate.add_codemodel_candidates()
        self.assertTrue(any(x[1] == 'extension_manager_test' for x in candidate.condition_patterns))
        self.assertFalse(any(x[1] == 'RuntimeCatalogLanguageTest' for x in candidate.condition_patterns))

    def test_existing_capture_directory_is_never_reused(self):
        self.capture()
        with self.assertRaisesRegex(planner.PlanError, 'reuse'):
            planner.capture_codemodel(self.root, self.logical, self.sha, self.tree)



class CMakeRuleSelectionTests(unittest.TestCase):
    """Exercise actual reviewed partition and fixture closure with synthetic discovery."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.sha = '1' * 40; self.tree = '2' * 40
        self.root = Path(self.tmp.name).resolve() / 'n' / self.sha[:12]
        self.root.mkdir(parents=True)
        self.logical = str(self.root) if os.name == 'nt' else 'C:\\Testing\\n\\' + self.sha[:12]
        self.contract = planner.load_module('test_real_partition_contract', 'verify_native_ci_closure.py')
        self.launcher = planner.load_module('test_real_selection_launcher', 'run_native_test_bundle.py')
        self.ci = planner.load_module('test_real_selection_ci', 'run_native_ci_verification.py')
        self.runtime = self.contract.CODEMODEL_RULES['runtime-catalog-language']['runner']
        self.extension = self.contract.CODEMODEL_RULES['extension-manager']['runner']
        self.safe = 'b/RelWithDebInfo/safe.exe'
        def case(name, path):
            return {'name': name, 'command': [self.logical + '\\' + path.replace('/', '\\')], 'properties': []}
        self.main = {'kind': 'ctestInfo', 'tests': [case('RuntimeCatalogLanguageTest', self.runtime),
                     case('extension_manager_test', self.extension), case('IndependentSafe', self.safe)]}
        self.i18n = {'kind': 'ctestInfo', 'tests': [case('unreviewed', 'i/RelWithDebInfo/other.exe')]}
        self.write('b/native-kit/discovery.json', self.main); self.write('i/native-kit/discovery.json', self.i18n)
        self.suites = [{'id': 'main', 'kind': 'ctest', 'full_discovery': 'b/native-kit/discovery.json',
                        'discovery': 'b/native-kit/discovery.json'},
                       {'id': 'i18n', 'kind': 'ctest', 'full_discovery': 'i/native-kit/discovery.json',
                        'discovery': 'i/native-kit/discovery.json'}]
        self.write('b/native-kit/run-plan.json', {})
        self.write('s/scripts/windows/verify_native_ci_closure.py', 'source-reviewed synthetic verifier')
        verifier = self.root / 's/scripts/windows/verify_native_ci_closure.py'
        def approved(case_name, path):
            return {'suite': 'main', 'case': case_name, 'executable': path, 'reason': 'synthetic reviewed case',
                    'evidence': ['s/review.md']}
        self.policy = {'schema': 2, 'verifier_sha256': planner.digest(verifier), 'suite_ids': ['main', 'i18n'],
                       'unreviewed_evidence': ['s/review.md'], 'approved_runners': [],
                       'approved_cases': [approved('RuntimeCatalogLanguageTest', self.runtime),
                                          approved('IndependentSafe', self.safe)]}
        self.write('s/.github/windows-native-kit/ci-closure-policy.json', self.policy)
        self.candidate_path = self.root / 'b/native-kit/stage-candidate.json'
        self.report_path = self.root / 'b/native-kit/stage-gaps.json'
        self.policy_path = self.root / 's/.github/windows-native-kit/ci-closure-policy.json'
        self.write('b/native-kit/stage-candidate.json', {'files': [{'destination': x} for x in
                   (self.runtime, self.safe, 'i/RelWithDebInfo/other.exe', 's/review.md')]})
        self.report = {'source_sha': self.sha, 'source_tree': self.tree, 'logical_root': self.logical,
                       'configuration': 'RelWithDebInfo', 'coverage': [{'suite': 'main', 'case': 'extension_manager_test',
                       'status': 'condition_missing', 'reason': 'synthetic extension target is absent'}]}
        self.write('b/native-kit/stage-gaps.json', self.report)
        self.capture = {'source_sha': self.sha, 'source_tree': self.tree, 'rule_coverage': [
            {'rule': 'runtime-catalog-language', 'status': 'available', 'missing': []},
            {'rule': 'extension-manager', 'status': 'condition_missing',
             'missing': [{'target': 'example', 'reason': 'not present'}]}]}
        self.write('b/native-kit/codemodel/capture.json', self.capture)
        self.git = mock.patch.object(planner, 'git', side_effect=self.fake_git); self.git.start(); self.addCleanup(self.git.stop)
        self.verifier = mock.patch.object(planner, 'load_reviewed_verifier', return_value=self.contract)
        self.verifier.start(); self.addCleanup(self.verifier.stop)
        self.plan_check = mock.patch.object(self.launcher, 'validate_plan', return_value=({}, [], self.suites))
        self.plan_check.start(); self.addCleanup(self.plan_check.stop)
        original = planner.load_module
        def modules(name, filename):
            if filename == 'run_native_test_bundle.py': return self.launcher
            if filename == 'run_native_ci_verification.py': return self.ci
            return original(name, filename)
        self.loader = mock.patch.object(planner, 'load_module', side_effect=modules)
        self.loader.start(); self.addCleanup(self.loader.stop)

    def write(self, relative, value):
        path = self.root / relative; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value if isinstance(value, str) else json.dumps(value), encoding='utf-8')

    def fake_git(self, source, *args, **kwargs):
        if args[:2] == ('rev-parse', 'HEAD'): return self.sha
        if args[:2] == ('rev-parse', 'HEAD^{tree}'): return self.tree
        if args and args[0] == 'status': return ''
        raise AssertionError(args)

    def select(self):
        return planner.select_codemodel_rules(self.root, self.logical, self.sha, self.tree,
                                             self.candidate_path, self.report_path, self.policy_path)

    def test_unapproved_missing_extension_is_not_selected_or_claimed(self):
        result = {row['rule']: row for row in self.select()['rules']}
        self.assertEqual(result['runtime-catalog-language']['status'], 'selected')
        self.assertEqual(result['runtime-catalog-language']['cases'], [{'suite': 'main', 'case': 'RuntimeCatalogLanguageTest'}])
        self.assertEqual(result['extension-manager']['status'], 'not_selected')
        self.assertEqual(result['extension-manager']['target_condition']['status'], 'condition_missing')

    def test_extension_rule_is_verified_only_when_really_approved_and_selected(self):
        self.policy['approved_cases'].append({'suite': 'main', 'case': 'extension_manager_test',
                                             'executable': self.extension, 'reason': 'synthetic reviewed case',
                                             'evidence': ['s/review.md']})
        self.write('s/.github/windows-native-kit/ci-closure-policy.json', self.policy)
        candidate = json.loads(self.candidate_path.read_text(encoding='utf-8'))
        candidate['files'].append({'destination': self.extension})
        self.write('b/native-kit/stage-candidate.json', candidate)
        self.report['coverage'] = []
        self.write('b/native-kit/stage-gaps.json', self.report)
        self.capture['rule_coverage'][1] = {'rule': 'extension-manager', 'status': 'available', 'missing': []}
        self.write('b/native-kit/codemodel/capture.json', self.capture)
        result = {row['rule']: row for row in self.select()['rules']}
        self.assertEqual(result['extension-manager']['status'], 'selected')
        self.assertEqual(result['extension-manager']['cases'], [{'suite': 'main', 'case': 'extension_manager_test'}])
        self.assertEqual(result['runtime-catalog-language']['status'], 'selected')

    def test_missing_runtime_condition_keeps_independent_safe_group(self):
        self.report['coverage'].append({'suite': 'main', 'case': 'RuntimeCatalogLanguageTest',
                                        'status': 'condition_missing', 'reason': 'fixture absent'})
        self.capture['rule_coverage'][0]['status'] = 'condition_missing'
        self.write('b/native-kit/stage-gaps.json', self.report); self.write('b/native-kit/codemodel/capture.json', self.capture)
        result = {row['rule']: row for row in self.select()['rules']}
        self.assertEqual(result['runtime-catalog-language']['status'], 'not_selected')
        self.assertEqual(result['extension-manager']['status'], 'not_selected')

    def test_a_selected_rule_with_missing_actual_targets_is_rejected(self):
        self.capture['rule_coverage'][0]['status'] = 'condition_missing'
        self.write('b/native-kit/codemodel/capture.json', self.capture)
        with self.assertRaisesRegex(planner.PlanError, 'selected CMake rule'):
            self.select()

    def test_approved_group_with_unreviewed_dependency_cannot_silently_disappear(self):
        self.main['tests'][0]['properties'].append({'name': 'DEPENDS', 'value': ['extension_manager_test']})
        self.write('b/native-kit/discovery.json', self.main)
        with self.assertRaisesRegex(planner.PlanError, 'does not close'):
            self.select()


class RequiredBootstrapDirectoryTests(unittest.TestCase):
    def test_file_allowlist_produces_all_authenticated_pth_parents(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory); source = base / 'origin'; source.mkdir()
            paths = {'LICENSE': 's/LICENSE', 'python.exe': 't/python/python.exe',
                     'driver.py': 's/scripts/driver.py', 'test.py': 's/tests/test.py',
                     'localize.py': 's/packaging/localization/helper.py'}
            files = []
            for name, destination in paths.items():
                item = source / name; item.write_bytes(('fixture:' + name).encode())
                files.append({'origin': 'repo', 'source': name, 'destination': destination,
                              'sha256': hashlib.sha256(item.read_bytes()).hexdigest()})
            plan = {'origins': {'repo': {'root': str(source), 'description': 'synthetic project',
                                        'revision': 'a' * 40, 'license_files': ['s/LICENSE']}}, 'files': files}
            plan_file = base / 'plan.json'; plan_file.write_text(json.dumps(plan), encoding='utf-8')
            stage = base / 'stage'; logical = r'C:\Testing\n\123456789abc'
            planner.audit.stage_allowlisted(plan_file, stage, logical)
            directories = set(planner.audit.inventory(stage, logical)['directories'])
            self.assertTrue({'t/python', 's', 's/scripts', 's/tests', 's/packaging/localization'} <= directories)


class BuildIdentityCacheTests(unittest.TestCase):
    def setUp(self):
        self.logical = 'C:\\Tests\\n\\123456789abc'
        self.qt_version = '6.12.0'

    def cache(self, role):
        def path(relative):
            return self.logical + '\\' + relative.replace('/', '\\')
        build = 'b' if role == 'main' else 'i'
        source = 's' if role == 'main' else 's/pj_app/tests/i18n'
        values = {'CMAKE_HOME_DIRECTORY': path(source), 'CMAKE_CACHEFILE_DIR': path(build),
                  'CMAKE_COMMAND': path('t/cmake/bin/cmake.exe'),
                  'CMAKE_MAKE_PROGRAM': path('t/builder/Scripts/ninja.exe'),
                  'Python3_EXECUTABLE': path('t/python/python.exe'), 'PJ_TEST_PYTHON': path('t/python/python.exe'),
                  'CMAKE_PREFIX_PATH': path('q/6.12.0/msvc2022_64'),
                  'PJ_IFW_TEST_ARCHIVE': path('t/ifw/ifw.7z'), 'PJ_IFW_TEST_EXTRACTOR': path('t/7z/7za.exe'),
                  'PJ_IFW_TEST_EXTRACTOR_SHA256': 'a' * 64, 'CMAKE_GENERATOR': 'Ninja Multi-Config',
                  'CMAKE_CONFIGURATION_TYPES': 'Debug;Release;RelWithDebInfo',
                  'CMAKE_PROJECT_NAME': 'plotjuggler4' if role == 'main' else 'plotjuggler4_i18n_tests',
                  'CMAKE_CXX_COMPILER': 'C:\\VS\\bin\\cl.exe', 'PJ_NATIVE_BUNDLE_MODE': 'ON'}
        if role == 'main':
            values.update(CMAKE_TOOLCHAIN_FILE=path('b/conan_toolchain.cmake'),
                          PJ_BUILD_TESTS='ON', PJ_PLUGIN_FEEDBACK_ACCEPTANCE='ON',
                          PJ_CSV_RUNTIME_PLUGIN=path('b/csv-prefix/lib/plotjuggler/plugins/csv-loader/csv.dll'))
        return values

    def test_each_role_requires_its_own_source_and_build_trees(self):
        main = planner.validate_build_cache(self.cache('main'), self.logical, 'main', self.qt_version)
        i18n = planner.validate_build_cache(self.cache('i18n'), self.logical, 'i18n', self.qt_version)
        self.assertEqual((main['source_dir'], main['build_tree']), ('s', 'b'))
        self.assertEqual((i18n['source_dir'], i18n['build_tree']), ('s/pj_app/tests/i18n', 'i'))
        with self.assertRaises(planner.PlanError):
            planner.validate_build_cache(self.cache('main'), self.logical, 'i18n', self.qt_version)
        with self.assertRaises(planner.PlanError):
            planner.validate_build_cache(self.cache('i18n'), self.logical, 'main', self.qt_version)

    def test_wrong_tool_qt_build_or_configuration_is_rejected(self):
        for key, replacement in [('CMAKE_HOME_DIRECTORY', 'C:\\other\\s'),
                                 ('CMAKE_CACHEFILE_DIR', self.logical + '\\i'),
                                 ('Python3_EXECUTABLE', 'C:\\Windows\\python.exe'),
                                 ('CMAKE_MAKE_PROGRAM', 'C:\\Windows\\ninja.exe'),
                                 ('CMAKE_PREFIX_PATH', 'C:\\Qt\\6.12.0'),
                                 ('PJ_IFW_TEST_EXTRACTOR_SHA256', '0' * 63),
                                 ('CMAKE_GENERATOR', 'Ninja'), ('CMAKE_CONFIGURATION_TYPES', 'Release'),
                                 ('PJ_NATIVE_BUNDLE_MODE', 'OFF'),
                                 ('PJ_PLUGIN_FEEDBACK_ACCEPTANCE', 'OFF'),
                                 ('PJ_CSV_RUNTIME_PLUGIN', 'C:\\other\\csv.dll'),
                                 ('CMAKE_CXX_COMPILER', 'C:\\compiler\\gcc.exe')]:
            with self.subTest(key=key):
                values = self.cache('main'); values[key] = replacement
                with self.assertRaises(planner.PlanError):
                    planner.validate_build_cache(values, self.logical, 'main', self.qt_version)

    def test_native_mode_is_required_in_both_independent_caches(self):
        for role in ('main', 'i18n'):
            for bad in ('OFF', '', None):
                values = self.cache(role)
                if bad is None:
                    del values['PJ_NATIVE_BUNDLE_MODE']
                else:
                    values['PJ_NATIVE_BUNDLE_MODE'] = bad
                with self.subTest(role=role, bad=bad), self.assertRaises(planner.PlanError):
                    planner.validate_build_cache(values, self.logical, role, self.qt_version)

    def test_duplicate_or_malformed_cache_entries_fail(self):
        self.assertEqual(planner.cache_values('// comment\nNAME:STRING=value\n'), {'NAME': 'value'})
        for raw in ('NAME:STRING=x\nNAME:FILEPATH=y\n', 'NOT_A_CACHE_ENTRY\n'):
            with self.subTest(raw=raw), self.assertRaises(planner.PlanError):
                planner.cache_values(raw)


if __name__ == '__main__':
    unittest.main()
