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
      test.scenario != "start") return false;
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
  return true;
}
