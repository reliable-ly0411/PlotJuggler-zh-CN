#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Scoped offline regression for the manually regenerated WASM symbol subset."""
from hashlib import sha256
import importlib.util
from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("make_cjk_font_subset", ROOT / "scripts/make_cjk_font_subset.py")
GEN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GEN)


class SymbolsRegenerationTest(unittest.TestCase):
    def setUp(self):
        self.reference = GEN.SYMBOL_OUTPUT.read_bytes()
        # This stand-in cannot prove provenance; the independent official-donor
        # check exercises the real advertised ZIP and hashes.
        buf = BytesIO()
        with ZipFile(buf, "w") as release:
            release.writestr(GEN.SYMBOL_DONOR, self.reference)
        self.fixture = buf.getvalue()

    def test_reference_subset_is_exact_and_contains_only_expected_glyph(self):
        self.assertEqual(len(self.reference), 6024)
        self.assertEqual(sha256(self.reference).hexdigest(), GEN.SYMBOL_OUTPUT_SHA256)
        self.assertEqual(TTFont(BytesIO(self.reference)).getBestCmap(), {0x25B8: "uni25B8"})

    def test_unsupported_tool_version_is_rejected_without_reading(self):
        with patch.object(GEN, "fonttools_version", "1.0.0"):
            with self.assertRaisesRegex(ValueError, "requires FontTools 4.61.1"):
                GEN.symbols_font(Path("missing.zip"))

    def test_wrong_archive_and_donor_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "fixture.zip"
            archive.write_bytes(self.fixture)
            with self.assertRaisesRegex(ValueError, "Official Symbols ZIP"):
                GEN.symbols_font(archive)
            with patch.object(GEN, "SYMBOL_ARCHIVE_SHA256", sha256(self.fixture).hexdigest()):
                with self.assertRaisesRegex(ValueError, "Official Symbols Regular TTF"):
                    GEN.symbols_font(archive)

    def test_regeneration_uses_exact_options_and_fails_if_output_hash_differs(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "fixture.zip"
            archive.write_bytes(self.fixture)
            with patch.object(GEN, "SYMBOL_ARCHIVE_SHA256", sha256(self.fixture).hexdigest()), \
                 patch.object(GEN, "SYMBOL_DONOR_SHA256", sha256(self.reference).hexdigest()):
                self.assertEqual(GEN.symbols_font(archive), self.reference)
                with patch.object(GEN, "SYMBOL_OUTPUT_SHA256", "0" * 64):
                    with self.assertRaisesRegex(ValueError, "Regenerated Symbols subset"):
                        GEN.symbols_font(archive)


if __name__ == "__main__":
    unittest.main()
