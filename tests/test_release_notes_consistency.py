#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Keep current release prose synchronized with catalogs and pinned payload scope."""
import ast
import json
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


class ReleaseNotesConsistencyTest(unittest.TestCase):
    def setUp(self):
        self.versions = dict(line.split('=', 1) for line in
                             (ROOT / 'versions.env').read_text(encoding='utf-8').splitlines()
                             if line and not line.startswith('#'))
        self.notes = (ROOT / 'docs/localization' /
                      ('RELEASE-' + self.versions['PJ_APP_VERSION'] + '.md')).read_text(encoding='utf-8')
        self.readme = (ROOT / 'docs/localization/README.zh-CN.md').read_text(encoding='utf-8')
        self.lock = json.loads((ROOT / 'packaging/localization/plugin-patches/source-lock.json')
                               .read_text(encoding='utf-8'))

    def test_catalog_counts_are_current(self):
        root = ET.parse(ROOT / 'pj_app/translations/plotjuggler4_zh_CN.ts').getroot()
        active = [m for m in root.findall('.//message') if
                  m.find('translation') is not None and
                  m.find('translation').get('type') not in ('obsolete', 'vanished')]
        # Published release notes describe immutable rc.2 bytes, not later development.
        # Keep their historical coverage number; the development README tracks source.
        for text in [self.readme]:
            match = re.search(r'([\d,]+) 条\s*(?:Qt 可提取消息|已提取 Qt 消息)', text)
            self.assertIsNotNone(match)
            self.assertEqual(int(match.group(1).replace(',', '')), len(active))

    def test_rebuilt_plugin_list_matches_active_source_lock(self):
        line = next(line for line in self.notes.splitlines() if '本版汉化重建集合共' in line)
        self.assertEqual(set(re.findall(r'`([a-z0-9-]+)`', line)),
                         {item['id'] for item in self.lock['plugins']})
        counts = list(map(int, re.findall(r'\d+', line)))
        self.assertEqual(counts, [len(self.lock['plugins']),
                                 sum('Windows' in x['platforms'] for x in self.lock['plugins']),
                                 sum('Linux' in x['platforms'] for x in self.lock['plugins'])])
        self.assertNotIn('toolbox-mosaico', {x['id'] for x in self.lock['plugins']})
        self.assertIn('Mosaico 1.3.0 明确保留官方原始二进制', self.notes)

    def test_packaged_plugin_counts_match_staging(self):
        source = (ROOT / 'packaging/localization/prepare_payload.py').read_text(encoding='utf-8')
        tree = ast.parse(source)
        core = next(ast.literal_eval(node.value) for node in tree.body
                    if isinstance(node, ast.Assign) and
                    any(isinstance(t, ast.Name) and t.id == 'CORE_PLUGINS' for t in node.targets))
        # These are the explicit Linux-only additions in the staging recipe.
        self.assertIn("['toolbox-assistant-agent', 'ros2-topic-subscriber'] if linux_tools else []", source)
        self.assertIn(f'Windows 包含 {len(core)} 个官方插件和 BIN', self.notes)
        self.assertIn(f'Linux 包含 {len(core) + 2} 个官方插件和 BIN', self.notes)
        self.assertIn(f'{len(core) + 1} 个插件', self.notes)
        self.assertIn(f'{len(core) + 3} 个插件的包内清单', self.notes)
        self.assertIn(f'实际加载其中 {len(core) + 2} 个', self.notes)
        fixture_verifier = (ROOT / 'packaging/localization/verify_package.py').read_text(encoding='utf-8')
        series = re.search(r'ArduPilot BIN: imported (\d+) numeric series', fixture_verifier)
        self.assertIsNotNone(series)
        self.assertIn(format(int(series.group(1)), ',') + ' 条数值序列', self.notes)

    def test_platform_and_source_boundaries_are_explicit(self):
        self.assertIn('Windows 未进行人工可见桌面目视验收', self.notes)
        self.assertIn('Qt ' + self.versions['PJ_QT_VERSION'], self.notes)
        for sdk in {x['sdk'] for x in self.lock['plugins']}:
            self.assertIn(sdk, self.notes)
        self.assertIn('上游 4.0.0 发布说明（全文）', self.notes)
        for placeholder in ['SOURCE_SHA', 'SOURCE_TREE', 'RUN_ID', 'RUN_URL', 'ASSET_TABLE']:
            self.assertIn('@' + placeholder + '@', self.notes)
        self.assertIn('不设置为 Latest', self.notes)
        self.assertIn('旧标签及原包保持不变', self.notes)


if __name__ == '__main__':
    unittest.main()
