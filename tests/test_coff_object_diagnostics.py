"""Synthetic parser/negative tests, never normalization of production objects."""
import importlib.util
from pathlib import Path
import struct
import unittest

spec=importlib.util.spec_from_file_location('coff',Path(__file__).resolve().parents[1]/'scripts/coff_object_diagnostics.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)


def fixture(payload=b'abc',timestamp=1,big=False):
    if big:
        header=struct.pack('<HHHHI',0,65535,2,0x8664,timestamp)+bytes.fromhex('c7a1bad1eebaa94baf20faf66aa4dcb8')+struct.pack('<IIIIIII',0,0,0,0,1,0,0)
    else:header=struct.pack('<HHIIIHH',0x8664,1,timestamp,0,0,0,0)
    section=b'.text\0\0\0'+struct.pack('<IIIIIIHHI',0,0,len(payload),len(header)+40,0,0,0,0,0x60000020)
    return header+section+payload


class CoffTests(unittest.TestCase):
    def test_codeview_object_name_precise_record(self):
        name=b'D:/runner/cache-a/main.obj\0'
        symbol=struct.pack('<HHI',6+len(name),0x1101,0)+name
        body=struct.pack('<III',4,0xf1,len(symbol))+symbol
        body+=b'\0'*((-len(body))%4)
        info=c.codeview_objects(body,100)
        self.assertEqual(info[0]['record_offset'],112)
        self.assertEqual(info[0]['name_offset'],120)
        self.assertEqual(info[0]['object_name'],'D:/runner/cache-a/main.obj')
        malformed=body[:12]+struct.pack('<H',65535)+body[14:]
        with self.assertRaises(ValueError):c.codeview_objects(malformed,100)

    def test_standard_and_bigobj(self):
        for big in (False,True):
            raw=fixture(big=big);d=c.inspect_object(raw)
            self.assertEqual(d['sections'][0]['name'],'.text')
            self.assertEqual(d['sections'][0]['sha256'],c.sha(b'abc'))
            self.assertEqual(d['sha256'],c.sha(raw))
            self.assertEqual(d['format'],'bigobj' if big else 'coff')
    def test_raw_timestamp_difference_remains_failure(self):
        d=c.compare_objects(fixture(timestamp=1),fixture(timestamp=2))
        self.assertFalse(d['equal']);self.assertIn('timestamp',d['changed_header_or_tables'])
        self.assertEqual(d['changed_sections'],[])
        self.assertEqual(d['differing_ranges'],[{'offset':4,'bytes':1}])
    def test_section_bytes_difference_without_mask(self):
        d=c.compare_objects(fixture(b'abc'),fixture(b'abd'))
        self.assertFalse(d['equal']);self.assertEqual(len(d['changed_sections']),1)
        self.assertEqual(d['differing_ranges'][0]['offset'],62)
    def test_path_evidence_has_offsets_and_raw_hash(self):
        payload=b'\0/pathmap:D:/runner/cache=Z:/pj-conan\0'
        raw=fixture(payload);d=c.inspect_object(raw)
        self.assertEqual(d['path_strings_count'],1)
        self.assertEqual(d['path_strings'][0]['offset'],61)
        self.assertEqual(d['sha256'],c.sha(raw))
    def test_truncated_bad_machine_and_executable_rejected(self):
        cases=[b'',fixture()[:-1]]
        for offset,value in [(0,0),(16,4)]:
            raw=bytearray(fixture());struct.pack_into('<H',raw,offset,value);cases.append(bytes(raw))
        for raw in cases:
            with self.assertRaises(ValueError):c.inspect_object(raw)
    def test_unsupported_bigobj_signature_rejected(self):
        raw=bytearray(fixture(big=True));raw[12]=0
        with self.assertRaises(ValueError):c.inspect_object(raw)
    def test_bad_symbol_and_section_pointer_rejected(self):
        raw=bytearray(fixture());struct.pack_into('<II',raw,8,1000,1)
        with self.assertRaises(ValueError):c.inspect_object(raw)
        raw=bytearray(fixture());struct.pack_into('<I',raw,40,1000)
        with self.assertRaises(ValueError):c.inspect_object(raw)

if __name__=='__main__':unittest.main()
