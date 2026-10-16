// SPDX-License-Identifier: MPL-2.0
#include "resource_image.h"

#include <QApplication>
#include <QJsonArray>
#include <QTemporaryDir>
#include <iostream>

int main(int argc, char** argv)
{
  QApplication app(argc, argv);
  QTemporaryDir directory;
  if (!directory.isValid())
  {
    return 1;
  }
  QImage original(8, 8, QImage::Format_ARGB32);
  original.fill(Qt::blue);
  QImage atlas(3, 2, QImage::Format_ARGB32);
  atlas.fill(Qt::green);
  atlas.setPixelColor(1, 0, Qt::red);
  atlas.setPixelColor(2, 0, Qt::yellow);
  atlas.setPixelColor(0, 1, QColor(255, 0, 0, 128));
  if (!atlas.save(directory.path() + "/atlas.png"))
  {
    return 2;
  }
  QJsonObject patch{{"file", "atlas.png"}, {"source", QJsonArray{1, 0, 2, 1}},
                    {"at", QJsonArray{3, 4}}};
  QJsonObject variant{{"canvas", QJsonArray{8, 8}}, {"patches", QJsonArray{patch}}};
  bool ok = false;
  QString error;
  auto rendered = PJ::resourceImageVariant(original, variant, directory.path(), &ok, &error);
  if (!ok || !error.isEmpty() || rendered.pixelColor(3, 4) != QColor(Qt::red) ||
      rendered.pixelColor(4, 4) != QColor(Qt::yellow) ||
      rendered.pixelColor(0, 0) != QColor(Qt::blue))
  {
    return 3;
  }
  // Descriptions use physical pixels even when the original has a high DPI tag.
  original.setDevicePixelRatio(2.0);
  rendered = PJ::resourceImageVariant(original, variant, directory.path(), &ok);
  if (!ok || rendered.devicePixelRatio() != 2.0 ||
      rendered.pixelColor(3, 4) != QColor(Qt::red))
  {
    return 4;
  }
  patch["source"] = QJsonArray{0, 1, 1, 1};
  patch["at"] = QJsonArray{0, 0};
  variant["patches"] = QJsonArray{patch};
  rendered = PJ::resourceImageVariant(original, variant, directory.path(), &ok);
  const auto blended = rendered.pixelColor(0, 0);
  if (!ok || blended.red() < 127 || blended.red() > 129 || blended.blue() < 126 ||
      blended.blue() > 128 || blended.alpha() != 255)
  {
    return 5;
  }
  const auto full = PJ::resourceImageVariant(original, QJsonObject{{"image", "atlas.png"}},
                                             directory.path(), &ok);
  if (!ok || full.size() != atlas.size() || full.pixelColor(1, 0) != QColor(Qt::red))
  {
    return 6;
  }
  if (PJ::resourceImageVariant(original, {}, directory.path(), &ok) != original || !ok)
  {
    return 7;
  }
  // A bad later patch must discard earlier drawing, rather than expose a partial translation.
  QJsonObject invalid = patch;
  invalid["file"] = "missing.png";
  variant["patches"] = QJsonArray{patch, invalid};
  auto expect_fallback = [&](const QJsonObject& value) {
    error.clear();
    const auto image = PJ::resourceImageVariant(original, value, directory.path(), &ok, &error);
    return !ok && !error.isEmpty() && image == original;
  };
  if (!expect_fallback(variant))
  {
    return 8;
  }
  for (const auto& bad : {QString("../atlas.png"), QString("/atlas.png"),
                          QString("C:/atlas.png"), QString("https://example.invalid/a.png")})
  {
    if (!expect_fallback(QJsonObject{{"image", bad}}))
    {
      return 9;
    }
  }
  for (const QJsonObject& invalid_variant : {
         QJsonObject{{"canvas", QJsonArray{8192, 8192}}, {"patches", QJsonArray{patch}}},
         QJsonObject{{"canvas", QJsonArray{8.5, 8}}, {"patches", QJsonArray{patch}}},
         QJsonObject{{"canvas", QJsonArray{8, 8}}, {"patches", QJsonArray{}}},
         QJsonObject{{"image", "atlas.png"}, {"patches", QJsonArray{patch}}}})
  {
    if (!expect_fallback(invalid_variant))
    {
      return 10;
    }
  }
  for (const auto& key : {QString("source"), QString("at")})
  {
    invalid = patch;
    invalid[key] = key == "source" ? QJsonArray{2, 1, 2, 2} : QJsonArray{8, 8};
    variant["patches"] = QJsonArray{invalid};
    if (!expect_fallback(variant))
    {
      return 11;
    }
  }
  PJ::resourceImageVariant(QImage(), {}, directory.path(), &ok);
  if (ok)
  {
    return 12;
  }
  std::cout << "PASS: native atlas pixels, high DPI, alpha, full-image/empty fallbacks, "
               "atomic failure and invalid geometry/path rejection\n";
  return 0;
}
