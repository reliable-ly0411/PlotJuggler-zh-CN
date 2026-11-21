# SPDX-License-Identifier: MPL-2.0
"""Reject swapped WASM lanes, probe kinds and corrupted downloaded bytes."""

import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('wasm_receipt', ROOT / 'packaging/localization/wasm_receipt.py')
RECEIPT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RECEIPT)


class WasmReceiptTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.upstream = self.root / 'upstream'
        self.controller = self.root / 'controller'
        for path in (self.upstream, self.controller):
            path.mkdir()
            subprocess.run(['git', 'init', '-q', str(path)], check=True)
            subprocess.run(['git', '-C', str(path), 'config', 'user.name', 'Fixture'], check=True)
            subprocess.run(['git', '-C', str(path), 'config', 'user.email', 'fixture@example.invalid'], check=True)
        self.upstream_sha = self.commit(self.upstream, 'upstream')
        baseline = self.controller / 'docs/localization/upstream-baseline.json'
        baseline.parent.mkdir(parents=True)
        baseline.write_text(json.dumps({'upstream_commit': self.upstream_sha}), encoding='utf-8')
        (self.controller / 'versions.env').write_text('PJ_APP_VERSION=1.0.0\n', encoding='utf-8')
        budget = self.controller / 'scripts/wasm_size_budget.mjs'
        budget.parent.mkdir()
        budget.write_text('// frozen fixture budget\n', encoding='utf-8')
        self.controller_sha = self.commit(self.controller, 'controller')
        self.package = self.controller / 'build/deploy'
        self.package.mkdir(parents=True)
        entries = []
        for name, data in [('assets/id/app.wasm', b'wasm'), ('assets/id/python_stdlib.zip', b'python'), ('presets/data', b'preset')]:
            file = self.package / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(data)
            entries.append({'path': name, 'representations': {'identity': {'path': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}}})
        self.manifest = self.package / 'manifest.json'
        self.manifest.write_text(json.dumps({'format': 'org.plotjuggler.wasm-deployment.v1', 'bundleId': 'fixture', 'version': '1.0.0', 'packagingRuntime': {}, 'files': entries}), encoding='utf-8')
        self.cache = self.controller / 'build/CMakeCache.txt'
        self.cache.write_text('PJ_WASM_ENABLE_INGRESS_PROBE:BOOL=OFF\n' + ''.join(f'PJ_WASM_WITH_{f}:BOOL=ON\n' for f in ['SCENE2D', 'SCENE3D', 'PYTHON']), encoding='utf-8')
        self.args = argparse.Namespace(mode='capture', role='localized', kind='production',
            source_repository='fixture/localized', source_sha=self.controller_sha,
            controller_sha=self.controller_sha, source_root=self.controller,
            controller_root=self.controller, package=['build/deploy'], cache=self.cache,
            output=self.root / 'receipt.json')

    def commit(self, path, message):
        subprocess.run(['git', '-C', str(path), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(path), 'commit', '--allow-empty', '-qm', message], check=True)
        return RECEIPT.git(path, 'rev-parse', 'HEAD')

    def run_receipt(self):
        with contextlib.redirect_stdout(io.StringIO()):
            RECEIPT.run(self.args)

    def test_round_trip_and_real_startup_total(self):
        self.run_receipt()
        report = json.loads(self.args.output.read_text(encoding='utf-8'))
        self.assertEqual(report['packages']['build/deploy']['startup_bytes'], 4)
        self.assertEqual(report['packages']['build/deploy']['total_bytes'], 16)
        self.args.mode = 'verify'
        self.run_receipt()

    def test_rejects_wrong_sha(self):
        self.args.source_sha = 'a' * 40
        with self.assertRaisesRegex(ValueError, 'Checkout SHA'):
            self.run_receipt()

    def test_rejects_localized_tree_labeled_upstream(self):
        self.args.role = 'upstream'
        self.args.source_repository = 'PlotJuggler/PlotJuggler'
        with self.assertRaisesRegex(ValueError, 'recorded upstream'):
            self.run_receipt()

    def test_accepts_exact_pinned_upstream_identity(self):
        self.args.mode = 'identity'
        self.args.role = 'upstream'
        self.args.source_repository = 'PlotJuggler/PlotJuggler'
        self.args.source_sha = self.upstream_sha
        self.args.source_root = self.upstream
        self.run_receipt()

    def select_planned_source(self, role, path, sha, repository, tree=None):
        record = self.controller / 'docs/localization/wasm-validation-targets.json'
        record.write_text(json.dumps({role: {
            'repository': repository, 'sha': sha,
            'tree': tree or RECEIPT.git(path, 'rev-parse', 'HEAD^{tree}'),
        }}), encoding='utf-8')
        self.args.controller_sha = self.commit(self.controller, 'validation controller')
        self.args.mode = 'identity'
        self.args.role = role
        self.args.source_root = path
        self.args.source_sha = sha
        self.args.source_repository = repository

    def test_exact_localized_product_may_differ_from_controller_with_plan(self):
        self.select_planned_source('localized', self.upstream, self.upstream_sha, 'fixture/localized')
        self.assertNotEqual(self.args.source_sha, self.args.controller_sha)
        self.run_receipt()

    def test_plan_does_not_relabel_other_checkout_as_localized(self):
        self.select_planned_source('localized', self.upstream, self.upstream_sha, 'fixture/localized')
        self.args.source_repository = 'fixture/other'
        with self.assertRaisesRegex(ValueError, 'distinct|exact validation role'):
            self.run_receipt()

    def test_plan_requires_exact_tree(self):
        self.select_planned_source('localized', self.upstream, self.upstream_sha, 'fixture/localized', tree='f' * 40)
        with self.assertRaisesRegex(ValueError, 'exact validation role'):
            self.run_receipt()

    def test_comparator_needs_plan(self):
        self.args.mode = 'identity'
        self.args.role = 'upstream-comparator'
        self.args.source_repository = 'PlotJuggler/PlotJuggler'
        with self.assertRaisesRegex(ValueError, 'official source plan'):
            self.run_receipt()

    def test_comparator_cannot_relabel_frozen_reference(self):
        self.select_planned_source('upstream-comparator', self.upstream, self.upstream_sha, 'PlotJuggler/PlotJuggler')
        with self.assertRaisesRegex(ValueError, 'not the frozen'):
            self.run_receipt()

    def test_comparator_accepts_distinct_exact_official_source(self):
        newer = self.commit(self.upstream, 'same-source comparator')
        self.select_planned_source('upstream-comparator', self.upstream, newer, 'PlotJuggler/PlotJuggler')
        self.run_receipt()

    def test_existing_budget_scripts_keep_independent_boundaries(self):
        for script, budget in [('wasm_size_budget.mjs', 16932000), ('wasm_size_budget.mjs', 20000000),
                               ('wasm_localized_size_budget.mjs', 26000000)]:
            for amount in [budget, budget + 1]:
                with self.subTest(script=script, amount=amount):
                    manifest = self.root / 'budget.json'
                    manifest.write_text(json.dumps({'files': [{'path': 'app.wasm', 'representations': {'identity': {'bytes': amount}}}]}), encoding='utf-8')
                    command = ['node', str(ROOT / 'scripts' / script), str(manifest)]
                    if script == 'wasm_size_budget.mjs':
                        command.append(str(budget))
                    result = subprocess.run(command, capture_output=True, text=True)
                    self.assertEqual(result.returncode, int(amount > budget), result.stdout + result.stderr)

    def test_rejects_probe_configuration_mismatch(self):
        self.args.kind = 'acceptance'
        with self.assertRaisesRegex(ValueError, 'probe configuration'):
            self.run_receipt()

    def test_rejects_production_receipt_as_acceptance(self):
        self.run_receipt()
        self.args.kind = 'acceptance'
        self.args.mode = 'verify'
        with self.assertRaisesRegex(ValueError, 'receipt identity'):
            self.run_receipt()

    def test_rejects_corrupted_file(self):
        self.run_receipt()
        (self.package / 'assets/id/app.wasm').write_bytes(b'bad!')
        self.args.mode = 'verify'
        with self.assertRaisesRegex(ValueError, 'representation mismatch'):
            self.run_receipt()

    def test_rejects_missing_file(self):
        (self.package / 'assets/id/app.wasm').unlink()
        with self.assertRaises(FileNotFoundError):
            self.run_receipt()

    def test_rejects_extra_downloaded_file(self):
        self.run_receipt()
        (self.package / 'unrecorded').write_text('extra', encoding='utf-8')
        self.args.mode = 'verify'
        with self.assertRaisesRegex(ValueError, 'receipt identity or bytes'):
            self.run_receipt()

    def test_rejects_changed_capability_probe_support(self):
        support = self.controller / 'build/capability.js'
        support.write_text('probe', encoding='utf-8')
        self.args.extra = ['build/capability.*']
        self.run_receipt()
        support.write_text('changed', encoding='utf-8')
        self.args.mode = 'verify'
        with self.assertRaisesRegex(ValueError, 'receipt identity or bytes'):
            self.run_receipt()

    def test_rejects_manifest_path_escape(self):
        data = json.loads(self.manifest.read_text(encoding='utf-8'))
        data['files'][0]['representations']['identity']['path'] = '../outside'
        self.manifest.write_text(json.dumps(data), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Unsafe artifact'):
            self.run_receipt()

    def test_rejects_disabled_shipped_feature(self):
        self.cache.write_text(self.cache.read_text(encoding='utf-8').replace('PJ_WASM_WITH_PYTHON:BOOL=ON', 'PJ_WASM_WITH_PYTHON:BOOL=OFF'), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Required shipped feature'):
            self.run_receipt()

    def test_rejects_source_modification(self):
        (self.controller / 'versions.env').write_text('changed', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Tracked source'):
            self.run_receipt()


if __name__ == '__main__':
    unittest.main()
