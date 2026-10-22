# SPDX-License-Identifier: MPL-2.0
"""Repository UTF-8 text contracts; binary identities are deliberately untouched."""
import ast
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class TextEncodingTest(unittest.TestCase):
    def test_release_and_acceptance_text_io_declares_encoding(self):
        files = list((ROOT / 'packaging/localization').glob('*.py')) + list((ROOT / 'tests').glob('*.py')) + list((ROOT / '.github/release_policy').glob('*.py'))
        missing = []
        for path in files:
            for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and node.func.attr in ('read_text', 'write_text')
                        and not any(k.arg == 'encoding' for k in node.keywords)):
                    missing.append(f'{path.relative_to(ROOT)}:{node.lineno}')
        self.assertEqual(missing, [])

    def test_installer_templates_survive_non_utf8_default(self):
        original = Path.open
        def legacy_open(path, mode='r', buffering=-1, encoding=None, errors=None, newline=None):
            if 'b' not in mode and encoding in (None, 'locale'):
                encoding = 'cp1252'
            return original(path, mode, buffering, encoding, errors, newline)
        with patch.object(Path, 'open', legacy_open):
            script = (ROOT / 'packaging/installer/packages/io.plotjuggler.application/meta/installscript.qs').read_text(encoding='utf-8')
            self.assertIn('Existing installation detected —', script)
            with tempfile.TemporaryDirectory(prefix='pj-encoding-') as directory:
                target = Path(directory) / 'unicode.json'
                value = '中文 %1 — path [fixture]'
                target.write_text(value, encoding='utf-8')
                self.assertEqual(target.read_bytes(), value.encode('utf-8'))
                self.assertNotEqual(target.read_text(encoding='locale'), value)
                self.assertEqual(target.read_text(encoding='utf-8'), value)


if __name__ == '__main__':
    unittest.main()
