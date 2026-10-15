# SPDX-License-Identifier: MPL-2.0
"""Ship the source location and license texts beside every packaged executable."""
import json
from pathlib import Path
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
