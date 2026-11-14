import hashlib, json, os, subprocess, sys, tempfile, unittest, zipfile
from unittest.mock import patch
from pathlib import Path
HERE=Path(__file__).resolve().parents[1]
SOURCE=HERE/'scripts'
sys.path.insert(0,str(SOURCE))
from package_privacy import check_metadata
from private_build_roots import load_private_roots

def manifest(platform='windows'):
 return {'schema':'private-build-roots/v1','platform':platform,'roots':{'source':['C:/Secret/源'] if platform=='windows' else ['/mnt/秘密/source'], 'build':['C:/Secret/build'] if platform=='windows' else ['/mnt/private/build'], 'cache':['C:/Secret/cache'] if platform=='windows' else ['/mnt/private/cache'], 'sdk':[]}}
class Roots(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.dir=Path(self.tmp.name)
  self.addCleanup(self.tmp.cleanup)
 def spec(self, obj):
  p=self.dir/'private.json'; p.write_text(json.dumps(obj,ensure_ascii=False),encoding='utf8'); return load_private_roots(p)
 def test_dynamic_roots_and_identity_bypass(self):
  spec=self.spec(manifest())
  for encoding in ('utf-8','utf-16le'):
   for lead in (b'', b'X'):
    for text in (r'compiler /pathmap:c:\SECRET\源=Z:/s',r'C:\SECRET\cache\file',r'c:\secret\build\x'):
     data=lead+text.encode(encoding)+b'\0\0'
     record={'observed_plugin_sha256':hashlib.sha256(data).hexdigest(),'nul_terminated_literals':[text]}
     with self.subTest(text=text,encoding=encoding,lead=lead),self.assertRaisesRegex(ValueError,'Unexpected private path'):
      check_metadata(data,'ProtobufParser.dll',{'public_ci_source_records':{'ProtobufParser.dll':record}},spec)
  self.assertEqual(check_metadata(b'C:/Program Files/Common Files/SSL','other.dll',{},spec),[])
  self.assertEqual(check_metadata(b'C:/Secret/cache-other/file','other.dll',{},spec),[])
 def test_unix_case_and_utf8(self):
  spec=self.spec(manifest('unix'))
  with self.assertRaises(ValueError): check_metadata('/mnt/秘密/source/file'.encode(),'f',{},spec)
  self.assertEqual(check_metadata(b'/MNT/private/build/x','f',{},spec),[])
 def test_task_root_families_even_without_manifest(self):
  for fake_root in (b'Q:/PJ42TEST',b'S:/PJ1234-RC99-ABCDEF12-20990101'):
   with self.subTest(root=fake_root),self.assertRaises(ValueError):
    check_metadata(b'compiler /pathmap:'+fake_root+b'=Z:/x','f',{})
 def test_invalid_manifests(self):
  for changed in ({}, {'schema':'private-build-roots/v1','platform':'windows','roots':{}}, {**manifest(),'platform':'bogus'}, {**manifest(),'roots':{**manifest()['roots'],'source':[]}}, {**manifest(),'roots':{**manifest()['roots'],'source':['C:/']}}, {**manifest(),'roots':{**manifest()['roots'],'build':['C:/secret/../x']}}, {**manifest(),'roots':{**manifest()['roots'],'unknown':[]}}):
   with self.subTest(changed=changed), self.assertRaisesRegex(ValueError,'Invalid private build roots manifest'):
    self.spec(changed)
 def runaudit(self,payload,mfile,output):
  env=dict(os.environ); env.update(PATH='',PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(SOURCE)); env.pop('QT_ROOT_DIR',None); env.pop('GITHUB_ACTIONS',None)
  return subprocess.run([sys.executable,str(HERE/'scripts/package_size_audit.py'),'--payload',str(payload),'--private-build-roots',str(mfile),'--out',str(output)],env=env,capture_output=True,text=True)
 def test_real_audit_entrypoint_and_fail_closed(self):
  p=self.dir/'roots.json'; p.write_text(json.dumps(manifest()),encoding='utf8')
  payload=self.dir/'payload';payload.mkdir(); out=self.dir/'report.json'
  r=self.runaudit(payload,p,out); self.assertNotEqual(r.returncode,0); self.assertFalse(out.exists())
  (payload/'BUILD-INFO.json').write_text('{}'); (payload/'data').write_bytes(b'compiler: /pathmap:C:/Secret/cache=Z:/pj-conan')
  r=self.runaudit(payload,p,out); self.assertNotEqual(r.returncode,0)
  result=json.loads(out.read_text()); self.assertEqual(result['privacy_scan'],'failed'); self.assertEqual(result['private_build_root_scan']['status'],'failed'); self.assertEqual(result['private_build_root_scan']['scanned_files'],2)
  self.assertNotIn('C:/Secret/cache',r.stdout+out.read_text())
  out.unlink(); (payload/'data').write_bytes(b'public content')
  r=self.runaudit(payload,p,out); self.assertEqual(r.returncode,0,r.stderr)
  result=json.loads(out.read_text());self.assertEqual(result['private_build_root_scan']['status'],'passed');self.assertEqual(result['privacy_scan'],'passed')
  # Stale success report cannot be silently reused or overwritten.
  r=self.runaudit(payload,p,out);self.assertNotEqual(r.returncode,0)
  out.unlink();p.write_text('{}');r=self.runaudit(payload,p,out);self.assertNotEqual(r.returncode,0);self.assertFalse(out.exists())
  p.unlink();r=self.runaudit(payload,p,out);self.assertNotEqual(r.returncode,0);self.assertFalse(out.exists())
 def test_collector_cmake_overrides_and_no_cache(self):
  prefix='C:' if os.name=='nt' else ''
  external=prefix+'/private/cache/dep-src'
  cache=self.dir/'CMakeCache.txt';cache.write_text('CPM_SOURCE_CACHE:PATH=OFF\nFETCHCONTENT_BASE_DIR:PATH='+prefix+'/build/_deps\nCPM_PACKAGE_dep_SOURCE_DIR:INTERNAL='+external+'\n')
  out=self.dir/'generated.json'
  cmd=[sys.executable,str(HERE/'scripts/collect_private_build_roots.py'),'--source',prefix+'/source','--build',prefix+'/build','--no-cache','--cmake-cache',str(cache),'--out',str(out)]
  result=subprocess.run(cmd,capture_output=True,text=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
  self.assertEqual(result.returncode,0,result.stderr); spec=load_private_roots(out)
  self.assertEqual(spec['root_count'],4);self.assertNotIn('/private/cache',result.stdout)
  self.assertIn(external.casefold() if os.name=='nt' else external,spec['paths'])
  out.unlink();cmd.remove('--cmake-cache');cmd.remove(str(cache))
  result=subprocess.run(cmd,capture_output=True,text=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
  self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(json.loads(out.read_text())['roots']['cache'],{'not_applicable':True})
 def test_zip_exact_and_changed(self):
  from verify_portable_zip import verify
  stage=self.dir/'stage';stage.mkdir();(stage/'a').write_text('alpha');z=self.dir/'x.zip'
  with zipfile.ZipFile(z,'w') as f:f.write(stage/'a','a')
  self.assertEqual(verify(stage,z),1)
  with zipfile.ZipFile(z,'w') as f:f.writestr('a','changed')
  with self.assertRaises(ValueError):verify(stage,z)
 def test_windows_cmake_root_and_mixed_case_inventory(self):
  from collect_private_build_roots import cmake_cache_roots
  from private_build_roots import stage_inventory_sha256
  f=self.dir/'windows-cache'; f.write_text('CPM_SOURCE_CACHE:PATH=OFF\nCPM_PACKAGE_wasmer_SOURCE_DIR:INTERNAL=C:/Private/External/wasmer\n')
  obj=manifest();obj['roots']['cache'].extend(cmake_cache_roots(f));spec=self.spec(obj)
  with self.assertRaises(ValueError):check_metadata(b'c:/private/external/wasmer/file', 'f', {}, spec)
  entries=[{'path':'a','bytes':1,'sha256':'x'},{'path':'B','bytes':1,'sha256':'y'}]
  self.assertEqual(stage_inventory_sha256(entries),stage_inventory_sha256(list(reversed(entries))))
 def test_exe_dump_binding_and_sidecar(self):
  import verify_windows_archives as w
  stage=self.dir/'staged';stage.mkdir();(stage/'a').write_bytes(b'clean')
  portable=self.dir/'portable.zip'
  with zipfile.ZipFile(portable,'w') as z:z.write(stage/'a','a')
  exe=self.dir/'installer.exe';exe.write_bytes(b'fake-installer')
  dev=self.dir/'devtool.exe';dev.write_bytes(b'fake-devtool')
  spec=self.spec(manifest('unix'));report=self.dir/'windows-report.json'
  def simulated(command,**kwargs):
   dump=Path(command[-1]);target=dump/'metadata/io.plotjuggler.application';target.mkdir(parents=True)
   (dump/'metadata/config').mkdir();(dump/'metadata/installer-config').mkdir()
   with zipfile.ZipFile(target/'1payload.zip','w') as z:z.write(stage/'a','a')
   return subprocess.CompletedProcess(command,0)
  with patch.object(w,'IFW47_DEVTOOL_SHA256',w.digest(dev)), patch.object(w.subprocess,'run',side_effect=simulated):
   reportdata=w.verify(stage,portable,exe,dev,w.digest(exe),spec,report)
   self.assertEqual(reportdata['installer_files'],1);self.assertEqual(reportdata['status'],'passed')
   report.unlink();(self.dir/'installer.dat').write_text('sidecar')
   with self.assertRaises(ValueError):w.verify(stage,portable,exe,dev,w.digest(exe),spec,report)
   self.assertFalse(report.exists())
   (self.dir/'installer.dat').unlink()
   original_hash=w.digest(exe)
   def mutate(command,**kwargs):
    simulated(command,**kwargs);exe.write_bytes(b'changed');return subprocess.CompletedProcess(command,0)
   with patch.object(w.subprocess,'run',side_effect=mutate):
    with self.assertRaises(ValueError):w.verify(stage,portable,exe,dev,original_hash,spec,report)
   self.assertFalse(report.exists())
 def test_full_mixed_case_binding(self):
  import verify_windows_archives as w
  from verify_windows_binding import verify
  stage=self.dir/'stage';stage.mkdir()
  (stage/'BUILD-INFO.json').write_text('{}');(stage/'a').write_text('one');(stage/'B').write_text('two')
  portable=self.dir/'x-Windows-x64.zip'
  with zipfile.ZipFile(portable,'w') as z:
   for f in stage.iterdir():z.write(f,f.name)
  exe=self.dir/'x-Windows-x64.exe';exe.write_bytes(b'fake-exe');dev=self.dir/'devtool';dev.write_bytes(b'fake-devtool')
  rootfile=self.dir/'roots.json';rootfile.write_text(json.dumps(manifest('unix')))
  report=self.dir/'binding.json';auditfile=self.dir/'audit.json';spec=load_private_roots(rootfile)
  def fake(command,**kwargs):
   dump=Path(command[-1]);target=dump/'metadata/io.plotjuggler.application';target.mkdir(parents=True)
   (dump/'metadata/config').mkdir();(dump/'metadata/installer-config').mkdir()
   with zipfile.ZipFile(target/'1payload.zip','w') as z:
    for f in stage.iterdir():z.write(f,f.name)
   return subprocess.CompletedProcess(command,0)
  with patch.object(w,'IFW47_DEVTOOL_SHA256',w.digest(dev)),patch.object(w.subprocess,'run',side_effect=fake):
   result=w.verify(stage,portable,exe,dev,w.digest(exe),spec,report)
  env=dict(os.environ);env.update(PATH='',PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(SOURCE));env.pop('QT_ROOT_DIR',None);env.pop('GITHUB_ACTIONS',None)
  p=subprocess.run([sys.executable,str(HERE/'scripts/package_size_audit.py'),'--payload',str(stage),'--package',str(portable),'--package',str(exe),'--private-build-roots',str(rootfile),'--out',str(auditfile)],capture_output=True,text=True,env=env)
  self.assertEqual(p.returncode,0,p.stderr);verify(json.loads(auditfile.read_text()),result)
 def test_binding_requires_matching_audit_and_archives(self):
  from verify_windows_binding import verify
  binding={'status':'passed','private_roots_manifest_sha256':'m','stage_inventory_sha256':'i','stage_files':1,'portable_files':1,'installer_files':1,'portable_sha256':'z','installer_sha256':'e'}
  audit={'privacy_scan':'passed','private_build_root_scan':{'status':'passed','manifest_sha256':'m','stage_inventory_sha256':'i','scanned_files':1},'packages':[{'name':'x-Windows-x64.zip','sha256':'z'},{'name':'x-Windows-x64.exe','sha256':'e'}]}
  verify(audit,binding)
  audit['packages'][1]['sha256']='other'
  with self.assertRaises(ValueError):verify(audit,binding)
 def test_unscanned_symlink_fails(self):
  p=self.dir/'roots.json';p.write_text(json.dumps(manifest()),encoding='utf8')
  payload=self.dir/'payload';payload.mkdir();(payload/'BUILD-INFO.json').write_text('{}')
  try:(payload/'link').symlink_to(self.dir/'outside')
  except OSError as error:
   if os.name=='nt' and getattr(error,'winerror',None)==1314:self.skipTest('Windows token lacks symlink privilege; no security settings changed')
   raise
  (self.dir/'outside').write_text('outside');out=self.dir/'report.json'
  r=self.runaudit(payload,p,out);self.assertNotEqual(r.returncode,0);self.assertFalse(out.exists())
if __name__=='__main__':unittest.main()
