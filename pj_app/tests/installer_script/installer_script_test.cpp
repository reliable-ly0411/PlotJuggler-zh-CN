// SPDX-License-Identifier: MPL-2.0
#include <QCoreApplication>
#include <QDebug>
#include <QFile>
#include <QJSEngine>

int main(int argc, char** argv) {
  QCoreApplication app(argc, argv);
  QFile source(QString::fromUtf8(PJ_INSTALLER_SCRIPT_PATH));
  if (!source.open(QFile::ReadOnly)) {
    qCritical() << "Cannot read production installer script";
    return 1;
  }
  QJSEngine engine;
  auto result = engine.evaluate(QString::fromUtf8(source.readAll()));
  if (!result.isError()) {
    result = engine.evaluate(QString::fromUtf8(R"JS(
function equal(actual, expected) {
    if (JSON.stringify(actual) !== JSON.stringify(expected))
        throw new Error('Restart argv mismatch: ' + JSON.stringify(actual));
}
var input = ['setup.exe', '--verbose', '--lang', 'zh_CN', '--script', 'controller.qs',
             '--cache-path', 'C:/cache', 'Marker=中文 space user@example.test',
             '--root', 'C:/old', 'TargetDir=C:/old'];
var original = JSON.stringify(input);
equal(restartArguments(input, 'en_US', 'C:/new 中文'),
      ['--lang', 'en_US', '--verbose', '--script', 'controller.qs', '--cache-path',
       'C:/cache', 'Marker=中文 space user@example.test', '--root', 'C:/new 中文',
       'TargetDir=C:/new 中文']);
if (JSON.stringify(input) !== original) throw new Error('Original argv mutated');
equal(restartArguments(['setup.exe', '--lang=en_US', '-t=old', '--', 'literal'],
                       'zh_CN', 'C:/chosen'),
      ['--lang', 'zh_CN', '-t=C:/chosen', '--', 'literal', 'TargetDir=C:/chosen']);
equal(restartArguments(['setup.exe'], 'zh_CN', 'C:/new'),
      ['--lang', 'zh_CN', 'TargetDir=C:/new']);
// #55: all six directed language changes and Traditional locale aliases.

var languages = ['zh_CN', 'en_US', 'zh_TW'];
for (var source = 0; source < 3; source++) {
  for (var destination = 0; destination < 3; destination++) {
    if (source === destination) continue;
    var target = 'C:\\測試 space\\new target\\';
    var language = installerLanguageForIndex(destination, 3);
    equal(language, languages[destination]);
    equal(restartArguments(['setup.exe','--lang',languages[source],
      '--offline-only','--root','old target','TargetDir=obsolete','--proxy','http://localhost:8080'],
      language,target),
      ['--lang',language,'--offline-only','--root',target,'--proxy','http://localhost:8080','TargetDir='+target]);
  }
}
for (var locale of ['zh_TW','zh-Hant-TW','zh_HK','zh_MO','ZH_tw']) {
  equal(installerLanguageIndex(locale,3),2);
  equal(installerLanguageIndex(locale,2),1);
}
for (var locale of ['zh_CN','zh-Hans-CN','zh_SG','zh']) equal(installerLanguageIndex(locale,3),0);
for (var locale of ['en_US','de_DE','']) equal(installerLanguageIndex(locale,3),1);
for (var index=0; index<3; index++) equal(installerLanguageForIndex(index,3),languages[index]);
equal(installerLanguageForIndex(2,2),'en_US');
equal(installerLanguageForIndex(-1,3),'en_US');
equal(restartArguments(['setup.exe','--lang=en_US','-t=old','--','literal'], 'zh_TW','new'),
      ['--lang','zh_TW','-t=new','--','literal','TargetDir=new']);

// Mock only official GuiProxy APIs. In particular, rejectPage does not exist;
// the old production branch throws TypeError here before it closes the dialog.
var events = [], targetExists = true, answer = 1;
var gui = {rejectWithoutPrompt: function() { events.push('quit'); }};
var QInstaller = {ComponentSelection: 3};
var QMessageBox = {Yes: 1, No: 2,
    question: function() { events.push('confirm'); return answer; },
    warning: function() { events.push('warning'); }};
var console = {log: function() {}};
function qsTranslate(context, text) { return text; }
var installer = {
    value: function() { return 'C:/fixture'; },
    fileExists: function() { return targetExists; },
    environmentVariable: function() { return 'C:/Windows'; },
    execute: function() { events.push('execute'); return ['PJ_REPLACEMENT_FAILED:identity', 1]; }
};
replacementGuard = 'AA=='; // Transport is mocked; no process or registry writes.
if (typeof gui.rejectPage !== 'undefined') throw new Error('Invented GuiProxy API');
for (var choice = 1; choice <= 2; ++choice) {
    events = []; answer = choice; targetExists = true;
    replacementAttempted = false; replacementBlocked = false;
    Component.prototype.componentSelectionPageEntered.call({});
    equal(events, choice === 1 ? ['confirm', 'execute', 'warning', 'quit'] : ['confirm', 'quit']);
    if (!replacementBlocked) throw new Error('Replacement failure was not persistent');
    targetExists = false;
    Component.prototype.componentSelectionPageEntered.call({});
    if (events[events.length - 1] !== 'quit') throw new Error('Blocked replacement did not close');
    equal(events.filter(function(event) { return event === 'confirm'; }), ['confirm']);
}
)JS"));
  }
  if (result.isError()) {
    qCritical().noquote() << result.toString();
    return 1;
  }
  qInfo() << "PASS: production language mapping, restart argv and fail-closed replacement in Qt QJSEngine";
  return 0;
}
