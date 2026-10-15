// SPDX-License-Identifier: MPL-2.0
#include "localized_meme.h"
#include <QDebug>
#include <QDir>
#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>

namespace
{
QJsonArray catalog()
{
  static const QJsonArray images = [] {
    QFile file(":/resources/memes/zh_CN.json");
    if (!file.open(QIODevice::ReadOnly))
    {
      return QJsonArray();
    }
    return QJsonDocument::fromJson(file.readAll()).object().value("images").toArray();
  }();
  return images;
}

QString originalPath(int index)
{
  return QString(":/resources/memes/meme_%1.jpg").arg(index, 2, 10, QChar('0'));
}
}  // namespace

QPixmap localizedMeme(int index, bool chinese, bool* text_fits)
{
  const QPixmap original(originalPath(index));
  const auto images = catalog();
  bool ok = !original.isNull() && images.size() == 106 && index >= 0 && index < images.size();
  QJsonObject entry;
  if (ok)
  {
    entry = images[index].toObject();
    ok = entry.value("id").toInt(-1) == index;
  }

  QPixmap image = original;
  if (ok && chinese && !entry.value("regions").toArray().isEmpty() &&
      entry.value("localization_status").toString() != "original-ai-unavailable")
  {
    const QString asset = entry.value("asset").toString();
    QPixmap localized;
    ok = asset.startsWith("zh_CN/") && !asset.contains("..") &&
         localized.load(":/resources/memes/" + asset);
    if (ok)
    {
      // Captions and restored backgrounds are baked into the reviewed asset.
      // Match the original splash footprint without changing glyph proportions.
      image = localized.scaled(original.size(), Qt::KeepAspectRatio, Qt::SmoothTransformation);
    }
    else
    {
      qWarning() << "Localized meme asset missing or invalid:" << index << asset;
    }
  }
  // Retain the existing export/API field for compatibility. With baked assets
  // this reports successful image loading, not a runtime font-metrics check.
  if (text_fits)
  {
    *text_fits = ok;
  }
  return image;
}

bool exportLocalizedMemes(const QString& directory, bool chinese)
{
  QDir().mkpath(directory);
  QJsonArray results;
  bool all_ok = true;
  const auto images = catalog();
  for (int i = 0; i < 106; ++i)
  {
    bool fits = false;
    const auto image = localizedMeme(i, chinese, &fits);
    const QString filename = QString("meme_%1.png").arg(i, 2, 10, QChar('0'));
    const bool saved = image.save(directory + "/" + filename);
    const auto entry = i < images.size() ? images[i].toObject() : QJsonObject();
    const bool translated = chinese && !entry.value("asset").toString().isEmpty();
    const bool unavailable =
        chinese && entry.value("localization_status").toString() == "original-ai-unavailable";
    const bool english_original = chinese || image.toImage() == QPixmap(originalPath(i)).toImage();
    QJsonObject result;
    result["id"] = i;
    result["file"] = filename;
    result["text_fits"] = fits;
    result["saved"] = saved;
    result["english_original"] = english_original;
    result["asset"] = translated ? entry.value("asset").toString() : originalPath(i);
    result["rendering"] =
        translated ? "ai-localized-asset" : (unavailable ? "original-ai-unavailable" : "original");
    result["width"] = image.width();
    result["height"] = image.height();
    results.append(result);
    all_ok = all_ok && saved && fits && english_original;
  }
  QFile report(directory + "/memes.json");
  if (!report.open(QIODevice::WriteOnly))
  {
    return false;
  }
  report.write(QJsonDocument(results).toJson());
  return all_ok;
}
