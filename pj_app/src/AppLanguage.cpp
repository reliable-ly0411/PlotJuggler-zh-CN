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
  if (language_ == "zh_CN"_L1) {
    catalog_loaded_ = translator_.load(u":/i18n/plotjuggler4_zh_CN.qm"_s) && app_.installTranslator(&translator_);
    if (!catalog_loaded_) {
      qWarning("Simplified Chinese translation catalog is missing; using English source text");
    }
  }
}

AppLanguage::~AppLanguage() {
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
