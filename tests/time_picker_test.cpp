// SPDX-License-Identifier: MPL-2.0
// Translated AM/PM labels must never change the selected time interval.
#include "plotjuggler_plugins/ToolboxMosaico/src/ui/picker/time_picker_widget.h"
#include <QApplication>
#include <QTranslator>
#include <QComboBox>
#include <QSpinBox>

int main(int argc, char** argv)
{
  QApplication app(argc, argv);
  QTranslator translator;
  if (argc < 2 || !translator.load(QString::fromLocal8Bit(argv[1]))) return 1;
  app.installTranslator(&translator);
  TimePickerWidget picker;
  const auto combos = picker.findChildren<QComboBox*>();
  const auto spins = picker.findChildren<QSpinBox*>();
  if (combos.size() != 2 || spins.size() != 4) return 2;
  if (combos[0]->itemText(0) != QString::fromUtf8("上午") ||
      combos[0]->itemText(1) != QString::fromUtf8("下午")) return 3;
  if (combos[0]->itemData(0) != "AM" || combos[0]->itemData(1) != "PM") return 4;
  if (picker.fromTime() != QTime(0, 0) || picker.toTime() != QTime(23, 59)) return 5;
  combos[0]->setCurrentIndex(1);
  if (picker.fromTime() != QTime(12, 0)) return 6;
  spins[0]->setValue(1); spins[1]->setValue(59);
  if (picker.fromTime() != QTime(13, 59)) return 7;
  combos[1]->setCurrentIndex(0); spins[2]->setValue(12);
  if (picker.toTime() != QTime(0, 59)) return 8;
  return 0;
}
