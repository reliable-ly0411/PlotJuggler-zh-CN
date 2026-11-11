# SPDX-License-Identifier: MPL-2.0
"""Collect privacy-scanned Windows DLL evidence for independent review only.

All production identity records remain unchanged. Only two positively privacy-
scanned DLLs may be copied to a newly created quarantine evidence directory.
The folder MUST be uploaded as ReviewOnly-*, never Software-* or a release asset.
The production real-DLL and whole-package gates must still execute unchanged.
"""
import argparse
import copy
import json
from pathlib import Path
import re
import subprocess
import sys

from package_privacy import check_metadata, load_public_records
from pe_content_fingerprint import fingerprint, METHOD
from windows_public_binary_review_helpers import (
    NAMES, QRC_EXPECTED, candidate_privacy, derive_qrc_offsets, sha,
)

COLLECTION_PHASE = "argument validation"


def privacy_rule(error):
    """Return only fixed scanner rule text, never untrusted file/matched bytes."""
    for rule in ("Unapproved public-source binary content", "Unexpected GitHub credential material",
                 "Unexpected private-key material", "Unexpected personal contact", "Unexpected private path"):
        if str(error).startswith(rule + " in "):
            return rule
    return "Package privacy scanner rejected file"


def diagnostic_name(name, records):
    try:
        check_metadata(name.encode("utf-8"), "review-diagnostic-filename", records)
    except ValueError:
        return "<redacted unsafe filename; sha256=" + sha(name.encode("utf-8")) + ">"
    return name


def main():
    global COLLECTION_PHASE
    parser = argparse.ArgumentParser(__doc__)
    for name in ("repo", "payload", "build", "out", "commit", "run", "run-attempt"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    repo, payload, build, out = (Path(value).resolve() for value in
                                 (args.repo, args.payload, args.build, args.out))
    if not re.fullmatch(r"[0-9a-f]{40}", args.commit):
        raise ValueError("Full immutable source SHA required")
    if not re.fullmatch(r"[1-9][0-9]*", args.run) or not re.fullmatch(r"[1-9][0-9]*", args.run_attempt):
        raise ValueError("Immutable workflow run and attempt required")
    COLLECTION_PHASE = "source and staged-build provenance"
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    if head != args.commit:
        raise ValueError("Source HEAD differs from expected workflow SHA")
    info_paths = list(payload.rglob("BUILD-INFO.json"))
    if len(info_paths) != 1:
        raise ValueError("Exactly one staged build identity is required")
    info = json.loads(info_paths[0].read_text(encoding="utf-8-sig"))
    expected_repo = "https://github.com/reliable-ly0411/PlotJuggler-zh-CN"
    if (info.get("commit") != args.commit or info.get("repository") != expected_repo or
            info.get("source_revision") != args.commit[:12]):
        raise ValueError("Staged build identity does not match this source")
    if out == payload or payload in out.parents or out.exists():
        raise ValueError("Review folder must be new and outside staged payload")
    # Use the policy alongside this source, not an arbitrary caller policy.
    policy_path = Path(__file__).resolve().parents[1] / "tests/data/public-build-records.json"
    if repo != Path(__file__).resolve().parents[1]:
        raise ValueError("Source repository must own this review tool and policy")
    records = load_public_records()
    # BUILD-INFO is included in the review manifest; it must itself be safe to
    # disclose. Diagnostic errors elsewhere never justify exporting this file.
    COLLECTION_PHASE = "BUILD-INFO privacy scan"
    check_metadata(info_paths[0].read_bytes(), "BUILD-INFO.json", records)
    temporary = copy.deepcopy(records)
    selected = {}
    selected_bytes = {}
    sources = []
    COLLECTION_PHASE = "generated Qt5 resource inventory"
    for basename in QRC_EXPECTED:
        paths = list(build.rglob(basename))
        if len(paths) != 1:
            raise ValueError("Expected one generated resource source per reviewed resource")
        path = paths[0]
        sources.append((path.relative_to(build).as_posix(), path.read_bytes()))
    # No binary is copied before BOTH selected DLLs pass the existing privacy
    # scanner under the narrow review-only public-path classification.
    for name in NAMES:
        COLLECTION_PHASE = "selected DLL privacy scan: " + name
        path = payload / name
        if not path.is_file() or path.is_symlink():
            raise ValueError("Missing regular staged DLL: " + name)
        data = path.read_bytes()
        literals, markers, scan_policy = candidate_privacy(data, name, records, check_metadata)
        COLLECTION_PHASE = "Qt5 resource provenance: " + name
        offsets, qrc_provenance = derive_qrc_offsets(data, sources) if name == "ToolboxMosaico.dll" else ([], [])
        check_metadata(json.dumps(qrc_provenance).encode("utf-8"), "resource-provenance.json", records)
        COLLECTION_PHASE = "bounded PE fingerprint: " + name
        content = {"method": METHOD, "file_bytes": len(data), "qt_rcc_mtime_offsets": offsets}
        content["sha256"] = fingerprint(data, content)
        if not content["sha256"]:
            raise ValueError("Unrecognized bounded PE fingerprint form in " + name)
        try:
            check_metadata(data, name, records)
        except ValueError as error:
            existing_gate = {"passed": False, "rule": privacy_rule(error)}
        else:
            existing_gate = {"passed": True}
        temporary["public_ci_source_records"][name] = scan_policy["public_ci_source_records"][name]
        selected[name] = {"file_bytes": len(data), "sha256": sha(data),
                          "privacy_scan": "passed for quarantine only",
                          "existing_production_gate": existing_gate,
                          "observed_public_literals": literals,
                          "content_fingerprint_for_review": content,
                          "qrc_field_provenance": qrc_provenance,
                          "classified_markers": markers}
        selected_bytes[name] = data
    # Diagnostic coverage of every staged file, even when the production gate
    # stopped at the first DLL. This report does not approve the package.
    inventory, errors = [], []
    COLLECTION_PHASE = "whole-payload privacy diagnostics"
    for path in sorted(payload.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        name = path.relative_to(payload).as_posix()
        data = path.read_bytes()
        entry = {"path": diagnostic_name(name, records), "file_bytes": len(data), "sha256": sha(data)}
        inventory.append(entry)
        if entry["path"] != name:
            errors.append({**entry, "rule": "Unsafe relative filename"})
        try:
            check_metadata(data, name, temporary)
        except ValueError as error:
            errors.append({**entry, "rule": privacy_rule(error)})
    report = {
        "purpose": "Quarantined build evidence for independent review; NOT a release approval",
        "source_commit": args.commit,
        "run": expected_repo + "/actions/runs/" + args.run,
        "run_attempt": int(args.run_attempt),
        "build_info": info,
        "approved_policy_sha256": sha(policy_path.read_bytes()),
        "production_gate_unchanged": True,
        "selected": selected,
        "whole_payload_privacy_diagnostic": {"approved_for_release": False,
                                              "files": inventory, "errors": errors},
        "not_executed": ["Independent binary review", "14 real-DLL counterexamples against any new approved identity",
                         "Candidate package acceptance", "Release eligibility"],
    }
    COLLECTION_PHASE = "isolated review export"
    out.mkdir(parents=True, exist_ok=False)
    (out / "review-manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    for name in NAMES:
        # Write the already scanned bytes, avoiding a scan/copy race.
        (out / name).write_bytes(selected_bytes[name])
        if sha((out / name).read_bytes()) != selected[name]["sha256"]:
            raise ValueError("Copied review file differs from scanned bytes")
    print(json.dumps({"review_only": True, "source_commit": args.commit,
                      "selected_files": list(selected), "payload_privacy_errors": len(errors)}))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as error:
        # No matched bytes/paths, environment values or credentials are logged.
        print(type(error).__name__ + ": review collection failed during " + COLLECTION_PHASE,
              file=sys.stderr)
        if isinstance(error, ValueError):
            print(privacy_rule(error), file=sys.stderr)
        raise SystemExit(1)
