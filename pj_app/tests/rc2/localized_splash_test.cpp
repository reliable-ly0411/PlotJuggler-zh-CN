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
 private slots:
  void preferences() {
    QTemporaryDir temporary;
    QSettings settings(temporary.filePath(u"settings.ini"_s), QSettings::IniFormat);
    for (const QString& language : {u"zh_CN"_s, u"en_US"_s}) {
      const PJ::AppLanguage translator(*qApp, language);
      QCOMPARE(PJ::startupSplashMode(settings), PJ::kSplashModeMemes);
      settings.setValue(PJ::kSplashModeKey, PJ::kSplashModeSerious);
      QCOMPARE(PJ::startupSplashMode(settings), PJ::kSplashModeSerious);
      settings.setValue(PJ::kSplashModeKey, PJ::kSplashModeMemes);
      QCOMPARE(PJ::startupSplashMode(settings), PJ::kSplashModeMemes);
    }
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
    {
      const PJ::AppLanguage translator(*qApp, u"zh_CN"_s);
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
          QVERIFY(image.save(capture + u"/zh-meme-%1.png"_s.arg(i)));
        }
      }
    }
    const PJ::AppLanguage translator(*qApp, u"en_US"_s);
    QCOMPARE(PJ::localizedMemeCaptions(), english);
  }
};
QTEST_MAIN(LocalizedSplashTest)
#include "localized_splash_test.moc"
