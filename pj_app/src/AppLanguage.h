// SPDX-License-Identifier: MPL-2.0
#pragma once

#include <QString>
#include <QList>
#include <QTranslator>

class QCoreApplication;
class QSettings;

namespace PJ {

// Owns the startup translator for the entire UI lifetime. Construct after the
// settings backend is ready and before any window; destroy before the app.
// Changing the saved preference never retranslates an existing widget tree.
class AppLanguage final {
 public:
  static inline const QString kPreferenceKey = QStringLiteral("Preferences::language");

  // Canonical persisted code plus an endonym recognizable in every UI locale.
  struct Choice {
    QString code;
    QString native_name;
  };

  [[nodiscard]] static QList<Choice> supportedLanguages();

  // Accepts the exact supported locale codes, also with BCP-47 hyphens.
  // Other regions/scripts are not guessed; unsupported values use English.
  [[nodiscard]] static QString normalizedLanguage(const QString& language);

  // A fresh profile starts in Simplified Chinese, independent of the OS locale.
  [[nodiscard]] static QString preferredLanguage(const QSettings& settings);

  explicit AppLanguage(QCoreApplication& app, const QString& language);
  ~AppLanguage();

  AppLanguage(const AppLanguage&) = delete;
  AppLanguage& operator=(const AppLanguage&) = delete;

  [[nodiscard]] const QString& language() const {
    return language_;
  }
  [[nodiscard]] bool catalogLoaded() const {
    return catalog_loaded_;
  }

 private:
  QCoreApplication& app_;
  QString language_;
  QTranslator translator_;
  bool catalog_loaded_ = false;
  QByteArray previous_plugin_language_;
  bool previous_plugin_language_set_ = false;
};

}  // namespace PJ
