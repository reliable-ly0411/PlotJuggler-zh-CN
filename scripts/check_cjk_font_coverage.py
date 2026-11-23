#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Check that both Chinese catalogs have embedded CJK glyph coverage."""
from pathlib import Path
import xml.etree.ElementTree as ET
from fontTools.ttLib import TTFont
ROOT = Path(__file__).resolve().parents[1]
cmap = TTFont(ROOT / 'resources/fonts/NotoSansSC/NotoSansSC-Subset.otf').getBestCmap()
with TTFont(ROOT / 'resources/fonts/NotoSansSymbols2/NotoSansSymbols2-Subset.ttf') as symbols:
    assert 0x25B8 in symbols.getBestCmap(), 'Noto Sans Symbols 2: missing U+25B8 menu separator'
for language in ('zh_CN', 'zh_TW'):
    catalog = ROOT / f'pj_app/translations/plotjuggler4_{language}.ts'
    text = ''.join(''.join(t.itertext()) for t in ET.parse(catalog).iter('translation'))
    ideographs = {c for c in text if 0x3400 <= ord(c) <= 0x9fff or 0x20000 <= ord(c) <= 0x3134f}
    missing = sorted(c for c in ideographs if ord(c) not in cmap)
    assert not missing, f'{language}: missing {missing}'
    print(f'{language}: {len(ideographs)} unique CJK glyphs covered')
