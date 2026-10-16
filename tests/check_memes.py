# SPDX-License-Identifier: MPL-2.0
"""Validate resource manifests; optionally compare pixels with a fixed Git baseline."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import struct
import subprocess
import xml.etree.ElementTree as ET

parser = argparse.ArgumentParser()
parser.add_argument("--reference-rev")
parser.add_argument("--pixel-report")
parser.add_argument("--export-reference")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
directory = root / "plotjuggler_app/resources/memes"
catalog = json.loads((directory / "zh_CN.json").read_text(encoding="utf-8"))
assert catalog["schema"] == 2 and catalog["rendering"] == "lossless-native-variants"
images = catalog["images"]
assert [image["id"] for image in images] == list(range(106))
assert {p.name for p in directory.glob("meme_*.jpg")} == {f"meme_{i:02d}.jpg" for i in range(106)}
base_qrc = {f.text for f in ET.parse(root / "plotjuggler_app/resource.qrc").findall(".//file")}
localized_qrc = {f.text for f in ET.parse(root / "plotjuggler_app/localized_resources.qrc").findall(".//file")}
assert not any(f.startswith("resources/memes/zh_CN") for f in base_qrc)
assert {"resources/memes/" + f"meme_{i:02d}.jpg" for i in range(106)} <= base_qrc
assets = catalog["assets"]
assert {"resources/memes/zh_CN.json", *("resources/memes/" + name for name in assets)} == localized_qrc

def sha(data):
    return hashlib.sha256(data).hexdigest()

for name, meta in assets.items():
    assert name.startswith("zh_CN/") and ".." not in name and "\\" not in name
    path = directory / name
    data = path.read_bytes()
    assert len(data) == meta["bytes"] and sha(data) == meta["sha256"], name
    assert data.startswith(b"\x89PNG\r\n\x1a\n"), name
    assert list(struct.unpack(">II", data[16:24])) == meta["size"], name
    # New derived resources contain pixels only, with no EXIF/text/private metadata.
    pos = 8
    while pos < len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        kind = data[pos + 4:pos + 8]
        assert kind in {b"IHDR", b"IDAT", b"IEND", b"PLTE", b"tRNS"}, (name, kind)
        pos += length + 12
    assert pos == len(data)

count = full = overlay = unavailable = 0
used = set()
for image in images:
    original = directory / f"meme_{image['id']:02d}.jpg"
    assert sha(original.read_bytes()) == image["original_sha256"], original.name
    assert image["regions"] or image.get("note"), image["id"]
    for region in image["regions"]:
        assert region["source"].strip() and re.search(r"[\u4e00-\u9fff]", region["text"]), region
        x, y, w, h = region["rect"]
        assert 0 <= x < 100 and 0 <= y < 100 and w > 0 and h > 0 and x + w <= 100 and y + h <= 100
        count += 1
    variant = image.get("variant")
    if not variant:
        if image["regions"]:
            assert image["localization_status"] == "original-ai-unavailable"
            unavailable += 1
        continue
    ref = image["reference"]
    assert len(ref["rgba_sha256"]) == 64 and len(ref["sha256"]) == 64
    if "image" in variant:
        used.add(variant["image"])
        assert assets[variant["image"]]["rgba_sha256"] == ref["rgba_sha256"]
        assert assets[variant["image"]]["size"] == ref["size"]
        assert image["variant_review"]["reason"]
        full += 1
    else:
        assert variant["canvas"] == ref["size"]
        assert len(variant["patches"]) == len(ref["patches"]) > 0
        for patch, proof in zip(variant["patches"], ref["patches"]):
            used.add(patch["file"])
            sx, sy, w, h = patch["source"]
            x, y = patch["at"]
            aw, ah = assets[patch["file"]]["size"]
            cw, ch = variant["canvas"]
            assert min(sx, sy, x, y) >= 0 and min(w, h) > 0
            assert sx + w <= aw and sy + h <= ah and x + w <= cw and y + h <= ch
            assert [x, y, w, h] == proof["rect"]
        overlay += 1
assert used == set(assets)
assert full + overlay == 88 and unavailable == 10
assert {"zh_CN/" + p.relative_to(directory / "zh_CN").as_posix()
        for p in (directory / "zh_CN").rglob("*.png")} == set(assets)
assert sum(m["bytes"] for m in assets.values()) < 70_000_000

report = {"originals": 106, "translated": full + overlay, "overlays": overlay,
          "complete_images": full, "original_fallbacks": unavailable,
          "translation_regions": count, "asset_bytes": sum(m["bytes"] for m in assets.values())}
if args.reference_rev:
    from PIL import Image
    assert args.reference_rev == catalog["reference_commit"]
    def reference(path):
        return subprocess.check_output(["git", "show", args.reference_rev + ":" + path], cwd=root)
    def rgba_hash(im):
        return sha(im.convert("RGBA").tobytes())
    checked_patches = 0
    for image in images:
        relative = f"plotjuggler_app/resources/memes/meme_{image['id']:02d}.jpg"
        assert reference(relative) == (root / relative).read_bytes(), relative
        if not image.get("variant"):
            continue
        ref = image["reference"]
        old = reference("plotjuggler_app/resources/memes/" + ref["file"])
        assert sha(old) == ref["sha256"]
        if args.export_reference:
            dest = Path(args.export_reference) / ref["file"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(old)
        with Image.open(io.BytesIO(old)) as source:
            assert list(source.size) == ref["size"] and rgba_hash(source) == ref["rgba_sha256"]
            variant = image["variant"]
            if "image" in variant:
                with Image.open(directory / variant["image"]) as actual:
                    assert actual.convert("RGBA").tobytes() == source.convert("RGBA").tobytes()
            else:
                for patch, proof in zip(variant["patches"], ref["patches"]):
                    x, y, w, h = proof["rect"]
                    expected = source.crop((x, y, x + w, y + h)).convert("RGBA")
                    with Image.open(directory / patch["file"]) as atlas:
                        sx, sy, _, _ = patch["source"]
                        actual = atlas.crop((sx, sy, sx + w, sy + h)).convert("RGBA")
                        assert actual.tobytes() == expected.tobytes(), image["id"]
                        assert rgba_hash(actual) == proof["rgba_sha256"]
                    checked_patches += 1
    report.update(reference_commit=args.reference_rev, pixel_identical_crops=checked_patches,
                  english_bytes_identical=True, complete_images_pixel_identical=True)
if args.pixel_report:
    Path(args.pixel_report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.pixel_report).write_text(json.dumps(report, indent=2), encoding="utf-8")
print("PASS: " + json.dumps(report))
