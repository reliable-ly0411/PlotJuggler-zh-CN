// SPDX-License-Identifier: MPL-2.0
#include "app_language.h"
#include <QApplication>
#include <QDir>
#include <QLibraryInfo>
#include <QLocale>
#include <QSettings>
#include <QTranslator>
#include <QDebug>

void installApplicationLanguage(QApplication& app)
{
  QString language = QSettings().value("Preferences::language", "zh_CN").toString();
  const auto arguments = app.arguments();
  for (int i = 1; i < arguments.size(); ++i)
  {
    if (arguments[i].startsWith("--language=")) language = arguments[i].mid(11);
    else if (arguments[i] == "--language" && i + 1 < arguments.size()) language = arguments[++i];
  }
  if (language != "zh_CN" && language != "zh-CN") return;
  QLocale::setDefault(QLocale(QLocale::Chinese, QLocale::China));
  auto* qt = new QTranslator(&app);
  if (qt->load("qtbase_zh_CN", app.applicationDirPath() + "/translations") ||
      qt->load("qtbase_zh_CN", QLibraryInfo::location(QLibraryInfo::TranslationsPath)))
    app.installTranslator(qt);
  auto* catalog = new QTranslator(&app);
  if (catalog->load(":/i18n/plotjuggler_zh_CN.qm")) app.installTranslator(catalog);
  else qWarning() << "Simplified Chinese translation catalog is missing";
}
