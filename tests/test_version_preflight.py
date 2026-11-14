# SPDX-License-Identifier: MPL-2.0
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class Preflight(unittest.TestCase):
    def test_current_source_without_generated_build_file(self):
        result=subprocess.run([sys.executable,str(ROOT/'tests/check_version.py'),'--source-only'],capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)
    def test_stale_installer_refused_without_compiling(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp)
            for name in ['tests/check_version.py','CMakeLists.txt','cmake/ForkVersion.cmake','package.xml','installer/config.xml','installer/io.plotjuggler.application/meta/package.xml']:
                target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
            for name in ['installer/config.xml','installer/io.plotjuggler.application/meta/package.xml']:
                p=root/name;original=p.read_text();p.write_text(original.replace('<Version>','<Version>999.'))
                result=subprocess.run([sys.executable,str(root/'tests/check_version.py'),'--source-only'],capture_output=True)
                self.assertNotEqual(result.returncode,0)
                p.write_text(original)
    def test_review_artifact_includes_all_manifest_exports(self):
        workflow=(ROOT/'.github/workflows/zh-windows.yml').read_text()
        section=workflow.split('    - name: Upload isolated DLL review evidence\n',1)[1].split('    - name:',1)[0]
        self.assertIn('path: review-only/public-binaries/',section)
        self.assertIn("steps.public-binary-review.outputs.manifest-ready == 'true'",section)
if __name__=='__main__':unittest.main()
