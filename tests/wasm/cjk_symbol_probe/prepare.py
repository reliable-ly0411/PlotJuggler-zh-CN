# SPDX-License-Identifier: MPL-2.0
import json
import shutil
import sys
from pathlib import Path
import xml.etree.ElementTree as ET
repo = Path(__file__).resolve().parents[3]
if len(sys.argv) != 2:
    raise SystemExit("Usage: prepare.py OUTPUT_DIRECTORY")
dest = Path(sys.argv[1]).resolve()
dest.mkdir(parents=True, exist_ok=True)
for name in ("CMakeLists.txt", "main.cpp"):
    shutil.copyfile(Path(__file__).with_name(name), dest / name)
for f in ("BundledFont.cpp", "BundledFont.h"):
    shutil.copyfile(repo / "pj_app/src" / f, dest / f)
# The WASM resources come from the exact production qrc and binary blobs.
shutil.copytree(repo / "resources/fonts/NotoSansSC", dest / "NotoSansSC", dirs_exist_ok=True)
shutil.copytree(repo / "resources/fonts/NotoSansSymbols2", dest / "NotoSansSymbols2", dirs_exist_ok=True)
faces = ("PlotJugglerSans-Regular.ttf", "PlotJugglerSans-Bold.ttf")
for f in faces:
    shutil.copyfile(repo / "resources/fonts/PlotJugglerSans" / f, dest / f)
(dest / "primary.qrc").write_text('<RCC><qresource prefix="/resources/fonts/PlotJugglerSans">' +
    ''.join(f"<file>{f}</file>" for f in faces) + '</qresource></RCC>')
s = (repo / "pj_app/src/main.cpp").read_text()
start = s.index("  if (const QString family = PJ::registerBundledFont(")
end = s.index("\n#else", start)
setup = s[start:end]
assert setup.count("QFontDatabase::addApplicationFont") == 2 and setup.count("#ifdef PJ_TARGET_WASM") == 1
(dest / "setup.inc").write_text(setup.replace("\n#ifdef PJ_TARGET_WASM", ""))
samples = []
for lang in ("zh_CN", "zh_TW"):
    r = ET.parse(repo / f"pj_app/translations/plotjuggler4_{lang}.ts").getroot()
    m = [n.findtext("translation") for c in r.findall("context") if c.findtext("name") == "MarketplaceWindow"
         for n in c.findall("message") if n.findtext("source") == "Plugin settings — open Preferences ▸ Plugins"]
    assert len(m) == 1 and m[0].count("▸") == 1 and "Preferences" not in m[0], (lang, m)
    samples.append(f'{{QStringLiteral("{lang}"), QStringLiteral({json.dumps(m[0], ensure_ascii=False)})}}')
(dest / "samples.inc").write_text(",\n".join(samples))
