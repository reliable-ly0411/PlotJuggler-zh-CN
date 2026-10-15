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
  data.numeric.clear();
  const QString directory = QFileInfo(info.filename).absolutePath();
  info.filename = directory + "/second.BIN";
  if (!loader->readDataFromFile(&info, data) || data.numeric.size() != 1) return 7;
  const auto& series = data.numeric.begin()->second;
  if (data.numeric.begin()->first != "/TST/Value" || series.size() != 1 ||
      std::abs(series.at(0).x - 4.0) > 1e-8 || std::abs(series.at(0).y - 2.5) > 1e-8) return 8;
  data.numeric.clear();
  info.filename = directory + "/invalid.BIN";
  if (loader->readDataFromFile(&info, data) || !data.numeric.empty()) return 9;
  std::cout << "PASS: BIN, FMT/FMTU, UNIT/MULT, TimeUS, instances 0/1/200, repeat-load and truncated input\n";
  return 0;
}
