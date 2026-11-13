import importlib.util
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from probe_windows_locked_dependencies import check_graph, compare_reports
from windows_conan_pathmap import render

def graph():
    mapping=json.loads((ROOT/'scripts/windows_conan_mapping_refs.json').read_text())
    compiled=json.loads((ROOT/'scripts/windows_conan_host_refs.json').read_text())
    lock=json.loads((ROOT/'cmake/conan/windows-msvc194.lock').read_text())
    nodes=[{'ref':r,'context':'host','package_type':'static-library' if r in compiled else 'header-library','binary':'Build','package_id':'id'} for r in mapping]
    nodes += [{'ref':r,'context':'build'} for r in lock['build_requires']]
    return {'graph':{'nodes':nodes}}

class LockedTests(unittest.TestCase):
    def test_raw_comparison_never_normalizes(self):
        a={'status':'passed-dll-privacy-not-product-approval','dlls':{'lib.dll':{'sha256':'a'}}}
        b={'status':a['status'],'dlls':{'lib.dll':{'sha256':'b'}}}
        self.assertTrue(compare_reports(a,a)['raw_dlls_equal'])
        self.assertFalse(compare_reports(a,b)['raw_dlls_equal'])
        b['status']='failed'
        with self.assertRaises(ValueError):compare_reports(a,b)
    def test_exact_contexts(self):self.assertEqual(len(check_graph(graph())),33)
    def test_unknown_build_context_fails(self):
        g=graph();g['graph']['nodes'].append({'ref':'unknown/1#'+'a'*32,'context':'build'})
        with self.assertRaisesRegex(ValueError,'build-context'):check_graph(g)
    def test_missing_header_closure_fails(self):
        g=graph();g['graph']['nodes']=[n for n in g['graph']['nodes'] if not n['ref'].startswith('xsimd/')]
        with self.assertRaisesRegex(ValueError,'closure'):check_graph(g)
    def test_22_build_audit_preserved(self):
        g=graph();g['graph']['nodes'][0]['binary']='Cache'
        with self.assertRaises(ValueError):check_graph(g)
    def test_linker_identity_is_explicit(self):
        kwargs=dict(source=r'C:\source',cache=r'C:\cache',experimental_refs=['fixture/1#'+'a'*32])
        self.assertNotIn('sharedlinkflags',render(**kwargs))
        profile=render(**kwargs,experimental_link_brepro=True)
        self.assertIn("tools.build:sharedlinkflags=['/Brepro']",profile)
        self.assertIn("tools.build:exelinkflags=['/Brepro']",profile)
        self.assertIn("'tools.build:sharedlinkflags', 'tools.build:exelinkflags'",profile)

if __name__=='__main__':unittest.main()
