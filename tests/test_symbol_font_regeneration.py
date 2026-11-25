#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Scoped offline regression for the manually regenerated WASM symbol subset."""
from hashlib import sha256
import importlib.util
from io import BytesIO
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch
from zipfile import ZipFile

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

    def test_reference_subset_has_pinned_size_and_sha256(self):
        self.assertEqual(len(self.reference), 6024)
        self.assertEqual(sha256(self.reference).hexdigest(), GEN.SYMBOL_OUTPUT_SHA256)

    def test_unsupported_tool_version_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "requires FontTools 4.61.1"):
            GEN.require_symbols_tool_version("1.0.0")

    def test_wrong_archive_and_donor_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "fixture.zip"
            archive.write_bytes(self.fixture)
            with self.assertRaisesRegex(ValueError, "Official Symbols ZIP"):
                GEN.read_symbols_donor(archive)
            with patch.object(GEN, "SYMBOL_ARCHIVE_SHA256", sha256(self.fixture).hexdigest()):
                with self.assertRaisesRegex(ValueError, "Official Symbols Regular TTF"):
                    GEN.read_symbols_donor(archive)


    def test_selects_only_the_exact_zip_member(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "fixture.zip"
            archive.write_bytes(self.fixture)
            with patch.object(GEN, "SYMBOL_ARCHIVE_SHA256", sha256(self.fixture).hexdigest()), \
                 patch.object(GEN, "SYMBOL_DONOR_SHA256", sha256(self.reference).hexdigest()):
                self.assertEqual(GEN.read_symbols_donor(archive), self.reference)


if __name__ == "__main__":
    if "--fonttools" in sys.argv:
        sys.argv.remove("--fonttools")

        class SymbolsFontToolsTest(unittest.TestCase):
            setUp = SymbolsRegenerationTest.setUp
            # This class exists only for the explicit dedicated invocation.
            # Ordinary unittest discovery runs the stdlib tests above.
            def test_regeneration_uses_real_fonttools_and_exact_options(self):
                from fontTools.ttLib import TTFont
                self.assertEqual(TTFont(BytesIO(self.reference)).getBestCmap(), {0x25B8: "uni25B8"})
                with tempfile.TemporaryDirectory() as directory:
                    archive = Path(directory) / "fixture.zip"
                    archive.write_bytes(self.fixture)
                    with patch.object(GEN, "SYMBOL_ARCHIVE_SHA256", sha256(self.fixture).hexdigest()), \
                         patch.object(GEN, "SYMBOL_DONOR_SHA256", sha256(self.reference).hexdigest()):
                        self.assertEqual(GEN.symbols_font(archive), self.reference)
                        with patch.object(GEN, "SYMBOL_OUTPUT_SHA256", "0" * 64):
                            with self.assertRaisesRegex(ValueError, "Regenerated Symbols subset"):
                                GEN.symbols_font(archive)

    unittest.main()
