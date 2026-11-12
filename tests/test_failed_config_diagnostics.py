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
  self.receipt={'schema':1,'still_running':False,'source_sha':'a'*40,'source_tree':'b'*40,'exit_code':1,'argv':['PRIVATE'], 'stderr_sha256':hashlib.sha256(self.data).hexdigest()}
  self.write()
 def write(self): (self.p/'configure.process.json').write_text(json.dumps(self.receipt), encoding="utf-8")
 def collect(self): return m.collect(self.root,self.out,'a'*40,'b'*40)
 def write_build(self, **changes):
  receipt={'schema':1,'still_running':False,'source_sha':'a'*40,'source_tree':'b'*40,'exit_code':0,
           'argv':['PRIVATE'], 'cwd':'C:/SECRET', 'environment':{'password':'SECRET'}}
  receipt.update(changes)
  (self.p/'build.process.json').write_text(json.dumps(receipt),encoding='utf-8')
  return receipt
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
 def test_phase_boundaries_preserve_configure_fields(self):
  cases=((1,None,'configure-failed'), (0,None,'configure-succeeded-build-not-observed'),
         (0,2,'build-failed'), (0,0,'after-successful-build'),
         (1,0,'not-established'), (1,2,'not-established'))
  for index,(configure_code,build_code,boundary) in enumerate(cases):
   with self.subTest(configure=configure_code,build=build_code):
    self.out=self.base/('boundary-'+str(index))
    self.receipt['exit_code']=configure_code; self.set_stream('stderr',b'')
    if build_code is not None: self.write_build(exit_code=build_code)
    report=self.collect()
    self.assertEqual(report['schema'],1); self.assertEqual(report['status'],'build-failed-not-a-candidate')
    self.assertEqual(report['exit_code'],configure_code); self.assertEqual(report['phase'],'configure-observed')
    self.assertEqual(report['binding'],'receipt-identity-matched'); self.assertEqual(report['phase_boundary'],boundary)
    self.assertEqual(report['diagnostic_categories'],[])
    if build_code is None:
     self.assertEqual(report['build_binding'],'unverified'); self.assertNotIn('build_exit_code',report)
     self.assertIn({'name':'build.process.json','status':'missing'},report['files'])
    else:
     self.assertEqual(report['build_binding'],'receipt-identity-matched'); self.assertEqual(report['build_exit_code'],build_code)
 def test_build_binding_does_not_substitute_for_configure_binding(self):
  (self.p/'configure.process.json').unlink()
  for code in (0,1):
   with self.subTest(exit_code=code):
    self.out=self.base/('build-only-'+str(code)); self.write_build(exit_code=code)
    report=self.collect()
    self.assertEqual(report['binding'],'unverified'); self.assertEqual(report['phase'],'configure-not-observed')
    self.assertNotIn('exit_code',report); self.assertEqual(report['phase_boundary'],'not-established')
    self.assertEqual(report['build_binding'],'receipt-identity-matched'); self.assertEqual(report['build_exit_code'],code)
 def test_legacy_or_incomplete_configure_receipt_cannot_prove_boundary(self):
  for index,changes in enumerate(({'schema':None},{'schema':True},{'still_running':None},{'still_running':True})):
   with self.subTest(changes=changes):
    self.out=self.base/('incomplete-configure-'+str(index))
    self.receipt.update(schema=1,still_running=False,exit_code=0); self.receipt.update(changes); self.write()
    self.write_build(); report=self.collect()
    self.assertEqual(report['exit_code'],0); self.assertEqual(report['binding'],'receipt-identity-matched')
    self.assertEqual(report['build_exit_code'],0); self.assertEqual(report['phase_boundary'],'not-established')
 def test_build_receipt_private_fields_and_raw_build_streams_are_omitted(self):
  self.receipt['exit_code']=0; self.set_stream('stderr',b'')
  self.write_build()
  for stream in ('stdout','stderr'):
   (self.p/('build.'+stream+'.bin')).write_bytes(b'CMake Error: Unknown CMake command PRIVATE SECRET password=SECRET')
  report=self.collect(); text=(self.out/'failure-diagnostics.json').read_text(encoding='utf-8')
  self.assertEqual(report['phase_boundary'],'after-successful-build'); self.assertEqual(report['diagnostic_categories'],[])
  data=(self.p/'build.process.json').read_bytes()
  self.assertIn({'name':'build.process.json','bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()},report['files'])
  self.assertEqual(sorted(path.name for path in self.out.iterdir()),['failure-diagnostics.json'])
  for value in ('PRIVATE','SECRET','password','argv','environment','cwd','C:/','build.stdout.bin','build.stderr.bin'):
   self.assertNotIn(value,text)
 def test_bad_build_identity(self):
  for key in ('source_sha','source_tree'):
   with self.subTest(key=key):
    self.write_build(**{key:'c'*40})
    with self.assertRaises(ValueError): self.collect()
    self.assertFalse(self.out.exists())
 def test_bad_build_completion_or_exit(self):
  changes=({'schema':None},{'schema':True},{'schema':2},{'still_running':None},{'still_running':0},
           {'still_running':True},{'exit_code':None},{'exit_code':True},{'exit_code':0.0},
           {'exit_code':'SECRET'},{'exit_code':-2147483649},{'exit_code':2147483648})
  for change in changes:
   with self.subTest(change=change):
    self.write_build(**change)
    with self.assertRaises(ValueError): self.collect()
    self.assertFalse(self.out.exists())
 def test_cli_rejects_malformed_build_receipt_without_echoing_secrets(self):
  for data in ('{PRIVATE SECRET','["SECRET"]','null','"SECRET"'):
   with self.subTest(data=data):
    (self.p/'build.process.json').write_text(data,encoding='utf-8')
    result=subprocess.run([sys.executable,'-B',str(BASE/'scripts/windows/collect_failed_config_diagnostics.py'),
                           '--root',str(self.root),'--output',str(self.out),'--source-sha','a'*40,'--source-tree','b'*40],
                          capture_output=True,text=True,encoding='utf-8',timeout=15)
    self.assertNotEqual(result.returncode,0); self.assertFalse(self.out.exists()); self.assertEqual(result.stdout,'')
    self.assertEqual(result.stderr.strip(),'Safe failure diagnostics could not be collected.')
 def test_oversized_build_receipt_cannot_prove_build_outcome(self):
  self.receipt['exit_code']=0; self.write(); self.write_build(private_padding='SECRET'*1024)
  with patch.object(m,'LIMIT',1024): report=self.collect()
  self.assertEqual(report['binding'],'receipt-identity-matched'); self.assertEqual(report['build_binding'],'unverified')
  self.assertNotIn('build_exit_code',report)
  self.assertEqual(report['phase_boundary'],'configure-succeeded-build-not-observed')
  self.assertIn({'name':'build.process.json','status':'over-limit-omitted'},report['files'])
 def test_oversized_configure_receipt_does_not_inherit_build_binding(self):
  self.receipt['private_padding']='SECRET'*1024; self.write(); self.write_build()
  with patch.object(m,'LIMIT',1024): report=self.collect()
  self.assertEqual(report['binding'],'unverified'); self.assertEqual(report['build_binding'],'receipt-identity-matched')
  self.assertNotIn('exit_code',report); self.assertEqual(report['phase_boundary'],'not-established')
 def test_build_receipt_symlink_is_rejected(self):
  outside=self.base/'SECRET'; outside.write_text('SECRET',encoding='utf-8')
  try: (self.p/'build.process.json').symlink_to(outside)
  except OSError: self.skipTest('symlink creation unavailable')
  with self.assertRaises(m.safe.audit.AuditError): self.collect()
  self.assertFalse(self.out.exists())
 def test_build_receipt_hardlink_is_rejected(self):
  import os
  self.write_build(); os.link(self.p/'build.process.json',self.base/'SECRET')
  with self.assertRaises(m.safe.audit.AuditError): self.collect()
  self.assertFalse(self.out.exists())
 def test_build_receipt_nonregular_file_is_rejected(self):
  (self.p/'build.process.json').mkdir()
  with self.assertRaises(m.safe.audit.AuditError): self.collect()
  self.assertFalse(self.out.exists())
 def test_build_receipt_named_stream_check_is_required(self):
  self.write_build()
  def check(path,is_directory):
   if path == self.p/'build.process.json':
    self.assertFalse(is_directory); raise m.safe.audit.AuditError('SECRET named stream')
  with patch.object(m.safe.audit,'check_no_named_streams',side_effect=check):
   with self.assertRaises(m.safe.audit.AuditError): self.collect()
  self.assertFalse(self.out.exists())
 def test_linked_process_directory_is_rejected(self):
  self.write_build(); outside=self.base/'SECRET'; self.p.rename(outside)
  try: self.p.symlink_to(outside,target_is_directory=True)
  except OSError: self.skipTest('symlink creation unavailable')
  with self.assertRaises(m.safe.EvidenceError): self.collect()
  self.assertFalse(self.out.exists())
 def test_workflow_gates(self):
  s=(BASE/'.github/workflows/zh-4x-ci.yml').read_text(encoding="utf-8")
  self.assertIn("if: always() && steps.build.outcome == 'failure'",s)
  self.assertIn("if: always() && steps.build.outcome == 'success'",s)
if __name__=='__main__': unittest.main()
