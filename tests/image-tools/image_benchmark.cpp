// SPDX-License-Identifier: MPL-2.0
#include "localized_meme.h"
#include <QCommandLineParser>
#include <QElapsedTimer>
#include <QFile>
#include <QGuiApplication>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QPixmapCache>
#include <iostream>
#ifdef Q_OS_WIN
#include <windows.h>
#include <psapi.h>
#endif

int main(int argc, char** argv)
{
  QGuiApplication app(argc, argv);
  QCommandLineParser parser;
  parser.addOption({"out", "JSON output", "file"});
  parser.addOption({"ids", "Ordered meme identifiers", "ids", "1,26,52,93"});
  parser.addOption({"language", "zh_CN or en_US", "locale", "zh_CN"});
  parser.addOption({"cache", "warm or clear (Qt pixmap cache, not OS cache)", "mode", "warm"});
  parser.addOption({"rounds", "Measured rounds after priming", "count", "12"});
  parser.process(app);
  const bool chinese = parser.value("language") == "zh_CN";
  const bool clear = parser.value("cache") == "clear";
  const int rounds = parser.value("rounds").toInt();
  if (rounds < 1 || rounds > 1000 || parser.value("out").isEmpty())
  {
    return 2;
  }
  QList<int> ids;
  for (const QString& text : parser.value("ids").split(','))
  {
    bool valid = false;
    const int id = text.toInt(&valid);
    if (!valid || id < 0 || id >= 106)
    {
      return 3;
    }
    ids.push_back(id);
  }
  QJsonArray measurements;
  QElapsedTimer timer;
  timer.start();
  bool loaded = false;
  QPixmap image = localizedMeme(ids.front(), chinese, &loaded);
  const double first_ms = timer.nsecsElapsed() / 1.0e6;
  if (!loaded || image.isNull())
  {
    return 4;
  }
  // Prime each ID. A fresh process is required to measure a process-cold first image.
  for (int id : ids)
  {
    image = localizedMeme(id, chinese, &loaded);
    if (!loaded || image.isNull())
    {
      return 5;
    }
  }
  for (int round = 0; round < rounds; ++round)
  {
    for (int id : ids)
    {
      if (clear)
      {
        QPixmapCache::clear();
      }
      timer.restart();
      image = localizedMeme(id, chinese, &loaded);
      const double ms = timer.nsecsElapsed() / 1.0e6;
      if (!loaded || image.isNull())
      {
        return 6;
      }
      measurements.append(QJsonObject{{"id", id}, {"round", round}, {"render_ms", ms},
                                       {"width", image.width()}, {"height", image.height()}});
    }
  }
  QJsonObject result{{"label", PJ_BENCH_LABEL}, {"qt", qVersion()},
                     {"language", chinese ? "zh_CN" : "en_US"},
                     {"cache", clear ? "Qt pixmap cache cleared per image" : "primed round-robin"},
                     {"OS_cache", "uncontrolled; not flushed"},
                     {"operation", "localizedMeme load/composite/final-scale; no PNG encoding or disk export"},
                     {"first_process_image_ms", first_ms}, {"samples", measurements}};
#ifdef Q_OS_WIN
  PROCESS_MEMORY_COUNTERS_EX memory{};
  memory.cb = sizeof(memory);
  if (GetProcessMemoryInfo(GetCurrentProcess(), reinterpret_cast<PROCESS_MEMORY_COUNTERS*>(&memory),
                           sizeof(memory)))
  {
    result["peak_working_set_bytes"] = double(memory.PeakWorkingSetSize);
    result["private_bytes_at_end"] = double(memory.PrivateUsage);
  }
#endif
  QFile out(parser.value("out"));
  if (!out.open(QIODevice::WriteOnly))
  {
    return 7;
  }
  out.write(QJsonDocument(result).toJson());
  std::cout << PJ_BENCH_LABEL << " first image ms=" << first_ms << '\n';
  return 0;
}
