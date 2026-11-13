# SPDX-License-Identifier: MPL-2.0
"""Pure/synthetic launcher checks. No Windows process or user VM is touched."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('native_launcher', ROOT / 'scripts/windows/run_native_test_bundle.py')
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


def plan():
    return {'schema': 1, 'source_sha': 'a' * 40, 'source_tree': 'b' * 40, 'configuration': 'RelWithDebInfo',
            'paths': {'python': 't/python/python.exe', 'ctest': 't/cmake/bin/ctest.exe',
                      'probe': 't/probe/probe.exe', 'qt': 'q/qt', 'fonts': 'b/fonts', 'feedback': 'b/feedback'},
            'runtime_dirs': ['c/runtime'],
            'suites': [{'id': 'main', 'kind': 'ctest', 'tree': 'b', 'discovery': '_bundle/main.json',
                        'full_discovery': '_bundle/main.json', 'build_identity': '_bundle/main-identity.json'},
                       {'id': 'i18n', 'kind': 'ctest', 'tree': 'i', 'discovery': '_bundle/i18n.json',
                        'full_discovery': '_bundle/i18n.json', 'build_identity': '_bundle/i18n-identity.json'},
                       {'id': 'file-dialog', 'kind': 'ctest', 'tree': 'b', 'discovery': '_bundle/dialog.json',
                        'full_discovery': '_bundle/main.json', 'pattern': '^dialog', 'platform': 'windows'},
                       {'id': 'csv-runtime', 'kind': 'csv', 'tree': 'b', 'discovery': '_bundle/csv.json',
                        'full_discovery': '_bundle/main.json', 'pattern': '^CsvRuntimeFileLoader_',
                        'build_identity': '_bundle/main-identity.json',
                        'prefix': 'b/prefix', 'identity': '_bundle/csv-identity.json'}]}


class LauncherTests(unittest.TestCase):
    def test_plan_requires_all_distinct_unfiltered_main_trees(self):
        p = plan()
        self.assertEqual(len(launcher.validate_plan(p, 'a' * 40, 'b' * 40, 'RelWithDebInfo')[2]), 4)
        for edit in ('missing', 'filter-main', 'global-platform', 'csv-filter', 'wrong-kind', 'wrong-source', 'same-tree', 'same-discovery', 'same-identity', 'wrong-repeat'):
            p = plan()
            if edit == 'missing': p['suites'].pop()
            elif edit == 'filter-main': p['suites'][0]['pattern'] = 'small-subset'
            elif edit == 'global-platform': p['suites'][1]['platform'] = 'windows'
            elif edit == 'csv-filter': p['suites'][3]['pattern'] = 'one-language'
            elif edit == 'wrong-kind': p['suites'][3]['kind'] = 'ctest'
            elif edit == 'same-tree': p['suites'][1]['tree'] = p['suites'][0]['tree']
            elif edit == 'same-discovery': p['suites'][1]['full_discovery'] = p['suites'][0]['full_discovery']
            elif edit == 'same-identity': p['suites'][1]['build_identity'] = p['suites'][0]['build_identity']
            elif edit == 'wrong-repeat': p['suites'][2]['full_discovery'] = p['suites'][1]['full_discovery']
            else: p['source_sha'] = 'f' * 40
            with self.subTest(edit=edit), self.assertRaises(launcher.LauncherError):
                launcher.validate_plan(p, 'a' * 40, 'b' * 40, 'RelWithDebInfo')

    def test_plan_cannot_load_an_unmanifested_or_run_output_executable(self):
        p = plan()
        files = [p['paths'][x] for x in ('python', 'ctest', 'probe')]
        files += [p['paths']['qt'] + '/bin/Qt6Core.dll']
        files += [x['discovery'] for x in p['suites']] + [p['suites'][3]['identity']]
        files += [p['suites'][0]['build_identity'], p['suites'][1]['build_identity']]
        directories = [p['paths'][x] for x in ('qt', 'fonts', 'feedback')] + p['runtime_dirs']
        directories += [x['tree'] for x in p['suites']] + [p['suites'][3]['prefix']]
        manifest = {'files': [{'path': x} for x in files], 'directories': directories}
        launcher.validate_plan_bindings(p['paths'], p['runtime_dirs'], p['suites'], manifest)
        p['paths']['probe'] = 'r/previous/unknown.exe'
        with self.assertRaises(launcher.LauncherError):
            launcher.validate_plan_bindings(p['paths'], p['runtime_dirs'], p['suites'], manifest)
        p = plan(); p['runtime_dirs'] = ['r/previous']
        manifest['directories'].append('r/previous')
        with self.assertRaises(launcher.LauncherError):
            launcher.validate_plan_bindings(p['paths'], p['runtime_dirs'], p['suites'], manifest)
        for forbidden in ('t/python', 'T/PYTHON/plugins'):
            p = plan(); p['runtime_dirs'] = [forbidden]
            manifest['directories'].append(forbidden)
            with self.subTest(directory=forbidden), self.assertRaises(launcher.LauncherError):
                launcher.validate_plan_bindings(p['paths'], p['runtime_dirs'], p['suites'], manifest)

    def test_test_path_excludes_driver_python_but_keeps_locked_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); windows = root / 'windows'; qt = root / 'qt'
            driver = root / 't/python/python.exe'; ctest = root / 't/cmake/bin/ctest.exe'
            conan = root / 'c/cpython/bin'
            for folder in (windows / 'System32', qt / 'bin', driver.parent, ctest.parent, conan):
                folder.mkdir(parents=True, exist_ok=True)
            driver.write_bytes(b'official-driver'); ctest.write_bytes(b'ctest')
            value = launcher.test_runtime_search_path(windows, qt, ctest, [conan], [], driver)
            paths = value.split(os.pathsep)
            self.assertIn(str(conan), paths)
            self.assertNotIn(str(driver.parent), paths)
            with self.assertRaises(launcher.LauncherError):
                launcher.test_runtime_search_path(windows, qt, ctest, [conan, driver.parent], [], driver)

    def test_csv_may_be_a_distinct_source_identified_tree_without_false_repeat(self):
        p = plan(); csv = p['suites'][3]
        csv.update(tree='csv', full_discovery='_bundle/csv-full.json', build_identity='_bundle/csv-build.json')
        launcher.validate_plan(p, 'a' * 40, 'b' * 40, 'RelWithDebInfo')
        doc = {'kind': 'ctestInfo', 'tests': [{'name': 'case', 'command': ['test'], 'properties': []}]}
        prepared = {item['id']: {'selected': {'case'}, 'unrun': [], 'desired': {'case'}} for item in p['suites']}
        with tempfile.TemporaryDirectory() as directory:
            progress = launcher.initialize_execution_plan(Path(directory), p['suites'], prepared,
                                                          {item['id']: doc for item in p['suites']}, 'reviewed-subset')
        self.assertIsNone(progress['csv-runtime']['repeat_of'])
        self.assertEqual(progress['csv-runtime']['overlapping_main_case_names'], ['case'])
        csv['full_discovery'] = p['suites'][0]['full_discovery']
        with self.assertRaises(launcher.LauncherError):
            launcher.validate_plan(p, 'a' * 40, 'b' * 40, 'RelWithDebInfo')

    def test_driver_import_path_is_exact_pinned_pth_and_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); python = root / 't/python'; python.mkdir(parents=True)
            (python / 'python312.zip').write_bytes(b'zip')
            for part in ('s/scripts', 's/tests', 's/packaging/localization'):
                (root / part).mkdir(parents=True)
            expected = [python / 'python312.zip', python, root / 's', root / 's/scripts', root / 's/tests', root / 's/packaging/localization']
            pth = python / 'python312._pth'
            pth.write_text('python312.zip\n.\n# no site\n' + ''.join(str(x) + '\n' for x in expected[2:]), encoding='utf-8')
            launcher.check_driver_import_paths(root, [str(x) for x in expected])
            with self.assertRaises(launcher.LauncherError): launcher.check_driver_import_paths(root, [str(x) for x in expected] + [str(root)])
            pth.write_text(pth.read_text(encoding='utf-8') + 'import site\n', encoding='utf-8')
            with self.assertRaises(launcher.LauncherError): launcher.check_driver_import_paths(root, [str(x) for x in expected])
            pth.unlink()
            with self.assertRaises(launcher.LauncherError): launcher.check_driver_import_paths(root, [str(x) for x in expected])

    def test_build_identity_binds_tree_source_and_cache_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / '_bundle').mkdir()
            record = {'schema': 1, 'role': 'i18n', 'source_sha': 'a' * 40, 'source_tree': 'b' * 40,
                      'configuration': 'RelWithDebInfo', 'source_dir': 's/pj_app/tests/i18n',
                      'build_tree': 'i', 'native_bundle_mode': True, 'cmake_cache_sha256': 'c' * 64}
            path = root / '_bundle/i18n.json'; path.write_text(json.dumps(record), encoding='utf-8')
            suite = {'id': 'i18n', 'tree': 'i', 'build_identity': '_bundle/i18n.json'}
            launcher.check_build_identity(root, suite, 'a' * 40, 'b' * 40, 'RelWithDebInfo', 'b')
            for key, value in (('source_dir', 's'), ('build_tree', 'b'), ('native_bundle_mode', False), ('native_bundle_mode', 1), ('cmake_cache_sha256', 'bad')):
                changed = dict(record, **{key: value}); path.write_text(json.dumps(changed), encoding='utf-8')
                with self.subTest(key=key), self.assertRaises(launcher.LauncherError):
                    launcher.check_build_identity(root, suite, 'a' * 40, 'b' * 40, 'RelWithDebInfo', 'b')
    def test_owned_outputs_are_fresh_per_suite_and_block_ctest_overrides(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); run = root / 'r' / ('run-' + 'a' * 32)
            (run / 'tmp').mkdir(parents=True); (run / 'main').mkdir(); (run / 'csv-runtime').mkdir()
            names = {'CsvRuntimeFileLoader_en_US', 'AppProfile.IsolatedPaths'}
            doc = {'kind': 'ctestInfo', 'tests': [
                {'name': name, 'command': ['test.exe'], 'properties': []} for name in names]}
            env = {'TEMP': str(run / 'tmp'), 'TMP': str(run / 'tmp'), 'PATH': 'safe'}
            first = launcher.prepare_owned_suite_outputs(root, run, {'id': 'main'}, names, doc, env)
            second = launcher.prepare_owned_suite_outputs(root, run, {'id': 'csv-runtime'}, {'CsvRuntimeFileLoader_en_US'}, doc, env)
            self.assertNotEqual(first['PJ_CSV_DIAGNOSTIC_DIR'], second['PJ_CSV_DIAGNOSTIC_DIR'])
            self.assertNotIn(first['PJ_NATIVE_OUTPUT_ROOT'], first['PATH'])
            self.assertNotIn('PJ_UPDATE_POINTCLOUD_GOLDENS', first)
            with self.assertRaises(FileExistsError):
                launcher.prepare_owned_suite_outputs(root, run, {'id': 'main'}, names, doc, env)
            for override in ('TEMP=elsewhere', 'TMP=elsewhere', 'XDG_CACHE_HOME=elsewhere',
                             'PJ_NATIVE_OUTPUT_ROOT=elsewhere', 'PJ_UPDATE_POINTCLOUD_GOLDENS=1',
                             'PJ_POINTCLOUD_GOLDEN_OUT=elsewhere', 'PJ_CSV_DIAGNOSTIC_DIR=elsewhere'):
                target = run / 'i18n'; target.mkdir(exist_ok=True)
                bad = {'kind': 'ctestInfo', 'tests': [{'name': 'AppProfile.IsolatedPaths', 'command': ['test.exe'],
                       'properties': [{'name': 'ENVIRONMENT', 'value': [override]}]}]}
                with self.subTest(override=override), self.assertRaises(launcher.LauncherError):
                    launcher.prepare_owned_suite_outputs(root, run, {'id': 'i18n'}, {'AppProfile.IsolatedPaths'}, bad, env)
            self.assertEqual(list((run / 'i18n').iterdir()), [])
            bad = {'kind': 'ctestInfo', 'tests': [{'name': 'AppProfile.IsolatedPaths', 'command': ['test.exe'],
                   'properties': [{'name': 'ENVIRONMENT_MODIFICATION', 'value': ['TEMP=set:C:/wrong']}]}]}
            with self.assertRaises(launcher.LauncherError):
                launcher.prepare_owned_suite_outputs(root, run, {'id': 'i18n'}, {'AppProfile.IsolatedPaths'}, bad, env)

            for variable in ('PATH', 'PYTHONHOME', 'PYTHONPATH', 'PYTHONEXECUTABLE', 'PYTHONUSERBASE'):
                for property_name, assignment in (('ENVIRONMENT', variable + '=C:/wrong'),
                                                  ('ENVIRONMENT_MODIFICATION', variable + '=set:C:/wrong')):
                    case = {'name': 'ordinary', 'command': ['test.exe'],
                            'properties': [{'name': property_name, 'value': [assignment]}]}
                    document = {'kind': 'ctestInfo', 'tests': [case]}
                    with self.subTest(variable=variable, property_name=property_name), self.assertRaises(launcher.LauncherError):
                        launcher.prepare_owned_suite_outputs(root, run, {'id': 'i18n'}, {'ordinary'}, document, env)


    def test_owned_output_inventory_keeps_real_evidence_and_refuses_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); run = root / 'r' / ('ci-' + 'b' * 32)
            (run / 'tmp').mkdir(parents=True); (run / 'main').mkdir()
            name = 'CsvRuntimeFileLoader_en_US'
            doc = {'kind': 'ctestInfo', 'tests': [{'name': name, 'command': ['test.exe'], 'properties': []}]}
            launcher.prepare_owned_suite_outputs(root, run, {'id': 'main'}, {name}, doc,
                                                 {'TEMP': str(run / 'tmp'), 'TMP': str(run / 'tmp'), 'PATH': 'safe'})
            output = run / 'main'; csv = output / 'csv-diagnostics/en_US.json'
            csv.write_text(json.dumps({'version': 1, 'records': [{'id': 'data-source-load-failed',
                            'level': 'error', 'message': 'plugin: translated'}]}), encoding='utf-8')
            image = output / 'pointcloud-golden/case_actual.png'; image.write_bytes(b'actual')
            profile = output / 'profile-tests'; (profile / 'fixture').mkdir()
            (profile / 'fixture/data').write_bytes(b'keep')
            receipt = launcher.inventory_owned_suite_outputs(output, {name}, True)
            self.assertEqual(receipt['csv'][0]['sha256'], hashlib.sha256(csv.read_bytes()).hexdigest())
            self.assertEqual(receipt['pointcloud'][0]['path'], image.name)
            self.assertTrue((profile / 'fixture/data').is_file())
            csv.unlink()
            with self.assertRaises(launcher.LauncherError):
                launcher.inventory_owned_suite_outputs(output, {name}, True)
            self.assertEqual(launcher.inventory_owned_suite_outputs(output, {name}, False)['missing_csv'], ['en_US.json'])
            if hasattr(os, 'symlink'):
                try: os.symlink(root, profile / 'fixture/escape', target_is_directory=True)
                except OSError: return
                with self.assertRaises(launcher.LauncherError):
                    launcher.inventory_owned_suite_outputs(output, set(), False)

    def test_discovery_comparison_includes_order_command_and_properties(self):
        doc = {'kind': 'ctestInfo', 'tests': [{'name': 'one', 'config': 'RelWithDebInfo',
                'command': ['C:/kit/a.exe'], 'properties': [{'name': 'TIMEOUT', 'value': 120}]}]}
        launcher.same_discovery(doc, json.loads(json.dumps(doc)))
        for key, replacement in [('command', ['C:/elsewhere/a.exe']), ('properties', []), ('name', 'other')]:
            other = json.loads(json.dumps(doc)); other['tests'][0][key] = replacement
            with self.subTest(key=key), self.assertRaises(launcher.LauncherError): launcher.same_discovery(doc, other)
        duplicate = json.loads(json.dumps(doc)); duplicate['tests'].append(dict(duplicate['tests'][0]))
        with self.assertRaises(launcher.LauncherError): launcher.same_discovery(duplicate, duplicate)

    def test_identity_rejects_system_session_zero_and_wrong_token(self):
        expected = {'session': 1, 'sid': 'S-1-5-21-100-500', 'integrity_rid': 12288,
                    'auth_luid': '00000000:12345678', 'elevation_type': 'full'}
        launcher.require_identity(dict(expected, pid=10), expected)
        for edit in ({'session': 0}, {'session': True}, {'integrity_rid': True}, {'sid': None},
                     {'sid': 'S-1-5-18'}, {'integrity_rid': 8192}, {'sid': 'S-1-5-21-101-500'},
                     {'auth_luid': '00000000:87654321'}, {'elevation_type': 'limited'}):
            actual = dict(expected, **edit)
            with self.subTest(actual=actual), self.assertRaises(launcher.LauncherError):
                launcher.require_identity(actual, expected)

    def test_mtime_restores_only_recorded_value_and_bytes_are_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); path = root / 'input.bin'; path.write_bytes(b'expected')
            original = path.stat().st_mtime_ns
            manifest = {'logical_root': r'C:\Testing\n\123456789abc',
                        'files': [{'path': 'input.bin', 'bytes': 8, 'sha256': hashlib.sha256(b'expected').hexdigest(),
                                   'mtime_ns': original}], 'directories': []}
            os.utime(path, ns=(path.stat().st_atime_ns, original - 2_000_000_000))
            changes = launcher.restore_verified_mtimes(root, manifest)
            self.assertEqual(len(changes), 1)
            launcher.check_immutable(root, manifest)
            path.write_bytes(b'tampered')
            with self.assertRaises(launcher.LauncherError): launcher.check_immutable(root, manifest)

    def test_reinventory_rejects_added_code_and_only_exact_ctest_logs_are_allowed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / 'b/bin').mkdir(parents=True)
            (root / 'b/bin/test.exe').write_bytes(b'known')
            logical = r'C:\Testing\n\123456789abc'
            manifest = {'logical_root': logical, **launcher.audit.inventory(root, logical)}
            generated = launcher.generated_ctest_outputs([{'tree': 'b'}])
            temporary = root / 'b/Testing/Temporary'; temporary.mkdir(parents=True)
            (temporary / 'LastTest.log').write_bytes(b'ctest output')
            receipt = launcher.check_immutable(root, manifest, generated)
            self.assertEqual(receipt['owned_generated_files'], ['b/Testing/Temporary/LastTest.log'])
            injected = root / 'b/bin/malicious.dll'; injected.write_bytes(b'unlisted')
            with self.assertRaisesRegex(launcher.LauncherError, 'unapproved file'):
                launcher.check_immutable(root, manifest, generated)
            injected.unlink()
            (temporary / 'payload.dll').write_bytes(b'unlisted')
            with self.assertRaisesRegex(launcher.LauncherError, 'unapproved file'):
                launcher.check_immutable(root, manifest, generated)

    def test_qttest_output_allowed_only_for_selected_case_and_exact_tree(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); logical = r'C:\Testing\n\123456789abc'
            (root / '_bundle').mkdir(); (root / 'b/Testing/Temporary').mkdir(parents=True)
            target = logical + r'\b\Testing\Temporary\bundled-translations.txt'
            contract = root / '_bundle/outputs.json'
            contract.write_text(json.dumps({'pj_bundled_translations_test': [target]}), encoding='utf-8')
            suite = {'id': 'main', 'tree': 'b', 'allowed_outputs': '_bundle/outputs.json'}
            command = [logical + r'\b\pj_bundled_translations_test.exe', '-o', '-,txt', '-o', target + ',txt']
            doc = {'kind': 'ctestInfo', 'tests': [{'name': 'pj_bundled_translations_test', 'command': command, 'properties': []}]}
            docs = {'main': doc}; prepared = {'main': {'selected': {'pj_bundled_translations_test'}}}
            generated = launcher.generated_ctest_outputs([suite], docs, prepared, logical, root)
            self.assertIn('b/Testing/Temporary/bundled-translations.txt', generated['files'])
            prepared['main']['selected'] = set()
            self.assertNotIn('b/Testing/Temporary/bundled-translations.txt',
                             launcher.generated_ctest_outputs([suite], docs, prepared, logical, root)['files'])
            prepared['main']['selected'] = {'pj_bundled_translations_test'}
            contract.write_text(json.dumps({'pj_bundled_translations_test': [logical + r'\b\plugins\malicious.dll']}), encoding='utf-8')
            with self.assertRaises(launcher.LauncherError):
                launcher.generated_ctest_outputs([suite], docs, prepared, logical, root)
            contract.write_text(json.dumps({'pj_bundled_translations_test': [target]}), encoding='utf-8')
            doc['tests'][0]['command'][4] = target + ',xml'
            with self.assertRaises(launcher.audit.AuditError):
                launcher.generated_ctest_outputs([suite], docs, prepared, logical, root)

    def test_process_capture_keeps_raw_ctest_stdout_and_stderr_bytes(self):
        expected = {'session': 1, 'sid': 'S-1-5-21-100-500', 'integrity_rid': 12288}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); stdout, stderr = root / 'stdout', root / 'stderr'
            child = mock.Mock(pid=55, _handle=123); child.wait.return_value = 0
            def start(*args, **kwargs):
                kwargs['stdout'].write(b'\xffout\n'); kwargs['stderr'].write(b'\xfestderr\n'); return child
            with mock.patch.object(launcher.subprocess, 'Popen', side_effect=start), \
                 mock.patch.object(launcher, 'process_identity', return_value=dict(expected, pid=55)):
                result = launcher.run_process(['C:/tool/ctest.exe', '--verbose'], root, {'PATH': 'restricted'},
                                              stdout, stderr, expected, 60)
            self.assertEqual(stdout.read_bytes(), b'\xffout\n')
            self.assertEqual(stderr.read_bytes(), b'\xfestderr\n')
            self.assertEqual(result['stdout_sha256'], hashlib.sha256(stdout.read_bytes()).hexdigest())
            self.assertEqual(result['exit_code'], 0)

    def test_process_timeout_is_reported_as_still_running_not_complete(self):
        expected = {'session': 1, 'sid': 'S-1-5-21-100-500', 'integrity_rid': 12288}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); child = mock.Mock(pid=55, _handle=123)
            child.wait.side_effect = subprocess.TimeoutExpired('ctest', 1)
            with mock.patch.object(launcher.subprocess, 'Popen', return_value=child), \
                 mock.patch.object(launcher, 'process_identity', return_value=dict(expected, pid=55)):
                result = launcher.run_process(['ctest'], root, {}, root / 'out', root / 'err', expected, 1)
            self.assertTrue(result['still_running'])
            self.assertIsNone(result['exit_code'])
            self.assertIsNone(result['stdout_sha256'])
            child.terminate.assert_not_called()

    def test_non_windows_launcher_fails_closed(self):
        with mock.patch.object(launcher.sys, 'platform', 'linux'):
            with self.assertRaises(launcher.LauncherError): launcher.current_identity()

    def test_subset_closes_against_full_tree_and_refuses_unreviewed_dependency(self):
        def case(name, properties=()):
            return {'name': name, 'command': ['C:/kit/test.exe'], 'properties': list(properties)}
        def doc(items): return {'kind': 'ctestInfo', 'tests': items}
        before = case('before')
        target = case('target', [{'name': 'DEPENDS', 'value': ['before']}])
        full = doc([before, target]); filtered = doc([target])
        suite = {'id': 'example', 'kind': 'ctest'}
        approved = {'status': 'approved', 'reason': 'independent audit', 'evidence': ['audit'], 'group': 'safe'}
        rejected = {'status': 'safety_unreviewed', 'reason': 'not reviewed', 'evidence': ['audit'], 'group': 'other'}
        decisions = {'example': {'before': rejected, 'target': approved}}
        with self.assertRaises(launcher.review.ReviewError):
            launcher.selection_plan([suite], {'example': full}, {'example': filtered}, decisions, 'full')
        planned = launcher.selection_plan([suite], {'example': full}, {'example': filtered}, decisions, 'reviewed-subset')
        self.assertEqual(planned['example']['selected'], set())
        self.assertEqual(planned['example']['unrun'][0]['case'], 'target')
        decisions['example']['before'] = approved
        planned = launcher.selection_plan([suite], {'example': full}, {'example': filtered}, decisions, 'reviewed-subset')
        self.assertEqual(planned['example']['selected'], {'before', 'target'})

    def test_filtered_baseline_must_match_full_source_metadata(self):
        full = {'kind': 'ctestInfo', 'tests': [{'name': 'a', 'command': ['a'], 'properties': []}]}
        filtered = {'kind': 'ctestInfo', 'tests': [{'name': 'a', 'command': ['different'], 'properties': []}]}
        decisions = {'x': {'a': {'status': 'approved', 'reason': 'ok', 'evidence': ['audit'], 'group': 'g'}}}
        with self.assertRaises(launcher.LauncherError):
            launcher.selection_plan([{'id': 'x', 'kind': 'ctest'}], {'x': full}, {'x': filtered}, decisions, 'full')

    def test_missing_unselected_fixture_does_not_block_closed_selected_case(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / 'b').mkdir(); (root / 'b/good.exe').write_bytes(b'exe')
            output = root / 'r'; output.mkdir()
            logical = r'C:\Testing\n\123456789abc'
            def case(name, extra):
                return {'name': name, 'config': 'RelWithDebInfo',
                        'command': [logical + r'\b\good.exe', *extra],
                        'properties': [{'name': 'WORKING_DIRECTORY', 'value': logical + r'\b'}]}
            full = {'kind': 'ctestInfo', 'tests': [case('safe', []), case('unrun', [logical + r'\s\missing.fixture'])]}
            baseline = output / 'selected.json'
            launcher.write_json_new(baseline, launcher.selected_document(full, {'safe'}))
            launcher.audit_selected_discovery(root, logical, {'id': 'main'}, baseline, {'safe'}, output, 'RelWithDebInfo')
            bad = output / 'bad.json'; launcher.write_json_new(bad, launcher.selected_document(full, {'unrun'}))
            with self.assertRaises(launcher.audit.AuditError):
                launcher.audit_selected_discovery(root, logical, {'id': 'main'}, bad, {'unrun'}, output, 'RelWithDebInfo')

    def test_main_and_i18n_cannot_hide_a_full_tree_registration(self):
        first = {'name': 'RuntimeCatalogLanguageTest', 'command': ['test'], 'properties': []}
        sentinel = {'name': 'omitted_sentinel', 'command': ['test'], 'properties': []}
        full = {'kind': 'ctestInfo', 'tests': [first, sentinel]}
        incomplete = {'kind': 'ctestInfo', 'tests': [first]}
        decision = {'status': 'approved', 'reason': 'audit', 'evidence': ['audit'], 'group': 'safe'}
        for name in ('main', 'i18n'):
            for mode in ('full', 'reviewed-subset'):
                with self.subTest(name=name, mode=mode), self.assertRaises(launcher.LauncherError):
                    launcher.selection_plan([{'id': name, 'kind': 'ctest'}], {name: full}, {name: incomplete},
                                            {name: {'RuntimeCatalogLanguageTest': decision, 'omitted_sentinel': decision}}, mode)

    def test_one_unclosed_group_does_not_block_an_independent_reviewed_group(self):
        def case(name, props=()): return {'name': name, 'command': ['test'], 'properties': list(props)}
        doc = {'kind': 'ctestInfo', 'tests': [case('unsafe'), case('blocked', [{'name': 'DEPENDS', 'value': ['unsafe']}]),
                                              case('independent')]}
        def decision(status, group):
            return {'status': status, 'reason': 'audit', 'evidence': ['audit'], 'group': group}
        decisions = {'main': {'unsafe': decision('safety_unreviewed', 'unsafe'),
                              'blocked': decision('approved', 'first'), 'independent': decision('approved', 'second')}}
        result = launcher.selection_plan([{'id': 'main', 'kind': 'ctest'}], {'main': doc}, {'main': doc},
                                         decisions, 'reviewed-subset')['main']
        self.assertEqual(result['selected'], {'independent'})
        self.assertEqual({row['case'] for row in result['unrun']}, {'unsafe', 'blocked'})

    def test_unreviewed_discovery_skips_only_its_own_tree(self):
        doc = {'kind': 'ctestInfo', 'tests': [{'name': 'case', 'command': ['test'], 'properties': []}]}
        suites = [{'id': 'one', 'kind': 'ctest'}, {'id': 'two', 'kind': 'ctest'}]
        decision = {'status': 'approved', 'reason': 'audit', 'evidence': ['audit'], 'group': 'safe'}
        docs = {'one': doc, 'two': doc}; decisions = {'one': {'case': decision}, 'two': {'case': decision}}
        gates = {'one': {'status': 'safety_unreviewed', 'reason': 'static initializers unresolved',
                         'evidence': [{'path': 'audit.txt'}]}, 'two': {'status': 'approved'}}
        result = launcher.selection_plan(suites, docs, docs, decisions, 'reviewed-subset', gates)
        self.assertEqual(result['one']['selected'], set())
        self.assertEqual(result['one']['unrun'][0]['status'], 'safety_unreviewed')
        self.assertEqual(result['two']['selected'], {'case'})
        with self.assertRaises(launcher.LauncherError):
            launcher.selection_plan(suites, docs, docs, decisions, 'full', gates)

    def test_real_app_cases_cannot_be_approved_by_a_review_label_alone(self):
        docs = {'main': {'kind': 'ctestInfo', 'tests': [
            {'name': 'ArduPilotLayoutRestoreTest', 'command': ['python', 'check_ardupilot_layout.py'], 'properties': []},
            {'name': 'WindowsApplicationContract', 'command': ['python', 'verify_windows_application.py'], 'properties': []},
            {'name': 'safe', 'command': ['test'], 'properties': []}]}}
        approved = {'status': 'approved', 'reason': 'profile', 'evidence': ['review'], 'group': 'g'}
        decisions = {'main': {case['name']: dict(approved) for case in docs['main']['tests']}}
        launcher.block_unclosed_real_app_cases(docs, decisions)
        self.assertEqual(decisions['main']['safe']['status'], 'approved')
        for name in ('ArduPilotLayoutRestoreTest', 'WindowsApplicationContract'):
            self.assertEqual(decisions['main'][name]['status'], 'safety_unreviewed')
        decisions = {'main': {case['name']: dict(approved) for case in docs['main']['tests']}}
        launcher.block_unclosed_real_app_cases(docs, decisions, guard_ready=True)
        self.assertEqual(decisions['main']['ArduPilotLayoutRestoreTest']['status'], 'approved')

    def test_renamed_real_app_script_cannot_bypass_guard_case_identity(self):
        docs = {'main': {'kind': 'ctestInfo', 'tests': [
            {'name': 'renamed', 'command': ['python', 'check_ardupilot_layout.py'], 'properties': []}]}}
        decisions = {'main': {'renamed': {'status': 'approved', 'reason': 'audit', 'evidence': [], 'group': 'g'}}}
        launcher.block_unclosed_real_app_cases(docs, decisions, guard_ready=True)
        self.assertEqual(decisions['main']['renamed']['status'], 'safety_unreviewed')

    def test_app_guard_requires_actual_dedicated_ci_build_and_ctest_evidence(self):
        for defect in ('none', 'unrelated_executable', 'missing_test_dir', 'spoofed_binary', 'missing_case', 'skip'):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve(); config = 'RelWithDebInfo'
                paths = {'app_guard_probe': 'b/app-marker-probe/RelWithDebInfo/native_app_marker_probe.exe',
                         'app_guard_validation': '_bundle/guard.json', 'application': 'b/app.exe',
                         'qt': 'q', 'ctest': 't/cmake/bin/ctest.exe'}
                tree = root / 'b/app-marker-probe'; source = root / 's/scripts/windows/native_app_marker_probe'
                output = tree / config
                exe_names = {'probe': 'native_app_marker_probe.exe', 'policy_test': 'marker_probe_policy_test.exe',
                             'windows_test': 'marker_probe_windows_tests.exe', 'process_fixture': 'plotjuggler_marker_test_fixture.exe'}
                names = ('CMakeLists.txt', 'main.cpp', 'policy.cpp', 'policy.h', 'tests/policy_test.cpp',
                         'tests/windows_probe_test.cpp', 'tests/known_process_fixture.cpp')
                def write(relative, data):
                    path = root / relative; path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(data if isinstance(data, bytes) else data.encode()); return path
                for name in names: write('s/scripts/windows/native_app_marker_probe/' + name, name)
                for name in exe_names.values(): write('b/app-marker-probe/' + config + '/' + name, name)
                for name in ('b/app.exe', 'q/bin/Qt6Core.dll', 't/cmake/bin/ctest.exe', 't/cmake/bin/cmake.exe'):
                    write(name, name)
                identities = {key: launcher.sha256(output / name) for key, name in exe_names.items()}
                identity = {'schema': 1, 'role': 'app-marker-probe', 'source_sha': 'a' * 40, 'source_tree': 'b' * 40,
                            'configuration': config, 'source_dir': 's/scripts/windows/native_app_marker_probe',
                            'build_tree': 'b/app-marker-probe', 'qt_core_sha256': launcher.sha256(root / 'q/bin/Qt6Core.dll'),
                            'cmake_cache_sha256': 'c' * 64, 'executables_sha256': identities}
                if defect == 'spoofed_binary': identity['executables_sha256']['windows_test'] = 'd' * 64
                write('_bundle/build-id.json', json.dumps(identity))
                tests = [{'name': 'marker_probe_policy', 'command': [str(output / exe_names['policy_test'])],
                          'properties': [{'name': 'WORKING_DIRECTORY', 'value': str(tree)}]}]
                for suffix in ('identity', 'marker_paths', 'access_denied', 'processes', 'qt', 'cli'):
                    tests.append({'name': 'marker_probe_windows_' + suffix, 'command': [str(output / exe_names['windows_test']), suffix],
                                  'properties': [{'name': 'WORKING_DIRECTORY', 'value': str(tree)}]})
                if defect == 'unrelated_executable':
                    unrelated = write('unrelated/always-pass.exe', b'pass')
                    tests[1]['command'][0] = str(unrelated)
                if defect == 'missing_case': tests.pop()
                discovery = json.dumps({'kind': 'ctestInfo', 'tests': tests})
                junit = root / '_bundle/junit.xml'
                case_xml = lambda x: f'<testcase name="{x["name"]}" status="run"/>'
                result_xml = '<testsuite>' + ''.join(case_xml(x) for x in tests) + '</testsuite>'
                if defect == 'skip': result_xml = result_xml.replace('status="run"/>', 'status="notrun"><skipped message="SKIP_RETURN_CODE=77"/></testcase>', 1)
                write('_bundle/junit.xml', result_xml)
                cmake, ctest = root / 't/cmake/bin/cmake.exe', root / paths['ctest']
                commands = {'configure': [cmake, '-S', source, '-B', tree, '-G', 'Ninja Multi-Config', '-DCMAKE_PREFIX_PATH=' + str(root / 'q'), '-DCMAKE_MAKE_PROGRAM=ninja'],
                            'build': [cmake, '--build', tree, '--config', config],
                            'discovery': [ctest, '--test-dir', tree, '-C', config, '--show-only=json-v1'],
                            'execution': [ctest, '--test-dir', tree, '-C', config, '--no-tests=error', '--verbose',
                                          '--test-output-size-passed', '1073741824', '--test-output-size-failed', '1073741824', '--output-junit', junit]}
                if defect == 'missing_test_dir': commands['execution'] = [ctest, '-C', config, '--no-tests=error', '--output-junit', junit]
                record = {'schema': 2, 'source_sha': 'a' * 40, 'source_tree': 'b' * 40, 'configuration': config,
                          'platform': 'windows', 'runner_environment': 'github-hosted', 'build_identity': '_bundle/build-id.json',
                          'probe_sha256': identities['probe'], 'qt_core_sha256': launcher.sha256(root / 'q/bin/Qt6Core.dll'),
                          'application_sha256': launcher.sha256(root / 'b/app.exe'), 'junit': '_bundle/junit.xml'}
                for phase, argv in commands.items():
                    stdout = write('_bundle/' + phase + '.stdout', discovery if phase == 'discovery' else phase)
                    stderr = write('_bundle/' + phase + '.stderr', '')
                    process = {'exit_code': 0, 'still_running': False, 'argv': [str(x) for x in argv], 'cwd': str(root),
                               'stdout_sha256': launcher.sha256(stdout), 'stderr_sha256': launcher.sha256(stderr)}
                    write('_bundle/' + phase + '.json', json.dumps(process))
                    for part, suffix in (('process', '.json'), ('stdout', '.stdout'), ('stderr', '.stderr')):
                        record[phase + '_' + part] = '_bundle/' + phase + suffix
                write('_bundle/guard.json', json.dumps(record))
                manifest = {'files': [{'path': file.relative_to(root).as_posix()} for file in root.rglob('*') if file.is_file()]}
                ok, reason = launcher.checked_app_guard(root, paths, manifest, 'a' * 40, 'b' * 40, config)
                self.assertEqual(ok, defect == 'none', reason)

    def test_app_guard_environment_override_blocks_only_that_case(self):
        doc = {'kind': 'ctestInfo', 'tests': [{'name': 'WindowsApplicationContract',
               'properties': [{'name': 'ENVIRONMENT', 'value': ['TEMP=C:/outside']}]}]}
        decisions = {'main': {'WindowsApplicationContract': {'status': 'approved', 'reason': 'audit', 'evidence': [], 'group': 'app'}}}
        launcher.block_guard_environment_overrides({'main': doc}, decisions)
        self.assertEqual(decisions['main']['WindowsApplicationContract']['status'], 'safety_unreviewed')

    def test_all_selection_receipts_exist_before_execution_and_uncertainty_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            doc = {'kind': 'ctestInfo', 'tests': [{'name': 'one', 'command': ['test'], 'properties': []}]}
            suites = [{'id': 'main', 'tree': 'b'}, {'id': 'i18n', 'tree': 'i'}]
            prepared = {'main': {'selected': {'one'}, 'unrun': [], 'desired': {'one'}},
                        'i18n': {'selected': set(), 'unrun': [{'case': 'one', 'status': 'condition_missing',
                                 'reason': 'no service'}], 'desired': {'one'}}}
            progress = launcher.initialize_execution_plan(root, suites, prepared, {'main': doc, 'i18n': doc}, 'reviewed-subset')
            self.assertTrue((root / 'main/selection.json').is_file())
            self.assertTrue((root / 'i18n/selection.json').is_file())
            self.assertTrue((root / 'execution-plan.json').is_file())
            launcher.mark_process_start(root / 'main', 'discovery', ['ctest', '--show-only=json-v1'], root)
            marker = json.loads((root / 'main/discovery-started.json').read_text(encoding='utf-8'))
            self.assertIn('uncertain', marker['outcome'])
            with self.assertRaises(FileExistsError):
                launcher.mark_process_start(root / 'main', 'discovery', ['ctest'], root)
            for phase, expected in [('not_started', 'not_started'), ('discovery_still_running', 'discovery_outcome_uncertain'),
                                    ('execution_started', 'execution_outcome_uncertain'),
                                    ('execution_still_running', 'execution_outcome_uncertain'),
                                    ('execution_finished', 'process_exited_but_case_outcomes_unverified')]:
                progress['main']['phase'] = phase
                self.assertEqual(launcher.incomplete_receipt(progress)['suites']['main']['case_status'], expected)

    def test_system_powershell_requires_exact_reviewed_file_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            windows = Path(directory); shell = windows / 'System32/WindowsPowerShell/v1.0/powershell.exe'
            shell.parent.mkdir(parents=True); shell.write_bytes(b'known')
            digest = hashlib.sha256(b'known').hexdigest()
            self.assertEqual(launcher.checked_system_powershell(windows, digest), shell)
            for wrong in ('f' * 64, 'not-a-hash'):
                with self.assertRaises(launcher.LauncherError): launcher.checked_system_powershell(windows, wrong)
            shell.write_bytes(b'changed')
            with self.assertRaises(launcher.LauncherError): launcher.checked_system_powershell(windows, digest)


if __name__ == '__main__':
    unittest.main()
