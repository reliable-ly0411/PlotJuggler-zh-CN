#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Rebuild only pinned official plugins with source-local display patches.

No upstream upload, credentials, protocol changes, version masquerading or AI
calls. Each source/SDK and Conan graph is isolated and recorded. A missing
plugin target, test failure, identity mismatch or missing notice aborts staging.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PATCHES = ROOT / 'packaging/localization/plugin-patches'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args, cwd=None, env=None):
    print('+', ' '.join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), cwd=cwd, env=env, check=True)


def checkout(url, commit, directory):
    if directory.exists():
        raise ValueError(f'Require a fresh source directory: {directory}')
    directory.mkdir(parents=True)
    run(['git', 'init', directory])
    run(['git', '-C', directory, 'fetch', '--depth=1', url, commit])
    run(['git', '-C', directory, '-c', 'core.autocrlf=false', 'checkout', '--detach', 'FETCH_HEAD'])
    actual = subprocess.check_output(['git', '-C', directory, 'rev-parse', 'HEAD'], text=True).strip()
    assert actual == commit, (actual, commit)


def validate_sdk_version(source, expected):
    version_file = source / 'VERSION'
    if version_file.is_file():
        actual = version_file.read_text().strip()
    else:
        # SDK 0.20.0 predates VERSION; its exact pinned recipe is authoritative.
        matches = re.findall(r'^\s+version\s*=\s*["\']([^"\']+)["\']\s*$',
                             (source / 'conanfile.py').read_text(), re.M)
        assert len(matches) == 1, 'ambiguous legacy SDK recipe version'
        actual = matches[0]
    assert actual == expected, (actual, expected)


def build_one(item, lock, work, prefix, platform):
    identifier = item['id']
    assert identifier != 'toolbox-mosaico', 'Mosaico must remain the original official binary (issue #20)'
    source = work / identifier / 'source'
    build = work / identifier / 'build'
    build.mkdir(parents=True)
    checkout(lock['repository'], item['commit'], source)
    assert (source / 'SDK_VERSION').read_text().strip() == item['sdk']
    manifest = json.loads((source / item['module'] / 'manifest.json').read_text())
    assert manifest['id'] == identifier and manifest['version'] == item['version']
    patch = PATCHES / (identifier + '.patch')
    assert digest(patch) == item['patch_sha256']
    run(['git', '-C', source, 'apply', '--check', patch])
    run(['git', '-C', source, 'apply', patch])
    shutil.copy2(PATCHES / 'pj_display_language.hpp', source)
    # Add deterministic offline checks to every isolated native build. The
    # Assistant variant also compiles its patched model and checks raw text.
    fixture = (PATCHES / 'display_language_test.cpp').as_posix()
    cmake_path = source / 'CMakeLists.txt'
    checks = '\nadd_executable(pj_localized_display_test "' + fixture + '")\n'
    checks += 'target_include_directories(pj_localized_display_test PRIVATE "${CMAKE_SOURCE_DIR}")\n'
    if identifier == 'toolbox-assistant-agent':
        checks += 'target_compile_definitions(pj_localized_display_test PRIVATE PJ_TEST_ASSISTANT=1)\n'
    for language in ['zh_CN', 'en_US']:
        name = 'LocalizedDisplay_' + language
        checks += f'add_test(NAME {name} COMMAND pj_localized_display_test {language})\n'
        checks += f'set_tests_properties({name} PROPERTIES ENVIRONMENT "PLOTJUGGLER_UI_LANGUAGE={language}")\n'
    for suffix, value in [('unknown', 'unrecognized'), ('empty', '')]:
        name = 'LocalizedDisplay_' + suffix
        checks += f'add_test(NAME {name} COMMAND pj_localized_display_test en_US)\n'
        checks += f'set_tests_properties({name} PROPERTIES ENVIRONMENT "PLOTJUGGLER_UI_LANGUAGE={value}")\n'
    cmake_path.write_text(cmake_path.read_text() + checks)
    sdk = item['sdk']
    common = ['-s', 'build_type=Release', '-s', 'compiler.cppstd=20', '-s:b', 'compiler.cppstd=20']
    if platform == 'Windows':
        common += ['-s', 'compiler.version=194']
    # Public vendor registry first; no signing/upload/authentication changes.
    probe = subprocess.run(['conan', 'install', '--requires=plotjuggler_sdk/' + sdk,
                            '--build=never', '-r=plotjuggler-conan', '-r=conancenter',
                            '-of', str(work / ('sdk-probe-' + sdk)), *common])
    sdk_acquisition = 'public-conan-binary; identity is the resolved graph reference/package revision'
    if probe.returncode:
        sdk_source = work / ('sdk-source-' + sdk)
        if not sdk_source.exists():
            checkout(lock['sdk_repository'], lock['sdk_commits'][sdk], sdk_source)
        actual_sdk = subprocess.check_output(['git', '-C', sdk_source, 'rev-parse', 'HEAD'], text=True).strip()
        assert actual_sdk == lock['sdk_commits'][sdk], 'unexpected reused SDK commit'
        assert not subprocess.check_output(['git', '-C', sdk_source, 'status', '--porcelain'], text=True).strip(), 'modified SDK checkout'
        sdk_acquisition = 'built from verified pinned source commit'
        validate_sdk_version(sdk_source, sdk)
        run(['conan', 'create', sdk_source, '--build=plotjuggler_sdk/*', '--build=missing', *common])
    graph = build / 'conan-graph.json'
    run(['conan', 'install', source / item['module'], '-of', build, '--build=missing',
         '-r=plotjuggler-conan', '-r=conancenter', *common,
         '-c', 'tools.cmake.cmaketoolchain:generator=Ninja',
         '-c', 'tools.build:jobs=2', '--lockfile-out=' + str(build / 'conan.lock'),
         '--format=json', '--out-file=' + str(graph)])
    env = os.environ.copy()
    env['PLOTJUGGLER_UI_LANGUAGE'] = 'en'
    # Never invoke external Assistant CLIs or a real server from release tests.
    for name in ['ANTHROPIC_API_KEY', 'OPENAI_API_KEY', 'CLAUDE_CODE_OAUTH_TOKEN']:
        env.pop(name, None)
    run(['cmake', '-S', source, '-B', build / 'native', '-G', 'Ninja',
         '-DCMAKE_TOOLCHAIN_FILE=' + str(build / 'conan_toolchain.cmake'),
         '-DCMAKE_PREFIX_PATH=' + str(build), '-DCMAKE_BUILD_TYPE=Release',
         '-DPJ_BUILD_PLUGIN=' + item['module'],
         *(['-DCMAKE_CXX_FLAGS=/utf-8'] if platform == 'Windows' else [])], env=env)
    run(['cmake', '--build', build / 'native', '--target', item['target'], '--parallel', '2'], env=env)
    run(['cmake', '--build', build / 'native', '--parallel', '2'], env=env)
    test_selection = ['-E', '(Live|live|Smoke|smoke)']
    if identifier == 'toolbox-assistant-agent':
        # Explicit pure-model allowlist. Dialog/settings tests can probe an
        # installed CLI even without API keys, so are deliberately not run.
        test_selection = ['-R', '^(LocalizedDisplay_.*|ToolboxAssistantAgent(ChatSession|UsageLedger|SettingsStore|ConversationState|SeriesStats|StreamJson)Test)$']
    if identifier == 'toolbox-assistant-agent':
        listing = subprocess.check_output(['ctest', '--test-dir', build / 'native', '--show-only=json-v1', *test_selection], env=env, text=True)
        selected = {test['name'] for test in json.loads(listing)['tests']}
        expected = {'ToolboxAssistantAgent' + name + 'Test' for name in
                    ['ChatSession', 'UsageLedger', 'SettingsStore', 'ConversationState', 'SeriesStats', 'StreamJson']}
        expected |= {'LocalizedDisplay_' + name for name in ['zh_CN', 'en_US', 'unknown', 'empty']}
        assert selected == expected, (selected, expected)
    run(['ctest', '--test-dir', build / 'native', '--no-tests=error', '--output-on-failure', '--timeout', '120',
         '--output-junit', str(build / 'offline-tests.xml'), *test_selection], env=env)
    run([sys.executable, source / 'scripts/release_tools.py', 'verify-version-consistency',
         item['module'], '--expected-version', item['version'], '--build-dir', build / 'native', '--check-manifest'], env=env)
    output = work / identifier / 'dist'
    run([sys.executable, source / 'scripts/release_tools.py', 'create-distribution-package',
         item['module'], '--version', item['version'], '--build-dir', build / 'native', '--output-dir', output], env=env)
    staged = output / identifier
    binaries = [p for p in staged.iterdir() if p.suffix in ('.so', '.dll')]
    assert len(binaries) == 1, binaries
    destination = prefix / 'lib/plotjuggler/plugins' / identifier
    shutil.copytree(staged, destination)
    notices = prefix / 'share/licenses/localized-plugins' / identifier
    notices.mkdir(parents=True)
    for candidate in source.glob('LICENSE*'):
        if candidate.is_file():
            shutil.copy2(candidate, notices)
    assert list(notices.glob('LICENSE*')), 'upstream license missing'
    shutil.copy2(patch, notices)
    shutil.copy2(PATCHES / 'pj_display_language.hpp', notices)
    nodes = json.loads(graph.read_text())['graph']['nodes']
    dependencies = []
    for node in nodes.values():
        if not node.get('ref') or not node.get('package_folder') or node.get('context') == 'build':
            continue
        ref = node['ref']
        licenses = Path(node['package_folder']) / 'licenses'
        if licenses.is_dir():
            shutil.copytree(licenses, notices / 'dependencies' / re.sub(r'[^A-Za-z0-9._-]', '_', ref.split('#')[0]))
        elif '/system' not in ref:
            raise ValueError('Missing dependency license: ' + ref)
        dependencies.append({key: node.get(key) for key in ['ref', 'package_id', 'prev', 'license']})
    # Include additional CPM-fetched dependency notices, not just Conan's graph.
    for dep in sorted((build / 'native/_deps').glob('*-src')):
        for candidate in list(dep.glob('LICENSE*')) + list(dep.glob('COPYING*')):
            if candidate.is_file():
                dst = notices / 'source-dependencies' / dep.name / candidate.name
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(candidate, dst)
    notice_files = [{'path': p.relative_to(prefix).as_posix(), 'sha256': digest(p)}
                    for p in sorted(notices.rglob('*')) if p.is_file()]
    files = [{'path': p.relative_to(prefix).as_posix(), 'sha256': digest(p)}
             for p in sorted(destination.rglob('*')) if p.is_file()]
    return {**item, 'kind': 'fork-localized-rebuild-not-upstream-binary',
            'helper_sha256': lock['helper_sha256'], 'sdk_source_fallback_commit': lock['sdk_commits'][sdk],
            'sdk_acquisition': sdk_acquisition,
            'conan_graph_sha256': digest(graph), 'conan_lock_sha256': digest(build / 'conan.lock'),
            'dependencies': dependencies, 'files': files, 'license_files': notice_files,
            'test_policy': 'pure-model Assistant allowlist; other upstream tests exclude live/smoke; no external AI',
            'ctest_selection': test_selection,
            'upstream_update_notice': 'Marketplace updates may replace this localized build; ID/version are preserved for compatibility.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--prefix', type=Path, required=True)
    args = parser.parse_args()
    lock = json.loads((PATCHES / 'source-lock.json').read_text())
    assert digest(PATCHES / 'pj_display_language.hpp') == lock['helper_sha256']
    platform = 'Windows' if os.name == 'nt' else 'Linux'
    if platform == 'Windows':
        os.environ.pop('PKG_CONFIG_PATH', None)
    work, prefix = args.work.resolve(), args.prefix.resolve()
    assert (prefix / 'share/plotjuggler4/release.json').is_file(), 'stage base payload first'
    results = []
    for item in lock['plugins']:
        if platform in item['platforms']:
            results.append(build_one(item, lock, work, prefix, platform))
            (work / 'completed.json').write_text(json.dumps(results, indent=2) + '\n')
    record_path = prefix / 'share/plotjuggler4/release.json'
    record = json.loads(record_path.read_text())
    record['localized_plugin_rebuilds'] = results
    record_path.write_text(json.dumps(record, indent=2) + '\n')
    shutil.copy2(PATCHES / 'source-lock.json', prefix / 'share/plotjuggler4/localized-plugin-sources.json')


if __name__ == '__main__':
    main()
