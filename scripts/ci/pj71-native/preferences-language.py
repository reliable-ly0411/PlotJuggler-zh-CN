#!/usr/bin/env python3
"""Verify the pinned PJ4 PreferencesLanguageTest-only probe."""
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

BASE = '5526844b48afa5cfa531f5125aa4ea7f29b43af8'
CANDIDATE = '38447475371eb386a7f1e542468f60f954249984'
TREE = 'bf49ccd7e396b1f463d4ebf6d7c38375f5a06bc3'
PATCH_SHA256 = 'c789f04ee25fb95f00b19d8298f00804aefacbcfeeb99f6f2642960f3984983f'
RAW_COMMIT = (
    'tree ' + TREE + '\nparent ' + BASE + '\n'
    'author Codex preview <codex-preview@openai.com> 1795309145 -0800\n'
    'committer Codex preview <codex-preview@openai.com> 1795309145 -0800\n\n'
    'fix(i18n): preserve unrecognized saved language on unrelated OK\n'
).encode()
TEST_SOURCE = 'pj_app/tests/preferences_language_test.cpp'
SCOPE = {'pj_app/src/PreferencesDialog.cpp', 'pj_app/src/PreferencesDialog.h', TEST_SOURCE}
PREFIX = 'pj_app_gui_tests.PreferencesLanguageTest.'
EXPECTED = {
    'ChineseMainWindowRendersWithTranslatedMenus',
    'EnglishMainWindowRendersWithSourceMenus',
    'TraditionalMainWindowRendersWithTranslatedMenus',
    'ChinesePreferencesRendersLanguageControls',
    'EnglishPreferencesRendersLanguageControls',
    'TraditionalPreferencesRendersLanguageControls',
    'FreshProfileOffersThreeLanguagesWithARestartNotice',
    'AcceptSavesNextLaunchLanguageWithoutRetranslatingTheSession',
    'CancelLeavesTheSavedLanguageAlone',
    'UnrelatedAcceptPreservesFutureLanguage',
    'ExplicitSelectionReplacesFutureLanguageOnlyOnAccept',
    'ExplicitSelectionCanSaveAlreadyDisplayedEnglishFallback',
    'TraditionalChoicePersistsOnAcceptButNotOnCancel',
    'SessionOverrideDoesNotChangeTheNextLaunchSelection',
    'LanguageSelectorHonorsBothSizeHintsAcrossFonts',
    'MinimumSizeKeepsTranslatedAppearanceControlsReachable',
    'TelemetryDefaultsOffAndCancelDoesNotConsent',
    'TelemetryConsentPersistsOnlyAfterAcceptAndCanBeRevoked',
}


def require(ok, message):
    if not ok:
        raise SystemExit(message)


def git(*args, data=None):
    return subprocess.check_output(['git', *args], input=data).decode().strip()


def patch_bytes():
    path = Path(__file__).with_suffix('.patch.b64')
    return base64.b64decode(b''.join(path.read_bytes().split()), validate=True)


def verify_patch(patch):
    require(hashlib.sha256(patch).hexdigest() == PATCH_SHA256, 'Patch SHA-256 mismatch')
    require(patch.splitlines()[0].startswith(f'From {CANDIDATE} '.encode()), 'Candidate patch header mismatch')


def verify_roster(text):
    cases = re.findall(r'^TEST\(PreferencesLanguageTest,\s*(\w+)\)', text, re.MULTILINE)
    require(len(cases) == len(EXPECTED) == 18 and set(cases) == EXPECTED,
            'Exact 18 test cases do not match the candidate test source')


def source(evidence):
    require(git('rev-parse', 'HEAD') == BASE, 'Pinned development base mismatch')
    require(not git('status', '--porcelain', '--untracked-files=no'), 'Expected clean tracked source')
    patch = patch_bytes()
    verify_patch(patch)
    git('apply', '--check', '--index', '--binary', '-', data=patch)
    git('apply', '--index', '--binary', '-', data=patch)
    require(set(git('diff', '--cached', '--name-only').splitlines()) == SCOPE, 'Unexpected patched paths')
    require(git('write-tree', '--missing-ok') == TREE, 'Candidate tree mismatch')
    require(git('hash-object', '-w', '-t', 'commit', '--stdin', data=RAW_COMMIT) == CANDIDATE,
            'Candidate commit object mismatch')
    git('checkout', '--detach', CANDIDATE)
    require(git('rev-parse', 'HEAD') == CANDIDATE, 'Candidate checkout mismatch')
    require(git('rev-parse', 'HEAD^{tree}') == TREE, 'Candidate checkout tree mismatch')
    require(not git('status', '--porcelain', '--untracked-files=no'), 'Candidate worktree is not clean')
    verify_roster(Path(TEST_SOURCE).read_text(encoding='utf-8'))
    (evidence / 'source.txt').write_text(
        f'base={BASE}\ncandidate={CANDIDATE}\ntree={TREE}\npatch_sha256={PATCH_SHA256}\n',
        encoding='utf-8',
    )
    (evidence / 'submodules.txt').write_text(git('submodule', 'status', '--recursive') + '\n', encoding='utf-8')



def seed(cache):
    # Same verified source-cache format as the stable-delta Linux lane.
    target = cache / 's'
    target.mkdir(parents=True, exist_ok=True)
    for blob in Path('.github/conan/source-backup').iterdir():
        if not re.fullmatch(r'[0-9a-f]{64}', blob.name):
            continue
        metadata = blob.with_suffix('.json')
        require(hashlib.sha256(blob.read_bytes()).hexdigest() == blob.name, f'Bad Conan seed {blob.name}')
        require(json.loads(metadata.read_text(encoding='utf-8')).get('references'), f'Missing Conan metadata {blob.name}')
        shutil.copy2(blob, target / blob.name)
        shutil.copy2(metadata, target / metadata.name)

    # xz 5.4.5's recipe points at the older unavailable tukaani.org path.
    digest = 'da9dec6c12cf2ecf269c31ab65b5de18e8e52b96f35d5bcd08c12b43e6878803'
    if not (target / digest).exists():
        url = 'https://github.com/tukaani-project/xz/releases/download/v5.4.5/xz-5.4.5.tar.xz'
        with urllib.request.urlopen(url, timeout=60) as download:
            data = download.read(10 * 1024 * 1024)
        require(hashlib.sha256(data).hexdigest() == digest, 'Wrong xz source bytes')
        (target / digest).write_bytes(data)
        (target / (digest + '.json')).write_text(json.dumps({
            'references': {'xz_utils/5.4.5': ['https://tukaani.org/xz/xz-5.4.5.tar.xz']},
            'timestamp': time.time(),
        }), encoding='utf-8')


def test(evidence):
    require(git('rev-parse', 'HEAD') == CANDIDATE and git('rev-parse', 'HEAD^{tree}') == TREE,
            'Unexpected source at CTest')
    verify_roster(Path(TEST_SOURCE).read_text(encoding='utf-8'))
    expected = {PREFIX + name for name in EXPECTED}
    ctest = ['ctest', '--test-dir', 'build', '-R', r'^pj_app_gui_tests\.PreferencesLanguageTest\.']
    listing = subprocess.check_output([*ctest, '--show-only=json-v1'])
    (evidence / 'ctest-discovery.json').write_bytes(listing)
    found = [case['name'] for case in json.loads(listing)['tests']]
    require(len(found) == len(expected) and set(found) == expected,
            f'CTest discovery mismatch: missing={expected - set(found)}, extra={set(found) - expected}')
    (evidence / 'test-names.txt').write_text('\n'.join(sorted(expected)) + '\n', encoding='utf-8')
    report = evidence / 'ctest.xml'
    log = evidence / 'ctest.log'
    with log.open('w', encoding='utf-8') as output:
        run = subprocess.run(
            [*ctest, '--no-tests=error', '--parallel', '1', '--timeout', '120',
             '--output-on-failure', '--output-junit', str(report)],
            stdout=output, stderr=subprocess.STDOUT, check=False,
        )
    print(log.read_text(encoding='utf-8'), end='')
    require(run.returncode == 0, f'CTest failed: {run.returncode}')
    cases = ET.parse(report).getroot().findall('.//testcase')
    require(len(cases) == len(expected) and {case.get('name') for case in cases} == expected,
            'CTest JUnit case roster mismatch')
    require(all(not any(case.find(tag) is not None for tag in ('failure', 'error', 'skipped')) for case in cases),
            'CTest JUnit contains failure, error or skipped case')
    print('Exactly 18 PreferencesLanguageTest cases passed.')


if __name__ == '__main__':
    evidence_root = Path(os.environ['RUNNER_TEMP']) / 'pj71-preferences-language-evidence'
    evidence_root.mkdir(parents=True, exist_ok=True)
    if len(sys.argv) == 3 and sys.argv[1] == 'seed':
        seed(Path(sys.argv[2]))
    else:
        require(len(sys.argv) == 2 and sys.argv[1] in ('source', 'test'), 'Expected source, seed or test')
        {'source': source, 'test': test}[sys.argv[1]](evidence_root)
