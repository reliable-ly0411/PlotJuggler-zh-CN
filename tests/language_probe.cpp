// SPDX-License-Identifier: MPL-2.0
// Process-level fixture; never installed or copied into production packages.
#include "app_language.h"
#include "app_settings.h"
#include <QApplication>
#include <QDialogButtonBox>
#include <QDir>
#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QLocale>
#include <QPushButton>
#include <QSettings>
#include <iostream>

int main(int argc, char** argv)
{
  QApplication app(argc, argv);
  if (!configureApplicationSettings(app))
  {
    return 2;
  }
  const auto arguments = app.arguments();
  const auto value = [&](const QString& option) {
    const int index = arguments.indexOf(option);
    return index >= 0 && index + 1 < arguments.size() ? arguments[index + 1] : QString();
  };
  if (arguments.contains("--set-language"))
  {
    QSettings settings;
    settings.setValue("Preferences::language", value("--set-language"));
    settings.sync();
    return settings.status() == QSettings::NoError ? 0 : 1;
  }
  QLocale::setDefault(QLocale(QLocale::German, QLocale::Germany));
  const auto before = QLocale();
  installApplicationLanguage(app);
  QDialogButtonBox buttons(QDialogButtonBox::Close | QDialogButtonBox::Cancel);
  const QJsonObject report{
    { "arguments", QJsonArray::fromStringList(arguments.mid(1)) },
    { "directory", QDir::currentPath() },
    { "language", app.property("interfaceLanguage").toString() },
    { "menu", QCoreApplication::translate("MainWindow", "App") },
    { "close", buttons.button(QDialogButtonBox::Close)->text() },
    { "qt_file_name", QCoreApplication::translate("QFileDialog", "File &name:") },
    { "fallback", QCoreApplication::translate("UnknownThirdPartyPlugin", "Untranslated sample") },
    { "numeric_locale_preserved", QLocale() == before && QLocale().toString(1.25) == "1,25" },
    { "settings_file", QSettings().fileName() }
  };
  const auto bytes = QJsonDocument(report).toJson();
  if (!value("--probe-output").isEmpty())
  {
    QFile file(value("--probe-output"));
    if (!file.open(QIODevice::WriteOnly) || file.write(bytes) != bytes.size())
    {
      return 3;
    }
  }
  else
  {
    std::cout << bytes.constData();
  }
  return value("--exit-code").toInt();
}
