# SPDX-License-Identifier: MPL-2.0
"""Read-only released ZIP/AppImage/DEB inventory; never execute downloaded binaries."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import urllib.request
import zipfile
from package_metadata import package_metadata

p = argparse.ArgumentParser()
p.add_argument("--manifest", required=True)
p.add_argument("--out", required=True)
a = p.parse_args()
baseline = json.loads(Path(a.manifest).read_text(encoding="utf-8"))
results = []
with tempfile.TemporaryDirectory() as temp:
    work = Path(temp)
    for release in baseline:
        if release["tag"] not in {"v3.18.0-zh.2", "v3.18.0-zh.3"}:
            continue
        for asset in release["assets"]:
            name = asset["name"]
            if not name.endswith(("Windows-x64.zip", "x86_64.AppImage", "24.04-amd64.deb")):
                continue
            archive = work / name
            print("Downloading", name, flush=True)
            with urllib.request.urlopen(asset["url"], timeout=180) as response, archive.open("wb") as out:
                shutil.copyfileobj(response, out)
            assert archive.stat().st_size == asset["bytes"]
            assert hashlib.file_digest(archive.open("rb"), "sha256").hexdigest() == asset["sha256"]
            container = package_metadata(archive)
            members = []
            payload = work / "payload"
            if name.endswith(".zip"):
                with zipfile.ZipFile(archive) as z:
                    for m in z.infolist():
                        if not m.is_dir():
                            members.append({"path": m.filename, "bytes": m.file_size,
                                            "compressed_bytes": m.compress_size})
            else:
                payload.mkdir()
                if name.endswith(".deb"):
                    subprocess.run(["dpkg-deb", "-x", str(archive), str(payload)], check=True)
                else:
                    data = archive.read_bytes()
                    offset = 0
                    while True:
                        offset = data.find(b"hsqs", offset)
                        assert offset >= 0, "SquashFS superblock missing"
                        if (offset + 96 <= len(data) and struct.unpack_from("<H", data, offset + 28)[0] == 4
                                and 96 < struct.unpack_from("<Q", data, offset + 40)[0] <= len(data) - offset):
                            break
                        offset += 4
                    subprocess.run(["unsquashfs", "-no-progress", "-o", str(offset), "-d", str(payload),
                                    str(archive)], check=True, stdout=subprocess.DEVNULL)
                for file in sorted(payload.rglob("*")):
                    if file.is_file() and not file.is_symlink():
                        members.append({"path": file.relative_to(payload).as_posix(), "bytes": file.stat().st_size})
                shutil.rmtree(payload)
            results.append({"tag": release["tag"], "name": name, "package_bytes": asset["bytes"],
                            "container": container,
                            "sha256": asset["sha256"], "payload_bytes": sum(m["bytes"] for m in members),
                            "main_executable_bytes": sum(m["bytes"] for m in members if Path(m["path"]).name in {"plotjuggler", "plotjuggler.exe"}),
                            "test_executable_bytes": sum(m["bytes"] for m in members if Path(m["path"]).name.startswith("pj_") and "_test" in m["path"]),
                            "files": members})
            archive.unlink()
out = Path(a.out)
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(results, indent=2), encoding="utf-8")
print(json.dumps([{k: v for k, v in r.items() if k != "files"} for r in results], indent=2))
