// SPDX-License-Identifier: MPL-2.0
#include "plotjuggler_app/localized_meme.h"
#include "resource_image.h"
#include <QApplication>
#include <QCryptographicHash>
#include <QDir>
#include <QFile>
#include <QFont>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QResource>
#include <QTemporaryDir>
#include <cmath>
#include <iostream>

#ifndef PJ_ENABLE_LOCALIZED_IMAGES
#define PJ_ENABLE_LOCALIZED_IMAGES 1
#endif

namespace
{
QString pixelHash(const QImage& input)
{
  const auto image = input.convertToFormat(QImage::Format_RGBA8888);
  QCryptographicHash hash(QCryptographicHash::Sha256);
  for (int y = 0; y < image.height(); ++y)
  {
    hash.addData(reinterpret_cast<const char*>(image.constScanLine(y)), image.width() * 4);
  }
  return QString::fromLatin1(hash.result().toHex());
}
QRect rect(const QJsonArray& a)
{
  return QRect(a[0].toInt(), a[1].toInt(), a[2].toInt(), a[3].toInt());
}
}  // namespace

int main(int argc, char** argv)
{
  QApplication app(argc, argv);
  QFile catalog(":/resources/memes/zh_CN.json");
  QJsonObject root;
  if (PJ_ENABLE_LOCALIZED_IMAGES)
  {
    if (!catalog.open(QIODevice::ReadOnly))
    {
      return 1;
    }
    root = QJsonDocument::fromJson(catalog.readAll()).object();
    if (root["images"].toArray().size() != 106)
    {
      return 2;
    }
  }
  else if (catalog.exists())
  {
    return 3;
  }
  const auto images = root["images"].toArray();
  const auto assets = root["assets"].toObject();
  qint64 stored_bytes = 0, uncompressed_bytes = 0;
  for (auto it = assets.begin(); it != assets.end(); ++it)
  {
    QFile file(":/resources/memes/" + it.key());
    const auto meta = it.value().toObject();
    if (!file.open(QIODevice::ReadOnly) ||
        QString::fromLatin1(QCryptographicHash::hash(file.readAll(), QCryptographicHash::Sha256).toHex()) !=
            meta["sha256"].toString())
    {
      return 4;
    }
    const QImage image(":/resources/memes/" + it.key());
    if (pixelHash(image) != meta["rgba_sha256"].toString())
    {
      return 5;
    }
    const QResource resource(":/resources/memes/" + it.key());
    stored_bytes += resource.size();
    uncompressed_bytes += meta["bytes"].toDouble();
  }
  const QString reference_dir = qEnvironmentVariable("PJ_MEME_REFERENCE_DIR");
  const QString audit_dir = qEnvironmentVariable("PJ_MEME_AUDIT_DIR");
  if (!audit_dir.isEmpty())
  {
    QDir().mkpath(audit_dir + "/before");
    QDir().mkpath(audit_dir + "/after");
  }
  QJsonArray proofs;
  int translated_count = 0, unavailable_count = 0, checked_crops = 0;
  for (int i = 0; i < 106; ++i)
  {
    const auto entry = i < images.size() ? images[i].toObject() : QJsonObject();
    const QString original_path = QString(":/resources/memes/meme_%1.jpg").arg(i, 2, 10, QChar('0'));
    const QPixmap original(original_path);
    bool ok = false;
    if (localizedMeme(i, false, &ok).toImage() != original.toImage() || !ok || original.isNull())
    {
      return 6;
    }
    const auto chinese = localizedMeme(i, true, &ok);
    if (!ok || chinese.isNull())
    {
      return 7;
    }
    const auto variant = entry["variant"].toObject();
    QPixmap expected = original;
    if (!variant.isEmpty())
    {
      const auto native = PJ::resourceImageVariant(original.toImage(), variant,
                                                    ":/resources/memes", &ok);
      if (!ok)
      {
        return 8;
      }
      const auto reference = entry["reference"].toObject();
      if (variant.contains("image"))
      {
        if (pixelHash(native) != reference["rgba_sha256"].toString())
        {
          return 9;
        }
      }
      else
      {
        const auto patches = variant["patches"].toArray();
        const auto references = reference["patches"].toArray();
        for (int n = 0; n < patches.size(); ++n)
        {
          const auto patch = patches[n].toObject();
          const auto area = rect(references[n].toObject()["rect"].toArray());
          if (pixelHash(native.copy(area)) != references[n].toObject()["rgba_sha256"].toString())
          {
            std::cerr << "Caption pixels changed in image " << i << '\n';
            return 10;
          }
          ++checked_crops;
        }
      }
      expected = QPixmap::fromImage(native).scaled(original.size(), Qt::KeepAspectRatio,
                                                    Qt::SmoothTransformation);
      if (chinese.toImage() != expected.toImage() || chinese.toImage() == original.toImage())
      {
        return 11;
      }
      if (!reference_dir.isEmpty())
      {
        const QPixmap before(reference_dir + '/' + reference["file"].toString());
        if (before.isNull())
        {
          return 12;
        }
        const auto before_scaled = before.scaled(original.size(), Qt::KeepAspectRatio,
                                                  Qt::SmoothTransformation).toImage();
        if (before_scaled.size() != chinese.size())
        {
          return 13;
        }
        if (variant.contains("image"))
        {
          if (before_scaled != chinese.toImage())
          {
            return 14;
          }
        }
        else
        {
          const double sx = double(chinese.width()) / native.width();
          const double sy = double(chinese.height()) / native.height();
          for (const auto& value : reference["patches"].toArray())
          {
            const auto r = rect(value.toObject()["rect"].toArray());
            const int left = int(std::ceil((r.x() + 4) * sx));
            const int top = int(std::ceil((r.y() + 4) * sy));
            const int right = int(std::floor((r.x() + r.width() - 4) * sx));
            const int bottom = int(std::floor((r.y() + r.height() - 4) * sy));
            const QRect protected_area(left, top, right - left, bottom - top);
            if (protected_area.isEmpty() ||
                pixelHash(before_scaled.copy(protected_area)) !=
                    pixelHash(chinese.toImage().copy(protected_area)))
            {
              std::cerr << "Scaled caption pixels changed in image " << i << '\n';
              return 15;
            }
          }
        }
        if (!audit_dir.isEmpty())
        {
          const QString name = QString("/meme_%1.png").arg(i, 2, 10, QChar('0'));
          before_scaled.save(audit_dir + "/before" + name);
          chinese.save(audit_dir + "/after" + name);
        }
      }
      ++translated_count;
    }
    if (entry["localization_status"].toString() == "original-ai-unavailable")
    {
      ++unavailable_count;
    }
    if (chinese.toImage() != expected.toImage())
    {
      return 16;
    }
    proofs.append(QJsonObject{{"id", i}, {"english_original", true},
                               {"width", chinese.width()}, {"height", chinese.height()},
                               {"native_caption_pixels", true},
                               {"scaled_reference_checked", !reference_dir.isEmpty()}});
  }
  if (PJ_ENABLE_LOCALIZED_IMAGES && translated_count != 88)
  {
    return 17;
  }
  const auto before = localizedMeme(0, true).toImage();
  app.setFont(QFont("Monospace", 48));
  if (localizedMeme(0, true).toImage() != before)
  {
    return 18;
  }
  for (int invalid : {-1, 106})
  {
    bool ok = true;
    if (!localizedMeme(invalid, true, &ok).isNull() || ok)
    {
      return 19;
    }
  }
  QTemporaryDir output;
  for (bool chinese : {false, true})
  {
    const QString path = output.path() + (chinese ? "/zh_CN" : "/en_US");
    if (!output.isValid() || !exportLocalizedMemes(path, chinese))
    {
      return 20;
    }
    QFile report(path + "/memes.json");
    if (!report.open(QIODevice::ReadOnly))
    {
      return 21;
    }
    const auto records = QJsonDocument::fromJson(report.readAll()).array();
    if (records.size() != 106)
    {
      return 22;
    }
    int localized_count = 0, fallback_count = 0;
    for (const auto& value : records)
    {
      const auto record = value.toObject();
      if (!record["saved"].toBool() || !record["text_fits"].toBool() ||
          !record["english_original"].toBool())
      {
        return 23;
      }
      localized_count += record["rendering"].toString().startsWith("localized-");
      fallback_count += record["rendering"].toString() == "original-ai-unavailable";
    }
    if (localized_count != (chinese ? translated_count : 0) ||
        fallback_count != (chinese ? unavailable_count : 0))
    {
      return 24;
    }
  }
  if (!audit_dir.isEmpty())
  {
    QFile report(audit_dir + "/summary.json");
    if (!report.open(QIODevice::WriteOnly))
    {
      return 25;
    }
    report.write(QJsonDocument(QJsonObject{
        {"translated_images", translated_count}, {"pixel_identical_crops", checked_crops},
        {"originals", 106}, {"localized_resource_stored_bytes", double(stored_bytes)},
        {"localized_resource_source_bytes", double(uncompressed_bytes)}, {"images", proofs}
    }).toJson());
  }
  std::cout << "PASS: " << translated_count << " localized variants, " << checked_crops
            << " native caption crops, 106 intact English originals, reference scaling and exports\n";
  return 0;
}
