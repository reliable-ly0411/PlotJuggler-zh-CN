# SPDX-License-Identifier: MPL-2.0
"""Check exhaustive splash translation metadata without an image dependency."""
import json
import hashlib
from pathlib import Path
import re
import xml.etree.ElementTree as ET
root = Path(__file__).resolve().parents[1]
directory = root / "plotjuggler_app/resources/memes"
catalog = json.loads((directory / "zh_CN.json").read_text(encoding="utf-8"))
assert catalog["schema"] == 1
assert catalog["rendering"] == "ai-localized-assets"
images = catalog["images"]
assert [image["id"] for image in images] == list(range(106))
assert {p.name for p in directory.glob("meme_*.jpg")} == {f"meme_{i:02d}.jpg" for i in range(106)}
resource_files = {entry.text for entry in ET.parse(root / "plotjuggler_app/resource.qrc").findall(".//file")}
assert {"resources/memes/" + f"meme_{i:02d}.jpg" for i in range(106)} <= resource_files
count = 0
assets = set()
unavailable = 0
for image in images:
    assert image["regions"] or image.get("note"), image["id"]
    original = directory / f"meme_{image['id']:02d}.jpg"
    assert hashlib.sha256(original.read_bytes()).hexdigest() == image["original_sha256"], original
    if image.get("localization_status") == "original-ai-unavailable":
        assert image["regions"] and not image.get("asset"), image["id"]
        assert image["generation_error"]["code"] in {"moderation_blocked", "network_error"}, image["id"]
        assert image["generation_error"]["attempts"] >= 2, image["id"]
        unavailable += 1
    elif image["regions"]:
        asset = image["asset"]
        assert asset == f"zh_CN/meme_{image['id']:02d}.png", asset
        assert "resources/memes/" + asset in resource_files, asset
        data = (directory / asset).read_bytes()
        assert data.startswith(b"\x89PNG\r\n\x1a\n"), asset
        assert hashlib.sha256(data).hexdigest() == image["asset_sha256"], asset
        assets.add(asset)
    else:
        assert "asset" not in image, image["id"]
    for region in image["regions"]:
        assert region["source"].strip() and re.search(r"[\u4e00-\u9fff]", region["text"]), region
        x, y, w, h = region["rect"]
        assert 0 <= x < 100 and 0 <= y < 100 and w > 0 and h > 0 and x + w <= 100 and y + h <= 100, region
        assert region["style"] in {"dark", "light", "card", "yellow", "red", "green"}
        count += 1
assert len(assets) + unavailable == 98
assert {"zh_CN/" + p.name for p in (directory / "zh_CN").glob("meme_*.png")} == assets
assert {p for p in resource_files if p.startswith("resources/memes/zh_CN/")} == {
    "resources/memes/" + asset for asset in assets
}
print(f"PASS: 106 intact originals; {len(assets)} AI-localized resources; {unavailable} documented original fallbacks; {count} translation regions; all SHA256 checks match")
