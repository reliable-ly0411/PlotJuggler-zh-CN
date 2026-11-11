// SPDX-License-Identifier: MPL-2.0
// Opt-in, synthetic-data acceptance; never invoked during ordinary startup.
#include "mainwindow.h"
#include "plotwidget.h"
#include <QAction>
#include <QApplication>
#include <QJsonArray>
#include <QJsonObject>
#include <QKeySequence>
#include <QMenu>
#include <QSaveFile>
#include <QSet>
#include <QTimer>
#include <algorithm>

namespace
{
QJsonObject checkPlotMenu(PlotWidget* plot, const QString& output)
{
  QJsonObject result;
  QTimer timer;
  timer.setSingleShot(true);
  QObject::connect(&timer, &QTimer::timeout, plot, [&]() {
    auto* menu = qobject_cast<QMenu*>(QApplication::activePopupWidget());
    if (!menu)
    {
      return;
    }
    QSet<QString> used;
    QJsonArray labels, duplicates;
    for (const auto* action : menu->actions())
    {
      if (action->isSeparator() || !action->isVisible())
      {
        continue;
      }
      labels.append(action->text());
      const QString mnemonic = QKeySequence::mnemonic(action->text()).toString().toUpper();
      if (mnemonic.isEmpty())
      {
        continue;
      }
      if (used.contains(mnemonic))
      {
        duplicates.append(action->text());
      }
      used.insert(mnemonic);
    }
    result["labels"] = labels;
    result["duplicate_mnemonics"] = duplicates;
    result["screenshot"] = menu->grab().save(output);
    result["ok"] = !labels.isEmpty() && duplicates.isEmpty() && result["screenshot"].toBool();
    menu->close();
  });
  timer.start(150);
  const bool invoked = QMetaObject::invokeMethod(
      plot, "canvasContextMenuTriggered", Qt::DirectConnection, Q_ARG(QPoint, QPoint(40, 40)));
  result["invoked"] = invoked;
  return result;
}
}  // namespace

QJsonObject MainWindow::checkAcceptanceRoundTrip(const QString& output)
{
  QJsonObject result;
  std::vector<std::string> names;
  for (const auto& series : _mapped_plot_data.numeric)
  {
    if (series.second.size() > 0)
    {
      names.push_back(series.first);
    }
  }
  std::sort(names.begin(), names.end(), [&](const auto& left, const auto& right) {
    const auto left_size = _mapped_plot_data.numeric.at(left).size();
    const auto right_size = _mapped_plot_data.numeric.at(right).size();
    return left_size != right_size ? left_size > right_size : left < right;
  });
  PlotWidget* plot = nullptr;
  const auto locate = [&]() {
    plot = nullptr;
    forEachWidget([&](PlotWidget* widget) {
      if (!plot)
      {
        plot = widget;
      }
    });
  };
  locate();
  if (!plot || names.empty())
  {
    return QJsonObject{ { "ok", false } };
  }
  const auto& name = names.front();
  plot->removeAllCurves();
  const auto* curve = plot->addCurve(name);
  const bool curve_added = curve && curve->curve->dataSize() > 1;
  plot->zoomOut(false);
  QApplication::processEvents();
  result["series"] = QString::fromStdString(name);
  result["source_points"] = int(_mapped_plot_data.numeric.at(name).size());
  result["curve_added"] = curve_added;
  result["timeseries_menu"] = checkPlotMenu(plot, output + "/timeseries-menu.png");
  const auto layout = xmlSaveState();
  const QString filename = output + "/roundtrip-layout.xml";
  QSaveFile file(filename);
  const auto bytes = layout.toByteArray(2);
  const bool saved =
      file.open(QIODevice::WriteOnly) && file.write(bytes) == bytes.size() && file.commit();
  plot->removeAllCurves();
  const bool cleared = plot->curveList().empty();
  const bool loaded = saved && loadLayoutFromFile(filename, false);
  locate();
  const bool restored =
      loaded && plot && plot->curveList().size() == 1 && plot->curveList().front().src_name == name;
  result["layout_saved"] = saved;
  result["curves_cleared"] = cleared;
  result["layout_restored"] = restored;
  if (!restored)
  {
    result["ok"] = false;
    return result;
  }
  plot->removeAllCurves();
  static_cast<PlotWidgetBase*>(plot)->setModeXY(true);
  const auto* xy_curve = plot->addCurveXY(name, name, "acceptance XY");
  const bool xy_added = xy_curve && xy_curve->curve->dataSize() > 1 && plot->isXYPlot();
  plot->zoomOut(false);
  QApplication::processEvents();
  result["xy_added"] = xy_added;
  result["xy_mode"] = plot->isXYPlot();
  result["xy_plot_screenshot"] = grab().save(output + "/xy-plot.png");
  result["xy_menu"] = checkPlotMenu(plot, output + "/xy-menu.png");
  // Restore the real serialized timeseries layout after exercising the XY menu.
  const bool final_loaded = loadLayoutFromFile(filename, false);
  locate();
  const bool final_restored = final_loaded && plot && !plot->isXYPlot() &&
                              plot->curveList().size() == 1 &&
                              plot->curveList().front().src_name == name;
  QApplication::processEvents();
  result["ok"] = curve_added && saved && cleared && restored && xy_added && final_restored &&
                 result["timeseries_menu"].toObject().value("ok").toBool() &&
                 result["xy_menu"].toObject().value("ok").toBool();
  return result;
}
