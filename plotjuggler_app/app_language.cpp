// SPDX-License-Identifier: MPL-2.0
#include "app_language.h"
#include <QApplication>
#include <QDir>
#include <QLibraryInfo>
#include <QLocale>
#include <QSettings>
#include <QTranslator>
#include <QDebug>

QString normalizedApplicationLanguage(QString language)
{
  language = language.trimmed().section('.', 0, 0).section('@', 0, 0);
  language.replace('-', '_');
  const QStringList parts = language.split('_', Qt::SkipEmptyParts);
  if (parts.isEmpty() || parts.first().compare("zh", Qt::CaseInsensitive) != 0) return "en_US";
  // Explicit script takes precedence over region, irrespective of casing.
  for (const auto& part : parts.mid(1))
  {
    if (part.compare("Hans", Qt::CaseInsensitive) == 0) return "zh_CN";
    if (part.compare("Hant", Qt::CaseInsensitive) == 0) return "zh_TW";
  }
  for (const auto& part : parts.mid(1))
  {
    if (part.compare("TW", Qt::CaseInsensitive) == 0 ||
        part.compare("HK", Qt::CaseInsensitive) == 0 ||
        part.compare("MO", Qt::CaseInsensitive) == 0) return "zh_TW";
    if (part.compare("CN", Qt::CaseInsensitive) == 0 ||
        part.compare("SG", Qt::CaseInsensitive) == 0) return "zh_CN";
  }
  return "zh_CN"; // A bare Chinese locale uses Simplified Chinese.
}

QString selectedApplicationLanguage(const QApplication& app)
{
  QSettings settings;
  const QStringList system_languages = QLocale::system().uiLanguages();
  QString language = settings.contains("Preferences::language")
      ? settings.value("Preferences::language").toString()
      : (system_languages.isEmpty() ? QStringLiteral("en_US") : system_languages.first());
  const auto arguments = app.arguments();
  for (int i = 1; i < arguments.size(); ++i)
  {
    if (arguments[i] == "--") break;
    if (arguments[i].startsWith("--language=")) language = arguments[i].mid(11);
    else if (arguments[i] == "--language" && i + 1 < arguments.size() &&
             !arguments[i + 1].startsWith("--")) language = arguments[++i];
  }
  return normalizedApplicationLanguage(language);
}

void installApplicationLanguage(QApplication& app)
{
  Q_INIT_RESOURCE(i18n);
  const QString language = selectedApplicationLanguage(app);
  app.setProperty("interfaceLanguage", language);
  if (language == "en_US") return;
  // Interface language must not change numeric parsing, protocol or export locales.
  auto* qt = new QTranslator(&app);
  const QString qt_catalog = "qtbase_" + language;
  if (qt->load(":/i18n/" + qt_catalog + ".qm") ||
      qt->load(qt_catalog, app.applicationDirPath() + "/translations") ||
      qt->load(qt_catalog, QLibraryInfo::location(QLibraryInfo::TranslationsPath)))
    app.installTranslator(qt);
  auto* catalog = new QTranslator(&app);
  if (catalog->load(":/i18n/plotjuggler_" + language + ".qm")) app.installTranslator(catalog);
  else qWarning() << "Translation catalog is missing:" << language;
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
