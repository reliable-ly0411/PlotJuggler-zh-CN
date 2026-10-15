// SPDX-License-Identifier: MPL-2.0
#include "plotjuggler_app/localized_meme.h"
#include <QApplication>
#include <QFile>
#include <QFont>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QTemporaryDir>
#include <iostream>

int main(int argc, char** argv)
{
  QApplication app(argc, argv);
  QFile catalog(":/resources/memes/zh_CN.json");
  if (!catalog.open(QIODevice::ReadOnly))
  {
    return 1;
  }
  const auto images = QJsonDocument::fromJson(catalog.readAll()).object()["images"].toArray();
  if (images.size() != 106)
  {
    return 2;
  }
  int translated_count = 0;
  int unavailable_count = 0;
  for (int i = 0; i < images.size(); ++i)
  {
    const auto entry = images[i].toObject();
    const QPixmap original(QString(":/resources/memes/meme_%1.jpg").arg(i, 2, 10, QChar('0')));
    bool ok = false;
    const auto english = localizedMeme(i, false, &ok);
    if (!ok || original.isNull() || english.toImage() != original.toImage())
    {
      return 3;
    }
    const auto chinese = localizedMeme(i, true, &ok);
    if (!ok || chinese.isNull())
    {
      std::cerr << "Missing Chinese image " << i << '\n';
      return 4;
    }
    QPixmap expected = original;
    if (!entry["asset"].toString().isEmpty())
    {
      const QPixmap asset(":/resources/memes/" + entry["asset"].toString());
      if (asset.isNull())
      {
        return 5;
      }
      expected = asset.scaled(original.size(), Qt::KeepAspectRatio, Qt::SmoothTransformation);
      if (chinese.toImage() == original.toImage())
      {
        return 6;
      }
      ++translated_count;
    }
    if (entry["localization_status"].toString() == "original-ai-unavailable")
    {
      ++unavailable_count;
    }
    if (chinese.toImage() != expected.toImage())
    {
      return 7;
    }
  }
  if (translated_count == 0)
  {
    return 8;
  }
  const auto before = localizedMeme(0, true).toImage();
  app.setFont(QFont("Monospace", 48));
  if (localizedMeme(0, true).toImage() != before)
  {
    return 9;
  }
  for (int invalid : { -1, 106 })
  {
    bool ok = true;
    if (!localizedMeme(invalid, true, &ok).isNull() || ok)
    {
      return 10;
    }
  }
  QTemporaryDir output;
  if (!output.isValid())
  {
    return 11;
  }
  for (bool chinese : { false, true })
  {
    const auto path = output.path() + (chinese ? "/zh_CN" : "/en_US");
    if (!exportLocalizedMemes(path, chinese))
    {
      return 12;
    }
    QFile report(path + "/memes.json");
    if (!report.open(QIODevice::ReadOnly))
    {
      return 13;
    }
    const auto records = QJsonDocument::fromJson(report.readAll()).array();
    if (records.size() != 106)
    {
      return 14;
    }
    int baked_count = 0;
    int fallback_count = 0;
    for (const auto& value : records)
    {
      const auto record = value.toObject();
      if (!record["saved"].toBool() || !record["text_fits"].toBool() ||
          !record["english_original"].toBool())
      {
        return 15;
      }
      if (record["rendering"].toString() == "ai-localized-asset")
      {
        ++baked_count;
      }
      if (record["rendering"].toString() == "original-ai-unavailable")
      {
        ++fallback_count;
      }
    }
    if (baked_count != (chinese ? translated_count : 0) ||
        fallback_count != (chinese ? unavailable_count : 0))
    {
      return 16;
    }
  }
  std::cout << "PASS: " << translated_count << " baked Chinese assets, " << unavailable_count
            << " documented original fallbacks, "
               "106 pixel-identical English originals, font independence and both exports\n";
  return 0;
}
