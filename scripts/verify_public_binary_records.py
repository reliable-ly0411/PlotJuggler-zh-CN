# SPDX-License-Identifier: MPL-2.0
"""Exercise approved real DLLs and changed-content counterexamples offline."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from package_privacy import check_metadata, load_public_records

p = argparse.ArgumentParser()
p.add_argument("--payload", required=True)
p.add_argument("--out", required=True)
a = p.parse_args()
records = load_public_records()
results = []
for name, record in records["public_ci_source_records"].items():
    data = (Path(a.payload) / name).read_bytes()
    assert check_metadata(data, name, records)
    literal = record["nul_terminated_literals"][0].encode() + b"\0"
    cases = {"synthetic_literal_only": literal, "synthetic_changed": b"different\0" + literal,
             "appended_content": data + b"\0different content"}
    changed = bytearray(data)
    changed[4096] ^= 1  # In the actual .text section, never a timestamp.
    cases["changed_code"] = bytes(changed)
    for case, probe in cases.items():
        try:
            check_metadata(probe, name, records)
        except ValueError:
            pass
        else:
            raise AssertionError(name + ": accepted " + case)
    # Independently of identity checking, no approved hash may hide a secret.
    secrets = {"other_user_path": b"C:\\Users\\AnotherUser\\private.bin\0",
               "github_token": ("gh" + "p_" + "x" * 36).encode(),
               "unknown_key": ("-----BEGIN PRIVATE KEY-----\n" + "A" * 128 +
                               "\n-----END PRIVATE KEY-----").encode()}
    for case, extra in secrets.items():
        probe = data + b"\0" + extra
        policy = copy.deepcopy(records)
        policy["public_ci_source_records"][name]["observed_plugin_sha256"] = hashlib.sha256(probe).hexdigest()
        try:
            check_metadata(probe, name, policy)
        except ValueError:
            pass
        else:
            raise AssertionError(name + ": accepted " + case)
    results.append({"file": name, "sha256": hashlib.sha256(data).hexdigest(),
                    "content_sha256": record["content_fingerprint"]["sha256"],
                    "accepted": True, "negative_cases_rejected": list(cases) + list(secrets)})
out = Path(a.out)
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(results, indent=2), encoding="utf-8")
print("PASS: two reviewed real DLLs; 14 changed-content/credential counterexamples rejected")
