# SPDX-License-Identifier: MPL-2.0
"""Preserve Conan host dependency notices without modifying the package cache."""
import hashlib
import json
from pathlib import Path
import shutil

import importlib.util

_spec = importlib.util.spec_from_file_location("arrow_source_evidence", Path(__file__).with_name("arrow_source_evidence.py"))
_arrow_source = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_arrow_source)
stage_arrow_source = _arrow_source.stage


def deploy(graph, output_folder, **kwargs):
    destination = Path(output_folder) / "Conan"
    destination.mkdir(parents=True, exist_ok=True)
    records = []
    for dependency in graph.root.conanfile.dependencies.host.values():
        if not dependency.package_folder:
            continue  # Conan skipped this binary; no package payload is linked.
        reference = str(dependency.ref)
        name = f"{dependency.ref.name}-{dependency.ref.version}"
        source = Path(dependency.package_folder) / "licenses"
        files = sorted(path for path in source.rglob("*") if path.is_file())
        if not files:
            raise RuntimeError(f"No packaged license texts for Conan host dependency {reference}")
        entries = []
        for path in files:
            target = destination / name / path.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
            entries.append({"path": target.relative_to(destination).as_posix(),
                            "sha256": hashlib.sha256(target.read_bytes()).hexdigest()})
        record = {"reference": reference, "files": entries}
        if dependency.ref.name.lower() == "arrow":
            # Do not borrow NOTICE from another Arrow version or infer that a
            # copyright file contains all upstream attribution requirements.
            notices = [entry["path"] for entry in entries
                       if Path(entry["path"]).name.lower() in ("notice", "notice.txt")]
            record["notice_evidence"] = {
                "status": "packaged-unverified" if notices else "missing",
                "paths": notices,
                "review": "Compare with NOTICE from this exact Arrow source release; "
                          "this inventory is not license approval",
            }
            source = stage_arrow_source(str(dependency.ref.version), destination / name / "upstream-source")
            if source["status"] == "missing":
                raise RuntimeError(f"Arrow {dependency.ref.version}: pinned source texts missing")
            source["directory"] = f"{name}/upstream-source"
            record["source_evidence"] = source
            if source["status"] in ("source-texts-sha256-verified", "pinned-vendored-source-texts"):
                source_hash = source["files"]["NOTICE.txt"]
                record["notice_evidence"]["source_byte_matches"] = [
                    entry["path"] for entry in entries
                    if entry["path"] in notices and entry["sha256"] == source_hash]
        records.append(record)
    (destination / "manifest.json").write_text(
        json.dumps({"scope": "Conan host dependency notices, including test dependencies; "
                            "not a claim that every listed library is shipped",
                    "closure_status": "incomplete",
                    "dependencies": sorted(records, key=lambda entry: entry["reference"])},
                   indent=2), encoding="utf-8")
