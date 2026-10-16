# SPDX-License-Identifier: MPL-2.0
"""Measure actual Qt5 RCC output, without running any downloaded application."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as ET

p = argparse.ArgumentParser()
p.add_argument("--rcc", default="rcc")
p.add_argument("--out", required=True)
a = p.parse_args()
root = Path(__file__).resolve().parents[1]
versions = [("zh.2", "de2821269e4fa138ff88dd5e856b111cc4942ee9"),
            ("zh.3", "3117288ce8d710bde4f7a86ca5ed5240ebb1c301"), ("zh.4", None)]

def read(revision, name):
    return (root / name).read_bytes() if revision is None else subprocess.check_output(
        ["git", "show", revision + ":" + name], cwd=root)

result = {"rcc": subprocess.check_output([a.rcc, "--version"], stderr=subprocess.STDOUT, text=True).strip(),
          "compression": "Qt5 default binary RCC options", "versions": []}
with tempfile.TemporaryDirectory() as temp:
    for label, revision in versions:
        work = Path(temp) / label
        work.mkdir()
        qrc_names = ["resource.qrc"] + (["localized_resources.qrc"] if revision is None else [])
        measurements = []
        for name in qrc_names:
            data = read(revision, "plotjuggler_app/" + name)
            (work / name).write_bytes(data)
            files = ET.fromstring(data).findall(".//file")
            total = 0
            hashes = {}
            for node in files:
                payload = read(revision, "plotjuggler_app/" + node.text)
                target = work / node.text
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(payload)
                total += len(payload)
                hashes.setdefault(hashlib.sha256(payload).hexdigest(), []).append(node.text)
            binary = work / (name + ".rcc")
            subprocess.run([a.rcc, "-binary", name, "-o", str(binary)], cwd=work, check=True)
            measurements.append({"qrc": name, "entries": len(files), "source_bytes": total,
                                 "binary_rcc_bytes": binary.stat().st_size,
                                 "duplicate_payload_groups": [v for v in hashes.values() if len(v) > 1]})
        result["versions"].append({"version": label, "source": revision or "working checkout",
                                   "qrc": measurements,
                                   "binary_rcc_bytes": sum(m["binary_rcc_bytes"] for m in measurements)})
out = Path(a.out)
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
