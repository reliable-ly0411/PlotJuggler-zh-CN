// SPDX-License-Identifier: LGPL-3.0-or-later
#include <QApplication>
#include <QFileInfo>
#include <QPluginLoader>
#include <iostream>
#include <cmath>
#include "PlotJuggler/dataloader_base.h"

/// Exercise the shared-library boundary used by the application.
int main(int argc, char** argv)
{
  QApplication app(argc, argv);
  if (argc != 3) return 2;
  QPluginLoader library(QString::fromLocal8Bit(argv[1]));
  auto* loader = qobject_cast<PJ::DataLoader*>(library.instance());
  if (!loader) { std::cerr << library.errorString().toStdString(); return 3; }
  PJ::FileLoadInfo info;
  info.filename = QString::fromLocal8Bit(argv[2]);
  PJ::PlotDataMapRef data;
  if (!loader->readDataFromFile(&info, data)) return 4;
  for (const auto& expected : {std::make_pair(0, 1.23), {1, 2.34}, {200, 3.45}})
  {
    const std::string prefix = "/TST/#" + std::to_string(expected.first) + "/Value";
    bool found = false;
    for (const auto& series : data.numeric)
    {
      if (series.first.find(prefix) != 0) continue;
      found = true;
      if (series.first.find("[V]") == std::string::npos || series.second.size() != 1 ||
          std::abs(series.second.at(0).y - expected.second) > 1e-8 ||
          std::abs(series.second.at(0).x - (expected.first == 0 ? 1.0 : expected.first == 1 ? 2.0 : 3.0)) > 1e-8) return 5;
    }
    if (!found) return 6;
  }
  const auto parameter = data.numeric.find("/1. Parameters/TEST_PARAM");
  if (parameter == data.numeric.end() || parameter->second.size() != 1 ||
      std::abs(parameter->second.at(0).x - 1.5) > 1e-8 ||
      std::abs(parameter->second.at(0).y - 7.5) > 1e-8) return 10;
  data.numeric.clear();
  const QString directory = QFileInfo(info.filename).absolutePath();
  info.filename = directory + "/gps.BIN";
  if (!loader->readDataFromFile(&info, data)) return 12;
  // GPS week 2000, week milliseconds 345600000, minus 18 leap seconds.
  constexpr double gps_epoch = 1525910382.0;
  const auto gps_parameter = data.numeric.find("/1. Parameters/TEST_PARAM");
  if (gps_parameter == data.numeric.end() ||
      std::abs(gps_parameter->second.at(0).x - (gps_epoch - 0.5)) > 1e-6) return 13;
  bool gps_value_found = false;
  for (const auto& item : data.numeric)
    if (item.first.find("/GPS/#0/GMS") == 0)
    {
      gps_value_found = true;
      if (item.second.size() != 2 ||
          std::abs(item.second.at(1).x - gps_epoch) > 1e-6 ||
          std::abs(item.second.at(1).y - 345600.0) > 1e-6) return 14;
    }
  if (!gps_value_found) return 15;
  data.numeric.clear();
  info.filename = directory + "/second.BIN";
  if (!loader->readDataFromFile(&info, data) || data.numeric.size() != 1) return 7;
  const auto& series = data.numeric.begin()->second;
  if (data.numeric.begin()->first != "/TST/Value" || series.size() != 1 ||
      std::abs(series.at(0).x - 4.0) > 1e-8 || std::abs(series.at(0).y - 2.5) > 1e-8) return 8;
  data.numeric.clear();
  info.filename = directory + "/invalid.BIN";
  if (loader->readDataFromFile(&info, data) || !data.numeric.empty()) return 9;
  for (const auto& filename : {"invalid_fmt.BIN", "invalid_fmtu.BIN"})
  {
    info.filename = directory + "/" + filename;
    bool rejected = false;
    try { loader->readDataFromFile(&info, data); }
    catch (const std::exception&) { rejected = true; }
    if (!rejected || !data.numeric.empty()) return 11;
  }
  std::cout << "PASS: BIN, FMT/FMTU, UNIT/MULT, TimeUS, GNSS time and GMS scaling, instances 0/1/200, legacy PARM timestamps, repeat-load and malformed input\n";
  return 0;
}
