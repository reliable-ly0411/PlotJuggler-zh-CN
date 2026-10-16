# SPDX-License-Identifier: MPL-2.0
"""Collect exactly seven audited software files. Never create a tag or release."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

SUFFIXES = ("Windows-x64.zip", "Windows-x64.exe", "x86_64.AppImage", "aarch64.AppImage",
            "24.04-amd64.deb", "bookworm-amd64.deb", "trixie-amd64.deb")


def expected_files(source):
    if not re.fullmatch(r"[0-9a-f]{40}", source):
        raise ValueError("A full source commit is required")
    version = "3.18.0-zh.4+upstream.3.17.2.apbin.1.g" + source[:12]
    return version, {"PlotJuggler-" + version + "-" + suffix for suffix in SUFFIXES}


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def inventory(directory, source):
    version, expected = expected_files(source)
    files = {}
    for path in Path(directory).rglob("*"):
        if path.is_symlink():
            raise ValueError("Symlinks are not release assets")
        if path.is_file():
            if path.name not in expected or path.name in files:
                raise ValueError("Unexpected or duplicate release attachment: " + path.name)
            files[path.name] = path
    if set(files) != expected:
        raise ValueError("Exactly seven software assets are required")
    return version, files


def collect(software, metadata, source, output, report):
    version, files = inventory(software, source)
    identities = []
    reports = list(Path(metadata).rglob("package-size.json"))
    if len(reports) != 6:
        raise ValueError("Six platform audit reports are required")
    for path in reports:
        audit = json.loads(path.read_text(encoding="utf-8"))
        if (audit["privacy_scan"] != "passed" or not audit["test_executables_absent"]
                or audit["build_info"]["commit"] != source or audit["build_info"]["version"] != version):
            raise ValueError("Package audit or source identity failed")
        for package in audit["packages"]:
            name = package["name"]
            if name not in files or any(item["name"] == name for item in identities):
                raise ValueError("Unrecognized or duplicate audited package")
            if files[name].stat().st_size != package["bytes"] or digest(files[name]) != package["sha256"]:
                raise ValueError("Software differs from its successful package audit")
            arch = audit["build_arch"].casefold()
            if "aarch64.AppImage" in name:
                if arch not in ("aarch64", "arm64"):
                    raise ValueError("ARM package was not built on ARM")
            elif arch not in ("amd64", "x86_64"):
                raise ValueError("x64 package was not built on x64")
            if name.endswith(".deb"):
                os_info = {key: value.strip('"') for key, value in audit["build_os"].items()}
                distro = name.rsplit("-", 2)[-2]
                codename = "noble" if distro == "24.04" else distro
                if os_info["VERSION_CODENAME"] != codename:
                    raise ValueError("DEB distribution does not match its actual builder")
            identities.append(package)
    if {item["name"] for item in identities} != set(files):
        raise ValueError("Every software file must have a passing audit")
    output, report = Path(output), Path(report)
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise ValueError("Release staging directory must be empty")
    for name, path in files.items():
        shutil.copyfile(path, output / name)
    report.mkdir(parents=True, exist_ok=True)
    result = {"tag": "v3.18.0-zh.4", "version": version, "source_commit": source,
              "software_assets": sorted(identities, key=lambda item: item["name"]),
              "asset_count": 7, "process_attachments": 0, "published": False}
    (report / "seven-packages.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    notes = f"""PlotJuggler 简体中文 v3.18.0-zh.4

Source: `{source}`; upstream baseline: PlotJuggler 3.17.2.

- Simplified Chinese UI with English switching and bundled ArduPilot DataFlash BIN loader.
- 88 localized startup images: 71 lossless overlays and 17 complete images. 10 untranslated fallbacks and 8 technical originals remain.
- Seven software assets: Windows x64 ZIP/installer, x86_64/aarch64 AppImages, Ubuntu 24.04 and Debian bookworm/trixie amd64 DEBs.
- Smaller localized image resources. Measured timings and limitations, including the English first-render regression, are in docs/zh4-performance.md. No universal startup-speed improvement is claimed.
- Original copyright and MPL-2.0 notices retained; the DataFlash plugin retains its LGPL-3.0 notices. DataFlash text logs are not supported by this loader.

Checksums:
"""
    notes += "\n".join(f"- `{item['sha256']}`  `{item['name']}`" for item in result["software_assets"]) + "\n"
    (report / "notes.md").write_text(notes, encoding="utf-8")
    return result


def verify_upload(manifest, release):
    expected = {item["name"]: item for item in manifest["software_assets"]}
    assets = release["assets"]
    if len(assets) != 7 or {item["name"] for item in assets} != set(expected):
        raise ValueError("Release must contain only the seven software files")
    if release["tag_name"] != manifest["tag"] or not release["draft"]:
        raise ValueError("Verify the exact draft before publication")
    for item in assets:
        wanted = expected[item["name"]]
        if item["size"] != wanted["bytes"] or item.get("digest") != "sha256:" + wanted["sha256"]:
            raise ValueError("Uploaded software identity mismatch")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("collect")
    for option in ("software", "metadata", "source", "output", "report"):
        command.add_argument("--" + option, required=True)
    command = commands.add_parser("verify-upload")
    command.add_argument("--manifest", required=True)
    command.add_argument("--release", required=True)
    args = parser.parse_args()
    if args.command == "collect":
        result = collect(args.software, args.metadata, args.source, args.output, args.report)
        print(json.dumps({key: value for key, value in result.items() if key != "software_assets"}, indent=2))
    else:
        verify_upload(json.loads(Path(args.manifest).read_text()), json.loads(Path(args.release).read_text()))
        print("PASS: exactly seven uploaded software identities; no process attachments")
