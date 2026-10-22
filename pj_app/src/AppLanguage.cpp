// SPDX-License-Identifier: MPL-2.0
#include "AppLanguage.h"

#include <QCoreApplication>
#include <QDebug>
#include <QSettings>
#include <QVariant>

using namespace Qt::StringLiterals;

// A reference from this object forces the resource object out of the static
// archive. Q_INIT_RESOURCE must live outside the PJ namespace. Register once
// even when tests construct more than one language owner in the same process.
static void initializeTranslationResources() {
  static const bool initialized = []() {
    Q_INIT_RESOURCE(pj_app_translations);
    return true;
  }();
  Q_UNUSED(initialized);
}

namespace PJ {

QString AppLanguage::normalizedLanguage(const QString& language) {
  return language == "zh_CN"_L1 || language == "zh-CN"_L1 ? u"zh_CN"_s : u"en_US"_s;
}

QString AppLanguage::preferredLanguage(const QSettings& settings) {
  return normalizedLanguage(settings.value(kPreferenceKey, u"zh_CN"_s).toString());
}

AppLanguage::AppLanguage(QCoreApplication& app, const QString& language)
    : app_(app), language_(normalizedLanguage(language)) {
  initializeTranslationResources();
  app_.setProperty("interfaceLanguage", language_);
  // Rebuilt pinned native plugins localize fixed text at its formatting site,
  // before it is combined with source code or server/user data. No credentials,
  // protocol data or persisted plugin configuration are passed through this hint.
  previous_plugin_language_set_ = qEnvironmentVariableIsSet("PLOTJUGGLER_UI_LANGUAGE");
  previous_plugin_language_ = qgetenv("PLOTJUGGLER_UI_LANGUAGE");
  qputenv("PLOTJUGGLER_UI_LANGUAGE", language_.toUtf8());
  if (language_ == "zh_CN"_L1) {
    catalog_loaded_ = translator_.load(u":/i18n/plotjuggler4_zh_CN.qm"_s) && app_.installTranslator(&translator_);
    if (!catalog_loaded_) {
      qWarning("Simplified Chinese translation catalog is missing; using English source text");
    }
  }
}

AppLanguage::~AppLanguage() {
  if (previous_plugin_language_set_) {
    qputenv("PLOTJUGGLER_UI_LANGUAGE", previous_plugin_language_);
  } else {
    qunsetenv("PLOTJUGGLER_UI_LANGUAGE");
  }
  if (catalog_loaded_) {
    app_.removeTranslator(&translator_);
  }
}

}  // namespace PJ

// Keep essential native-dialog buttons translated even when a Qt kit omits its
// qtbase catalog. Qt6 uses QPlatformTheme for QDialogButtonBox's standard labels.
[[maybe_unused]] static const char* const kStandardButtonKeys[] = {
    QT_TRANSLATE_NOOP("QPlatformTheme", "OK"),       QT_TRANSLATE_NOOP("QPlatformTheme", "Save"),
    QT_TRANSLATE_NOOP("QPlatformTheme", "Save All"), QT_TRANSLATE_NOOP("QPlatformTheme", "Open"),
    QT_TRANSLATE_NOOP("QPlatformTheme", "&Yes"),     QT_TRANSLATE_NOOP("QPlatformTheme", "Yes to &All"),
    QT_TRANSLATE_NOOP("QPlatformTheme", "&No"),      QT_TRANSLATE_NOOP("QPlatformTheme", "N&o to All"),
    QT_TRANSLATE_NOOP("QPlatformTheme", "Abort"),    QT_TRANSLATE_NOOP("QPlatformTheme", "Retry"),
    QT_TRANSLATE_NOOP("QPlatformTheme", "Ignore"),   QT_TRANSLATE_NOOP("QPlatformTheme", "Close"),
    QT_TRANSLATE_NOOP("QPlatformTheme", "Cancel"),   QT_TRANSLATE_NOOP("QPlatformTheme", "Discard"),
    QT_TRANSLATE_NOOP("QPlatformTheme", "Help"),     QT_TRANSLATE_NOOP("QPlatformTheme", "Apply"),
    QT_TRANSLATE_NOOP("QPlatformTheme", "Reset"),    QT_TRANSLATE_NOOP("QPlatformTheme", "Restore Defaults"),
};

// Qt 6.11.1's qtbase_zh_CN still carries the older QFileDialog labels and
// file-icon context. Keep the current runtime keys, including accelerators
// and platform disambiguation, in the application catalog as a small override.
[[maybe_unused]] static const char* const kQtFileDialogKeys[] = {
    QT_TRANSLATE_NOOP("QFileDialog", "&Look in:"),
    QT_TRANSLATE_NOOP("QFileDialog", "Files of &type:"),
    QT_TRANSLATE_NOOP("QAbstractFileIconProvider", "Drive"),
    QT_TRANSLATE_NOOP("QAbstractFileIconProvider", "File"),
    QT_TRANSLATE_NOOP("QAbstractFileIconProvider", "Unknown"),
};
[[maybe_unused]] static const struct {
  const char* source;
  const char* comment;
} kQtFileIconProviderKeys[] = {
    QT_TRANSLATE_NOOP3("QAbstractFileIconProvider", "File Folder", "Match Windows Explorer"),
    QT_TRANSLATE_NOOP3("QAbstractFileIconProvider", "Folder", "All other platforms"),
    QT_TRANSLATE_NOOP3("QAbstractFileIconProvider", "Alias", "macOS Finder"),
    QT_TRANSLATE_NOOP3("QAbstractFileIconProvider", "Shortcut", "All other platforms"),
};
