# SPDX-License-Identifier: MPL-2.0
"""Review and fixture/dependency selection use synthetic CTest metadata only."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('native_review', ROOT / 'scripts/windows/native_test_review.py')
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


def case(name, **props):
    return {'name': name, 'properties': [{'name': key, 'value': value} for key, value in props.items()]}


def discovery():
    return {'kind': 'ctestInfo', 'tests': [case('setup', FIXTURES_SETUP=['f']),
            case('target', FIXTURES_REQUIRED=['f'], DEPENDS=['prior']), case('prior'),
            case('cleanup', FIXTURES_CLEANUP=['f'], DEPENDS=['setup', 'target']), case('disabled', DISABLED=True)]}


class NativeReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.evidence = self.root / 'independent-review.txt'; self.evidence.write_text('reviewed exact source and cases', encoding='utf-8')
        self.evidence_record = {'path': 'independent-review.txt', 'sha256': hashlib.sha256(self.evidence.read_bytes()).hexdigest()}
        self.identity = {'sid': 'S-1-5-21-1-500', 'session': 1, 'integrity_rid': 12288}

    def record(self):
        return {'schema': 1, 'source_sha': 'a' * 40, 'source_tree': 'b' * 40, 'manifest_sha256': 'c' * 64,
                'probe_sha256': 'd' * 64, 'preflight_sha256': 'e' * 64, 'identity': self.identity,
                'session_review': {'status': 'approved', 'reason': 'independent active desktop evidence',
                                   'evidence': [self.evidence_record]},
                'suites': [{'id': 'main', 'discovery': {'status': 'approved', 'reason': 'static initialization reviewed',
                                                       'evidence': [self.evidence_record]},
                            'groups': [{'name': 'safe', 'status': 'approved', 'reason': 'source and host audit',
                                        'cases': ['setup', 'target', 'prior', 'cleanup'], 'evidence': [self.evidence_record],
                                        'runtime_paths_review': {'status': 'approved', 'reason': 'argv, cwd and relative paths reviewed',
                                                                 'evidence': [self.evidence_record]}},
                                       {'name': 'disabled', 'status': 'disabled', 'reason': 'disabled by source',
                                        'cases': ['disabled'], 'evidence': [self.evidence_record]}]}]}

    def validate(self, record=None):
        return review.validate_review(record or self.record(), self.root, self.identity, 'a' * 40, 'b' * 40,
                                      'c' * 64, 'd' * 64, 'e' * 64, {'main': discovery()})

    def test_depends_and_fixture_setup_cleanup_are_all_in_closure(self):
        self.assertEqual(review.selection_closure(discovery(), {'target'}), {'target', 'prior', 'setup', 'cleanup'})
        # Cleanup depends on target, so starting with setup also closes over
        # the entire transitive dependency and required-fixture graph.
        self.assertEqual(review.selection_closure(discovery(), {'setup'}), {'setup', 'cleanup', 'target', 'prior'})

    def test_setup_introduced_by_dependency_still_adds_cleanup(self):
        doc = {'kind': 'ctestInfo', 'tests': [case('setup', FIXTURES_SETUP=['f']),
               case('dependent', DEPENDS=['setup']), case('cleanup', FIXTURES_CLEANUP=['f'])]}
        self.assertEqual(review.selection_closure(doc, {'dependent'}), {'dependent', 'setup', 'cleanup'})
        decisions = {name: {'status': 'approved', 'reason': 'review', 'evidence': [], 'group': 'g'}
                     for name in ('setup', 'dependent')}
        decisions['cleanup'] = {'status': 'safety_unreviewed', 'reason': 'not reviewed', 'evidence': [], 'group': 'other'}
        with self.assertRaisesRegex(review.ReviewError, 'cleanup'):
            review.approved_selection(doc, decisions, 'reviewed-subset', {'dependent'})

    def test_unapproved_fixture_or_dependency_refuses_group(self):
        decisions = {x: {'status': 'approved', 'reason': 'review', 'evidence': [], 'group': 'g'} for x in ('target', 'setup', 'cleanup')}
        decisions['prior'] = {'status': 'safety_unreviewed', 'reason': 'not audited', 'evidence': [], 'group': 'other'}
        decisions['disabled'] = {'status': 'disabled', 'reason': 'disabled', 'evidence': [], 'group': 'other'}
        with self.assertRaisesRegex(review.ReviewError, 'prior'):
            review.approved_selection(discovery(), decisions, 'reviewed-subset')

    def test_full_requires_every_case_and_subset_lists_disabled(self):
        decisions = self.validate()['main']
        selected, unrun = review.approved_selection(discovery(), decisions, 'reviewed-subset')
        self.assertEqual(selected, {'target', 'prior', 'setup', 'cleanup'})
        self.assertEqual([(x['case'], x['status']) for x in unrun], [('disabled', 'disabled')])
        with self.assertRaises(review.ReviewError): review.approved_selection(discovery(), decisions, 'full')

    def test_record_binds_actual_probe_identity_and_complete_case_partition(self):
        for defect in ('probe', 'preflight', 'sid', 'missing-case', 'duplicate-case', 'unreviewed-discovery', 'no-evidence', 'no-session-proof', 'no-path-proof'):
            record = self.record()
            if defect == 'probe': record['probe_sha256'] = 'f' * 64
            elif defect == 'preflight': record['preflight_sha256'] = 'f' * 64
            elif defect == 'sid': record['identity'] = dict(self.identity, sid='S-1-5-18')
            elif defect == 'missing-case': record['suites'][0]['groups'][0]['cases'].remove('target')
            elif defect == 'duplicate-case': record['suites'][0]['groups'][1]['cases'].append('target')
            elif defect == 'unreviewed-discovery': record['suites'][0]['discovery']['status'] = 'unreviewed'
            elif defect == 'no-evidence': record['suites'][0]['groups'][0]['evidence'] = []
            elif defect == 'no-session-proof': record['session_review']['evidence'] = []
            else: record['suites'][0]['groups'][0]['runtime_paths_review']['evidence'] = []
            with self.subTest(defect=defect), self.assertRaises(review.ReviewError): self.validate(record)

    def test_modified_or_external_evidence_fails(self):
        record = self.record(); self.evidence.write_text('changed', encoding='utf-8')
        with self.assertRaises(review.ReviewError): self.validate(record)
        record['suites'][0]['discovery']['evidence'] = [{'path': '../outside', 'sha256': 'a' * 64}]
        with self.assertRaises(review.ReviewError): self.validate(record)

    def test_disabled_case_cannot_be_approved(self):
        record = self.record(); record['suites'][0]['groups'][1]['status'] = 'approved'
        with self.assertRaises(review.ReviewError): self.validate(record)

    def test_missing_dependency_or_fixture_fails_closed(self):
        d = discovery(); d['tests'][1]['properties'][1]['value'] = ['not-registered']
        with self.assertRaises(review.ReviewError): review.selection_closure(d, {'target'})
        d = discovery(); d['tests'][1]['properties'][0]['value'] = ['not-registered-fixture']
        with self.assertRaises(review.ReviewError): review.selection_closure(d, {'target'})


if __name__ == '__main__':
    unittest.main()
