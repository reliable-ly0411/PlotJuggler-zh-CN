"""Validate original meme provenance and resource integrity, not visual quality."""
import hashlib
import json
from pathlib import Path
import struct
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
MEMES = ROOT / 'resources/memes'


class OriginalMemeCatalogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads((MEMES / 'zh_CN.json').read_text(encoding='utf-8'))
        cls.images = cls.catalog['images']
        cls.aliases = {x.get('alias') for x in ET.parse(ROOT / 'resources/resources.qrc').iter('file')}

    def test_exact_original_slots(self):
        self.assertEqual([e['id'] for e in self.images], list(range(1, 38)))
        self.assertEqual(len(list(MEMES.glob('meme_*.jpg'))), 37)

    def test_original_source_hashes(self):
        for e in self.images:
            with self.subTest(id=e['id']):
                source = (MEMES / f"meme_{e['id']:02}.jpg").read_bytes()
                self.assertEqual(hashlib.sha256(source).hexdigest(), e['original_sha256'])

    def test_variants_are_packaged_and_bounded(self):
        for e in self.images:
            variant = e.get('variant', {})
            files = [variant['image']] if 'image' in variant else [p['file'] for p in variant.get('patches', [])]
            for file in files:
                with self.subTest(id=e['id'], file=file):
                    self.assertIn('memes/' + file, self.aliases)
                    data = (MEMES / file).read_bytes()
                    self.assertEqual(data[:8], b'\x89PNG\r\n\x1a\n')
                    width, height = struct.unpack('>II', data[16:24])
                    self.assertTrue(0 < width <= 8192 and 0 < height <= 8192)
                    self.assertLessEqual(width * height, 16 * 1024 * 1024)
            if 'patches' in variant:
                w, h = variant['canvas']
                for patch in variant['patches']:
                    x, y, pw, ph = patch['source']
                    sw, sh = struct.unpack('>II', (MEMES / patch['file']).read_bytes()[16:24])
                    dx, dy = patch['at']
                    self.assertTrue(0 <= x < x + pw <= sw and 0 <= y < y + ph <= sh)
                    self.assertTrue(0 <= dx < dx + pw <= w and 0 <= dy < dy + ph <= h)

    def test_reviewed_slots_have_asset_or_technical_exception(self):
        for e in self.images:
            if e['pixel_review'].startswith('passed'):
                self.assertTrue(e.get('variant') or e['localization_status'] == 'original-technical-labels')
            if e['localization_status'] in ('pending', 'unavailable'):
                self.assertFalse(e['pixel_review'].startswith('passed'))
                self.assertFalse(e.get('variant'))


if __name__ == '__main__':
    unittest.main()
