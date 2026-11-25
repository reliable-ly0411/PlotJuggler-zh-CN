#pragma once
// SPDX-License-Identifier: MPL-2.0

#include <QJsonObject>
#include <QList>
#include <QString>

namespace PJ {

class PlotWidget;

/// Observe the actual plotted adapters and viewport without invalidating caches,
/// changing the view, or reattaching curves. Sample counts describe the adapter's
/// current materialized window, not an independent read of the backing store.
[[nodiscard]] QJsonObject collectPlotState(const QList<PlotWidget*>& plots);

/// Atomically write an opt-in diagnostic snapshot; no source file contents or
/// filesystem paths are included. Call on the GUI thread after layout settlement.
[[nodiscard]] bool writePlotStateDump(const QList<PlotWidget*>& plots, const QString& path);

}  // namespace PJ
