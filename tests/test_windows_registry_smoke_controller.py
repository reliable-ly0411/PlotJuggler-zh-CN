# SPDX-License-Identifier: MPL-2.0
"""Exercise the controller with fake self-owned keys, never the OS registry."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('registry_smoke', ROOT / 'scripts/windows/native_registry_smoke/run_smoke.py')
smoke = importlib.util.module_from_spec(spec); spec.loader.exec_module(smoke)

NORMAL = (b'Owned late sentinel: HKCU\\Software\\PJFixtureLate-11111111-1111-4111-8111-111111111111\n'
          b'Private test registry: HKCU\\PlotJugglerTest-22222222-2222-4222-8222-222222222222\n'
          b'Native guard initialized; QApplication-free lifecycle probe.\n'
          b'Late QSettings write failed closed; self-owned real sentinel untouched.\n')
FAULT = (b'Owned late sentinel: HKCU\\Software\\PJFixtureLate-33333333-3333-4333-8333-333333333333\n'
         b'Private test registry: HKCU\\PlotJugglerTest-44444444-4444-4444-8444-444444444444\n'
         b'Native guard initialized; QApplication-free lifecycle probe.\n'
         b'Injected owned-key cleanup failure: 5\n')


class FakeRegistry:
    def __init__(self, present): self.present = set(present); self.removed = []; self.queried = []
    def exists(self, key): self.queried.append(key); return key in self.present
    def remove_exact_owned(self, key): self.present.remove(key); self.removed.append(key)


class RegistrySmokeTests(unittest.TestCase):
    def test_normal_and_injected_check_only_exact_child_keys(self):
        keys = smoke.owned_names(FAULT); registry = FakeRegistry(keys); calls = []
        def run(argv, env, capture_output, timeout):
            calls.append((argv, dict(env)))
            return subprocess.CompletedProcess(argv, 0 if len(calls) == 1 else 1, b'raw', NORMAL if len(calls) == 1 else FAULT)
        with tempfile.TemporaryDirectory() as directory:
            result = smoke.execute(Path('owned.exe'), Path(directory), {'PJ_FIXTURE_FAIL_CLEANUP': 'old'}, registry, run)
            self.assertTrue(result['complete']); self.assertEqual(registry.removed, keys)
            self.assertEqual(set(registry.queried), set(keys + smoke.owned_names(NORMAL)))
            self.assertNotIn('PJ_FIXTURE_FAIL_CLEANUP', calls[0][1])
            self.assertEqual(calls[1][1]['PJ_FIXTURE_FAIL_CLEANUP'], '1')
            self.assertEqual((Path(directory) / 'injected.stderr.bin').read_bytes(), FAULT)

    def test_unknown_or_duplicate_identity_and_wrong_exit_never_delete(self):
        for bad in (FAULT.replace(b'PlotJugglerTest-', b'Other-'), FAULT + FAULT):
            with self.assertRaises(smoke.SmokeError): smoke.owned_names(bad)
        registry = FakeRegistry(smoke.owned_names(FAULT)); count = 0
        def run(argv, **kw):
            nonlocal count
            count += 1
            return subprocess.CompletedProcess(argv, 0, b'', NORMAL if count == 1 else FAULT)
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(smoke.SmokeError):
            smoke.execute(Path('owned.exe'), Path(directory), {}, registry, run)
        self.assertEqual(registry.removed, [])

    def test_missing_one_owned_key_refuses_all_cleanup(self):
        registry = FakeRegistry(smoke.owned_names(FAULT)[:1]); count = 0
        def run(argv, **kw):
            nonlocal count
            count += 1
            return subprocess.CompletedProcess(argv, 0 if count == 1 else 1, b'', NORMAL if count == 1 else FAULT)
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(smoke.SmokeError):
            smoke.execute(Path('owned.exe'), Path(directory), {}, registry, run)
        self.assertEqual(registry.removed, [])

    def test_nonwindows_controller_does_not_launch(self):
        proc = subprocess.run([__import__('sys').executable, str(ROOT / 'scripts/windows/native_registry_smoke/run_smoke.py'),
                               '--exe', '/none', '--source-dir', '/none', '--test-mains-dir', '/none',
                               '--qt-core', '/none', '--output', '/none'], capture_output=True)
        if __import__('sys').platform != 'win32':
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn(b'requires a disposable GitHub-hosted Windows runner', proc.stderr)


if __name__ == '__main__': unittest.main()
