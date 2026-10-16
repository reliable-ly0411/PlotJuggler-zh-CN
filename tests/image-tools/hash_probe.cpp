// SPDX-License-Identifier: MPL-2.0
#include <QCoreApplication>
#include <QCryptographicHash>
#include <QDir>
#include <QElapsedTimer>
#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>
#ifdef PJ_HASH_IMAGES
#include <QImage>
#include <QThreadPool>
#endif
#include <cstring>
#include <iostream>

namespace
{
QString digest(const char* bytes, int row_bytes, int height, int stride)
{
  QCryptographicHash hash(QCryptographicHash::Sha256);
  for (int y = 0; y < height; ++y)
    hash.addData(bytes + y * stride, row_bytes);
  return QString::fromLatin1(hash.result().toHex());
}

bool save(const QString& path, const QByteArray& bytes)
{
  QFile file(path);
  return file.open(QIODevice::WriteOnly) && file.write(bytes) == bytes.size();
}
}  // namespace

int main(int argc, char** argv)
{
  QCoreApplication app(argc, argv);
  if (argc != 8)
    return 2;
  const int width = QString::fromLocal8Bit(argv[2]).toInt();
  const int height = QString::fromLocal8Bit(argv[3]).toInt();
  const QString mode = QString::fromLocal8Bit(argv[4]);
  const int iterations = QString::fromLocal8Bit(argv[5]).toInt();
  const QString output = QString::fromLocal8Bit(argv[6]);
  const QString expected = QString::fromLatin1(argv[7]);
  if (width <= 0 || height <= 0 || qint64(width) * height > 16 * 1024 * 1024 ||
      iterations <= 0 || expected.size() != 64 || !QDir().mkpath(output))
    return 3;
  QFile input(QString::fromLocal8Bit(argv[1]));
  if (!input.open(QIODevice::ReadOnly))
    return 4;
  const QByteArray fixture = input.readAll();
  const int row_bytes = width * 4;
  if (fixture.size() != row_bytes * height)
    return 5;

  // Core-only builds never create a QImage, pixmap, GUI application or thread pool.
  // The owned, immutable fixture remains alive for every addData call.
  QByteArray padded(fixture.size() + 64, char(0xA5));
#ifdef PJ_HASH_IMAGES
  if (qEnvironmentVariableIntValue("PJ_SCALE_THREADS") > 0)
    QThreadPool::globalInstance()->setMaxThreadCount(qEnvironmentVariableIntValue("PJ_SCALE_THREADS"));
  QImage source(width, height, QImage::Format_RGB32);
  for (int y = 0; y < height; ++y)
  {
    auto* row = reinterpret_cast<QRgb*>(source.scanLine(y));
    const auto* rgba = reinterpret_cast<const uchar*>(fixture.constData() + y * row_bytes);
    for (int x = 0; x < width; ++x)
    {
      if (rgba[x * 4 + 3] != 255)
        return 6;
      row[x] = qRgb(rgba[x * 4], rgba[x * 4 + 1], rgba[x * 4 + 2]);
    }
  }
#endif
  QElapsedTimer timer;
  timer.start();
  const int configured_seconds = qEnvironmentVariableIntValue("PJ_HASH_SECONDS");
  const int seconds = configured_seconds > 0 ? configured_seconds : 45;
  int completed = 0;
  QJsonObject failure;
  for (int iteration = 0; iteration < iterations && timer.elapsed() < seconds * 1000; ++iteration)
  {
    const int offset = mode == "offset" ? iteration % 64 : 0;
    const char* bytes = fixture.constData();
    int stride = row_bytes;
    QString actual;
#ifdef PJ_HASH_IMAGES
    QImage converted;
    if (mode == "image-copy")
    {
      const auto copy = source.copy();
      converted = copy.convertToFormat(QImage::Format_RGBA8888);
    }
    else if (mode == "image-direct")
      converted = source.convertToFormat(QImage::Format_RGBA8888);
    else
      return 7;
    bytes = reinterpret_cast<const char*>(converted.constBits());
    stride = converted.bytesPerLine();
    actual = digest(bytes, row_bytes, height, stride);
#else
    if (mode == "offset")
    {
      std::memcpy(padded.data() + offset, fixture.constData(), fixture.size());
      bytes = padded.constData() + offset;
    }
    if (mode == "once")
      actual = QString::fromLatin1(QCryptographicHash::hash(fixture, QCryptographicHash::Sha256).toHex());
    else if (mode == "rows" || mode == "offset")
      actual = digest(bytes, row_bytes, height, stride);
    else
      return 8;
#endif
    ++completed;
    if (actual != expected)
    {
      // Retain the first digest, retry on the same live buffer, then freeze its rows.
      const QString retry = digest(bytes, row_bytes, height, stride);
      QByteArray consumed;
      consumed.reserve(fixture.size());
      for (int y = 0; y < height; ++y)
        consumed.append(bytes + y * stride, row_bytes);
      failure = {{"iteration", iteration}, {"initial_sha256", actual},
          {"repeat_rows_sha256", retry},
          {"snapshot_sha256", QString::fromLatin1(QCryptographicHash::hash(consumed, QCryptographicHash::Sha256).toHex())},
          {"snapshot_equals_fixture", consumed == fixture}, {"stride", stride},
          {"pointer_mod_64", int(reinterpret_cast<quintptr>(bytes) % 64)}};
      if (!save(output + "/capture.rgba", consumed))
        return 9;
      break;
    }
  }
  const QJsonObject report{{"qt", qVersion()}, {"mode", mode}, {"width", width},
      {"height", height}, {"row_bytes", row_bytes}, {"completed", completed},
      {"requested", iterations}, {"elapsed_ms", double(timer.elapsed())},
      {"expected_sha256", expected}, {"failure", failure},
      {"fixture_final_sha256", QString::fromLatin1(QCryptographicHash::hash(fixture, QCryptographicHash::Sha256).toHex())},
      {"malloc_perturb", qEnvironmentVariable("MALLOC_PERTURB_")},
      {"threads", qEnvironmentVariable("PJ_SCALE_THREADS")}};
  if (!save(output + "/report.json", QJsonDocument(report).toJson()))
    return 10;
  std::cout << (failure.isEmpty() ? "PASS" : "FAIL") << " mode=" << mode
            << " completed=" << completed << " initial="
            << failure["initial_sha256"].toString().toStdString() << '\n';
  return failure.isEmpty() ? 0 : 15;
}
