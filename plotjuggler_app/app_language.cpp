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
  language = (language == "zh_CN" || language == "zh-CN") ? "zh_CN" : "en_US";
  app.setProperty("interfaceLanguage", language);
  if (language != "zh_CN") return;
  QLocale::setDefault(QLocale(QLocale::Chinese, QLocale::China));
  auto* qt = new QTranslator(&app);
  if (qt->load("qtbase_zh_CN", app.applicationDirPath() + "/translations") ||
      qt->load("qtbase_zh_CN", QLibraryInfo::location(QLibraryInfo::TranslationsPath)))
    app.installTranslator(qt);
  auto* catalog = new QTranslator(&app);
  if (catalog->load(":/i18n/plotjuggler_zh_CN.qm")) app.installTranslator(catalog);
  else qWarning() << "Simplified Chinese translation catalog is missing";
}

// Qt 5.15 standard button keys; our own translations also work without qtbase_zh_CN.qm.
static const char* const standardButtonKeys[] = {
  QT_TRANSLATE_NOOP("QPlatformTheme", "OK"),
  QT_TRANSLATE_NOOP("QPlatformTheme", "Save"),
  QT_TRANSLATE_NOOP("QPlatformTheme", "Save All"),
  QT_TRANSLATE_NOOP("QPlatformTheme", "Open"),
  QT_TRANSLATE_NOOP("QPlatformTheme", "&Yes"),
  QT_TRANSLATE_NOOP("QPlatformTheme", "Yes to &All"),
  QT_TRANSLATE_NOOP("QPlatformTheme", "&No"),
  QT_TRANSLATE_NOOP("QPlatformTheme", "N&o to All"),
  QT_TRANSLATE_NOOP("QPlatformTheme", "Abort"),
  QT_TRANSLATE_NOOP("QPlatformTheme", "Retry"),
  QT_TRANSLATE_NOOP("QPlatformTheme", "Ignore"),
  QT_TRANSLATE_NOOP("QPlatformTheme", "Close"),
  QT_TRANSLATE_NOOP("QPlatformTheme", "Cancel"),
  QT_TRANSLATE_NOOP("QPlatformTheme", "Discard"),
  QT_TRANSLATE_NOOP("QPlatformTheme", "Help"),
  QT_TRANSLATE_NOOP("QPlatformTheme", "Apply"),
  QT_TRANSLATE_NOOP("QPlatformTheme", "Reset"),
  QT_TRANSLATE_NOOP("QPlatformTheme", "Restore Defaults"),
};
