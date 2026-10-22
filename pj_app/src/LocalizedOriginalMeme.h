// SPDX-License-Identifier: MPL-2.0
#pragma once
#include "OriginalMemeVariant.h"
#include <QFile>
#include <QJsonDocument>
#include <QPixmap>
#include <QStringList>

namespace PJ {
namespace original_meme_detail {
inline QJsonArray catalog() {
  static const QJsonArray images = [] {
    QFile file(QStringLiteral(":/resources/memes/zh_CN.json"));
    if (!file.open(QIODevice::ReadOnly)) return QJsonArray{};
    return QJsonDocument::fromJson(file.readAll()).object().value("images").toArray();
  }();
  return images;
}
inline QJsonObject entry(int index) {
  for (const auto& value : catalog()) {
    const auto item = value.toObject();
    if (item.value("id").toInt(-1) == index) return item;
  }
  return {};
}
inline bool available(const QJsonObject& item) {
  return item.value("pixel_review").toString().startsWith("passed") &&
      (!item.value("variant").toObject().isEmpty() ||
       item.value("localization_status").toString() == "original-technical-labels");
}
}  // namespace original_meme_detail

// Original 4.x numbering is 01..37. Missing/unreviewed translations return null,
// never an English fallback. Extra original Chinese jokes are a separate pool.
inline QPixmap localizedOriginalMeme(int index) {
  const auto item = original_meme_detail::entry(index);
  if (index < 1 || index > 37 || !original_meme_detail::available(item)) return {};
  const QImage original(QStringLiteral(":/resources/memes/meme_%1.jpg").arg(index, 2, 10, QChar('0')));
  bool ok = false;
  QString error;
  const auto image = original_meme_detail::resourceImageVariant(
      original, item.value("variant").toObject(), QStringLiteral(":/resources/memes"), &ok, &error);
  if (!ok) return {};
  return QPixmap::fromImage(image.scaled(original.size(), Qt::KeepAspectRatio, Qt::SmoothTransformation));
}
inline QStringList localizedOriginalMemeIds() {
  QStringList ids;
  for (int i = 1; i <= 37; ++i) {
    if (original_meme_detail::available(original_meme_detail::entry(i)))
      ids.append(QStringLiteral("%1").arg(i, 2, 10, QChar('0')));
  }
  return ids;
}
} // namespace PJ
