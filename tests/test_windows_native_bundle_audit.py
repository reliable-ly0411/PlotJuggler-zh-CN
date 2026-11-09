# SPDX-License-Identifier: MPL-2.0
"""Synthetic-only checks: these do not run native binaries or CTest."""
import importlib.util
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/windows/native_bundle_audit.py"
spec = importlib.util.spec_from_file_location("native_bundle_audit", SCRIPT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

ROOT = r"C:\Testing\PlotJuggler\n\123456789abc"
SHA = "123456789abc" + "0" * 28


def provenance():
    return {"source_sha": SHA, "source_tree": "a" * 40, "workflow_sha": "d" * 40, "source_clean": True,
            "configuration": "RelWithDebInfo", "qt": "6.12.0", "sdk": "0.39.0", "windows_sdk": "10.0",
            "compiler": "MSVC 19.4", "generator": "Ninja Multi-Config", "runner_image": "windows-test",
            "conan_lock_sha256": "e" * 64, "conan_graph_sha256": "f" * 64,
            "submodules": {"thirdparty": "b" * 40},
            "tools": [{"name": name, "version": "1", "origin": "https://example.invalid/official",
                       "sha256": "c" * 64} for name in
                      ("cmake", "ctest", "python", "embedded-cpython", "lrelease", "lupdate", "rcc", "ifw", "7z")]}


class AuditTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.root = self.base / "payload"
        (self.root / "b/RelWithDebInfo").mkdir(parents=True)
        (self.root / "s/cm").mkdir(parents=True)
        (self.root / "b/RelWithDebInfo/a.exe").write_bytes(b"exe")
        (self.root / "s/cm/test.py").write_bytes(b"fixture")
        self.meta = self.base / "provenance.json"
        self.meta.write_text(json.dumps(provenance()), encoding="utf-8")
        self.manifest = self.base / "manifest.json"
        self.disc = self.base / "ctest.json"
        self.doc = {"kind": "ctestInfo", "tests": [{"name": "case.one", "config": "RelWithDebInfo",
                    "command": [ROOT + r"\b\RelWithDebInfo\a.exe", "--fixture=" + ROOT + r"\s\cm\test.py"],
                    "properties": [{"name": "WORKING_DIRECTORY", "value": ROOT + r"\b"},
                                   {"name": "TIMEOUT", "value": 120.0}]}]}
        self.write_discovery()

    def tearDown(self):
        self.tmp.cleanup()

    def write_discovery(self):
        self.disc.write_text(json.dumps(self.doc), encoding="utf-8")

    def capture(self):
        return audit.create_manifest(self.root, audit.windows_root(ROOT), self.meta, self.manifest)

    def test_capture_roundtrip_detects_tampering_and_extra_files(self):
        result = self.capture()
        self.assertEqual(result["files"], 2)
        self.assertEqual(audit.verify_manifest(self.root, self.manifest, True, result["manifest_sha256"], ROOT, SHA, "a" * 40, "RelWithDebInfo")["files"], 2)
        (self.root / "s/cm/test.py").write_bytes(b"changed")
        with self.assertRaises(audit.AuditError):
            audit.verify_manifest(self.root, self.manifest, False, result["manifest_sha256"], ROOT, SHA, "a" * 40, "RelWithDebInfo")
        (self.root / "s/cm/test.py").write_bytes(b"fixture")
        (self.root / "unexpected_empty_directory").mkdir()
        with self.assertRaises(audit.AuditError):
            audit.verify_manifest(self.root, self.manifest, False, result["manifest_sha256"], ROOT, SHA, "a" * 40, "RelWithDebInfo")
        (self.root / "unexpected_empty_directory").rmdir()
        (self.root / "unexpected").write_bytes(b"x")
        with self.assertRaises(audit.AuditError):
            audit.verify_manifest(self.root, self.manifest, False, result["manifest_sha256"], ROOT, SHA, "a" * 40, "RelWithDebInfo")

    @unittest.skipIf(os.name == 'nt', 'POSIX mode-denial probe; Windows needs a separate owned ACL fixture')
    def test_unreadable_directory_fails_capture_and_verify(self):
        locked = self.root / 'b/locked'; locked.mkdir()
        result = self.capture()
        (locked / 'hidden-extra.txt').write_bytes(b'unlisted')
        locked.chmod(0)
        try:
            if os.access(locked, os.R_OK | os.X_OK):
                self.skipTest('effective identity can bypass the mode denial')
            with self.assertRaises(audit.AuditError):
                audit.create_manifest(self.root, ROOT, self.meta, self.base / 'unreadable-manifest.json')
            with self.assertRaises(audit.AuditError):
                audit.verify_manifest(self.root, self.manifest, False, result['manifest_sha256'], ROOT, SHA, 'a' * 40, 'RelWithDebInfo')
        finally:
            locked.chmod(0o700)

    def test_stage_accepts_only_named_hashed_files_with_notices(self):
        source = self.base / "origin"; source.mkdir()
        (source / "LICENSE").write_bytes(b"license")
        (source / "test.exe").write_bytes(b"test binary")
        (source / "secret-not-listed").write_bytes(b"do not copy")
        sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
        plan = {"origins": {"repo": {"root": str(source), "description": "Project source", "revision": "a" * 40,
                                         "license_files": ["s/LICENSE"]}},
                "directories": ["b/empty_working_directory"],
                "files": [{"origin": "repo", "source": "LICENSE", "destination": "s/LICENSE", "sha256": sha(source / "LICENSE")},
                          {"origin": "repo", "source": "test.exe", "destination": "b/test.exe", "sha256": sha(source / "test.exe")}]}
        plan_path = self.base / "plan.json"; plan_path.write_text(json.dumps(plan), encoding="utf8")
        staging = self.base / "stage"
        result = audit.stage_allowlisted(plan_path, staging, ROOT)
        self.assertEqual(result["files_copied"], 2)
        self.assertFalse((staging / "secret-not-listed").exists())
        self.assertTrue((staging / "b/empty_working_directory").is_dir())
        origins = json.loads((staging / "_bundle/origins.json").read_text(encoding="utf8"))
        self.assertNotIn(str(source), json.dumps(origins))
        self.assertEqual((staging / "b/test.exe").read_bytes(), b"test binary")
        with self.assertRaises(audit.AuditError): audit.stage_allowlisted(plan_path, staging, ROOT)

    def test_stage_fails_before_copy_on_hash_or_license_error(self):
        source = self.base / "origin"; source.mkdir(); (source / "a").write_bytes(b"a")
        plan = {"origins": {"repo": {"root": str(source), "description": "Project", "revision": "a" * 40,
                                         "license_files": ["s/LICENSE"]}},
                "files": [{"origin": "repo", "source": "a", "destination": "s/a", "sha256": "0" * 64}]}
        plan_path = self.base / "plan.json"; plan_path.write_text(json.dumps(plan), encoding="utf8")
        staging = self.base / "stage"
        with self.assertRaises(audit.AuditError): audit.stage_allowlisted(plan_path, staging, ROOT)
        self.assertEqual(list(staging.iterdir()), [])
        plan["files"][0]["sha256"] = hashlib.sha256(b"a").hexdigest()
        plan_path.write_text(json.dumps(plan), encoding="utf8")
        with self.assertRaises(audit.AuditError): audit.stage_allowlisted(plan_path, staging, ROOT)
        self.assertEqual(list(staging.iterdir()), [])

    def test_internal_manifest_needs_independent_digest(self):
        output = self.root / "_bundle/manifest.json"
        result = audit.create_manifest(self.root, ROOT, self.meta, output)
        self.assertEqual(audit.verify_manifest(self.root, output, False, result["manifest_sha256"], ROOT, SHA, "a" * 40, "RelWithDebInfo")["files"], 2)
        with self.assertRaises(audit.AuditError):
            audit.verify_manifest(self.root, output, False, "0" * 64, ROOT, SHA, "a" * 40, "RelWithDebInfo")
        with self.assertRaises(audit.AuditError):
            audit.verify_manifest(self.root, output, False, result["manifest_sha256"], ROOT.replace("Testing", "Other"), SHA, "a" * 40, "RelWithDebInfo")
        with self.assertRaises(audit.AuditError):
            audit.verify_manifest(self.root, output, False, result["manifest_sha256"], ROOT, "f" * 40, "a" * 40, "RelWithDebInfo")
        with self.assertRaises(audit.AuditError):
            audit.create_manifest(self.root, ROOT, self.meta, output)

    def test_existing_owned_run_evidence_can_be_ignored_without_reading_or_deleting_it(self):
        (self.root / "r").mkdir()
        result = self.capture()
        old = self.root / "r/previous"; old.mkdir(); (old / "evidence.bin").write_bytes(b"keep")
        with self.assertRaises(audit.AuditError):
            audit.verify_manifest(self.root, self.manifest, False, result["manifest_sha256"], ROOT, SHA, "a" * 40, "RelWithDebInfo")
        audit.verify_manifest(self.root, self.manifest, False, result["manifest_sha256"], ROOT, SHA, "a" * 40,
                              "RelWithDebInfo", allow_owned_runs=True)
        self.assertEqual((old / "evidence.bin").read_bytes(), b"keep")
        (self.root / "b/unexpected").write_bytes(b"x")
        with self.assertRaises(audit.AuditError):
            audit.verify_manifest(self.root, self.manifest, False, result["manifest_sha256"], ROOT, SHA, "a" * 40,
                                  "RelWithDebInfo", allow_owned_runs=True)

    def test_rejects_unpinned_or_dirty_provenance_and_wrong_root(self):
        p = provenance(); p["source_clean"] = False
        self.meta.write_text(json.dumps(p), encoding="utf8")
        with self.assertRaises(audit.AuditError): self.capture()
        p = provenance(); p["tools"].pop()
        self.meta.write_text(json.dumps(p), encoding="utf8")
        with self.assertRaises(audit.AuditError): self.capture()
        p = provenance(); p["tools"][0]["origin"] = "https://user:secret@example.invalid/archive"
        self.meta.write_text(json.dumps(p), encoding="utf8")
        with self.assertRaises(audit.AuditError): self.capture()
        p = provenance(); p["compiler"] = "MSVC\nSECRET=value"
        self.meta.write_text(json.dumps(p), encoding="utf8")
        with self.assertRaises(audit.AuditError): self.capture()
        self.meta.write_text(json.dumps(provenance()), encoding="utf8")
        with self.assertRaises(audit.AuditError):
            audit.create_manifest(self.root, audit.windows_root(ROOT[:-12] + "a" * 12), self.meta, self.manifest)
        for path in (r"C:\Testing\..\n\123456789abc", ROOT + r"\other", r"\\server\share\n\123456789abc"):
            with self.assertRaises(audit.AuditError): audit.windows_root(path)

    def test_rejects_nonredistributable_cache_git_and_windows_collisions(self):
        for rel in ("b/vcruntime140d.dll", "b/vcruntime140_1d.dll", "b/msvcp140_2d.dll", "b/mfc140ud.dll", "b/ucrtbased.dll", "b/x.obj", "b/x.pdb", "b/x.lib", "b/CMakeCache.txt", "b/credentials.json", "s/.git/config", "b/CON.txt", "b/COM¹.txt", "b/CONOUT$", "b/with space ", "b/NUL .txt", "b/CON .txt", "b/COM1 .foo", "t/pwsh.exe", "b/powershell.exe"):
            with self.subTest(rel=rel):
                with self.assertRaises(audit.AuditError): audit.check_windows_relative(rel, ROOT)
        with self.assertRaises(audit.AuditError): audit.windows_root(r"C:\NUL .txt\n\123456789abc")
        (self.root / "b/a.dll").write_bytes(b"1")
        (self.root / "b/A.dll").write_bytes(b"2")
        with self.assertRaises(audit.AuditError): self.capture()

    def test_rejects_long_path(self):
        with self.assertRaises(audit.AuditError): audit.check_windows_relative("s/" + "x" * 220, ROOT)
        # Windows counts UTF-16 units: each supplementary character costs two.
        with self.assertRaises(audit.AuditError): audit.check_windows_relative("s/" + "😀" * 110, ROOT)

    def test_windows_stream_api_fail_closed_on_named_streams_and_errors(self):
        def fake_kernel(names, ending=38, first_error=None):
            kernel = mock.Mock()
            state = {'index': 0, 'error': first_error}
            def set_name(pointer, value):
                audit.ctypes.cast(pointer, audit.ctypes.POINTER(audit.StreamData)).contents.name = value
            def first(path, level, pointer, flags):
                if first_error is not None:
                    return audit.ctypes.c_void_p(-1).value
                set_name(pointer, names[0]); return 42
            def following(handle, pointer):
                state['index'] += 1
                if state['index'] < len(names):
                    set_name(pointer, names[state['index']]); return True
                state['error'] = ending; return False
            kernel.FindFirstStreamW.side_effect = first
            kernel.FindNextStreamW.side_effect = following
            kernel.FindClose.return_value = True
            return kernel, lambda: state['error']
        for names in (['::$DATA'], ['::$DATA', ':secret:$DATA']):
            kernel, error = fake_kernel(names)
            self.assertEqual(audit.windows_stream_names(self.root, kernel, error), names)
            kernel.FindClose.assert_called_once()
        kernel, error = fake_kernel([], first_error=38)
        self.assertEqual(audit.windows_stream_names(self.root, kernel, error), [])
        kernel.FindClose.assert_not_called()
        for args in ({'first_error': 50}, {'names': ['::$DATA'], 'ending': 5}):
            names = args.pop('names', [])
            kernel, error = fake_kernel(names, **args)
            with self.assertRaises(audit.AuditError): audit.windows_stream_names(self.root, kernel, error)
        path = self.root / 'b/RelWithDebInfo/a.exe'
        with mock.patch.object(audit.os, 'name', 'nt'), mock.patch.object(audit, 'windows_stream_names', return_value=['::$DATA', ':secret:$DATA']):
            with self.assertRaises(audit.AuditError): audit.check_no_named_streams(path, False)
        with mock.patch.object(audit.os, 'name', 'nt'), mock.patch.object(audit, 'windows_stream_names', return_value=[]):
            audit.check_no_named_streams(self.root, True)
            with self.assertRaises(audit.AuditError): audit.check_no_named_streams(path, False)

    @unittest.skipUnless(os.name == 'nt', 'real NTFS named streams require Windows')
    def test_real_ntfs_named_stream_is_rejected(self):
        target = self.root / 'b/RelWithDebInfo/a.exe'
        audit.check_no_named_streams(target, False)
        with open(str(target) + ':native-kit-test', 'wb') as stream:
            stream.write(b'test-only')
        with self.assertRaises(audit.AuditError): audit.check_no_named_streams(target, False)

    def test_rejects_symlink_and_linked_root(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symbolic links are unavailable")
        try:
            (self.root / "b/link").symlink_to(self.root / "s", target_is_directory=True)
        except OSError as error:
            if os.name == "nt" and getattr(error, "winerror", None) == 1314:
                self.skipTest("Windows symlink privilege is unavailable")
            raise
        with self.assertRaises(audit.AuditError): self.capture()
        (self.root / "b/link").unlink()
        alias = self.base / "linkroot"; alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(audit.AuditError): audit.inventory(alias, ROOT)

    def test_rejects_hardlinked_staged_files(self):
        if not hasattr(os, "link"):
            self.skipTest("hard links are unavailable")
        os.link(self.root / "s/cm/test.py", self.root / "s/cm/hardlink")
        with self.assertRaises(audit.AuditError): self.capture()

    def test_audits_command_paths_cwd_and_properties(self):
        result = audit.audit_discovery(self.root, ROOT, self.disc, None, "RelWithDebInfo")
        self.assertEqual(result["test_count"], 1)
        self.assertEqual(result["path_reference_count"], 3)
        with self.assertRaises(audit.AuditError):
            audit.audit_discovery(self.root, ROOT, self.disc, None, "Debug")
        self.doc["tests"][0]["properties"].append({"name": "ENVIRONMENT", "value": ["QT_QPA_FONTDIR=D:/external/fonts"]})
        self.write_discovery()
        with self.assertRaises(audit.AuditError): audit.audit_discovery(self.root, ROOT, self.disc, None, "RelWithDebInfo")
        self.doc["tests"][0]["properties"].pop(); self.doc["tests"][0]["command"][0] = "a.exe"; self.write_discovery()
        with self.assertRaises(audit.AuditError): audit.audit_discovery(self.root, ROOT, self.disc, None, "RelWithDebInfo")

    def test_unc_and_posix_paths_fail_even_when_embedded_in_arguments(self):
        for value in (r"--fixture=\\server\share\fixture", "--fixture=/tmp/out/file", "--input=/tmp",
                      r"--input=\Windows\System32\secret.txt", r"-IC:\outside\file", r"--input=C:..\outside"):
            with self.subTest(value=value):
                self.doc["tests"][0]["command"] = [ROOT + r"\b\RelWithDebInfo\a.exe", value]
                self.write_discovery()
                with self.assertRaises(audit.AuditError): audit.audit_discovery(self.root, ROOT, self.disc, None, "RelWithDebInfo")
        self.doc["tests"][0]["command"] = [ROOT + r"\b\RelWithDebInfo\a.exe", "https://example.invalid/a/b"]
        self.write_discovery()
        self.assertEqual(audit.audit_discovery(self.root, ROOT, self.disc, None, "RelWithDebInfo")["test_count"], 1)

    def test_ctest_backtrace_source_paths_are_checked(self):
        self.doc["backtraceGraph"] = {"files": [ROOT + r"\s\cm\test.py"]}
        self.write_discovery()
        self.assertEqual(audit.audit_discovery(self.root, ROOT, self.disc, None, "RelWithDebInfo")["path_reference_count"], 4)
        self.doc["backtraceGraph"]["files"] = [r"D:\outside\CMakeLists.txt"]
        self.write_discovery()
        with self.assertRaises(audit.AuditError): audit.audit_discovery(self.root, ROOT, self.disc, None, "RelWithDebInfo")

    def test_missing_output_must_be_exact_and_for_the_same_case(self):
        missing = ROOT + r"\b\result.txt"
        self.doc["tests"][0]["command"].append("--out=" + missing); self.write_discovery()
        with self.assertRaises(audit.AuditError): audit.audit_discovery(self.root, ROOT, self.disc, None, "RelWithDebInfo")
        allow = self.base / "allow.json"; allow.write_text(json.dumps({"case.one": [missing]}), encoding="utf8")
        self.assertEqual(audit.audit_discovery(self.root, ROOT, self.disc, allow, "RelWithDebInfo")["test_count"], 1)
        allow.write_text(json.dumps({"wrong": [missing]}), encoding="utf8")
        with self.assertRaises(audit.AuditError): audit.audit_discovery(self.root, ROOT, self.disc, allow, "RelWithDebInfo")
        allow.write_text(json.dumps({"case.one": [missing, ROOT + r"\b\unused.txt"]}), encoding="utf8")
        with self.assertRaises(audit.AuditError): audit.audit_discovery(self.root, ROOT, self.disc, allow, "RelWithDebInfo")

    def test_junit_requires_exact_set_and_records_top_and_nested_skips(self):
        self.doc["tests"].append({"name": "case.two"}); self.write_discovery()
        junit = self.base / "result.xml"
        junit.write_text('''<testsuite><testcase name="case.one" status="run"><system-out>[  SKIPPED ] Suite.Child (1 ms)
[  SKIPPED ] 1 test, listed below:
[  SKIPPED ] Suite.Child
SKIP   : Widget::fixture() intentional
Totals: 1 passed, 0 failed, 1 skipped, 0 blacklisted</system-out></testcase>
<testcase name="case.two" status="notrun"><skipped message="not available"/></testcase></testsuite>''', encoding="utf8")
        result = audit.audit_results(self.disc, junit)
        self.assertEqual(result["top_level_skips"], ["case.two"])
        self.assertEqual(len(result["nested_skips"]), 2)
        self.assertFalse(result["complete_without_skips_or_failures"])
        self.doc["tests"].append({"name": "missing"}); self.write_discovery()
        with self.assertRaises(audit.AuditError): audit.audit_results(self.disc, junit)

    def test_unidentified_gtest_or_qt_skip_summary_is_not_a_pass(self):
        junit = self.base / "result.xml"
        junit.write_text('<testsuite><testcase name="case.one" status="run"><system-out>'
                         '[  SKIPPED ] 3 tests, listed below:\n'
                         'Totals: 1 passed, 0 failed, 2 skipped, 0 blacklisted'
                         '</system-out></testcase></testsuite>', encoding="utf8")
        result = audit.audit_results(self.disc, junit)
        self.assertEqual({x["case"] for x in result["nested_skips"]},
                         {"gtest:unidentified_skip_count=3", "qt:unidentified_skip_count=2"})
        self.assertFalse(result["complete_without_skips_or_failures"])

    def test_ctest_truncation_markers_fail_without_conflating_input_mismatches(self):
        junit = self.base / "result.xml"
        for marker in ("test output was removed", "The output exceeds the threshold"):
            with self.subTest(marker=marker):
                junit.write_text('<testsuite><testcase name="case.one" status="run"><system-out>' + marker +
                                 '</system-out></testcase></testsuite>', encoding="utf8")
                result = audit.audit_results(self.disc, junit)
                self.assertEqual(result["truncated_outputs"], ["case.one"])
                self.assertFalse(result["complete_without_skips_or_failures"])

    def test_ctest_status_reason_and_unknown_status_are_not_conflated(self):
        junit = self.base / "result.xml"
        for status, element, category in (
                ("run", "", "pass"), ("fail", "", "failure"),
                ("notrun", '<skipped message="Unable to find executable"/>', "not_run"),
                ("notrun", '<skipped message="SKIP_RETURN_CODE=4"/>', "conditional_skip"),
                ("disabled", "", "disabled")):
            with self.subTest(status=status, category=category):
                junit.write_text(f'<testsuite><testcase name="case.one" status="{status}">{element}</testcase></testsuite>', encoding="utf8")
                result = audit.audit_results(self.disc, junit)
                self.assertEqual(result['case_results'][0]['category'], category)
                self.assertEqual(result['complete_without_skips_or_failures'], category == 'pass')
        for status in ('', 'unknown'):
            attribute = '' if not status else f' status="{status}"'
            junit.write_text(f'<testsuite><testcase name="case.one"{attribute}/></testsuite>', encoding="utf8")
            with self.assertRaises(audit.AuditError):
                audit.audit_results(self.disc, junit)
        for status, children in (('run', '<skipped/>'), ('run', '<failure/>'), ('fail', '<skipped/>'),
                                 ('notrun', '<failure/>'), ('disabled', '<skipped/>'),
                                 ('notrun', '<skipped/><skipped/>')):
            junit.write_text(f'<testsuite><testcase name="case.one" status="{status}">{children}</testcase></testsuite>', encoding="utf8")
            with self.assertRaises(audit.AuditError): audit.audit_results(self.disc, junit)

    def test_space_counts_host_copies_guest_archive_and_reserves(self):
        result = audit.space_estimate(100, 200, 250, 500, 50, 50, 100, 2)
        self.assertEqual(result["host_needed_bytes"], 250)
        self.assertEqual(result["guest_needed_bytes"], 450)
        self.assertTrue(result["host_sufficient"] and result["guest_sufficient"])
        self.assertFalse(audit.space_estimate(100, 200, 249, 449, 50, 50, 100, 2)["host_sufficient"])
        with self.assertRaises(audit.AuditError): audit.space_estimate(0, 200, 1, 1, 0, 0, 0, 1)



class QtTestOutputTests(unittest.TestCase):
    def test_discovery_allows_exact_qttest_output_and_not_other_destinations(self):
        logical = r'C:\Testing\n\123456789abc'
        target = logical + r'\b\Testing\Temporary\bundled-translations.txt'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / 'b').mkdir()
            (root / 'b/pj_bundled_translations_test.exe').write_bytes(b'fixture')
            test = {'name': 'pj_bundled_translations_test', 'config': 'RelWithDebInfo',
                    'command': [logical + r'\b\pj_bundled_translations_test.exe', '-o', '-,txt', '-o', target + ',txt'],
                    'properties': [{'name': 'WORKING_DIRECTORY', 'value': logical + r'\b'}]}
            document = root / 'discovery.json'; contract = root / 'outputs.json'
            document.write_text(json.dumps({'kind': 'ctestInfo', 'tests': [test]}), encoding='utf-8')
            contract.write_text(json.dumps({'pj_bundled_translations_test': [target]}), encoding='utf-8')
            result = audit.audit_discovery(root, logical, document, contract, 'RelWithDebInfo')
            self.assertTrue(any(x['path'] == target and not x['exists'] for x in result['references']))
            with self.assertRaises(audit.AuditError):
                audit.audit_discovery(root, logical, document, None, 'RelWithDebInfo')
            test['command'][4] = logical + r'\b\plugins\bad.dll,txt'
            document.write_text(json.dumps({'kind': 'ctestInfo', 'tests': [test]}), encoding='utf-8')
            with self.assertRaises(audit.AuditError):
                audit.audit_discovery(root, logical, document, contract, 'RelWithDebInfo')

    def test_only_exact_bundled_case_parses_txt_suffix(self):
        logical = r'C:\Testing\n\123456789abc'
        target = logical + r'\b\Testing\Temporary\bundled-translations.txt'
        test = {'name': 'pj_bundled_translations_test', 'command': [logical + r'\b\pj_bundled_translations_test.exe',
                '-o', '-,txt', '-o', target + ',txt'], 'properties': []}
        self.assertEqual(audit.bundled_qttest_output(test, logical), target)
        for value in (target + ',xml', logical + r'\b\plugins\payload.dll,txt', target + ',txt,txt'):
            case = dict(test, command=test['command'][:4] + [value])
            with self.subTest(value=value), self.assertRaises(audit.AuditError): audit.bundled_qttest_output(case, logical)
        self.assertIsNone(audit.bundled_qttest_output({'name': 'other', 'command': test['command']}, logical))

if __name__ == "__main__":
    unittest.main()
