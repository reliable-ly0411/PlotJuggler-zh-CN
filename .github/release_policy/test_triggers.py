# SPDX-License-Identifier: MPL-2.0
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]
class TriggerTests(unittest.TestCase):
 def test_sync_build_requires_new_formal_release(self):
  text=(ROOT/'.github/workflows/zh-sync.yml').read_text()
  self.assertIn("if: needs.sync.outputs.build == 'true'",text)
  self.assertIn('default: sync',text)
  self.assertNotIn("needs.sync.outputs.changed == 'true'",text)
  self.assertIn('sync-four:',text)
  self.assertIn('refs/heads/zh-CN-4.x-dev',text)
 def test_native_and_image_workflows_have_no_push_or_pr(self):
  for name in ('zh-release.yml','zh-linux.yml','zh-windows.yml','zh-image-tools.yml','zh-resource-audit.yml'):
   text=(ROOT/'.github/workflows'/name).read_text()
   events=text.split("'on':",1)[1].split('permissions:',1)[0]
   for event in ('  push:', '  pull_request:', '  schedule:', '  release:', '  workflow_run:'):
    self.assertNotIn(event,events,name)
   self.assertIn('workflow_dispatch:',events)
 def test_no_automatic_publisher(self):
  text=(ROOT/'.github/workflows/zh-release.yml').read_text()
  for bad in ('gh release', 'contents: write', 'publish:'):
   self.assertNotIn(bad,text)
  self.assertIn('scripts/release_assets.py collect',text)
if __name__=='__main__':unittest.main()
