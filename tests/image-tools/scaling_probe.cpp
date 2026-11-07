// SPDX-License-Identifier: MPL-2.0
#include "resource_image.h"
#include <QColor>
#include <QCryptographicHash>
#include <QDir>
#include <QFile>
#include <QGuiApplication>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QPixmap>
#include <QThreadPool>
#include <cmath>
#include <iostream>

namespace
{
QRect rect(const QJsonArray& a)
{
  return QRect(a[0].toInt(), a[1].toInt(), a[2].toInt(), a[3].toInt());
}
QString hash(const QImage& input)
{
  const auto image = input.convertToFormat(QImage::Format_RGBA8888);
  QCryptographicHash h(QCryptographicHash::Sha256);
  for (int y = 0; y < image.height(); ++y)
    h.addData(reinterpret_cast<const char*>(image.constScanLine(y)), image.width() * 4);
  return QString::fromLatin1(h.result().toHex());
}
QJsonObject info(const QImage& image)
{
  int min_alpha = 255, not_opaque = 0;
  // These are raw high bytes, including in RGB32 where alpha is implicitly opaque.
  if (image.depth() == 32)
    for (int y = 0; y < image.height(); ++y)
      for (int x = 0; x < image.width(); ++x)
      {
        const int a = qAlpha(reinterpret_cast<const QRgb*>(image.constScanLine(y))[x]);
        min_alpha = qMin(min_alpha, a);
        not_opaque += a != 255;
      }
  return {{"format", int(image.format())}, {"alpha_channel", image.hasAlphaChannel()},
          {"dpr", image.devicePixelRatio()}, {"width", image.width()}, {"height", image.height()},
          {"raw_min_alpha", min_alpha}, {"raw_nonopaque_pixels", not_opaque}};
}
}

int main(int argc, char** argv)
{
  QGuiApplication app(argc, argv);
  if (argc != 5)
    return 2;
  const QString resources = QString::fromLocal8Bit(argv[1]);
  const QString reference = QString::fromLocal8Bit(argv[2]);
  const QString output = QString::fromLocal8Bit(argv[3]);
  const int id = QString::fromLocal8Bit(argv[4]).toInt();
  if (qEnvironmentVariableIntValue("PJ_SCALE_THREADS") > 0)
    QThreadPool::globalInstance()->setMaxThreadCount(qEnvironmentVariableIntValue("PJ_SCALE_THREADS"));
  QDir().mkpath(output);
  QFile file(resources + "/zh_CN.json");
  if (!file.open(QIODevice::ReadOnly))
    return 3;
  const auto entry = QJsonDocument::fromJson(file.readAll()).object()["images"].toArray()[id].toObject();
  const auto variant = entry["variant"].toObject();
  const auto ref = entry["reference"].toObject();
  const QPixmap original(resources + QString("/meme_%1.jpg").arg(id, 2, 10, QChar('0')));
  const QPixmap before(reference + '/' + ref["file"].toString());
  if (original.isNull() || before.isNull())
    return 4;
  bool failed = false;
  QJsonArray attempts;
  for (int attempt = 0; attempt < 16; ++attempt)
  {
    bool ok = false;
    const auto native = PJ::resourceImageVariant(original.toImage(), variant, resources, &ok);
    if (!ok)
      return 5;
    const QPixmap native_pixmap = QPixmap::fromImage(native);
    const auto scaled_before = before.scaled(original.size(), Qt::KeepAspectRatio,
                                              Qt::SmoothTransformation).toImage();
    const auto after = native_pixmap.scaled(original.size(), Qt::KeepAspectRatio,
                                            Qt::SmoothTransformation).toImage();
    const auto canvas = variant["canvas"].toArray();
    const auto background = original.toImage().scaled(canvas[0].toInt(), canvas[1].toInt(),
                                                      Qt::IgnoreAspectRatio, Qt::SmoothTransformation);
    QJsonArray patches;
    int changed_total = 0;
    QImage diff(after.size(), QImage::Format_RGB32);
    diff.fill(Qt::black);
    for (const auto& value : ref["patches"].toArray())
    {
      const auto r = rect(value.toObject()["rect"].toArray());
      const double sx = double(after.width()) / native.width();
      const double sy = double(after.height()) / native.height();
      const int left = int(std::ceil((r.x() + 4) * sx));
      const int top = int(std::ceil((r.y() + 4) * sy));
      const int right = int(std::floor((r.x() + r.width() - 4) * sx));
      const int bottom = int(std::floor((r.y() + r.height() - 4) * sy));
      const QRect area(left, top, right - left, bottom - top);
      int changed = 0, max_delta = 0;
      QJsonArray examples;
      for (int y = area.top(); y <= area.bottom(); ++y)
        for (int x = area.left(); x <= area.right(); ++x)
        {
          const auto a = scaled_before.pixelColor(x, y);
          const auto b = after.pixelColor(x, y);
          if (a != b)
          {
            ++changed;
            const int delta = qMax(qMax(qAbs(a.red() - b.red()), qAbs(a.green() - b.green())),
                                   qMax(qAbs(a.blue() - b.blue()), qAbs(a.alpha() - b.alpha())));
            max_delta = qMax(max_delta, delta);
            diff.setPixelColor(x, y, Qt::magenta);
            if (examples.size() < 16)
              examples.append(QJsonObject{{"x", x}, {"y", y}, {"before", a.name(QColor::HexArgb)},
                                          {"after", b.name(QColor::HexArgb)}});
          }
        }
      changed_total += changed;
      patches.append(QJsonObject{{"native_pixels_identical", hash(native.copy(r)) == hash(before.toImage().copy(r))},
          {"protected_rect", QJsonArray{left, top, right - left, bottom - top}},
          {"changed_pixels", changed}, {"max_channel_delta", max_delta}, {"examples", examples}});
    }
    attempts.append(QJsonObject{{"attempt", attempt}, {"changed_pixels", changed_total},
        {"before", info(before.toImage())}, {"native", info(native)},
        {"native_pixmap", info(native_pixmap.toImage())}, {"background_scaled", info(background)},
        {"scaled_before", info(scaled_before)}, {"scaled_after", info(after)}, {"patches", patches}});
    if (attempt == 0 || changed_total)
    {
      const QString prefix = output + QString("/attempt_%1").arg(attempt);
      scaled_before.save(prefix + "_before.png");
      after.save(prefix + "_after.png");
      diff.save(prefix + "_diff.png");
    }
    failed |= changed_total != 0;
  }
  QFile report(output + "/probe.json");
  if (!report.open(QIODevice::WriteOnly))
    return 6;
  const QJsonObject result{{"qt", qVersion()}, {"platform", QGuiApplication::platformName()},
      {"cpu_features_disabled", qEnvironmentVariable("QT_NO_CPU_FEATURE")},
      {"threads", QThreadPool::globalInstance()->maxThreadCount()}, {"image", id},
      {"strict_pixel_failure", failed}, {"attempts", attempts}};
  report.write(QJsonDocument(result).toJson());
  std::cout << "image=" << id << " Qt=" << qVersion() << " strict_failure=" << failed << '\n';
  return failed ? 15 : 0;
}
