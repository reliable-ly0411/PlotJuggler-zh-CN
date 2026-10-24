// SPDX-License-Identifier: MPL-2.0
#include <QApplication>
#include <QDir>
#include <QSettings>
#include <QTemporaryDir>
#include <QTest>

#include "AppLanguage.h"
#include "LocalizedOriginalMeme.h"
#include "Splashscreen.h"
using namespace Qt::StringLiterals;
class LocalizedSplashTest : public QObject {
  Q_OBJECT
  QTemporaryDir settings_directory_;
 private slots:
  void initTestCase() {
    QVERIFY(settings_directory_.isValid());
    QCoreApplication::setOrganizationName(QStringLiteral("PlotJugglerTest"));
    QCoreApplication::setApplicationName(QStringLiteral("localized_splash_test"));
    QSettings::setDefaultFormat(QSettings::IniFormat);
    QSettings::setPath(QSettings::IniFormat, QSettings::UserScope, settings_directory_.path());
  }
  void preferences() {
    QTemporaryDir temporary;
    QSettings settings(temporary.filePath(u"settings.ini"_s), QSettings::IniFormat);
    for (const QString& language : {u"zh_CN"_s, u"zh_TW"_s, u"en_US"_s}) {
      const PJ::AppLanguage translator(*qApp, language);
      QCOMPARE(PJ::startupSplashMode(settings), PJ::kSplashModeMemes);
      settings.setValue(PJ::kSplashModeKey, PJ::kSplashModeSerious);
      QCOMPARE(PJ::startupSplashMode(settings), PJ::kSplashModeSerious);
      settings.setValue(PJ::kSplashModeKey, PJ::kSplashModeMemes);
      QCOMPARE(PJ::startupSplashMode(settings), PJ::kSplashModeMemes);
    }
  }
  void traditionalPoolNeverUsesSimplifiedRasterCaptions() {
    QSettings settings;
    settings.setValue(PJ::kSplashModeKey, PJ::kSplashModeMemes);
    settings.setValue(u"previousLocalizedFunnyMemesList"_s, QStringList{u"01"_s, u"02"_s, u"extra:0"_s});
    {
      const PJ::AppLanguage translator(*qApp, u"zh_TW"_s);
      QVERIFY(translator.catalogLoaded());
      const auto ids = PJ::chineseMemeIds();
      QCOMPARE(ids.size(), 8);
      for (const auto& id : ids) {
        QVERIFY(id.startsWith(u"extra:"_s));
        QVERIFY(!PJ::chineseMemePixmap(id).isNull());
      }
      QVERIFY(PJ::chineseMemePixmap(u"01"_s).isNull());
      for (int repeat = 0; repeat < 12; ++repeat) {
        QVERIFY(!PJ::makeStartupSplash().isNull());
        QVERIFY(settings.value(u"previousLocalizedFunnyMemesList"_s).toStringList().last().startsWith(u"extra:"_s));
        QCOMPARE(settings.value(PJ::kSplashModeKey).toString(), PJ::kSplashModeMemes);
      }
    }
    const PJ::AppLanguage simplified(*qApp, u"zh_CN"_s);
    QCOMPARE(PJ::chineseMemeIds().size(), PJ::localizedOriginalMemeIds().size() + 8);
    QVERIFY(!PJ::chineseMemePixmap(u"01"_s).isNull());
  }
  void reviewedOriginalPoolRenders() {
    const PJ::AppLanguage translator(*qApp, u"zh_CN"_s);
    const auto originals = PJ::localizedOriginalMemeIds();
    QCOMPARE(originals.size(), 33);
    QVERIFY(!originals.contains(u"09"_s));
    QVERIFY(!originals.contains(u"13"_s));
    const auto ids = PJ::chineseMemeIds();
    QCOMPARE(ids.size(), originals.size() + 8);
    QVERIFY(!ids.contains(u"11"_s));
    QVERIFY(!ids.contains(u"24"_s));
    for (const auto& id : ids) {
      QVERIFY2(!PJ::chineseMemePixmap(id).isNull(), qPrintable(id));
    }
    QVERIFY(PJ::chineseMemePixmap(u"11"_s).isNull());
    QVERIFY(PJ::chineseMemePixmap(u"24"_s).isNull());
    QVERIFY(PJ::chineseMemePixmap(u"extra:99"_s).isNull());
    QVERIFY(PJ::localizedOriginalMeme(0).isNull());
    QVERIFY(PJ::localizedOriginalMeme(38).isNull());
  }
  void allCompositionsTranslateAndRender() {
    QStringList english;
    QList<QImage> images;
    {
      const PJ::AppLanguage translator(*qApp, u"en_US"_s);
      english = PJ::localizedMemeCaptions();
      QCOMPARE(english.size(), 16);
      for (int i = 0; i < 8; ++i) {
        images.append(PJ::localizedMemeForTest(i).toImage());
      }
    }
    for (const QString& language : {u"zh_CN"_s, u"zh_TW"_s}) {
      const PJ::AppLanguage translator(*qApp, language);
      QVERIFY(translator.catalogLoaded());
      const auto chinese = PJ::localizedMemeCaptions();
      QCOMPARE(chinese.size(), english.size());
      for (int i = 0; i < 16; ++i) {
        QVERIFY(chinese.at(i) != english.at(i));
      }
      const QString capture = qEnvironmentVariable("PJ_SPLASH_CAPTURE_DIR");
      if (!capture.isEmpty()) {
        QVERIFY(QDir().mkpath(capture));
      }
      for (int i = 0; i < 8; ++i) {
        const auto image = PJ::localizedMemeForTest(i).toImage();
        QVERIFY(!image.isNull());
        QVERIFY(image != images.at(i));
        QCOMPARE(image.deviceIndependentSize(), QSizeF(600, 390));
        if (!capture.isEmpty()) {
          QVERIFY(image.save(capture + u"/%1-meme-%2.png"_s.arg(language).arg(i)));
        }
      }
    }
    const PJ::AppLanguage translator(*qApp, u"en_US"_s);
    QCOMPARE(PJ::localizedMemeCaptions(), english);
  }
};
QTEST_MAIN(LocalizedSplashTest)
#include "localized_splash_test.moc"
