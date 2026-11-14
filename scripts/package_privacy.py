# SPDX-License-Identifier: MPL-2.0
"""Offline package checks. Diagnostics identify the file/rule, never the matched secret."""
import base64
import binascii
import hashlib
import json
from pathlib import Path
import re
from pe_content_fingerprint import fingerprint as pe_fingerprint
from linux_public_elf import reviewed_spans
from private_build_roots import contains_private_root

# Prefix families, including variable-length installation JWTs, are documented at:
# https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/about-authentication-to-github#githubs-token-formats
GITHUB_TOKEN = re.compile(r"(?:gh[pousr]_[A-Za-z0-9_.-]{24,}|github_pat_[A-Za-z0-9_]{20,})")
PRIVATE_KEY = re.compile(r"-----BEGIN ((?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY)-----[ \t]*(?:\r?\n|\\r\\n|\\n)([A-Za-z0-9+/=\\\s]+?)-----END \1-----")
PRIVATE_PATH = re.compile(r"[A-Z]:[\\/]Users[\\/](?!Public[\\/]|Default[\\/])[^\\/\x00\r\n]+", re.I)
# Concrete task-owned root and Conan's identifiable package cache layout, on
# any drive. Do not treat arbitrary absolute paths or vendor examples as private.
PRIVATE_BUILD_PATH = re.compile(
    r"[A-Z]:[\\/](?:PJ3181-20261111-1235(?:[\\/]|$)|"
    r"(?:[^\x00\r\n]*?[\\/])?(?:\.conan2|conan[^\\/\x00\r\n]*)[\\/]p[\\/](?:b[\\/])?[^\\/\x00\r\n]+[\\/])",
    re.I)
# Reject task directory families before any public-record substitutions.
# Exact roots also come from the mandatory private package-audit manifest.
TASK_PRIVATE_ROOT = re.compile(
    r"[A-Z]:[\\/]PJ(?:[0-9]{2}[0-9A-Z]{2,4}|"
    r"[0-9]{4}-RC[0-9]+-[0-9A-F]{8}-[0-9]{8})(?=$|[\\/\x00\s\"'=])",
    re.I)
REVIEWED_WINDOWS_MODULES = frozenset(name.casefold() for name in
    ("DataLoadParquet.dll", "ToolboxMosaico.dll", "ProtobufParser.dll"))
PERSONAL_CONTACT = re.compile(r"@qq\.com\b", re.I)
PYTHON_EXAMPLE_FILE = re.compile(r"(^|/)python3\.\d+/venv/scripts/common/Activate\.ps1$")


def load_public_records():
    path = Path(__file__).resolve().parents[1] / "tests/data/public-build-records.json"
    return json.loads(path.read_text(encoding="utf-8"))


def check_metadata(data, relative_name, records, private_roots=None):
    """Return narrowly classified public markers, or reject unexpected sensitive data.

    Approved file hashes permit only exact path literals. Every byte is still
    checked for secret material and unrelated private paths before acceptance.
    """
    name = relative_name.replace("\\", "/")
    # Examine the original bytes before identity checks or approved masks.
    views = (data.decode("latin1"), data.decode("utf-8", errors="replace"),
             data.decode("utf-16le", errors="ignore"), data[1:].decode("utf-16le", errors="ignore"))
    if any(TASK_PRIVATE_ROOT.search(view) for view in views) or (
            private_roots is not None and contains_private_root(data, private_roots)):
        raise ValueError("Unexpected private path in " + name)
    digest = hashlib.sha256(data).hexdigest()
    qt = {key.casefold(): value for key, value in records.get("qt_records", {}).items()}.get(name.casefold())
    qt = qt if qt and qt["sha256"] == digest else None
    ci = records.get("public_ci_source_records", {}).get(name, {})
    local = records.get("local_reviewed_exact_sha256", {}).get(name, {})
    local_exact = (local.get("sha256") == digest and local.get("bytes") == len(data))
    if name.rsplit("/", 1)[-1].casefold() in REVIEWED_WINDOWS_MODULES and not (ci or local_exact):
        raise ValueError("Unapproved public-source binary content in " + name)
    if ci and not local_exact:
        content = ci.get("content_fingerprint", {})
        exact = digest == ci.get("observed_plugin_sha256")
        equivalent = bool(content.get("sha256") and pe_fingerprint(data, content) == content["sha256"])
        if not (exact or equivalent):
            raise ValueError("Unapproved public-source binary content in " + name)
    immutable = records.get("immutable_public_records", {}).get(name, {})
    immutable = immutable if immutable.get("sha256") == digest else {}
    selftest = records.get("public_selftest_keys", {}).get(name, {})
    approved_keys = {(item["kind"], item["der_sha256"])
                     for item in selftest.get("public_key_fingerprints", [])}
    if digest not in selftest.get("file_sha256", []):
        approved_keys = set()
    example = records.get("cpython_venv_example", {})
    python_example = bool(PYTHON_EXAMPLE_FILE.search(name) and digest == example.get("sha256"))
    markers = ([{"path": name, "kind": "local reviewed exact SHA256", "file_sha256": digest}]
               if local_exact else [])
    # A local identity grants no public CI path exemptions.
    if local_exact:
        ci = {}
    linux_spans = reviewed_spans(data, name)
    representations = (data.decode("latin1"), data.decode("utf-16le", errors="ignore"),
                       data[1:].decode("utf-16le", errors="ignore"))
    for index, text in enumerate(representations):
        # These checks precede path classification even for an approved dependency.
        if GITHUB_TOKEN.search(text):
            raise ValueError("Unexpected GitHub credential material in " + name)
        for match in PRIVATE_KEY.finditer(text):
            if index == 0 and ("private_key", match.start(), match.end()) in linux_spans:
                markers.append({"path": name, "kind": "exact public ELF NUL record", "rule": "private key"})
                continue
            body = re.sub(r"\s+", "", match[2].replace("\\n", "").replace("\\r", ""))
            if len(body) >= 64 and re.fullmatch(r"[A-Za-z0-9+/=]+", body):
                try:
                    fingerprint = hashlib.sha256(base64.b64decode(body, validate=True)).hexdigest()
                except (ValueError, binascii.Error):
                    fingerprint = "invalid base64"
                if (match[1], fingerprint) not in approved_keys:
                    raise ValueError("Unexpected private-key material in " + name)
                markers.append({"path": name, "kind": "hash-verified published self-test key",
                                "der_sha256": fingerprint})
        if PERSONAL_CONTACT.search(text):
            raise ValueError("Unexpected personal contact in " + name)
        # Only the precise path regex span is masked, not its entire record.
        # All other content and representations remain subject to every rule.
        if index == 0:
            replacements = [(m.start(), m.end()) for m in PRIVATE_PATH.finditer(text)
                            if ("private_path", m.start(), m.end()) in linux_spans]
            for start, end in reversed(replacements):
                text = text[:start] + "X" * (end - start) + text[end:]
                markers.append({"path": name, "kind": "exact public ELF NUL record", "rule": "private path"})
        count = 0
        for literal in immutable.get("literals", []):
            count += text.count(literal)
            text = text.replace(literal, "<hash-verified public dependency record>")
        if count:
            markers.append({"path": name, "kind": "hash-verified public dependency record", "count": count})
        # Require complete binary identity above, then replace only previously
        # reviewed, NUL-terminated Arrow __FILE__ records. No directory exemption.
        count = 0
        for literal in ci.get("nul_terminated_literals", []):
            count += text.count(literal + "\0")
            text = text.replace(literal + "\0", "<verified public CI source record>\0")
        if count:
            markers.append({"path": name, "kind": "content-verified public CI source record", "count": count,
                            "file_sha256": digest, "content_sha256": content.get("sha256")})
        if qt:
            count = 0
            for literal in qt["public_pdb_records"]:
                count += text.count(literal)
                text = text.replace(literal, "<verified public Qt PDB record>")
            if count:
                markers.append({"path": name, "kind": "hash-verified Qt PDB record", "count": count})
        if python_example:
            literal = example["literal"]
            count = text.count(literal)
            text = text.replace(literal, "<verified CPython documentation example>")
            if count:
                markers.append({"path": name, "kind": "hash-verified CPython documentation example", "count": count})
        if PRIVATE_PATH.search(text) or PRIVATE_BUILD_PATH.search(text):
            raise ValueError("Unexpected private path in " + name)
    return markers
