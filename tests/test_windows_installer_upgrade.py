#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
import copy
import json
import os
from pathlib import Path, PureWindowsPath
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import windows_installer_upgrade as upgrade
import verify_windows_installer_resources as resource


class UpgradeTests(unittest.TestCase):
    def test_exact_registration(self):
        rows = [dict(scope='user', location='C:/isolated/target', uninstall=json.dumps(['C:/isolated/target/maintenancetool.exe','--start-uninstaller']))]
        upgrade.validate_registration(rows, 'C:/isolated/target', json.loads)
        for flags in (['--uninstall'], ['--start-uninstaller','--extra'], ['--start-uninstaller','purge'], []):
            invalid = [dict(rows[0], uninstall=json.dumps(['C:/isolated/target/maintenancetool.exe', *flags]))]
            with self.assertRaises(AssertionError):
                upgrade.validate_registration(invalid, 'C:/isolated/target', json.loads)
        for bad in [[], rows*2, [dict(rows[0], scope='machine64')], [dict(rows[0], location='C:/other')],
                    [dict(rows[0], uninstall=json.dumps(['C:/other/maintenancetool.exe','--start-uninstaller']))]]:
            with self.assertRaises(AssertionError):
                upgrade.validate_registration(bad, 'C:/isolated/target', json.loads)

    @unittest.skipUnless(os.name == 'nt', 'Native CommandLineToArgvW requires Windows')
    def test_native_official_uninstall_command(self):
        target = 'C:/isolated target'
        command = '"C:/isolated target/maintenancetool.exe" --start-uninstaller'
        row = dict(scope='user', location=target, uninstall=command)
        upgrade.validate_registration([row], target)
        for invalid in (command+' --extra', command+' purge', command.replace('--start-uninstaller','--uninstall')):
            with self.assertRaises(AssertionError):
                upgrade.validate_registration([dict(row, uninstall=invalid)], target)

    def test_initial_scope_arguments(self):
        for path_type in (Path, PureWindowsPath):
            with self.subTest(path_type=path_type.__name__):
                paths = {k:path_type('C:/isolated')/k for k in ('target','userMenu','allMenu','desktop')}
                paths['group']='SyntheticFixtureGroup'
                args=upgrade.fixture_values(paths, '{test}')
                self.assertIn('AllUsers=false',args)
                self.assertIn('RunProgram=',args)
                self.assertIn('StartMenuDir=SyntheticFixtureGroup',args)
                for flag,key in (('TargetDir','target'),('UserStartMenuProgramsPath','userMenu'),
                                 ('AllUsersStartMenuProgramsPath','allMenu'),('DesktopDir','desktop')):
                    self.assertIn(flag+'='+str(paths[key]),args)

    def test_build_only_inert_fixture_and_real_script(self):
        with tempfile.TemporaryDirectory() as directory:
            stage=Path(directory)/'new'
            def fake_build(argv, *args, **kwargs):
                Path(argv[-1]).write_bytes(b'synthetic builder stand-in, never executed')
                return ''
            with patch.object(upgrade,'checked_process',fake_build):
                upgrade.build_fixture(stage,'new','binarycreator','translations',{},resource.stage_inputs)
            component=stage/'packages/io.plotjuggler.application'
            self.assertEqual((component/'data/FIXTURE-RECEIPT.txt').read_text(encoding='utf-8'),'PJ-SYNTHETIC-NEW')
            self.assertFalse((component/'data/bin/PlotJuggler4.exe').read_bytes().startswith(b'MZ'))
            self.assertIsNone(ET.parse(component/'meta/package.xml').getroot().find('Licenses'))
            self.assertFalse(ET.parse(stage/'config.xml').getroot().findtext('RunProgram'))
            script=(component/'meta/installscript.qs').read_text(encoding='utf-8')
            self.assertIn('PJ_REPLACEMENT_VERIFIED',script)
            self.assertIn('componentSelectionPageEntered',script)
            self.assertNotIn('__PJ_REPLACEMENT_HELPER_GZIP__',script)

    def test_timeout_does_not_kill_or_retry(self):
        class Running:
            def wait(self, timeout):
                raise subprocess.TimeoutExpired('synthetic',timeout)
        with tempfile.TemporaryDirectory() as directory, patch.object(upgrade.subprocess,'Popen',return_value=Running()) as launch:
            with self.assertRaisesRegex(AssertionError,'retained, no retry'):
                upgrade.checked_process(['synthetic'],Path(directory)/'output',{},timeout=0)
            self.assertEqual(launch.call_count,1)

    def test_record_contract_and_negative_controls(self):
        config=dict(target='C:/scope/target',userMenu='C:/scope/menu',allMenu='C:/scope/all',desktop='C:/scope/desktop',temporary='C:/scope/tmp',
                    newUuid='{new}',cache='C:/scope/tmp/cache',group='Group')
        fixture,controller=Path('C:/scope/new.exe'),Path('C:/scope/controller.qs')
        argv=json.dumps([str(fixture),'--script',str(controller),'--cache-path',config['cache']])
        base=dict(config,pid=123,executable=str(fixture),commandLine=argv,uuid='{new}',allUsers='false',runProgram='',TEMP=config['temporary'],TMP=config['temporary'],
                  targetPresent=False,toolPresent=False,oldKeyPresent=False,menu='C:/scope/menu/Group',status=0)
        records=[dict(base,kind=k) for k in ['introduction','target','components','start-menu','ready','installed','finished']]
        upgrade.validate_records(records,config,fixture,controller,json.loads)
        upgrade.validate_records(records[:2],config,fixture,controller,json.loads,refused=True)
        with self.assertRaises(AssertionError):
            upgrade.validate_records(records,config,fixture,controller,json.loads,refused=True)
        for position,key,value in [(4,'oldKeyPresent',True),(4,'targetPresent',True),(4,'toolPresent',True),(4,'menu','C:/outside'),
                                   (0,'uuid','other'),(0,'runProgram','app.exe'),(0,'TEMP','C:/outside'),(6,'status',1),(0,'pid',999)]:
            bad=copy.deepcopy(records);bad[position][key]=value
            with self.assertRaises(AssertionError):upgrade.validate_records(bad,config,fixture,controller,json.loads)

    @unittest.skipUnless(shutil.which('node'),'Node unavailable')
    def test_controller(self):
        subprocess.run(['node',str(ROOT/'tests/test_windows_installer_upgrade_node.js')],check=True,timeout=30)

if __name__=='__main__':unittest.main()
