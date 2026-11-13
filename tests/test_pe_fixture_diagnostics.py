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
    def test_malformed_rejected(self):
        for raw in (b'',b'MZ',fixture()[:-1]):
            with self.assertRaises(ValueError):pe.inspect_pe(raw)

if __name__=='__main__':unittest.main()
