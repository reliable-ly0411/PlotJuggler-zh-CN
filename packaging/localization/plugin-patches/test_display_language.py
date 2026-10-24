#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Offline helper/patch-prose checks, independent of Qt, Conan and plugin SDKs.

This does not build plugin binaries. The native builder separately compiles the
same display fixture against pinned MCAP and Assistant sources.
"""
from collections import Counter
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile
import unittest

PATCHES = Path(__file__).resolve().parent
LITERAL = r'"(?:[^"\\]|\\.)*"'
CALL = re.compile(r'pj_zh_localization::text\((' + LITERAL + r'), (' +
                  LITERAL + r'), (' + LITERAL + r')\)')
PLACEHOLDER = re.compile(r'\{[^{}]*\}|%\d+')
LANGUAGES = [
    ('zh_CN', 'zh_CN', 1),
    ('zh_TW', 'zh_TW', 2),
    ('en_US', 'en_US', 0),
    ('unrecognized', 'en_US', 0),
    ('', 'en_US', 0),
    (None, 'en_US', 0),
    ('zh-TW', 'en_US', 0),
    ('zh_HK', 'en_US', 0),
    ('zh_TW.UTF-8', 'en_US', 0),
    ('x' * 128, 'en_US', 0),
]


def prose_calls():
    """Read only fixed-literal display calls added by the maintained patches."""
    for patch in sorted(PATCHES.glob('*.patch')):
        additions = '\n'.join(line[1:] for line in patch.read_text(encoding='utf-8').splitlines()
                              if line.startswith('+') and not line.startswith('+++'))
        matches = list(CALL.finditer(additions))
        if len(matches) != additions.count('pj_zh_localization::text('):
            raise AssertionError(f'{patch.name}: every display call must have three fixed literals')
        for match in matches:
            yield patch.name, match.groups()


class DisplayLanguageDataTest(unittest.TestCase):
    def test_fixed_prose_has_three_languages_and_preserved_placeholders(self):
        calls = list(prose_calls())
        self.assertTrue(calls, 'no display prose found')
        for patch, literals in calls:
            values = [json.loads(literal) for literal in literals]
            for translated in values[1:]:
                with self.subTest(patch=patch, english=values[0], translated=translated):
                    self.assertTrue(translated)
                    self.assertEqual(Counter(PLACEHOLDER.findall(values[0])),
                                     Counter(PLACEHOLDER.findall(translated)))

    def test_protocol_names_and_commands_in_prose_are_not_translated(self):
        tokens = ['FileDescriptorSet', 'SummaryOffset', 'Statistics', 'ROS 2',
                  'metadata.yaml', 'ros2 bag convert', 'storage_id: mcap',
                  'MCAP', 'arrow-ipc', 'JSON']
        for patch, literals in prose_calls():
            values = [json.loads(literal) for literal in literals]
            for token in tokens:
                if token in values[0]:
                    with self.subTest(patch=patch, english=values[0], token=token):
                        self.assertEqual(values[1].count(token), values[0].count(token))
                        self.assertEqual(values[2].count(token), values[0].count(token))


class DisplayLanguageNativeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compiler = shlex.split(os.environ.get('CXX', 'cl' if os.name == 'nt' else 'c++'))
        if not cls.compiler or not shutil.which(cls.compiler[0]):
            raise unittest.SkipTest('A native C++ compiler is required for helper execution')
        cls.temporary = tempfile.TemporaryDirectory(prefix='pj-display-language-')
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.work = Path(cls.temporary.name)
        suffix = '.exe' if os.name == 'nt' else ''
        cls.fixture = cls.work / ('display_fixture' + suffix)
        cls.corpus = cls.work / ('display_corpus' + suffix)
        cls.compile(PATCHES / 'display_language_test.cpp', cls.fixture)
        rows = ',\n'.join('    {' + ', '.join(literals) + '}' for _, literals in prose_calls())
        # Exercise the one composed validation message that needs English
        # singular/plural grammar, using its actual patched C++ expression.
        transform = (PATCHES / 'toolbox-transform-editor.patch').read_text(encoding='utf-8')
        declaration = re.search(r'^\+      const std::string msg = .+\n .+;', transform, re.M)
        if declaration is None:
            raise AssertionError('Transform validation-message fixture no longer matches its source patch')
        transform_expression = '\n'.join(line[1:] for line in declaration.group().splitlines())
        source = cls.work / 'corpus.cpp'
        source.write_text('''#include <pj_display_language.hpp>
#include <cstdlib>
#include <cstring>
#include <string>
std::string transformNoOutput(int num_outputs) {
  const std::string n = std::to_string(num_outputs);
  const std::string plural = num_outputs == 1 ? "" : "s";
''' + transform_expression + '''
  return msg;
}
int main(int argc, char** argv) {
  if (argc != 2) return 1;
  const int expected = std::atoi(argv[1]);
  if (expected < 0 || expected > 2) return 2;
  const char* const cases[][3] = {
''' + rows + '''
  };
  for (const auto& row : cases) {
    if (std::strcmp(pj_zh_localization::text(row[0], row[1], row[2]), row[expected]) != 0) return 3;
  }
  const char* const singular[] = {
    "function produced no output — declared 1 output, so it must return exactly 1 value per point",
    "函数未产生输出；已声明 1 个输出，因此每个点必须恰好返回 1 个值",
    "函式未產生輸出；已宣告 1 個輸出，因此每個點必須剛好傳回 1 個值"
  };
  const char* const plural[] = {
    "function produced no output — declared 2 outputs, so it must return exactly 2 values per point",
    "函数未产生输出；已声明 2 个输出，因此每个点必须恰好返回 2 个值",
    "函式未產生輸出；已宣告 2 個輸出，因此每個點必須剛好傳回 2 個值"
  };
  if (transformNoOutput(1) != singular[expected]) return 4;
  if (transformNoOutput(2) != plural[expected]) return 5;
  return 0;
}
''', encoding='utf-8')
        cls.compile(source, cls.corpus)

    @classmethod
    def compile(cls, source, output):
        """Compile without replacing compiler exception or character semantics."""
        if Path(cls.compiler[0]).name.lower() in ('cl', 'cl.exe'):
            flags = ['/nologo', '/std:c++20', '/EHsc', '/utf-8', '/W4', '/WX',
                     '/I' + str(PATCHES), str(source), '/Fe:' + str(output),
                     '/Fo:' + str(output.with_suffix('.obj'))]
        else:
            flags = ['-std=c++20', '-Wall', '-Wextra', '-Werror', '-pedantic',
                     '-I', str(PATCHES), str(source), '-o', str(output)]
        result = subprocess.run(cls.compiler + flags, cwd=cls.work, capture_output=True, text=True)
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)

    def test_language_selection_raw_payload_and_startup_snapshot(self):
        for value, expected, _ in LANGUAGES:
            with self.subTest(language=value):
                env = os.environ.copy()
                if value is None:
                    env.pop('PLOTJUGGLER_UI_LANGUAGE', None)
                else:
                    env['PLOTJUGGLER_UI_LANGUAGE'] = value
                result = subprocess.run([str(self.fixture), expected], env=env,
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_every_patched_display_literal_selects_the_expected_language(self):
        for value, _, expected_index in LANGUAGES:
            with self.subTest(language=value):
                env = os.environ.copy()
                if value is None:
                    env.pop('PLOTJUGGLER_UI_LANGUAGE', None)
                else:
                    env['PLOTJUGGLER_UI_LANGUAGE'] = value
                result = subprocess.run([str(self.corpus), str(expected_index)], env=env,
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
