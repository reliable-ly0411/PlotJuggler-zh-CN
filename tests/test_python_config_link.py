# SPDX-License-Identifier: MPL-2.0
"""Synthetic ELF-header policy tests plus a real host ELF/SONAME probe."""
import importlib.util
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('links',ROOT/'scripts/normalize_python_config_link.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class ConfigLinks(unittest.TestCase):
    def fixture(self, root, triple):
        lib=root/'usr/lib'/m.LIBRARY;lib.parent.mkdir(parents=True)
        header=bytearray(20);header[:7]=b'\x7fELF\x02\x01\x01';header[16:18]=(3).to_bytes(2,'little')
        header[18:20]=m.LAYOUTS[triple][0].to_bytes(2,'little');lib.write_bytes(header)
        config=lib.parent/'python3.10'/('config-3.10-'+triple);config.mkdir(parents=True)
        link=config/'libpython3.10.so';link.symlink_to('../../'+triple+'/libpython3.10.so.1')
        (config/'Makefile').write_text('retained sysconfig')
        return lib,link
    def test_known_layouts_and_idempotence(self):
        for triple in m.LAYOUTS:
            with self.subTest(triple=triple),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);lib,link=self.fixture(root,triple)
                with patch.object(m.subprocess,'check_output',return_value='(SONAME) Library soname: ['+m.LIBRARY+']'):
                    self.assertTrue(m.normalize(root)['changed']);self.assertFalse(m.normalize(root)['changed'])
                self.assertEqual(link.resolve(),lib);self.assertEqual((link.parent/'Makefile').read_text(),'retained sysconfig')
    def test_reject_without_changing_link(self):
        for failure in ['missing','nonelf','machine','soname','unknown','escape','target_symlink']:
            with self.subTest(failure=failure),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);lib,link=self.fixture(root,'x86_64-linux-gnu')
                if failure=='missing':lib.unlink()
                if failure=='nonelf':lib.write_bytes(b'not ELF')
                if failure=='machine':
                    b=bytearray(lib.read_bytes());b[18:20]=(183).to_bytes(2,'little');lib.write_bytes(b)
                if failure in ['unknown','escape']:
                    link.unlink();link.symlink_to('other.so' if failure=='unknown' else '/etc/passwd')
                if failure=='target_symlink':lib.unlink();lib.symlink_to('/etc/passwd')
                old=link.readlink()
                soname='wrong.so' if failure=='soname' else m.LIBRARY
                with patch.object(m.subprocess,'check_output',return_value='(SONAME) ['+soname+']'):
                    with self.assertRaises(ValueError):m.normalize(root)
                self.assertEqual(link.readlink(),old)
    def test_real_elf_soname(self):
        machine={'x86_64':62,'aarch64':183}.get(platform.machine())
        if machine is None or not shutil.which('cc') or not shutil.which('readelf'):
            self.fail('real native ELF compiler/readelf unavailable')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'probe.c';source.write_text('int probe(void){return 0;}')
            library=root/'probe.so'
            subprocess.run(['cc','-shared','-fPIC',str(source),'-Wl,-soname,'+m.LIBRARY,'-o',str(library)],check=True)
            m.verify_elf(library,machine)
            with self.assertRaises(ValueError):m.verify_elf(library,183 if machine==62 else 62)

if __name__=='__main__':unittest.main()
