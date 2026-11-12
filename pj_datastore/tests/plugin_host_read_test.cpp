// Copyright 2026 Davide Faconti
// SPDX-License-Identifier: MPL-2.0

#include <gtest/gtest.h>

#include <algorithm>
#include <climits>
#include <cstdint>
#include <memory>
#include <string_view>
#include <vector>

#include "pj_base/sdk/plugin_data_api.hpp"
#include "pj_base/type_tree.hpp"
#include "pj_datastore/engine.hpp"
#include "pj_datastore/object_store.hpp"
#include "pj_datastore/plugin_data_host.hpp"
#include "pj_datastore/writer.hpp"
#include "plugin_host_test_helpers.hpp"

namespace PJ {
namespace {

using namespace PJ::sdk;
using test::ArrowSeries;
using test::expectNullRows;

struct Fixture {
  DataEngine engine;
  ObjectStore object_store;
  DatastoreToolboxHost toolbox_impl{engine, object_store};
  ToolboxHostView toolbox{toolbox_impl.raw()};
};

TEST(PluginDataHostReadTest, CatalogSnapshotIsDeterministicAndIncludesSchemaBackedTopics) {
  Fixture f;
  DataWriter writer(f.engine);

  auto schema =
      makeStruct("pose", {makePrimitive("x", PrimitiveType::kFloat32), makePrimitive("y", PrimitiveType::kInt16)});
  const auto schema_id = *writer.registerSchema("pose_schema", schema);
  const auto source_a = *f.toolbox.createDataSource("robot_b");
  const auto source_b = *f.toolbox.createDataSource("robot_a");

  TopicDescriptor desc;
  desc.name = "pose";
  desc.schema_id = schema_id;
  ASSERT_TRUE(writer.registerTopic(source_a.id, desc).has_value());

  auto topic_b = *f.toolbox.ensureTopic(source_b, "imu");
  ASSERT_TRUE(f.toolbox.ensureField(topic_b, "ax", PrimitiveType::kFloat32).has_value());

  auto snapshot_or = f.toolbox.catalogSnapshot();
  ASSERT_TRUE(snapshot_or.has_value());
  auto snapshot = std::move(snapshot_or.value());
  ASSERT_EQ(snapshot.dataSources().size(), 2U);
  EXPECT_EQ(snapshot.dataSources()[0].handle.id, source_a.id);
  EXPECT_EQ(snapshot.dataSources()[1].handle.id, source_b.id);
  ASSERT_EQ(snapshot.topics().size(), 2U);
  EXPECT_EQ(snapshot.topics()[0].source.id, source_a.id);
  EXPECT_EQ(toStringView(snapshot.topics()[0].name), "pose");
  EXPECT_EQ(snapshot.topics()[0].field_count, 2U);
  EXPECT_EQ(snapshot.topics()[1].source.id, source_b.id);
  EXPECT_EQ(toStringView(snapshot.topics()[1].name), "imu");
  EXPECT_EQ(snapshot.topics()[1].field_count, 1U);
  ASSERT_EQ(snapshot.fields().size(), 3U);
  EXPECT_EQ(fromAbiType(snapshot.fields()[0].type), PrimitiveType::kFloat32);
  EXPECT_EQ(fromAbiType(snapshot.fields()[1].type), PrimitiveType::kInt16);
  EXPECT_EQ(fromAbiType(snapshot.fields()[2].type), PrimitiveType::kFloat32);

  std::vector<std::string_view> field_names;
  for (const auto& field : snapshot.fields()) {
    field_names.push_back(toStringView(field.name));
  }
  EXPECT_NE(std::find(field_names.begin(), field_names.end(), "x"), field_names.end());
  EXPECT_NE(std::find(field_names.begin(), field_names.end(), "y"), field_names.end());
  EXPECT_NE(std::find(field_names.begin(), field_names.end(), "ax"), field_names.end());
}

TEST(PluginDataHostReadTest, CatalogSnapshotMustBeReacquiredAfterStructuralMutation) {
  Fixture f;
  const auto source = *f.toolbox.createDataSource("src");
  const auto topic = *f.toolbox.ensureTopic(source, "data");
  ASSERT_TRUE(f.toolbox.ensureField(topic, "a", PrimitiveType::kFloat64).has_value());

  auto snapshot_before_or = f.toolbox.catalogSnapshot();
  ASSERT_TRUE(snapshot_before_or.has_value());
  auto snapshot_before = std::move(snapshot_before_or.value());
  EXPECT_EQ(snapshot_before.fields().size(), 1U);

  ASSERT_TRUE(f.toolbox.ensureField(topic, "b", PrimitiveType::kFloat64).has_value());

  auto snapshot_after_or = f.toolbox.catalogSnapshot();
  ASSERT_TRUE(snapshot_after_or.has_value());
  auto snapshot_after = std::move(snapshot_after_or.value());
  EXPECT_EQ(snapshot_after.fields().size(), 2U);
  ASSERT_EQ(snapshot_before.fields().size(), 1U);
  EXPECT_EQ(toStringView(snapshot_before.fields()[0].name), "a");
}

TEST(PluginDataHostReadTest, ReadSeriesPreservesExactPrimitiveTypesAndNulls) {
  Fixture f;
  const auto source = *f.toolbox.createDataSource("src");
  const auto topic = *f.toolbox.ensureTopic(source, "data");
  const auto i8 = *f.toolbox.ensureField(topic, "i8", PrimitiveType::kInt8);
  const auto u32 = *f.toolbox.ensureField(topic, "u32", PrimitiveType::kUint32);
  const auto u64 = *f.toolbox.ensureField(topic, "u64", PrimitiveType::kUint64);
  const auto flag = *f.toolbox.ensureField(topic, "flag", PrimitiveType::kBool);
  const auto label = *f.toolbox.ensureField(topic, "label", PrimitiveType::kString);

  const std::vector<NamedFieldValue> row1 = {
      {.name = "i8", .value = int8_t{-5}},
      {.name = "u32", .value = uint32_t{123456}},
      {.name = "u64", .value = uint64_t{(uint64_t{1} << 60) + 7}},
      {.name = "flag", .value = true},
      {.name = "label", .value = std::string_view("alpha")},
  };
  const std::vector<NamedFieldValue> row2 = {
      {.name = "i8", .value = PJ::kNull},
      {.name = "u32", .value = uint32_t{42}},
      {.name = "u64", .value = uint64_t{9}},
      {.name = "flag", .value = false},
      {.name = "label", .value = std::string_view("beta")},
  };
  ASSERT_TRUE(f.toolbox.appendRecord(topic, 1, row1).has_value());
  ASSERT_TRUE(f.toolbox.appendRecord(topic, 2, row2).has_value());
  f.toolbox_impl.flushPending();

  auto i8_series_or = f.toolbox.readSeries(i8);
  ASSERT_TRUE(i8_series_or.has_value());
  auto i8_series = std::move(i8_series_or.value());
  ASSERT_EQ(i8_series.type(), PrimitiveType::kInt8);
  ASSERT_EQ(i8_series.timestamps().size(), 2U);
  EXPECT_EQ(i8_series.timestamps()[0], 1);
  EXPECT_EQ(i8_series.timestamps()[1], 2);
  EXPECT_EQ(i8_series.valuesAsInt8()[0], -5);
  expectNullRows(f.toolbox, i8, {false, true});

  auto u32_series_or = f.toolbox.readSeries(u32);
  ASSERT_TRUE(u32_series_or.has_value());
  auto u32_series = std::move(u32_series_or.value());
  ASSERT_EQ(u32_series.type(), PrimitiveType::kUint32);
  ASSERT_EQ(u32_series.rowCount(), 2U);
  EXPECT_EQ(u32_series.valuesAsUint32()[0], 123456U);
  EXPECT_EQ(u32_series.valuesAsUint32()[1], 42U);
  expectNullRows(f.toolbox, u32, {false, false});

  auto u64_series_or = f.toolbox.readSeries(u64);
  ASSERT_TRUE(u64_series_or.has_value());
  auto u64_series = std::move(u64_series_or.value());
  ASSERT_EQ(u64_series.type(), PrimitiveType::kUint64);
  ASSERT_EQ(u64_series.rowCount(), 2U);
  EXPECT_EQ(u64_series.valuesAsUint64()[0], (uint64_t{1} << 60) + 7);
  EXPECT_EQ(u64_series.valuesAsUint64()[1], 9U);
  expectNullRows(f.toolbox, u64, {false, false});

  auto flag_series_or = f.toolbox.readSeries(flag);
  ASSERT_TRUE(flag_series_or.has_value());
  auto flag_series = std::move(flag_series_or.value());
  ASSERT_EQ(flag_series.type(), PrimitiveType::kBool);
  ASSERT_EQ(flag_series.timestamps().size(), 2U);
  ArrowSeries flag_arrow;
  ASSERT_TRUE(flag_arrow.read(f.toolbox, flag).has_value());
  EXPECT_EQ(flag_arrow.format(), "b");
  EXPECT_EQ(ArrowArrayViewGetIntUnsafe(flag_arrow.values(), 0), 1);
  EXPECT_EQ(ArrowArrayViewGetIntUnsafe(flag_arrow.values(), 1), 0);
  expectNullRows(f.toolbox, flag, {false, false});

  auto label_series_or = f.toolbox.readSeries(label);
  ASSERT_TRUE(label_series_or.has_value());
  ASSERT_EQ(label_series_or->type(), PrimitiveType::kString);
  ASSERT_EQ(label_series_or->timestamps().size(), 2U);
  ArrowSeries label_arrow;
  ASSERT_TRUE(label_arrow.read(f.toolbox, label).has_value());
  EXPECT_EQ(label_arrow.format(), "u");
  EXPECT_EQ(label_arrow.stringAt(0), "alpha");
  EXPECT_EQ(label_arrow.stringAt(1), "beta");
  expectNullRows(f.toolbox, label, {false, false});
}

TEST(PluginDataHostReadTest, ReadSeriesRejectsUnknownField) {
  Fixture f;
  const auto source = *f.toolbox.createDataSource("src");
  const auto topic = *f.toolbox.ensureTopic(source, "data");
  ASSERT_TRUE(f.toolbox.ensureField(topic, "value", PrimitiveType::kFloat64).has_value());
  const FieldHandle bad_field{.topic = topic, .id = 999};
  const auto result = f.toolbox.readSeries(bad_field);
  EXPECT_FALSE(result.has_value());
}

// ---------------------------------------------------------------------------
// Catalog edge cases
// ---------------------------------------------------------------------------

TEST(PluginDataHostReadTest, EmptyCatalogSnapshotReturnsZeroCounts) {
  Fixture f;
  auto snapshot_or = f.toolbox.catalogSnapshot();
  ASSERT_TRUE(snapshot_or.has_value());
  auto snapshot = std::move(snapshot_or.value());
  EXPECT_EQ(snapshot.dataSources().size(), 0U);
  EXPECT_EQ(snapshot.topics().size(), 0U);
  EXPECT_EQ(snapshot.fields().size(), 0U);
}

TEST(PluginDataHostReadTest, FieldHandleTopicBindingMatchesContainingTopic) {
  Fixture f;
  const auto source = *f.toolbox.createDataSource("src");
  const auto topic = *f.toolbox.ensureTopic(source, "data");
  ASSERT_TRUE(f.toolbox.ensureField(topic, "a", PrimitiveType::kFloat32).has_value());
  ASSERT_TRUE(f.toolbox.ensureField(topic, "b", PrimitiveType::kInt32).has_value());

  auto snapshot_or = f.toolbox.catalogSnapshot();
  ASSERT_TRUE(snapshot_or.has_value());
  auto snapshot = std::move(snapshot_or.value());

  for (const auto& topic_info : snapshot.topics()) {
    for (uint32_t i = topic_info.first_field; i < topic_info.first_field + topic_info.field_count; ++i) {
      ASSERT_LT(i, snapshot.fields().size());
      EXPECT_EQ(snapshot.fields()[i].handle.topic.id, topic_info.handle.id)
          << "field index " << i << " should belong to topic " << topic_info.handle.id;
    }
  }
}

TEST(PluginDataHostReadTest, CatalogSnapshotTopicOrderIsStableWithinSource) {
  Fixture f;
  const auto source = *f.toolbox.createDataSource("src");
  ASSERT_TRUE(f.toolbox.ensureTopic(source, "b").has_value());
  ASSERT_TRUE(f.toolbox.ensureTopic(source, "a").has_value());

  auto snapshot_or = f.toolbox.catalogSnapshot();
  ASSERT_TRUE(snapshot_or.has_value());
  auto snapshot = std::move(snapshot_or.value());
  ASSERT_EQ(snapshot.topics().size(), 2U);
  EXPECT_LT(snapshot.topics()[0].handle.id, snapshot.topics()[1].handle.id);
}

TEST(PluginDataHostReadTest, ReadSeriesRejectsUnknownTopic) {
  Fixture f;
  const FieldHandle bad_field{.topic = TopicHandle{.id = 999}, .id = 0};
  const auto result = f.toolbox.readSeries(bad_field);
  EXPECT_FALSE(result.has_value());
}

// ---------------------------------------------------------------------------
// Type-specific reads
// ---------------------------------------------------------------------------

TEST(PluginDataHostReadTest, ReadSeriesFloat32RoundTrip) {
  Fixture f;
  const auto source = *f.toolbox.createDataSource("src");
  const auto topic = *f.toolbox.ensureTopic(source, "data");
  const auto field = *f.toolbox.ensureField(topic, "val", PrimitiveType::kFloat32);

  const float values[] = {1.5F, -2.25F, 0.0F};
  for (int i = 0; i < 3; ++i) {
    const std::vector<NamedFieldValue> fields = {{.name = "val", .value = values[i]}};
    ASSERT_TRUE(f.toolbox.appendRecord(topic, i, fields).has_value());
  }
  f.toolbox_impl.flushPending();

  auto series_or = f.toolbox.readSeries(field);
  ASSERT_TRUE(series_or.has_value());
  auto series = std::move(series_or.value());
  ASSERT_EQ(series.type(), PrimitiveType::kFloat32);
  ASSERT_EQ(series.timestamps().size(), 3U);
  EXPECT_FLOAT_EQ(series.valuesAsFloat32()[0], 1.5F);
  EXPECT_FLOAT_EQ(series.valuesAsFloat32()[1], -2.25F);
  EXPECT_FLOAT_EQ(series.valuesAsFloat32()[2], 0.0F);
}

TEST(PluginDataHostReadTest, ReadSeriesFloat64RoundTrip) {
  Fixture f;
  const auto source = *f.toolbox.createDataSource("src");
  const auto topic = *f.toolbox.ensureTopic(source, "data");
  const auto field = *f.toolbox.ensureField(topic, "val", PrimitiveType::kFloat64);

  const double values[] = {1e-15, -3.14159265358979, 1e+300};
  for (int i = 0; i < 3; ++i) {
    const std::vector<NamedFieldValue> fields = {{.name = "val", .value = values[i]}};
    ASSERT_TRUE(f.toolbox.appendRecord(topic, i, fields).has_value());
  }
  f.toolbox_impl.flushPending();

  auto series_or = f.toolbox.readSeries(field);
  ASSERT_TRUE(series_or.has_value());
  auto series = std::move(series_or.value());
  ASSERT_EQ(series.type(), PrimitiveType::kFloat64);
  ASSERT_EQ(series.timestamps().size(), 3U);
  EXPECT_DOUBLE_EQ(series.valuesAsFloat64()[0], 1e-15);
  EXPECT_DOUBLE_EQ(series.valuesAsFloat64()[1], -3.14159265358979);
  EXPECT_DOUBLE_EQ(series.valuesAsFloat64()[2], 1e+300);
}

TEST(PluginDataHostReadTest, ReadSeriesInt32RoundTrip) {
  Fixture f;
  const auto source = *f.toolbox.createDataSource("src");
  const auto topic = *f.toolbox.ensureTopic(source, "data");
  const auto field = *f.toolbox.ensureField(topic, "val", PrimitiveType::kInt32);

  const int32_t values[] = {-1, 0, INT32_MAX};
  for (int i = 0; i < 3; ++i) {
    const std::vector<NamedFieldValue> fields = {{.name = "val", .value = values[i]}};
    ASSERT_TRUE(f.toolbox.appendRecord(topic, i, fields).has_value());
  }
  f.toolbox_impl.flushPending();

  auto series_or = f.toolbox.readSeries(field);
  ASSERT_TRUE(series_or.has_value());
  auto series = std::move(series_or.value());
  ASSERT_EQ(series.type(), PrimitiveType::kInt32);
  ASSERT_EQ(series.timestamps().size(), 3U);
  EXPECT_EQ(series.valuesAsInt32()[0], -1);
  EXPECT_EQ(series.valuesAsInt32()[1], 0);
  EXPECT_EQ(series.valuesAsInt32()[2], INT32_MAX);
}

TEST(PluginDataHostReadTest, ReadSeriesInt64RoundTrip) {
  Fixture f;
  const auto source = *f.toolbox.createDataSource("src");
  const auto topic = *f.toolbox.ensureTopic(source, "data");
  const auto field = *f.toolbox.ensureField(topic, "val", PrimitiveType::kInt64);

  // Keep spread within uint32_t range to avoid Frame-of-Reference offset overflow.
  const int64_t values[] = {-500'000'000LL, 0, 500'000'000LL};
  for (int i = 0; i < 3; ++i) {
    const std::vector<NamedFieldValue> fields = {{.name = "val", .value = values[i]}};
    ASSERT_TRUE(f.toolbox.appendRecord(topic, i, fields).has_value());
  }
  f.toolbox_impl.flushPending();

  auto series_or = f.toolbox.readSeries(field);
  ASSERT_TRUE(series_or.has_value());
  auto series = std::move(series_or.value());
  ASSERT_EQ(series.type(), PrimitiveType::kInt64);
  ASSERT_EQ(series.timestamps().size(), 3U);
  EXPECT_EQ(series.valuesAsInt64()[0], -500'000'000LL);
  EXPECT_EQ(series.valuesAsInt64()[1], 0);
  EXPECT_EQ(series.valuesAsInt64()[2], 500'000'000LL);
}

TEST(PluginDataHostReadTest, ReadSeriesStringWithNulls) {
  Fixture f;
  const auto source = *f.toolbox.createDataSource("src");
  const auto topic = *f.toolbox.ensureTopic(source, "data");
  const auto field = *f.toolbox.ensureField(topic, "label", PrimitiveType::kString);

  const std::vector<NamedFieldValue> row0 = {{.name = "label", .value = std::string_view("abc")}};
  const std::vector<NamedFieldValue> row1 = {{.name = "label", .value = PJ::kNull}};
  const std::vector<NamedFieldValue> row2 = {{.name = "label", .value = std::string_view("de")}};
  ASSERT_TRUE(f.toolbox.appendRecord(topic, 0, row0).has_value());
  ASSERT_TRUE(f.toolbox.appendRecord(topic, 1, row1).has_value());
  ASSERT_TRUE(f.toolbox.appendRecord(topic, 2, row2).has_value());
  f.toolbox_impl.flushPending();

  auto series_or = f.toolbox.readSeries(field);
  ASSERT_TRUE(series_or.has_value());
  auto series = std::move(series_or.value());
  ASSERT_EQ(series.type(), PrimitiveType::kString);
  ASSERT_EQ(series.timestamps().size(), 3U);

  ArrowSeries arrow;
  ASSERT_TRUE(arrow.read(f.toolbox, field).has_value());
  EXPECT_EQ(arrow.format(), "u");
  expectNullRows(f.toolbox, field, {false, true, false});
  EXPECT_EQ(arrow.stringAt(0), "abc");
  EXPECT_EQ(arrow.stringAt(2), "de");
  // Arrow strings use one terminal offset after the last row.
  EXPECT_EQ(arrow.values()->buffer_views[1].data.as_int32[3], 5);
  EXPECT_EQ(arrow.values()->buffer_views[2].size_bytes, 5);
}

// ---------------------------------------------------------------------------
// Boundary conditions
// ---------------------------------------------------------------------------

TEST(PluginDataHostReadTest, ReadSeriesEmptyField) {
  Fixture f;
  const auto source = *f.toolbox.createDataSource("src");
  const auto topic = *f.toolbox.ensureTopic(source, "data");
  const auto field = *f.toolbox.ensureField(topic, "val", PrimitiveType::kFloat64);

  f.toolbox_impl.flushPending();

  auto series_or = f.toolbox.readSeries(field);
  ASSERT_TRUE(series_or.has_value());
  auto series = std::move(series_or.value());
  EXPECT_EQ(series.timestamps().size(), 0U);
  EXPECT_EQ(series.type(), PrimitiveType::kFloat64);
  EXPECT_TRUE(series.valid());
}

TEST(PluginDataHostReadTest, ReadSeriesMultiChunkFloat64) {
  Fixture f;
  const auto source = *f.toolbox.createDataSource("src");
  const auto topic = *f.toolbox.ensureTopic(source, "data");
  const auto field = *f.toolbox.ensureField(topic, "val", PrimitiveType::kFloat64);

  constexpr int kRowCount = 1100;  // > 1024 default chunk size
  for (int i = 0; i < kRowCount; ++i) {
    const std::vector<NamedFieldValue> fields = {{.name = "val", .value = double(i) * 0.1}};
    ASSERT_TRUE(f.toolbox.appendRecord(topic, i, fields).has_value());
  }
  f.toolbox_impl.flushPending();

  auto series_or = f.toolbox.readSeries(field);
  ASSERT_TRUE(series_or.has_value());
  auto series = std::move(series_or.value());
  ASSERT_EQ(series.type(), PrimitiveType::kFloat64);
  ASSERT_EQ(series.timestamps().size(), static_cast<size_t>(kRowCount));

  EXPECT_EQ(series.timestamps()[0], 0);
  EXPECT_EQ(series.timestamps()[kRowCount - 1], kRowCount - 1);
  EXPECT_EQ(series.timestamps()[550], 550);

  EXPECT_DOUBLE_EQ(series.valuesAsFloat64()[0], 0.0);
  EXPECT_DOUBLE_EQ(series.valuesAsFloat64()[kRowCount - 1], double(kRowCount - 1) * 0.1);
  EXPECT_DOUBLE_EQ(series.valuesAsFloat64()[550], 550.0 * 0.1);
}

// ---------------------------------------------------------------------------
// SDK RAII tests
// ---------------------------------------------------------------------------

TEST(PluginDataHostReadTest, CatalogSnapshotDefaultConstructorIsEmpty) {
  CatalogSnapshot snapshot;
  EXPECT_EQ(snapshot.dataSources().size(), 0U);
  EXPECT_EQ(snapshot.topics().size(), 0U);
  EXPECT_EQ(snapshot.fields().size(), 0U);
  // Destructor runs safely — no crash.
}

TEST(PluginDataHostReadTest, CatalogSnapshotMoveTransfersOwnership) {
  Fixture f;
  const auto source = *f.toolbox.createDataSource("src");
  ASSERT_TRUE(f.toolbox.ensureTopic(source, "t").has_value());

  auto original_or = f.toolbox.catalogSnapshot();
  ASSERT_TRUE(original_or.has_value());
  auto original = std::move(original_or.value());
  ASSERT_GT(original.dataSources().size(), 0U);

  // Move-construct.
  CatalogSnapshot moved(std::move(original));
  EXPECT_GT(moved.dataSources().size(), 0U);
  EXPECT_EQ(original.dataSources().size(), 0U);  // NOLINT(bugprone-use-after-move)

  // Move-assign.
  CatalogSnapshot assigned;
  assigned = std::move(moved);
  EXPECT_GT(assigned.dataSources().size(), 0U);
  EXPECT_EQ(moved.dataSources().size(), 0U);  // NOLINT(bugprone-use-after-move)
}

TEST(PluginDataHostReadTest, MaterializedSeriesMoveTransfersOwnership) {
  Fixture f;
  const auto source = *f.toolbox.createDataSource("src");
  const auto topic = *f.toolbox.ensureTopic(source, "data");
  const auto field = *f.toolbox.ensureField(topic, "val", PrimitiveType::kFloat64);

  const std::vector<NamedFieldValue> fields = {{.name = "val", .value = 3.14}};
  ASSERT_TRUE(f.toolbox.appendRecord(topic, 1, fields).has_value());
  f.toolbox_impl.flushPending();

  auto original_or = f.toolbox.readSeries(field);
  ASSERT_TRUE(original_or.has_value());
  auto original = std::move(original_or.value());
  ASSERT_EQ(original.timestamps().size(), 1U);
  ASSERT_EQ(original.type(), PrimitiveType::kFloat64);

  // Move-construct.
  MaterializedSeriesView moved(std::move(original));
  EXPECT_EQ(moved.type(), PrimitiveType::kFloat64);
  ASSERT_EQ(moved.timestamps().size(), 1U);
  EXPECT_EQ(moved.timestamps()[0], 1);
  EXPECT_DOUBLE_EQ(moved.valuesAsFloat64()[0], 3.14);
  EXPECT_EQ(original.timestamps().size(), 0U);  // NOLINT(bugprone-use-after-move)

  // Move-assign.
  MaterializedSeriesView assigned;
  assigned = std::move(moved);
  EXPECT_EQ(assigned.type(), PrimitiveType::kFloat64);
  ASSERT_EQ(assigned.timestamps().size(), 1U);
  EXPECT_EQ(assigned.timestamps()[0], 1);
  EXPECT_DOUBLE_EQ(assigned.valuesAsFloat64()[0], 3.14);
  EXPECT_EQ(moved.timestamps().size(), 0U);  // NOLINT(bugprone-use-after-move)
}

}  // namespace
}  // namespace PJ
