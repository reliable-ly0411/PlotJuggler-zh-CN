# SPDX-License-Identifier: MPL-2.0
"""Rebuild reviewed lossless variants from the immutable source images (Pillow 11.3.0)."""
import hashlib
import io
import json
from pathlib import Path
import subprocess

from PIL import Image

root = Path(__file__).resolve().parents[1]
directory = root / "plotjuggler_app/resources/memes"
catalog = json.loads((directory / "zh_CN.json").read_text(encoding="utf-8"))
for entry in catalog["images"]:
    variant = entry.get("variant")
    if not variant:
        continue
    reference = entry["reference"]
    data = subprocess.check_output([
        "git", "show", catalog["reference_commit"] + ":plotjuggler_app/resources/memes/" + reference["file"]
    ], cwd=root)
    assert hashlib.sha256(data).hexdigest() == reference["sha256"]
    with Image.open(io.BytesIO(data)) as source:
        source = source.convert("RGB")
        if "image" in variant:
            outputs = {variant["image"]: source}
        else:
            outputs = {}
            for patch, proof in zip(variant["patches"], reference["patches"]):
                name = patch["file"]
                if name not in outputs:
                    outputs[name] = Image.new("RGB", catalog["assets"][name]["size"])
                x, y, width, height = proof["rect"]
                outputs[name].paste(source.crop((x, y, x + width, y + height)), patch["source"][:2])
        for name, image in outputs.items():
            output = directory / name
            output.parent.mkdir(parents=True, exist_ok=True)
            encoded = io.BytesIO()
            image.save(encoded, format="PNG", optimize=True, compress_level=9)
            payload = encoded.getvalue()
            assert hashlib.sha256(payload).hexdigest() == catalog["assets"][name]["sha256"], name
            output.write_bytes(payload)
print("PASS: reproduced all 88 PNG variants from the fixed reference commit")
