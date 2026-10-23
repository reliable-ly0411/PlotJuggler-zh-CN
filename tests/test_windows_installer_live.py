import contextlib
import importlib.util
import io
import json
from pathlib import Path, PureWindowsPath
import unittest
from unittest.mock import patch
import shutil
import subprocess

spec = importlib.util.spec_from_file_location('live_probe', Path(__file__).resolve().parents[1] / 'scripts/windows_installer_live.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class LiveProbeTests(unittest.TestCase):
    def records(self):
        fixture, controller = Path('/fixture.exe'), Path('/controller.qs')
        targets = list(map(Path, ['/initial path', '/edited 中文 one', "/edited 中文 two's"]))
        rows = []
        for stage, lang in enumerate(['zh_CN', 'en_US', 'zh_CN']):
            argv = [str(fixture), '--script', str(controller), '--root', str(targets[stage])]
            argv += ['TargetDir=' + str(targets[stage]), '--cache-path', '/tmp/ifw-cache',
                     'PJProbeMarker=中文 space user@example.test']
            base = dict(language=lang, pid=10 + stage, target=str(targets[stage]),
                        executable=str(fixture), commandLine=json.dumps(argv), liveFixturePids=[10 + stage],
                        TEMP='/tmp', TMP='/tmp')
            chinese = lang == 'zh_CN'
            rows.append(dict(base, kind='introduction', title='欢迎' if chinese else 'Welcome',
                        message='欢迎使用 PlotJuggler 4 zh-CN 安装向导。' if chinese else 'Welcome to the PlotJuggler 4 zh-CN Setup.',
                        nextButton='下一步(&N) >' if chinese else '&Next >',
                        cancelButton='取消' if chinese else 'Cancel'))
            if stage < 2:
                rows.append(dict(base, kind='target-before-edit', field=str(targets[stage]), title=['选择安装目录', 'Choose Installation Directory'][stage], description=['请选择 PlotJuggler 4 的安装位置：', 'Please select where PlotJuggler 4 will be installed:'][stage]))
                edited = dict(base, target=str(targets[stage + 1]))
                rows.append(dict(edited, kind='target-edited', field=str(targets[stage + 1])))
                rows.append(dict(edited, kind='before-switch'))
            else:
                rows.append(dict(base, kind='finished'))
        return rows, fixture, controller, targets

    def check(self, records):
        with contextlib.redirect_stdout(io.StringIO()):
            probe.validate_records(*records, parse_argv=json.loads)

    def test_qdebug_cache_paths_decode_quoted_windows_paths(self):
        cache = str(PureWindowsPath("C:/temp/中文 path/tmp/ifw-cache"))
        diagnostic = '[time] Using metadata cache from ' + json.dumps(cache, ensure_ascii=True)
        self.assertEqual(probe.metadata_cache_paths(diagnostic), [cache])
        self.assertEqual(probe.metadata_cache_paths('Using metadata cache from C:/temp/cache'), ['C:/temp/cache'])
        with self.assertRaises(ValueError):
            probe.metadata_cache_paths('Using metadata cache from "unterminated')
        with self.assertRaises(AssertionError):
            probe.metadata_cache_paths('Using metadata cache from ""')

    def test_windows_cache_path_without_windows_host(self):
        with patch.object(probe, 'Path', PureWindowsPath):
            argv = probe.fixture_arguments(PureWindowsPath('C:/test/setup.exe'),
                                           PureWindowsPath('C:/test/controller.qs'),
                                           PureWindowsPath('C:/test/unused'))
        self.assertEqual(argv[argv.index('--cache-path') + 1],
                         str(PureWindowsPath('C:/test/tmp/ifw-cache')))

    def test_gui_startup_has_authoritative_positional_target(self):
        target = Path("/isolated folder/中文 target")
        argv = probe.fixture_arguments(Path('/fixture.exe'), Path('/controller.qs'), target)
        self.assertEqual(argv[argv.index('--root') + 1], str(target))
        self.assertEqual([arg for arg in argv if arg.startswith('TargetDir=')], ['TargetDir=' + str(target)])
        self.assertEqual(argv[argv.index('--lang') + 1], 'zh_CN')
        self.assertEqual(argv[argv.index('--cache-path') + 1], str(Path('/tmp') / 'ifw-cache'))
        self.assertIn('PJProbeMarker=中文 space user@example.test', argv)

    def test_cli_root_alone_cannot_pass_gui_contract(self):
        data = self.records()
        row = data[0][0]
        argv = json.loads(row['commandLine'])
        row['commandLine'] = json.dumps([arg for arg in argv if not arg.startswith('TargetDir=')])
        with self.assertRaisesRegex(AssertionError, 'TargetDir positional'):
            self.check(data)

    def test_duplicate_initial_target_cannot_pass(self):
        data = self.records()
        row = data[0][0]
        row['commandLine'] = json.dumps(json.loads(row['commandLine']) + ['TargetDir=/wrong'])
        with self.assertRaisesRegex(AssertionError, 'TargetDir positional'):
            self.check(data)

    def test_positive_record_contract(self):
        self.check(self.records())

    @unittest.skipUnless(shutil.which('node'), 'Node is unavailable')
    def test_controller_callbacks(self):
        subprocess.run(['node', str(Path(__file__).with_name('test_windows_installer_live.js'))], check=True, timeout=20)

    def test_positional_slash_normalization(self):
        data = self.records()
        for row in (data[0][4], data[0][8]):
            argv = json.loads(row['commandLine'])
            position = next(i for i, arg in enumerate(argv) if arg.startswith('TargetDir='))
            argv[position] = argv[position].replace('/', '\\')
            row['commandLine'] = json.dumps(argv)
        self.check(data)

    def test_negative_cases(self):
        for mutation in ('same_pid', 'missing_script', 'stale_root', 'wrong_language', 'english_standard_page', 'english_buttons', 'unexpected_page', 'stale_field', 'wrong_executable', 'lingering_previous', 'untranslated_custom', 'wrong_cache', 'wrong_temp', 'missing_marker'):
            with self.subTest(mutation=mutation):
                data = self.records()
                row = data[0][4]
                if mutation == 'wrong_cache': row['commandLine'] = row['commandLine'].replace('/tmp/ifw-cache', '/outside-cache')
                elif mutation == 'wrong_temp': row['TEMP'] = '/outside-temp'
                elif mutation == 'missing_marker': row['commandLine'] = row['commandLine'].replace('user@example.test', 'lost')
                elif mutation == 'lingering_previous': row['liveFixturePids'] = [10, 11]
                elif mutation == 'untranslated_custom': data[0][1]['description'] = 'English'
                elif mutation == 'same_pid': row['pid'] = 10
                elif mutation == 'missing_script': row['commandLine'] = json.dumps(['/fixture.exe'])
                elif mutation == 'stale_root': row['commandLine'] = data[0][0]['commandLine']
                elif mutation == 'wrong_language': row['language'] = 'zh_CN'
                elif mutation == 'english_standard_page': data[0][0]['message'] = 'Welcome to the PlotJuggler 4 zh-CN Setup.'
                elif mutation == 'english_buttons': data[0][0]['nextButton'] = '&Next >'
                elif mutation == 'unexpected_page': row['kind'] = 'unexpected-page'
                elif mutation == 'stale_field': data[0][5]['field'] = '/old'
                elif mutation == 'wrong_executable': row['executable'] = '/other.exe'
                with self.assertRaises((AssertionError, ValueError)):
                    self.check(data)

if __name__ == '__main__': unittest.main()
