# SPDX-License-Identifier: MPL-2.0
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
BASE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('diag', BASE/'scripts/windows/collect_failed_config_diagnostics.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
  self.base=Path(self.tmp.name); self.root=self.base/'root'; self.out=self.base/'output'
  self.p=self.root/'b/native-kit/codemodel/process'; self.p.mkdir(parents=True)
  self.data=b'CMake Error: Unknown CMake command SECRET\npassword=SECRET'
  (self.p/'configure.stderr.bin').write_bytes(self.data)
  self.receipt={'source_sha':'a'*40,'source_tree':'b'*40,'exit_code':1,'argv':['PRIVATE'], 'stderr_sha256':hashlib.sha256(self.data).hexdigest()}
  self.write()
 def write(self): (self.p/'configure.process.json').write_text(json.dumps(self.receipt), encoding="utf-8")
 def collect(self): return m.collect(self.root,self.out,'a'*40,'b'*40)
 def test_failure_no_zip_private_text_omitted(self):
  r=self.collect(); self.assertEqual(r['exit_code'],1); self.assertEqual(r['diagnostic_categories'],['unknown-command'])
  text=(self.out/'failure-diagnostics.json').read_text(encoding="utf-8")
  for value in ('SECRET','PRIVATE','password','argv'): self.assertNotIn(value,text)
 def test_missing_receipt_no_classification(self):
  (self.p/'configure.process.json').unlink(); r=self.collect()
  self.assertEqual(r['binding'],'unverified'); self.assertEqual(r['diagnostic_categories'],[])
 def test_bad_identity(self):
  self.receipt['source_sha']='c'*40; self.write()
  with self.assertRaises(ValueError): self.collect()
  self.assertFalse(self.out.exists())
 def test_bad_hash(self):
  self.receipt['stderr_sha256']='c'*64; self.write()
  with self.assertRaises(ValueError): self.collect()
 def test_existing_output(self):
  self.out.mkdir()
  with self.assertRaises(ValueError): self.collect()
 def test_symlink(self):
  (self.p/'configure.stderr.bin').unlink(); outside=self.base/'secret'; outside.write_text('SECRET', encoding='utf-8')
  try: (self.p/'configure.stderr.bin').symlink_to(outside)
  except OSError: self.skipTest('symlink creation unavailable')
  with self.assertRaises(Exception): self.collect()
 def test_hardlink(self):
  import os
  (self.p/'configure.stderr.bin').unlink(); outside=self.base/'secret'; outside.write_text('SECRET', encoding='utf-8'); os.link(outside,self.p/'configure.stderr.bin')
  with self.assertRaises(Exception): self.collect()
 def test_oversize(self):
  with patch.object(m,'LIMIT',10): r=self.collect()
  self.assertEqual(r['binding'],'unverified'); self.assertEqual(r['diagnostic_categories'],[])
 def test_bad_exit(self):
  self.receipt['exit_code']='SECRET'; self.write()
  with self.assertRaises(ValueError): self.collect()
 def test_workflow_gates(self):
  s=(BASE/'.github/workflows/zh-4x-ci.yml').read_text(encoding="utf-8")
  self.assertIn("if: always() && steps.build.outcome == 'failure'",s)
  self.assertIn("if: always() && steps.build.outcome == 'success'",s)
if __name__=='__main__': unittest.main()
