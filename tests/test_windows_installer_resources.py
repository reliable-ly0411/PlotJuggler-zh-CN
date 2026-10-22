#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Cross-platform unit checks, not the Windows integration result."""
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ifw_smoke', ROOT / 'scripts/verify_windows_installer_resources.py')
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


class InstallerResourceSmokeTests(unittest.TestCase):
    def test_stage_real_metadata_and_only_synthetic_payload(self):
        with tempfile.TemporaryDirectory(prefix='smoke space ') as directory:
            config, packages, meta, translations, qrc = smoke.stage_inputs(ROOT, Path(directory))
            self.assertNotIn('__PJ_', config.read_text(encoding='utf-8'))
            self.assertNotIn('__PJ_', (meta / 'package.xml').read_text(encoding='utf-8'))
            original = ROOT / 'packaging/installer/packages/io.plotjuggler.application/meta'
            for name in ('installscript.qs', 'targetwidget.ui', 'languagewidget.ui', 'zh_CN.ts'):
                self.assertEqual((meta / name).read_bytes(), (original / name).read_bytes())
            self.assertEqual([p.name for p in (meta.parent / 'data').iterdir()],
                             ['SYNTHETIC-NOT-AN-APPLICATION.txt'])
            group = ET.parse(qrc).getroot().find('qresource')
            self.assertEqual(group.attrib['prefix'], '/translations_new')
            self.assertEqual([e.text for e in group], ['ifw_zh_CN.qm', 'qt_zh_CN.qm', smoke.MARKER])

    def test_missing_embedded_resource_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fixture.exe'
            content = bytearray(128)
            content[:2] = b'MZ'
            struct.pack_into('<I', content, 0x3c, 64)
            content[64:68] = b'PE\0\0'
            path.write_bytes(content)
            with self.assertRaisesRegex(ValueError, 'resource name missing'):
                smoke.verify_pe_resources(path)
            for name in ('ifw_zh_CN.qm', 'qt_zh_CN.qm', smoke.MARKER):
                content += name.encode('utf-16-be')
            path.write_bytes(content)
            smoke.verify_pe_resources(path)

    def test_non_pe_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'not-pe.exe'
            path.write_bytes(b'not a PE file')
            with self.assertRaisesRegex(ValueError, 'not a PE'):
                smoke.verify_pe_resources(path)


if __name__ == '__main__':
    unittest.main()
