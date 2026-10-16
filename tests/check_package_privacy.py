# SPDX-License-Identifier: MPL-2.0
"""Synthetic leak regressions; never use real credentials or contact an API."""
import base64
import hashlib
from pathlib import Path
import sys
import struct
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from package_privacy import check_metadata
from pe_content_fingerprint import fingerprint, METHOD


class PackagePrivacy(unittest.TestCase):
    def setUp(self):
        self.qt_literal = "C:\\Users\\qt\\work\\qt\\qtbase\\lib\\Qt5Core.pdb"
        self.qt_data = ("RSDS\0" + self.qt_literal + "\0").encode()
        self.example = "C:\\Users\\MyUser\\Common\\.venv"
        self.example_data = ("# Published example\n" + self.example).encode()
        self.records = {
            "qt_records": {"Qt5Core.dll": {"sha256": self.sha(self.qt_data), "public_pdb_records": [self.qt_literal]}},
            "cpython_venv_example": {"sha256": self.sha(self.example_data), "literal": self.example}}

    @staticmethod
    def sha(data):
        return hashlib.sha256(data).hexdigest()

    def rejected(self, data, name="payload.bin", records=None):
        with self.assertRaises(ValueError) as error:
            check_metadata(data, name, records or self.records)
        # Do not echo arbitrary credential values in failures or CI logs.
        self.assertNotIn(data.decode("latin1"), str(error.exception))

    def test_exact_public_records(self):
        self.assertTrue(check_metadata(self.qt_data, "Qt5Core.dll", self.records))
        self.assertTrue(check_metadata(self.example_data, "usr/lib/python3.10/venv/scripts/common/Activate.ps1", self.records))

    def test_no_filename_or_prefix_exemption(self):
        self.rejected(self.qt_data, "unapproved.dll")
        self.rejected(self.qt_data + b"changed", "Qt5Core.dll")
        self.rejected(self.example_data, "README.txt")
        self.rejected(self.example_data + b"changed", "usr/lib/python3.10/venv/scripts/common/Activate.ps1")

    def test_private_path_beside_public_record(self):
        data = self.qt_data + b"C:\\Users\\PrivateUser\\flight.bin\0"
        self.rejected(data, "Qt5Core.dll")
        # Even a trusted hash can permit only its exact recorded public path.
        self.records["qt_records"]["Qt5Core.dll"]["sha256"] = self.sha(data)
        self.rejected(data, "Qt5Core.dll")

    def test_paths_in_ascii_utf16_and_forward_slashes(self):
        for text in ("C:\\Users\\PrivateUser\\workspace", "C:/Users/PrivateUser/workspace", "C:\\Users\\runneradmin\\workspace", "C:\\Users\\\u6d4b\u8bd5\u7528\u6237\\workspace"):
            for encoding in ("utf-8", "utf-16le"):
                for prefix in (b"", b"x"):
                    with self.subTest(encoding=encoding, prefix=prefix):
                        self.rejected(prefix + text.encode(encoding))

    def test_contacts_remain_blocked(self):
        for encoding in ("ascii", "utf-16le"):
            self.rejected(("synthetic" + "@" + "qq.com").encode(encoding))

    def test_token_families_and_installation_jwt(self):
        tokens = ["gh" + family + "_" + "a" * 36 for family in "pousr"]
        tokens += ["github_" + "pat_" + "b" * 70,
                   "gh" + "s_1234567_" + "eyJ" + "c" * 30 + "." + "d" * 40 + "." + "e" * 40]
        for token in tokens:
            for encoding in ("ascii", "utf-16le"):
                with self.subTest(prefix=token[:4], encoding=encoding):
                    self.rejected(token.encode(encoding))

    def test_private_key_material_and_json_escapes(self):
        for kind in ("PRIVATE KEY", "RSA PRIVATE KEY", "DSA PRIVATE KEY", "EC PRIVATE KEY", "OPENSSH PRIVATE KEY", "ENCRYPTED PRIVATE KEY"):
            key = "-" * 5 + "BEGIN " + kind + "-" * 5 + "\n" + "A" * 64 + "\n" + "B" * 64 + "\n" + "-" * 5 + "END " + kind + "-" * 5
            for value in (key, key.replace("\n", "\\n"), key.replace("\n", "\\r\\n")):
                for encoding in ("ascii", "utf-16le"):
                    self.rejected(value.encode(encoding))

    def test_approved_hash_cannot_hide_a_secret(self):
        data = self.qt_data + ("gh" + "p_" + "z" * 36).encode()
        self.records["qt_records"]["Qt5Core.dll"]["sha256"] = self.sha(data)
        self.rejected(data, "Qt5Core.dll")

    def test_public_key_header_and_token_placeholders(self):
        data = ("-" * 5 + "BEGIN PRIVATE KEY" + "-" * 5 + "\0" + "ghp_<placeholder> github_pat_<placeholder>").encode()
        self.assertEqual(check_metadata(data, "library.bin", self.records), [])

    def test_ci_source_records_have_no_directory_exemption(self):
        literal = "C:\\Users\\runneradmin\\.conan2\\p\\b\\arrow_public\\b\\src\\cpp\\src\\arrow\\array.cc"
        self.records["public_ci_source_records"] = {
            "DataLoadParquet.dll": {"observed_plugin_sha256": self.sha((literal + "\0").encode()),
                                    "nul_terminated_literals": [literal]}}
        data = (literal + "\0").encode()
        self.assertTrue(check_metadata(data, "DataLoadParquet.dll", self.records))
        self.rejected(data, "another.dll")
        self.rejected((literal + "/private.bin\0").encode(), "DataLoadParquet.dll")
        self.rejected(data + b"C:\\Users\\runneradmin\\private.bin\0", "DataLoadParquet.dll")
        self.rejected(data + ("gh" + "p_" + "x" * 36).encode(), "DataLoadParquet.dll")

    def test_ci_content_identity_blocks_auditor_synthetic_reproduction(self):
        literal = "C:\\Users\\runneradmin\\.conan2\\public\\source.cc"
        for name in ("DataLoadParquet.dll", "ToolboxMosaico.dll"):
            data = (literal + "\0").encode()
            record = {"observed_plugin_sha256": "0" * 64, "artifact_sha256": self.sha(data),
                      "nul_terminated_literals": [literal]}
            self.records["public_ci_source_records"] = {name: record}
            self.rejected(data, name)
            self.rejected(data + b"changed", name)
            # Missing identity fields must also fail closed.
            record.pop("observed_plugin_sha256")
            self.rejected(data, name)

    def test_ci_pe_content_fingerprint_is_narrow(self):
        literal = "C:\\Users\\runneradmin\\.conan2\\public\\source.cc"
        data = bytearray(1024)
        data[:2] = b"MZ"
        struct.pack_into("<I", data, 60, 128)
        data[128:132] = b"PE\0\0"
        struct.pack_into("<HHI", data, 132, 0x8664, 1, 123456)
        struct.pack_into("<HH", data, 148, 240, 0x2000)
        struct.pack_into("<H", data, 152, 0x20b)
        struct.pack_into("<I", data, 260, 16)
        struct.pack_into("<II", data, 312, 4096, 28)
        data[392:400] = b".rdata\0\0"
        struct.pack_into("<IIII", data, 400, 512, 4096, 512, 512)
        struct.pack_into("<I", data, 524, 13)
        data[600:600 + len(literal) + 1] = (literal + "\0").encode()
        struct.pack_into(">Q", data, 900, 1792127804307)
        content = {"method": METHOD, "file_bytes": len(data), "qt_rcc_mtime_offsets": [900]}
        content["sha256"] = fingerprint(data, content)
        self.assertIsNotNone(content["sha256"])
        record = {"observed_plugin_sha256": "0" * 64, "content_fingerprint": content,
                  "nul_terminated_literals": [literal]}
        self.records["public_ci_source_records"] = {"DataLoadParquet.dll": record}
        self.assertTrue(check_metadata(data, "DataLoadParquet.dll", self.records))
        changed_time = bytearray(data)
        struct.pack_into("<I", changed_time, 136, 999999)
        struct.pack_into("<I", changed_time, 516, 999999)
        struct.pack_into(">Q", changed_time, 900, 1792127805307)
        self.assertTrue(check_metadata(changed_time, "DataLoadParquet.dll", self.records))
        self.rejected(data, "another.dll")
        self.rejected(data + b"changed", "DataLoadParquet.dll")
        changed_content = bytearray(data)
        changed_content[800] = 1
        self.rejected(changed_content, "DataLoadParquet.dll")
        invalid_time = bytearray(data)
        invalid_time[900:908] = b"private!"
        self.rejected(invalid_time, "DataLoadParquet.dll")
        for extra in ("C:\\Users\\AnotherUser\\private.bin", "gh" + "p_" + "x" * 36,
                      "-----BEGIN PRIVATE KEY-----\n" + "A" * 128 + "\n-----END PRIVATE KEY-----"):
            leaked = data + b"\0" + extra.encode()
            # Even explicitly approved file identity cannot suppress these checks.
            record["observed_plugin_sha256"] = self.sha(leaked)
            self.rejected(leaked, "DataLoadParquet.dll")

    def test_immutable_public_dependency_requires_exact_hash_and_filename(self):
        data = b"C:\\Users\\runneradmin\\.cargo\\public.rs"
        self.records["immutable_public_records"] = {
            "dependency.dll": {"sha256": self.sha(data), "literals": ["C:\\Users\\runneradmin\\"]}}
        self.assertTrue(check_metadata(data, "dependency.dll", self.records))
        self.rejected(data, "other.dll")
        self.rejected(data + b"changed", "dependency.dll")
        leaked = data + b"\0C:\\Users\\PrivateUser\\secret.bin"
        self.records["immutable_public_records"]["dependency.dll"]["sha256"] = self.sha(leaked)
        self.rejected(leaked, "dependency.dll")
        token = data + ("gh" + "p_" + "x" * 36).encode()
        self.records["immutable_public_records"]["dependency.dll"]["sha256"] = self.sha(token)
        self.rejected(token, "dependency.dll")

    def test_public_selftest_keys_require_file_and_key_fingerprints(self):
        def key(body):
            return '-'*5+'BEGIN PRIVATE KEY'+'-'*5+'\n'+body+'\n'+'-'*5+'END PRIVATE KEY'+'-'*5
        public = key('A'*128)
        name = 'lib-public-selftest.so'
        fingerprint = self.sha(base64.b64decode('A'*128))
        for encoding in ('ascii', 'utf-16le'):
            data = public.encode(encoding)
            record = {'file_sha256': [self.sha(data)],
                      'public_key_fingerprints': [{'kind': 'PRIVATE KEY', 'der_sha256': fingerprint}]}
            self.records['public_selftest_keys'] = {name: record}
            self.assertTrue(check_metadata(data, name, self.records))
            self.rejected(data, 'other.so')
            self.rejected(data+b'changed', name)
            for appended in (key('B'*128), 'gh'+'p_'+'z'*36, 'C:\\Users\\PrivateUser\\secret.bin'):
                leaked = data+b'\0'+appended.encode(encoding)
                record['file_sha256'] = [self.sha(leaked)]
                self.rejected(leaked, name)


if __name__ == "__main__":
    unittest.main()
