# SPDX-License-Identifier: MPL-2.0
"""Offline package checks. Diagnostics identify the file/rule, never the matched secret."""
import hashlib
import json
from pathlib import Path
import re

# Prefix families, including variable-length installation JWTs, are documented at:
# https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/about-authentication-to-github#githubs-token-formats
GITHUB_TOKEN = re.compile(r"(?:gh[pousr]_[A-Za-z0-9_.-]{24,}|github_pat_[A-Za-z0-9_]{20,})")
PRIVATE_KEY = re.compile(r"-----BEGIN ((?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY)-----[ \t]*(?:\r?\n|\\r\\n|\\n)([A-Za-z0-9+/=\\\s]+?)-----END \1-----")
PRIVATE_PATH = re.compile(r"[A-Z]:[\\/]Users[\\/](?!Public[\\/]|Default[\\/])[^\\/\x00\r\n]+", re.I)
PERSONAL_CONTACT = re.compile(r"@qq\.com\b", re.I)
PYTHON_EXAMPLE_FILE = re.compile(r"(^|/)python3\.\d+/venv/scripts/common/Activate\.ps1$")


def load_public_records():
    path = Path(__file__).resolve().parents[1] / "tests/data/public-build-records.json"
    return json.loads(path.read_text(encoding="utf-8"))


def check_metadata(data, relative_name, records):
    """Return narrowly classified public markers, or reject unexpected sensitive data.

    Approved file hashes permit only exact path literals. Every byte is still
    checked for secret material and unrelated private paths before acceptance.
    """
    name = relative_name.replace("\\", "/")
    digest = hashlib.sha256(data).hexdigest()
    qt = {key.casefold(): value for key, value in records.get("qt_records", {}).items()}.get(name.casefold())
    qt = qt if qt and qt["sha256"] == digest else None
    ci = records.get("public_ci_source_records", {}).get(name, {})
    immutable = records.get("immutable_public_records", {}).get(name, {})
    immutable = immutable if immutable.get("sha256") == digest else {}
    example = records.get("cpython_venv_example", {})
    python_example = bool(PYTHON_EXAMPLE_FILE.search(name) and digest == example.get("sha256"))
    markers = []
    representations = (data.decode("latin1"), data.decode("utf-16le", errors="ignore"),
                       data[1:].decode("utf-16le", errors="ignore"))
    for text in representations:
        # These checks precede path classification even for an approved dependency.
        if GITHUB_TOKEN.search(text):
            raise ValueError("Unexpected GitHub credential material in " + name)
        for match in PRIVATE_KEY.finditer(text):
            body = re.sub(r"\s+", "", match[2].replace("\\n", "").replace("\\r", ""))
            if len(body) >= 64 and re.fullmatch(r"[A-Za-z0-9+/=]+", body):
                raise ValueError("Unexpected private-key material in " + name)
        if PERSONAL_CONTACT.search(text):
            raise ValueError("Unexpected personal contact in " + name)
        count = 0
        for literal in immutable.get("literals", []):
            count += text.count(literal)
            text = text.replace(literal, "<hash-verified public dependency record>")
        if count:
            markers.append({"path": name, "kind": "hash-verified public dependency record", "count": count})
        # Unlike dependency DLLs, our linked plugin changes its PE build fields
        # between runs. Accept only complete NUL-terminated, previously observed
        # public Arrow __FILE__ records, never the runneradmin directory generally.
        count = 0
        for literal in ci.get("nul_terminated_literals", []):
            count += text.count(literal + "\0")
            text = text.replace(literal + "\0", "<verified public CI source record>\0")
        if count:
            markers.append({"path": name, "kind": "exact public CI source record", "count": count})
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
        if PRIVATE_PATH.search(text):
            raise ValueError("Unexpected private path in " + name)
    return markers
