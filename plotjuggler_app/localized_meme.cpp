// SPDX-License-Identifier: MPL-2.0
#include "localized_meme.h"
#include <QDir>
#include <QFile>
#include <QFontDatabase>
#include <QFontMetrics>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QPainter>
#include <QDebug>

namespace {
QJsonArray catalog()
{
  static const QJsonArray images = [] {
    QFile file(":/resources/memes/zh_CN.json");
    if (!file.open(QIODevice::ReadOnly)) return QJsonArray();
    return QJsonDocument::fromJson(file.readAll()).object().value("images").toArray();
  }();
  return images;
}
QString chineseFont()
{
  const auto families = QFontDatabase().families();
  for (const auto& name : {"Microsoft YaHei", "Noto Sans CJK SC", "WenQuanYi Micro Hei", "SimHei"})
    if (families.contains(QString::fromLatin1(name))) return QString::fromLatin1(name);
  return QFont().family();
}
}

QPixmap localizedMeme(int index, bool chinese, bool* text_fits)
{
  QPixmap image(QString(":/resources/memes/meme_%1.jpg").arg(index, 2, 10, QChar('0')));
  const auto images = catalog();
  bool ok = !image.isNull() && images.size() == 106 && index >= 0 && index < images.size();
  if (ok) ok = images[index].toObject().value("id").toInt(-1) == index;
  if (!ok || !chinese) { if (text_fits) *text_fits = ok; return image; }
  const QPixmap original = image;
  QPainter painter(&image);
  painter.setRenderHint(QPainter::Antialiasing);
  const auto regions = images[index].toObject().value("regions").toArray();
  for (const auto& value : regions)
  {
    const auto region = value.toObject();
    const auto coords = region.value("rect").toArray();
    if (coords.size() != 4) { ok = false; continue; }
    QRect box(qRound(coords[0].toDouble() * image.width() / 100),
              qRound(coords[1].toDouble() * image.height() / 100),
              qRound(coords[2].toDouble() * image.width() / 100),
              qRound(coords[3].toDouble() * image.height() / 100));
    box = box.intersected(image.rect());
    const QString style = region.value("style").toString();
    const bool light = style == "light" || style == "card" || style == "yellow";
    QColor background = light ? QColor("#ffffff") : QColor("#15181f");
    if (style == "green") background = QColor("#17453e");
    if (style == "red") background = QColor("#ad3037");
    if (style == "card") background = QColor("#c6af88");
    if (style == "yellow") background = QColor("#d6bc4b");
    // Opaque masks remove the English lettering. Text is painted into the
    // pixmap, so this is also used by the actual QSplashScreen at startup.
    painter.fillRect(box, background);
    const int padding = box.height() < 16 ? 1 : 3;
    const QRect text_box = box.adjusted(padding, padding, -padding, -padding);
    const QString text = region.value("text").toString();
    QFont font(chineseFont()); font.setBold(true);
    const int flags = Qt::AlignCenter | Qt::TextWordWrap;
    bool fits = false;
    for (int size = qMax(5, qMin(box.height(), image.width() / 14)); size >= 5; --size)
    {
      font.setPixelSize(size);
      const QRect bounds = QFontMetrics(font).boundingRect(text_box, flags, text);
      if (bounds.width() <= text_box.width() && bounds.height() <= text_box.height())
      { fits = true; break; }
    }
    ok = ok && fits && !text.isEmpty();
    painter.setFont(font);
    painter.setPen(light ? QColor("#15181f") : QColor("#ffffff"));
    painter.drawText(text_box, flags, text);
  }
  // Keep source attribution intact even when a caption reaches a lower corner.
  QJsonArray preserved = images[index].toObject().value("preserve").toArray();
  preserved.append(QJsonArray{0, 97, 15, 3});
  for (const auto& value : preserved)
  {
    const auto c = value.toArray();
    if (c.size() != 4) continue;
    const QRect area(qRound(c[0].toDouble() * image.width() / 100),
                     qRound(c[1].toDouble() * image.height() / 100),
                     qRound(c[2].toDouble() * image.width() / 100),
                     qRound(c[3].toDouble() * image.height() / 100));
    painter.drawPixmap(area, original, area);
  }
  painter.end();
  if (text_fits) *text_fits = ok;
  if (!ok) qWarning() << "Meme translation text did not fit:" << index;
  return image;
}

bool exportLocalizedMemes(const QString& directory, bool chinese)
{
  QDir().mkpath(directory);
  QJsonArray results;
  bool all_ok = true;
  for (int i = 0; i < 106; ++i)
  {
    bool fits = false;
    const auto image = localizedMeme(i, chinese, &fits);
    const QString filename = QString("meme_%1.png").arg(i, 2, 10, QChar('0'));
    const bool saved = image.save(directory + "/" + filename);
    const bool english_original = chinese || image.toImage() ==
      QPixmap(QString(":/resources/memes/meme_%1.jpg").arg(i, 2, 10, QChar('0'))).toImage();
    QJsonObject result;
    result["id"] = i; result["file"] = filename; result["text_fits"] = fits;
    result["saved"] = saved; result["english_original"] = english_original;
    result["width"] = image.width(); result["height"] = image.height();
    results.append(result); all_ok = all_ok && saved && fits && english_original;
  }
  QFile report(directory + "/memes.json");
  if (!report.open(QIODevice::WriteOnly)) return false;
  report.write(QJsonDocument(results).toJson());
  return all_ok;
}
