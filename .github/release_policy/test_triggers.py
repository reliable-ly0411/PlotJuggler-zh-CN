# SPDX-License-Identifier: MPL-2.0
import pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parents[2]
class TriggerTests(unittest.TestCase):
 def test_heavy_upstream_recipes_have_no_automatic_event(self):
  for name in ('appimage-builder-image.yml','conan-lock-refresh.yml','linux-appimage-release.yml','linux-ci.yml','nix.yml','pixi-ci.yml','sanitizers.yml','wasm-ci.yml','windows-ci.yml','windows-release.yml'):
   text=(ROOT/'.github/workflows'/name).read_text(encoding='utf-8')
   events=text.split('on:',1)[1].split('\njobs:',1)[0].split('\npermissions:',1)[0].split('\nconcurrency:',1)[0]
   for forbidden in ('  push:','  pull_request:','  schedule:','  release:'):
    self.assertNotIn(forbidden,events,name)
   self.assertIn('  workflow_dispatch:',events,name)
 def test_native_is_explicit_manual_request(self):
  text=(ROOT/'.github/workflows/zh-4x-ci.yml').read_text(encoding='utf-8')
  self.assertIn("github.event.created && startsWith(github.ref_name, 'zh-CN-4.x-ci/manual-build-')",text)
  self.assertIn('contents: read',text)
  self.assertIn('cancel-in-progress: false',text)
 def test_promotion_keeps_human_and_immutable_artifact_guards(self):
  text=(ROOT/'.github/workflows/zh-4x-publish.yml').read_text(encoding='utf-8')
  for required in ('inputs.visual_reviewed','github.event.created','publish-accepted-','CANDIDATE_ATTEMPT','sha256sum -c','--downloads draft-check','--draft=false'):
   self.assertIn(required,text)
  self.assertNotIn('--clobber',text)
 def test_plugin_preflight_has_one_creation_only_and_no_publication(self):
  text=(ROOT/'.github/workflows/zh-4x-plugin-preflight.yml').read_text(encoding='utf-8')
  branch='zh-CN-4.x-ci/plugin-preflight-rc2-final5'
  self.assertIn("branches: ['"+branch+"']", text)
  self.assertIn("github.event.created && github.ref_name == '"+branch+"'", text)
  self.assertIn('contents: read', text)
  self.assertIn('--preflight', text)
  self.assertNotIn('contents: write', text)
  self.assertNotIn('gh release', text)
  for event,created,ref,expected in [('push',True,branch,True),('push',False,branch,False),
      ('push',True,'zh-CN-4.x-dev',False),('pull_request',True,branch,False),
      ('push',True,'zh-CN-4.x-ci/other',False)]:
   self.assertEqual(event=='push' and created and ref==branch,expected)
if __name__=='__main__':unittest.main()
