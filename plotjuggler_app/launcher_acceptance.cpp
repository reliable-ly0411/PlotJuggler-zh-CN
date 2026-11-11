// SPDX-License-Identifier: MPL-2.0
#include "launcher_acceptance.h"
#include <QApplication>
#include <QComboBox>
#include <QCryptographicHash>
#include <QDialog>
#include <QDialogButtonBox>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QKeyEvent>
#include <QLabel>
#include <QMouseEvent>
#include <QPushButton>
#include <QRegularExpression>
#include <QSaveFile>
#include <QTimer>
#include <QDebug>

static bool plainPath(QString path) {
  path = QDir::cleanPath(QFileInfo(path).absoluteFilePath());
  while (!path.isEmpty()) {
    QFileInfo info(path);
    if (info.isSymLink()) return false;
    const QString parent = info.dir().absolutePath();
    if (parent == path) break;
    path = parent;
  }
  return true;
}
static QString hashFile(const QString& path) {
  QFile f(path);
  if (!f.exists()) return QStringLiteral("missing");
  if (!f.open(QIODevice::ReadOnly)) return {};
  QCryptographicHash hash(QCryptographicHash::Sha256);
  if (!hash.addData(&f)) return {};
  return QString::fromLatin1(hash.result().toHex());
}
bool parseLauncherAcceptance(const QStringList& args, LauncherAcceptance& test, QStringList& forwarded) {
  bool requested = false;
  for (const auto& arg : args) {
    if (arg == "--") break;
    if (arg.startsWith("--self-test-launcher") || arg.startsWith("--launcher-test")) {
      requested = true;
      if (arg != "--self-test-launcher-ui" && arg != "--launcher-test-scenario" && arg != "--launcher-test-nonce") return false;
    }
  }
  if (!requested) { forwarded = args; return true; }
  QString config, nonce;
  int outputs = 0, scenarios = 0, nonces = 0, configs = 0;
  bool launch = false;
  for (int i = 0; i < args.size(); ++i) {
    const QString a = args[i];
    if (a == "--") { forwarded += args.mid(i); break; }
    if (a == "--launch") launch = true;
    if (a == "--self-test-launcher-ui" || a == "--launcher-test-scenario" || a == "--launcher-test-nonce") {
      if (++i >= args.size() || args[i].isEmpty() || args[i].startsWith("--")) return false;
      if (a == "--self-test-launcher-ui") { test.output = args[i]; ++outputs; }
      else if (a == "--launcher-test-scenario") { test.scenario = args[i]; ++scenarios; }
      else { nonce = args[i]; ++nonces; }
      continue;
    }
    if (a == "--config-dir") {
      if (i + 1 >= args.size() || args[i+1].isEmpty() || args[i+1].startsWith("--")) return false;
      config = args[i+1]; ++configs;
    } else if (a.startsWith("--config-dir=")) { config = a.mid(13); ++configs; }
    forwarded << a;
  }
  test.enabled = outputs || scenarios || nonces;
  if (!test.enabled) return true;
  if (outputs != 1 || scenarios != 1 || nonces != 1 || configs != 1 || launch || (nonce.size() != 64 || !QRegularExpression("^[0-9a-f]{64}$").match(nonce).hasMatch()) ||
      (test.scenario != "start-en_US" && test.scenario != "start-zh_CN" && test.scenario != "start-zh_TW" && test.scenario != "cancel")) return false;
  const QFileInfo ci(config), oi(test.output);
  if (!ci.isAbsolute() || !oi.isAbsolute() || !ci.isDir() || ci.fileName() != "config" ||
      oi.exists() || !plainPath(config) || !plainPath(test.output) || ci.dir().absolutePath() != oi.dir().absolutePath() ||
      !oi.fileName().startsWith("case-") || oi.fileName().size() <= 5) return false;
  const QString root = ci.dir().absolutePath();
  const QString appdir = QCoreApplication::applicationDirPath();
  if (root == appdir || root.startsWith(appdir + "/") || appdir.startsWith(root + "/")) return false;
  QFile marker(QDir(root).filePath("launcher-acceptance.json"));
  if (!plainPath(marker.fileName()) || !marker.open(QIODevice::ReadOnly)) return false;
  QJsonParseError error;
  const auto doc = QJsonDocument::fromJson(marker.readAll(), &error);
  if (error.error != QJsonParseError::NoError || !doc.isObject()) return false;
  const auto m = doc.object();
  const QString ini = "PlotJuggler/io.plotjuggler.PlotJuggler.zh-CN.ini";
  const QString inipath = QDir(config).filePath(ini);
  if (m.value("schema").toInt() != 1 || m.value("purpose").toString() != "launcher-gui-acceptance" ||
      m.value("nonce").toString() != nonce || m.value("ini").toString() != ini ||
      !plainPath(inipath) || hashFile(inipath).isEmpty() || hashFile(inipath) != m.value("before_sha256").toString()) return false;
  if (!QDir().mkdir(test.output)) return false;
  if (test.scenario.startsWith("start-")) test.target = test.scenario.mid(6);
  return true;
}
static void key(QWidget* widget, int k) {
  QKeyEvent press(QEvent::KeyPress, k, Qt::NoModifier), release(QEvent::KeyRelease, k, Qt::NoModifier);
  QApplication::sendEvent(widget, &press); QApplication::sendEvent(widget, &release);
}
static void click(QWidget* widget) {
  QPoint p = widget->rect().center();
  QMouseEvent press(QEvent::MouseButtonPress, p, Qt::LeftButton, Qt::LeftButton, Qt::NoModifier);
  QMouseEvent release(QEvent::MouseButtonRelease, p, Qt::LeftButton, Qt::NoButton, Qt::NoModifier);
  QApplication::sendEvent(widget, &press); QApplication::sendEvent(widget, &release);
}
void driveLauncherAcceptance(QDialog* dialog, const LauncherAcceptance& test) {
  QTimer::singleShot(150, dialog, [dialog, test] {
    auto combos = dialog->findChildren<QComboBox*>("launcherLanguage");
    auto starts = dialog->findChildren<QPushButton*>("launcherStart");
    auto boxes = dialog->findChildren<QDialogButtonBox*>();
    auto fail = [] { qCritical() << "launcher acceptance failed"; qApp->exit(3); };
    if (!dialog->isVisible() || combos.size() != 1 || starts.size() != 1 || boxes.size() != 1) { fail(); return; }
    auto combo = combos.first(); auto start = starts.first(); auto cancel = boxes.first()->button(QDialogButtonBox::Cancel);
    if (!cancel || !combo->isVisible() || !combo->isEnabled() || !start->isVisible() || !start->isEnabled() || !cancel->isVisible() || !cancel->isEnabled()) { fail(); return; }
    QJsonArray labels, options;
    for (auto label : dialog->findChildren<QLabel*>()) labels.append(label->text());
    for (int i=0; i<combo->count(); ++i) options.append(combo->itemText(i));
    QJsonObject report{{"title",dialog->windowTitle()}, {"labels",labels}, {"options",options},
      {"start",start->text()}, {"cancel",cancel->text()}, {"initial",combo->currentData().toString()},
      {"width",dialog->width()}, {"height",dialog->height()}, {"dpr",dialog->devicePixelRatioF()},
      {"platform",QGuiApplication::platformName()}, {"qt",qVersion()}};
    if (!dialog->grab().save(QDir(test.output).filePath("before.png"))) { fail(); return; }
    if (!test.target.isEmpty()) {
      const int target = combo->findData(test.target);
      if (target < 0 || target == combo->currentIndex()) { fail(); return; }
      int changes = 0;
      const auto connection = QObject::connect(combo, QOverload<int>::of(&QComboBox::currentIndexChanged), dialog, [&changes](int){ ++changes; });
      for (int n = 0; n < combo->count() && combo->currentIndex() != target; ++n)
        key(combo, combo->currentIndex() < target ? Qt::Key_Down : Qt::Key_Up);
      QObject::disconnect(connection);
      if (!changes || combo->currentData().toString() != test.target) { fail(); return; }
    }
    report.insert("selected",combo->currentData().toString());
    if (!dialog->grab().save(QDir(test.output).filePath("after.png"))) { fail(); return; }
    QSaveFile file(QDir(test.output).filePath("report.json"));
    const auto bytes = QJsonDocument(report).toJson();
    if (!file.open(QIODevice::WriteOnly) || file.write(bytes) != bytes.size() || !file.commit()) { fail(); return; }
    click(test.scenario == "cancel" ? cancel : start);
  });
}
