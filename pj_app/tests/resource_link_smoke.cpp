// SPDX-License-Identifier: MPL-2.0
#include <QCoreApplication>
#include <QFile>
#include <QJsonDocument>

int main(int argc, char** argv) {
  QCoreApplication app(argc, argv);
  QFile manifest(QStringLiteral(":/resources/memes/zh_CN.json"));
  if (!manifest.open(QIODevice::ReadOnly)) {
    return 1;
  }
  return QJsonDocument::fromJson(manifest.readAll()).isObject() ? 0 : 2;
}
