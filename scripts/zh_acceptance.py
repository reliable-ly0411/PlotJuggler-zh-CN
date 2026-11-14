# SPDX-License-Identifier: MPL-2.0
"""Capture independent Qt5 acceptance stages and report every required failure."""
import argparse
import configparser
import hashlib
import json
from pathlib import Path
import subprocess

LANGUAGES = ("zh_CN", "zh_TW", "en_US")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", required=True)
    parser.add_argument("--plugin", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--window-size", default="1100x700")
    parser.add_argument("--version-file", help="Build FORK-VERSION.json containing the expected version")
    parser.add_argument("--ui-only", action="store_true",
                        help="Run UI and restart stages only; do not export images")
    parser.add_argument("--original-images", action="store_true",
                        help="Expect a build with localized image resources disabled")
    return parser.parse_args(argv)


def validate_ui(report, language, version):
    if not isinstance(report, dict):
        return ["invalid-ui-report-type"]
    errors = []
    gates = {
        "version": version is not None and report.get("version") == version,
        "language": report.get("language") == language and report.get("language_ok"),
        "menu": report.get("menu_ok"),
        "screenshot": report.get("screenshot_ok"),
        "data": report.get("data_ok") and isinstance(report.get("numeric_series"), int)
                and report["numeric_series"] >= 4,
        "localization": isinstance(report.get("localization"), dict)
                        and report["localization"].get("ok"),
        "regression": isinstance(report.get("regression"), dict)
                      and report["regression"].get("ok"),
    }
    for name, passed in gates.items():
        if not passed:
            errors.append(name + "-gate-failed")
    return errors


def validate_memes(report, language, localized_count):
    if not isinstance(report, list):
        return ["invalid-meme-report-type"]
    errors = []
    if len(report) != 107:
        errors.append("meme-count-gate-failed")
    if not all(isinstance(item, dict) and item.get("text_fits") and item.get("saved")
               and item.get("english_original") for item in report):
        errors.append("meme-rendering-gates-failed")
    count = sum(isinstance(item, dict) and item.get("rendering") in
                ("localized-overlay", "localized-full-image") for item in report)
    if localized_count is None or count != (localized_count if language == "zh_CN" else 0):
        errors.append("localized-image-count-gate-failed")
    return errors


def settings_file(out):
    return out / "settings/PlotJuggler/io.plotjuggler.PlotJuggler.zh-CN.ini"


def settings_signature(path):
    try:
        return (path.stat().st_mtime_ns, hashlib.sha256(path.read_bytes()).hexdigest())
    except OSError:
        return None


def restart_dependency(out, language, before):
    """Do not let a missing/stale config pass by falling back to default Chinese."""
    path = settings_file(out)
    after = settings_signature(path)
    if after is None:
        return "settings-file-missing"
    if after == before:
        return "settings-not-refreshed-by-ui-stage"
    try:
        config = configparser.ConfigParser(interpolation=None)
        config.read_string(path.read_text(encoding="utf-8-sig"))
        value = config.get("General", "Preferences%3A%3Alanguage", fallback=None)
    except (OSError, UnicodeError, configparser.Error):
        return "settings-unreadable-or-invalid"
    if value != language:
        return "saved-language-preference-mismatch"
    return None


def _output_bytes(value):
    return value.encode("utf-8", errors="replace") if isinstance(value, str) else value or b""


def run_stage(language, name, command, report_path, log_path, validator, output, runner):
    stage = {"language": language, "stage": name, "status": "failed", "reasons": [],
             "report": report_path.relative_to(output).as_posix(),
             "log": log_path.relative_to(output).as_posix()}
    errors = stage["reasons"]
    stdout = b""
    try:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        # A previous run's report cannot prove this subprocess succeeded.
        report_path.unlink(missing_ok=True)
        result = runner(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
        stdout = _output_bytes(result.stdout)
        stage["exit_code"] = result.returncode
        if result.returncode:
            errors.append("process-nonzero")
    except subprocess.TimeoutExpired as error:
        stdout = _output_bytes(error.output)
        errors.append("process-timeout")
    except Exception:
        # Record stable rule names, not arbitrary exception/credential contents.
        errors.append("process-or-output-error")
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_bytes(stdout)
    except OSError:
        errors.append("process-log-write-failed")
    report = None
    try:
        report = json.loads(report_path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        errors.append("report-missing")
    except (OSError, UnicodeError, ValueError):
        errors.append("report-invalid-or-unreadable")
    else:
        try:
            errors.extend(validator(report))
        except Exception:
            errors.append("report-validation-error")
    if not errors:
        stage["status"] = "passed"
    # Invalid/failed report bodies stay in their original file, never in a
    # synthesized error message or summary (which might disclose arbitrary data).
    return stage, report if not errors else None


def run_acceptance(args, *, root=None, runner=None):
    root = Path(root) if root is not None else Path(__file__).resolve().parents[1]
    runner = subprocess.run if runner is None else runner
    app, plugin, output = Path(args.app).resolve(), Path(args.plugin).resolve(), Path(args.out).resolve()
    output.mkdir(parents=True, exist_ok=True)
    launcher = ["--launch"] if app.suffix == ".AppImage" else []
    fixture = root / "plotjuggler_plugins/DataLoadAPBin/tests/curves.BIN"
    preflight = {"status": "passed", "reasons": []}
    for path, reason in ((app, "application-missing"), (plugin, "plugin-missing"),
                         (fixture, "synthetic-fixture-missing")):
        if not path.is_file():
            preflight["reasons"].append(reason)
    version, localized_count = None, None
    try:
        version_file = Path(args.version_file) if args.version_file else root / "build/FORK-VERSION.json"
        version = json.loads(version_file.read_text(encoding="utf-8"))["version"]
        if not isinstance(version, str) or not version:
            raise ValueError
    except (OSError, UnicodeError, ValueError, KeyError, TypeError):
        preflight["reasons"].append("expected-version-unavailable")
        version = None
    if not args.ui_only:
        try:
            catalog = json.loads((root / "plotjuggler_app/resources/memes/zh_CN.json").read_text(encoding="utf-8"))
            localized_count = sum(bool(item.get("variant")) for item in catalog["images"])
            if args.original_images:
                localized_count = 0
        except (OSError, UnicodeError, ValueError, KeyError, TypeError, AttributeError):
            preflight["reasons"].append("image-catalog-unavailable")
    if preflight["reasons"]:
        preflight["status"] = "failed"
    stages, reports = [], []
    for language in LANGUAGES:
        out = output / language
        before = settings_signature(settings_file(out))
        command = [str(app), *launcher, "-n", "--disable_opengl", "--self-test-ui", str(out),
                   "--self-test-size", args.window_size, "-d", str(fixture), "--language", language]
        stage, report = run_stage(language, "ui", command, out / "ui.json", out / "process.log",
                                  lambda value: validate_ui(value, language, version), output, runner)
        stages.append(stage)
        summary = {"language": language, **report} if report is not None else {"language": language}
        dependency = restart_dependency(out, language, before)
        if dependency:
            stages.append({"language": language, "stage": "restart", "status": "not-executed",
                           "reasons": [dependency]})
        else:
            restarted = out / "restarted"
            command = [str(app), *launcher, "-n", "--disable_opengl", "--config-dir", str(out / "settings"),
                       "--self-test-ui", str(restarted), "--self-test-size", args.window_size,
                       "-d", str(fixture)]
            stage, _ = run_stage(language, "restart", command, restarted / "ui.json", out / "restart.log",
                                 lambda value: validate_ui(value, language, version), output, runner)
            stages.append(stage)
        if args.ui_only:
            stages.append({"language": language, "stage": "memes", "status": "not-selected",
                           "reasons": []})
        else:
            meme_out = out / "memes"
            command = [str(app), *launcher, "--language", language, "--config-dir", str(out / "settings"),
                       "--export-memes", str(meme_out)]
            stage, memes = run_stage(language, "memes", command, meme_out / "memes.json", out / "memes.log",
                                     lambda value: validate_memes(value, language, localized_count), output, runner)
            stages.append(stage)
            if memes is not None:
                summary["meme_images"] = len(memes)
        failed = [item["stage"] for item in stages if item["language"] == language and item["status"] not in ("passed", "not-selected")]
        if failed:
            summary.update(acceptance_status="failed", failed_stages=failed)
        reports.append(summary)
    counts = {status: sum(item["status"] == status for item in stages)
              for status in ("passed", "failed", "not-executed", "not-selected")}
    selected_count = 6 if args.ui_only else 9
    passed = preflight["status"] == "passed" and counts["passed"] == selected_count
    result = {"passed": passed, "scope": "ui-only" if args.ui_only else "full",
              "selected_stage_count": selected_count, "preflight": preflight,
              "counts": counts, "stages": stages}
    (output / "summary.json").write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "stage-results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if passed else 1


def main(argv=None):
    args = parse_args(argv)
    try:
        code = run_acceptance(args)
    except OSError:
        print("FAIL: acceptance report directory is unavailable")
        return 1
    if code:
        print("FAIL: acceptance stages incomplete; see stage-results.json")
    elif args.ui_only:
        print("PASS: six selected UI and restart stages; image export not selected")
    else:
        print("PASS: three language catalogs, UI window captures, bundled synthetic DataFlash loader")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
