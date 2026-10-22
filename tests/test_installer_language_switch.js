// SPDX-License-Identifier: MPL-2.0
// Script-level tests only: native IFW/PowerShell UI remains a Windows test.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const script = fs.readFileSync(path.join(__dirname, '../packaging/installer/packages/io.plotjuggler.application/meta/installscript.qs'), 'utf8');
function fixture(currentLanguage, selection, succeeds = true, probeResult = ['4321\r\n', 0]) {
  const events = [];
  const widget = { language: { currentIndex: selection }, applyLanguage: { enabled: true } };
  const context = {
    component: { userInterface: () => widget },
    installer: {
      value: key => ({ UILanguage: currentLanguage, InstallerFilePath: "C:/My Folder/it's safe; & setup.exe" })[key],
      environmentVariable: () => 'C:/Windows',
      execute: () => probeResult,
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
  assert.ok(command.includes("'-" + "-lang', '" + expected + "'"));
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
