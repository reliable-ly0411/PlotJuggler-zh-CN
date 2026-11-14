# SPDX-License-Identifier: MPL-2.0
"""Exercise approved real DLLs and changed-content counterexamples offline."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from package_privacy import check_metadata, load_public_records

# Deliberately synthetic legacy-style path. Never imported into an allowlist.
SYNTHETIC_PUBLIC_PATH = (
    b"C:\\Users\\runneradmin\\.conan2\\p\\b\\arrow0000000000000\\b\\src\\cpp\\synthetic_only.cc\0")


def verify_payload(payload, records):
    results = []
    for name, record in records["public_ci_source_records"].items():
        data = (Path(payload) / name).read_bytes()
        # An empty marker list means a clean scan, not failed verification.
        # check_metadata raises ValueError on rejection.
        check_metadata(data, name, records)
        cases = {"synthetic_literal_only": SYNTHETIC_PUBLIC_PATH,
                 "synthetic_changed": b"different\0" + SYNTHETIC_PUBLIC_PATH,
                 "appended_content": data + b"\0different content"}
        if len(data) <= 4096:
            raise ValueError("Reviewed DLL is too small for the code mutation probe")
        changed = bytearray(data)
        changed[4096] ^= 1  # Existing real Release DLL .text mutation probe.
        cases["changed_code"] = bytes(changed)
        for case, probe in cases.items():
            try:
                check_metadata(probe, name, records)
            except ValueError:
                pass
            else:
                raise AssertionError(name + ": accepted " + case)
        # Retain the three original identity-independent leak probes and add a
        # legacy public-path injection. Updating an exact hash cannot silently
        # restore an old path exception to a no-path record.
        secrets = {"other_user_path": b"C:\\Users\\AnotherUser\\private.bin\0",
                   "github_token": ("gh" + "p_" + "x" * 36).encode(),
                   "unknown_key": ("-----BEGIN PRIVATE KEY-----\n" + "A" * 128 +
                                   "\n-----END PRIVATE KEY-----").encode(),
                   "unapproved_public_path": SYNTHETIC_PUBLIC_PATH}
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
    if not results:
        raise ValueError("No production DLL identity records to verify")
    return results


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--payload", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    # CLI policy always comes from the repository, never caller-provided JSON.
    results = verify_payload(args.payload, load_public_records())
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    count = sum(len(item["negative_cases_rejected"]) for item in results)
    print(f"PASS: {len(results)} reviewed real DLLs; {count} changed-content/credential counterexamples rejected")


if __name__ == "__main__":
    main()
