# SPDX-License-Identifier: MPL-2.0
"""Synthetic closure inputs, not a Windows run or VM safety evidence."""
import copy
import contextlib
import hashlib
import io
import json
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('native_closure', ROOT / 'scripts/windows/verify_native_ci_closure.py')
closure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(closure)
SHA, TREE = '1' * 40, '2' * 40
LOGICAL = 'C:\\Test\\n\\' + SHA[:12]


def test_case(name, executable, args=(), **properties):
    return {'name': name, 'command': [LOGICAL + '\\' + executable.replace('/', '\\'), *args],
            'properties': [{'name': key, 'value': value} for key, value in properties.items()]}


def fixture():
    src = ['s/policy.py', 's/exact.cpp', 's/runner.cpp']
    paths = src + ['i/test.exe', 'b/tf.exe', 'q/6.12.0/msvc2022_64/plugins/platforms/qoffscreen.dll']
    exact = {'suite': 'i18n', 'case': 'exact', 'executable': 'i/test.exe', 'reason': 'Reviewed exact case',
             'evidence': ['s/exact.cpp'], 'source_files': ['s/exact.cpp'], 'dynamic_files': [], 'subprocesses': []}
    runner = {'suite': 'main', 'executable': 'b/tf.exe', 'registration_kind': 'gtest-exact-filter',
              'name_prefix': 'tf.', 'reason': 'Reviewed whole TF source and direct in-process dependencies.',
              'evidence': ['s/runner.cpp'], 'source_files': ['s/runner.cpp'], 'dynamic_files': [],
              'subprocesses': [], 'exclusions': [], 'value_parameters': {}}
    policy = {'schema': 2, 'suite_ids': ['main', 'i18n'], 'unreviewed_evidence': ['s/policy.py'],
              'reviewed_source_sha256': {name: hashlib.sha256(name.encode()).hexdigest() for name in src},
              'approved_cases': [exact], 'approved_runners': [runner]}
    docs = {'i18n': {'kind': 'ctestInfo', 'tests': [test_case('exact', 'i/test.exe'), test_case('other', 'i/test.exe')]},
            'main': {'kind': 'ctestInfo', 'tests': [test_case('tf.Math.Safe', 'b/tf.exe',
                        ['--gtest_filter=Math.Safe', '--gtest_also_run_disabled_tests']),
                        test_case('tf.Math.Unavailable', 'b/tf.exe',
                        ['--gtest_filter=Math.Unavailable', '--gtest_also_run_disabled_tests'])]}}
    coverage = [{'suite': 'main', 'case': 'tf.Math.Unavailable', 'status': 'condition_missing',
                 'reason': 'Fixture unavailable'}]
    plan = {'origins': {}, 'files': [{'destination': name, 'sha256': hashlib.sha256(name.encode()).hexdigest()} for name in paths]}
    return policy, docs, paths, coverage, plan


class PartitionTests(unittest.TestCase):
    def derive(self, policy, docs, paths, coverage):
        return closure.derive_partition(policy, docs, SHA, TREE, LOGICAL, paths, coverage)

    def test_exact_and_reviewed_runner_expand_but_other_cases_are_partitioned(self):
        policy, docs, paths, coverage, _ = fixture()
        result = self.derive(policy, docs, paths, coverage)
        groups = {suite['id']: {g['cases'][0]: g['status'] for g in suite['groups']} for suite in result['suites']}
        self.assertEqual(groups['main'], {'tf.Math.Safe': 'approved', 'tf.Math.Unavailable': 'condition_missing'})
        self.assertEqual(groups['i18n'], {'exact': 'approved', 'other': 'safety_unreviewed'})

    def test_unknown_or_disabled_approval_cannot_be_certified(self):
        for defect in ('wrong-executable', 'duplicate', 'source'):
            policy, docs, paths, coverage, _ = fixture()
            if defect == 'wrong-executable': docs['i18n']['tests'][0]['command'][0] = LOGICAL + '\\i\\other.exe'
            elif defect == 'duplicate': policy['approved_cases'].append(copy.deepcopy(policy['approved_cases'][0]))
            elif defect == 'source': policy['approved_cases'][0]['evidence'] = ['s/missing.cpp']
            with self.subTest(defect=defect), self.assertRaises(closure.ClosureError):
                self.derive(policy, docs, paths, coverage)

    def test_unregistered_reviewed_targets_are_reported_without_fabricating_cases(self):
        policy,docs,paths,coverage,_=fixture()
        docs['i18n']['tests']=[docs['i18n']['tests'][1]]
        docs['main']['tests']=[test_case('other','i/test.exe')]
        result=self.derive(policy,docs,paths,[])
        self.assertEqual(len(result['unregistered']),2)
        self.assertTrue(all(x['status']=='condition_missing' for x in result['unregistered']))
        self.assertEqual({g['cases'][0] for s in result['suites'] for g in s['groups']},{'other'})

    def test_missing_or_disabled_reviewed_cases_are_explicitly_unrun(self):
        for defect in ('disabled', 'missing-condition', 'missing-executable'):
            with self.subTest(defect=defect):
                policy, docs, paths, coverage, _ = fixture()
                if defect == 'disabled':
                    docs['i18n']['tests'][0]['properties'].append({'name': 'DISABLED', 'value': True})
                elif defect == 'missing-condition':
                    coverage.append({'suite': 'i18n', 'case': 'exact', 'status': 'condition_missing', 'reason': 'missing fixture'})
                else:
                    paths.remove('i/test.exe')
                result = self.derive(policy, docs, paths, coverage)
                group = next(g for suite in result['suites'] if suite['id'] == 'i18n'
                             for g in suite['groups'] if g['cases'] == ['exact'])
                self.assertEqual(group['status'], 'disabled' if defect == 'disabled' else 'condition_missing')
                self.assertTrue(group['reason'])

    def test_missing_runner_is_not_a_pass_and_does_not_block_other_suite(self):
        policy, docs, paths, coverage, _ = fixture()
        paths.remove('b/tf.exe')
        result = self.derive(policy, docs, paths, coverage)
        main = next(x for x in result['suites'] if x['id'] == 'main')
        group = next(x for x in main['groups'] if x['cases'] == ['tf.Math.Safe'])
        self.assertEqual(group['status'], 'condition_missing')
        self.assertIn('b/tf.exe', group['reason'])
        i18n = next(x for x in result['suites'] if x['id'] == 'i18n')
        self.assertEqual(next(x for x in i18n['groups'] if x['cases'] == ['exact'])['status'], 'approved')

    def test_gtest_filter_must_select_one_reviewed_case(self):
        for argv in (['--gtest_filter=*', '--gtest_also_run_disabled_tests'],
                     ['--gtest_filter=Math.Other', '--gtest_also_run_disabled_tests'],
                     ['--gtest_filter=Math.Safe'],
                     ['--gtest_filter=Math.Safe', '--gtest_also_run_disabled_tests', '--extra']):
            policy, docs, paths, coverage, _ = fixture()
            docs['main']['tests'][0]['command'][1:] = argv
            with self.subTest(argv=argv), self.assertRaises(closure.ClosureError):
                self.derive(policy, docs, paths, coverage)

    def test_runner_only_policy_works_but_no_approval_fails(self):
        policy, docs, paths, coverage, _ = fixture()
        policy['approved_cases'] = []
        result = self.derive(policy, docs, paths, coverage)
        self.assertTrue(any(g['status'] == 'approved' for x in result['suites'] for g in x['groups']))
        policy['approved_runners'] = []
        with self.assertRaises(closure.ClosureError): self.derive(policy, docs, paths, coverage)

    def test_source_reviewed_gtest_bool_parameters_map_to_literal_filters(self):
        policy, docs, paths, coverage, _ = fixture()
        policy['approved_runners'][0]['value_parameters'] = {'WithBool': {'0': 'false', '1': 'true'}}
        docs['main']['tests'].append(test_case('tf.WithBool.Same/false', 'b/tf.exe',
                ['--gtest_filter=WithBool.Same/0', '--gtest_also_run_disabled_tests']))
        groups = self.derive(policy, docs, paths, coverage)['suites'][0]['groups']
        self.assertEqual(next(x for x in groups if x['cases'] == ['tf.WithBool.Same/false'])['status'], 'approved')
        docs['main']['tests'][-1]['command'][1] = '--gtest_filter=WithBool.Same/1'
        with self.assertRaises(closure.ClosureError): self.derive(policy, docs, paths, coverage)

    def test_named_parameters_require_exact_source_reviewed_pretty_name(self):
        policy, docs, paths, coverage, _ = fixture()
        policy['approved_runners'][0]['value_parameters'] = {'Formats/Color': {'Red':'Red','Blue':'Blue'}}
        docs['main']['tests'].append(test_case('tf.Formats/Color.Render/Red  # GetParam() = Red','b/tf.exe',
                              ['--gtest_filter=Formats/Color.Render/Red','--gtest_also_run_disabled_tests']))
        result = self.derive(policy,docs,paths,coverage)
        groups = next(x['groups'] for x in result['suites'] if x['id']=='main')
        self.assertEqual(next(x for x in groups if x['cases'][0].startswith('tf.Formats/'))['status'],'approved')
        docs['main']['tests'][-1]['name'] = 'tf.Formats/Color.Render/Red  # GetParam() = Unknown'
        with self.assertRaises(closure.ClosureError): self.derive(policy,docs,paths,coverage)
        docs['main']['tests'][-1]['name'] = 'tf.Formats/Color.Render/Other  # GetParam() = Other'
        docs['main']['tests'][-1]['command'][1] = '--gtest_filter=Formats/Color.Render/Other'
        with self.assertRaises(closure.ClosureError): self.derive(policy,docs,paths,coverage)

    def test_rhi_runner_requires_actual_exact_d3d11_environment(self):
        policy,docs,paths,coverage,_=fixture()
        policy['approved_runners'][0]['name_prefix']='tf.d3d11.'
        docs['main']['tests']=[test_case('tf.d3d11.Math.Safe','b/tf.exe',
            ['--gtest_filter=Math.Safe','--gtest_also_run_disabled_tests'],ENVIRONMENT=['PJ_GRAPHICS_API=d3d11'])]
        result=self.derive(policy,docs,paths,[])
        self.assertTrue(any(x['status']=='approved' for x in result['suites'][0]['groups']))
        docs['main']['tests'][0]['properties'][0]['value']=['PJ_GRAPHICS_API=d3d11','PJ_UPDATE_POINTCLOUD_GOLDENS=1']
        with self.assertRaises(closure.ClosureError): self.derive(policy,docs,paths,[])

    def test_explicit_runner_exclusion_has_a_specific_reason(self):
        policy, docs, paths, coverage, _ = fixture()
        policy['approved_runners'][0]['exclusions'] = [{'case': 'tf.Math.Unavailable',
            'status': 'condition_missing', 'reason': 'Requires a Debug build.'}]
        coverage.clear()
        groups = self.derive(policy, docs, paths, coverage)['suites'][0]['groups']
        result = next(x for x in groups if x['cases'] == ['tf.Math.Unavailable'])
        self.assertEqual((result['status'], result['reason']), ('condition_missing', 'Requires a Debug build.'))

    def test_unapproved_fixture_does_not_enter_approved_selection(self):
        policy, docs, paths, coverage, _ = fixture()
        docs['i18n']['tests'][0]['properties'].append({'name': 'DEPENDS', 'value': ['other']})
        with self.assertRaisesRegex(closure.ClosureError, 'fixture or DEPENDS'):
            self.derive(policy, docs, paths, coverage)

    def test_source_set_comes_from_exact_git_records(self):
        tracked = ['LICENSE', 'p/file', '.github/conan/source-backup/' + 'a' * 64]
        self.assertEqual(closure.source_paths_match(tracked, ['s/p/file', 's/LICENSE', 'b/test.exe']), ['s/p/file', 's/LICENSE'])
        for paths in (['s/LICENSE'], ['s/LICENSE', 's/p/file', 's/p/FILE'], ['s/LICENSE', 's/../outside'], ['s/LICENSE', None]):
            with self.subTest(paths=paths), self.assertRaises(closure.ClosureError):
                closure.source_paths_match(tracked, paths)

    def test_exact_generated_source_paths_only(self):
        tracked = ['LICENSE', 'p/file']
        generated = list(closure.SYNTHETIC_MEDIA_PATHS)
        destinations = ['s/LICENSE', 's/p/file', *generated, 'b/test.exe']
        self.assertEqual(len(closure.source_paths_match(tracked, destinations, generated)), 6)
        for defect in ('missing', 'extra', 'tracked_fixture', 'case_collision', 'partial_exception'):
            with self.subTest(defect=defect):
                actual = list(destinations); index = list(tracked); exceptions = list(generated)
                if defect == 'missing': actual.remove(generated[0])
                elif defect == 'extra': actual.append('s/other.untracked')
                elif defect == 'tracked_fixture': index.append(generated[0][2:])
                elif defect == 'case_collision': actual.append(generated[0].upper())
                else: exceptions.pop()
                with self.assertRaises(closure.ClosureError):
                    closure.source_paths_match(index, actual, exceptions)

    def test_status_and_index_fail_closed(self):
        rows = ['?? ' + path[2:] for path in closure.SYNTHETIC_MEDIA_PATHS]
        closure.verify_generated_source_status('\0'.join(rows) + '\0')
        for bad in ('', '\0'.join(rows), '\0'.join(rows[:-1])+'\0',
                    '\0'.join(rows+[rows[0]])+'\0', '\0'.join(rows+[' M CMakeLists.txt'])+'\0'):
            with self.subTest(bad=bad), self.assertRaises(closure.ClosureError):
                closure.verify_generated_source_status(bad)
        good = '100644 ' + 'a'*40 + ' 0\tLICENSE\0' + '100755 ' + 'b'*40 + ' 0\tbin/run\0'
        self.assertEqual(closure.parse_tracked_source(good), ['LICENSE', 'bin/run'])
        for bad in (good[:-1], good.replace('100644', '120000'), good.replace(' 0\t', ' 1\t', 1),
                    good.replace('bin/run', '../bad')):
            with self.subTest(bad=bad), self.assertRaises(closure.ClosureError):
                closure.parse_tracked_source(bad)

    def test_csv_dynamic_path_comes_from_exact_prebuilt_identity(self):
        policy, docs, paths, coverage, plan = fixture()
        with tempfile.TemporaryDirectory() as directory:
            plugin = 'b/csv-prefix/lib/plotjuggler/plugins/csv-loader/runtime.dll'
            plugin_hash = hashlib.sha256(b'csv bytes').hexdigest()
            identity = {'schema': 1, 'source_sha': SHA, 'source_tree': TREE, 'configuration': 'RelWithDebInfo',
                        'plugin': LOGICAL + '\\' + plugin.replace('/', '\\'), 'plugin_sha256': plugin_hash}
            file = Path(directory) / 'identity.json'; file.write_text(json.dumps(identity), encoding='utf-8')
            plan['origins'] = {'fixture': {'root': directory}}
            plan['files'].extend([{'origin': 'fixture', 'source': 'identity.json',
                'destination': 'b/native-kit/csv-prebuilt.json', 'sha256': hashlib.sha256(file.read_bytes()).hexdigest()},
                {'origin': 'fixture', 'source': 'runtime.dll', 'destination': plugin, 'sha256': plugin_hash}])
            policy['approved_cases'][0]['dynamic_files'] = [{'selector': 'csv-prebuilt-plugin', 'role': 'plugin'}]
            partition = self.derive(policy, docs, paths, coverage)
            inventory = closure.derive_dynamic_inventory(policy, partition, plan, docs, LOGICAL)
            scope = next(x for x in inventory['scopes'] if x['suite'] == 'i18n')
            self.assertEqual(scope['dynamic_files'], [{'path': plugin, 'sha256': plugin_hash, 'role': 'plugin'}])
            file.write_text(json.dumps(dict(identity, plugin_sha256='0'*64)), encoding='utf-8')
            with self.assertRaises(closure.ClosureError):
                closure.derive_dynamic_inventory(policy, partition, plan, docs, LOGICAL)

    def test_source_analysis_inventory_is_bound_to_selected_cases_and_hashes(self):
        policy, docs, paths, coverage, plan = fixture()
        policy['approved_runners'][0]['dynamic_files'] = [{'path': paths[-1], 'role': 'qt-plugin'}]
        partition = self.derive(policy, docs, paths, coverage)
        result = closure.derive_dynamic_inventory(policy, partition, plan, docs, LOGICAL)
        self.assertEqual(result['basis'], 'source-analysis')
        self.assertEqual({(x['suite'], x['cases'][0]) for x in result['scopes']}, {('main', 'tf.Math.Safe'), ('i18n', 'exact')})
        self.assertEqual(next(x for x in result['scopes'] if x['suite'] == 'main')['dynamic_files'][0]['role'], 'qt-plugin')
        closure.verify_dynamic_inventory(result, copy.deepcopy(result))
        policy['reviewed_source_sha256']['s/runner.cpp'] = '0' * 64
        with self.assertRaises(closure.ClosureError): closure.derive_dynamic_inventory(policy, partition, plan, docs, LOGICAL)
        policy['reviewed_source_sha256']['s/runner.cpp'] = hashlib.sha256(b's/runner.cpp').hexdigest()
        altered = copy.deepcopy(result); altered['scopes'][0]['runner']['sha256'] = 'f' * 64
        with self.assertRaises(closure.ClosureError): closure.verify_dynamic_inventory(altered, result)
        plan['files'] = [x for x in plan['files'] if x['destination'] != paths[-1]]
        with self.assertRaises(closure.ClosureError): closure.derive_dynamic_inventory(policy, partition, plan, docs, LOGICAL)

    def test_unreviewed_bundled_seed_directory_must_really_be_empty(self):
        policy, docs, paths, coverage, plan = fixture()
        policy['approved_cases'][0]['absent_paths'] = ['b/pj_app/lib/plotjuggler/plugins']
        partition = self.derive(policy,docs,paths,coverage)
        closure.derive_dynamic_inventory(policy,partition,plan,docs,LOGICAL)
        plan['files'].append({'destination':'b/pj_app/lib/plotjuggler/plugins/unreviewed.dll','sha256':'a'*64})
        with self.assertRaises(closure.ClosureError):
            closure.derive_dynamic_inventory(policy,partition,plan,docs,LOGICAL)

    def test_locked_cpython_selector_uses_exact_graph_package_bytes(self):
        policy, docs, paths, coverage, plan = fixture()
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp); folder='c/p/python/p'; ref='cpython/3.12.7#'+'c'*32
            def put(relative, data):
                file=base/relative;file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(data)
                plan['files'].append({'origin':'local','source':relative,'destination':relative,
                                      'sha256':hashlib.sha256(data).hexdigest()})
            plan['origins']={'local':{'root':temp}}
            graph={'graph':{'nodes':{'1':{'context':'host','ref':ref,
                             'package_folder':LOGICAL+'\\'+folder.replace('/','\\')}}}}
            put('b/conan-install-graph.json',json.dumps(graph).encode())
            put('s/conan.lock',json.dumps({'requires':[ref]}).encode())
            put('s/.github/windows-native-kit/tool-pins.json',
                json.dumps({'artifacts':[{'name':'python','version':'3.12.10'}]}).encode())
            put(folder+'/bin/python312.dll',b'locked runtime')
            put(folder+'/bin/DLLs/unicodedata.pyd',b'locked unicodedata')
            put(folder+'/bin/Lib/encodings/__init__.py',b'encoding')
            put(folder+'/bin/Lib/os.py',b'os')
            probe='b/pj_scripting/RelWithDebInfo/pj_scripting_python_tests.exe'
            home=(LOGICAL+'\\'+folder.replace('/','\\')+'\\bin').replace('\\','/')
            probe_bytes=(home+'\0'+hashlib.sha256(b'locked runtime').hexdigest()+'\0'+
                         hashlib.sha256(b'locked unicodedata').hexdigest()+'\0').encode()
            put(probe,probe_bytes)
            policy['approved_cases'][0]['executable']=probe
            docs['i18n']['tests'][0]['command'][0]=LOGICAL+'\\'+probe.replace('/','\\')
            paths.append(probe)
            policy['approved_cases'][0]['dynamic_files']=[
                {'selector':'locked-cpython','artifact':'runtime-dll','role':'runtime-module'},
                {'selector':'locked-cpython','artifact':'unicodedata-extension','role':'runtime-module'},
                {'selector':'locked-cpython','artifact':'stdlib-encodings','role':'data'},
                {'selector':'locked-cpython','artifact':'stdlib-os','role':'data'}]
            partition=self.derive(policy,docs,paths,coverage)
            inventory=closure.derive_dynamic_inventory(policy,partition,plan,docs,LOGICAL)
            scope=next(x for x in inventory['scopes'] if x['suite']=='i18n')
            self.assertEqual(len(scope['dynamic_files']),4)
            extension=folder+'/bin/DLLs/unicodedata.pyd'
            self.assertIn({'path':extension, 'sha256':hashlib.sha256(b'locked unicodedata').hexdigest(),
                           'role':'runtime-module'},scope['dynamic_files'])
            self.assertFalse((base/folder/'bin/DLLs/math.pyd').exists())
            for defect in ('missing-extension', 'changed-extension', 'changed-recorded-hash', 'old-math-selector'):
                with self.subTest(defect=defect):
                    altered_plan=copy.deepcopy(plan); altered_policy=copy.deepcopy(policy)
                    if defect == 'missing-extension':
                        altered_plan['files']=[row for row in altered_plan['files'] if row['destination']!=extension]
                    elif defect in ('changed-extension', 'changed-recorded-hash'):
                        (base/extension).write_bytes(b'tampered unicodedata')
                        if defect == 'changed-recorded-hash':
                            next(row for row in altered_plan['files'] if row['destination']==extension)['sha256'] = (
                                hashlib.sha256(b'tampered unicodedata').hexdigest())
                    else:
                        altered_policy['approved_cases'][0]['dynamic_files'][1]['artifact']='math-extension'
                    try:
                        with self.assertRaises(closure.ClosureError):
                            closure.derive_dynamic_inventory(altered_policy,partition,altered_plan,docs,LOGICAL)
                    finally:
                        (base/extension).write_bytes(b'locked unicodedata')
            later_ref='cpython/3.12.17#'+'c'*32
            graph['graph']['nodes']['1']['ref']=later_ref
            for relative, data in (('b/conan-install-graph.json', json.dumps(graph).encode()),
                                   ('s/conan.lock', json.dumps({'requires':[later_ref]}).encode())):
                (base/relative).write_bytes(data)
                next(row for row in plan['files'] if row['destination']==relative)['sha256'] = hashlib.sha256(data).hexdigest()
            self.assertEqual(len(closure.derive_dynamic_inventory(policy,partition,plan,docs,LOGICAL)['scopes']),
                             len(inventory['scopes']))
            (base/folder/'bin/python312.dll').write_bytes(b'tampered')
            with self.assertRaises(closure.ClosureError):
                closure.derive_dynamic_inventory(policy,partition,plan,docs,LOGICAL)


class GeneratedMediaTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name); self.rows={}
        def put(path, data):
            target=self.root/path; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(data)
            self.rows[path]={'path':path,'sha256':hashlib.sha256(data).hexdigest()}
        self.put=put
        license_data=b'MCAP MIT license'
        put(closure.MEDIA_CONTROL+'MCAP-LICENSE',license_data)
        lock={'version':'2.1.1','license_sha256':hashlib.sha256(license_data).hexdigest()}
        sources={}
        for name, data in (('generate_media_fixtures.py',b'generator'),('mcap_fixture_generator.cpp',b'writer'),
                           ('mcap-source-lock.json',json.dumps(lock).encode())):
            put('s/scripts/native-fixtures/'+name,data); sources[name]=hashlib.sha256(data).hexdigest()
        files={}
        for name,path in zip(closure.SYNTHETIC_MEDIA_NAMES,closure.SYNTHETIC_MEDIA_PATHS):
            data=('synthetic '+name).encode(); put(path,data)
            files[name]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
        def video(width,height):
            return {'codec_name':'h264','pix_fmt':'yuv420p','width':width,'height':height,
                    'avg_frame_rate':'30/1','nb_read_frames':'120','duration':'4.000','has_b_frames':2}
        names=closure.SYNTHETIC_MEDIA_NAMES
        self.media={'schema':1,'synthetic':True,'files':files,'generator_sources':sources,'mcap_source':lock,
                    'semantics':{'video':{names[0]:video(640,480),names[1]:video(1920,1080)},
                      'mcap':{names[2]:{'channels':1,'messages_per_channel':90,'all_payloads_timestamps_sequences_validated':True},
                              names[3]:{'channels':4,'messages_per_channel':8400,'all_payloads_timestamps_sequences_validated':True}}}}
        self.write_control()

    def write_control(self):
        data=json.dumps(self.media).encode(); self.put(closure.MEDIA_CONTROL+'manifest.json',data)
        self.sha=hashlib.sha256(data).hexdigest()
        self.receipt={'schema':1,'source_sha':SHA,'source_tree':TREE,'manifest_sha256':self.sha,
                      'files':{path:self.media['files'][name] for name,path in
                               zip(closure.SYNTHETIC_MEDIA_NAMES,closure.SYNTHETIC_MEDIA_PATHS)}}
        self.put(closure.MEDIA_CONTROL+'generation-receipt.json',json.dumps(self.receipt).encode())

    def verify(self, expected=None, staged=True):
        return closure.verify_generated_media(self.root,SHA,TREE,self.sha if expected is None else expected,
                                               list(self.rows.values()) if staged else None)

    def test_verified_source_and_staged_manifest(self):
        self.assertEqual(self.verify()['manifest_sha256'],self.sha)
        self.assertEqual(len(self.verify(staged=False)['files']),4)

    def test_reject_untrusted_digest_and_changed_copied_input(self):
        with self.assertRaises(closure.ClosureError): self.verify('f'*64)
        (self.root/closure.SYNTHETIC_MEDIA_PATHS[0]).write_bytes(b'tampered')
        with self.assertRaises(closure.ClosureError): self.verify()

    def test_reject_wrong_source_semantics_license_and_stage_membership(self):
        for defect in ('generator','license','video','mcap','missing','extra','manifest-row'):
            with self.subTest(defect=defect):
                self.setUp()
                if defect=='generator': (self.root/'s/scripts/native-fixtures/generate_media_fixtures.py').write_bytes(b'altered')
                elif defect=='license': (self.root/(closure.MEDIA_CONTROL+'MCAP-LICENSE')).write_bytes(b'altered')
                elif defect=='video': self.media['semantics']['video'][closure.SYNTHETIC_MEDIA_NAMES[0]]['width']=854; self.write_control()
                elif defect=='mcap': self.media['semantics']['mcap'][closure.SYNTHETIC_MEDIA_NAMES[2]]['messages_per_channel']=89; self.write_control()
                elif defect=='missing': self.media['files'].pop(closure.SYNTHETIC_MEDIA_NAMES[0]); self.write_control_missing()
                elif defect=='extra': self.media['files']['extra.mp4']={'bytes':1,'sha256':'a'*64}; self.write_control()
                else: self.rows.pop(closure.SYNTHETIC_MEDIA_PATHS[0])
                with self.assertRaises(closure.ClosureError): self.verify()

    def write_control_missing(self):
        data=json.dumps(self.media).encode(); self.put(closure.MEDIA_CONTROL+'manifest.json',data)
        self.sha=hashlib.sha256(data).hexdigest(); self.receipt['manifest_sha256']=self.sha
        self.put(closure.MEDIA_CONTROL+'generation-receipt.json',json.dumps(self.receipt).encode())

    def test_independent_checkout_inventory_and_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            checkout=Path(directory); (checkout/'p').mkdir()
            (checkout/'LICENSE').write_bytes(b'license'); (checkout/'p/file').write_bytes(b'source')
            self.put('s/LICENSE',b'license'); self.put('s/p/file',b'source')
            index=('100644 '+'a'*40+' 0\tLICENSE\0'+'100644 '+'b'*40+' 0\tp/file\0').encode()
            def fake(argv,**kwargs):
                tail=argv[3:]
                if tail==['rev-parse','HEAD']: out=(SHA+'\n').encode()
                elif tail==['rev-parse','HEAD^{tree}']: out=(TREE+'\n').encode()
                elif tail[0]=='status': out=b''
                elif tail[0]=='ls-files': out=index
                else: self.fail('unexpected git command: '+repr(tail))
                return types.SimpleNamespace(returncode=0,stdout=out,stderr=b'')
            dest=['s/LICENSE','s/p/file',*closure.SYNTHETIC_MEDIA_PATHS]
            with mock.patch.object(closure.subprocess,'run',side_effect=fake):
                self.assertEqual(closure.verify_independent_checkout(self.root,checkout,SHA,TREE,dest,list(self.rows.values()))['tracked_files'],2)
                with self.assertRaises(closure.ClosureError):
                    closure.verify_independent_checkout(self.root,checkout,SHA,TREE,dest+['s/unplanned.py'],list(self.rows.values()))
                (checkout/'p/file').write_bytes(b'changed')
                with self.assertRaises(closure.ClosureError):
                    closure.verify_independent_checkout(self.root,checkout,SHA,TREE,dest,list(self.rows.values()))

    def test_staged_replay_checks_manifest_inventory_not_only_candidate(self):
        control='b/native-kit/closure-evidence/'
        self.put('s/LICENSE',b'license')
        candidate={'files':[{'destination':'s/LICENSE','sha256':self.rows['s/LICENSE']['sha256']}]}
        report={'source_sha':SHA,'source_tree':TREE,'logical_root':LOGICAL,'configuration':'RelWithDebInfo'}
        for name,value in (('candidate-plan.json',candidate),('candidate-report.json',report),('ci-policy.json',{})):
            self.put(control+name,json.dumps(value).encode())
        extra={'path':'s/unplanned.py','sha256':'a'*64}
        manifest={'files':[*self.rows.values(),extra], 'provenance':{
            'generated_fixtures':{'manifest_sha256':self.sha,'files':self.receipt['files']},
            'source_clean_scope':'tracked checkout clean; four generated fixture inputs are identified separately'}}
        with mock.patch.object(closure,'check_staged_receipt_integrity'), \
                mock.patch.object(closure,'verify_generated_media',return_value=manifest['provenance']['generated_fixtures']), \
                mock.patch.object(closure,'verify_independent_checkout',side_effect=closure.ClosureError('inventory checked')) as check, \
                mock.patch.dict(closure.os.environ,{'GITHUB_WORKSPACE':'/separate-checkout'}):
            with self.assertRaisesRegex(closure.ClosureError,'inventory checked'):
                closure.verify_staged_inputs(self.root,manifest,{}, {},SHA,TREE,LOGICAL,self.root)
            self.assertIn('s/unplanned.py',check.call_args.args[4])


class CMakeFileApiTests(unittest.TestCase):
    """Only synthetic JSON/PE-like bytes; these are not a CMake or Windows run."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.entries = {}; self.objects = {}
        self.reply = 'b/native-kit/codemodel/reply/'
        self.index = self.reply + 'index-2026-01-01T000000.json'

    def put(self, path, data):
        target = self.root / path; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        self.entries[path] = hashlib.sha256(data).hexdigest()

    def put_json(self, path, value):
        self.objects[path] = copy.deepcopy(value)
        self.put(path, json.dumps(value, ensure_ascii=False).encode('utf-8'))

    def prepare(self, name):
        self.name = name; rule = closure.CODEMODEL_RULES[name]
        self.policy = {'reviewed_source_sha256': {}}
        for source in (rule['cmake'], 's/' + rule['source'], 's/pj_runtime/CMakeLists.txt'):
            self.put(source, source.encode())
            self.policy['reviewed_source_sha256'][source] = self.entries[source]
        self.sdk = 'c/p/sdk/package'
        sdk_hashes = {}
        for relative in closure.SDK_FIXTURE_FILES:
            path = self.sdk + '/' + relative
            self.put(path, ('synthetic sdk ' + relative).encode())
            sdk_hashes[relative] = self.entries[path]
        patcher = mock.patch.dict(closure.SDK_FIXTURE_FILES, sdk_hashes, clear=True)
        patcher.start(); self.addCleanup(patcher.stop)
        runner_id = rule['target'] + '::@runner'
        refs = [{'name': rule['target'], 'id': runner_id, 'jsonFile': 'target-runner.json'}]
        definitions, dependencies, literals = [], [], []
        for number, (macro, target) in enumerate(rule['definitions'].items()):
            target_id = target + '::@fixture'
            path = 'b/fixture/RelWithDebInfo/' + target + '.dll'
            literal = (LOGICAL + '\\' + path).replace('\\', '/')
            definitions.append({'define': macro + '=\"' + literal + '\"'})
            dependencies.append({'id': target_id})
            refs.append({'name': target, 'id': target_id, 'jsonFile': 'target-fixture' + str(number) + '.json'})
            self.put(path, ('synthetic DLL ' + target).encode())
            source_kind, source = closure.CODEMODEL_PLUGIN_SOURCES[target]
            source_path = (self.sdk + '/' if source_kind == 'sdk' else 's/') + source
            if source_kind == 'source':
                self.put(source_path, source_path.encode())
                self.policy['reviewed_source_sha256'][source_path] = self.entries[source_path]
            source_record = (LOGICAL + '\\' + source_path).replace('\\', '/') if source_kind == 'sdk' else source
            self.put_json(self.reply + 'target-fixture' + str(number) + '.json',
                          {'name': target, 'id': target_id, 'type': 'SHARED_LIBRARY',
                           'artifacts': [{'path': path[2:]}, {'path': path[2:-4] + '.lib'}],
                           'sources': [{'path': source_record, 'compileGroupIndex': 0}]})
            literals.append(literal.encode('utf-16-le') + b'\0\0')
        self.put(rule['runner'], b'synthetic exe\0' + b'\0'.join(literals))
        self.put_json(self.reply + 'target-runner.json',
                      {'name': rule['target'], 'id': runner_id, 'type': 'EXECUTABLE',
                       'artifacts': [{'path': rule['runner'][2:]}], 'dependencies': dependencies,
                       'sources': [{'path': rule['source'], 'compileGroupIndex': 0},
                                   {'path': 'generated/mocs_compilation.cpp', 'isGenerated': True, 'compileGroupIndex': 0}],
                       'compileGroups': [{'language': 'CXX', 'defines': definitions}]})
        self.put_json(self.reply + 'codemodel-v2-test.json',
                      {'kind': 'codemodel', 'version': {'major': 2, 'minor': 8},
                       'paths': {'source': LOGICAL + '\\s', 'build': LOGICAL + '\\b'},
                       'configurations': [{'name': 'RelWithDebInfo', 'targets': refs}]})
        self.put_json(self.index, {'cmake': {'generator': {'name': 'Ninja Multi-Config', 'multiConfig': True}},
                                   'reply': {'codemodel-v2': {'kind': 'codemodel', 'version': {'major': 2, 'minor': 8},
                                                               'jsonFile': 'codemodel-v2-test.json'}}})

    def verify(self):
        files = [{'path': path, 'sha256': sha} for path, sha in self.entries.items()]
        return closure.verify_codemodel_dynamic_targets(self.root, LOGICAL, files, self.policy, self.index,
                                                       self.name, SHA, TREE)

    def test_four_language_and_eleven_marketplace_targets(self):
        for name, count in (('runtime-catalog-language', 4), ('extension-manager', 11)):
            with self.subTest(rule=name):
                self.prepare(name)
                result = self.verify()
                self.assertEqual(len(result['artifacts']), count)
                self.assertEqual(result['basis'], 'cmake-file-api-and-executable-literals')
                self.assertEqual(len(result['reply_files']), count + 3)
                self.assertTrue(all(item['sha256'] == self.entries[item['path']] for item in result['artifacts']))

    def test_rejects_malformed_unauthenticated_or_mismatched_inputs(self):
        for defect in ('missing-definition', 'duplicate-definition', 'wrong-plugin', 'missing-dependency',
                       'wrong-source', 'wrong-config', 'wrong-root', 'target-id', 'missing-literal',
                       'missing-file', 'changed-bytes', 'duplicate-name', 'outside-root', 'wrong-source-pin',
                       'wrong-sdk-helper', 'wrong-sdk-source', 'plugin-source-mismatch', 'alias-target'):
            with self.subTest(defect=defect):
                self.prepare('runtime-catalog-language')
                runner_path = self.reply + 'target-runner.json'; runner = copy.deepcopy(self.objects[runner_path])
                model_path = self.reply + 'codemodel-v2-test.json'; model = copy.deepcopy(self.objects[model_path])
                define = runner['compileGroups'][0]['defines']
                if defect == 'missing-definition': define.pop()
                elif defect == 'duplicate-definition': define.append(copy.deepcopy(define[0]))
                elif defect == 'wrong-plugin': define[0]['define'] = define[0]['define'].split('=')[0] + '=' + define[1]['define'].split('=', 1)[1]
                elif defect == 'missing-dependency': runner['dependencies'].pop()
                elif defect == 'wrong-source': runner['sources'][0]['path'] = 'pj_app/tests/other.cpp'
                elif defect == 'wrong-config': model['configurations'][0]['name'] = 'Debug'
                elif defect == 'wrong-root': model['paths']['build'] = 'C:\\Other\\b'
                elif defect == 'target-id': runner['id'] = 'other'
                elif defect == 'missing-literal': self.put(closure.CODEMODEL_RULES[self.name]['runner'], b'synthetic binary without paths')
                elif defect == 'missing-file': self.entries.pop(next(x for x in self.entries if x.endswith('.dll')))
                elif defect == 'changed-bytes': (self.root / closure.CODEMODEL_RULES[self.name]['runner']).write_bytes(b'tampered')
                elif defect == 'duplicate-name': model['configurations'][0]['targets'].append(copy.deepcopy(model['configurations'][0]['targets'][0]))
                elif defect == 'outside-root': define[0]['define'] = define[0]['define'].split('=')[0] + '=\"C:/Other/payload.dll\"'
                elif defect == 'wrong-source-pin': self.policy['reviewed_source_sha256'][closure.CODEMODEL_RULES[self.name]['cmake']] = 'f' * 64
                elif defect == 'wrong-sdk-helper':
                    self.put(self.sdk + '/lib/cmake/plotjuggler_sdk/PjSdkTestFixtures.cmake', b'other helper')
                elif defect == 'wrong-sdk-source':
                    self.put(self.sdk + '/share/plotjuggler_sdk/test_fixtures/mock_data_source.cpp', b'other fixture')
                elif defect == 'plugin-source-mismatch':
                    path = self.reply + 'target-fixture0.json'
                    target = copy.deepcopy(self.objects[path]); target['sources'][0]['path'] = 'different.cpp'
                    self.put_json(path, target)
                else:
                    model['configurations'][0]['targets'][1]['name'] = 'mock_data_source_plugin'
                self.put_json(runner_path, runner); self.put_json(model_path, model)
                with self.assertRaises(closure.ClosureError): self.verify()

    def test_rejects_duplicate_json_keys_and_ambiguous_paths(self):
        self.prepare('runtime-catalog-language')
        self.put(self.index, b'{"reply":{},"reply":{}}')
        with self.assertRaises(closure.ClosureError): self.verify()
        self.prepare('runtime-catalog-language')
        runner = copy.deepcopy(self.objects[self.reply + 'target-runner.json'])
        runner['sources'][0]['path'] = 'pj_app/tests/../tests/runtime_catalog_language_test.cpp'
        self.put_json(self.reply + 'target-runner.json', runner)
        with self.assertRaises(closure.ClosureError): self.verify()


class CandidateReceiptTests(unittest.TestCase):
    """Exercise control flow with mocked platform checks, never real CI proof."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve() / 'n' / SHA[:12]
        self.root.mkdir(parents=True)
        self.logical = str(self.root) if os.name == 'nt' else 'C:\\Users\\Administrator\\PlotJuggler-4.1.0-zh-test-558a\\n\\' + SHA[:12]
        self.output = self.root / 'b/native-kit/closure-evidence'; self.output.mkdir(parents=True)
        self.policy_path = self.root / 's/.github/windows-native-kit/ci-closure-policy.json'
        self.candidate = self.root / 'b/native-kit/stage-candidate.json'
        self.report = self.root / 'b/native-kit/stage-gaps.json'
        def write(relative, value):
            path = self.root / relative; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(value); return path
        self.write = write
        policy = {'schema': 2, 'verifier_sha256': closure.digest(Path(closure.__file__)), 'qt_version': '6.12.0'}
        write(self.policy_path.relative_to(self.root).as_posix(), json.dumps(policy).encode())
        write('b/native-kit/run-plan.json', b'{}'); write('b/discovery.json', b'{}')
        qt = 'q/6.12.0/msvc2022_64/bin/Qt6Core.dll'; write(qt, b'qt')
        files = [self.policy_path.relative_to(self.root).as_posix(), 'b/native-kit/run-plan.json', 'b/discovery.json', qt]
        self.plan = {'origins': {'root': {'root': str(self.root)}},
                     'files': [{'origin': 'root', 'source': x, 'destination': x,
                                'sha256': closure.digest(self.root / x)} for x in files]}
        write(self.candidate.relative_to(self.root).as_posix(), json.dumps(self.plan).encode())
        write(self.report.relative_to(self.root).as_posix(), json.dumps({'source_sha': SHA, 'source_tree': TREE,
              'logical_root': self.logical, 'configuration': 'RelWithDebInfo', 'coverage': []}).encode())
        suites = [{'id': 'main', 'full_discovery': 'b/discovery.json', 'discovery': 'b/discovery.json'}]
        paths = {'qt': 'q/6.12.0/msvc2022_64', 'python': 't/python/python.exe', 'ctest': 't/cmake/bin/ctest.exe'}
        prepared = {'main': {'selected': {'Case'}, 'unrun': []}}
        self.launcher = types.SimpleNamespace(LauncherError=RuntimeError,
             validate_plan=lambda *a: (paths, ['c/runtime'], suites), selection_plan=lambda *a: prepared)
        self.driver = types.SimpleNamespace(CIError=RuntimeError, validate_policy=lambda *a: {'main': {}},
                                            validate_ci_selection=lambda *a: None)

    def execute(self, bad=None):
        def git(argv, **kwargs):
            return types.SimpleNamespace(returncode=0, stdout=(SHA if argv[-1] == 'HEAD' else TREE if argv[-1] == 'HEAD^{tree}' else '').encode())
        def module(name, filename):
            return self.launcher if filename == 'run_native_test_bundle.py' else self.driver
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.dict(closure.os.environ, {'GITHUB_SHA': SHA, 'SystemRoot': 'C:\\Windows'}))
            # Keep the real strict root check while using only an owned temp tree.
            stack.enter_context(mock.patch.object(closure, '_candidate_build_root', return_value=self.logical))
            for name, replacement in {'run': git}.items(): stack.enter_context(mock.patch.object(closure.subprocess, name, side_effect=replacement))
            stack.enter_context(mock.patch.object(closure, '_module', side_effect=module))
            for name, result in {'derive_partition': {'schema': 1}, 'derive_dynamic_inventory': {'basis': 'source-analysis'},
                    'verify_conan_graph': {'host_packages': 1}, 'verify_conan_process_records': {'scope': 'synthetic'},
                    'verify_generated_media': {'manifest_sha256':'a'*64,'files':{}},
                    'verify_generated_source_status': None, 'parse_tracked_source': [], 'source_paths_match': [],
                    'verify_cmake_build_records': {'scope': 'synthetic'},
                    'verify_hosted_preflights': {'scope': 'synthetic'}, 'verify_host_system_resolution': {'modules': []},
                    'prepare_qt_declarations': {'schema': 1, 'files': [{'source': 'bin/Qt6Core.dll'}], 'origins': {}},
                    'derive_verified_python_pair': {'driver':'t/python/python312.dll','conan':'c/python/python312.dll'},
                    'derive_pe_processes': [], 'resolve_candidate_pe_imports': {'scope':'synthetic','system_imports':[],'legacy_checks':[]},
                    'candidate_provenance': {'scope': 'synthetic'}}.items():
                target = mock.patch.object(closure, name, side_effect=closure.ClosureError('missing actual evidence') if name == bad else None,
                                           return_value=result)
                stack.enter_context(target)
            return closure.prepare_candidate_receipt(self.root, self.candidate, self.report, self.policy_path, self.output)

    def test_successful_checks_create_candidate_only_receipt(self):
        result = self.execute()
        self.assertIn('test runs remain required', result['scope'])
        receipt = json.loads((self.output / 'receipt.json').read_text(encoding='utf-8'))
        self.assertEqual({x['kind'] for x in receipt['evidence']}, closure.REQUIRED_EVIDENCE_KINDS)
        self.assertEqual(receipt['candidate_plan_sha256'], closure.digest(self.candidate))
        self.assertEqual(len(next(x for x in receipt['evidence'] if x['kind'] == 'case-source-review')['cases']), 1)

    def test_missing_concrete_evidence_does_not_write_a_receipt(self):
        for control in ('verify_conan_graph', 'verify_generated_media', 'source_paths_match'):
            with self.subTest(control=control), self.assertRaises(closure.ClosureError): self.execute(control)
            self.assertFalse((self.output / 'receipt.json').exists())

    def test_fixed_producer_root_and_policy_verifier_pin(self):
        self.assertEqual(closure._candidate_build_root(SHA),
                         'C:\\Users\\Administrator\\PlotJuggler-4.1.0-zh-test-558a\\n\\' + SHA[:12])
        policy = json.loads((ROOT / '.github/windows-native-kit/ci-closure-policy.json').read_text(encoding='utf-8'))
        self.assertEqual(policy['verifier_sha256'], closure.digest(Path(closure.__file__)))
        candidate_policy = json.loads(self.policy_path.read_text(encoding='utf-8'))
        candidate_policy['verifier_sha256'] = '0' * 64
        self.policy_path.write_text(json.dumps(candidate_policy), encoding='utf-8')
        with self.assertRaisesRegex(closure.ClosureError, 'verifier identity is invalid'):
            self.execute()
        self.assertFalse((self.output / 'receipt.json').exists())

    def test_pending_modern_policy_cannot_write_candidate_receipt(self):
        policy = json.loads(self.policy_path.read_text(encoding="utf-8"))
        policy['approval_status'] = 'pending-modern-native-review'
        self.policy_path.write_text(json.dumps(policy), encoding="utf-8")
        with self.assertRaisesRegex(closure.ClosureError, 'pending-modern-native-review'):
            self.execute()
        self.assertFalse((self.output / 'receipt.json').exists())

    def test_wrong_producer_root_does_not_write_receipt(self):
        report = json.loads(self.report.read_text(encoding='utf-8'))
        report['logical_root'] = self.logical.replace('\\n\\', '\\other\\n\\')
        self.report.write_text(json.dumps(report), encoding='utf-8')
        with self.assertRaisesRegex(closure.ClosureError, 'actual CI source and fixed root'):
            self.execute()
        self.assertFalse((self.output / 'receipt.json').exists())


@unittest.skipUnless(shutil.which('git'), 'Git is required')
class SourcePinCheckoutTests(unittest.TestCase):
    def test_verifier_sha_is_preserved_when_checkout_enables_autocrlf(self):
        policy = json.loads((ROOT / '.github/windows-native-kit/ci-closure-policy.json').read_text(encoding='utf-8'))
        verifier = Path(closure.__file__).read_bytes()
        expected = policy['verifier_sha256']
        self.assertEqual(hashlib.sha256(verifier).hexdigest(), expected)
        with tempfile.TemporaryDirectory(prefix='native-pin-checkout-') as temp:
            repo = Path(temp).resolve()
            protected = repo / 'scripts/windows/verify_native_ci_closure.py'
            protected.parent.mkdir(parents=True)
            protected.write_bytes(verifier)
            control = repo / 'unprotected.py'; control.write_bytes(verifier)
            (repo / '.gitattributes').write_bytes((ROOT / '.gitattributes').read_bytes())
            env = {key: value for key, value in os.environ.items() if not key.upper().startswith('GIT_')}
            env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull, GIT_ATTR_NOSYSTEM='1')
            def git(*args):
                return subprocess.run(['git', '-C', str(repo), '-c', 'core.autocrlf=true',
                                       '-c', 'core.safecrlf=false', *args], env=env,
                                      capture_output=True, check=True).stdout
            git('init', '-q')
            git('add', '.gitattributes', protected.relative_to(repo).as_posix(), 'unprotected.py')
            git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'checkout fixture')
            protected.unlink(); control.unlink()
            git('checkout', '--', protected.relative_to(repo).as_posix(), 'unprotected.py')
            self.assertEqual(hashlib.sha256(protected.read_bytes()).hexdigest(), expected)
            self.assertEqual(protected.read_bytes(), verifier)
            self.assertIn(b'\r\n', control.read_bytes())
            self.assertNotEqual(hashlib.sha256(control.read_bytes()).hexdigest(), expected)


class StagedReceiptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.entries = {}
        def put(relative, value):
            path = self.root / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(value)
            self.entries[relative] = hashlib.sha256(value).hexdigest()
            return self.entries[relative]
        self.put = put
        prefix = 'b/native-kit/closure-evidence/'
        policy_sha = put('s/.github/windows-native-kit/ci-closure-policy.json', b'policy')
        verifier_sha = put('s/scripts/windows/verify_native_ci_closure.py', b'verifier')
        plan_sha = put(prefix + 'candidate-plan.json', b'plan')
        report_sha = put(prefix + 'candidate-report.json', b'report')
        put(prefix + 'ci-policy.json', b'{}'); put(prefix + 'provenance.json', b'{}')
        evidence = [{'kind': 'candidate-input', 'path': prefix + 'candidate-plan.json', 'sha256': plan_sha},
                    {'kind': 'candidate-input', 'path': prefix + 'candidate-report.json', 'sha256': report_sha}]
        for kind in sorted(closure.REQUIRED_EVIDENCE_KINDS - {'candidate-input'}):
            relative = prefix + kind + '.json'; value = kind.encode()
            item = {'kind': kind, 'path': relative, 'sha256': put(relative, value)}
            if kind == 'case-source-review': item['cases'] = [{'suite': 'i18n', 'case': 'exact'}]
            evidence.append(item)
        self.receipt = {'schema': 1, 'source_sha': SHA, 'source_tree': TREE, 'configuration': 'RelWithDebInfo',
                        'reviewed_policy_sha256': policy_sha, 'verifier_sha256': verifier_sha,
                        'candidate_plan_sha256': plan_sha, 'candidate_report_sha256': report_sha, 'evidence': evidence}
        import json
        put(prefix + 'receipt.json', json.dumps(self.receipt).encode())
        self.manifest = {'files': [{'path': name, 'sha256': value} for name, value in self.entries.items()]}

    def check(self, receipt=None):
        return closure.check_staged_receipt_integrity(self.root, self.manifest, self.receipt if receipt is None else receipt, SHA, TREE)

    def test_checks_all_manifest_bytes_without_claiming_execution_proof(self):
        result = self.check()
        self.assertIn('evidence-specific replay still required', result['scope'])
        self.assertEqual(result['evidence_files'], len(self.receipt['evidence']))

    def test_modified_evidence_or_self_asserted_receipt_fails(self):
        altered = copy.deepcopy(self.receipt); altered['source_tree'] = 'f' * 40
        with self.assertRaises(closure.ClosureError): self.check(altered)
        (self.root / self.receipt['evidence'][0]['path']).write_bytes(b'tampered')
        with self.assertRaises(closure.ClosureError): self.check()

    def test_missing_or_duplicate_evidence_cannot_be_certified(self):
        import json
        prefix = 'b/native-kit/closure-evidence/'
        for mutation in ('missing', 'duplicate', 'missing-cases'):
            altered = copy.deepcopy(self.receipt)
            if mutation == 'missing': altered['evidence'] = altered['evidence'][1:]
            elif mutation == 'duplicate': altered['evidence'].append(copy.deepcopy(altered['evidence'][0]))
            else: next(x for x in altered['evidence'] if x['kind'] == 'case-source-review')['cases'] = []
            raw = json.dumps(altered).encode(); self.put(prefix + 'receipt.json', raw)
            next(x for x in self.manifest['files'] if x['path'] == prefix + 'receipt.json')['sha256'] = hashlib.sha256(raw).hexdigest()
            with self.subTest(mutation=mutation), self.assertRaises(closure.ClosureError): self.check(altered)


class QtArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'qtbase.7z'; self.path.write_bytes(b'official-test-archive')
        url = 'https://download.qt.io/online/qtsdkrepository/test/qtbase.7z'
        self.pin = {'file': self.path.name, 'url': url, 'sha256': hashlib.sha256(self.path.read_bytes()).hexdigest(),
                    'bytes': self.path.stat().st_size, 'source': url + '.mirrorlist'}

    def test_official_pin_checks_archive_bytes(self):
        self.assertEqual(closure.authenticate_qt_archive(self.path, self.pin)['sha256'], self.pin['sha256'])
        self.path.write_bytes(b'forged-other-archive!')
        with self.assertRaises(closure.ClosureError): closure.authenticate_qt_archive(self.path, self.pin)

    def test_listing_rejects_unsafe_duplicate_or_linked_members(self):
        good = b'Path = 6.12.0/msvc2022_64/bin/Qt6Core.dll\nSize = 7\nAttributes = A\nEncrypted = -\n'
        self.assertEqual(closure.parse_7z_listing(good)['6.12.0/msvc2022_64/bin/qt6core.dll']['bytes'], 7)
        for bad in (good + b'\n' + good, good.replace(b'Qt6Core.dll', b'../evil.dll'),
                    good + b'Symbolic Link = other\n', good.replace(b'Encrypted = -', b'Encrypted = +'),
                    good.replace(b'Qt6Core.dll', b'bad*.dll')):
            with self.subTest(bad=bad), self.assertRaises(closure.ClosureError): closure.parse_7z_listing(bad)

    def test_untrusted_source_or_mismatch_fails(self):
        for field, value in (('url', 'https://example.org/online/qtsdkrepository/test/qtbase.7z'),
                             ('source', 'https://example.org/checksum'), ('sha256', 'a' * 63), ('bytes', True)):
            pin = dict(self.pin, **{field: value})
            with self.subTest(field=field), self.assertRaises(closure.ClosureError):
                closure.authenticate_qt_archive(self.path, pin)


class QtArchiveNormalizationTests(unittest.TestCase):
    """Exercise all eight real names with synthetic bytes, never replacing official pins."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name) / 'archives'; self.directory.mkdir()
        self.policy = json.loads((ROOT / '.github/windows-native-kit/ci-closure-policy.json').read_text(encoding='utf-8'))
        # This class tests the historical normalization mechanism using synthetic bytes,
        # not the repository's pending development acceptance policy.
        self.policy.pop('approval_status', None)
        self.aliases = self.policy['qt_archive_aliases']
        self.assertEqual(len(self.aliases), 8)
        for pin in self.policy['qt_archives']:
            local = next(k for k, v in self.aliases.items() if v == pin['file'])
            data = ('synthetic:' + local).encode()
            pin.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
            (self.directory / local).write_bytes(data)
        self.local = next(iter(self.aliases))

    def normalize(self):
        return closure.normalize_qt_archives(self.directory, self.policy)

    def test_all_eight_names_canonicalize_and_remain_strictly_authenticatable(self):
        receipt = self.normalize()
        self.assertEqual({x['retained_file'] for x in receipt}, set(self.aliases))
        self.assertEqual({p.name for p in self.directory.iterdir()}, set(self.aliases.values()))
        for pin in self.policy['qt_archives']:
            closure.authenticate_qt_archive(self.directory / pin['file'], pin)
        self.assertEqual(len(closure.retained_qt_archives(self.directory, self.policy['qt_archives'])), 8)
        self.assertEqual(len(self.normalize()), 8)  # Safe retry after partial rename.

    def test_bad_inventory_fails_before_any_rename(self):
        for mutation in ('missing', 'unknown', 'case', 'collision', 'tamper', 'size',
                         'directory', 'symlink', 'hardlink', 'fifo'):
            with self.subTest(mutation=mutation):
                with tempfile.TemporaryDirectory() as tmp:
                    original = self.directory
                    self.directory = Path(tmp) / 'archives'
                    shutil.copytree(original, self.directory)
                    path = self.directory / self.local
                    if mutation == 'missing': path.unlink()
                    elif mutation == 'unknown': (self.directory / 'unknown.7z').write_bytes(b'?')
                    elif mutation == 'case': path.rename(path.with_name(path.name.upper()))
                    elif mutation == 'collision': shutil.copyfile(path, self.directory / self.aliases[self.local])
                    elif mutation == 'tamper': path.write_bytes(b'x' * path.stat().st_size)
                    elif mutation == 'size': path.write_bytes(b'x')
                    elif mutation == 'directory': (self.directory / 'ignored').mkdir()
                    elif mutation == 'symlink': (self.directory / 'link').symlink_to(path)
                    elif mutation == 'hardlink': os.link(path, self.directory / 'link')
                    elif mutation == 'fifo':
                        if not hasattr(os, 'mkfifo'):
                            self.directory = original
                            continue
                        os.mkfifo(self.directory / 'pipe')
                    before = sorted(p.name for p in self.directory.iterdir())
                    with self.assertRaises(closure.ClosureError): self.normalize()
                    self.assertEqual(sorted(p.name for p in self.directory.iterdir()), before)
                    self.directory = original

    def test_invalid_ambiguous_or_untrusted_policies_fail_without_rename(self):
        for mutation in ('duplicate-pin', 'case-pin', 'alias-target', 'alias-collision',
                         'alias-ambiguous', 'alias-missing', 'unsafe-alias', 'url', 'source', 'hash', 'size'):
            with self.subTest(mutation=mutation):
                original = self.policy
                self.policy = copy.deepcopy(original)
                pins, aliases = self.policy['qt_archives'], self.policy['qt_archive_aliases']
                if mutation == 'duplicate-pin': pins.append(copy.deepcopy(pins[0]))
                elif mutation == 'case-pin':
                    pins.append(copy.deepcopy(pins[0])); pins[-1]['file'] = pins[-1]['file'].upper()
                elif mutation == 'alias-target': aliases[self.local] = 'absent.7z'
                elif mutation == 'alias-collision': aliases[self.local.upper()] = aliases[self.local]
                elif mutation == 'alias-ambiguous': aliases['another.7z'] = aliases[self.local]
                elif mutation == 'alias-missing': del aliases[self.local]
                elif mutation == 'unsafe-alias': aliases['../unsafe.7z'] = aliases.pop(self.local)
                elif mutation == 'url': pins[0]['url'] = 'https://example.org/' + pins[0]['file']
                elif mutation == 'source': pins[0]['source'] += '?unreviewed'
                elif mutation == 'hash': pins[0]['sha256'] = 'invalid'
                elif mutation == 'size': pins[0]['bytes'] = True
                before = sorted(p.name for p in self.directory.iterdir())
                with self.assertRaises(closure.ClosureError): self.normalize()
                self.assertEqual(sorted(p.name for p in self.directory.iterdir()), before)
                self.policy = original

    def test_canonical_only_consumer_rejects_alias_and_missing_archive(self):
        with self.assertRaises(closure.ClosureError):
            closure.retained_qt_archives(self.directory, self.policy['qt_archives'])
        self.normalize()
        (self.directory / self.aliases[self.local]).unlink()
        with self.assertRaises(closure.ClosureError):
            closure.retained_qt_archives(self.directory, self.policy['qt_archives'])

    def test_cli_checks_policy_identity_and_emits_all_eight_mappings(self):
        root = Path(self.tmp.name)
        target = root / 'd/qt-archives'; target.parent.mkdir()
        self.directory.rename(target); self.directory = target
        policy_path = root / 's/.github/windows-native-kit/ci-closure-policy.json'
        policy_path.parent.mkdir(parents=True)
        self.policy['verifier_sha256'] = '0' * 64
        policy_path.write_text(json.dumps(self.policy), encoding='utf-8')
        command = [__import__('sys').executable, '-I', '-B', str(Path(closure.__file__)),
                   '--normalize-qt-archives', '--root', str(root), '--reviewed-policy', str(policy_path)]
        bad = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(bad.returncode, 1)
        self.assertIn('exact source-reviewed verifier', bad.stderr)
        self.assertEqual({p.name for p in target.iterdir()}, set(self.aliases))
        self.policy['verifier_sha256'] = closure.digest(Path(closure.__file__))
        policy_path.write_text(json.dumps(self.policy), encoding='utf-8')
        good = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(good.returncode, 0, good.stderr)
        receipt = json.loads(good.stdout)['qt_archive_identities']
        self.assertEqual({x['retained_file']: x['file'] for x in receipt}, self.aliases)

    def test_producer_authenticates_before_qt_execution_and_build(self):
        script = (ROOT / 'scripts/windows/prepare_native_ci.ps1').read_text(encoding='utf-8')
        check = script.index("'--normalize-qt-archives'")
        self.assertLess(script.index('--archive-dest $qtArchives'), check)
        for marker in ("$actualQt =", "@('profile', 'detect'", "Invoke-Checked $cmake @('-S'"):
            self.assertLess(check, script.index(marker))
        self.assertIn('Invoke-Checked $builderPython', script[check - 150:check])


class HostedPreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.identity = {'pid': 9, 'sid': 'S-1-5-18', 'session': 0, 'integrity_rid': 16384,
                         'auth_luid': '00000000:000003e7', 'elevation_type': 'full'}
        def put(name, value):
            path = self.root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(value)
            return hashlib.sha256(value).hexdigest()
        self.put = put
        self.put('s/tests/test_windows_native_bootstrap.py', b'bootstrap tests')
        self.put('s/scripts/windows/bootstrap_native_test_kit.ps1', b'bootstrap script')
        base = 'b/native-kit/bootstrap-selftest-evidence/'
        out = self.put(base + 'stdout.bin', b'')
        err = self.put(base + 'stderr.bin', b'test_actual_embedded_verifier_rejects_malformed_cases ... ok\n'
            b'test_full_fixed_root_and_refuse_reuse ... ok\n')
        proc = {'schema': 1, 'scope': 'disposable-windows-ci-only', 'source_sha': SHA,
                'synthetic_sha': '3'*40, 'exit_code': 0,
                'executable': 'C:\\tools\\python.exe',
                'test_sha256': hashlib.sha256(b'bootstrap tests').hexdigest(),
                'bootstrap_sha256': hashlib.sha256(b'bootstrap script').hexdigest(),
                'stdout_sha256': out, 'stderr_sha256': err,
                'argv': ['python.exe','-B','-m','unittest','discover','-s','tests','-p','test_windows_native_bootstrap.py','-v']}
        put(base + 'process.json', json.dumps(proc).encode())
        testsha = put('s/tests/test_windows_native_python_origin.py', b'origin tests')
        scriptsha = put('s/scripts/windows/verify_embedded_python_origin.ps1', b'origin verifier')
        originout = put(base + 'python-origin.stdout.bin', b'')
        originerr = put(base + 'python-origin.stderr.bin',
                        b'test_actual_dotnet_compare_accepts_exact_zip_and_rejects_tampering ... ok\n')
        origin = {'schema': 1, 'scope': 'disposable-windows-ci-only', 'source_sha': SHA,
                  'source_tree': TREE,
                  'synthetic_sha': proc['synthetic_sha'], 'bootstrap_sha256': proc['bootstrap_sha256'],
                  'executable': proc['executable'], 'executable_sha256': 'a'*64, 'exit_code': 0,
                  'test_sha256': testsha, 'python_origin_script_sha256': scriptsha,
                  'stdout_sha256': originout, 'stderr_sha256': originerr,
                  'argv': [proc['executable'], '-I', '-B', '-m', 'unittest', 'discover', '-s', 'tests',
                           '-p', 'test_windows_native_python_origin.py', '-v']}
        put(base + 'python-origin.process.json', json.dumps(origin).encode())
        qt = 'q/6.12.0/msvc2022_64/bin/Qt6Core.dll'; qtsha = put(qt, b'qtcore')
        exe = 'b/ci-temp-probe/RelWithDebInfo/pj_native_ci_temp_probe.exe'; exesha = put(exe, b'temp probe')
        def win(relative): return LOGICAL + '\\' + relative.replace('/', '\\')
        tempbase = 'b/native-kit/ci-temp-probe-evidence/'
        for phase in ('before-plugin-preflight', 'before-marker-mutation', 'before-main-discovery'):
            run = win('ci-discovery'); temp = run + '\\tmp'
            proof = {'scope':'disposable-windows-ci-only','pid':5,'user_sid':'S-1-5-18','session':0,
                     'integrity_rid':16384,'auth_luid':'00000000:000003e7','elevation_type':'full',
                     'qt_version':'6.12.0','qt_core':win(qt),'run_root':run,'qt_temp':temp}
            stdout = put(tempbase+phase+'.stdout.bin', json.dumps(proof).encode())
            stderr = put(tempbase+phase+'.stderr.bin', b'')
            record = {'schema':1,'phase':phase,'cwd':win('s'),'executable':win(exe),'exit_code':0,
                      'argv':['--run-root',run,'--temp',temp,'--qt','6.12.0','--qt-core',win(qt)],
                      'temp':temp,'tmp':temp,'executable_sha256':exesha,'qt_core_sha256':qtsha,
                      'stdout_sha256':stdout,'stderr_sha256':stderr}
            put(tempbase+phase+'.json',json.dumps(record).encode())
        guard = put('s/cmake/test_mains/pj_test_windows_registry.h', b'guard')
        regexe = put('b/registry-smoke/RelWithDebInfo/registry_fixture_smoke.exe', b'registry exe')
        src = 'scripts/windows/native_registry_smoke/main.cpp'; srcsha = put('s/'+src,b'actual source')
        rb='b/native-kit/registry-smoke-evidence/'
        uid='11111111-1111-4111-8111-111111111111'
        k1='PlotJugglerTest-'+uid; k2='Software\\PJFixtureLate-'+uid
        header=('Private test registry: HKCU\\'+k1+'\nOwned late sentinel: HKCU\\'+k2+'\n'
                'Native guard initialized; QApplication-free lifecycle probe.\n').encode()
        put(rb+'normal.stdout.bin',b''); put(rb+'injected.stdout.bin',b'')
        put(rb+'normal.stderr.bin',header+b'Late QSettings write failed closed; self-owned real sentinel untouched.\n')
        put(rb+'injected.stderr.bin',header+b'Injected owned-key cleanup failure: 5\n')
        registry={'schema':1,'complete':True,'exe_sha256':regexe,'qt_core_sha256':qtsha,'guard_header_sha256':guard,
                  'normal':{'exit_code':0,'owned_keys':[k1,k2],'absent_after':[True,True]},
                  'injected':{'exit_code':1,'owned_keys':[k1,k2],'present_before_exact_cleanup':[True,True],
                              'absent_after_exact_cleanup':[True,True]}}
        regsha=put(rb+'receipt.json',json.dumps(registry).encode())
        regbuild={'schema':1,'source_sha':SHA,'source_tree':TREE,'configuration':'RelWithDebInfo',
                  'source_files':[{'path':src,'sha256':srcsha}], 'executable_sha256':regexe,
                  'qt_core_sha256':qtsha,'receipt_sha256':regsha}
        put('b/native-kit/registry-smoke-build/producer-identity.json',json.dumps(regbuild).encode())
        original=b'void ActiveWidgetsMarker::clear() {\n  live_.clear();\n  QFile::remove(path_);\n}'
        originalsha=put('s/pj_runtime/src/ActiveWidgetsMarker.cpp',original)
        runner=put('b/pj_app/RelWithDebInfo/pj_app_gui_tests.exe',b'restored runner')
        module=closure._module('fixture_mutation','native_marker_mutation.py')
        mutation={'schema':1,'complete':True,'scope':'disposable-windows-ci-only','source_sha':SHA,'source_tree':TREE,
                  'case':module.CASE,'ci_identity':self.identity,'original_source_sha256':originalsha,
                  'mutated_source_sha256':hashlib.sha256(module.mutant(original)).hexdigest(),
                  'baseline_runner_sha256':'c'*64,'mutant_runner_sha256':'d'*64,'restored_runner_sha256':runner,
                  'qt_preflight_sha256':hashlib.sha256((self.root/tempbase/'before-marker-mutation.stdout.bin').read_bytes()).hexdigest()}
        mb='b/native-kit/marker-mutation-evidence/'
        put(mb+'receipt.json',json.dumps(mutation).encode())
        bad='<failure message="QFile::exists(marker_path_) Actual: true Expected: false clean-exit clear must remove an unowned record"/>'
        def xml(failure):
            return ('<testsuites><testsuite><testcase name="'+module.CASE_NAME+'" classname="'+module.CASE_CLASS+
                    '" status="run">'+failure+'</testcase></testsuite></testsuites>').encode()
        put(mb+'mutant.xml',xml(bad)); put(mb+'original.xml',xml(''))
        for phase in ('mutant-build','mutant-test','original-build','original-test'):
            output=b'ActiveWidgetsMarker.cpp.obj pj_runtime.lib pj_app_gui_tests.exe' if phase.endswith('build') else b'test'
            out=put(mb+phase+'.stdout.bin',output); err=put(mb+phase+'.stderr.bin',b'')
            code=1 if phase=='mutant-test' else 0
            put(mb+phase+'.process.json',json.dumps({'exit_code':code,'identity':self.identity,
                                                    'stdout_sha256':out,'stderr_sha256':err}).encode())

    def verify(self): return closure.verify_hosted_preflights(self.root,SHA,TREE,LOGICAL,'6.12.0')

    def test_raw_controls_are_independently_rechecked(self):
        self.assertEqual(self.verify()['mutation_phases'],4)

    def test_changed_bootstrap_temp_registry_and_mutation_refuse(self):
        for path in ('b/native-kit/bootstrap-selftest-evidence/stderr.bin',
                     'b/native-kit/bootstrap-selftest-evidence/python-origin.stderr.bin',
                     's/scripts/windows/verify_embedded_python_origin.ps1',
                     'b/native-kit/ci-temp-probe-evidence/before-main-discovery.stdout.bin',
                     'b/native-kit/registry-smoke-evidence/injected.stderr.bin',
                     'b/native-kit/marker-mutation-evidence/mutant.xml'):
            item=self.root/path; original=item.read_bytes(); item.write_bytes(b'altered')
            with self.subTest(path=path), self.assertRaises((closure.ClosureError, ValueError)):
                self.verify()
            item.write_bytes(original)


class SystemResolutionTests(unittest.TestCase):
    def test_each_named_system_import_must_resolve_to_microsoft_system32(self):
        def resolver(name):
            return {'requested': name, 'path': 'C:\\Windows\\System32\\KERNELBASE.dll', 'sha256': 'a'*64,
                    'signature_status': 'Valid', 'signature_subject': 'CN=Microsoft Windows, O=Microsoft Corporation, C=US'}
        result = closure.verify_host_system_resolution(['kernel32.dll', 'api-ms-win-core-test-l1-1-0.dll'], 'C:\\Windows', resolver)
        self.assertEqual(len(result['modules']), 2)
        for field, value in (('path','C:\\Users\\User\\evil.dll'), ('signature_status','UnknownError'),
                             ('signature_subject','CN=Other, O=Other'), ('sha256','bad')):
            def wrong(name): return dict(resolver(name), **{field: value})
            with self.subTest(field=field), self.assertRaises(closure.ClosureError):
                closure.verify_host_system_resolution(['kernel32.dll'], 'C:\\Windows', wrong)

    def test_duplicates_and_wildcards_are_never_system_approval(self):
        for names in ([], ['KERNEL32.dll', 'kernel32.dll'], ['api-ms-win-*.dll']):
            with self.subTest(names=names), self.assertRaises(closure.ClosureError):
                closure.verify_host_system_resolution(names, 'C:\\Windows', lambda x: {})


class ReachablePEClosureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.rows = []; self.imports = {}
        self.plan = {'origins': {'payload': {'root': str(self.root)}}, 'files': self.rows}
        self.add('b/runner.exe', {'normal': ['KERNEL32.dll', 'fixture.dll'], 'delay': ['api-ms-win-core-test-l1-1-0.dll']})
        self.add('b/lib/fixture.dll', {'normal': ['USER32.dll'], 'delay': []})

    def add(self, path, imports):
        file = self.root / path; file.parent.mkdir(parents=True, exist_ok=True); file.write_bytes(path.encode())
        self.rows.append({'origin': 'payload', 'source': path, 'destination': path, 'sha256': hashlib.sha256(path.encode()).hexdigest()})
        self.imports[path] = imports

    def reader(self, path, require_x64):
        if not require_x64: raise ValueError('must require AMD64')
        return self.imports[path.relative_to(self.root).as_posix()]

    def resolver(self, name):
        if name.casefold() == 'fixture.dll': return None
        return {'requested': name, 'path': 'C:\\Windows\\System32\\KERNELBASE.dll', 'sha256': 'a'*64,
                'signature_status': 'Valid', 'signature_subject': 'CN=Microsoft Windows, O=Microsoft Corporation, C=US'}

    def verify(self, resolver=None):
        processes = [{'executable': 'b/runner.exe', 'working_directory': 'b', 'modules': []}]
        return closure.resolve_candidate_pe_imports(self.plan, processes, ['b/lib'], 'C:\\Windows',
                                                    resolver or self.resolver, pe_reader=self.reader, legacy_probe=lambda name: [])

    def test_follows_only_reachable_provider_and_records_api_set_delay(self):
        self.add('b/lib/unrelated.dll', {'normal': ['unknown.dll'], 'delay': []})
        result = self.verify()
        self.assertEqual({x['destination'] for x in result['plan']['files']}, {'b/runner.exe', 'b/lib/fixture.dll'})
        self.assertEqual({(x['importer'], x['kind'], x['requested']) for x in result['system_imports']},
                         {('b/runner.exe', 'normal', 'KERNEL32.dll'),
                          ('b/runner.exe', 'delay', 'api-ms-win-core-test-l1-1-0.dll'),
                          ('b/lib/fixture.dll', 'normal', 'USER32.dll')})
        self.assertIn('not dynamic-load observation', result['scope'])
        self.assertEqual([(x['requested'],x['result']) for x in result['legacy_checks']], [('fixture.dll','absent')])

    def test_windows_or_legacy_system_shadow_refuses_path_provider(self):
        processes=[{'executable':'b/runner.exe','working_directory':'b','modules':[]}]
        for collision in ('C:\\Windows\\fixture.dll','C:\\Windows\\System\\fixture.dll'):
            with self.subTest(collision=collision), self.assertRaisesRegex(closure.ClosureError,'shadows'):
                closure.resolve_candidate_pe_imports(self.plan,processes,['b/lib'],'C:\\Windows',self.resolver,
                    pe_reader=self.reader,legacy_probe=lambda name: [collision])
        with self.assertRaisesRegex(closure.ClosureError,'cannot check'):
            closure.resolve_candidate_pe_imports(self.plan,processes,['b/lib'],'C:\\Windows',self.resolver,
                pe_reader=self.reader,legacy_probe=mock.Mock(side_effect=PermissionError('denied')))
        self.rows[:]=[row for row in self.rows if row['destination']!='b/lib/fixture.dll']
        self.add('b/fixture.dll',{'normal':[],'delay':[]})
        result=closure.resolve_candidate_pe_imports(self.plan,processes,['b/lib'],'C:\\Windows',self.resolver,
            pe_reader=self.reader,legacy_probe=mock.Mock(side_effect=AssertionError('app directory precedes legacy dirs')))
        self.assertIn('b/fixture.dll',{row['destination'] for row in result['plan']['files']})

    def test_controlled_host_collision_flows_into_actual_pe_resolver(self):
        host=self.root/'synthetic-host/Windows'; (host/'System').mkdir(parents=True)
        (host/'fixture.dll').write_bytes(b'owned collision sentinel')
        processes=[{'executable':'b/runner.exe','working_directory':'b','modules':[]}]
        with self.assertRaisesRegex(closure.ClosureError,'shadows'):
            closure.resolve_candidate_pe_imports(self.plan,processes,['b/lib'],'C:\\Windows',self.resolver,
                pe_reader=self.reader,legacy_probe=lambda name: closure.windows_earlier_dll_presence(name,host,lambda:host))

    def test_controlled_earlier_directory_probe_checks_presence_and_links(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); (root/'System').mkdir()
            self.assertEqual(closure.windows_earlier_dll_presence('fixture.dll',root,lambda:root),[])
            (root/'System/fixture.dll').write_bytes(b'owned sentinel, never loaded')
            self.assertEqual(closure.windows_earlier_dll_presence('fixture.dll',root,lambda:root),
                             [str(root/'System/fixture.dll')])
            with self.assertRaises(closure.ClosureError):
                closure.windows_earlier_dll_presence('../bad.dll',root,lambda:root)
            with self.assertRaises(closure.ClosureError):
                closure.windows_earlier_dll_presence('fixture.dll',root,lambda:root/'different')

    @unittest.skipUnless(__import__('os').name == 'nt', 'requires a real Windows filesystem')
    def test_windows_earlier_probe_is_case_insensitive_on_owned_ntfs(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); (root/'System').mkdir(); (root/'System/FiXtUrE.DLL').write_bytes(b'owned')
            self.assertEqual(len(closure.windows_earlier_dll_presence('fixture.dll',root,lambda:root)),1)

    def test_rejects_system_collision_unresolved_api_and_unsigned_module(self):
        self.add('b/hidden/KERNEL32.dll', {'normal': [], 'delay': []})
        with self.assertRaises(closure.ClosureError): self.verify()
        self.rows.pop(); self.imports.pop('b/hidden/KERNEL32.dll')
        with self.assertRaises(closure.ClosureError):
            self.verify(lambda name: None if name.casefold().startswith('api-') else self.resolver(name))
        def unsigned(name):
            if name.casefold() == 'fixture.dll': return None
            return dict(self.resolver(name), signature_status='UnknownError')
        with self.assertRaises(closure.ClosureError): self.verify(unsigned)

    def test_rejects_different_visible_providers_and_changed_bytes(self):
        self.add('b/lib2/fixture.dll', {'normal': [], 'delay': []})
        with self.assertRaises(closure.ClosureError):
            closure.resolve_candidate_pe_imports(self.plan, [{'executable':'b/runner.exe','working_directory':'b','modules':[]}],
                                                 ['b/lib', 'b/lib2'], 'C:\\Windows',
                                                 self.resolver, pe_reader=self.reader, legacy_probe=lambda name: [])
        (self.root / 'b/runner.exe').write_bytes(b'changed')
        with self.assertRaises(closure.ClosureError): self.verify()

    def test_same_dll_is_resolved_per_process_with_no_driver_path_leak(self):
        self.add('t/python/python.exe', {'normal':['python312.dll'], 'delay':[]})
        self.add('t/python/python312.dll', {'normal':[], 'delay':[]})
        self.add('c/cpython/bin/python312.dll', {'normal':[], 'delay':[]})
        self.imports['b/runner.exe'] = {'normal':['python312.dll'], 'delay':[]}
        processes = [{'executable':'t/python/python.exe','working_directory':'b','modules':[]},
                     {'executable':'b/runner.exe','working_directory':'b','modules':[]}]
        pair = {'driver':'t/python/python312.dll','conan':'c/cpython/bin/python312.dll'}
        result = closure.resolve_candidate_pe_imports(self.plan, processes, ['c/cpython/bin'], 'C:\\Windows',
                        lambda name: None, pe_reader=self.reader, python_pair=pair, legacy_probe=lambda name: [])
        self.assertTrue(set(pair.values()) <= {x['destination'] for x in result['plan']['files']})
        with self.assertRaises(closure.ClosureError):
            closure.resolve_candidate_pe_imports(self.plan, processes, ['c/cpython/bin', 't/python'], 'C:\\Windows',
                                                lambda name: None, pe_reader=self.reader, python_pair=pair, legacy_probe=lambda name: [])
        with self.assertRaises(closure.ClosureError):
            closure.resolve_candidate_pe_imports(self.plan, processes, ['c/cpython/bin'], 'C:\\Windows',
                                                lambda name: None, pe_reader=self.reader, legacy_probe=lambda name: [])
        # The special exception never applies to any other process or DLL.
        self.add('b/python312.dll', {'normal':[], 'delay':[]})
        with self.assertRaises(closure.ClosureError):
            closure.resolve_candidate_pe_imports(self.plan, processes, ['c/cpython/bin'], 'C:\\Windows',
                                                lambda name: None, pe_reader=self.reader, python_pair=pair, legacy_probe=lambda name: [])


class ProcessDerivationTests(unittest.TestCase):
    def setUp(self):
        fixed = ['t/python/python.exe','t/python/_ssl.pyd','t/cmake/bin/cmake.exe','t/cmake/bin/ctest.exe',
                 't/7z/7za.exe','b/ci-temp-probe/RelWithDebInfo/pj_native_ci_temp_probe.exe',
                 'i/temp-probe/RelWithDebInfo/pj_native_temp_probe.exe','b/runner.exe','q/plugins/qoffscreen.dll']
        self.files = [{'path': x, 'sha256':'a'*64} for x in fixed]
        self.suites = [{'id':'main'}]
        self.prepared = {'main': {'selected': {'Case'}}}
        self.docs = {'main': {'kind':'ctestInfo','tests':[test_case('Case','b/runner.exe',
                          WORKING_DIRECTORY=LOGICAL+'\\b')]}}
        self.inventory = {'scopes':[{'suite':'main','cases':['Case'],'runner':{'path':'b/runner.exe','sha256':'a'*64},
                           'dynamic_files':[{'path':'q/plugins/qoffscreen.dll','sha256':'a'*64,'role':'qt-plugin'}],
                           'subprocesses':[]}]}

    def verify(self):
        return closure.derive_pe_processes(self.suites,self.prepared,self.docs,self.inventory,self.files,LOGICAL)

    def test_derives_driver_extensions_and_selected_process_context(self):
        result = self.verify()
        driver = next(x for x in result if x['executable'] == 't/python/python.exe')
        self.assertEqual(driver['modules'], ['t/python/_ssl.pyd'])
        selected = next(x for x in result if x['executable'] == 'b/runner.exe')
        self.assertEqual(selected['working_directory'], 'b')
        self.assertEqual(selected['modules'], ['q/plugins/qoffscreen.dll'])

    def test_outside_cwd_missing_scope_and_unreviewed_child_fail(self):
        for defect in ('cwd','scope','child'):
            with self.subTest(defect=defect):
                self.setUp()
                if defect == 'cwd': self.docs['main']['tests'][0]['properties'][0]['value'] = 'C:\\outside'
                elif defect == 'scope': self.inventory['scopes'][0]['cases'] = ['different']
                else: self.inventory['scopes'][0]['subprocesses'] = [{'path':'b/child.exe','sha256':'a'*64}]
                with self.assertRaises(closure.ClosureError): self.verify()


class ConanGraphTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.files = []
        def put(name, value):
            path = self.root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(value)
            self.files = [x for x in self.files if x['path'] != name]
            self.files.append({'path': name, 'sha256': hashlib.sha256(value).hexdigest()})
        self.put = put
        self.folder = 'c/p/zlib-test/p'; self.ref = 'zlib/1.3#' + 'c'*32
        self.pkgid, self.prev = 'a'*40, 'b'*32
        contents = {'licenses/LICENSE': b'notice', 'bin/zlib.dll': b'actual dll'}
        for name, value in contents.items(): put(self.folder + '/' + name, value)
        raw = ('12345\n' + ''.join(name + ': ' + hashlib.md5(value, usedforsecurity=False).hexdigest() + '\n'
                                    for name, value in contents.items())).encode()
        put(self.folder + '/conanmanifest.txt', raw)
        graph = {'graph': {'nodes': {'0': {'context': 'host'}, '1': {'context': 'host', 'ref': self.ref,
                 'rrev': 'c'*32, 'package_id': self.pkgid, 'prev': self.prev,
                 'package_folder': LOGICAL + '\\' + self.folder.replace('/', '\\')}}}}
        graph_bytes = json.dumps(graph).encode(); put('b/conan-install-graph.json', graph_bytes)
        identity = {'schema': 1, 'source_sha': SHA, 'source_tree': TREE,
                    'graph_sha256': hashlib.sha256(graph_bytes).hexdigest(), 'packages': [
                        {'ref': self.ref, 'rrev': 'c'*32, 'package_id': self.pkgid, 'prev': self.prev,
                         'package_folder': self.folder, 'manifest_sha256': hashlib.sha256(raw).hexdigest(), 'runtime_dirs': []}]}
        put('b/native-kit/conan-runtime-identity.json', json.dumps(identity).encode())
        put('s/conan.lock', json.dumps({'requires': [self.ref + '%123.4']}).encode())

    def verify(self): return closure.verify_conan_graph(self.root, self.files, SHA, TREE, LOGICAL)

    def test_complete_host_identity_and_original_license(self):
        self.assertEqual(self.verify()['host_packages'], 1)

    def test_bad_lock_missing_notice_tamper_and_unclaimed_file_refuse(self):
        for defect in ('lock', 'notice', 'tamper', 'extra'):
            with self.subTest(defect=defect):
                case = ConanGraphTests('test_complete_host_identity_and_original_license'); case.setUp()
                try:
                    if defect == 'lock': case.put('s/conan.lock', json.dumps({'requires': []}).encode())
                    elif defect == 'notice': case.files = [x for x in case.files if not x['path'].endswith('/licenses/LICENSE')]
                    elif defect == 'tamper': (case.root / case.folder / 'bin/zlib.dll').write_bytes(b'altered')
                    else: case.put('c/unclaimed/unknown.dll', b'unknown')
                    with self.assertRaises(closure.ClosureError): case.verify()
                finally: case.doCleanups()


class PythonPairTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.files = {}
        self.folder = 'c/p/cpython/p'; ref = 'cpython/3.12.7#' + 'c'*32
        def put(path, value):
            target = self.root / path; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(value)
            self.files[path] = hashlib.sha256(value).hexdigest()
        self.put = put
        contents = {'licenses/LICENSE': b'python notice', 'bin/python312.dll': b'conan python'}
        for path, value in contents.items(): put(self.folder + '/' + path, value)
        manifest = ('12345\n' + ''.join(path + ': ' + hashlib.md5(value, usedforsecurity=False).hexdigest() + '\n'
                                         for path, value in contents.items())).encode()
        put(self.folder + '/conanmanifest.txt', manifest)
        graph = {'graph': {'nodes': {'0': {'context':'host'}, '1': {'context':'host', 'ref':ref,
                 'rrev':'c'*32, 'package_id':'a'*40, 'prev':'b'*32,
                 'package_folder':LOGICAL+'\\'+self.folder.replace('/','\\')}}}}
        put('b/conan-install-graph.json',json.dumps(graph).encode())
        identity = {'schema':1,'source_sha':SHA,'source_tree':TREE,'graph_sha256':self.files['b/conan-install-graph.json'],
                    'packages':[{'ref':ref,'rrev':'c'*32,'package_id':'a'*40,'prev':'b'*32,
                        'package_folder':self.folder,'manifest_sha256':self.files[self.folder+'/conanmanifest.txt'],'runtime_dirs':[]}]}
        put('b/native-kit/conan-runtime-identity.json',json.dumps(identity).encode())
        put('s/conan.lock',json.dumps({'requires':[ref]}).encode())
        put('s/.github/windows-native-kit/tool-pins.json',
            json.dumps({'artifacts':[{'name':'python','version':'3.12.10'}]}).encode())
        package = LOGICAL + '\\' + self.folder.replace('/','\\')
        put('b/pj_python_bin_dirs.txt',(package+'\\bin\n'+package+'\n').encode())
        put('t/python/python.exe',b'driver exe'); put('t/python/python312.dll',b'official driver python')

    def verify(self):
        return closure.derive_verified_python_pair(self.root, [{'path':p,'sha256':h} for p,h in self.files.items()], SHA,TREE,LOGICAL)

    def test_binds_driver_and_locked_package_not_just_name(self):
        self.assertEqual(self.verify(), {'driver':'t/python/python312.dll','conan':self.folder+'/bin/python312.dll'})

    def test_bad_configured_home_or_changed_dll_fails(self):
        self.put('b/pj_python_bin_dirs.txt',b'C:\\other\\bin\nC:\\other\n')
        with self.assertRaises(closure.ClosureError): self.verify()
        self.setUp(); (self.root / (self.folder+'/bin/python312.dll')).write_bytes(b'tampered')
        with self.assertRaises(closure.ClosureError): self.verify()

    def test_version_is_derived_from_lock_and_abi_from_driver_pin(self):
        def inputs(version='3.12.17', driver='3.12.10'):
            ref='cpython/'+version+'#'+'c'*32
            graph={'graph':{'nodes':{'host':{'context':'host','ref':ref,'package_folder':'C:\\p'}}}}
            lock={'requires':[ref+'%1784130325.623']}
            pins={'artifacts':[{'name':'python','version':driver}]}
            return graph, lock, pins
        graph, lock, pins = inputs()
        self.assertEqual(closure.locked_cpython_host_node(graph,lock,pins)['ref'],
                         'cpython/3.12.17#'+'c'*32)
        for defect in ('different_recipe','different_revision','wrong_abi','missing_lock',
                       'duplicate_lock','duplicate_host','bad_graph','duplicate_driver','bad_driver'):
            with self.subTest(defect=defect):
                graph, lock, pins = inputs()
                if defect == 'different_recipe':
                    lock['requires']=['cpython/3.12.16#'+'c'*32]
                elif defect == 'different_revision':
                    lock['requires']=['cpython/3.12.17#'+'d'*32]
                elif defect == 'wrong_abi':
                    graph,lock,pins=inputs('3.13.1')
                elif defect == 'missing_lock':
                    lock['requires']=[]
                elif defect == 'duplicate_lock':
                    lock['requires']*=2
                elif defect == 'duplicate_host':
                    graph['graph']['nodes']['second']=dict(graph['graph']['nodes']['host'])
                elif defect == 'bad_graph':
                    graph={'graph':None}
                elif defect == 'duplicate_driver':
                    pins['artifacts']*=2
                else:
                    pins['artifacts'][0]['version']='3.13.0'
                with self.assertRaises(closure.ClosureError):
                    closure.locked_cpython_host_node(graph,lock,pins)

    def test_full_pair_accepts_a_different_locked_patch_version(self):
        ref='cpython/3.12.17#'+'c'*32
        graph=json.loads((self.root/'b/conan-install-graph.json').read_text(encoding='utf-8'))
        graph['graph']['nodes']['1']['ref']=ref
        self.put('b/conan-install-graph.json',json.dumps(graph).encode())
        identity=json.loads((self.root/'b/native-kit/conan-runtime-identity.json').read_text(encoding='utf-8'))
        identity['graph_sha256']=self.files['b/conan-install-graph.json']
        identity['packages'][0]['ref']=ref
        self.put('b/native-kit/conan-runtime-identity.json',json.dumps(identity).encode())
        self.put('s/conan.lock',json.dumps({'requires':[ref]}).encode())
        self.assertEqual(self.verify()['conan'],self.folder+'/bin/python312.dll')


class ConanProcessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.files = {}; self.docs = {}
        self.put('s/conan.lock', b'locked recipe refs')
        self.put('b/conan-install-graph.json', b'actual graph bytes')
        self.prefix = 'b/native-kit/conan-evidence/'
        def wp(name): return LOGICAL + '\\' + name.replace('/', '\\')
        self.wp = wp
        remotes = [{'name': name, 'url': url, 'enabled': True, 'verify_ssl': True, 'force_auth': False,
                    'allowed_packages': None, 'recipes_only': False} for name, url in (
            ('conancenter', 'https://center2.conan.io'),
            ('plotjuggler-conan', 'https://plotjuggler.jfrog.io/artifactory/api/conan/plotjuggler-conan'))]
        commands = {
            'remotes': ['remote', 'list', '--format=json'],
            'install': ['install', wp('s'), '--output-folder=' + wp('b'), '--build=missing',
                        '-r=plotjuggler-conan', '-r=conancenter', '--lockfile=' + wp('s/conan.lock'),
                        '--lockfile-partial', '-s', 'build_type=RelWithDebInfo', '-s', 'compiler.cppstd=20',
                        '-c', 'tools.build:jobs=2', '-o', 'cpython/*:shared=True', '-s',
                        'cpython/*:build_type=Release', '-s', 'compiler.version=194', '-c',
                        'tools.cmake.cmaketoolchain:generator=Ninja Multi-Config', '--format=json',
                        '--out-file=' + wp('b/conan-install-graph.json')]}
        for phase in ('remotes', 'install'):
            stdout = json.dumps(remotes).encode() if phase == 'remotes' else b''
            self.put(self.prefix + phase + '.stdout.bin', stdout)
            self.put(self.prefix + phase + '.stderr.bin', b'')
            value = {'argv': [wp('t/builder/Scripts/conan.exe'), *commands[phase]], 'cwd': wp('s'),
                     'exit_code': 0, 'conan_sha256': 'f' * 64, 'source_sha': SHA, 'source_tree': TREE,
                     'lock_sha256': self.files['s/conan.lock'], 'stdout_sha256': self.files[self.prefix + phase + '.stdout.bin'],
                     'stderr_sha256': self.files[self.prefix + phase + '.stderr.bin']}
            if phase == 'install': value['graph_sha256'] = self.files['b/conan-install-graph.json']
            self.put_json(self.prefix + phase + '.process.json', value)

    def put(self, relative, value):
        path = self.root / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(value)
        self.files[relative] = hashlib.sha256(value).hexdigest()

    def put_json(self, relative, value):
        self.docs[relative] = copy.deepcopy(value); self.put(relative, json.dumps(value).encode())

    def verify(self):
        return closure.verify_conan_process_records(self.root, [{'path': x, 'sha256': h} for x, h in self.files.items()],
                                                    SHA, TREE, LOGICAL)

    def test_binds_raw_process_output_but_does_not_claim_tool_provenance(self):
        result = self.verify()
        self.assertIn('not independently authenticated', result['scope'])
        self.assertEqual(result['graph_sha256'], self.files['b/conan-install-graph.json'])

    def test_changed_options_remote_or_process_fail(self):
        for defect in ('remote-url', 'remote-tls', 'remote-extra', 'graph', 'exit', 'binary',
                       'unexpected-arg', 'lock-path', 'stdout-tamper'):
            with self.subTest(defect=defect):
                self.setUp()
                remotes = json.loads((self.root / (self.prefix + 'remotes.stdout.bin')).read_text(encoding='utf-8'))
                remotes_record = copy.deepcopy(self.docs[self.prefix + 'remotes.process.json'])
                install_record = copy.deepcopy(self.docs[self.prefix + 'install.process.json'])
                if defect == 'remote-url': remotes[0]['url'] = 'https://untrusted.example'
                elif defect == 'remote-tls': remotes[0]['verify_ssl'] = False
                elif defect == 'remote-extra': remotes.append(copy.deepcopy(remotes[0]))
                elif defect == 'graph': install_record['graph_sha256'] = '0' * 64
                elif defect == 'exit': install_record['exit_code'] = 1
                elif defect == 'binary': install_record['conan_sha256'] = '0' * 64
                elif defect == 'unexpected-arg': install_record['argv'].append('--remote=other')
                elif defect == 'lock-path': install_record['argv'][7] = '--lockfile=C:\\other.lock'
                else: (self.root / (self.prefix + 'install.stdout.bin')).write_bytes(b'tampered')
                if defect.startswith('remote-'):
                    self.put(self.prefix + 'remotes.stdout.bin', json.dumps(remotes).encode())
                    remotes_record['stdout_sha256'] = self.files[self.prefix + 'remotes.stdout.bin']
                self.put_json(self.prefix + 'remotes.process.json', remotes_record)
                self.put_json(self.prefix + 'install.process.json', install_record)
                with self.assertRaises(closure.ClosureError): self.verify()


class CMakeProcessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name); self.files={}; self.docs={}; self.base='b/native-kit/codemodel/process/'
        self.put('b/native-kit/codemodel/query/codemodel-v2',b'')
        self.put('s/conan.lock',b'lock'); self.put('t/cmake/bin/cmake.exe',b'cmake'); self.put('t/7z/7za.exe',b'7za')
        win=lambda x: LOGICAL+'\\'+x.replace('/','\\')
        plugin=win('b/csv-prefix/plugin.dll')
        self.put('b/native-kit/csv-prebuilt.json',json.dumps({'plugin':plugin}).encode())
        self.put_json('b/native-kit/build_identity.json', {'source_sha': SHA, 'source_tree': TREE,
                      'role': 'main', 'compiler': {'path': r'C:\VS\bin\cl.exe', 'sha256': 'c' * 64}})
        qt=win('q/6.12.0/msvc2022_64'); ninja=win('t/builder/Scripts/ninja.exe')
        commands={'configure':[win('t/cmake/bin/cmake.exe'),'-S',win('s'),'-B',win('b'),
                   '-DCMAKE_TOOLCHAIN_FILE='+win('b/conan_toolchain.cmake'),'-DPJ_BUILD_TESTS=ON','-DPJ_BUILD_DEMOS=OFF',
                   '-DPJ_PLUGIN_FEEDBACK_ACCEPTANCE=ON','-DPJ_CSV_RUNTIME_PLUGIN='+plugin,'-G','Ninja Multi-Config',
                   '-DCMAKE_PREFIX_PATH='+qt,'-DCMAKE_MAKE_PROGRAM='+ninja,'-DPython3_EXECUTABLE='+win('t/python/python.exe'),
                   '-DPJ_TEST_PYTHON='+win('t/python/python.exe'),'-DPJ_IFW_TEST_ARCHIVE='+win('t/ifw/ifw.7z'),
                   '-DPJ_IFW_TEST_EXTRACTOR='+win('t/7z/7za.exe'),'-DPJ_IFW_TEST_EXTRACTOR_SHA256='+self.files['t/7z/7za.exe'],
                   '-DPJ_NATIVE_BUNDLE_MODE=ON','-DCMAKE_BUILD_TYPE=RelWithDebInfo','-DCMAKE_POLICY_DEFAULT_CMP0141=NEW',
                   '-DCMAKE_MSVC_DEBUG_INFORMATION_FORMAT=Embedded',
                   r'-DCMAKE_C_COMPILER:FILEPATH=C:\VS\bin\cl.exe', r'-DCMAKE_CXX_COMPILER:FILEPATH=C:\VS\bin\cl.exe'],
                  'build':[win('t/cmake/bin/cmake.exe'),'--build',win('b'),'--config','RelWithDebInfo','--parallel','2']}
        for phase in ('configure','build'):
            self.put(self.base+phase+'.stdout.bin', b'runtime_catalog_language_test.cpp.obj runtime_catalog_language_test.exe' if phase=='build' else b'')
            self.put(self.base+phase+'.stderr.bin',b'')
            record={'schema':1,'source_sha':SHA,'source_tree':TREE,'exit_code':0,'still_running':False,'cwd':LOGICAL,
                    'lock_sha256':self.files['s/conan.lock'],'cmake_sha256':self.files['t/cmake/bin/cmake.exe'],
                    'ninja_sha256':'c'*64,'stdout_sha256':self.files[self.base+phase+'.stdout.bin'],
                    'stderr_sha256':self.files[self.base+phase+'.stderr.bin'],'argv':commands[phase]}
            self.put_json(self.base+phase+'.process.json',record)

    def put(self,path,data):
        file=self.root/path;file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(data)
        self.files[path]=hashlib.sha256(data).hexdigest()
    def put_json(self,path,value):
        self.docs[path]=copy.deepcopy(value);self.put(path,json.dumps(value).encode())
    def verify(self):
        return closure.verify_cmake_build_records(self.root,[{'path':p,'sha256':h} for p,h in self.files.items()],
                    SHA,TREE,LOGICAL,'6.12.0',{('main','RuntimeCatalogLanguageTest')})
    def test_exact_query_commands_and_selected_build_log(self):
        self.assertIn('raw producer',self.verify()['scope'])
    def test_changed_missing_or_relative_compiler_pin_fails(self):
        for value in (None, '-DCMAKE_CXX_COMPILER:FILEPATH=cl.exe', r'-DCMAKE_CXX_COMPILER:FILEPATH=C:\Other\cl.exe'):
            with self.subTest(value=value):
                self.setUp(); path = self.base + 'configure.process.json'; record = copy.deepcopy(self.docs[path])
                if value is None: record['argv'].pop()
                else: record['argv'][-1] = value
                self.put_json(path, record)
                with self.assertRaises(closure.ClosureError): self.verify()

    def test_wrong_command_query_or_missing_real_link_marker_fails(self):
        for defect in ('query','args','exit','log'):
            with self.subTest(defect=defect):
                self.setUp(); path=self.base+'build.process.json'; record=copy.deepcopy(self.docs[path])
                if defect=='query': self.put('b/native-kit/codemodel/query/codemodel-v2',b'nonempty')
                elif defect=='args': record['argv'][-1]='16'
                elif defect=='exit': record['exit_code']=1
                else:
                    self.put(self.base+'build.stdout.bin',b'runtime_catalog_language_test.cpp.obj')
                    record['stdout_sha256']=self.files[self.base+'build.stdout.bin']
                self.put_json(path,record)
                with self.assertRaises(closure.ClosureError): self.verify()


class OfficialToolPayloadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.proof = self.root / 'r/proof'; self.proof.mkdir(parents=True)
        for name in ('tools', 'tmp'): (self.proof / name).mkdir()
        self.files = {}
        self.original_pth = b'python312.zip\n.\n'
        self.put('t/cmake/bin/cmake.exe', b'official cmake')
        self.put('t/python/python.exe', b'official python')
        self.pth = self.original_pth + ''.join(str(self.root / x) + '\n' for x in
                         ('s', 's/scripts', 's/tests', 's/packaging/localization')).encode()
        self.put('t/python/python312._pth', self.pth)
        self.put('t/ifw/ifw.7z', b'official ifw archive')
        self.put('t/ifw/notices/doc/LICENSE.txt', b'ifw notice')
        self.put('t/7z/License.txt', b'7z notice')
        artifacts = [{'name': name, 'file': name + '.archive', 'sha256': self.files['t/ifw/ifw.7z']
                      if name == 'ifw' else 'a' * 64} for name in ('cmake', 'python', '7zr-bootstrap', '7z-extra', 'ifw')]
        self.put('s/.github/windows-native-kit/tool-pins.json', json.dumps({'artifacts': artifacts}).encode())

    def put(self, relative, data):
        path = self.root / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
        self.files[relative] = hashlib.sha256(data).hexdigest()

    def verify(self):
        class ToolError(Exception): pass
        def download(pin, path): path.write_bytes(b'fixture'); return {}
        def extract(archive, target, prefix=''):
            if target.name == 'cmake':
                (target / 'bin').mkdir(parents=True); (target / 'bin/cmake.exe').write_bytes(b'official cmake')
            else:
                target.mkdir(); (target / 'python.exe').write_bytes(b'official python')
                (target / 'python312._pth').write_bytes(self.original_pth)
        helper = types.SimpleNamespace(ToolError=ToolError, download=download, extract_zip=extract)
        def sevenzip(argv, **kwargs):
            if argv[1] == 'l':
                if str(argv[-1]).endswith('ifw.7z'):
                    return types.SimpleNamespace(returncode=0, stdout=b'Path = doc/LICENSE.txt\nSize = 10\nFolder = -\n')
                return types.SimpleNamespace(returncode=0, stdout=b'Path = License.txt\nSize = 9\nFolder = -\n')
            return types.SimpleNamespace(returncode=0, stdout=b'ifw notice' if argv[-1] == 'doc/LICENSE.txt' else b'7z notice')
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(closure, '_module', return_value=helper))
            stack.enter_context(mock.patch.object(closure, '_pinned_tool', return_value=Path('pinned')))
            stack.enter_context(mock.patch.object(closure, '_extractor', return_value=Path('7za')))
            stack.enter_context(mock.patch.object(closure, '_extract_env', return_value={}))
            stack.enter_context(mock.patch.object(closure.shutil, 'disk_usage', return_value=types.SimpleNamespace(free=8 * 1024**3)))
            stack.enter_context(mock.patch.object(closure.subprocess, 'run', side_effect=sevenzip))
            return closure.verify_clean_tool_payload(self.root, [{'path': x, 'sha256': h} for x, h in self.files.items()], self.proof)

    def test_matches_zip_members_path_extension_and_original_notices(self):
        result = self.verify()
        self.assertEqual((result['cmake_files'], result['python_files'], result['ifw_notices']), (1, 2, 1))
        self.assertIn('after trusted process startup', result['scope'])

    def test_rejects_rehashed_tampered_pth_or_notice(self):
        for path in ('t/python/python312._pth', 't/ifw/notices/doc/LICENSE.txt'):
            with self.subTest(path=path):
                self.setUp(); self.put(path, b'tampered but manifest rehashed')
                with self.assertRaises(closure.ClosureError): self.verify()


class FixedDownloadTests(unittest.TestCase):
    def test_fixed_download_checks_size_and_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            data = b'official bytes'
            pin = {'file': 'qt.7z', 'url': 'https://download.qt.io/online/qt.7z',
                   'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
            with mock.patch.object(closure.urllib.request, 'urlopen', return_value=io.BytesIO(data)):
                self.assertEqual(closure.download_fixed_artifact(pin, directory).read_bytes(), data)
            with mock.patch.object(closure.urllib.request, 'urlopen', return_value=io.BytesIO(data)):
                with self.assertRaises(closure.ClosureError): closure.download_fixed_artifact(pin, directory)
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.object(closure.urllib.request, 'urlopen', return_value=io.BytesIO(data + b'extra')):
                with self.assertRaises(closure.ClosureError): closure.download_fixed_artifact(pin, directory)


class QtExtractionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.qt = self.root / 'q/6.12.0/msvc2022_64'
        self.contents = {'bin/Qt6Core.dll': b'core', 'bin/lrelease.exe': b'lrelease',
                         'bin/lupdate.exe': b'lupdate', 'bin/rcc.exe': b'rcc',
                         'licenses/qtbase/LICENSE.txt': b'original notice'}
        for name, data in self.contents.items():
            path = self.qt / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
        archives = self.root / 'd/qt-archives'; archives.mkdir(parents=True)
        self.archive = archives / 'qtbase.7z'; self.archive.write_bytes(b'official synthetic archive')
        (self.root / 'b/native-kit').mkdir(parents=True)
        url = 'https://download.qt.io/online/qtsdkrepository/test/qtbase.7z'
        pin = {'file': 'qtbase.7z', 'url': url, 'source': url + '.mirrorlist',
               'sha256': hashlib.sha256(self.archive.read_bytes()).hexdigest(), 'bytes': self.archive.stat().st_size}
        self.policy = {'qt_version': '6.12.0', 'qt_archives': [pin]}
        self.tamper = False

    def sevenzip(self, argv, **kwargs):
        if argv[1] == 'l':
            blocks = []
            for path, data in self.contents.items():
                blocks.append('Path = 6.12.0/msvc2022_64/' + path + '\nSize = ' + str(len(data)) + '\nAttributes = A\nEncrypted = -')
            return types.SimpleNamespace(returncode=0, stdout=('\n\n'.join(blocks) + '\n').encode(), stderr=b'')
        target = Path(next(x[2:] for x in argv if x.startswith('-o')))
        listing = Path(next(x[1:] for x in argv if x.startswith('@'))).read_text(encoding='utf-8').splitlines()
        for name in listing:
            relative = name.removeprefix('6.12.0/msvc2022_64/')
            data = self.contents[relative]
            if self.tamper and relative.endswith('Qt6Core.dll'): data = b'evil'
            out = target.joinpath(*name.split('/')); out.parent.mkdir(parents=True, exist_ok=True); out.write_bytes(data)
        return types.SimpleNamespace(returncode=0, stdout=b'', stderr=b'')

    def prepare(self):
        with mock.patch.object(closure, '_extractor', return_value=Path('7za')), \
             mock.patch.object(closure, '_extract_env', return_value={}), \
             mock.patch.object(closure.subprocess, 'run', side_effect=self.sevenzip), \
             mock.patch.object(closure.shutil, 'disk_usage', return_value=types.SimpleNamespace(free=8 * 1024**3)):
            return closure.prepare_qt_declarations(self.root, self.policy, self.root / 'b/native-kit/reference')

    def test_authenticates_archive_and_compares_every_selected_member(self):
        result = self.prepare()
        self.assertEqual({x['source'] for x in result['files']}, set(self.contents))
        origin = next(iter(result['origins'].values()))
        self.assertEqual(origin['revision'], self.policy['qt_archives'][0]['sha256'])
        self.assertIn('q/6.12.0/msvc2022_64/licenses/qtbase/LICENSE.txt', origin['license_files'])

    def test_windows_case_alias_is_scanned_once(self):
        # Simulate a case-insensitive lookup even on a case-sensitive host.
        # Looking up both spellings must not enumerate the same directory twice.
        real_is_dir, real_rglob = Path.is_dir, Path.rglob
        alias = str(self.qt / 'LICENSES')
        def is_dir(path):
            return True if str(path) == alias else real_is_dir(path)
        def rglob(path, pattern):
            return real_rglob(self.qt / 'licenses', pattern) if str(path) == alias else real_rglob(path, pattern)
        with mock.patch.object(Path, 'is_dir', is_dir), mock.patch.object(Path, 'rglob', rglob):
            selected, notices = closure._qt_selected_files(self.qt)
        self.assertEqual(set(selected), set(self.contents))
        self.assertEqual(notices, ['licenses/qtbase/LICENSE.txt'])

    def test_distinct_case_colliding_qt_directories_are_rejected(self):
        # Simulate two distinct directory entries even on a Windows volume,
        # where creating such a pair may be unavailable.
        real_iterdir, real_is_dir = Path.iterdir, Path.is_dir
        alias = self.qt / 'LICENSES'
        def iterdir(path):
            entries = list(real_iterdir(path))
            return iter(entries + [alias]) if str(path) == str(self.qt) else iter(entries)
        def is_dir(path):
            return True if str(path) == str(alias) else real_is_dir(path)
        with mock.patch.object(Path, 'iterdir', iterdir), mock.patch.object(Path, 'is_dir', is_dir):
            with self.assertRaisesRegex(closure.ClosureError, 'case-colliding'):
                closure._qt_selected_files(self.qt)

    def test_changed_extracted_member_and_missing_notice_fail(self):
        self.tamper = True
        with self.assertRaisesRegex(closure.ClosureError, 'differ'): self.prepare()
        other = QtExtractionTests('test_authenticates_archive_and_compares_every_selected_member')
        other.setUp()
        try:
            (other.qt / 'licenses/qtbase/LICENSE.txt').unlink()
            with self.assertRaisesRegex(closure.ClosureError, 'license'): other.prepare()
        finally:
            other.doCleanups()


class PendingModernPolicyTests(unittest.TestCase):
    def test_repository_policy_is_pending_and_all_policy_apis_fail_before_work(self):
        import inspect
        policy = json.loads((ROOT / '.github/windows-native-kit/ci-closure-policy.json').read_text(encoding="utf-8"))
        self.assertEqual(policy['approval_status'], 'pending-modern-native-review')
        checked = []
        for name, function in vars(closure).items():
            if not inspect.isfunction(function) or function.__module__ != closure.__name__:
                continue
            signature = inspect.signature(function)
            if 'policy' not in signature.parameters:
                continue
            arguments = {key: policy if key == 'policy' else None
                         for key, parameter in signature.parameters.items()
                         if parameter.default is inspect.Parameter.empty or key == 'policy'}
            with self.subTest(entry=name), self.assertRaisesRegex(closure.ClosureError, 'pending-modern-native-review'):
                function(**arguments)
            checked.append(name)
        self.assertIn('derive_partition', checked)
        self.assertIn('verify_staged_inputs', checked)
        self.assertIn('candidate_provenance', checked)
        self.assertIn('prepare_qt_declarations', checked)

    def test_unknown_approval_label_cannot_enable_the_policy(self):
        for label in ('approved', 'reviewed', '', False):
            with self.subTest(label=label), self.assertRaises(closure.ClosureError):
                closure.require_reviewed_policy({'approval_status': label})


if __name__ == '__main__': unittest.main()
