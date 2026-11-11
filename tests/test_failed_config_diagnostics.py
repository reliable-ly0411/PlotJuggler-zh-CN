# SPDX-License-Identifier: MPL-2.0
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
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
 def set_stream(self, name, data):
  (self.p/('configure.'+name+'.bin')).write_bytes(data)
  self.receipt[name+'_sha256']=hashlib.sha256(data).hexdigest(); self.write()
 def test_wrapped_known_errors_emit_only_fixed_categories(self):
  messages=(
   ('Native test kit requires its locked Conan\n  CPython runtime','native-cpython-runtime-missing'),
   ('CMake detected wrong cpython version - this is likely a bug with the cpython Conan package','cpython-version-mismatch'),
   ('Syntax error in cmake code at PRIVATE\n  Invalid character escape','cmake-syntax-error'),
   ('Each download\n  failed! url=SECRET','download-failed'),
  )
  for index,(message,label) in enumerate(messages):
   with self.subTest(label=label):
    self.out=self.base/('output-'+str(index))
    self.set_stream('stderr',('CMake Error at C:/PRIVATE/SECRET.cmake:123 (message):\r\n  '+message+'\r\n').encode())
    report=self.collect()
    self.assertEqual(report['diagnostic_categories'],[label])
    self.assertEqual(report['cmake_error_headers'],1)
    self.assertEqual(report['unclassified_error_count'],0)
    text=(self.out/'failure-diagnostics.json').read_text(encoding='utf-8')
    for value in ('PRIVATE','SECRET','C:/','url=','argv',message): self.assertNotIn(value,text)
 def test_unknown_error_is_counted_without_leaking_its_body(self):
  self.set_stream('stderr',b'CMake Error at C:/PRIVATE/SECRET.cmake:7 (message):\n  token=SECRET, unknown reason\n')
  report=self.collect()
  self.assertEqual(report['diagnostic_categories'],[])
  self.assertEqual(report['cmake_error_headers'],1)
  self.assertEqual(report['unclassified_error_count'],1)
  text=(self.out/'failure-diagnostics.json').read_text(encoding='utf-8')
  for value in ('PRIVATE','SECRET','token','unknown reason','C:/'): self.assertNotIn(value,text)
 def test_multiple_streams_count_each_error_and_deduplicate_categories(self):
  self.set_stream('stdout',b'CMake Error: Unknown CMake command SECRET\n')
  self.set_stream('stderr',b'CMake Error: Unknown CMake command PRIVATE\n'
                         b'CMake Error: undisclosed cause SECRET\n'
                         b'CMake Warning: Unknown CMake command in an unrelated warning\n')
  report=self.collect()
  self.assertEqual(report['diagnostic_categories'],['unknown-command'])
  self.assertEqual(report['cmake_error_headers'],3)
  self.assertEqual(report['unclassified_error_count'],1)
 def test_progress_and_warning_do_not_classify_an_unrelated_error(self):
  for boundary in ('-- ', 'CMake Warning: ', 'CMake Deprecation Warning: '):
   with self.subTest(boundary=boundary):
    labels,errors,unclassified=m.classify_output('CMake Error: SECRET\n'+boundary+'Unknown CMake command\n')
    self.assertEqual(labels,['unknown-command']); self.assertEqual(errors,1); self.assertEqual(unclassified,1)
 def test_cli_rejects_malformed_receipt_without_echoing_secrets(self):
  (self.p/'configure.process.json').write_text('{PRIVATE SECRET',encoding='utf-8')
  result=subprocess.run([sys.executable,'-B',str(BASE/'scripts/windows/collect_failed_config_diagnostics.py'),
                         '--root',str(self.root),'--output',str(self.out),'--source-sha','a'*40,'--source-tree','b'*40],
                        capture_output=True,text=True,encoding='utf-8',timeout=15)
  self.assertNotEqual(result.returncode,0); self.assertFalse(self.out.exists())
  self.assertEqual(result.stdout,'')
  self.assertEqual(result.stderr.strip(),'Safe failure diagnostics could not be collected.')
 def test_oversize_stream_is_not_classified_even_with_a_valid_receipt(self):
  self.set_stream('stderr',b'CMake Error: Unknown CMake command SECRET\n'+b'X'*2048)
  with patch.object(m,'LIMIT',1024): report=self.collect()
  self.assertEqual(report['binding'],'receipt-identity-matched')
  self.assertEqual(report['diagnostic_categories'],[])
  self.assertNotIn('cmake_error_headers',report); self.assertNotIn('unclassified_error_count',report)
  self.assertIn({'name':'configure.stderr.bin','status':'over-limit-omitted'},report['files'])
 def test_missing_receipt_no_classification(self):
  (self.p/'configure.process.json').unlink(); r=self.collect()
  self.assertEqual(r['binding'],'unverified'); self.assertEqual(r['diagnostic_categories'],[])
  self.assertNotIn('cmake_error_headers',r); self.assertNotIn('unclassified_error_count',r)
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
  self.assertNotIn('cmake_error_headers',r); self.assertNotIn('unclassified_error_count',r)
 def test_bad_exit(self):
  self.receipt['exit_code']='SECRET'; self.write()
  with self.assertRaises(ValueError): self.collect()
 def test_workflow_gates(self):
  s=(BASE/'.github/workflows/zh-4x-ci.yml').read_text(encoding="utf-8")
  self.assertIn("if: always() && steps.build.outcome == 'failure'",s)
  self.assertIn("if: always() && steps.build.outcome == 'success'",s)
if __name__=='__main__': unittest.main()
