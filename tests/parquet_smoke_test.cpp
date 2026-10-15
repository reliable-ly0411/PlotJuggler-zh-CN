// SPDX-License-Identifier: MPL-2.0
// Arrow uses the identifier "signals"; parse it before Qt defines that macro.
#include <arrow/api.h>
#include <arrow/io/api.h>
#include <parquet/arrow/writer.h>
#include <QApplication>
#include <QDialog>
#include <QPluginLoader>
#include <QRadioButton>
#include <QSettings>
#include <QTemporaryDir>
#include <QTimer>
#include <cmath>
#include <iostream>
#include "PlotJuggler/dataloader_base.h"

int main(int argc, char** argv)
{
  QApplication app(argc, argv);
  if (argc != 2) return 2;
  QTemporaryDir temporary;
  if (!temporary.isValid()) return 3;
  QSettings::setDefaultFormat(QSettings::IniFormat);
  QSettings::setPath(QSettings::IniFormat, QSettings::UserScope, temporary.path());
  QCoreApplication::setOrganizationName("PlotJuggler-tests");
  QCoreApplication::setApplicationName("ParquetCompatibility");

  arrow::DoubleBuilder builder;
  if (!builder.Append(1.25).ok() || !builder.Append(2.5).ok()) return 4;
  std::shared_ptr<arrow::Array> values;
  if (!builder.Finish(&values).ok()) return 5;
  auto table = arrow::Table::Make(arrow::schema({arrow::field("Value", arrow::float64())}),
                                std::vector<std::shared_ptr<arrow::Array>>{values});
  const QString filename = temporary.path() + "/manufactured.parquet";
  auto file = arrow::io::FileOutputStream::Open(filename.toStdString());
  if (!file.ok()) return 6;
  auto output = file.ValueOrDie();
  if (!parquet::arrow::WriteTable(*table, arrow::default_memory_pool(), output, 1024).ok() ||
      !output->Close().ok()) return 7;

  QPluginLoader library(QString::fromLocal8Bit(argv[1]));
  auto* loader = qobject_cast<PJ::DataLoader*>(library.instance());
  if (!loader) { std::cerr << library.errorString().toStdString(); return 8; }
  QTimer::singleShot(0, [] {
    for (auto* widget : QApplication::topLevelWidgets())
      if (auto* dialog = qobject_cast<QDialog*>(widget))
        if (dialog->isVisible())
        {
          if (auto* index = dialog->findChild<QRadioButton*>("radioButtonIndex"))
            index->setChecked(true);
          dialog->accept();
        }
  });
  PJ::FileLoadInfo info;
  info.filename = filename;
  PJ::PlotDataMapRef data;
  if (!loader->readDataFromFile(&info, data)) return 9;
  const auto series = data.numeric.find("Value");
  if (series == data.numeric.end() || series->second.size() != 2) return 10;
  if (std::abs(series->second.at(0).x) > 1e-8 ||
      std::abs(series->second.at(1).x - 1.0) > 1e-8 ||
      std::abs(series->second.at(0).y - 1.25) > 1e-8 ||
      std::abs(series->second.at(1).y - 2.5) > 1e-8) return 11;
  std::cout << "PASS: manufactured Parquet file survives shared-library loading with exact values\n";
  return 0;
}
