import contextlib
import importlib.util
import io
import hashlib
import tarfile
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('notice_stage_fixture', ROOT/'scripts/stage_fork_notices.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class ResolutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.build = self.root/'nonstandard build'
        self.build.mkdir()
        self.out = self.root/'output'
        self.source = self.root/'private source'
        self.source.mkdir()
        (self.source/'LICENSE').write_text('known license')
        self.addCleanup(self.tmp.cleanup)
    def cache(self, text):
        (self.build/'CMakeCache.txt').write_text(text, encoding='utf-8')
        return module.read_cmake_cache(self.build)
    def run_stage(self, dependency, cache):
        return module.stage_downloaded_notice(self.root, self.out, dependency, self.build, cache)
    def test_missing_cache_and_system_distinction(self):
        record = self.run_stage('data_tamer', None)
        self.assertEqual(record['status'], 'incomplete')
        self.assertEqual(self.run_stage('data_tamer', self.cache('CMAKE_BUILD_TYPE:STRING=Release\n'))['status'], 'not-downloaded')
        with self.assertRaisesRegex(RuntimeError, 'source directory is unavailable'):
            self.run_stage('data_tamer', self.cache('CPM_PACKAGES:INTERNAL=data_tamer\n'))
    def test_same_configured_source_and_no_private_manifest_paths(self):
        cache=self.cache(f'FETCHCONTENT_SOURCE_DIR_DATA_TAMER:PATH={self.source}\nCPM_PACKAGE_data_tamer_SOURCE_DIR:INTERNAL={self.source}\nCPM_PACKAGE_data_tamer_VERSION:INTERNAL=1.0.3\n')
        record=self.run_stage('data_tamer',cache)
        self.assertEqual(record['source_resolution'],'configured')
        self.assertEqual(record['configured_version'],'1.0.3')
        self.assertEqual(record['status'],'staged-unverified')
        self.assertEqual(record['closure_status'],'incomplete')
        self.assertEqual((self.out/'Licenses/Downloaded/data_tamer/LICENSE').read_text(),'known license')
        self.assertNotIn(str(self.root),json.dumps(record))
        self.assertEqual(len(record['files'][0]['sha256']),64)
    def test_conflicting_sources_and_missing_wasmer_files_fail(self):
        other=self.root/'another'; other.mkdir()
        cache=self.cache(f'FETCHCONTENT_SOURCE_DIR_DATA_TAMER:PATH={self.source}\nCPM_PACKAGE_data_tamer_SOURCE_DIR:INTERNAL={other}\n')
        with self.assertRaisesRegex(RuntimeError,'conflicting'): self.run_stage('data_tamer',cache)
        cache=self.cache(f'CPM_PACKAGE_wasmer_SOURCE_DIR:INTERNAL={self.source}\n')
        with self.assertRaisesRegex(RuntimeError,'ATTRIBUTIONS'): self.run_stage('wasmer',cache)
        self.assertFalse((self.out/'Licenses/Downloaded/wasmer').exists())
        (self.source/'ATTRIBUTIONS').write_text('attributions')
        (self.source/'LICENSE').unlink()
        with self.assertRaisesRegex(RuntimeError,'LICENSE'): self.run_stage('wasmer',cache)
    def test_legacy_fallback_when_real_and_not_override_system(self):
        legacy=self.build/'_deps'/'data_tamer-src'; legacy.mkdir(parents=True)
        (legacy/'LICENSE').write_text('legacy')
        self.assertEqual(self.run_stage('data_tamer',None)['source_resolution'],'legacy-fallback')
        self.assertEqual(self.run_stage('data_tamer',self.cache('CMAKE_BUILD_TYPE:STRING=Release\n'))['status'],'not-downloaded')
        self.assertEqual(self.run_stage('data_tamer',self.cache('CPM_PACKAGES:INTERNAL=data_tamer\n'))['source_resolution'],'legacy-fallback')
    def test_cli_help_no_side_effect(self):
        before=set(self.root.iterdir())
        r=subprocess.run([sys.executable,str(ROOT/'scripts/stage_fork_notices.py'),'--help'],cwd=self.root,capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertIn('--build-dir',r.stdout)
        self.assertEqual(set(self.root.iterdir()),before)
        self.assertFalse((self.root/'--help').exists())
    def test_arrow_archive_version_hash_and_bytes(self):
        spec=importlib.util.spec_from_file_location('arrow_fixture',ROOT/'scripts/arrow_source_evidence.py')
        evidence=importlib.util.module_from_spec(spec); spec.loader.exec_module(evidence)
        archive=self.root/'source.tar.gz'
        with tarfile.open(archive,'w:gz') as tf:
            for name, content in [('LICENSE.txt',b'license 21'),('NOTICE.txt',b'notice 21')]:
                info=tarfile.TarInfo('apache-arrow-21.0.0/'+name); info.size=len(content); tf.addfile(info,io.BytesIO(content))
        digest=hashlib.sha256(archive.read_bytes()).hexdigest()
        with patch.dict(evidence.RELEASES, {'21.0.0':digest}), patch.dict(evidence.TEXT_HASHES, {'21.0.0':{'LICENSE.txt':hashlib.sha256(b'license 21').hexdigest(),'NOTICE.txt':hashlib.sha256(b'notice 21').hexdigest()}}):
            result=evidence.stage('21.0.0', self.out/'21', archive)
            self.assertEqual(result['closure_status'],'incomplete')
            self.assertEqual((self.out/'21/NOTICE.txt').read_bytes(),b'notice 21')
            with self.assertRaisesRegex(RuntimeError,'SHA256 mismatch'):
                evidence.stage('26.0.1',self.out/'26',archive)
            self.assertFalse((self.out/'26').exists())
    def test_vendored_missing_tamper_and_unknown_fail_closed(self):
        spec=importlib.util.spec_from_file_location('arrow_vendored_fixture',ROOT/'scripts/arrow_source_evidence.py')
        evidence=importlib.util.module_from_spec(spec); spec.loader.exec_module(evidence)
        missing=self.root/'no-materials'
        with patch.object(evidence,'VENDORED',missing), patch.dict(os.environ,{},clear=True):
            self.assertEqual(evidence.stage('21.0.0',self.out)['status'],'missing')
            self.assertFalse(self.out.exists())
        copy=self.root/'vendored'; shutil.copytree(ROOT/'licenses/apache-arrow',copy)
        (copy/'21.0.0/NOTICE.txt').write_text('wrong version')
        with patch.object(evidence,'VENDORED',copy), patch.dict(os.environ,{},clear=True):
            with self.assertRaisesRegex(RuntimeError,'text SHA256 mismatch'): evidence.stage('21.0.0',self.out)
            with self.assertRaises(ValueError): evidence.stage('99.0.0',self.out)
            self.assertFalse(self.out.exists())
    def test_arrow24_exact_vendored_materials_and_rejections(self):
        spec=importlib.util.spec_from_file_location('arrow24_fixture',ROOT/'scripts/arrow_source_evidence.py')
        evidence=importlib.util.module_from_spec(spec); spec.loader.exec_module(evidence)
        with patch.dict(os.environ,{},clear=True):
            result=evidence.stage('24.0.0',self.out)
            self.assertEqual(result['status'],'pinned-vendored-source-texts')
            self.assertEqual(result['closure_status'],'incomplete')
            self.assertEqual(result['archive_sha256'],'9a8094d24fa33b90c672ab77fdda253f29300c8b0dd3f0b8e55a29dbd98b82c9')
            for name in ('LICENSE.txt','NOTICE.txt'):
                self.assertEqual((self.out/name).read_bytes(),(ROOT/'licenses/apache-arrow/24.0.0'/name).read_bytes())
            for version in ('24','24.0.1','24.0.0-rc1','99.0.0'):
                with self.assertRaisesRegex(ValueError,'Unsupported Arrow version'):
                    evidence.stage(version,self.root/'rejected')
            self.assertFalse((self.root/'rejected').exists())
        copy=self.root/'arrow24-vendored'; shutil.copytree(ROOT/'licenses/apache-arrow',copy)
        with patch.object(evidence,'VENDORED',copy), patch.dict(os.environ,{},clear=True):
            # A matching manifest alone must never authorize modified source text.
            (copy/'24.0.0/NOTICE.txt').write_bytes(b'altered')
            with self.assertRaisesRegex(RuntimeError,'text SHA256 mismatch'):
                evidence.stage('24.0.0',self.root/'tampered')
            self.assertFalse((self.root/'tampered').exists())
            manifest=copy/'manifest.json'; data=json.loads(manifest.read_text())
            data['releases']['24.0.0']['archive_sha256']='0'*64
            manifest.write_text(json.dumps(data))
            with self.assertRaisesRegex(RuntimeError,'manifest mismatch'):
                evidence.stage('24.0.0',self.root/'bad-manifest')
            self.assertFalse((self.root/'bad-manifest').exists())

    def test_conan_default_stages_source_separately_when_package_notice_missing(self):
        spec=importlib.util.spec_from_file_location('conan_fixture',ROOT/'scripts/conan_license_deployer.py')
        deployer=importlib.util.module_from_spec(spec); spec.loader.exec_module(deployer)
        package=self.root/'conan-package'; (package/'licenses').mkdir(parents=True)
        (package/'licenses/LICENSE').write_text('package license')
        import types
        ref=type('Ref',(),{'name':'arrow','version':'21.0.0','__str__':lambda self:'arrow/21.0.0'})()
        dep=types.SimpleNamespace(ref=ref,package_folder=str(package))
        graph=types.SimpleNamespace(root=types.SimpleNamespace(conanfile=types.SimpleNamespace(dependencies=types.SimpleNamespace(host={'arrow':dep}))))
        with patch.dict(os.environ,{},clear=True): deployer.deploy(graph,self.out)
        result=json.loads((self.out/'Conan/manifest.json').read_text())
        record=result['dependencies'][0]
        self.assertEqual(result['closure_status'],'incomplete')
        self.assertEqual(record['notice_evidence']['status'],'missing')
        self.assertEqual(record['source_evidence']['status'],'pinned-vendored-source-texts')
        self.assertEqual(record['source_evidence']['directory'],'arrow-21.0.0/upstream-source')
        self.assertEqual(record['source_evidence']['files']['NOTICE.txt'],hashlib.sha256((self.out/'Conan/arrow-21.0.0/upstream-source/NOTICE.txt').read_bytes()).hexdigest())
    def test_configured_arrow_version_is_exact_and_ambiguous_rejected(self):
        config=self.root/'arrow cmake'; config.mkdir()
        (config/'ArrowConfigVersion.cmake').write_text('set(PACKAGE_VERSION "26.0.1")\n')
        cache={'Arrow_DIR':str(config)}
        self.assertEqual(module.configured_arrow_version(cache),'26.0.1')
        (config/'arrow-config-version.cmake').write_text('set(PACKAGE_VERSION "21.0.0")\n')
        with self.assertRaisesRegex(RuntimeError,'ambiguous'): module.configured_arrow_version(cache)
    def test_main_nonstandard_build_and_arrow_cli(self):
        repo=self.root/'fake-repo'; repo.mkdir(); (repo/'scripts').mkdir()
        for name in ('plotjuggler_plugins/DataLoadAPBin/LICENSE','plotjuggler_plugins/DataLoadAPBin/COPYING.GPL3','plotjuggler_plugins/DataLoadAPBin/UPSTREAM.md','LICENSE.md','docs/zh-CN.md','docs/THIRD-PARTY-3X.md','licenses/qt5/notice','3rdparty/qwt/COPYING','3rdparty/Qt-Advanced-Docking/LICENSE','3rdparty/color_widgets/COPYING','3rdparty/QCodeEditor/LICENSE.MIT','3rdparty/backward-cpp/LICENSE.txt','3rdparty/date-3.0.4/LICENSE.txt','3rdparty/sol2-3.5.0/LICENSE.txt','plotjuggler_plugins/ToolboxFFT/3rdparty/KissFFT/COPYING'):
            path=repo/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_text('fixture')
        (self.build/'plotjuggler_app').mkdir()
        (self.build/'plotjuggler_app/QT5-TRANSLATIONS.json').write_text('{}')
        (self.build/'FORK-VERSION.json').write_text('{"version":"fixture"}')
        self.cache(f'FETCHCONTENT_SOURCE_DIR_DATA_TAMER:PATH={self.source}\nCPM_PACKAGE_data_tamer_SOURCE_DIR:INTERNAL={self.source}\n')
        (self.build/'dependency-notices/Conan').mkdir(parents=True)
        (self.build/'dependency-notices/Conan/manifest.json').write_text('{}')
        shutil.copyfile(ROOT/'scripts/arrow_source_evidence.py',repo/'scripts/arrow_source_evidence.py')
        shutil.copytree(ROOT/'licenses/apache-arrow',repo/'licenses/apache-arrow')
        for name in ('windows-runtime-notices', 'ifw'):
            shutil.copytree(ROOT/'licenses'/name, repo/'licenses'/name)
        metadata = Path('installer/io.plotjuggler.application/meta/license_ifw.txt')
        (repo/metadata).parent.mkdir(parents=True)
        shutil.copyfile(ROOT/metadata, repo/metadata)
        argv=['stage',str(self.out),'--build-dir',str(self.build),'--arrow-source-version','26.0.1']
        with patch.object(module,'__file__',str(repo/'scripts/stage_fork_notices.py')), patch.object(sys,'argv',argv), patch.object(module.subprocess,'check_output',return_value='abcdef\n'), patch.object(module,'stage_distro_notices'), patch.dict(os.environ, {}, clear=True), contextlib.redirect_stdout(io.StringIO()):
            module.main()
        manifest=json.loads((self.out/'Licenses/Downloaded/manifest.json').read_text())
        self.assertEqual(manifest['dependencies'][0]['status'],'staged-unverified')
        self.assertEqual(manifest['closure_status'],'incomplete')
        source=json.loads((self.out/'Licenses/ArrowSource/evidence.json').read_text())
        self.assertEqual(source['status'],'pinned-vendored-source-texts')
        self.assertEqual(source['directory'],'26.0.1')
        self.assertEqual(source['closure_status'],'incomplete')
        self.assertEqual((self.out/'Licenses/ArrowSource/26.0.1/NOTICE.txt').read_bytes(),(ROOT/'licenses/apache-arrow/26.0.1/NOTICE.txt').read_bytes())
        self.assertEqual(json.loads((self.out/'BUILD-INFO.json').read_text())['version'],'fixture')
        config=self.root/'arrow-config'; config.mkdir()
        (config/'ArrowConfigVersion.cmake').write_text('set(PACKAGE_VERSION "26.0.1")\n')
        self.cache(f'Arrow_DIR:PATH={config}\n')
        auto=self.root/'auto-output'
        with patch.object(module,'__file__',str(repo/'scripts/stage_fork_notices.py')), patch.object(sys,'argv',['stage',str(auto),'--build-dir',str(self.build)]), patch.object(sys,'platform','linux'), patch.object(module.subprocess,'check_output',return_value='abcdef\n'), patch.object(module,'stage_distro_notices'), patch.dict(os.environ,{},clear=True), contextlib.redirect_stdout(io.StringIO()):
            module.main()
        source=json.loads((auto/'Licenses/ArrowSource/evidence.json').read_text())
        self.assertEqual(source['status'],'pinned-vendored-source-texts')
        self.assertEqual(source['version_origin'],'cmake-package-version')
        if os.name == 'nt':
            for output in (self.out, auto):
                module.validate_windows_runtime_materials(output/'Licenses', repo/metadata)
                for name in ('windows-runtime-notices', 'ifw'):
                    original = repo/'licenses'/name
                    staged = output/'Licenses'/name
                    self.assertEqual({p.relative_to(original) for p in original.rglob('*') if p.is_file()},
                                     {p.relative_to(staged) for p in staged.rglob('*') if p.is_file()})
                    for path in original.rglob('*'):
                        if path.is_file():
                            self.assertEqual(path.read_bytes(), (staged/path.relative_to(original)).read_bytes())

if __name__=='__main__': unittest.main()
