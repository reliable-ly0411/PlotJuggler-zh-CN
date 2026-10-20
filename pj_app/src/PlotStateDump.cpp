// SPDX-License-Identifier: MPL-2.0

#include "PlotStateDump.h"

#include <QJsonArray>
#include <QJsonDocument>
#include <QSaveFile>
#include <algorithm>
#include <cmath>
#include <limits>
#include <qwt_plot_curve.h>

#include "pj_plotting/DatastoreCurveAdapter.h"
#include "pj_plotting/PlotWidget.h"

using namespace Qt::StringLiterals;

namespace PJ {
namespace {

/// Plot viewports are y-up QRectFs; their height may legitimately be negative.
QJsonObject rectState(const QRectF& rect) {
  return {{u"x_min"_s, rect.left()},
          {u"x_max"_s, rect.right()},
          {u"y_min"_s, std::min(rect.top(), rect.bottom())},
          {u"y_max"_s, std::max(rect.top(), rect.bottom())}};
}

/// Count precisely the finite points offered to Qwt, including viewport overlap.
QJsonObject curveState(const PlotWidgetBase::CurveInfo& info, const QRectF& viewport) {
  const auto* data = info.curve->data();
  QJsonObject curve{{u"visible"_s, info.curve->isVisible()}};
  if (const auto* adapter = dynamic_cast<const DatastoreCurveAdapter*>(data)) {
    curve.insert(u"topic"_s, adapter->source().topic_name);
    curve.insert(u"field"_s, adapter->source().field_name);
  }
  const std::size_t count = data != nullptr ? data->size() : 0;
  qint64 finite = 0;
  qint64 in_view = 0;
  double min_x = std::numeric_limits<double>::infinity();
  double max_x = -std::numeric_limits<double>::infinity();
  double min_y = std::numeric_limits<double>::infinity();
  double max_y = -std::numeric_limits<double>::infinity();
  const QRectF normalized_viewport = viewport.normalized();
  for (std::size_t index = 0; index < count; ++index) {
    const QPointF point = data->sample(index);
    if (!std::isfinite(point.x()) || !std::isfinite(point.y())) {
      continue;
    }
    ++finite;
    if (normalized_viewport.contains(point)) {
      ++in_view;
    }
    min_x = std::min(min_x, point.x());
    max_x = std::max(max_x, point.x());
    min_y = std::min(min_y, point.y());
    max_y = std::max(max_y, point.y());
  }
  curve.insert(u"sample_count"_s, static_cast<qint64>(count));
  curve.insert(u"finite_sample_count"_s, finite);
  curve.insert(u"finite_samples_in_view"_s, in_view);
  if (finite != 0) {
    curve.insert(
        u"sample_bounds"_s,
        QJsonObject{{u"x_min"_s, min_x}, {u"x_max"_s, max_x}, {u"y_min"_s, min_y}, {u"y_max"_s, max_y}});
  }
  return curve;
}

}  // namespace

QJsonObject collectPlotState(const QList<PlotWidget*>& plots) {
  QJsonArray states;
  for (const PlotWidget* plot : plots) {
    const QRectF viewport = plot->currentBoundingRect();
    QJsonArray curves;
    for (const auto& info : plot->curveList()) {
      curves.append(curveState(info, viewport));
    }
    states.append(QJsonObject{{u"id"_s, plot->stateId()},
                              {u"viewport"_s, rectState(viewport)},
                              {u"curves"_s, curves}});
  }
  return {{u"version"_s, 1}, {u"plots"_s, states}};
}

bool writePlotStateDump(const QList<PlotWidget*>& plots, const QString& path) {
  QSaveFile file(path);
  if (!file.open(QIODevice::WriteOnly)) {
    return false;
  }
  const QByteArray bytes = QJsonDocument(collectPlotState(plots)).toJson(QJsonDocument::Indented);
  return file.write(bytes) == bytes.size() && file.commit();
}

}  // namespace PJ
