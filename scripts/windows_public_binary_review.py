# SPDX-License-Identifier: MPL-2.0
"""Collect privacy-scanned Windows DLL evidence for independent review only.

All production identity records remain unchanged. Only three positively privacy-
scanned DLLs may be copied to a newly created quarantine evidence directory.
The folder MUST be uploaded as ReviewOnly-*, never Software-* or a release asset.
The production real-DLL and whole-package gates must still execute unchanged.
"""
import argparse
import copy
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from package_privacy import check_metadata, load_public_records
from pe_content_fingerprint import fingerprint, METHOD
from windows_public_binary_review_helpers import (
    NAMES, QRC_EXPECTED, candidate_privacy, derive_qrc_offsets, observed_public_literals, unknown_marker_count, unknown_public_path_hashes, sha,
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
        return "<redacted unsafe filename>"
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
    info_bytes = info_paths[0].read_bytes()
    check_metadata(info_bytes, "BUILD-INFO.json", records)
    selected, selected_bytes = {}, {}
    temporary = copy.deepcopy(records)
    # Resource provenance is relevant only to Toolbox; missing/ambiguous
    # sources must not prevent independent scans of the other selected DLLs.
    sources = []
    source_error = False
    for basename in QRC_EXPECTED:
        paths = list(build.rglob(basename))
        if len(paths) != 1:
            source_error = True
            continue
        try:
            sources.append((basename, paths[0].read_bytes()))
        except OSError:
            source_error = True
    for name in NAMES:
        COLLECTION_PHASE = "selected DLL review: " + name
        entry = {"status": "failed", "approved_for_release": False,
                 "rule": "Missing or unreadable regular DLL", "unknown_marker_count": 0}
        selected[name] = entry
        path = payload / name
        try:
            if not path.is_file() or path.is_symlink():
                continue
            data = path.read_bytes()
            entry["sha256"] = sha(data)
            old = ([literal for record in records["public_ci_source_records"].values()
                    for literal in record["nul_terminated_literals"]]
                   if name == "ProtobufParser.dll" else
                   records["public_ci_source_records"][name]["nul_terminated_literals"])
            literals = observed_public_literals(data, old)
            entry["unknown_marker_count"] = unknown_marker_count(data, literals)
            entry["unknown_public_path_sha256"] = unknown_public_path_hashes(data, old, literals)
            entry["rule"] = "Package privacy scanner rejected file"
            try:
                literals, markers, scan_policy = candidate_privacy(data, name, records, check_metadata)
            except ValueError as error:
                entry["rule"] = privacy_rule(error)
                continue
            entry["privacy_scan"] = "passed for quarantine only"
            temporary["public_ci_source_records"][name] = scan_policy["public_ci_source_records"][name]
            try:
                if name not in records.get("public_ci_source_records", {}):
                    raise ValueError("Unapproved public-source binary content in " + name)
                check_metadata(data, name, records)
            except ValueError as error:
                entry["existing_production_gate"] = {"passed": False, "rule": privacy_rule(error)}
            else:
                entry["existing_production_gate"] = {"passed": True}
            entry["rule"] = "Fingerprint or provenance unsupported; identity not approved"
            if name == "ToolboxMosaico.dll":
                if source_error:
                    continue
                offsets, provenance = derive_qrc_offsets(data, sources)
                check_metadata(json.dumps(provenance).encode("utf-8"), "resource-provenance.json", records)
            else:
                offsets, provenance = [], []
            content = {"method": METHOD, "file_bytes": len(data), "qt_rcc_mtime_offsets": offsets}
            content["sha256"] = fingerprint(data, content)
            if not content["sha256"]:
                continue
            entry.update({"status": "safe for independent review only",
                          "file_bytes": len(data), "observed_public_literals": literals,
                          "qrc_field_provenance": provenance,
                          "content_fingerprint_for_review": content})
            entry.pop("rule")
            selected_bytes[name] = data
        except (ValueError, OSError, KeyError, UnicodeError, IndexError):
            # Never expose exception text, which can contain private bytes.
            continue
    # Diagnostic only. Production whole-package audit remains a separate gate.
    inventory, errors = [], []
    COLLECTION_PHASE = "whole-payload privacy diagnostics"
    for path in sorted(payload.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        name = path.relative_to(payload).as_posix()
        data = path.read_bytes()
        safe_name = diagnostic_name(name, records)
        entry = {"path": safe_name, "file_bytes": len(data), "sha256": sha(data)}
        inventory.append(entry)
        if safe_name != name:
            errors.append({**entry, "rule": "Unsafe relative filename"})
        try:
            check_metadata(data, name, temporary)
        except ValueError as error:
            errors.append({**entry, "rule": privacy_rule(error)})
    report = {
        "purpose": "Quarantined evidence for independent review; NOT a release approval",
        "source_commit": args.commit,
        "run": expected_repo + "/actions/runs/" + args.run,
        "run_attempt": int(args.run_attempt),
        "approved_policy_sha256": sha(policy_path.read_bytes()),
        "build_info": {"commit": args.commit, "source_revision": args.commit[:12],
                       "repository": expected_repo, "sha256": sha(info_bytes)},
        "production_gate_unchanged": True,
        "selected": selected,
        "whole_payload_privacy_diagnostic": {"approved_for_release": False,
                                              "files": inventory, "errors": errors},
        "not_executed": ["Independent binary review", "14 real-DLL counterexamples against any new approved identity",
                         "Candidate package acceptance", "Release eligibility"],
    }
    COLLECTION_PHASE = "isolated review export"
    out.mkdir(parents=True, exist_ok=False)
    for name, data in selected_bytes.items():
        (out / name).write_bytes(data)
        if sha((out / name).read_bytes()) != selected[name]["sha256"]:
            (out / name).unlink(missing_ok=True)
            raise ValueError("Review copy verification failed")
    # A completed atomic manifest is the only signal that upload is safe.
    temp_manifest = out / "review-manifest.json.tmp"
    temp_manifest.write_text(json.dumps(report, indent=2), encoding="utf-8")
    os.replace(temp_manifest, out / "review-manifest.json")
    # This invocation created the directory, verified every exported copy, and
    # atomically committed the manifest. Never signal based on an existing file.
    print(json.dumps({"review_only": True, "selected_files": list(selected_bytes)}))
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8", newline="\n") as stream:
            stream.write("manifest-ready=true\n")
    if len(selected_bytes) != len(NAMES):
        raise SystemExit(1)


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
