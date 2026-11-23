#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Check actual localized characters against the fonts embedded in browser builds."""
from pathlib import Path
import unicodedata
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = ROOT / 'resources/fonts'
LATIN = FONT_DIR / 'PlotJugglerSans/PlotJugglerSans-Regular.ttf'
SC = FONT_DIR / 'NotoSansSC/NotoSansSC-Subset.otf'
SYMBOLS = FONT_DIR / 'NotoSansSymbols2/NotoSansSymbols2-Subset.ttf'


def required_codepoints(text: str) -> set[int]:
    # Layout controls do not need font glyphs. Check characters actually used,
    # not every unassigned codepoint in a broad punctuation range.
    return {ord(ch) for ch in text if unicodedata.category(ch) not in ('Cc', 'Cf')}


def check_coverage(text: str, covered: set[int]) -> None:
    missing = required_codepoints(text) - covered
    if missing:
        names = ', '.join(f'U+{cp:04X} {chr(cp)}' for cp in sorted(missing))
        raise ValueError(f'Missing catalog glyphs: {names}')


def active_catalog_text(path: Path) -> str:
    return ''.join(''.join(node.itertext()) for node in ET.parse(path).iter('translation')
                   if node.get('type') not in ('unfinished', 'obsolete', 'vanished'))


def font_cmap(path: Path) -> set[int]:
    from fontTools.ttLib import TTFont

    with TTFont(path) as font:
        return set(font.getBestCmap())


def main() -> int:
    latin, sc, symbols = (font_cmap(path) for path in (LATIN, SC, SYMBOLS))
    if not set(map(ord, '創擊補')) <= sc:
        raise ValueError('Noto Sans SC: missing traditional regression glyph(s) 創擊補')
    if 0x25B8 not in symbols or 0x25B8 in latin | sc:
        raise ValueError('U+25B8 must be provided uniquely by Noto Sans Symbols 2')
    covered = latin | sc | symbols
    for language in ('zh_CN', 'zh_TW'):
        catalog = ROOT / f'pj_app/translations/plotjuggler4_{language}.ts'
        text = active_catalog_text(catalog)
        ideographs = {cp for cp in required_codepoints(text)
                      if 0x3400 <= cp <= 0x9FFF or 0x20000 <= cp <= 0x3134F}
        if ideographs - sc:
            raise ValueError(f'{language}: Noto Sans SC missing ideographs {sorted(ideographs - sc)}')
        try:
            check_coverage(text, covered)
        except ValueError as error:
            raise ValueError(f'{language}: {error}') from error
        print(f'{language}: {len(required_codepoints(text))} actual translated codepoints covered')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
