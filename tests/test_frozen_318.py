# SPDX-License-Identifier: MPL-2.0
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import subprocess
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('frozen',ROOT/'scripts/verify_frozen_318.py')
f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)

class FrozenChecks(unittest.TestCase):
    def test_source_binding(self):
        m=json.loads(f.MANIFEST.read_text()); m['source_files']={}
        values=[m['source'],m['tree'],str(m['epoch']),'']
        with patch.object(f,'git',side_effect=values):f.verify_source(ROOT,m,True)
        for pos in range(4):
            bad=values.copy();bad[pos]='WRONG'
            with self.subTest(pos=pos),patch.object(f,'git',side_effect=bad):
                with self.assertRaises(ValueError):f.verify_source(ROOT,m,True)
    def test_input_hash(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); (root/'lock').write_text('changed')
            m={'source':'s','tree':'t','epoch':1,'source_files':{'lock':f.digest(b'locked')}}
            with patch.object(f,'git',side_effect=['s','t','1']), patch.object(f.subprocess,'check_output',return_value=b'changed'):
                with self.assertRaises(ValueError):f.verify_source(root,m)
    def test_crlf_checkout_and_changed_content(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            def g(*args):
                return subprocess.check_output(['git','-C',td,*args],text=True).strip()
            g('init');g('config','user.email','test@example.invalid');g('config','user.name','Test')
            g('config','core.autocrlf','true')
            (root/'hook.py').write_bytes(b'print(1)\n')
            g('add','hook.py');g('commit','-m','fixture')
            m={'source':g('rev-parse','HEAD'),'tree':g('rev-parse','HEAD^{tree}'),
               'epoch':int(g('show','-s','--format=%ct','HEAD')),
               'source_files':{'hook.py':f.digest(b'print(1)\n')}}
            (root/'hook.py').write_bytes(b'print(1)\r\n')
            f.verify_source(root,m,True)
            (root/'hook.py').write_bytes(b'print(2)\r\n')
            with self.assertRaises(ValueError):f.verify_source(root,m)

    def test_toolchain(self):
        s={'os':'Windows','arch':'x86_64','compiler':'msvc','compiler.version':'194','build_type':'Release'}
        graph={'graph':{'nodes':{'1':{'context':'host','ref':'example/1','settings':s}}}}
        f.verify_toolchain(graph,{})
        for key in s:
            bad=copy.deepcopy(graph);bad['graph']['nodes']['1']['settings'][key]='wrong'
            with self.subTest(key=key):
                with self.assertRaises(ValueError):f.verify_toolchain(bad,{})
        with self.assertRaises(ValueError):f.verify_toolchain({'graph':{'nodes':{}}},{})
    def test_manifest_scope(self):
        m=json.loads(f.MANIFEST.read_text())
        self.assertEqual(len(m['dlls']),3)
        self.assertEqual(sum(x['nodes'] for x in m['qrc_structs']),10)
        self.assertEqual(m['review_run'],43569903164)
        self.assertEqual(m['review_artifact'],14106135528)
    def test_frozen_workflow(self):
        s=(ROOT/'.github/workflows/zh-native-318-diagnostic.yml').read_text()
        self.assertIn('ref: baf7d62133db26bb14911d446a1ce623fe704274',s)
        w=(ROOT/'.github/workflows/zh-windows.yml').read_text()
        self.assertLess(w.index('--initial'),w.index('- name: Build Plotjuggler'))
        self.assertLess(w.index('Installer created successfully:'),w.index('--graph "$env:RUNNER_TEMP'))
        self.assertIn("PJ_CTEST_REGEX: '.*'",w)
        self.assertIn('scripts/verify_windows_binding.py',w)
        self.assertIn('scripts/package_size_audit.py',w)

if __name__=='__main__':unittest.main()
