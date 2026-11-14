import copy, hashlib, json, os, struct, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import linux_public_elf as elf
import package_privacy as privacy

STAGE=Path(os.environ['PLOTJUGGLER_REVIEW_STAGE']) if os.environ.get('PLOTJUGGLER_REVIEW_STAGE') else None
NAMES=('lib/libgnutls.so.30','lib/libpython3.12.so.1.0')

class SyntheticLinux(unittest.TestCase):
 def test_pinned_span_and_unrelated_path(self):
  b=bytearray(1024);b[:7]=b'\x7fELF\x02\x01\x01'
  struct.pack_into('<HH',b,16,3,62);struct.pack_into('<Q',b,32,64);struct.pack_into('<HH',b,54,56,2)
  struct.pack_into('<IIQQQQQQ',b,64,1,0,0,0x400000,0,len(b),len(b),0)
  struct.pack_into('<IIQQQQQQ',b,120,2,0,256,0,0,64,64,0)
  for i,(tag,value) in enumerate(((5,0x400180),(10,32),(14,1),(0,0))):struct.pack_into('<qQ',b,256+i*16,tag,value)
  b[384:399]=b'\0libexample.so\0'
  record=b'example C:\\Users\\SampleUser\\file';start=512;end=start+len(record);b[start:end]=record
  m=privacy.PRIVATE_PATH.search(record.decode('latin1'));self.assertIsNotNone(m)
  name='lib/libexample.so'
  entry={'elf_sha256':hashlib.sha256(b).hexdigest(),'soname':'libexample.so','source':'synthetic','nul_records':[{'rule':'private_path','start':start,'end':end,'match_start':start+m.start(),'match_end':start+m.end(),'record_sha256':hashlib.sha256(record).hexdigest()}]}
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'manifest.json'
   def pin():
    p.write_text(json.dumps({'records':{name:entry}}));return hashlib.sha256(p.read_bytes()).hexdigest()
   with patch.object(elf,'MANIFEST',p):
    with patch.object(elf,'MANIFEST_SHA256',pin()):self.assertEqual(len(privacy.check_metadata(bytes(b),name,{})),1)
    # Re-pin the changed synthetic ELF to prove unrelated records still scan.
    b.extend(b'\0C:\\Users\\PrivateUser\\secret\0');entry['elf_sha256']=hashlib.sha256(b).hexdigest()
    with patch.object(elf,'MANIFEST_SHA256',pin()):
     with self.assertRaises(ValueError):privacy.check_metadata(bytes(b),name,{})

@unittest.skipUnless(STAGE and all((STAGE/n).is_file() for n in NAMES), 'Set PLOTJUGGLER_REVIEW_STAGE to the reviewed stage')
class PinnedLinux(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.data={n:(STAGE/n).read_bytes() for n in NAMES}
  cls.records=privacy.load_public_records()
  cls.manifest=json.loads(elf.MANIFEST.read_bytes())
 def reject(self,data,name):
  with self.assertRaises(ValueError): privacy.check_metadata(data,name,self.records)
 def test_actual_original_positive(self):
  for name in NAMES:
   with self.subTest(name=name):
    m=privacy.check_metadata(self.data[name],name,self.records)
    self.assertEqual(len(m),6 if 'gnutls' in name else 2)
 def test_mutate_arbitrary_byte_or_hash(self):
  for name in NAMES:
   b=bytearray(self.data[name]);b[-1]^=1
   with self.subTest(name=name): self.reject(bytes(b),name)
 def test_append_secrets_paths_contacts(self):
  additions=[b'\0'+(b'ghp_'+b'a'*36)+b'\0',b'\0C:\\Users\\PrivateUser\\flight.log\0',b'\0'+(b'private'+b'@qq.com')+b'\0',b'\0'+b'-----BEGIN PRIVATE KEY-----\n'+b'A'*80+b'\n-----END PRIVATE KEY-----\0']
  for name in NAMES:
   spans=elf.reviewed_spans(self.data[name],name)
   for add in additions:
    data=self.data[name]+add
    with self.subTest(name=name,kind=add[:12]):
     self.reject(data,name)
     # Even if identity were independently trusted, only the existing exact
     # spans may be classified; all unrelated content must still fail.
     with patch.object(privacy,'reviewed_spans',return_value=spans): self.reject(data,name)
 def test_basename_and_version(self):
  for name in NAMES:
   for renamed in (name+'.new',name.replace('lib/','other/'),name.replace('.so.', '.so.999')):
    with self.subTest(name=renamed): self.reject(self.data[name],renamed)
 def test_source_range_arch_soname_hash_and_label_manifest_tampering(self):
  for name in NAMES:
   for field,value in [('source','https://invalid.example/mismatch'),('architecture','arm64'),('soname','different.so'),('elf_sha256','0'*64),('label','changed')]:
    m=copy.deepcopy(self.manifest);m['records'][name][field]=value
    self.assert_manifest_rejected(m,name)
   for field in ('start','end','match_start','match_end'):
    m=copy.deepcopy(self.manifest);m['records'][name]['nul_records'][0][field]+=1
    self.assert_manifest_rejected(m,name)
   m=copy.deepcopy(self.manifest);m['records'][name]['nul_records'][0]['record_sha256']='0'*64
   self.assert_manifest_rejected(m,name)
 def assert_manifest_rejected(self,m,name):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'manifest.json';path.write_text(json.dumps(m))
   with patch.object(elf,'MANIFEST',path): self.reject(self.data[name],name)
 def test_identity_checks_independently(self):
  for name in NAMES:
   self.assertEqual(elf._soname(self.data[name]),name.split('/')[-1])
   for offset in (4,5,16,18):
    b=bytearray(self.data[name]);b[offset]^=1
    with self.subTest(name=name,offset=offset):self.assertIsNone(elf._soname(bytes(b)))
 def test_original_policy_still_fails(self):
  for name in NAMES:
   with patch.object(privacy,'reviewed_spans',return_value=set()): self.reject(self.data[name],name)
if __name__=='__main__': unittest.main(verbosity=2)
