# SPDX-License-Identifier: MPL-2.0
"""Offline review-only boundary tests; no real DLLs, build tree or network."""
from pathlib import Path
import json
import copy
import os
import struct
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from package_privacy import check_metadata as check
from pe_content_fingerprint import fingerprint, METHOD
from windows_public_binary_review_helpers import (
    candidate_privacy, derive_qrc_offsets, observed_public_literals, unknown_public_path_hashes, path_diagnostics, rc5_shadow, qrc_struct, sha, load_quarantine_catalog, validate_quarantine_catalog,
)

PUBLIC_SOURCE = r"C:\Users\runneradmin\.conan2\p\b\arrow5bfe34ade08ff\b\src\cpp\src\arrow\array\array_base.cc"
FIXTURE_RECORDS = {"public_ci_source_records": {
    name: {"observed_plugin_sha256": "0" * 64, "nul_terminated_literals": [PUBLIC_SOURCE]}
    for name in ("DataLoadParquet.dll", "ToolboxMosaico.dll")}}


def generated_qrc(file_count):
    """Small synthetic Qt5 v2 node table: two directories and known files."""
    blob = bytearray((file_count + 2) * 22)
    for offset in (0, 22):
        struct.pack_into(">H", blob, offset + 4, 2)
        struct.pack_into(">I", blob, offset + 6, file_count if offset else 1)
        struct.pack_into(">I", blob, offset + 10, 2 if offset else 1)
    for index in range(file_count):
        offset = (index + 2) * 22
        struct.pack_into(">I", blob, offset, index * 16)
        struct.pack_into(">Q", blob, offset + 14, 1792127804307 + index)
    source = ("// Synthetic generated fixture; never product resources.\r\n"
              "static const unsigned char qt_resource_struct[] = {\r\n" +
              ",".join("0x%02x" % value for value in blob) +
              "\r\n};\r\nint version = 2;\r\n")
    return source.encode("utf-8")


SOURCES = [("plugins/ToolboxMosaico/qrc_mosaico_resources.cpp", generated_qrc(1)),
           ("thirdparty/QCodeEditor/qrc_qcodeeditor_resources.cpp", generated_qrc(5))]


class ReviewScope(unittest.TestCase):
    old = PUBLIC_SOURCE
    new = old.replace("5bfe34ade08ff", "0123456789abc")

    def policy(self):
        return {"public_ci_source_records": {"DataLoadParquet.dll": {
            "observed_plugin_sha256": "0" * 64, "nul_terminated_literals": [self.old]}}}

    def test_cache_hex_only_ascii_and_unaligned_utf16(self):
        for encoding, prefix in (("ascii", b""), ("utf-16le", b""), ("utf-16le", b"x")):
            data = prefix + (self.new + "\0").encode(encoding)
            literals, markers, policy = candidate_privacy(data, "DataLoadParquet.dll", self.policy(), check)
            self.assertEqual(literals, [self.new])
            self.assertTrue(markers)
            self.assertEqual(self.policy()["public_ci_source_records"]["DataLoadParquet.dll"]["observed_plugin_sha256"], "0" * 64)

    def test_path_or_identity_scope_cannot_expand(self):
        for modified in (self.new.replace("runneradmin", "AnotherUser"),
                         self.new.replace("array_base.cc", "private.bin"),
                         self.new + "/suffix", self.new[:-1],
                         self.new.replace("0123456789abc", "0123456789abcd"),
                         self.new.replace("0123456789abc", "0123456789abg")):
            with self.subTest(case=sha(modified.encode())):
                with self.assertRaises(ValueError):
                    candidate_privacy((modified + "\0").encode(), "DataLoadParquet.dll", self.policy(), check)
        with self.assertRaises(ValueError):
            candidate_privacy((self.new + "\0").encode(), "NotInScope.dll", self.policy(), check)

    def test_missing_nul_does_not_qualify(self):
        self.assertEqual(observed_public_literals(self.new.encode(), [self.old]), [])

    def test_approved_public_prefix_cannot_hide_secret_or_other_path(self):
        for encoding in ("ascii", "utf-16le"):
            for extra in (r"C:\Users\AnotherUser\private.bin",
                          "gh" + "p_" + "x" * 36,
                          "-----BEGIN PRIVATE KEY-----\n" + "A" * 128 + "\n-----END PRIVATE KEY-----",
                          "synthetic" + "@" + "qq.com"):
                with self.subTest(encoding=encoding, case=sha(extra.encode())):
                    with self.assertRaises(ValueError):
                        candidate_privacy((self.new + "\0" + extra + "\0").encode(encoding),
                                          "DataLoadParquet.dll", self.policy(), check)

    def test_ascii_equivalence_and_strict_rejections(self):
        equivalent = self.new.upper().replace("\\", "/")
        self.assertEqual(observed_public_literals((equivalent + "\0").encode(), [self.old]), [equivalent])
        for value in (self.new.replace("runneradmin", "runneradmın"),
                      self.new.replace("array_base.cc", "../array_base.cc"),
                      self.new + ".extra", self.new.replace("0123456789abc", "123")):
            self.assertEqual(observed_public_literals((value + "\0").encode("utf-16le"), [self.old]), [])

    def test_unknown_public_path_hash_requires_bounded_reviewed_root_and_package(self):
        value = self.new.replace("array_base.cc", "new_source.cc")
        expected = unknown_public_path_hashes((value + "\0").encode(), [self.old], [])
        self.assertEqual(len(expected), 1)
        for encoding, prefix in (("ascii", b""), ("utf-16le", b""), ("utf-16le", b"x")):
            self.assertEqual(unknown_public_path_hashes(prefix + (value + "\0").encode(encoding), [self.old], []), expected)
        for bad in (value.replace("runneradmin", "SomeOtherUser"),
                    value.replace("arrow0123456789abc", "other0123456789abc"),
                    value.replace("0123456789abc", "0123456789ab"),
                    value.replace("new_source.cc", "..\\new_source.cc"),
                    value.replace("new_source.cc", "new_sourcе.cc")):
            self.assertEqual(unknown_public_path_hashes((bad + "\0").encode("utf-16le"), [self.old], []), [])
        self.assertEqual(unknown_public_path_hashes(value.encode(), [self.old], []), [])
        self.assertEqual(unknown_public_path_hashes(("X" + value + "\0").encode(), [self.old], []), [])
        self.assertEqual(unknown_public_path_hashes((value + "\0").encode(), [self.old], [value]), [])

    def test_diagnostic_hash_accepts_end_only_without_export_approval(self):
        data = ("X" + self.new + "\0").encode()
        diag = path_diagnostics(data, [self.old])
        self.assertEqual(diag["boundary_counts"]["no_nul_start"], 1)
        self.assertEqual(diag["reason_counts"]["known_exact_literal"], 1)
        expected = self.old.lower().replace("\\", "/").replace("5bfe34ade08ff", "{cache}")
        self.assertEqual(diag["path_sha256"], [sha(expected.encode("ascii"))])
        shadow = rc5_shadow(data, "DataLoadParquet.dll", self.policy(), [self.old], check)
        self.assertEqual(shadow["matched_occurrences"], 1)
        self.assertTrue(shadow["passed"])
        literals, _, policy = candidate_privacy(data, "DataLoadParquet.dll", self.policy(), check)
        self.assertEqual(literals, [self.new])
        self.assertEqual(policy["public_ci_source_records"]["DataLoadParquet.dll"]["observed_plugin_sha256"], sha(data))
        with self.assertRaises(ValueError):
            check(data, "DataLoadParquet.dll", self.policy())

    def test_diagnostic_allowlist_layout_and_secret_boundaries(self):
        candidate = self.new.replace("array_base.cc", "new_file.cc")
        for layout in (candidate, candidate.replace("\\p\\b\\", "\\p\\")):
            for encoding in ("ascii", "utf-16le"):
                self.assertEqual(len(path_diagnostics((layout + "\0").encode(encoding), [self.old])["path_sha256"]), 1)
        for bad in (candidate.replace("runneradmin", "someone"),
                    candidate.replace("arrow0123456789abc", "other0123456789abc"),
                    candidate.replace("\\p\\b\\", "\\p\\other\\"),
                    candidate.replace("0123456789abc", "0123456789abcd"),
                    candidate.replace("new_file.cc", "..\\new_file.cc"),
                    candidate.replace("new_file.cc", "new_ﬁle.cc")):
            self.assertEqual(path_diagnostics((bad + "\0").encode("utf-16le"), [self.old])["path_sha256"], [])
        for extra in ("gh" + "p_" + "x" * 36, "person" + "@qq.com",
                      "-----BEGIN PRIVATE KEY-----\n" + "A" * 128 + "\n-----END PRIVATE KEY-----"):
            diag = path_diagnostics((candidate + "\0" + extra + "\0").encode(), [self.old])
            self.assertTrue(diag["hashes_suppressed_for_secret"])
            self.assertEqual(diag["path_sha256"], [])

    def test_malformed_utf16_cannot_hide_private_marker_from_residual(self):
        literal = self.new
        data = ("person@qq.com" + literal[:4]).encode("utf-16le") + b"\x00\xd8" + (literal[4:] + "\0").encode("utf-16le")
        with self.assertRaises(ValueError):
            candidate_privacy(data, "DataLoadParquet.dll", self.policy(), check)

    def test_old_production_gate_still_rejects_unreviewed_candidate(self):
        data = (self.new + "\0").encode()
        original = self.policy()
        candidate_privacy(data, "DataLoadParquet.dll", original, check)
        with self.assertRaises(ValueError):
            check(data, "DataLoadParquet.dll", original)


class QuarantineCatalog(unittest.TestCase):
    def setUp(self):
        self.catalog = json.loads((REPO / "tests/data/windows-quarantine-protobuf-catalog.json").read_text())
        self.paths = load_quarantine_catalog()
        self.name = "ToolboxMosaico.dll"
        self.other = "ProtobufParser.dll"
        self.policy = FIXTURE_RECORDS
        self.path = self.paths[self.name][0].replace("0000000000000", "0123456789abc")

    def test_finite_exact_per_dll_catalog_and_production_rejection(self):
        self.assertEqual(len(self.catalog["entries"]), 31)
        self.assertEqual([len(self.paths[n]) for n in (self.name, self.other)], [29, 29])
        for name in (self.name, self.other):
            for path in self.paths[name]:
                data = (path.replace("0000000000000", "0123456789abc") + "\0").encode()
                literals, _, _ = candidate_privacy(data, name, self.policy, check)
                self.assertEqual(len(literals), 1)
                with self.assertRaises(ValueError):
                    check(data, name, self.policy)
        unique = set(self.paths[self.other]) - set(self.paths[self.name])
        self.assertTrue(unique)
        data = (next(iter(unique)) + "\0").encode()
        with self.assertRaises(ValueError):
            candidate_privacy(data, self.name, self.policy, check)
        unique = set(self.paths[self.name]) - set(self.paths[self.other])
        self.assertTrue(unique)
        with self.assertRaises(ValueError):
            candidate_privacy((next(iter(unique)) + "\0").encode(), self.other, self.policy, check)

    def test_exact_filename_and_cache_boundary(self):
        path = self.path
        for value in (path.replace("runneradmin", "anotheruser"),
                      path.replace("proto0123456789abc", "other0123456789abc"),
                      path.replace("/p/b/", "/p/"),
                      path.replace("0123456789abc", "0123456789ab"),
                      path.replace("0123456789abc", "0123456789abcd"),
                      path.replace("/google/", "/../google/"),
                      path + ".extra", path.rsplit("/", 1)[0] + "/unreviewed.cc"):
            with self.subTest(case=sha(value.encode())):
                with self.assertRaises(ValueError):
                    candidate_privacy((value + "\0").encode(), self.name, self.policy, check)
        with self.assertRaises(ValueError):
            candidate_privacy(path.encode(), self.name, self.policy, check)
        for encoding, prefix in (("ascii", b""), ("utf-16le", b""), ("utf-16le", b"x")):
            value = path.upper().replace("/", "\\")
            self.assertEqual(candidate_privacy(prefix + (value + "\0").encode(encoding), self.name, self.policy, check)[0], [value])

    def test_catalog_never_masks_adjacent_secret_or_private_path(self):
        for encoding, alignment in (("ascii", b""), ("utf-16le", b""), ("utf-16le", b"x")):
            for prefix in ("person@qq.com", r"C:\Users\OtherUser\private.bin", "gh"+"p_"+"x"*36,
                           "-----BEGIN PRIVATE KEY-----\n"+"A"*128+"\n-----END PRIVATE KEY-----"):
                with self.subTest(encoding=encoding, alignment=len(alignment), case=sha(prefix.encode())):
                    with self.assertRaises(ValueError):
                        candidate_privacy(alignment + (prefix + self.path + "\0").encode(encoding), self.name, self.policy, check)

    def test_catalog_schema_and_mapping_fail_closed(self):
        cases = []
        for field, value in (("canonical_path", "c:/other"), ("official_relative_path", "src/google/protobuf/../private.cc"),
                             ("git_blob_sha", "invalid"), ("diagnostic_sha256", "0"*64)):
            bad = copy.deepcopy(self.catalog)
            bad["entries"][0][field] = value
            cases.append(bad)
        bad = copy.deepcopy(self.catalog)
        bad["dll_entries"][self.name][0] = "0"*64
        cases.append(bad)
        for value in cases:
            with self.assertRaises(ValueError):
                validate_quarantine_catalog(value)


class ResourceEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = SOURCES

    def pe(self):
        data = bytearray(16384)
        data[:2] = b"MZ"
        struct.pack_into("<I", data, 60, 128)
        data[128:132] = b"PE\0\0"
        struct.pack_into("<HHI", data, 132, 0x8664, 1, 123456)
        struct.pack_into("<HH", data, 148, 240, 0x2000)
        struct.pack_into("<H", data, 152, 0x20b)
        struct.pack_into("<I", data, 260, 16)
        struct.pack_into("<II", data, 312, 4096, 28)
        data[392:400] = b".rdata\0\0"
        struct.pack_into("<IIII", data, 400, 15872, 4096, 15872, 512)
        struct.pack_into("<I", data, 524, 13)
        cursor = 2048
        for name, source in self.sources:
            blob, _, _ = qrc_struct(source.decode("utf-8"))
            data[cursor:cursor + len(blob)] = blob
            cursor += 1024
        return data

    def test_synthetic_qt5_structs_locate_six_fields(self):
        data = self.pe()
        positions, evidence = derive_qrc_offsets(data, self.sources)
        self.assertEqual(len(positions), 6)
        self.assertEqual(sorted(len(item["dll_timestamp_offsets"]) for item in evidence), [1, 5])
        record = {"method": METHOD, "file_bytes": len(data), "qt_rcc_mtime_offsets": positions}
        original = fingerprint(data, record)
        self.assertIsNotNone(original)
        changed_time = bytearray(data)
        for offset in positions:
            value = struct.unpack_from(">Q", changed_time, offset)[0]
            struct.pack_into(">Q", changed_time, offset, value + 1000)
        self.assertEqual(fingerprint(changed_time, record), original)
        changed_code = bytearray(data)
        changed_code[1024] ^= 1
        self.assertNotEqual(fingerprint(changed_code, record), original)

    def test_generated_source_hash_preserves_original_crlf_bytes(self):
        _, evidence = derive_qrc_offsets(self.pe(), self.sources)
        for item, (_, original) in zip(evidence, self.sources):
            self.assertEqual(item["generated_source_sha256"], sha(original))
            normalized = original.decode("utf-8").replace("\r\n", "\n").encode("utf-8")
            self.assertNotEqual(item["generated_source_sha256"], sha(normalized))

    def test_duplicate_struct_is_not_a_unique_provenance(self):
        data = self.pe()
        blob, _, _ = qrc_struct(self.sources[0][1].decode("utf-8"))
        data[6000:6000 + len(blob)] = blob
        with self.assertRaises(ValueError):
            derive_qrc_offsets(data, self.sources)

    def test_unknown_source_or_struct_without_linked_bytes_fails(self):
        with self.assertRaises(ValueError):
            derive_qrc_offsets(self.pe(), [("qrc_unknown.cpp", self.sources[0][1])])
        data = self.pe()
        data[2048] ^= 1
        with self.assertRaises(ValueError):
            derive_qrc_offsets(data, self.sources)

    def test_epoch_like_arbitrary_bytes_are_not_masked(self):
        data = self.pe()
        positions, _ = derive_qrc_offsets(data, self.sources)
        struct.pack_into(">Q", data, 10000, 1792127804307)
        record = {"method": METHOD, "file_bytes": len(data), "qt_rcc_mtime_offsets": positions}
        expected = fingerprint(data, record)
        struct.pack_into(">Q", data, 10000, 1792127805307)
        self.assertNotEqual(fingerprint(data, record), expected)


class CollectorIntegration(unittest.TestCase):
    """Synthetic PE fixtures exercise CLI plumbing, never actual DLL acceptance."""
    def setup_fixture(self, root):
        # Copy only the tool/scanner and synthetic policy into an isolated Git
        # repository. No dependency on the caller's current HEAD or build tree.
        scripts = root / "scripts"
        scripts.mkdir()
        for name in ("windows_public_binary_review.py", "windows_public_binary_review_helpers.py",
                     "package_privacy.py", "pe_content_fingerprint.py", "linux_public_elf.py"):
            (scripts / name).write_bytes((REPO / "scripts" / name).read_bytes())
        policy = root / "tests/data/public-build-records.json"
        policy.parent.mkdir(parents=True)
        (policy.parent / "windows-quarantine-protobuf-catalog.json").write_bytes(
            (REPO / "tests/data/windows-quarantine-protobuf-catalog.json").read_bytes())
        (policy.parent / "linux-public-elf-records.json").write_bytes(
            (REPO / "tests/data/linux-public-elf-records.json").read_bytes())
        policy.write_text(json.dumps(FIXTURE_RECORDS), encoding="utf-8")
        installer = root / "installer/config.xml"
        installer.parent.mkdir()
        installer.write_bytes(b"<Installer><Title>Before staging</Title></Installer>")
        subprocess.run(["git", "init", "--quiet"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "-c", "core.autocrlf=false", "add", "scripts", "tests", "installer"],
                       cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                        "-c", "commit.gpgsign=false", "-c", "core.hooksPath=" + str(root / "no-hooks"),
                        "commit", "--quiet", "-m", "Synthetic review fixture"],
                       cwd=root, check=True, capture_output=True)
        payload, build = root / "payload", root / "build"
        payload.mkdir()
        build.mkdir()
        ResourceEvidence.setUpClass()
        helper = ResourceEvidence()
        for relative, source in helper.sources:
            (build / Path(relative).name).write_bytes(source)
        for name, record in FIXTURE_RECORDS["public_ci_source_records"].items():
            data = helper.pe()
            data.extend(b"\0" * (131072 - len(data)))
            # Extend the one PE .rdata section, preserving the synthetic layout.
            struct.pack_into("<IIII", data, 400, len(data)-512, 4096, len(data)-512, 512)
            literals = b"\0".join(value.encode() for value in record["nul_terminated_literals"]) + b"\0"
            data[8192:8192 + len(literals)] = literals
            (payload / name).write_bytes(data)
        (payload / "ProtobufParser.dll").write_bytes((payload / "DataLoadParquet.dll").read_bytes())
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
        info = {"commit": head, "source_revision": head[:12],
                "repository": "https://github.com/reliable-ly0411/PlotJuggler-zh-CN",
                "version": "SYNTHETIC-FIXTURE-NOT-A-PRODUCT"}
        (payload / "BUILD-INFO.json").write_text(json.dumps(info), encoding="utf-8")
        command = [sys.executable, str(scripts / "windows_public_binary_review.py"),
                   "--repo", str(root), "--payload", str(payload), "--build", str(build),
                   "--out", str(root / "review"), "--commit", head, "--run", "1", "--run-attempt", "1"]
        return payload, command

    def test_review_folder_is_separate_and_never_approves_production(self):
        with tempfile.TemporaryDirectory(prefix="PJ review 空间-") as temp:
            root = Path(temp)
            _, command = self.setup_fixture(root)
            # Real staging updates installer Title/DisplayName legitimately;
            # a blanket repository-clean assertion must not prevent evidence.
            (root / "installer/config.xml").write_bytes(b"<Installer><Title>After staging</Title></Installer>")
            result = subprocess.run(command, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads((root / "review/review-manifest.json").read_text())
            self.assertFalse(report["whole_payload_privacy_diagnostic"]["approved_for_release"])
            self.assertEqual(report["whole_payload_privacy_diagnostic"]["errors"], [])
            for name in ("DataLoadParquet.dll", "ToolboxMosaico.dll", "ProtobufParser.dll"):
                self.assertFalse(report["selected"][name]["existing_production_gate"]["passed"])
                self.assertTrue((root / "review" / name).is_file())
                self.assertEqual(report["selected"][name]["file_bytes"], (root / "review" / name).stat().st_size)
                self.assertEqual(report["selected"][name]["observed_public_literals"], [PUBLIC_SOURCE])
            self.assertEqual(len(report["selected"]["ToolboxMosaico.dll"]["qrc_field_provenance"]), 2)
            info_bytes = (root / "payload/BUILD-INFO.json").read_bytes()
            self.assertEqual(report["build_info"]["sha256"], sha(info_bytes))
            self.assertNotIn("version", report["build_info"])
            self.assertEqual(sorted(path.name for path in (root / "review").iterdir()),
                             ["DataLoadParquet.dll", "ProtobufParser.dll", "ToolboxMosaico.dll", "review-manifest.json"])
            self.assertEqual((root / "tests/data/public-build-records.json").read_text(encoding="utf-8"),
                             json.dumps(FIXTURE_RECORDS))

    def test_private_path_does_not_export_any_dll_or_matched_content(self):
        with tempfile.TemporaryDirectory(prefix="pj-review-prototype-") as temp:
            root = Path(temp)
            payload, command = self.setup_fixture(root)
            path = payload / "DataLoadParquet.dll"
            with path.open("ab") as stream:
                stream.write(b"\0C:\\Users\\AnotherUser\\private.bin\0")
            result = subprocess.run(command, text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("AnotherUser", result.stderr + result.stdout)
            self.assertFalse((root / "review/DataLoadParquet.dll").exists())
            self.assertTrue((root / "review/ToolboxMosaico.dll").exists())
            self.assertNotIn("AnotherUser", (root / "review/review-manifest.json").read_text())

    def test_second_dll_privacy_failure_exports_neither_dll(self):
        with tempfile.TemporaryDirectory(prefix="pj-review-fixture-") as temp:
            root = Path(temp)
            payload, command = self.setup_fixture(root)
            with (payload / "ToolboxMosaico.dll").open("ab") as stream:
                stream.write(("\0gh" + "p_" + "x" * 36).encode())
            result = subprocess.run(command, text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((root / "review/ToolboxMosaico.dll").exists())
            self.assertTrue((root / "review/DataLoadParquet.dll").exists())

    def test_build_identity_cannot_disclose_secret_in_manifest(self):
        with tempfile.TemporaryDirectory(prefix="pj-review-fixture-") as temp:
            root = Path(temp)
            payload, command = self.setup_fixture(root)
            path = payload / "BUILD-INFO.json"
            info = json.loads(path.read_text(encoding="utf-8"))
            secret = "gh" + "p_" + "x" * 36
            info["unexpected"] = secret
            path.write_text(json.dumps(info), encoding="utf-8")
            result = subprocess.run(command, text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn(secret, result.stdout + result.stderr)
            self.assertFalse((root / "review").exists())

    def test_diagnostic_never_includes_matched_secret_bytes(self):
        with tempfile.TemporaryDirectory(prefix="pj-review-fixture-") as temp:
            root = Path(temp)
            payload, command = self.setup_fixture(root)
            secret = "gh" + "p_" + "x" * 36
            (payload / "notes.txt").write_text(secret, encoding="utf-8")
            result = subprocess.run(command, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            text = (root / "review/review-manifest.json").read_text(encoding="utf-8")
            report = json.loads(text)
            self.assertNotIn(secret, text + result.stdout + result.stderr)
            errors = report["whole_payload_privacy_diagnostic"]["errors"]
            self.assertEqual(len(errors), 1)
            self.assertEqual(errors[0]["path"], "notes.txt")
            self.assertEqual(errors[0]["rule"], "Unexpected GitHub credential material")
            self.assertFalse(report["whole_payload_privacy_diagnostic"]["approved_for_release"])

    def test_unsafe_diagnostic_filename_is_redacted(self):
        with tempfile.TemporaryDirectory(prefix="pj-review-fixture-") as temp:
            root = Path(temp)
            payload, command = self.setup_fixture(root)
            secret = "gh" + "p_" + "x" * 36
            (payload / secret).write_bytes(b"synthetic fixture")
            result = subprocess.run(command, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            text = (root / "review/review-manifest.json").read_text(encoding="utf-8")
            self.assertNotIn(secret, text + result.stdout + result.stderr)
            self.assertIn("redacted unsafe filename", text)
            errors = json.loads(text)["whole_payload_privacy_diagnostic"]["errors"]
            self.assertEqual([item["rule"] for item in errors], ["Unsafe relative filename"])

    def test_partial_manifest_and_output_are_safe(self):
        with tempfile.TemporaryDirectory(prefix="pj-review-fixture-") as temp:
            root = Path(temp)
            payload, command = self.setup_fixture(root)
            canary = "CANARY_PRIVATE_USER"
            with (payload / "ToolboxMosaico.dll").open("ab") as stream:
                stream.write(("\0C:\\Users\\" + canary + "\\secret.bin\0").encode())
            output = root / "github-output"
            output.write_text("sentinel\n")
            result = subprocess.run(command, text=True, capture_output=True,
                                    env={**os.environ, "GITHUB_OUTPUT": str(output)})
            self.assertNotEqual(result.returncode, 0)
            manifest = (root / "review/review-manifest.json").read_text()
            self.assertNotIn(canary, manifest + result.stdout + result.stderr)
            self.assertEqual(output.read_text(), "sentinel\nmanifest-ready=true\n")
            self.assertFalse((root / "review/ToolboxMosaico.dll").exists())
            self.assertTrue((root / "review/DataLoadParquet.dll").exists())
            self.assertGreater(json.loads(manifest)["selected"]["ToolboxMosaico.dll"]["unknown_marker_count"], 0)

    def test_adjacent_known_literal_scans_residual_prefix(self):
        old = ReviewScope.old
        literal = ReviewScope.new
        policy = ReviewScope().policy()
        sensitive = (r"C:\Users\OtherUser\private.bin", "gh" + "p_" + "x" * 36,
                     "-----BEGIN PRIVATE KEY-----\n" + "A" * 128 + "\n-----END PRIVATE KEY-----",
                     "person" + "@qq.com")
        for encoding, offset in (("ascii", b""), ("utf-16le", b""), ("utf-16le", b"x")):
            for prefix in sensitive:
                with self.subTest(encoding=encoding, offset=len(offset), kind=sha(prefix.encode())):
                    data = offset + (prefix + literal + "\0").encode(encoding)
                    with self.assertRaises(ValueError):
                        candidate_privacy(data, "DataLoadParquet.dll", policy, check)
                    if "@qq.com" in prefix:
                        self.assertTrue(path_diagnostics(data, [old])["hashes_suppressed_for_secret"])
                        self.assertEqual(path_diagnostics(data, [old])["path_sha256"], [])
        data = (literal + "\0X" + literal + "\0").encode()
        found, _, _ = candidate_privacy(data, "DataLoadParquet.dll", policy, check)
        self.assertEqual(found, [literal])

    def test_end_only_shadow_is_not_production_approval(self):
        with tempfile.TemporaryDirectory(prefix="pj-review-fixture-") as temp:
            root = Path(temp)
            payload, command = self.setup_fixture(root)
            path = payload / "DataLoadParquet.dll"
            data = bytearray(path.read_bytes())
            offset = data.find(PUBLIC_SOURCE.encode())
            self.assertGreater(offset, 0)
            data[offset - 1] = ord("X")
            path.write_bytes(data)
            result = subprocess.run(command, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((root / "review/DataLoadParquet.dll").read_bytes(), data)
            entry = json.loads((root / "review/review-manifest.json").read_text())["selected"]["DataLoadParquet.dll"]
            self.assertTrue(entry["rc5_end_only_shadow"]["passed"])
            self.assertEqual(entry["path_diagnostics"]["boundary_counts"]["no_nul_start"], 1)
            self.assertEqual(len(entry["path_diagnostics"]["path_sha256"]), 1)
            self.assertFalse(entry["existing_production_gate"]["passed"])
            self.assertFalse(entry["approved_for_release"])

    def test_catalog_paths_produce_quarantine_only_exports(self):
        with tempfile.TemporaryDirectory(prefix="pj-review-fixture-") as temp:
            root = Path(temp)
            payload, command = self.setup_fixture(root)
            catalog = load_quarantine_catalog()
            for name in ("ToolboxMosaico.dll", "ProtobufParser.dll"):
                path = payload / name
                with path.open("ab") as stream:
                    stream.write((catalog[name][0] + "\0").encode())
            result = subprocess.run(command, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads((root / "review/review-manifest.json").read_text())
            for name in ("ToolboxMosaico.dll", "ProtobufParser.dll"):
                self.assertEqual((root / "review" / name).read_bytes(), (payload / name).read_bytes())
                self.assertIn(catalog[name][0], report["selected"][name]["observed_public_literals"])
                self.assertFalse(report["selected"][name]["existing_production_gate"]["passed"])
                self.assertFalse(report["selected"][name]["approved_for_release"])

    def test_secret_in_selected_dll_suppresses_all_path_hashes(self):
        with tempfile.TemporaryDirectory(prefix="pj-review-fixture-") as temp:
            root = Path(temp)
            payload, command = self.setup_fixture(root)
            path = payload / "DataLoadParquet.dll"
            token = "gh" + "p_" + "x" * 36
            with path.open("ab") as stream:
                stream.write(("\0" + token + "\0").encode())
            result = subprocess.run(command, text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            manifest = (root / "review/review-manifest.json").read_text()
            self.assertNotIn(token, manifest + result.stdout + result.stderr)
            entry = json.loads(manifest)["selected"]["DataLoadParquet.dll"]
            self.assertTrue(entry["path_diagnostics"]["hashes_suppressed_for_secret"])
            self.assertEqual(entry["path_diagnostics"]["path_sha256"], [])
            self.assertFalse((root / "review/DataLoadParquet.dll").exists())

    def test_stale_review_directory_never_signals_or_overwrites(self):
        with tempfile.TemporaryDirectory(prefix="pj-review-fixture-") as temp:
            root = Path(temp)
            payload, command = self.setup_fixture(root)
            review = root / "review"
            review.mkdir()
            manifest = review / "review-manifest.json"
            dll = review / "DataLoadParquet.dll"
            manifest.write_text("stale manifest")
            dll.write_bytes(b"stale dll")
            output = root / "github-output"
            output.write_text("sentinel\n")
            result = subprocess.run(command, text=True, capture_output=True,
                                    env={**os.environ, "GITHUB_OUTPUT": str(output)})
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(output.read_text(), "sentinel\n")
            self.assertEqual(manifest.read_text(), "stale manifest")
            self.assertEqual(dll.read_bytes(), b"stale dll")
            self.assertEqual({p.name for p in review.iterdir()},
                             {"review-manifest.json", "DataLoadParquet.dll"})

    def test_build_info_extra_fields_do_not_enter_manifest(self):
        with tempfile.TemporaryDirectory(prefix="pj-review-fixture-") as temp:
            root = Path(temp)
            payload, command = self.setup_fixture(root)
            path = payload / "BUILD-INFO.json"
            info = json.loads(path.read_text(encoding="utf-8"))
            info["extra"] = "CANARY_UNRELATED_BUILD_METADATA"
            path.write_text(json.dumps(info), encoding="utf-8")
            result = subprocess.run(command, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = (root / "review/review-manifest.json").read_text()
            self.assertNotIn(info["extra"], manifest + result.stdout + result.stderr)
            report = json.loads(manifest)
            self.assertEqual(report["build_info"]["sha256"], sha(path.read_bytes()))
            self.assertEqual(set(report["build_info"]), {"commit", "source_revision", "repository", "sha256"})

    def test_mismatched_source_commit_cannot_create_review_folder(self):
        with tempfile.TemporaryDirectory(prefix="pj-review-fixture-") as temp:
            root = Path(temp)
            _, command = self.setup_fixture(root)
            command[command.index("--commit") + 1] = "0" * 40
            result = subprocess.run(command, text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((root / "review").exists())


if __name__ == "__main__":
    unittest.main()
