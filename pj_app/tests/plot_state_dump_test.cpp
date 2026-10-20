// SPDX-License-Identifier: MPL-2.0

#include <gtest/gtest.h>

#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QTemporaryDir>

#include "PlotStateDump.h"
#include "pj_datastore/writer.hpp"
#include "pj_plotting/PlotWidget.h"
#include "pj_runtime/CatalogModel.h"
#include "pj_runtime/SessionManager.h"

using namespace Qt::StringLiterals;

namespace {

/// The snapshot must report a stale adapter honestly, never repair it by reading
/// the store independently or by rebinding the curve as a side effect.
TEST(PlotStateDumpTest, ObservesAdapterCacheWithoutRepairingOrChangingViewport) {
  PJ::SessionManager session;
  PJ::CatalogModel catalog(&session);
  PJ::PlotWidget plot(&session, &catalog);
  const auto dataset = session.dataEngine().createDataset(PJ::DatasetDescriptor{.source_name = "samples"});
  ASSERT_TRUE(dataset.has_value());
  auto writer = session.dataEngine().createWriter();
  const auto handle = writer.registerScalarSeries(*dataset, "/signal", PJ::NumericType::kFloat64);
  ASSERT_TRUE(handle.has_value());
  writer.appendScalar(*handle, 1'000'000'000, 10.0);
  writer.appendScalar(*handle, 2'000'000'000, 20.0);
  ASSERT_FALSE(session.commitChunks(writer.flushAll()).empty());
  ASSERT_EQ(catalog.curves().size(), 1u);
  ASSERT_NE(plot.addCurve(catalog.curves().front().name), nullptr);
  plot.setStateId(u"snapshot"_s);
  plot.setZoomRectangle(QRectF(QPointF(0.0, 40.0), QPointF(4.0, 0.0)), false);
  const QRectF viewport = plot.currentBoundingRect();
  const auto read_curve = [&plot]() {
    return PJ::collectPlotState({&plot})[u"plots"_s].toArray().first().toObject()[u"curves"_s]
        .toArray().first().toObject();
  };
  ASSERT_EQ(read_curve()[u"finite_sample_count"_s].toInteger(), 2);

  writer.appendScalar(*handle, 3'000'000'000, 30.0);
  ASSERT_FALSE(session.dataEngine().commitChunks(writer.flushAll()).empty());
  EXPECT_EQ(read_curve()[u"finite_sample_count"_s].toInteger(), 2);
  EXPECT_EQ(plot.currentBoundingRect(), viewport);

  session.notifyIngest({handle->topic_id}, false);
  const QJsonObject curve = read_curve();
  EXPECT_EQ(curve[u"finite_sample_count"_s].toInteger(), 3);
  EXPECT_EQ(curve[u"finite_samples_in_view"_s].toInteger(), 3);
  EXPECT_DOUBLE_EQ(curve[u"sample_bounds"_s].toObject()[u"y_max"_s].toDouble(), 30.0);
  EXPECT_EQ(plot.currentBoundingRect(), viewport);
}

TEST(PlotStateDumpTest, EmptyPlotsAndWriteFailuresCannotMasqueradeAsSamples) {
  PJ::SessionManager session;
  PJ::CatalogModel catalog(&session);
  PJ::PlotWidget plot(&session, &catalog);
  const QJsonObject state = PJ::collectPlotState({&plot});
  ASSERT_EQ(state[u"version"_s].toInt(), 1);
  ASSERT_EQ(state[u"plots"_s].toArray().size(), 1);
  EXPECT_TRUE(state[u"plots"_s].toArray().first().toObject()[u"curves"_s].toArray().isEmpty());
  QTemporaryDir dir;
  ASSERT_TRUE(dir.isValid());
  EXPECT_FALSE(PJ::writePlotStateDump({&plot}, dir.path()));
  const QString path = dir.filePath(u"state.json"_s);
  ASSERT_TRUE(PJ::writePlotStateDump({&plot}, path));
  QFile file(path);
  ASSERT_TRUE(file.open(QIODevice::ReadOnly));
  EXPECT_EQ(QJsonDocument::fromJson(file.readAll()).object(), state);
}

}  // namespace
