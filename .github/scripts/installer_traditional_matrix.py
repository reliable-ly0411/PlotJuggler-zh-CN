# SPDX-License-Identifier: MPL-2.0
"""Disposable real Windows IFW language-matrix controller; no install."""
import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path.cwd().resolve()
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
from verify_windows_installer_resources import stage_inputs, verify_pe_resources, run
import windows_installer_live as live

TRANSITIONS = (
    ("zh_CN", "en_US", "zh_TW", "zh_CN"),
    ("zh_CN", "zh_TW", "en_US", "zh_CN"),
)
INTRO = {
    "en_US": ("Welcome", "Welcome to the PlotJuggler 4 zh-CN Setup.", "Next", "Cancel"),
    "zh_CN": ("欢迎", "欢迎使用 PlotJuggler 4 zh-CN 安装向导。", "下一步", "取消"),
    "zh_TW": ("歡迎", "歡迎使用 PlotJuggler 4 zh-CN 安裝程式。", "下一步", "取消"),
}
CUSTOM = {
    "en_US": ("Choose Installation Directory", "Please select where PlotJuggler 4 will be installed:"),
    "zh_CN": ("选择安装目录", "请选择 PlotJuggler 4 的安装位置："),
    "zh_TW": ("選擇安裝目錄", "請選擇 PlotJuggler 4 的安裝位置："),
}


def replace(text, old, new, count=1):
    if text.count(old) != count:
        raise ValueError("Unexpected source anchor: " + repr(old[:90]))
    return text.replace(old, new)


def controller_source(text):
    text = replace(text, "stage > 2 ||", 'stage >= probe.languages.length || installer.value("UILanguage") !== probe.languages[stage] ||')
    text = replace(text, "stage === 2", "stage === probe.languages.length - 1", 2)
    text = replace(text, "stage >= 2", "stage >= probe.languages.length - 1")
    text = replace(text, '''    record("before-switch", {});
    var page = gui.pageWidgetByObjectName("DynamicLanguageWidget");
    page.language.currentIndex = stage === 0 ? 1 : 0;''', '''    var page = gui.pageWidgetByObjectName("DynamicLanguageWidget");
    var names = {"zh_CN": 0, "en_US": 1, "zh_TW": 2};
    if (page.language.count !== 3 || page.language.currentIndex !== names[probe.languages[stage]]) {
        record("unexpected-languages", {});
        gui.rejectWithoutPrompt();
        return;
    }
    var source = page.language.currentIndex;
    var successor = probe.languages[stage + 1];
    page.language.currentIndex = names[successor];
    record("before-switch", {sourceIndex: source, selectedIndex: page.language.currentIndex, successor: successor});''')
    return text


def validator(chain, evidence):
    def check(records, fixture, controller, targets):
        order = ["introduction", "component-metadata", "target-before-edit", "target-edited", "before-switch"]
        if [r["kind"] for r in records] != order * (len(chain) - 1) + ["introduction", "component-metadata", "finished"]:
            raise AssertionError("Unexpected real wizard sequence")
        intros = [r for r in records if r["kind"] == "introduction"]
        metadata = [r for r in records if r["kind"] == "component-metadata"]
        custom = [r for r in records if r["kind"] == "target-before-edit"]
        changes = [r for r in records if r["kind"] == "target-edited"]
        switches = [r for r in records if r["kind"] == "before-switch"]
        index = {"zh_CN": 0, "en_US": 1, "zh_TW": 2}
        if len({r["pid"] for r in intros}) != len(chain):
            raise AssertionError("Insufficient distinct real installer processes")
        cache = Path(controller).parent / "tmp" / "ifw-cache"
        scope = live.fixture_overrides(controller)
        rows = []
        same = live.normalized
        for i, (language, row, component) in enumerate(zip(chain, intros, metadata)):
            target = same(targets[i])
            if row["language"] != language or same(row["target"]) != target:
                raise AssertionError("Restart language or TargetDir not preserved")
            if same(Path(row["executable"]).resolve()) != same(Path(fixture).resolve()):
                raise AssertionError("Observer does not belong to exact fixture")
            if row["liveFixturePids"] != [row["pid"]]:
                raise AssertionError("Another fixture process still alive")
            argv = live.windows_argv(row["commandLine"])
            for flag, val, normalize in (
                ("--lang", language, str), ("--cache-path", cache, same),
                ("--script", controller, same), ("--root", targets[i], same),
            ):
                if argv.count(flag) != 1 or normalize(argv[argv.index(flag)+1]) != normalize(val):
                    raise AssertionError("Restart flag not preserved: " + flag)
            dirs = [same(a.split("=", 1)[1]) for a in argv if a.startswith("TargetDir=")]
            if dirs != [target] or argv.count("PJProbeMarker=中文 space user@example.test") != 1:
                raise AssertionError("TargetDir or exact Unicode marker not preserved")
            for name, field in (("DesktopDir", "desktopDir"), ("StartMenuDir", "startMenuDir"), ("ProductUUID", "productUUID")):
                if row[field] != scope[name] or argv.count(name + "=" + scope[name]) != 1:
                    raise AssertionError("Synthetic scope override not preserved: " + name)
            if any(same(row[key]) != same(cache.parent) for key in ("TEMP", "TMP")):
                raise AssertionError("Fixture temp scope not preserved")
            title, message, nxt, cancel = INTRO[language]
            for field, actual, expected in (
                ("title", row["title"], title), ("message", row["message"], message),
                ("next", row["nextButton"], nxt), ("cancel", row["cancelButton"], cancel),
            ):
                correct = actual == expected if field == "message" else expected in actual
                if not correct:
                    raise AssertionError(f"{language} real wizard {field}: {actual!r}, expected {expected!r}")
            if (component["pid"], component["language"], same(component["target"])) != (row["pid"], language, target):
                raise AssertionError("Metadata came from wrong fixture process")
            if not component["componentName"] or not component["componentDescription"]:
                raise AssertionError("Real component metadata empty")
            detail = {x: row[x] for x in ("language", "title", "message", "nextButton", "cancelButton")}
            detail.update({x: component[x] for x in ("componentName", "componentDescription")})
            if i < len(chain)-1:
                page = custom[i]
                next_target = same(targets[i+1])
                if (page["title"], page["description"]) != CUSTOM[language] or same(page["field"]) != target:
                    raise AssertionError("Localized custom target widget or restored field mismatch")
                if same(changes[i]["field"]) != next_target or same(changes[i]["target"]) != next_target:
                    raise AssertionError("Actual edited target field did not transfer")
                expected_next = chain[i+1]
                if (switches[i]["sourceIndex"], switches[i]["selectedIndex"], switches[i]["successor"]) != (
                    index[language], index[expected_next], expected_next
                ) or same(switches[i]["target"]) != next_target:
                    raise AssertionError("Real selector transition mismatch")
                detail.update(customTitle=page["title"], customDescription=page["description"], successor=expected_next)
            rows.append(detail)
        evidence.write_text(json.dumps({"chain": chain, "observations": rows}, ensure_ascii=True, indent=2), encoding="utf-8")
        print("VERIFIED REAL IFW DIRECTION CHAIN:", " -> ".join(chain))
    return check


def windows_matrix(fixture, root, shell, evidence):
    text = (SCRIPTS / "windows_installer_live.qs.in").read_text(encoding="utf-8")
    template = root / "paired controller.qs.in"
    template.write_text(controller_source(text), encoding="utf-8")
    # Reuse exact production observer harness's lifecycle, forced cleanup on
    # failure only, PID and metadata cache checks. Make sequence configurable.
    original = (SCRIPTS / "windows_installer_live.py").read_text(encoding="utf-8")
    suffix = "def probe_gui(fixture, temporary, powershell, template):"
    if original.count(suffix) != 1:
        raise ValueError("Unknown base observer signature")
    original = original[original.index(suffix):]
    old_targets = '''    targets = [temporary / 'unused initial target', temporary / 'edited target 中文 one',
               temporary / "edited target 中文 two's"]'''
    new_targets = '''    targets = [temporary / f"unused target 中文 {i}'s" for i in range(len(chain))]'''
    derived = replace(original, old_targets, new_targets)
    derived = replace(derived, "changedTargets=list(map(str, targets[1:])))", "changedTargets=list(map(str, targets[1:])), languages=list(chain))")
    derived = replace(derived, "while time.monotonic() - started < 100:", "while time.monotonic() - started < 180:")
    derived = replace(derived, "did not finish within 100 seconds", "did not finish within 180 seconds")
    derived = replace(derived, "preserved in all three processes.", "preserved in all observed processes.")
    evidence.mkdir(parents=True, exist_ok=True)
    for i, chain in enumerate(TRANSITIONS):
        case = root / f"chain {i}"
        case.mkdir()
        matrix_fixture = case / fixture.name
        shutil.copy2(fixture, matrix_fixture)
        scope = dict(vars(live))
        scope.update(chain=chain, validate_records=validator(chain, evidence / f"chain-{i}.json"))
        exec(compile(derived, "ifw_matrix_probe.py", "exec"), scope)
        scope["probe_gui"](matrix_fixture, case, shell, template)
    seen = {(a,b) for chain in TRANSITIONS for a,b in zip(chain, chain[1:])}
    if seen != {(a,b) for a in INTRO for b in INTRO if a != b}:
        raise AssertionError("Directed matrix not complete")
    print("PASS: 6/6 real directed IFW language switches, actual process, custom target and standard wizard controls.")


def main(qtbin, evidence):
    if sys.platform != "win32":
        raise RuntimeError("Requires real Windows; do not emulate")
    shell = shutil.which("pwsh")
    if not shell:
        raise RuntimeError("PowerShell required")
    qtbin, evidence = Path(qtbin).resolve(strict=True), Path(evidence).resolve()
    with tempfile.TemporaryDirectory(prefix="pj separated IFW fixture ") as directory:
        stage = Path(directory)
        tools = stage / "IFW tools"
        run([shell, "-NoProfile", "-NonInteractive", "-File", ROOT / "packaging/installer/install_ifw.ps1", "-Destination", tools])
        version = run([tools / "bin/installerbase.exe", "--version"])
        if "IFW Version: 4.10.0, built with Qt " not in version:
            raise RuntimeError("Wrong IFW")
        config, packages, meta, translations, qrc = stage_inputs(ROOT, stage)
        run([qtbin / "lrelease.exe", ROOT / "packaging/installer/translations/ifw_zh_CN.ts", meta / "zh_CN.ts", "-qm", translations / "ifw_zh_CN.qm"])
        shutil.copy2(qtbin.parent / "translations/qtbase_zh_CN.qm", translations / "qt_zh_CN.qm")
        run([shell, "-NoProfile", "-NonInteractive", "-File", ROOT / "packaging/installer/prepare_traditional_stage.ps1",
             "-QtBin", qtbin, "-StageDir", stage], cwd=stage)
        fixture = stage / "SYNTHETIC-DO-NOT-INSTALL.exe"
        run([tools / "bin/binarycreator.exe", "--offline-only", "-r", qrc, "-c", config, "-p", packages, fixture], cwd=stage)
        verify_pe_resources(fixture)
        for name in ("ifw_zh_TW.qm","qt_zh_TW.qm"):
            if name.encode("utf-16-be") not in fixture.read_bytes():
                raise RuntimeError("Traditional resource not embedded: " + name)
        windows_matrix(fixture, stage, shell, evidence)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--qt-bin", required=True)
    parser.add_argument("--evidence", required=True)
    args = parser.parse_args()
    main(args.qt_bin, args.evidence)
