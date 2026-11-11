// SPDX-License-Identifier: MPL-2.0
#include <QCoreApplication>
#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QTest>

#include "AppLanguage.h"
#include "pj_marketplace/marketplace_text.hpp"

using namespace Qt::StringLiterals;

// Tests the display boundary without installing plugins or modifying registry records.
class MarketplaceCatalogTest : public QObject {
  Q_OBJECT
 private slots:
  void allRegistryMetadata_data() {
    QTest::addColumn<QString>("id");
    QTest::addColumn<QString>("version");
    QTest::addColumn<QString>("source");
    QFile file(QString::fromUtf8(PJ_REGISTRY_LOCK));
    QVERIFY(file.open(QIODevice::ReadOnly));
    const auto entries = QJsonDocument::fromJson(file.readAll()).object().value("extensions").toArray();
    QCOMPARE(entries.size(), 30);
    for (const auto& value : entries) {
      const auto entry = value.toObject();
      for (const auto& field : {u"name"_s, u"description"_s}) {
        const auto row = (entry.value("id").toString() + "/" + field).toUtf8();
        QTest::newRow(row.constData()) << entry.value("id").toString() << entry.value("version").toString()
                                       << entry.value(field).toString();
      }
    }
  }

  void allRegistryMetadata() {
    QFETCH(QString, id);
    QFETCH(QString, version);
    QFETCH(QString, source);
    for (const QString& code : {u"zh_CN"_s, u"zh_TW"_s}) {
      const PJ::AppLanguage language(*QCoreApplication::instance(), code);
      const QString translated = PJ::marketplacePluginText(id, version, source);
      QVERIFY2(translated != source, qPrintable(id + ": " + source));
      QVERIFY(!translated.isEmpty());
      // A plugin update with unchanged metadata must remain translated.
      QCOMPARE(PJ::marketplacePluginText(id, u"99.0.0"_s, source), translated);
    }
    const PJ::AppLanguage language(*QCoreApplication::instance(), u"en_US"_s);
    QCOMPARE(PJ::marketplacePluginText(id, version, source), source);
  }

  void categoriesTranslateWithoutChangingCanonicalTokens() {
    for (const QString& code : {u"zh_CN"_s, u"zh_TW"_s}) {
      const PJ::AppLanguage language(*QCoreApplication::instance(), code);
      for (const char* source : {"Data loaders", "Data streams", "Message parsers", "Toolboxes"}) {
        QVERIFY(QCoreApplication::translate("PJ::MarketplaceWindow", source) != QString::fromUtf8(source));
      }
    }
  }

  void exactSourceAndIdAreRequired() {
    for (const QString& code : {u"zh_CN"_s, u"zh_TW"_s}) {
      const PJ::AppLanguage language(*QCoreApplication::instance(), code);
      QCOMPARE(
          PJ::marketplacePluginText(u"unknown-fft"_s, u"1.0.1"_s, u"Fast Fourier Transform"_s),
          u"Fast Fourier Transform"_s);
      QCOMPARE(
          PJ::marketplacePluginText(u"toolbox-fft"_s, u"1.0.1"_s, u"A changed upstream description"_s),
          u"A changed upstream description"_s);
    }
    const PJ::AppLanguage language(*QCoreApplication::instance(), u"zh_CN"_s);
    QCOMPARE(
        PJ::marketplacePluginText(u"toolbox-fft"_s, u"1.0.1"_s, u"Fast Fourier Transform"_s),
        u"快速傅里叶变换（FFT）"_s);
  }
};
QTEST_GUILESS_MAIN(MarketplaceCatalogTest)
#include "marketplace_catalog_test.moc"
