// SPDX-License-Identifier: MPL-2.0
#include <QJsonDocument>
#include <QJsonObject>
#include <QTest>

#include "AppLanguage.h"
#include "BrowserPersistence.h"

using namespace Qt::StringLiterals;

namespace PJ {
// Exercise the production decoder without constructing browser-only storage.
class BrowserPersistenceTestPeer {
 public:
  static QHash<QString, QVariant> decode(const QByteArray& encoded) {
    return BrowserPersistence::decodePreferences(encoded).values;
  }
};
}  // namespace PJ

class BrowserLanguageTest : public QObject {
  Q_OBJECT

 private slots:
  void canonicalLanguageChoicesRoundTripThroughTheDurableEnvelope() {
    for (const auto& choice : PJ::AppLanguage::supportedLanguages()) {
      const auto sanitized = PJ::BrowserPersistence::sanitizePreference(PJ::AppLanguage::kPreferenceKey, choice.code);
      QVERIFY(sanitized.has_value());
      QCOMPARE(*sanitized, QVariant(choice.code));
      const QJsonObject values{{PJ::AppLanguage::kPreferenceKey, choice.code}};
      const QJsonDocument document(QJsonObject{{u"version"_s, 1}, {u"values"_s, values}});
      const auto restored = PJ::BrowserPersistenceTestPeer::decode(document.toJson(QJsonDocument::Compact));
      QCOMPARE(restored.value(PJ::AppLanguage::kPreferenceKey), QVariant(choice.code));
    }
  }

  void nonCanonicalOrUnsupportedValuesCannotEnterDurableStorage() {
    for (const QString& invalid : {u"zh-TW"_s, u"zh_HK"_s, u"zh-Hant"_s, u"zh"_s, u"/private/path"_s,
                                   u"fr_FR"_s, QString{}}) {
      QVERIFY(!PJ::BrowserPersistence::sanitizePreference(PJ::AppLanguage::kPreferenceKey, invalid).has_value());
      const QJsonObject values{{PJ::AppLanguage::kPreferenceKey, invalid}};
      const QJsonDocument document(QJsonObject{{u"version"_s, 1}, {u"values"_s, values}});
      QVERIFY(!PJ::BrowserPersistenceTestPeer::decode(document.toJson()).contains(PJ::AppLanguage::kPreferenceKey));
    }
    QVERIFY(!PJ::BrowserPersistence::sanitizePreference(PJ::AppLanguage::kPreferenceKey, true).has_value());
    QVERIFY(!PJ::BrowserPersistence::sanitizePreference(PJ::AppLanguage::kPreferenceKey, 1).has_value());
    QVERIFY(!PJ::BrowserPersistence::isDurablePreferenceKey(u"Preferences::language/private"_s));
  }
};

QTEST_GUILESS_MAIN(BrowserLanguageTest)
#include "browser_language_test.moc"
