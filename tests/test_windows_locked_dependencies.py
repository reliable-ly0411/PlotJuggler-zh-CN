import importlib.util
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from probe_windows_locked_dependencies import check_graph, compare_reports, ignored_option_warnings
from windows_conan_pathmap import render

def graph():
    mapping=json.loads((ROOT/'scripts/windows_conan_mapping_refs.json').read_text())
    compiled=json.loads((ROOT/'scripts/windows_conan_host_refs.json').read_text())
    lock=json.loads((ROOT/'cmake/conan/windows-msvc194.lock').read_text())
    nodes=[{'ref':r,'context':'host','package_type':'static-library' if r in compiled else 'header-library','binary':'Build','package_id':'id'} for r in mapping]
    nodes += [{'ref':r,'context':'build'} for r in lock['build_requires']]
    return {'graph':{'nodes':nodes}}

class LockedTests(unittest.TestCase):
    def test_expected_openssl_capability_probes(self):
        output='\n'.join(f"cl : Command line warning D9002 : ignoring unknown option '{s}'" for s in ('-x','/dev/null','-dM')).encode()
        self.assertEqual(ignored_option_warnings(output),[])
    def test_ignored_policy_or_unknown_option_rejected(self):
        for flag in ('/pathmap:C:/cache=Z:/public','/Brepro','/unknown','-x-extra'):
            output=f"cl : Command line warning D9002 : ignoring unknown option '{flag}'".encode()
            self.assertEqual(len(ignored_option_warnings(output)),1)
        self.assertEqual(len(ignored_option_warnings(b"LINK : warning LNK4044: unrecognized option '/Brepro'; ignored")),1)
        self.assertEqual(len(ignored_option_warnings(b"unknown formatting D9002 -x")),1)
    def test_raw_comparison_never_normalizes(self):
        a={'status':'passed-dll-privacy-not-product-approval','dlls':{'lib.dll':{'sha256':'a'}}}
        b={'status':a['status'],'dlls':{'lib.dll':{'sha256':'b'}}}
        self.assertTrue(compare_reports(a,a)['raw_dlls_equal'])
        self.assertFalse(compare_reports(a,b)['raw_dlls_equal'])
        b['status']='failed'
        with self.assertRaises(ValueError):compare_reports(a,b)
    def test_exact_contexts(self):self.assertEqual(len(check_graph(graph())),33)
    def test_real_txt_consumer_is_not_a_dependency(self):
        g=graph();g['graph']['nodes'].append({'id':'0','recipe':'Consumer','context':'host','ref':'conanfile'})
        self.assertEqual(len(check_graph(g)),34)
        g['graph']['nodes'][-1]['id']='99'
        with self.assertRaisesRegex(ValueError,'host mapping'):check_graph(g)
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
