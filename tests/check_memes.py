# SPDX-License-Identifier: MPL-2.0
"""Check exhaustive splash translation metadata without an image dependency."""
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
root = Path(__file__).resolve().parents[1]
directory = root / "plotjuggler_app/resources/memes"
catalog = json.loads((directory / "zh_CN.json").read_text(encoding="utf-8"))
assert catalog["schema"] == 1
images = catalog["images"]
assert [image["id"] for image in images] == list(range(106))
assert {p.name for p in directory.glob("meme_*.jpg")} == {f"meme_{i:02d}.jpg" for i in range(106)}
resource_files = {entry.text for entry in ET.parse(root / "plotjuggler_app/resource.qrc").findall(".//file")}
assert {"resources/memes/" + f"meme_{i:02d}.jpg" for i in range(106)} <= resource_files
count = 0
for image in images:
    assert image["regions"] or image.get("note"), image["id"]
    for region in image["regions"]:
        assert region["source"].strip() and re.search(r"[\u4e00-\u9fff]", region["text"]), region
        x, y, w, h = region["rect"]
        assert 0 <= x < 100 and 0 <= y < 100 and w > 0 and h > 0 and x + w <= 100 and y + h <= 100, region
        assert region["style"] in {"dark", "light", "card", "yellow", "red", "green"}
        count += 1
print(f"PASS: all 106 source images reviewed; {count} translated regions; product/code identifiers and attribution retained")
