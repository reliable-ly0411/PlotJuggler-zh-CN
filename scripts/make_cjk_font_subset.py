#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Regenerate the Chinese UI font embedded in the browser build.

The browser has no system font fallback, so the WebAssembly build embeds a
subset of Noto Sans SC: every character the zh_CN and zh_TW catalogs use, the 3,755
common GB2312 level-1 hanzi (so Chinese series and file names render too),
and CJK punctuation. Rerun after a catalog refresh adds new characters:

  python3 scripts/make_cjk_font_subset.py /path/to/NotoSansSC-Regular.otf

The source font is NotoSansSC-Regular.otf from
https://github.com/notofonts/noto-cjk (Sans/SubsetOTF/SC). Needs fontTools.

For the independently pinned U+25B8 fallback, supply the official v2.008 ZIP manually:
  python3 scripts/make_cjk_font_subset.py --symbols-release /path/to/NotoSansSymbols2-v2.008.zip
  python3 scripts/make_cjk_font_subset.py --symbols-release /path/to/NotoSansSymbols2-v2.008.zip --check

Symbols generation requires FontTools 4.61.1 and never downloads a font.
https://github.com/notofonts/symbols/releases/tag/NotoSansSymbols2-v2.008
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import xml.etree.ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
CATALOGS = [ROOT / f'pj_app/translations/plotjuggler4_{language}.ts' for language in ('zh_CN', 'zh_TW')]
OUTPUT = ROOT / 'resources/fonts/NotoSansSC/NotoSansSC-Subset.otf'

SYMBOL_OUTPUT = ROOT / 'resources/fonts/NotoSansSymbols2/NotoSansSymbols2-Subset.ttf'
SYMBOL_ARCHIVE_SHA256 = '346c930bbe8eb946701a05c54e9c11a2094dee1d93c387bf1771c0a3e335688f'
SYMBOL_DONOR = 'NotoSansSymbols2/googlefonts/ttf/NotoSansSymbols2-Regular.ttf'
SYMBOL_DONOR_SHA256 = '7d5fb73b7ca67a6798101741f5d280a3d016a56a197afcd4199dbb57b4b82a21'
SYMBOL_OUTPUT_SHA256 = 'af2c02d3aea7811b6096164cf83fb58a97182aeb71d3540070f154f79b7ea8b1'
SYMBOL_FONTTOOLS = '4.61.1'


def require_hash(data: bytes, expected: str, label: str) -> None:
    if sha256(data).hexdigest() != expected:
        raise ValueError(f'{label} does not match the pinned SHA-256')


def read_symbols_donor(archive: Path) -> bytes:
    zip_bytes = archive.read_bytes()
    require_hash(zip_bytes, SYMBOL_ARCHIVE_SHA256, 'Official Symbols ZIP')
    with ZipFile(BytesIO(zip_bytes)) as release:
        donor = release.read(SYMBOL_DONOR)
    require_hash(donor, SYMBOL_DONOR_SHA256, 'Official Symbols Regular TTF')
    return donor


def require_symbols_tool_version(actual: str) -> None:
    if actual != SYMBOL_FONTTOOLS:
        raise ValueError(f'Symbol generation requires FontTools {SYMBOL_FONTTOOLS}, got {actual}')


def symbols_font(archive: Path) -> bytes:
    from fontTools import subset, version

    require_symbols_tool_version(version)
    donor = read_symbols_donor(archive)
    options = subset.Options()
    options.layout_features = ['*']
    options.name_IDs = ['*']
    options.notdef_outline = True
    options.ignore_missing_unicodes = False
    font = subset.load_font(BytesIO(donor), options)
    subsetter = subset.Subsetter(options)
    subsetter.populate(unicodes=[0x25B8])
    subsetter.subset(font)
    result = BytesIO()
    subset.save_font(font, result, options)
    data = result.getvalue()
    require_hash(data, SYMBOL_OUTPUT_SHA256, 'Regenerated Symbols subset')
    return data


def gb2312_level1() -> str:
    """Rows 16-55 of GB2312 hold the 3,755 most common hanzi."""
    chars = []
    for row in range(0xB0, 0xD8):
        for cell in range(0xA1, 0xFF):
            try:
                chars.append(bytes((row, cell)).decode('gb2312'))
            except UnicodeDecodeError:
                pass
    return ''.join(chars)


def catalog_text() -> str:
    return ''.join(''.join(t.itertext()) for catalog in CATALOGS
                   for t in ET.parse(catalog).getroot().iter('translation'))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('source', nargs='?', type=Path, help='NotoSansSC-Regular.otf')
    parser.add_argument('--symbols-release', type=Path, help='local official NotoSansSymbols2 v2.008 ZIP')
    parser.add_argument('--check', action='store_true', help='verify the tracked Symbols subset without writing')
    args = parser.parse_args()
    if (args.source is None) == (args.symbols_release is None):
        parser.error('provide either NotoSansSC-Regular.otf or --symbols-release, not both')
    if args.check and args.symbols_release is None:
        parser.error('--check requires --symbols-release')
    if args.symbols_release is not None:
        try:
            data = symbols_font(args.symbols_release)
            if args.check:
                require_hash(SYMBOL_OUTPUT.read_bytes(), SYMBOL_OUTPUT_SHA256, 'Tracked Symbols subset')
            else:
                SYMBOL_OUTPUT.write_bytes(data)
        except (OSError, ValueError, ImportError) as error:
            parser.error(str(error))
        print(f'{SYMBOL_OUTPUT.relative_to(ROOT)}: U+25B8, {len(data)} bytes; pinned SHA-256 verified')
        return 0
    from fontTools import subset

    punctuation = ''.join(map(chr, range(0x3000, 0x3040))) + ''.join(map(chr, range(0xFF00, 0xFFF0))) + '“”‘’…—·'
    text = set(catalog_text() + gb2312_level1() + punctuation + '中文简体繁體')
    # Latin comes from the bundled PlotJuggler Sans, first in the family list.
    text = ''.join(sorted(c for c in text if ord(c) > 0x7F))
    options = subset.Options()
    options.layout_features = ['*']
    options.name_IDs = ['*']
    options.notdef_outline = True
    font = subset.load_font(str(args.source), options)
    subsetter = subset.Subsetter(options)
    subsetter.populate(text=text)
    subsetter.subset(font)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    subset.save_font(font, str(OUTPUT), options)
    print(f'{OUTPUT.relative_to(ROOT)}: {len(text)} characters, {OUTPUT.stat().st_size} bytes')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
