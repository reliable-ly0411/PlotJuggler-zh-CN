# SPDX-License-Identifier: MPL-2.0
"""Ship the source location and license texts beside every packaged executable."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[1]
destination = Path(sys.argv[1]).resolve()
notices = destination / "Licenses" / "ArduPilot-DataFlash"
notices.mkdir(parents=True, exist_ok=True)
plugin = root / "plotjuggler_plugins/DataLoadAPBin"
for name in ("LICENSE", "COPYING.GPL3", "UPSTREAM.md"):
    shutil.copyfile(plugin / name, notices / name)
shutil.copyfile(root / "LICENSE.md", destination / "Licenses/PlotJuggler-MPL-2.0.txt")
shutil.copyfile(root / "docs/zh-CN.md", destination / "README-zh-CN.md")
shutil.copyfile(root / "docs/THIRD-PARTY-3X.md", destination / "Licenses/THIRD-PARTY-3X.md")
shutil.copytree(root / "licenses/qt5", destination / "Licenses/Qt5", dirs_exist_ok=True)
shutil.copyfile(root / "build/plotjuggler_app/QT5-TRANSLATIONS.json",
                destination / "Licenses/Qt5/QT5-TRANSLATIONS.json")
conan_notices = root / "build/dependency-notices/Conan"
if os.name == "nt":
    if not (conan_notices / "manifest.json").is_file():
        raise SystemExit("Conan dependency license inventory is missing")
    shutil.copytree(conan_notices, destination / "Licenses/Conan", dirs_exist_ok=True)
for dependency in ("data_tamer", "wasmer"):
    source = root / f"build/_deps/{dependency}-src/LICENSE"
    if source.is_file():
        target = destination / "Licenses/Downloaded" / dependency / "LICENSE"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
if sys.platform.startswith("linux"):
    # Preserve distro copyright notices for the resolved runtime dependency tree.
    # This records build dependencies, not a claim that all are bundled in DEBs.
    libraries = set()
    for binary in destination.iterdir():
        if not binary.is_file():
            continue
        with binary.open("rb") as stream:
            if stream.read(4) != b"\x7fELF":
                continue
        result = subprocess.run(["ldd", str(binary)], text=True, capture_output=True)
        libraries.update(re.findall(r"(?:=>\s+|^\s*)(/[^\s]+)", result.stdout, re.M))
    owners = set()
    for library in sorted(libraries):
        result = subprocess.run(["dpkg-query", "-S", library], text=True, capture_output=True)
        if result.returncode == 0:
            owners.update(line.split(": ", 1)[0] for line in result.stdout.splitlines()
                          if ": " in line and not line.startswith("diversion "))
    distro_notices = destination / "Licenses/Distro"
    distro_notices.mkdir(parents=True, exist_ok=True)
    records = []
    for owner in sorted(owners):
        name = owner.split(":", 1)[0]
        source = Path("/usr/share/doc") / name / "copyright"
        if source.is_file():
            target = distro_notices / name / "copyright"
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            version = subprocess.check_output(
                ["dpkg-query", "-W", "-f=${Version}", owner], text=True).strip()
            records.append({"package": owner, "version": version,
                            "copyright": target.relative_to(distro_notices).as_posix()})
    common = Path("/usr/share/common-licenses")
    if common.is_dir():
        shutil.copytree(common, distro_notices / "common-licenses", dirs_exist_ok=True)
    (distro_notices / "manifest.json").write_text(
        json.dumps({"scope": "Resolved runtime dependency notices; DEBs use system dependencies",
                    "packages": records}, indent=2), encoding="utf-8")
for source in (
    "3rdparty/qwt/COPYING", "3rdparty/Qt-Advanced-Docking/LICENSE",
    "3rdparty/color_widgets/COPYING", "3rdparty/QCodeEditor/LICENSE.MIT",
    "3rdparty/backward-cpp/LICENSE.txt", "3rdparty/date-3.0.4/LICENSE.txt",
    "3rdparty/sol2-3.5.0/LICENSE.txt", "plotjuggler_plugins/ToolboxFFT/3rdparty/KissFFT/COPYING",
):
    target = destination / "Licenses/Vendored" / source
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(root / source, target)
version_file = root / "build/FORK-VERSION.json"
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
