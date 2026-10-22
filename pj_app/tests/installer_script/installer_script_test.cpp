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
)JS"));
  }
  if (result.isError()) {
    qCritical().noquote() << result.toString();
    return 1;
  }
  qInfo() << "PASS: production restart argv in Qt QJSEngine (not Node)";
  return 0;
}
