import importlib.util
from pathlib import Path
from types import SimpleNamespace as NS
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('hook', ROOT/'scripts/hook_windows_conan_pathmap.py')
h = importlib.util.module_from_spec(spec); spec.loader.exec_module(h)

class Values:
    def __init__(self, text='os=Windows\ncompiler=msvc\narch=x86_64\n'):
        self.text = text
    def dumps(self): return self.text
    def get_safe(self, name): return dict(x.split('=') for x in self.text.splitlines()).get(name)

class Conf(dict):
    def get(self, name, default=None, check_type=None):
        value = super().get(name, default)
        if check_type and not isinstance(value, check_type): raise ValueError(name)
        return value
    def define(self, name, value): self[name] = value

def item(cache=r'C:\cache-a', token='abcdefgh', name='fixture'):
    return NS(context='host',ref=NS(name=name,version='1.0',user=None,channel=None,revision='a'*32),
              settings=Values(),options=Values(''),source_folder=cache+'\\p\\b\\'+token+'\\s',
              build_folder=cache+'\\p\\b\\'+token+'\\b',package_folder=cache+'\\p\\'+token+'\\p')

def setup():
    c=item(); d=item(name='dep'); c.dependencies=NS(host={'dep':d})
    refs=[h.exact_ref(c.ref),h.exact_ref(d.ref)]
    c.conf=Conf({h.POLICY_CONF:h.policy_digest(refs),h.REFS_CONF:refs,
      'tools.info.package_id:confs':[h.POLICY_CONF,h.REFS_CONF,'tools.build:sharedlinkflags','tools.build:exelinkflags'],
      'tools.build:sharedlinkflags':['/Brepro'],'tools.build:exelinkflags':['/Brepro'],
      'tools.build:cflags':['/experimental:deterministic','/pathmap:C:/cache-a=Z:/pj-conan'],
      'tools.build:cxxflags':['/experimental:deterministic','/pathmap:C:/cache-a=Z:/pj-conan']})
    return c

class HookTests(unittest.TestCase):
    def test_root_consumer_maps_dependencies(self):
        c=setup();c.ref=None;h.pre_generate(c)
        self.assertEqual(len(c.conf['tools.build:cflags']),3)
        self.assertIn('/package',c.conf['tools.build:cflags'][0])
    def test_build_context_rejected(self):
        c=setup();c.context='build'
        with self.assertRaisesRegex(ValueError,'build-context'):h.pre_generate(c)
    def test_link_policy_not_optional(self):
        c=setup();c.conf['tools.build:sharedlinkflags']=[]
        with self.assertRaisesRegex(ValueError,'linker'):h.pre_generate(c)
    def test_mapping_refs_cover_exact_lock_host_set(self):
        import json
        refs=json.loads((ROOT/'scripts/windows_conan_mapping_refs.json').read_text())
        lock=json.loads((ROOT/'cmake/conan/windows-msvc194.lock').read_text())
        self.assertEqual(len(refs),24);self.assertEqual(set(refs),set(lock['requires']))
        compiled=json.loads((ROOT/'scripts/windows_conan_host_refs.json').read_text())
        self.assertEqual(len(compiled),22);self.assertTrue(set(compiled)<set(refs))
    def test_inactive(self):
        c=NS(conf=Conf()); h.pre_generate(c)
    def test_version_object_and_pinned_revision(self):
        c=item(); c.ref.version=NS(); c.ref.version=type('Version',(),{'__str__':lambda s:'1.0'})()
        self.assertEqual(h.exact_ref(c.ref),'fixture/1.0#'+'a'*32)
        c.ref.revision=None
        with self.assertRaises(ValueError): h.exact_ref(c.ref)
    def test_two_caches_same_semantic_targets(self):
        a=setup(); b=setup()
        for x in [b,*b.dependencies.host.values()]:
            for f in ('source_folder','build_folder','package_folder'):
                setattr(x,f,getattr(x,f).replace('cache-a','cache-b').replace('abcdefgh','differenttoken'))
        flags_a=h.mapping_flags(a,set(a.conf[h.REFS_CONF]));flags_b=h.mapping_flags(b,set(b.conf[h.REFS_CONF]))
        self.assertNotEqual(flags_a,flags_b)
        self.assertEqual(sorted(x.split('=')[1] for x in flags_a),sorted(x.split('=')[1] for x in flags_b))
    def test_exact_maps_precede_retained_fallback(self):
        c=setup();h.pre_generate(c)
        flags=c.conf['tools.build:cflags']
        self.assertEqual(len(flags),5);self.assertEqual(flags,c.conf['tools.build:cxxflags'])
        self.assertEqual(flags[-1],'/pathmap:C:/cache-a=Z:/pj-conan')
    def test_same_source_build_and_longest_first(self):
        c=setup();c.build_folder=c.source_folder+'\\build';fs=h.mapping_flags(c,set(c.conf[h.REFS_CONF]))
        self.assertIn('/build=',fs[0])
        c.build_folder=c.source_folder
        self.assertTrue(any(x.endswith('/source-build') for x in h.mapping_flags(c,set(c.conf[h.REFS_CONF]))))
    def test_unreviewed_or_changed_semantics(self):
        c=setup();a=h.identity(c,set(c.conf[h.REFS_CONF]));c.options=Values('shared=True')
        self.assertNotEqual(a,h.identity(c,set(c.conf[h.REFS_CONF])))
        c.ref.revision='b'*32
        with self.assertRaises(ValueError):h.mapping_flags(c,set(c.conf[h.REFS_CONF]))
    def test_bad_policy_and_package_identity(self):
        for change in ({h.POLICY_CONF:'0'*64},{'tools.info.package_id:confs':[]},{h.REFS_CONF:['a','a']}):
            c=setup();c.conf.update(change)
            with self.assertRaises(ValueError):h.pre_generate(c)
    def test_unsafe_roots_and_collisions(self):
        for bad in ('C:/','C:/cache/../x','relative','C:/cache space','C:/bad=x'):
            with self.assertRaises(ValueError):h.root(bad)
        c=setup();d=next(iter(c.dependencies.host.values()));d.package_folder=c.source_folder
        with self.assertRaises(ValueError):h.mapping_flags(c,set(c.conf[h.REFS_CONF]))
    def test_failure_is_atomic(self):
        c=setup();before=list(c.conf['tools.build:cflags']);c.conf['tools.build:cxxflags']=[]
        with self.assertRaises(ValueError):h.pre_generate(c)
        self.assertEqual(before,c.conf['tools.build:cflags'])

if __name__=='__main__':unittest.main()
