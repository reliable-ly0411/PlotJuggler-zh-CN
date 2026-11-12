# SPDX-License-Identifier: MPL-2.0
"""Small C compiler fixture verifies the final loader and private-path gate."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/'scripts/linux_stage_elfs.py'

class LinuxStageTest(unittest.TestCase):
 def test_private_build_rpath_and_dwarf_are_removed_without_breaking_loading(self):
  if not all(shutil.which(x) for x in ('cc','cmake','readelf','objcopy','nm')):
   self.fail('required ELF staging tools are missing')
  with tempfile.TemporaryDirectory(prefix='pj-private-elf-') as tmp:
   root=Path(tmp); build=root/'private-build'; stage=root/'stage';build.mkdir();stage.mkdir()
   (build/'dep.c').write_text('int answer(void) { return 42; }\n')
   (build/'main.c').write_text('extern int answer(void); int main(void) { return answer() != 42; }\n')
   subprocess.run(['cc','-shared','-fPIC','-g',str(build/'dep.c'),'-o',str(build/'libfixture.so')],check=True)
   subprocess.run(['cc','-g',str(build/'main.c'),'-L'+str(build),'-lfixture',
                   '-Wl,-rpath,'+str(build),'-o',str(build/'plotjuggler')],check=True)
   shutil.copy2(build/'plotjuggler',build/'plotjuggler-launcher')
   for f in build.iterdir():
    if f.name in ('plotjuggler','plotjuggler-launcher','libfixture.so'):shutil.copy2(f,stage/f.name)
   def run(*args):return subprocess.run([sys.executable,str(SCRIPT),*map(str,args)],capture_output=True,text=True)
   audit=('audit','--root',stage,'--private-root',build,'--report',root/'audit.json')
   self.assertNotEqual(run(*audit).returncode,0,'raw build path must fail the gate')
   normalized=run('normalize','--root',stage,'--build-bin',build,'--layout','deb','--report',root/'normalized.json')
   self.assertEqual(normalized.returncode,0,normalized.stderr)
   self.assertEqual(run(*audit).returncode,0)
   output=subprocess.check_output(['readelf','-W','-S',str(stage/'plotjuggler')],text=True)
   self.assertIn('.symtab',output);self.assertNotIn('.debug_info',output)
   self.assertIn('answer',subprocess.check_output(['nm','-D',str(stage/'libfixture.so')],text=True))
   env={k:v for k,v in os.environ.items() if k!='LD_LIBRARY_PATH'}
   self.assertEqual(subprocess.run([str(stage/'plotjuggler')],env=env).returncode,0,'$ORIGIN must resolve the staged library')
   refusal=run('normalize','--root',build,'--build-bin',build,'--layout','deb','--report',root/'bad.json')
   self.assertNotEqual(refusal.returncode,0,'refuse to alter the build tree')
if __name__=='__main__':unittest.main()
