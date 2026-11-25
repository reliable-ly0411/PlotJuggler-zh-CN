// SPDX-License-Identifier: MPL-2.0
#include "../src/LocalizedOriginalMeme.h"
#include <QtTest/QtTest>

class LocalizedOriginalMemeTest : public QObject {
  Q_OBJECT
private slots:
  void catalogHasEveryOriginalSlot() {
    const auto catalog = PJ::original_meme_detail::catalog();
    QCOMPARE(catalog.size(), 37);
    for (int i = 0; i < catalog.size(); ++i)
      QCOMPARE(catalog.at(i).toObject().value("id").toInt(), i + 1);
  }
  void reviewedImagesLoad() {
    const auto ids = PJ::localizedOriginalMemeIds();
    QVERIFY(!ids.isEmpty());
    for (const auto& id : ids) {
      const auto image = PJ::localizedOriginalMeme(id.toInt());
      QVERIFY2(!image.isNull(), qPrintable(id));
      const QPixmap original(QString(":/resources/memes/meme_%1.jpg").arg(id));
      QVERIFY(image.width() <= original.width());
      QVERIFY(image.height() <= original.height());
      QVERIFY(image.width() == original.width() || image.height() == original.height());
    }
  }
  void incompleteImagesNeverFallBackToEnglish() {
    for (const auto& value : PJ::original_meme_detail::catalog()) {
      const auto item = value.toObject();
      if (!PJ::original_meme_detail::available(item))
        QVERIFY(PJ::localizedOriginalMeme(item.value("id").toInt()).isNull());
    }
    for (int id : {-1, 0, 38}) QVERIFY(PJ::localizedOriginalMeme(id).isNull());
  }
  void productOnlyImagesRemainUnchanged() {
    for (int id : {2, 34}) {
      const QPixmap original(QString(":/resources/memes/meme_%1.jpg").arg(id, 2, 10, QChar('0')));
      QCOMPARE(PJ::localizedOriginalMeme(id).toImage(), original.toImage());
    }
  }
  void invalidVariantIsRejected() {
    const QImage original(16, 16, QImage::Format_RGB32);
    bool ok = true;
    QString error;
    QJsonObject variant{{"image", "../bad.png"}};
    PJ::original_meme_detail::resourceImageVariant(original, variant, ":/resources/memes", &ok, &error);
    QVERIFY(!ok);
    QVERIFY(!error.isEmpty());
  }
};
QTEST_MAIN(LocalizedOriginalMemeTest)
#include "localized_original_meme_test.moc"
