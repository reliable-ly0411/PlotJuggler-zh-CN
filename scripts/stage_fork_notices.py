# SPDX-License-Identifier: MPL-2.0
"""Ship the source location and license texts beside every packaged executable."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

def stage_arrow_source(*args):
    # Delay helper loading until after argparse, keeping --help free of work.
    import importlib.util
    spec = importlib.util.spec_from_file_location("arrow_source_evidence", Path(__file__).with_name("arrow_source_evidence.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.stage(*args)

def query_dpkg_owner(path):
    """Resolve merged-/usr aliases and preserve architecture in package identity."""
    for candidate in dict.fromkeys((str(path), str(Path(path).resolve()))):
        result = subprocess.run(["dpkg-query", "-S", candidate], text=True, capture_output=True)
        if result.returncode == 0:
            owners = [line.split(": ", 1)[0] for line in result.stdout.splitlines()
                      if ": " in line and not line.startswith("diversion ")]
            if len(owners) == 1:
                return owners[0]
    return None


def query_dpkg_version(owner):
    """Reject ambiguous multi-architecture output rather than joining versions."""
    result = subprocess.run(["dpkg-query", "-W", "-f=${binary:Package}\t${Version}\n", owner],
                            text=True, capture_output=True)
    rows = [line.split("\t") for line in result.stdout.splitlines() if line]
    if result.returncode or len(rows) != 1 or len(rows[0]) != 2 or rows[0][0] != owner:
        return None
    return rows[0][1] or None


def stage_distro_notices(destination):
    # This is an observation of resolved build-host ELF dependencies, not a
    # package closure or a substitute for inspecting the final payload.
    libraries, unresolved, failures = set(), set(), []
    for binary in destination.iterdir():
        if not binary.is_file():
            continue
        with binary.open("rb") as stream:
            if stream.read(4) != b"\x7fELF":
                continue
        result = subprocess.run(["ldd", str(binary)], text=True, capture_output=True)
        if result.returncode:
            failures.append(binary.name)
        for line in result.stdout.splitlines():
            if "=> not found" in line:
                unresolved.add(line.split("=>", 1)[0].strip())
            match = re.search(r"(?:=>\s+|^\s*)(/[^\s]+)", line)
            if match:
                libraries.add(match.group(1))
    owners, unowned = set(), set()
    for library in sorted(libraries):
        owner = query_dpkg_owner(library)
        if owner:
            owners.add(owner)
        else:
            unowned.add(Path(library).name)
    distro = destination / "Licenses/Distro"
    distro.mkdir(parents=True, exist_ok=True)
    records = []
    for owner in sorted(owners):
        name = owner.split(":", 1)[0]
        source = Path("/usr/share/doc") / name / "copyright"
        version = query_dpkg_version(owner)
        record = {"package": owner, "version": version, "copyright": None}
        if source.is_file():
            target = distro / name / "copyright"
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            record["copyright"] = target.relative_to(distro).as_posix()
        records.append(record)
    common = Path("/usr/share/common-licenses")
    if common.is_dir():
        shutil.copytree(common, distro / "common-licenses", dirs_exist_ok=True)
    (distro / "manifest.json").write_text(json.dumps({
        "scope": "Build-host ELF dependencies observed by ldd; not final package closure",
        "status": "incomplete" if (unowned or unresolved or failures or not records or
                                   any(not r["version"] or not r["copyright"] for r in records)) else "observed",
        "packages": records, "unowned_library_names": sorted(unowned),
        "unresolved_library_names": sorted(unresolved), "ldd_failed_binaries": sorted(failures)
    }, indent=2), encoding="utf-8")


def read_cmake_cache(build_dir):
    cache = build_dir / "CMakeCache.txt"
    if not cache.is_file():
        return None
    entries = {}
    for line in cache.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith(("//", "#")) or "=" not in line or ":" not in line.split("=", 1)[0]:
            continue
        key, value = line.split("=", 1)
        key = key.rsplit(":", 1)[0]
        if key in entries:
            raise RuntimeError(f"Duplicate CMake cache key: {key}")
        entries[key] = value
    return entries


def resolve_downloaded_source(build_dir, dependency, cache):
    """Find configured source, or a legacy fallback; never guess a system source."""
    keys = (f"FETCHCONTENT_SOURCE_DIR_{dependency.upper()}",
            f"CPM_PACKAGE_{dependency}_SOURCE_DIR", f"{dependency}_SOURCE_DIR")
    found = []
    if cache is not None:
        for key in keys:
            value = cache.get(key, "")
            if not value or value.endswith("-NOTFOUND"):
                continue
            path = Path(value)
            if not path.is_absolute():
                raise RuntimeError(f"{dependency}: non-absolute configured source directory")
            found.append(path.resolve())
        if len(set(found)) > 1:
            raise RuntimeError(f"{dependency}: conflicting configured source directories")
        if found:
            if not found[0].is_dir():
                raise RuntimeError(f"{dependency}: configured source directory missing")
            return found[0], "configured"
    legacy = build_dir / "_deps" / f"{dependency}-src"
    packages = cache.get("CPM_PACKAGES", "").split(";") if cache is not None else []
    if legacy.is_dir() and (cache is None or dependency in packages):
        return legacy.resolve(), "legacy-fallback"
    if dependency in packages:
        raise RuntimeError(f"{dependency}: CPM package is recorded but its source directory is unavailable")
    if cache is None:
        return None, "incomplete"
    return None, "not-downloaded"


def configured_arrow_version(cache):
    """Read the literal CMake package version; no inference from system ldd."""
    if not cache:
        return None
    directory = cache.get("Arrow_DIR", "")
    if not directory or directory.endswith("-NOTFOUND"):
        return None
    directory = Path(directory)
    if not directory.is_absolute():
        raise RuntimeError("Arrow: configured package directory is not absolute")
    files = [directory / n for n in ("ArrowConfigVersion.cmake", "arrow-config-version.cmake") if (directory / n).is_file()]
    if not files:
        raise RuntimeError("Arrow: configured package version file missing")
    versions = set()
    for file in files:
        versions.update(re.findall(r'(?mi)^\s*set\s*\(\s*PACKAGE_VERSION\s+"([0-9]+\.[0-9]+\.[0-9]+)"\s*\)', file.read_text(encoding="utf-8")))
    if len(versions) != 1:
        raise RuntimeError("Arrow: configured package version ambiguous")
    return versions.pop()


def stage_downloaded_notice(root, destination, dependency, build_dir=None, cache=None):
    # root retained for callers of the original helper and its legacy tests.
    build_dir = Path(build_dir) if build_dir is not None else root / "build"
    if cache is None:
        cache = read_cmake_cache(build_dir)
    source, resolution = resolve_downloaded_source(build_dir, dependency, cache)
    record = {"dependency": dependency, "source_resolution": resolution,
              "status": "incomplete" if resolution != "not-downloaded" else "not-downloaded",
              "closure_status": "incomplete", "configured_version": None, "files": []}
    if cache:
        version = cache.get(f"CPM_PACKAGE_{dependency}_VERSION", "")
        # Untrusted cache values must not leak arbitrary paths into the manifest.
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.+_-]*", version):
            record["configured_version"] = version
    if dependency == "wasmer":
        recipe = root / "cmake/download_wasmer.cmake"
        if recipe.is_file():
            versions = re.findall(r'(?m)^\s*set\(WASMER_VERSION\s+"v([0-9]+\.[0-9]+\.[0-9]+)"\s*\)', recipe.read_text(encoding="utf-8"))
            if len(versions) == 1:
                record["recipe_declared_version"] = versions[0]
                record["version_correspondence"] = "unverified"
    if source is None:
        return record
    names = ["LICENSE"] + (["ATTRIBUTIONS"] if dependency == "wasmer" else [])
    for name in names:
        if not (source / name).is_file():
            raise RuntimeError(f"{dependency}: required {name} missing from downloaded source")
    target_dir = destination / "Licenses/Downloaded" / dependency
    target_dir.mkdir(parents=True, exist_ok=True)
    for name in names:
        target = target_dir / name
        shutil.copyfile(source / name, target)
        record["files"].append({"path": f"{dependency}/{name}",
                                "sha256": hashlib.sha256(target.read_bytes()).hexdigest()})
    record["status"] = "staged-unverified"
    return record


def validate_windows_runtime_materials(licenses, metadata_license):
    """Verify reviewed bytes; this does not establish license closure."""
    qt = licenses / "windows-runtime-notices"
    ifw = licenses / "ifw"

    def checked(path, expected):
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise RuntimeError(f"Missing or changed Windows notice: {path.name}")

    manifest_path = qt / "upstream-text-manifest.json"
    checked(manifest_path, "8a43392fb79228fc11278a06856c0dcc70c2fcdbb29a5c47f3eb0010f73793dd")
    checked(qt / "NOTICE.txt", "163c15b72a9b1ce6bdf39dda60093864a5f1d4e991367429b7207a61bb241507")
    checked(ifw / "NOTICE.txt", "a6cb6021b7babf75d0860a6a3d5325259ab1dded3365d087909eb549d6c8238f")
    ifw_sha = "0dbe024961f6ab5c52689cbd036c977975d0d0f6a67ff97762d96cb819dd5652"
    checked(ifw / "LICENSE.GPL3-EXCEPT", ifw_sha)
    checked(metadata_license, ifw_sha)
    if (ifw / "LICENSE.GPL3-EXCEPT").read_bytes() != metadata_license.read_bytes():
        raise RuntimeError("IFW payload and installer metadata licenses differ")
    records = json.loads(manifest_path.read_text(encoding="utf-8"))["files"]
    names = [record["file"] for record in records]
    if len(names) != 33 or len({name.casefold() for name in names}) != 33:
        raise RuntimeError("Invalid Windows notice inventory")
    for record in records:
        name = record["file"]
        if Path(name).name != name or "\\" in name:
            raise RuntimeError("Invalid Windows notice filename")
        checked(qt / name, record["sha256"])


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--build-dir", type=Path, default=root / "build")
    parser.add_argument("--arrow-source-version", choices=("21.0.0", "26.0.1"))
    parser.add_argument("--arrow-source-archive", type=Path)
    args = parser.parse_args()
    if args.arrow_source_archive and not args.arrow_source_version:
        parser.error("--arrow-source-archive requires --arrow-source-version")
    metadata_license = root / "installer/io.plotjuggler.application/meta/license_ifw.txt"
    if os.name == "nt":
        validate_windows_runtime_materials(root / "licenses", metadata_license)
    destination = args.destination.resolve()
    build_dir = args.build_dir.resolve()
    notices = destination / "Licenses" / "ArduPilot-DataFlash"
    notices.mkdir(parents=True, exist_ok=True)
    plugin = root / "plotjuggler_plugins/DataLoadAPBin"
    for name in ("LICENSE", "COPYING.GPL3", "UPSTREAM.md"):
        shutil.copyfile(plugin / name, notices / name)
    shutil.copyfile(root / "LICENSE.md", destination / "Licenses/PlotJuggler-MPL-2.0.txt")
    shutil.copyfile(root / "docs/zh-CN.md", destination / "README-zh-CN.md")
    shutil.copyfile(root / "docs/THIRD-PARTY-3X.md", destination / "Licenses/THIRD-PARTY-3X.md")
    shutil.copytree(root / "licenses/qt5", destination / "Licenses/Qt5", dirs_exist_ok=True)
    shutil.copyfile(build_dir / "plotjuggler_app/QT5-TRANSLATIONS.json",
                    destination / "Licenses/Qt5/QT5-TRANSLATIONS.json")
    conan_notices = build_dir / "dependency-notices/Conan"
    if os.name == "nt":
        if not (conan_notices / "manifest.json").is_file():
            raise SystemExit("Conan dependency license inventory is missing")
        shutil.copytree(conan_notices, destination / "Licenses/Conan", dirs_exist_ok=True)
        # Inventory integrity is evidence, not license closure.
        for component in ("windows-runtime-notices", "ifw"):
            shutil.copytree(root / "licenses" / component,
                            destination / "Licenses" / component, dirs_exist_ok=True)
        validate_windows_runtime_materials(destination / "Licenses", metadata_license)
    cache = read_cmake_cache(build_dir)
    downloaded = [stage_downloaded_notice(root, destination, dependency, build_dir, cache)
                  for dependency in ("data_tamer", "wasmer", "lz4", "zstd")]
    manifest = destination / "Licenses/Downloaded/manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({"closure_status": "incomplete", "dependencies": downloaded,
        "scope": "configured downloaded sources only; not a final package inventory"}, indent=2), encoding="utf-8")
    if sys.platform.startswith("linux"):
        stage_distro_notices(destination)
    configured_arrow = configured_arrow_version(cache) if sys.platform.startswith("linux") else None
    if args.arrow_source_version and configured_arrow and args.arrow_source_version != configured_arrow:
        raise RuntimeError("Arrow: requested source version differs from configured package version")
    arrow_version = args.arrow_source_version or configured_arrow
    if arrow_version:
        evidence = stage_arrow_source(arrow_version,
            destination / "Licenses/ArrowSource" / arrow_version, args.arrow_source_archive)
        if evidence["status"] == "missing":
            raise RuntimeError(f"Arrow {arrow_version}: pinned source texts missing")
        evidence["directory"] = arrow_version
        evidence["version_origin"] = "cmake-package-version" if configured_arrow else "explicit"
    else:
        evidence = {"status": "version-unresolved", "closure_status": "incomplete"}
    evidence_path = destination / "Licenses/ArrowSource/evidence.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    for source in (
        "3rdparty/qwt/COPYING", "3rdparty/Qt-Advanced-Docking/LICENSE",
        "3rdparty/color_widgets/COPYING", "3rdparty/QCodeEditor/LICENSE.MIT",
        "3rdparty/backward-cpp/LICENSE.txt", "3rdparty/date-3.0.4/LICENSE.txt",
        "3rdparty/sol2-3.5.0/LICENSE.txt", "plotjuggler_plugins/ToolboxFFT/3rdparty/KissFFT/COPYING",
    ):
        target = destination / "Licenses/Vendored" / source
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / source, target)
    version_file = build_dir / "FORK-VERSION.json"
    version_info = json.loads(version_file.read_text(encoding="utf-8"))
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    info = {
        **version_info,
        "commit": commit,
        "repository": "https://github.com/reliable-ly0411/PlotJuggler-zh-CN",
        "upstream": "https://github.com/PlotJuggler/PlotJuggler",
        "ardupilot_parser_commit": "3e2f9253adc2d41e17b2f0fec74f4b2487c42fb0",
        "dataflash_formats": ["BIN"],
    }
    (destination / "BUILD-INFO.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    print(json.dumps(info))

    # Qt IFW compares numeric components; its visible title carries the public SemVer.
    if (destination / "plotjuggler.exe").exists():
        config = root / "installer/config.xml"
        tree = ET.parse(config)
        tree.getroot().find("Title").text = "PlotJuggler zh-CN " + info["version"]
        tree.write(config, encoding="utf-8", xml_declaration=True)
        package = root / "installer/io.plotjuggler.application/meta/package.xml"
        tree = ET.parse(package)
        tree.getroot().find("DisplayName").text = "PlotJuggler zh-CN " + info["version"]
        tree.write(package, encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    main()
