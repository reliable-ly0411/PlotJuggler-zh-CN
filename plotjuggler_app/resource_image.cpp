// SPDX-License-Identifier: MPL-2.0
#include "resource_image.h"

#include <QHash>
#include <QJsonArray>
#include <QImageReader>
#include <QPainter>
#include <QVector>

namespace
{
constexpr int MAX_DIMENSION = 8192;
constexpr qint64 MAX_PIXELS = 16 * 1024 * 1024;

bool integer(const QJsonValue& value, int* output)
{
  if (!value.isDouble())
  {
    return false;
  }
  const int number = value.toInt(-1);
  if (number < 0 || value.toDouble() != double(number))
  {
    return false;
  }
  *output = number;
  return true;
}

bool tuple(const QJsonValue& value, int count, QVector<int>* result)
{
  if (!value.isArray() || value.toArray().size() != count)
  {
    return false;
  }
  result->clear();
  for (const auto& number : value.toArray())
  {
    int parsed = 0;
    if (!integer(number, &parsed))
    {
      return false;
    }
    result->push_back(parsed);
  }
  return true;
}

bool relativeFile(const QString& file)
{
  return !file.isEmpty() && !file.startsWith('/') && !file.contains('\\') &&
         !file.contains(':') && !file.contains(QChar(0)) &&
         !file.split('/').contains("..") && !file.split('/').contains(".");
}

bool boundedSize(const QSize& size)
{
  return size.width() > 0 && size.height() > 0 && size.width() <= MAX_DIMENSION &&
         size.height() <= MAX_DIMENSION && qint64(size.width()) * size.height() <= MAX_PIXELS;
}
}  // namespace

QImage PJ::resourceImageVariant(const QImage& original, const QJsonObject& description,
                               const QString& root, bool* ok, QString* error)
{
  if (ok)
  {
    *ok = false;
  }
  if (error)
  {
    error->clear();
  }
  const auto fail = [&](const char* message) {
    if (error)
    {
      *error = QString::fromLatin1(message);
    }
    return original;
  };
  if (original.isNull())
  {
    return fail("Original image is missing");
  }
  if (description.isEmpty())
  {
    if (ok)
    {
      *ok = true;
    }
    return original;
  }

  QHash<QString, QImage> loaded;
  const auto load = [&](const QString& file) -> QImage {
    if (!relativeFile(file))
    {
      return {};
    }
    if (!loaded.contains(file))
    {
      QImageReader reader(root + '/' + file);
      if (!boundedSize(reader.size()))
      {
        return {};
      }
      QImage image = reader.read();
      image.setDevicePixelRatio(1.0);
      loaded.insert(file, image);
    }
    return loaded.value(file);
  };
  QImage result;
  if (description.contains("image"))
  {
    if (description.contains("patches") || description.contains("canvas"))
    {
      return fail("Full image and patch descriptions cannot be combined");
    }
    result = load(description.value("image").toString());
    if (result.isNull() || !boundedSize(result.size()))
    {
      return fail("Full image is missing or invalid");
    }
  }
  else
  {
    QVector<int> canvas;
    if (!tuple(description.value("canvas"), 2, &canvas) ||
        !boundedSize(QSize(canvas[0], canvas[1])) ||
        !description.value("patches").isArray())
    {
      return fail("Invalid patch canvas");
    }
    const auto patches = description.value("patches").toArray();
    if (patches.isEmpty() || patches.size() > 256)
    {
      return fail("Invalid patch count");
    }
    result = original.scaled(QSize(canvas[0], canvas[1]), Qt::IgnoreAspectRatio,
                             Qt::SmoothTransformation)
                 .convertToFormat(QImage::Format_ARGB32_Premultiplied);
    if (result.isNull())
    {
      return fail("Cannot allocate patch canvas");
    }
    result.setDevicePixelRatio(1.0);
    QPainter painter(&result);
    for (const auto& value : patches)
    {
      if (!value.isObject())
      {
        return fail("Invalid patch object");
      }
      const auto patch = value.toObject();
      const auto image = load(patch.value("file").toString());
      QVector<int> source, at;
      if (image.isNull() || !boundedSize(image.size()) ||
          !tuple(patch.value("source"), 4, &source) ||
          !tuple(patch.value("at"), 2, &at) || source[2] <= 0 || source[3] <= 0 ||
          qint64(source[0]) + source[2] > image.width() ||
          qint64(source[1]) + source[3] > image.height() ||
          qint64(at[0]) + source[2] > result.width() ||
          qint64(at[1]) + source[3] > result.height())
      {
        return fail("Patch is missing or outside its source or destination");
      }
      // Equal source/destination sizes: caption pixels are never resampled here.
      painter.drawImage(QRect(at[0], at[1], source[2], source[3]), image,
                        QRect(source[0], source[1], source[2], source[3]));
    }
    painter.end();
  }
  if (ok)
  {
    *ok = true;
  }
  result.setDevicePixelRatio(original.devicePixelRatio());
  return result;
}
