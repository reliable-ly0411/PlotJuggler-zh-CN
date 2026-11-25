# SPDX-License-Identifier: MPL-2.0
"""Synthetic preservation checks; no Windows VM or CI process is run."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('native_ci_evidence', ROOT / 'scripts/windows/collect_native_ci_evidence.py')
evidence = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evidence)

BINDING = {'schema': 1, 'scope': 'github-hosted-windows-ci', 'source_sha': 'a' * 40,
           'source_tree': 'b' * 40, 'configuration': 'RelWithDebInfo',
           'archive_sha256': 'c' * 64, 'manifest_sha256': 'd' * 64}


def write_json(path, value):
    path.write_text(json.dumps(value), encoding='utf-8')


class NativeCIEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.parent = Path(self.temporary.name)
        self.root = self.parent / 'kit'
        self.root.mkdir()
        (self.root / 'r').mkdir()
        self.run = self.root / 'r' / ('ci-' + '1' * 32)
        self.run.mkdir()
        write_json(self.run / 'artifact-binding.json', BINDING)
        self.output = self.parent / 'out'

    def test_completed_run_copies_raw_known_files_and_binds_hashes(self):
        main = self.run / 'main'; main.mkdir()
        original = b'\xff\x00raw\r\nstdout\n'
        (main / 'stdout.bin').write_bytes(original)
        (main / 'LastTest.log').write_bytes(b'last\r\n')
        (main / 'secret-unrelated.txt').write_text('not allowed', encoding='utf-8')
        write_json(self.run / 'summary.json', {'status': 'planned-ci-groups-completed'})
        screenshots = self.run / 'screenshots'; screenshots.mkdir()
        (screenshots / 'full-apbin-en_US.png').write_bytes(b'PNG')
        (screenshots / 'private.png').write_bytes(b'not included')
        receipt = evidence.collect(self.root, self.output, BINDING, 'success', 'clean')
        self.assertEqual(receipt['run_status'], 'planned-ci-groups-completed')
        self.assertEqual(receipt['binding'], BINDING)
        self.assertEqual((self.output / 'main/stdout.bin').read_bytes(), original)
        self.assertEqual((self.output / 'main/LastTest.log').read_bytes(), b'last\r\n')
        self.assertTrue((self.output / 'screenshots/full-apbin-en_US.png').is_file())
        self.assertFalse((self.output / 'screenshots/private.png').exists())
        self.assertFalse((self.output / 'main/secret-unrelated.txt').exists())
        files = {row['path']: row for row in receipt['files']}
        self.assertEqual(files['main/stdout.bin']['sha256'], hashlib.sha256(original).hexdigest())
        self.assertEqual(json.loads((self.output / 'evidence-manifest.json').read_text(encoding='utf-8')), receipt)

    def test_incomplete_and_no_run_are_not_success(self):
        write_json(self.run / 'incomplete.json', {'status': 'incomplete', 'suites': {'main': 'uncertain'}})
        receipt = evidence.collect(self.root, self.output, BINDING, 'failure', 'producer')
        self.assertEqual(receipt['run_status'], 'incomplete')
        self.assertTrue((self.output / 'incomplete.json').is_file())
        with self.assertRaises(evidence.EvidenceError):
            evidence.collect(self.root, self.parent / 'second', BINDING, 'success', 'producer')
        empty = self.parent / 'empty'; empty.mkdir()
        receipt = evidence.collect(empty, self.parent / 'none', BINDING, 'failure', 'clean')
        self.assertEqual(receipt['run_status'], 'not-started')
        with self.assertRaises(evidence.EvidenceError):
            evidence.collect(empty, self.parent / 'bad', BINDING, 'success', 'clean')

    def test_mismatched_binding_and_double_run_are_rejected(self):
        write_json(self.run / 'artifact-binding.json', dict(BINDING, archive_sha256='f' * 64))
        with self.assertRaises(evidence.EvidenceError):
            evidence.collect(self.root, self.output, BINDING, 'failure', 'clean')
        other = self.root / 'r' / ('ci-' + '2' * 32); other.mkdir()
        with self.assertRaises(evidence.EvidenceError):
            evidence.collect(self.root, self.parent / 'other', BINDING, 'failure', 'clean')

    def test_expected_log_symlink_and_hardlink_are_rejected(self):
        main = self.run / 'main'; main.mkdir()
        outside = self.parent / 'outside.txt'; outside.write_text('outside', encoding='utf-8')
        try:
            (main / 'stdout.bin').symlink_to(outside)
        except OSError:
            self.skipTest('symlink creation is not available')
        with self.assertRaises((evidence.EvidenceError, evidence.audit.AuditError)):
            evidence.collect(self.root, self.output, BINDING, 'failure', 'clean')
        (main / 'stdout.bin').unlink()
        try:
            os.link(outside, main / 'stdout.bin')
        except OSError:
            self.skipTest('hardlink creation is not available')
        with self.assertRaises(evidence.audit.AuditError):
            evidence.collect(self.root, self.parent / 'hardlink', BINDING, 'failure', 'clean')

    def test_bootstrap_must_match_and_existing_output_is_not_overwritten(self):
        bootstrap = self.parent / 'bootstrap.json'
        write_json(bootstrap, {'status': 'verified', **BINDING})
        receipt = evidence.collect(self.root, self.output, BINDING, 'failure', 'producer', bootstrap)
        self.assertIn('bootstrap.json', {row['path'] for row in receipt['files']})
        with self.assertRaises(evidence.EvidenceError):
            evidence.collect(self.root, self.output, BINDING, 'failure', 'producer', bootstrap)
        write_json(bootstrap, {'status': 'verified', **dict(BINDING, source_tree='f' * 40)})
        with self.assertRaises(evidence.EvidenceError):
            evidence.collect(self.root, self.parent / 'bad-bootstrap', BINDING, 'failure', 'producer', bootstrap)

    def test_success_needs_bound_pre_execution_python_origin_when_requested(self):
        write_json(self.run / 'summary.json', {'status': 'planned-ci-groups-completed'})
        origin = self.parent / 'python-origin.json'
        with self.assertRaises(evidence.EvidenceError):
            evidence.collect(self.root, self.output, BINDING, 'success', 'clean', python_origin=origin,
                             require_origin=True)
        write_json(origin, {'schema': 1, 'scope': 'disposable-github-hosted-windows-ci', **BINDING,
                            'members': [{'path': 't/python/python.exe', 'sha256': 'e' * 64}]})
        # The Python proof has a more specific scope than the run binding.
        record = json.loads(origin.read_text(encoding='utf-8'))
        record['scope'] = 'disposable-github-hosted-windows-ci'
        write_json(origin, record)
        receipt = evidence.collect(self.root, self.parent / 'with-origin', BINDING, 'success', 'clean',
                                   python_origin=origin, require_origin=True)
        self.assertIn('python-origin.json', {row['path'] for row in receipt['files']})
        write_json(origin, dict(record, source_sha='f' * 40))
        with self.assertRaises(evidence.EvidenceError):
            evidence.collect(self.root, self.parent / 'wrong-origin', BINDING, 'success', 'clean',
                             python_origin=origin, require_origin=True)

    def test_cli_refuses_non_windows_or_non_hosted_environment(self):
        args = ['collector', '--root', str(self.root), '--output', str(self.output), '--source-sha', 'a' * 40,
                '--source-tree', 'b' * 40, '--archive-sha256', 'c' * 64, '--manifest-sha256', 'd' * 64,
                '--scope', 'clean', '--outcome', 'failure']
        with mock.patch.object(evidence.sys, 'platform', 'linux'), mock.patch.object(evidence.sys, 'argv', args):
            self.assertEqual(evidence.main(), 1)
        self.assertFalse(self.output.exists())

    def test_workflow_keeps_two_run_receipts_separate_from_the_one_raw_kit(self):
        workflow = (ROOT / '.github/workflows/zh-4x-ci.yml').read_text(encoding='utf-8')
        producer = workflow.split('  windows-native-test-build:\n', 1)[1].split('\n  windows-native-test-clean:', 1)[0]
        clean = workflow.split('  windows-native-test-clean:\n', 1)[1].split('\n  source-checks:', 1)[0]
        for job, name, scope in ((producer, 'windows-native-producer-evidence-', 'producer'),
                                 (clean, 'windows-native-clean-evidence-', 'clean')):
            self.assertIn(name, job)
            self.assertIn('--scope ' + scope + ' --outcome $env:VERIFY_OUTCOME', job)
            self.assertIn('if: always() && steps.native_evidence.outcome == \'success\'', job)
            self.assertLess(job.index('id: native_verify'), job.index('id: native_evidence'))
        self.assertIn('archive: false', producer)
        self.assertNotIn('archive: false', clean)
        needs = re.search(r'(?m)^\s*needs:\s*\[([^]]+)\]', clean)
        self.assertIsNotNone(needs)
        self.assertEqual({part.strip() for part in needs.group(1).split(',')},
                         {'windows-native-test-build', 'windows-native-media'})


if __name__ == '__main__':
    unittest.main()
