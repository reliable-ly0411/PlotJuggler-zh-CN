import importlib.util
from pathlib import Path
import struct
import unittest
spec=importlib.util.spec_from_file_location('pe',Path(__file__).resolve().parents[1]/'scripts/pe_fixture_diagnostics.py')
pe=importlib.util.module_from_spec(spec);spec.loader.exec_module(pe)


def fixture(payload=b'code'):
    data=bytearray(128+len(payload));data[:2]=b'MZ';struct.pack_into('<I',data,60,64)
    data[64:68]=b'PE\0\0';struct.pack_into('<HHIIIHH',data,68,0x8664,1,123,0,0,0,0x2000)
    data[88:96]=b'.rdata\0\0';struct.pack_into('<II',data,104,len(payload),128)
    data[128:]=payload
    return bytes(data)

class PETests(unittest.TestCase):
    def test_raw_hash_and_sections_no_rewrite(self):
        raw=fixture();result=pe.inspect_pe(raw)
        self.assertEqual(result['sections'][0]['name'],'.rdata')
        self.assertFalse(result['byte_rewriting'])
        self.assertNotEqual(result['sha256'],pe.inspect_pe(fixture(b'other'))['sha256'])
    def test_privacy_separator_and_utf16_detection(self):
        result=pe.inspect_pe(fixture('D:/cache/a.obj'.encode('utf-16le')),['D:\\cache'],['D:\\cache\\a.obj'])
        self.assertEqual(result['forbidden_paths_found'],['D:\\cache'])
        self.assertEqual(result['object_names_found'],['D:\\cache\\a.obj'])
    def test_absent_object_name_is_not_claim_of_debug_removal(self):
        self.assertEqual(pe.inspect_pe(fixture(),object_names=['x.obj'])['object_names_found'],[])
    def test_export_and_debug_timestamps_are_read_without_masking(self):
        raw=bytearray(640);raw[:2]=b'MZ';struct.pack_into('<I',raw,60,64)
        raw[64:68]=b'PE\0\0';struct.pack_into('<HHIIIHH',raw,68,0x8664,1,123,0,0,240,0x2000)
        struct.pack_into('<H',raw,88,0x20b);struct.pack_into('<I',raw,196,16)
        struct.pack_into('<II',raw,200,0x1000,40)
        struct.pack_into('<II',raw,248,0x1080,28)
        raw[328:336]=b'.rdata\0\0';struct.pack_into('<IIII',raw,336,256,0x1000,256,384)
        struct.pack_into('<I',raw,408,1);struct.pack_into('<I',raw,416,0x1040)
        struct.pack_into('<I',raw,448,0x1050);raw[464:479]=b'exported_paths\0'
        struct.pack_into('<I',raw,516,456);struct.pack_into('<I',raw,524,13)
        before=bytes(raw);result=pe.inspect_pe(raw)
        self.assertEqual(result['exports'],['exported_paths'])
        self.assertEqual(result['debug_directory'],[{'timestamp':456,'timestamp_offset':516,'type':13}])
        self.assertEqual(result['timestamp'],123)
        self.assertEqual(bytes(raw),before)

    def test_malformed_rejected(self):
        for raw in (b'',b'MZ',fixture()[:-1]):
            with self.assertRaises(ValueError):pe.inspect_pe(raw)

if __name__=='__main__':unittest.main()
