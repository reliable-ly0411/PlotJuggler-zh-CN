// SPDX-License-Identifier: MPL-2.0
// Script-level tests only: native IFW/PowerShell UI remains a Windows test.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const script = fs.readFileSync(path.join(__dirname, '../packaging/installer/packages/io.plotjuggler.application/meta/installscript.qs'), 'utf8');
function fixture(currentLanguage, selection, succeeds = true, probeResult = [JSON.stringify({pid:4321, argv:['setup.exe', '--lang=en_US', '--proxy', 'http://user:pass@host/', 'Extra=quote"value', '--root', 'C:/old']}), 0]) {
  const events = [];
  const widget = { language: { currentIndex: selection }, applyLanguage: { enabled: true } };
  const context = {
    component: { userInterface: () => widget },
    installer: {
      value: key => ({ UILanguage: currentLanguage, InstallerFilePath: "C:/My Folder/it's safe; & setup.exe", TargetDir: 'C:/chosen folder/中文' })[key],
      environmentVariable: () => 'C:/Windows',
      execute: (program, args) => { widget.probe = args.at(-1); return probeResult; },
      executeDetached: (program, args) => { events.push({ program, args }); return succeeds; },
    },
    gui: { rejectWithoutPrompt: () => events.push('exit') },
    qsTranslate: (context, source) => source,
    QMessageBox: { warning: () => events.push('warning') },
  };
  vm.createContext(context);
  vm.runInContext(script, context);
  context.Component.prototype.applyLanguage();
  return { events, widget };
}
for (const [current, selection, expected] of [['en_US', 0, 'zh_CN'], ['zh_CN', 1, 'en_US']]) {
  const { events, widget } = fixture(current, selection);
  assert.equal(events.length, 2);
  assert.equal(events[1], 'exit');
  assert.equal(widget.applyLanguage.enabled, false);
  assert.match(events[0].program, /System32\/WindowsPowerShell\/v1.0\/powershell.exe$/);
  const command = events[0].args.at(-1);
  assert.ok(command.includes("'C:/My Folder/it''s safe; & setup.exe'"));
  assert.ok(command.includes('"--lang" "' + expected + '"'));
  assert.ok(command.includes('"--proxy" "http://user:pass@host/"'));
  assert.ok(command.includes('"--root" "C:/chosen folder/中文"'));
  assert.ok(command.includes('"TargetDir=C:/chosen folder/中文"'));
  assert.ok(!command.includes('--lang=en_US'));
  assert.ok(widget.probe.includes('$child.ParentProcessId'));
  assert.ok(widget.probe.includes('$parent.ExecutablePath'));
  assert.ok(widget.probe.includes('CommandLineToArgvW'));
  assert.ok(widget.probe.includes('GetLongPathName'));
  assert.ok(widget.probe.includes('if (!$length -or $length -ge 32768)'));
  assert.ok(widget.probe.includes('(Resolve-PJLongPath $parent.ExecutablePath)'));
  assert.ok(command.indexOf('Wait-Process') < command.indexOf('Start-Process'));
  assert.ok(command.includes('-Timeout 30'));
}
assert.equal(fixture('zh_CN', 0).events.length, 0);
const failed = fixture('en_US', 0, false);
assert.equal(failed.events.at(-1), 'warning');
assert.equal(failed.widget.applyLanguage.enabled, true);
assert.ok(!failed.events.includes('exit'));

for (const probe of [[], ['', 1], ['Access denied', 0], ['0', 0]]) {
  const denied = fixture('en_US', 0, true, probe);
  assert.deepEqual(denied.events, ['warning']);
  assert.equal(denied.widget.applyLanguage.enabled, true);
}
for (const [isInstaller, isCli] of [[false, false], [true, true], [false, true]]) {
  const context = { installer: { isInstaller: () => isInstaller, isCommandLineInstance: () => isCli } };
  vm.createContext(context);
  vm.runInContext(script, context);
  // No component/gui API is supplied: touching one would fail this guard test.
  context.Component.prototype.installerLoaded();
}
console.log('Installer language switch script checks passed');

// Test Windows argument escaping independently of the shell grammar.
const quoting = {};
vm.createContext(quoting);
vm.runInContext(script, quoting);
assert.equal(quoting.quoteWindowsArgument(''), '""');
assert.equal(quoting.quoteWindowsArgument('a b'), '"a b"');
assert.equal(quoting.quoteWindowsArgument('a"b'), '"a' + '\\' + '"b"');
assert.equal(quoting.quoteWindowsArgument('x\\'), '"x' + '\\'.repeat(2) + '"');
assert.equal(quoting.quoteWindowsArgument('x\\"y'), '"x' + '\\'.repeat(3) + '"y"');
for (const invalid of [{pid:4321, argv:[]}, {pid:4321, argv:[1]}, {pid:'4321;evil', argv:['setup.exe']}]) {
  assert.deepEqual(fixture('en_US', 0, true, [JSON.stringify(invalid),0]).events, ['warning']);
}
assert.deepEqual(Array.from(quoting.restartArguments(['setup.exe','--lang','en_US','--lang=fr_FR','-t=old','TargetDir=old','--','literal'], 'zh_CN', 'C:/new')), ['--lang','zh_CN','-t=C:/new','--','literal','TargetDir=C:/new']);
// Optional real PowerShell parse/control-flow test; no process is started.
const cp = require('node:child_process'), os = require('node:os');
const shell = process.platform === 'win32' ? 'powershell.exe' : 'pwsh';
const available = cp.spawnSync(shell, ['-NoProfile', '-Command', 'exit 0']);
if (!available.error && available.status === 0) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'restart test '));
  try {
    const result = fixture('en_US', 0);
    const data = path.join(dir, 'fixture.json');
    fs.writeFileSync(data, JSON.stringify({probe:result.widget.probe, command:result.events[0].args.at(-1)}));
    const run = cp.spawnSync(shell, ['-NoProfile','-NonInteractive','-File',path.join(__dirname,'test_installer_restart.ps1'),'-FixturePath',data], {encoding:'utf8',timeout:30000});
    assert.equal(run.status,0,run.stdout + run.stderr);
    console.log(run.stdout.trim());
  } finally { fs.rmSync(dir,{recursive:true,force:true}); }
} else { console.log('SKIP: PowerShell runtime unavailable'); }

// IFW 4.10 Component::languageChanged -> ScriptEngine::callScriptMethod extracts
// retranslateUi then QJSValue::call(arguments), not callWithInstance(context).
// Exercise detached/global and foreign native-like receivers, not only method
// calls on Component.prototype (which hid the production failure).
for (const receiver of ['detached', 'native-like', 'script-instance']) {
  const values = {}, shown = {};
  let language = 'zh_CN', existing = false, maintained = false;
  const translations = {
    'Choose Installation Directory': '选择安装目录',
    'Please select where PlotJuggler 4 will be installed:': '请选择 PlotJuggler 4 的安装位置：',
  };
  const context = {
    installer: {
      fileExists: name => name.endsWith('/maintenancetool.exe') ? maintained : existing,
      setValue: (key, value) => { values[key] = value; },
    },
    qsTranslate: (_, source) => language === 'zh_CN' ? (translations[source] || '中文:' + source) : source,
  };
  vm.createContext(context);
  vm.runInContext(script, context);
  const hook = context.Component.prototype.retranslateUi;
  const invoke = () => receiver === 'detached' ? hook() : hook.call(receiver === 'native-like' ? Object.create(null) : Object.create(context.Component.prototype));
  invoke(); // The reserved hook is safe before a GUI page exists.
  context.targetDirectoryPage = {
    targetDirectory: {text: 'C:/isolated 中文 target'},
    description: {setText: text => { shown.description = text; }},
    warning: {setText: text => { shown.warning = text; }},
  };
  invoke();
  assert.equal(context.targetDirectoryPage.windowTitle, '选择安装目录');
  assert.equal(shown.description, '请选择 PlotJuggler 4 的安装位置：');
  assert.equal(shown.warning, '');
  assert.equal(values.TargetDir, 'C:/isolated 中文 target');
  existing = true;
  invoke();
  assert.match(shown.warning, /中文:.*existing directory/);
  maintained = true;
  invoke();
  assert.match(shown.warning, /中文:.*Existing installation detected/);
  language = 'en_US';
  context.targetDirectoryPage.targetDirectory.text = 'C:/another isolated target';
  invoke();
  assert.equal(context.targetDirectoryPage.windowTitle, 'Choose Installation Directory');
  assert.equal(shown.description, 'Please select where PlotJuggler 4 will be installed:');
  assert.ok(!shown.warning.startsWith('中文:'));
  assert.equal(values.TargetDir, 'C:/another isolated target');
}
console.log('Reserved IFW translation hook receiver regression checks passed');
