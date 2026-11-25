#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Run real CSV/FileLoader regressions only after the verified rebuilt DSO is staged."""
import argparse
import hashlib
import json
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
import subprocess
import stat
import sys

ROOT = Path(__file__).resolve().parents[2]
EXPECTED = {'CsvRuntimeFileLoader_' + language for language in ['zh_CN', 'zh_TW', 'en_US']}
CASES = {'CsvRuntimeFileLoader.' + name for name in [
    'EmptyCsvWritesTranslatedPrefixedDiagnosticJson', 'ShortWarningContinue', 'ShortWarningAbort',
    'ShortWarningClose', 'LongWarningContinue', 'LongWarningAbort', 'LongWarningClose']}


def audit_results(report):
    """Reject partial CTest success and filtered/skipped/truncated underlying GTests."""
    root = ET.parse(report).getroot()
    totals = {'tests': '3', 'failures': '0', 'disabled': '0', 'skipped': '0'}
    if root.tag != 'testsuite' or any(root.get(key) != value for key, value in totals.items()) or root.get('errors', '0') != '0':
        raise ValueError('CSV runtime suite must contain exactly three executed successful language tests')
    cases = list(root.iter('testcase'))
    if len(cases) != 3 or {case.get('name') for case in cases} != EXPECTED:
        raise ValueError('CSV runtime languages are missing, duplicated or unexpected')
    for case in cases:
        output = '\n'.join(node.text or '' for node in case.findall('system-out'))
        started = re.findall(r'^\[ RUN      \] (\S+)\r?$', output, re.M)
        passed = re.findall(r'^\[       OK \] (\S+) \(\d+ ms\)\r?$', output, re.M)
        if (case.get('status') != 'run'
                or any(case.find(tag) is not None for tag in ('failure', 'error', 'skipped'))
                or len(started) != 7 or set(started) != CASES or len(passed) != 7 or set(passed) != CASES
                or len(re.findall(r'^\[  PASSED  \] 7 tests\.\r?$', output, re.M)) != 1
                or re.search(r'\[\s*(?:SKIPPED|FAILED)\s*\]|DISABLED TEST|Google Test filter|truncat|test output was removed|exceeds the threshold', output, re.I)):
            raise ValueError('Incomplete CSV runtime evidence: ' + str(case.get('name')))
    return sorted(EXPECTED)



def staged_csv(prefix):
    """Fail closed on missing, ambiguous, altered or unlocked staged plugin bytes."""
    record = json.loads((prefix / 'share/plotjuggler4/release.json').read_text(encoding='utf-8'))
    lock = json.loads((ROOT / 'packaging/localization/plugin-patches/source-lock.json').read_text(encoding='utf-8'))
    source = next(item for item in lock['plugins'] if item['id'] == 'csv-loader')
    matches = [item for item in record['localized_plugin_rebuilds'] if item['id'] == source['id']]
    assert len(matches) == 1, 'exactly one rebuilt CSV record is required'
    item = matches[0]
    for field in ['version', 'commit', 'sdk', 'patch_sha256']:
        assert item[field] == source[field], 'staged CSV source identity differs: ' + field
    binaries = [entry for entry in item['files'] if Path(entry['path']).suffix in ('.so', '.dll')]
    assert len(binaries) == 1, 'exactly one rebuilt CSV binary is required'
    entry = binaries[0]
    binary = (prefix / entry['path']).resolve()
    assert binary.parent == (prefix / 'lib/plotjuggler/plugins/csv-loader').resolve()
    assert hashlib.sha256(binary.read_bytes()).hexdigest() == entry['sha256'], 'staged CSV binary hash differs'
    return binary


def runtime_environment(build, qt_override=None):
    """Give Windows CTest the DLL paths of this build, including during discovery."""
    env = os.environ.copy()
    if sys.platform != 'win32':
        return env
    if qt_override is None:
        cache = (build / 'CMakeCache.txt').read_text(encoding='utf-8')
        qt_dirs = re.findall(r'^Qt6_DIR:PATH=(.+)$', cache, re.M)
        if len(qt_dirs) != 1:
            raise ValueError('Require the configured Qt6_DIR for Windows CSV runtime tests')
        qt = Path(qt_dirs[0].strip()).parents[2]
    else:
        qt = Path(qt_override)
        if not (qt / 'bin').is_dir() or not (qt / 'plugins').is_dir():
            raise ValueError('The explicit Qt runtime must contain bin and plugins')
    dirs = [str(qt / 'bin')]
    for name in ['pj_ffmpeg_bin_dirs.txt', 'pj_python_bin_dirs.txt']:
        listing = build / name
        if listing.is_file():
            dirs.extend(line.strip() for line in listing.read_text(encoding='utf-8').splitlines() if line.strip())
    # Like test.bat, prefer the exact configured dependencies over unrelated
    # system Qt/Python installs. Staging has not yet deployed a complete runtime.
    env['PATH'] = ';'.join([*dirs, env.get('PATH', '')])
    env['QT_PLUGIN_PATH'] = str(qt / 'plugins')
    return env


def file_sha256(path):
    """Hash large native files without buffering the whole executable."""
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def file_contains(path, needle):
    """Find a compiled string even when it straddles a read boundary."""
    overlap = b''
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            data = overlap + chunk
            if needle in data:
                return True
            overlap = data[-(len(needle) - 1):] if len(needle) > 1 else b''
    return False


def selected_runner(listing):
    """Require exactly the three language registrations and one shared runner."""
    doc = json.loads(listing)
    tests = doc.get('tests', [])
    if {test.get('name') for test in tests} != EXPECTED or len(tests) != len(EXPECTED):
        raise ValueError('CSV runtime language registrations are incomplete or duplicated')
    runners = []
    for test in tests:
        command = test.get('command')
        if not isinstance(command, list) or len(command) != 1:
            raise ValueError('CSV runtime test must directly invoke its one runner')
        properties = {p['name']: p['value'] for p in test.get('properties', [])}
        if test.get('config') != 'RelWithDebInfo' or properties.get('DISABLED', False):
            raise ValueError('CSV runtime test has the wrong configuration or is disabled')
        language = test['name'].removeprefix('CsvRuntimeFileLoader_')
        environment = properties.get('ENVIRONMENT', [])
        if f'PLOTJUGGLER_UI_LANGUAGE={language}' not in environment or 'QT_QPA_PLATFORM=offscreen' not in environment:
            raise ValueError('CSV runtime language or Qt platform property differs')
        runners.append(Path(command[0]).resolve())
    if len(set(runners)) != 1 or not runners[0].is_file():
        raise ValueError('CSV runtime runner is absent or ambiguous')
    return runners[0]


def csv_sdk_version():
    lock = json.loads((ROOT / 'packaging/localization/plugin-patches/source-lock.json').read_text(encoding='utf-8'))
    return next(item for item in lock['plugins'] if item['id'] == 'csv-loader')['sdk']


def verify_release_source(prefix, source_sha):
    record = json.loads((Path(prefix) / 'share/plotjuggler4/release.json').read_text(encoding='utf-8'))
    if record.get('source_commit') != source_sha:
        raise ValueError('CSV staged rebuild is not bound to the exact source commit')


def capture_prebuilt(path, listing, plugin, source_sha, source_tree, qt_dir, qt_version, host_sdk, ctest):
    """Seal a fresh runner, real staged DSO, Qt and exact CTest for same-root use."""
    if not re.fullmatch(r'[0-9a-f]{40}', source_sha or '') or not re.fullmatch(r'[0-9a-f]{40}', source_tree or ''):
        raise ValueError('Prebuilt identity needs the full source commit and tree')
    if not qt_version or not host_sdk:
        raise ValueError('Prebuilt identity needs the Qt and host SDK versions')
    runner = selected_runner(listing)
    plugin = Path(plugin).resolve(strict=True)
    qt_core = (Path(qt_dir).resolve(strict=True) / 'bin/Qt6Core.dll').resolve(strict=True)
    ctest = Path(ctest).resolve(strict=True)
    if not file_contains(runner, plugin.as_posix().encode('utf-8') + b'\0'):
        raise ValueError('Runner does not contain the exact staged CSV plugin path')
    record = {'schema': 1, 'source_sha': source_sha, 'source_tree': source_tree,
              'configuration': 'RelWithDebInfo', 'runner': runner.as_posix(),
              'runner_sha256': file_sha256(runner), 'plugin': plugin.as_posix(),
              'plugin_sha256': file_sha256(plugin), 'plugin_sdk': csv_sdk_version(),
              'host_sdk': host_sdk, 'qt_version': qt_version, 'qt_core': qt_core.as_posix(),
              'qt_core_sha256': file_sha256(qt_core), 'ctest': ctest.as_posix(),
              'ctest_sha256': file_sha256(ctest)}
    path = Path(path)
    if path.exists():
        raise ValueError('Refusing to replace existing prebuilt identity')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return record


def verify_bound_manifest(manifest_path, expected_sha256, kit, paths, source_sha, source_tree):
    """Verify independently anchored bundle identity and every selected input."""
    manifest_path = Path(manifest_path)
    if not re.fullmatch(r'[0-9a-f]{64}', expected_sha256 or '') or file_sha256(manifest_path) != expected_sha256:
        raise ValueError('Bundle manifest digest differs from independent evidence')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    provenance = manifest.get('provenance', {})
    if (manifest.get('schema') != 1 or provenance.get('source_sha') != source_sha or
            provenance.get('source_tree') != source_tree or provenance.get('configuration') != 'RelWithDebInfo'):
        raise ValueError('Bundle manifest source or configuration differs')
    if os.name == 'nt' and os.path.normcase(os.path.normpath(str(kit))) != os.path.normcase(os.path.normpath(manifest.get('logical_root', ''))):
        raise ValueError('Bundle is not at the verified build-time root')
    entries = manifest.get('files', [])
    if not isinstance(entries, list):
        raise ValueError('Invalid bundle manifest file list')
    by_path = {}
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get('path'), str):
            raise ValueError('Invalid bundle manifest file record')
        key = entry['path'].casefold()
        if key in by_path:
            raise ValueError('Duplicate case-insensitive bundle manifest path')
        by_path[key] = entry
    for entry in entries:
        rel = entry['path']
        if ('\\' in rel or any(part in ('', '.', '..') or ':' in part for part in rel.split('/'))):
            raise ValueError('Invalid manifest input path')
        path = kit.joinpath(*rel.split('/'))
        if not inside(path, kit) or not path.is_file():
            raise ValueError('A manifest input is missing or outside the kit')
        for part in (path, *path.parents):
            info = part.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                raise ValueError('A manifest input has a link or reparse-point ancestor')
            if part == kit:
                break
        if entry.get('bytes') != path.stat().st_size or entry.get('sha256') != file_sha256(path):
            raise ValueError('A manifest input hash or size differs: ' + rel)
    for path in paths:
        path = Path(path).resolve(strict=True)
        if not inside(path, kit) or not path.is_file():
            raise ValueError('A required prebuilt input is missing or outside the kit')
        if path.relative_to(kit).as_posix().casefold() not in by_path:
            raise ValueError('A required prebuilt input is absent from the bundle manifest')
    return provenance


def verify_prebuilt_files(path, plugin, source_sha, source_tree, qt_dir, ctest, kit, manifest, manifest_sha256, prefix, build):
    """Check all immutable identities before CTest can execute discovery."""
    if not re.fullmatch(r'[0-9a-f]{40}', source_sha or '') or not re.fullmatch(r'[0-9a-f]{40}', source_tree or ''):
        raise ValueError('Prebuilt execution requires a full source commit and tree')
    record = json.loads(Path(path).read_text(encoding='utf-8'))
    if record.get('schema') != 1 or record.get('configuration') != 'RelWithDebInfo':
        raise ValueError('Unsupported CSV prebuilt identity')
    if record.get('source_sha') != source_sha or record.get('source_tree') != source_tree:
        raise ValueError('CSV prebuilt source identity does not match')
    runner = Path(record.get('runner', '')).resolve(strict=True)
    plugin = Path(plugin).resolve(strict=True)
    qt_core = (Path(qt_dir).resolve(strict=True) / 'bin/Qt6Core.dll').resolve(strict=True)
    ctest = Path(ctest).resolve(strict=True)
    if (record.get('plugin') != plugin.as_posix() or record.get('qt_core') != qt_core.as_posix() or
            record.get('ctest') != ctest.as_posix()):
        raise ValueError('CSV prebuilt plugin, Qt or CTest absolute path differs')
    inputs = [path, runner, plugin, qt_core, ctest, ROOT / 'packaging/localization/plugin-patches/source-lock.json',
              prefix / 'share/plotjuggler4/release.json', Path(__file__).resolve(),
              build / 'pj_ffmpeg_bin_dirs.txt', build / 'pj_python_bin_dirs.txt']
    provenance = verify_bound_manifest(manifest, manifest_sha256, kit, inputs, source_sha, source_tree)
    verify_release_source(prefix, source_sha)
    if record.get('plugin_sdk') != csv_sdk_version() or record.get('host_sdk') != provenance.get('sdk') or record.get('qt_version') != provenance.get('qt'):
        raise ValueError('CSV prebuilt Qt or SDK identity differs')
    for item, key in [(runner, 'runner_sha256'), (plugin, 'plugin_sha256'), (qt_core, 'qt_core_sha256'), (ctest, 'ctest_sha256')]:
        if record.get(key) != file_sha256(item):
            raise ValueError('CSV prebuilt runner, plugin, Qt or CTest bytes differ')
    if not file_contains(runner, plugin.as_posix().encode('utf-8') + b'\0'):
        raise ValueError('CSV runner lacks the exact staged plugin path')
    return record


def verify_prebuilt_selection(record, listing):
    runner = selected_runner(listing)
    if record.get('runner') != runner.as_posix() or record.get('runner_sha256') != file_sha256(runner):
        raise ValueError('CSV selected runner differs from the sealed prebuilt runner')


def verify_runtime_directories(build, qt, kit, manifest_path):
    """Only immutable manifest directories may be prepended to the DLL path."""
    manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    declared = manifest.get('directories')
    if not isinstance(declared, list) or any(not isinstance(x, str) for x in declared):
        raise ValueError('Bundle manifest lacks its immutable directory list')
    immutable = {value.casefold() for value in declared}
    paths = [Path(qt) / 'bin', Path(qt) / 'plugins']
    for name in ('pj_ffmpeg_bin_dirs.txt', 'pj_python_bin_dirs.txt'):
        listing = Path(build) / name
        if not listing.is_file():
            raise ValueError('Prebuilt runtime dependency path list is missing: ' + name)
        paths.extend(Path(line.strip()) for line in listing.read_text(encoding='utf-8').splitlines() if line.strip())
    for path in paths:
        if not path.is_absolute() or '..' in path.parts:
            raise ValueError('Prebuilt runtime dependency path must be absolute and canonical')
        try:
            relative = path.relative_to(kit).as_posix()
        except ValueError:
            raise ValueError('Prebuilt runtime dependency path is outside the kit') from None
        if relative.casefold() == 'r' or relative.casefold().startswith('r/') or relative.casefold() not in immutable:
            raise ValueError('Prebuilt runtime dependency directory is not an immutable manifest input')
        for part in (path, *path.parents):
            info = part.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                raise ValueError('Prebuilt runtime directory has a link or reparse-point ancestor')
            if part == kit:
                break
        if not path.is_dir():
            raise ValueError('Prebuilt runtime dependency directory is missing')


def inside(path, root):
    try:
        return Path(path).resolve().is_relative_to(Path(root).resolve())
    except (OSError, ValueError):
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--prefix', type=Path, required=True)
    parser.add_argument('--capture-prebuilt', type=Path, help='Capture identity after a fresh same-root build')
    parser.add_argument('--prebuilt-identity', type=Path, help='Run a previously verified same-root build without compiling')
    parser.add_argument('--source-sha', help='Full source commit for prebuilt capture or verification')
    parser.add_argument('--source-tree', help='Full source tree for prebuilt capture or verification')
    parser.add_argument('--kit-root', type=Path, help='Exact verified kit root for prebuilt execution')
    parser.add_argument('--qt-dir', type=Path, help='Exact verified Qt runtime for prebuilt execution')
    parser.add_argument('--ctest', type=Path, help='Exact portable CTest executable')
    parser.add_argument('--qt-version', help='Pinned Qt version when capturing the prebuilt identity')
    parser.add_argument('--host-sdk', help='Host SDK version when capturing the prebuilt identity')
    parser.add_argument('--manifest', type=Path, help='Verified native kit manifest')
    parser.add_argument('--manifest-sha256', help='Independently obtained manifest SHA-256')
    parser.add_argument('--report', type=Path, help='Optional output JUnit path in the verified kit root')
    args = parser.parse_args()
    if args.capture_prebuilt and args.prebuilt_identity:
        parser.error('choose capture or prebuilt execution, not both')
    if not (args.capture_prebuilt or args.prebuilt_identity) and any((
            args.source_sha, args.source_tree, args.kit_root, args.qt_dir, args.ctest, args.qt_version,
            args.host_sdk, args.manifest, args.manifest_sha256, args.report)):
        parser.error('prebuilt-only options require an explicit prebuilt mode')
    build, prefix = args.build.resolve(), args.prefix.resolve()
    if args.capture_prebuilt or args.prebuilt_identity:
        if not all((args.kit_root, args.qt_dir, args.ctest, args.source_sha, args.source_tree)):
            parser.error('prebuilt mode requires kit root, Qt, CTest and source identity')
        kit = args.kit_root.resolve(strict=True)
        if any(not inside(path, kit) for path in (ROOT, build, prefix, args.qt_dir, args.ctest)):
            raise ValueError('Prebuilt CSV paths must remain under the verified kit root')
    binary = staged_csv(prefix)
    if args.prebuilt_identity:
        if not all((args.kit_root, args.qt_dir, args.ctest, args.source_sha, args.source_tree, args.report,
                    args.manifest, args.manifest_sha256)):
            parser.error('prebuilt execution requires kit root, Qt, CTest, source identity, manifest and report')
        required_paths = (ROOT, build, prefix, args.qt_dir, args.ctest, args.report, args.prebuilt_identity, args.manifest)
        if any(not inside(path, kit) for path in required_paths):
            raise ValueError('Prebuilt CSV paths must remain under the verified kit root')
        if not args.ctest.is_file():
            raise ValueError('The explicit portable CTest executable is missing')
        if args.qt_version or args.host_sdk:
            parser.error('Qt and host SDK capture options are not accepted during prebuilt execution')
        if args.report.exists() or not args.report.parent.is_dir():
            raise ValueError('Prebuilt CSV report must be new and have an existing parent')
        record = verify_prebuilt_files(args.prebuilt_identity, binary, args.source_sha, args.source_tree,
                                       args.qt_dir, args.ctest, kit, args.manifest, args.manifest_sha256, prefix, build)
        verify_runtime_directories(build, args.qt_dir.resolve(strict=True), kit, args.manifest)
        env = runtime_environment(build, args.qt_dir.resolve(strict=True))
        ctest = str(args.ctest.resolve(strict=True))
    else:
        if args.capture_prebuilt and not all((args.qt_version, args.host_sdk)):
            parser.error('prebuilt capture requires Qt and host SDK versions')
        if args.capture_prebuilt and any((args.manifest, args.manifest_sha256, args.report)):
            parser.error('manifest and report options belong only to prebuilt execution')
        if args.capture_prebuilt and not inside(args.capture_prebuilt, kit):
            raise ValueError('Prebuilt identity output must remain under the kit root')
        if not args.capture_prebuilt:
            subprocess.run(['cmake', '-S', str(ROOT), '-B', str(build),
                            '-DPJ_CSV_RUNTIME_PLUGIN=' + binary.as_posix()], check=True)
            subprocess.run(['cmake', '--build', str(build), '--config', 'RelWithDebInfo',
                            '--target', 'csv_runtime_file_loader_test', '--parallel', '2'], check=True)
        else:
            verify_release_source(prefix, args.source_sha)
        env = runtime_environment(build, args.qt_dir if args.capture_prebuilt else None)
        ctest = str(args.ctest.resolve(strict=True)) if args.capture_prebuilt else 'ctest'
    selection = ['-R', '^CsvRuntimeFileLoader_']
    listing = subprocess.check_output([ctest, '--test-dir', str(build), '-C', 'RelWithDebInfo',
                                       '--show-only=json-v1', *selection], env=env, text=True, encoding='utf-8')
    if args.capture_prebuilt:
        capture_prebuilt(args.capture_prebuilt, listing, binary, args.source_sha, args.source_tree,
                         args.qt_dir, args.qt_version, args.host_sdk, args.ctest)
        return
    if args.prebuilt_identity:
        verify_prebuilt_selection(record, listing)
    else:
        selected = {test['name'] for test in json.loads(listing)['tests']}
        assert selected == EXPECTED, (selected, EXPECTED)
    report = args.report.resolve() if args.report else build / 'csv-runtime.xml'
    if args.prebuilt_identity:
        # Preserve the native runner's full output in its parent process log.
        # A marker-based audit still fails closed if CTest removes any output.
        output_options = ['--verbose', '--test-output-size-passed', '1073741824',
                          '--test-output-size-failed', '1073741824']
    else:
        # The existing build-and-run publication gate remains unchanged.
        output_options = ['--output-on-failure', '--test-output-size-passed', '262144']
    subprocess.run([ctest, '--test-dir', str(build), '-C', 'RelWithDebInfo', '--no-tests=error',
                    '--timeout', '120', *output_options, '--output-junit', str(report),
                    *selection], env=env, check=True)
    audit_results(report)


if __name__ == '__main__':
    main()
