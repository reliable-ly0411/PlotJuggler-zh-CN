// SPDX-License-Identifier: MPL-2.0
#include "localized_meme.h"
#include "resource_image.h"
#include <QDebug>
#include <QDir>
#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>

#ifndef PJ_ENABLE_LOCALIZED_IMAGES
#define PJ_ENABLE_LOCALIZED_IMAGES 1
#endif

namespace
{
QJsonArray catalog()
{
#if PJ_ENABLE_LOCALIZED_IMAGES
  static const QJsonArray images = [] {
    QFile file(":/resources/memes/zh_CN.json");
    if (!file.open(QIODevice::ReadOnly))
    {
      return QJsonArray();
    }
    return QJsonDocument::fromJson(file.readAll()).object().value("images").toArray();
  }();
  return images;
#else
  return {};
#endif
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
  bool ok = !original.isNull() && index >= 0 && index < 106;
  QJsonObject entry;
  if (ok && chinese && PJ_ENABLE_LOCALIZED_IMAGES)
  {
    ok = images.size() == 106;
    if (ok)
    {
      entry = images[index].toObject();
      ok = entry.value("id").toInt(-1) == index;
    }
  }

  QPixmap image = original;
  if (ok && chinese && PJ_ENABLE_LOCALIZED_IMAGES)
  {
    QJsonObject variant = entry.value("variant").toObject();
    // Keep compatibility with existing full-image catalogs.
    if (variant.isEmpty() && !entry.value("asset").toString().isEmpty())
    {
      variant["image"] = entry.value("asset").toString();
    }
    if (!variant.isEmpty())
    {
      QString error;
      const auto localized = PJ::resourceImageVariant(original.toImage(), variant,
                                                       ":/resources/memes", &ok, &error);
      if (ok)
      {
        // Retain the zh.3 display footprint and the same final smooth scaling.
        image = QPixmap::fromImage(localized).scaled(original.size(), Qt::KeepAspectRatio,
                                                    Qt::SmoothTransformation);
      }
      else
      {
        qWarning() << "Localized meme variant missing or invalid:" << index << error;
      }
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
    const auto variant = entry.value("variant").toObject();
    const bool translated = chinese && !variant.isEmpty();
    const bool unavailable =
        chinese && entry.value("localization_status").toString() == "original-ai-unavailable";
    const bool english_original = chinese || image.toImage() == QPixmap(originalPath(i)).toImage();
    QJsonObject result;
    result["id"] = i;
    result["file"] = filename;
    result["text_fits"] = fits;
    result["saved"] = saved;
    result["english_original"] = english_original;
    result["variant"] = translated ? variant : QJsonObject();
    result["rendering"] =
        translated ? (variant.contains("patches") ? "localized-overlay" : "localized-full-image") :
        (unavailable ? "original-ai-unavailable" : "original");
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
