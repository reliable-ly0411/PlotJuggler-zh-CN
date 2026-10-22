import contextlib
import importlib.util
import io
import json
from pathlib import Path
import unittest
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
            if stage:
                argv += ['TargetDir=' + str(targets[stage])]
            base = dict(language=lang, pid=10 + stage, target=str(targets[stage]),
                        executable=str(fixture), commandLine=json.dumps(argv), liveFixturePids=[10 + stage])
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

    def test_positive_record_contract(self):
        self.check(self.records())

    @unittest.skipUnless(shutil.which('node'), 'Node is unavailable')
    def test_controller_callbacks(self):
        subprocess.run(['node', str(Path(__file__).with_name('test_windows_installer_live.js'))], check=True, timeout=20)

    def test_positional_slash_normalization(self):
        data = self.records()
        for row in (data[0][4], data[0][8]):
            argv = json.loads(row['commandLine'])
            argv[-1] = argv[-1].replace('/', '\\')
            row['commandLine'] = json.dumps(argv)
        self.check(data)

    def test_negative_cases(self):
        for mutation in ('same_pid', 'missing_script', 'stale_root', 'wrong_language', 'english_standard_page', 'english_buttons', 'unexpected_page', 'stale_field', 'wrong_executable', 'lingering_previous', 'untranslated_custom'):
            with self.subTest(mutation=mutation):
                data = self.records()
                row = data[0][4]
                if mutation == 'lingering_previous': row['liveFixturePids'] = [10, 11]
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
