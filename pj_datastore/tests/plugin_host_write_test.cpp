// Copyright 2026 Davide Faconti
// SPDX-License-Identifier: MPL-2.0

#include <gtest/gtest.h>

#include <cstddef>
#include <cstdint>
#include <string_view>
#include <vector>

#include "nanoarrow/nanoarrow.h"
#include "nanoarrow/nanoarrow.hpp"
#include "pj_base/sdk/plugin_data_api.hpp"
#include "pj_datastore/engine.hpp"
#include "pj_datastore/object_store.hpp"
#include "pj_datastore/plugin_data_host.hpp"
#include "plugin_host_test_helpers.hpp"

namespace PJ {
namespace {

using namespace PJ::sdk;
using test::ArrowSeries;
using test::expectNullRows;

/// A one-batch stream owns the schema and array until the host accepts it.
Expected<ArrowStreamHolder> makeStream(ArrowSchema* schema, ArrowArray* array) {
  ArrowStreamHolder stream;
  if (ArrowBasicArrayStreamInit(stream.out(), schema, 1) != NANOARROW_OK) {
    return unexpected("Could not allocate a one-batch Arrow stream");
  }
  ArrowBasicArrayStreamSetArray(stream.get(), 0, array);
  return stream;
}

struct Fixture {
  DataEngine engine;
  ObjectStore object_store;
  DatastoreToolboxHost toolbox_impl{engine, object_store};
  ToolboxHostView toolbox{toolbox_impl.raw()};
};

TEST(PluginDataHostWriteTest, SourceHostWritesWithinBoundDataSource) {
  Fixture f;
  const auto source = *f.toolbox.createDataSource("sensor");

  DatastoreSourceWriteHost source_impl(f.engine, source);
  SourceWriteHostView writer(source_impl.raw());

  const auto topic = *writer.ensureTopic("imu");
  const auto field = *writer.ensureField(topic, "ax", PrimitiveType::kFloat32);
  EXPECT_EQ(field.topic.id, topic.id);

  const std::vector<NamedFieldValue> fields = {{.name = "ax", .value = 1.25F}};
  ASSERT_TRUE(writer.appendRecord(topic, 10, fields).has_value());
  source_impl.flushPending();

  auto series_or = f.toolbox.readSeries(field);
  ASSERT_TRUE(series_or.has_value());
  auto series = std::move(series_or.value());
  ASSERT_EQ(series.type(), PrimitiveType::kFloat32);
  ASSERT_EQ(series.timestamps().size(), 1U);
  EXPECT_EQ(series.timestamps()[0], 10);
  EXPECT_FLOAT_EQ(series.valuesAsFloat32()[0], 1.25F);
}

TEST(PluginDataHostWriteTest, AppendRecordConvertsExactNumericValuesAndNullsInexactValues) {
  Fixture f;
  const auto source = *f.toolbox.createDataSource("sensor");

  DatastoreSourceWriteHost source_impl(f.engine, source);
  SourceWriteHostView writer(source_impl.raw());

  const auto topic = *writer.ensureTopic("imu");
  const auto field = *writer.ensureField(topic, "ax", PrimitiveType::kInt32);
  const std::vector<NamedFieldValue> exact = {{.name = "ax", .value = int16_t{7}}};
  const std::vector<NamedFieldValue> inexact = {{.name = "ax", .value = 7.5}};
  ASSERT_TRUE(writer.appendRecord(topic, 1, exact).has_value());
  ASSERT_TRUE(writer.appendRecord(topic, 2, inexact).has_value());
  source_impl.flushPending();
  auto series_or = f.toolbox.readSeries(field);
  ASSERT_TRUE(series_or.has_value());
  ASSERT_EQ(series_or->type(), PrimitiveType::kInt32);
  ASSERT_EQ(series_or->timestamps().size(), 2U);
  EXPECT_EQ(series_or->timestamps()[0], 1);
  EXPECT_EQ(series_or->timestamps()[1], 2);
  EXPECT_EQ(series_or->valuesAsInt32()[0], 7);
  expectNullRows(f.toolbox, field, {false, true});
}

TEST(PluginDataHostWriteTest, AppendRecordFastRejectsUnknownFieldHandle) {
  Fixture f;
  const auto source = *f.toolbox.createDataSource("sensor");

  DatastoreSourceWriteHost source_impl(f.engine, source);
  SourceWriteHostView writer(source_impl.raw());

  const auto topic = *writer.ensureTopic("imu");
  ASSERT_TRUE(writer.ensureField(topic, "ax", PrimitiveType::kFloat64).has_value());

  const FieldHandle bad_field{.topic = topic, .id = 999};
  const std::vector<BoundFieldValue> fields = {{.field = bad_field, .value = 1.0}};
  const auto status = writer.appendBoundRecord(topic, 1, fields);
  EXPECT_FALSE(status.has_value());
}

TEST(PluginDataHostWriteTest, ParserHostIsBoundToSingleTopic) {
  Fixture f;
  const auto source = *f.toolbox.createDataSource("sensor");
  const auto topic = *f.toolbox.ensureTopic(source, "packets");
  const auto other_topic = *f.toolbox.ensureTopic(source, "other");
  const auto foreign_field = *f.toolbox.ensureField(other_topic, "count", PrimitiveType::kInt32);

  DatastoreParserWriteHost parser_impl(f.engine, topic);
  ParserWriteHostView parser(parser_impl.raw());

  const auto count_field = *parser.ensureField("count", PrimitiveType::kInt32);
  const std::vector<NamedFieldValue> good_fields = {{.name = "count", .value = int32_t{42}}};
  ASSERT_TRUE(parser.appendRecord(100, good_fields).has_value());

  const std::vector<BoundFieldValue> bad_fields = {{.field = foreign_field, .value = int32_t{9}}};
  const auto status = parser.appendBoundRecord(101, bad_fields);
  EXPECT_FALSE(status.has_value());

  parser_impl.flushPending();
  auto series_or = f.toolbox.readSeries(count_field);
  ASSERT_TRUE(series_or.has_value());
  auto series = std::move(series_or.value());
  ASSERT_EQ(series.timestamps().size(), 1U);
  EXPECT_EQ(series.timestamps()[0], 100);
  ASSERT_EQ(series.type(), PrimitiveType::kInt32);
  EXPECT_EQ(series.valuesAsInt32()[0], 42);
}

TEST(PluginDataHostWriteTest, ToolboxCanWriteIntoExistingDataSource) {
  Fixture f;
  const auto source = *f.toolbox.createDataSource("sensor");
  const auto topic = *f.toolbox.ensureTopic(source, "labels");
  const auto field = *f.toolbox.ensureField(topic, "name", PrimitiveType::kString);

  const std::vector<NamedFieldValue> fields = {{.name = "name", .value = std::string_view("hello")}};
  ASSERT_TRUE(f.toolbox.appendRecord(topic, 5, fields).has_value());
  f.toolbox_impl.flushPending();

  auto series_or = f.toolbox.readSeries(field);
  ASSERT_TRUE(series_or.has_value());
  auto series = std::move(series_or.value());
  ASSERT_EQ(series.type(), PrimitiveType::kString);
  ASSERT_EQ(series.timestamps().size(), 1U);
  EXPECT_EQ(series.timestamps()[0], 5);
  ArrowSeries arrow;
  ASSERT_TRUE(arrow.read(f.toolbox, field).has_value());
  EXPECT_EQ(arrow.format(), "u");
  EXPECT_FALSE(ArrowArrayViewIsNull(arrow.values(), 0));
  EXPECT_EQ(arrow.stringAt(0), "hello");
}

TEST(PluginDataHostWriteTest, ArrowStreamPreservesExactNarrowPrimitiveTypes) {
  Fixture f;
  const auto source = *f.toolbox.createDataSource("sensor");

  DatastoreSourceWriteHost source_impl(f.engine, source);
  SourceWriteHostView writer(source_impl.raw());
  const auto topic = *writer.ensureTopic("narrow");

  nanoarrow::UniqueSchema schema;
  ASSERT_EQ(ArrowSchemaInitFromType(schema.get(), NANOARROW_TYPE_STRUCT), NANOARROW_OK);
  ASSERT_EQ(ArrowSchemaAllocateChildren(schema.get(), 4), NANOARROW_OK);
  ArrowSchemaInit(schema->children[0]);
  ASSERT_EQ(ArrowSchemaSetName(schema->children[0], "_timestamp"), NANOARROW_OK);
  ASSERT_EQ(ArrowSchemaSetType(schema->children[0], NANOARROW_TYPE_INT64), NANOARROW_OK);
  ArrowSchemaInit(schema->children[1]);
  ASSERT_EQ(ArrowSchemaSetName(schema->children[1], "i8"), NANOARROW_OK);
  ASSERT_EQ(ArrowSchemaSetType(schema->children[1], NANOARROW_TYPE_INT8), NANOARROW_OK);
  ArrowSchemaInit(schema->children[2]);
  ASSERT_EQ(ArrowSchemaSetName(schema->children[2], "u16"), NANOARROW_OK);
  ASSERT_EQ(ArrowSchemaSetType(schema->children[2], NANOARROW_TYPE_UINT16), NANOARROW_OK);
  ArrowSchemaInit(schema->children[3]);
  ASSERT_EQ(ArrowSchemaSetName(schema->children[3], "u32"), NANOARROW_OK);
  ASSERT_EQ(ArrowSchemaSetType(schema->children[3], NANOARROW_TYPE_UINT32), NANOARROW_OK);

  nanoarrow::UniqueArray array;
  ASSERT_EQ(ArrowArrayInitFromSchema(array.get(), schema.get(), nullptr), NANOARROW_OK);
  ASSERT_EQ(ArrowArrayStartAppending(array.get()), NANOARROW_OK);

  for (int64_t i = 0; i < 3; ++i) {
    ASSERT_EQ(ArrowArrayAppendInt(array->children[0], 100 + i), NANOARROW_OK);
    ASSERT_EQ(ArrowArrayAppendInt(array->children[1], -5 + i), NANOARROW_OK);
    ASSERT_EQ(ArrowArrayAppendUInt(array->children[2], 1000 + static_cast<uint64_t>(i)), NANOARROW_OK);
    ASSERT_EQ(ArrowArrayAppendUInt(array->children[3], 70000 + static_cast<uint64_t>(i)), NANOARROW_OK);
    ASSERT_EQ(ArrowArrayFinishElement(array.get()), NANOARROW_OK);
  }
  ASSERT_EQ(ArrowArrayFinishBuildingDefault(array.get(), nullptr), NANOARROW_OK);

  auto stream_or = makeStream(schema.get(), array.get());
  ASSERT_TRUE(stream_or.has_value());
  auto stream = std::move(*stream_or);
  ASSERT_TRUE(writer.appendArrowStream(topic, std::move(stream), "_timestamp").has_value());
  source_impl.flushPending();

  auto snapshot_or = f.toolbox.catalogSnapshot();
  ASSERT_TRUE(snapshot_or.has_value());
  auto snapshot = std::move(snapshot_or.value());
  PrimitiveType i8_type = PrimitiveType::kFloat64;
  PrimitiveType u16_type = PrimitiveType::kFloat64;
  PrimitiveType u32_type = PrimitiveType::kFloat64;
  for (const auto& field : snapshot.fields()) {
    const auto name = toStringView(field.name);
    if (name == "i8") {
      i8_type = fromAbiType(field.type);
    } else if (name == "u16") {
      u16_type = fromAbiType(field.type);
    } else if (name == "u32") {
      u32_type = fromAbiType(field.type);
    }
  }

  ASSERT_EQ(i8_type, PrimitiveType::kInt8);
  ASSERT_EQ(u16_type, PrimitiveType::kUint16);
  ASSERT_EQ(u32_type, PrimitiveType::kUint32);
  ASSERT_EQ(snapshot.fields().size(), 3U);
  for (const auto& field : snapshot.fields()) {
    EXPECT_EQ(field.handle.topic.id, topic.id);
    auto series_or = f.toolbox.readSeries(field.handle);
    ASSERT_TRUE(series_or.has_value());
    ASSERT_EQ(series_or->type(), fromAbiType(field.type));
    ASSERT_EQ(series_or->rowCount(), 3U);
    for (int64_t row = 0; row < 3; ++row) {
      EXPECT_EQ(series_or->timestamps()[row], 100 + row);
      if (toStringView(field.name) == "i8") {
        EXPECT_EQ(series_or->valuesAsInt8()[row], -5 + row);
      } else if (toStringView(field.name) == "u16") {
        EXPECT_EQ(series_or->valuesAsUint16()[row], 1000 + row);
      } else {
        ASSERT_EQ(toStringView(field.name), "u32");
        EXPECT_EQ(series_or->valuesAsUint32()[row], 70000 + row);
      }
    }
    expectNullRows(f.toolbox, field.handle, {false, false, false});
  }
}

TEST(PluginDataHostWriteTest, CreateDataSourceReturnsDistinctHandles) {
  Fixture f;
  const auto source_a = *f.toolbox.createDataSource("alpha");
  const auto source_b = *f.toolbox.createDataSource("beta");
  EXPECT_NE(source_a.id, source_b.id);
}

TEST(PluginDataHostWriteTest, EnsureTopicIsIdempotent) {
  Fixture f;
  const auto source = *f.toolbox.createDataSource("sensor");

  DatastoreSourceWriteHost source_impl(f.engine, source);
  SourceWriteHostView writer(source_impl.raw());

  const auto topic1 = *writer.ensureTopic("imu");
  const auto topic2 = *writer.ensureTopic("imu");
  EXPECT_EQ(topic1.id, topic2.id);
}

TEST(PluginDataHostWriteTest, EnsureTopicDifferentNamesYieldDifferentIds) {
  Fixture f;
  const auto source = *f.toolbox.createDataSource("sensor");

  DatastoreSourceWriteHost source_impl(f.engine, source);
  SourceWriteHostView writer(source_impl.raw());

  const auto topic_a = *writer.ensureTopic("imu");
  const auto topic_b = *writer.ensureTopic("gps");
  EXPECT_NE(topic_a.id, topic_b.id);
}

TEST(PluginDataHostWriteTest, EnsureFieldIsIdempotentForSameType) {
  Fixture f;
  const auto source = *f.toolbox.createDataSource("sensor");

  DatastoreSourceWriteHost source_impl(f.engine, source);
  SourceWriteHostView writer(source_impl.raw());

  const auto topic = *writer.ensureTopic("imu");
  const auto field1 = *writer.ensureField(topic, "ax", PrimitiveType::kFloat64);
  const auto field2 = *writer.ensureField(topic, "ax", PrimitiveType::kFloat64);
  EXPECT_EQ(field1.id, field2.id);
  EXPECT_EQ(field1.topic.id, field2.topic.id);
}

TEST(PluginDataHostWriteTest, EnsureFieldRejectsTypeMismatchOnExistingField) {
  Fixture f;
  const auto source = *f.toolbox.createDataSource("sensor");

  DatastoreSourceWriteHost source_impl(f.engine, source);
  SourceWriteHostView writer(source_impl.raw());

  const auto topic = *writer.ensureTopic("imu");
  ASSERT_TRUE(writer.ensureField(topic, "x", PrimitiveType::kFloat64).has_value());
  const auto result = writer.ensureField(topic, "x", PrimitiveType::kInt32);
  EXPECT_FALSE(result.has_value());
}

TEST(PluginDataHostWriteTest, AppendRecordRejectsDuplicateFieldNames) {
  Fixture f;
  const auto source = *f.toolbox.createDataSource("sensor");

  DatastoreSourceWriteHost source_impl(f.engine, source);
  SourceWriteHostView writer(source_impl.raw());

  const auto topic = *writer.ensureTopic("imu");
  const auto x = *writer.ensureField(topic, "x", PrimitiveType::kInt32);

  const std::vector<NamedFieldValue> fields = {
      {.name = "x", .value = int32_t{1}},
      {.name = "x", .value = int32_t{2}},
  };
  const auto status = writer.appendRecord(topic, 1, fields);
  EXPECT_FALSE(status.has_value());
  const std::vector<NamedFieldValue> aliases = {
      {.name = "nested/x", .value = 1.0},
      {.name = "nested//x", .value = 2.0},
  };
  EXPECT_FALSE(writer.appendRecord(topic, 2, aliases).has_value());
  source_impl.flushPending();
  auto series_or = f.toolbox.readSeries(x);
  ASSERT_TRUE(series_or.has_value());
  EXPECT_EQ(series_or->rowCount(), 0U);
}

TEST(PluginDataHostWriteTest, AppendRecordRejectsInvalidTopicHandle) {
  Fixture f;
  const auto source = *f.toolbox.createDataSource("sensor");

  DatastoreSourceWriteHost source_impl(f.engine, source);
  SourceWriteHostView writer(source_impl.raw());

  const TopicHandle bad_topic{.id = 999};
  const std::vector<NamedFieldValue> fields = {{.name = "x", .value = int32_t{1}}};
  const auto status = writer.appendRecord(bad_topic, 1, fields);
  EXPECT_FALSE(status.has_value());
}

TEST(PluginDataHostWriteTest, AppendRecordSparseFieldsProduceNullsForMissingColumns) {
  Fixture f;
  const auto source = *f.toolbox.createDataSource("sensor");

  DatastoreSourceWriteHost source_impl(f.engine, source);
  SourceWriteHostView writer(source_impl.raw());

  const auto topic = *writer.ensureTopic("imu");
  const auto field_a = *writer.ensureField(topic, "a", PrimitiveType::kFloat64);
  const auto field_b = *writer.ensureField(topic, "b", PrimitiveType::kFloat64);

  // Append only field "a", leaving "b" missing.
  const std::vector<NamedFieldValue> fields = {{.name = "a", .value = double{3.14}}};
  ASSERT_TRUE(writer.appendRecord(topic, 100, fields).has_value());
  source_impl.flushPending();

  auto series_b_or = f.toolbox.readSeries(field_b);
  ASSERT_TRUE(series_b_or.has_value());
  auto series_b = std::move(*series_b_or);
  ASSERT_EQ(series_b.timestamps().size(), 1U);
  EXPECT_EQ(series_b.timestamps()[0], 100);
  expectNullRows(f.toolbox, field_b, {true});

  // Field "a" should have valid data.
  auto series_a_or = f.toolbox.readSeries(field_a);
  ASSERT_TRUE(series_a_or.has_value());
  auto series_a = std::move(*series_a_or);
  ASSERT_EQ(series_a.timestamps().size(), 1U);
  ASSERT_EQ(series_a.type(), PrimitiveType::kFloat64);
  EXPECT_DOUBLE_EQ(series_a.valuesAsFloat64()[0], 3.14);
  expectNullRows(f.toolbox, field_a, {false});
}

TEST(PluginDataHostWriteTest, AppendRecordTimestampOnlyRow) {
  Fixture f;
  const auto source = *f.toolbox.createDataSource("sensor");

  DatastoreSourceWriteHost source_impl(f.engine, source);
  SourceWriteHostView writer(source_impl.raw());

  const auto topic = *writer.ensureTopic("heartbeat");
  const std::vector<NamedFieldValue> fields = {};
  const auto status = writer.appendRecord(topic, 42, fields);
  // Just verify it does not crash. Accept either success or error.
  (void)status;
}

TEST(PluginDataHostWriteTest, AppendRecordFastHappyPath) {
  Fixture f;
  const auto source = *f.toolbox.createDataSource("sensor");

  DatastoreSourceWriteHost source_impl(f.engine, source);
  SourceWriteHostView writer(source_impl.raw());

  const auto topic = *writer.ensureTopic("imu");
  const auto field = *writer.ensureField(topic, "ax", PrimitiveType::kFloat64);

  const std::vector<BoundFieldValue> fields = {{.field = field, .value = double{2.5}}};
  ASSERT_TRUE(writer.appendBoundRecord(topic, 10, fields).has_value());
  source_impl.flushPending();

  auto series_or = f.toolbox.readSeries(field);
  ASSERT_TRUE(series_or.has_value());
  auto series = std::move(*series_or);
  ASSERT_EQ(series.timestamps().size(), 1U);
  EXPECT_EQ(series.timestamps()[0], 10);
  ASSERT_EQ(series.type(), PrimitiveType::kFloat64);
  EXPECT_DOUBLE_EQ(series.valuesAsFloat64()[0], 2.5);
}

TEST(PluginDataHostWriteTest, AppendRecordFastRejectsWrongTopic) {
  Fixture f;
  const auto source = *f.toolbox.createDataSource("sensor");

  DatastoreSourceWriteHost source_impl(f.engine, source);
  SourceWriteHostView writer(source_impl.raw());

  const auto topic_a = *writer.ensureTopic("imu");
  const auto topic_b = *writer.ensureTopic("gps");
  const auto field_a = *writer.ensureField(topic_a, "ax", PrimitiveType::kFloat64);

  // Use field from topic_a with topic_b.
  const std::vector<BoundFieldValue> fields = {{.field = field_a, .value = double{1.0}}};
  const auto status = writer.appendBoundRecord(topic_b, 1, fields);
  EXPECT_FALSE(status.has_value());
}

TEST(PluginDataHostWriteTest, AppendRecordFastRejectsDuplicateFieldIds) {
  Fixture f;
  const auto source = *f.toolbox.createDataSource("sensor");

  DatastoreSourceWriteHost source_impl(f.engine, source);
  SourceWriteHostView writer(source_impl.raw());

  const auto topic = *writer.ensureTopic("imu");
  const auto field = *writer.ensureField(topic, "ax", PrimitiveType::kFloat64);

  const std::vector<BoundFieldValue> fields = {
      {.field = field, .value = double{1.0}},
      {.field = field, .value = double{2.0}},
  };
  const auto status = writer.appendBoundRecord(topic, 1, fields);
  EXPECT_FALSE(status.has_value());
}

TEST(PluginDataHostWriteTest, AppendBoundRecordConvertsExactNumericValuesAndNullsInexactValues) {
  Fixture f;
  const auto source = *f.toolbox.createDataSource("sensor");

  DatastoreSourceWriteHost source_impl(f.engine, source);
  SourceWriteHostView writer(source_impl.raw());

  const auto topic = *writer.ensureTopic("imu");
  const auto field = *writer.ensureField(topic, "ax", PrimitiveType::kFloat64);

  const std::vector<BoundFieldValue> exact = {{.field = field, .value = int32_t{42}}};
  const std::vector<BoundFieldValue> inexact = {{.field = field, .value = (int64_t{1} << 53) + 1}};
  ASSERT_TRUE(writer.appendBoundRecord(topic, 1, exact).has_value());
  ASSERT_TRUE(writer.appendBoundRecord(topic, 2, inexact).has_value());
  source_impl.flushPending();
  auto series_or = f.toolbox.readSeries(field);
  ASSERT_TRUE(series_or.has_value());
  ASSERT_EQ(series_or->type(), PrimitiveType::kFloat64);
  ASSERT_EQ(series_or->timestamps().size(), 2U);
  EXPECT_EQ(series_or->timestamps()[0], 1);
  EXPECT_EQ(series_or->timestamps()[1], 2);
  EXPECT_DOUBLE_EQ(series_or->valuesAsFloat64()[0], 42.0);
  expectNullRows(f.toolbox, field, {false, true});
}

TEST(PluginDataHostWriteTest, AppendRecordNullValueViaIsNull) {
  Fixture f;
  const auto source = *f.toolbox.createDataSource("sensor");

  DatastoreSourceWriteHost source_impl(f.engine, source);
  SourceWriteHostView writer(source_impl.raw());

  const auto topic = *writer.ensureTopic("imu");
  const auto field = *writer.ensureField(topic, "ax", PrimitiveType::kFloat64);

  const std::vector<NamedFieldValue> fields = {{.name = "ax", .value = PJ::kNull}};
  ASSERT_TRUE(writer.appendRecord(topic, 10, fields).has_value());
  source_impl.flushPending();

  auto series_or = f.toolbox.readSeries(field);
  ASSERT_TRUE(series_or.has_value());
  auto series = std::move(*series_or);
  ASSERT_EQ(series.timestamps().size(), 1U);
  EXPECT_EQ(series.timestamps()[0], 10);
  expectNullRows(f.toolbox, field, {true});
}

TEST(PluginDataHostWriteTest, AppendRecordFastNullValue) {
  Fixture f;
  const auto source = *f.toolbox.createDataSource("sensor");

  DatastoreSourceWriteHost source_impl(f.engine, source);
  SourceWriteHostView writer(source_impl.raw());

  const auto topic = *writer.ensureTopic("imu");
  const auto field = *writer.ensureField(topic, "ax", PrimitiveType::kFloat64);

  const std::vector<BoundFieldValue> fields = {{.field = field, .value = PJ::kNull}};
  ASSERT_TRUE(writer.appendBoundRecord(topic, 10, fields).has_value());
  source_impl.flushPending();

  auto series_or = f.toolbox.readSeries(field);
  ASSERT_TRUE(series_or.has_value());
  auto series = std::move(*series_or);
  ASSERT_EQ(series.timestamps().size(), 1U);
  EXPECT_EQ(series.timestamps()[0], 10);
  expectNullRows(f.toolbox, field, {true});
}

TEST(PluginDataHostWriteTest, ArrowStreamFloat64RoundTrip) {
  Fixture f;
  const auto source = *f.toolbox.createDataSource("sensor");

  DatastoreSourceWriteHost source_impl(f.engine, source);
  SourceWriteHostView writer(source_impl.raw());
  const auto topic = *writer.ensureTopic("data");

  // Build a struct schema: {_timestamp: INT64, value: DOUBLE}
  nanoarrow::UniqueSchema schema;
  ASSERT_EQ(ArrowSchemaInitFromType(schema.get(), NANOARROW_TYPE_STRUCT), NANOARROW_OK);
  ASSERT_EQ(ArrowSchemaAllocateChildren(schema.get(), 2), NANOARROW_OK);
  ArrowSchemaInit(schema->children[0]);
  ASSERT_EQ(ArrowSchemaSetName(schema->children[0], "_timestamp"), NANOARROW_OK);
  ASSERT_EQ(ArrowSchemaSetType(schema->children[0], NANOARROW_TYPE_INT64), NANOARROW_OK);
  ArrowSchemaInit(schema->children[1]);
  ASSERT_EQ(ArrowSchemaSetName(schema->children[1], "value"), NANOARROW_OK);
  ASSERT_EQ(ArrowSchemaSetType(schema->children[1], NANOARROW_TYPE_DOUBLE), NANOARROW_OK);

  // Append 3 rows: {100,1.5}, {200,2.5}, {300,3.5}
  nanoarrow::UniqueArray array;
  ASSERT_EQ(ArrowArrayInitFromSchema(array.get(), schema.get(), nullptr), NANOARROW_OK);
  ASSERT_EQ(ArrowArrayStartAppending(array.get()), NANOARROW_OK);
  const int64_t timestamps[] = {100, 200, 300};
  const double values[] = {1.5, 2.5, 3.5};
  for (int i = 0; i < 3; ++i) {
    ASSERT_EQ(ArrowArrayAppendInt(array->children[0], timestamps[i]), NANOARROW_OK);
    ASSERT_EQ(ArrowArrayAppendDouble(array->children[1], values[i]), NANOARROW_OK);
    ASSERT_EQ(ArrowArrayFinishElement(array.get()), NANOARROW_OK);
  }
  ASSERT_EQ(ArrowArrayFinishBuildingDefault(array.get(), nullptr), NANOARROW_OK);

  auto stream_or = makeStream(schema.get(), array.get());
  ASSERT_TRUE(stream_or.has_value());
  auto stream = std::move(*stream_or);
  ASSERT_TRUE(writer.appendArrowStream(topic, std::move(stream), "_timestamp").has_value());
  source_impl.flushPending();

  // Find the "value" field handle via catalog snapshot.
  auto snapshot_or = f.toolbox.catalogSnapshot();
  ASSERT_TRUE(snapshot_or.has_value());
  auto snapshot = std::move(*snapshot_or);
  FieldHandle value_field{};
  bool found = false;
  for (const auto& fi : snapshot.fields()) {
    if (toStringView(fi.name) == "value") {
      value_field = fi.handle;
      found = true;
      break;
    }
  }
  ASSERT_TRUE(found) << "Field 'value' not found in catalog";

  auto series_or = f.toolbox.readSeries(value_field);
  ASSERT_TRUE(series_or.has_value());
  auto series = std::move(*series_or);
  ASSERT_EQ(series.type(), PrimitiveType::kFloat64);
  ASSERT_EQ(series.timestamps().size(), 3U);
  for (int i = 0; i < 3; ++i) {
    EXPECT_EQ(series.timestamps()[static_cast<size_t>(i)], timestamps[i]);
    EXPECT_DOUBLE_EQ(series.valuesAsFloat64()[i], values[i]);
  }
}

TEST(PluginDataHostWriteTest, ArrowStreamCustomTimestampColumnName) {
  Fixture f;
  const auto source = *f.toolbox.createDataSource("sensor");

  DatastoreSourceWriteHost source_impl(f.engine, source);
  SourceWriteHostView writer(source_impl.raw());
  const auto topic = *writer.ensureTopic("custom_ts");

  // Build a struct schema: {ts: INT64, val: FLOAT}
  nanoarrow::UniqueSchema schema;
  ASSERT_EQ(ArrowSchemaInitFromType(schema.get(), NANOARROW_TYPE_STRUCT), NANOARROW_OK);
  ASSERT_EQ(ArrowSchemaAllocateChildren(schema.get(), 2), NANOARROW_OK);
  ArrowSchemaInit(schema->children[0]);
  ASSERT_EQ(ArrowSchemaSetName(schema->children[0], "ts"), NANOARROW_OK);
  ASSERT_EQ(ArrowSchemaSetType(schema->children[0], NANOARROW_TYPE_INT64), NANOARROW_OK);
  ArrowSchemaInit(schema->children[1]);
  ASSERT_EQ(ArrowSchemaSetName(schema->children[1], "val"), NANOARROW_OK);
  ASSERT_EQ(ArrowSchemaSetType(schema->children[1], NANOARROW_TYPE_FLOAT), NANOARROW_OK);

  // Append 2 rows.
  nanoarrow::UniqueArray array;
  ASSERT_EQ(ArrowArrayInitFromSchema(array.get(), schema.get(), nullptr), NANOARROW_OK);
  ASSERT_EQ(ArrowArrayStartAppending(array.get()), NANOARROW_OK);
  ASSERT_EQ(ArrowArrayAppendInt(array->children[0], 10), NANOARROW_OK);
  ASSERT_EQ(ArrowArrayAppendDouble(array->children[1], 1.0), NANOARROW_OK);
  ASSERT_EQ(ArrowArrayFinishElement(array.get()), NANOARROW_OK);
  ASSERT_EQ(ArrowArrayAppendInt(array->children[0], 20), NANOARROW_OK);
  ASSERT_EQ(ArrowArrayAppendDouble(array->children[1], 2.0), NANOARROW_OK);
  ASSERT_EQ(ArrowArrayFinishElement(array.get()), NANOARROW_OK);
  ASSERT_EQ(ArrowArrayFinishBuildingDefault(array.get(), nullptr), NANOARROW_OK);

  auto stream_or = makeStream(schema.get(), array.get());
  ASSERT_TRUE(stream_or.has_value());
  auto stream = std::move(*stream_or);
  ASSERT_TRUE(writer.appendArrowStream(topic, std::move(stream), "ts").has_value());
  source_impl.flushPending();

  // Find the "val" field handle via catalog snapshot.
  auto snapshot_or = f.toolbox.catalogSnapshot();
  ASSERT_TRUE(snapshot_or.has_value());
  auto snapshot = std::move(*snapshot_or);
  FieldHandle val_field{};
  bool found = false;
  for (const auto& fi : snapshot.fields()) {
    if (toStringView(fi.name) == "val") {
      val_field = fi.handle;
      found = true;
      break;
    }
  }
  ASSERT_TRUE(found) << "Field 'val' not found in catalog";

  auto series_or = f.toolbox.readSeries(val_field);
  ASSERT_TRUE(series_or.has_value());
  auto series = std::move(*series_or);
  ASSERT_EQ(series.type(), PrimitiveType::kFloat32);
  ASSERT_EQ(series.timestamps().size(), 2U);
  EXPECT_EQ(series.timestamps()[0], 10);
  EXPECT_EQ(series.timestamps()[1], 20);
  EXPECT_FLOAT_EQ(series.valuesAsFloat32()[0], 1.0F);
  EXPECT_FLOAT_EQ(series.valuesAsFloat32()[1], 2.0F);
}

TEST(PluginDataHostWriteTest, ArrowStreamRejectsExplicitMissingTimestampAndRetainsOwnership) {
  Fixture f;
  const auto source = *f.toolbox.createDataSource("sensor");

  DatastoreSourceWriteHost source_impl(f.engine, source);
  SourceWriteHostView writer(source_impl.raw());
  const auto topic = *writer.ensureTopic("no_ts");

  // Build a struct schema with only a data column (no "_timestamp").
  nanoarrow::UniqueSchema schema;
  ASSERT_EQ(ArrowSchemaInitFromType(schema.get(), NANOARROW_TYPE_STRUCT), NANOARROW_OK);
  ASSERT_EQ(ArrowSchemaAllocateChildren(schema.get(), 1), NANOARROW_OK);
  ArrowSchemaInit(schema->children[0]);
  ASSERT_EQ(ArrowSchemaSetName(schema->children[0], "data"), NANOARROW_OK);
  ASSERT_EQ(ArrowSchemaSetType(schema->children[0], NANOARROW_TYPE_INT32), NANOARROW_OK);

  nanoarrow::UniqueArray array;
  ASSERT_EQ(ArrowArrayInitFromSchema(array.get(), schema.get(), nullptr), NANOARROW_OK);
  ASSERT_EQ(ArrowArrayStartAppending(array.get()), NANOARROW_OK);
  ASSERT_EQ(ArrowArrayAppendInt(array->children[0], 42), NANOARROW_OK);
  ASSERT_EQ(ArrowArrayFinishElement(array.get()), NANOARROW_OK);
  ASSERT_EQ(ArrowArrayFinishBuildingDefault(array.get(), nullptr), NANOARROW_OK);

  auto stream_or = makeStream(schema.get(), array.get());
  ASSERT_TRUE(stream_or.has_value());
  auto stream = std::move(*stream_or);
  auto* owned_stream = stream.get();
  ASSERT_NE(owned_stream->release, nullptr);
  const auto status = writer.appendArrowStream(topic, owned_stream, "missing_ts");
  ASSERT_FALSE(status.has_value());
  EXPECT_NE(status.error().find("timestamp column 'missing_ts' not found"), std::string::npos);
  EXPECT_NE(owned_stream->release, nullptr);
  source_impl.flushPending();
  auto field_or = writer.ensureField(topic, "data", PrimitiveType::kInt32);
  ASSERT_TRUE(field_or.has_value());
  auto empty_or = f.toolbox.readSeries(*field_or);
  ASSERT_TRUE(empty_or.has_value());
  EXPECT_EQ(empty_or->rowCount(), 0U);

  // The SDK wrapper defaults to an explicit "timestamp" column selection.
  const auto default_status = writer.appendArrowStream(topic, owned_stream);
  ASSERT_FALSE(default_status.has_value());
  EXPECT_NE(default_status.error().find("timestamp column 'timestamp' not found"), std::string::npos);
  EXPECT_NE(owned_stream->release, nullptr);

  // With no selected timestamp column, this same retained stream uses synthetic time.
  ASSERT_TRUE(writer.appendArrowStream(topic, owned_stream, "").has_value());
  EXPECT_EQ(owned_stream->release, nullptr);
  source_impl.flushPending();
  auto series_or = f.toolbox.readSeries(*field_or);
  ASSERT_TRUE(series_or.has_value());
  ASSERT_EQ(series_or->rowCount(), 1U);
  EXPECT_EQ(series_or->timestamps()[0], 0);
  EXPECT_EQ(series_or->valuesAsInt32()[0], 42);
}

// ---------------------------------------------------------------------------
// Late column addition (schema evolution)
// ---------------------------------------------------------------------------

TEST(PluginDataHostWriteTest, LateColumnAddition) {
  Fixture f;
  const auto source = *f.toolbox.createDataSource("sensor");

  DatastoreSourceWriteHost source_impl(f.engine, source);
  SourceWriteHostView writer(source_impl.raw());
  const auto topic = *writer.ensureTopic("json");

  // Row 1: only field "x"
  const std::vector<NamedFieldValue> row1 = {{.name = "x", .value = 1.0}};
  ASSERT_TRUE(writer.appendRecord(topic, 10, row1).has_value());

  // Row 2: "x" plus new field "y" — triggers auto-seal of chunk 1
  const std::vector<NamedFieldValue> row2 = {
      {.name = "x", .value = 2.0},
      {.name = "y", .value = 3.0},
  };
  ASSERT_TRUE(writer.appendRecord(topic, 20, row2).has_value());
  source_impl.flushPending();

  // Find field handles via catalog
  auto snapshot_or = f.toolbox.catalogSnapshot();
  ASSERT_TRUE(snapshot_or.has_value());
  auto snapshot = std::move(*snapshot_or);
  FieldHandle x_field{}, y_field{};
  for (const auto& fi : snapshot.fields()) {
    auto name = std::string_view(fi.name.data, fi.name.size);
    if (name == "x") {
      x_field = fi.handle;
    }
    if (name == "y") {
      y_field = fi.handle;
    }
  }

  // x should have 2 rows across 2 chunks
  auto x_series_or = f.toolbox.readSeries(x_field);
  ASSERT_TRUE(x_series_or.has_value());
  auto x_series = std::move(*x_series_or);
  ASSERT_EQ(x_series.timestamps().size(), 2U);
  EXPECT_EQ(x_series.timestamps()[0], 10);
  EXPECT_EQ(x_series.timestamps()[1], 20);
  ASSERT_EQ(x_series.type(), PrimitiveType::kFloat64);
  EXPECT_DOUBLE_EQ(x_series.valuesAsFloat64()[0], 1.0);
  EXPECT_DOUBLE_EQ(x_series.valuesAsFloat64()[1], 2.0);

  // y should have 1 row (only in chunk 2)
  auto y_series_or = f.toolbox.readSeries(y_field);
  ASSERT_TRUE(y_series_or.has_value());
  auto y_series = std::move(*y_series_or);
  ASSERT_EQ(y_series.timestamps().size(), 1U);
  EXPECT_EQ(y_series.timestamps()[0], 20);
  ASSERT_EQ(y_series.type(), PrimitiveType::kFloat64);
  EXPECT_DOUBLE_EQ(y_series.valuesAsFloat64()[0], 3.0);
}

TEST(PluginDataHostWriteTest, UntypedNullForUnknownFieldIsSkipped) {
  Fixture f;
  const auto source = *f.toolbox.createDataSource("sensor");

  DatastoreSourceWriteHost source_impl(f.engine, source);
  SourceWriteHostView writer(source_impl.raw());
  const auto topic = *writer.ensureTopic("sparse");

  // Row 1: "x" is non-null, "y" is untyped null (kNull) and never seen → skipped
  const std::vector<NamedFieldValue> row = {
      {.name = "x", .value = 1.0},
      {.name = "y", .value = PJ::kNull},
  };
  ASSERT_TRUE(writer.appendRecord(topic, 10, row).has_value());
  source_impl.flushPending();

  // Only field "x" should exist
  auto snapshot_or = f.toolbox.catalogSnapshot();
  ASSERT_TRUE(snapshot_or.has_value());
  auto snapshot = std::move(*snapshot_or);
  int field_count = 0;
  for (const auto& fi : snapshot.fields()) {
    auto name = std::string_view(fi.name.data, fi.name.size);
    EXPECT_EQ(name, "x") << "unexpected field: " << name;
    ++field_count;
  }
  EXPECT_EQ(field_count, 1);
}

TEST(PluginDataHostWriteTest, TypedNullForUnknownFieldCreatesColumn) {
  Fixture f;
  const auto source = *f.toolbox.createDataSource("sensor");

  DatastoreSourceWriteHost source_impl(f.engine, source);
  SourceWriteHostView writer(source_impl.raw());
  const auto topic = *writer.ensureTopic("typed");

  // Row 1: "x" non-null, "y" is a typed null (type known but value absent)
  const std::vector<NamedFieldValue> row = {
      {.name = "x", .value = 1.0},
      {.name = "y", .value = TypedNull{PrimitiveType::kFloat64}},
  };
  ASSERT_TRUE(writer.appendRecord(topic, 10, row).has_value());
  source_impl.flushPending();

  // Both fields should exist
  auto snapshot_or = f.toolbox.catalogSnapshot();
  ASSERT_TRUE(snapshot_or.has_value());
  auto snapshot = std::move(*snapshot_or);
  FieldHandle x_field{}, y_field{};
  int field_count = 0;
  for (const auto& fi : snapshot.fields()) {
    auto name = std::string_view(fi.name.data, fi.name.size);
    if (name == "x") {
      x_field = fi.handle;
    }
    if (name == "y") {
      y_field = fi.handle;
    }
    ++field_count;
  }
  EXPECT_EQ(field_count, 2);

  // y should have 1 row with null value
  auto y_series_or = f.toolbox.readSeries(y_field);
  ASSERT_TRUE(y_series_or.has_value());
  auto y_series = std::move(*y_series_or);
  ASSERT_EQ(y_series.timestamps().size(), 1U);
  EXPECT_EQ(y_series.type(), PrimitiveType::kFloat64);
  EXPECT_EQ(y_series.timestamps()[0], 10);
  expectNullRows(f.toolbox, y_field, {true});
}

TEST(PluginDataHostWriteTest, VariableLengthArraySimulation) {
  Fixture f;
  const auto source = *f.toolbox.createDataSource("sensor");

  DatastoreSourceWriteHost source_impl(f.engine, source);
  SourceWriteHostView writer(source_impl.raw());
  const auto topic = *writer.ensureTopic("varlen");

  // Row 1: 2-element array
  const std::vector<NamedFieldValue> row1 = {
      {.name = "data[0]", .value = 10.0},
      {.name = "data[1]", .value = 20.0},
  };
  ASSERT_TRUE(writer.appendRecord(topic, 100, row1).has_value());

  // Row 2: 4-element array — data[2] and data[3] are new columns
  const std::vector<NamedFieldValue> row2 = {
      {.name = "data[0]", .value = 11.0},
      {.name = "data[1]", .value = 21.0},
      {.name = "data[2]", .value = 31.0},
      {.name = "data[3]", .value = 41.0},
  };
  ASSERT_TRUE(writer.appendRecord(topic, 200, row2).has_value());
  source_impl.flushPending();

  // Find field handles
  auto snapshot_or = f.toolbox.catalogSnapshot();
  ASSERT_TRUE(snapshot_or.has_value());
  auto snapshot = std::move(*snapshot_or);
  ASSERT_EQ(snapshot.fields().size(), 4U);
  FieldHandle d0{}, d1{}, d2{}, d3{};
  for (const auto& fi : snapshot.fields()) {
    auto name = std::string_view(fi.name.data, fi.name.size);
    if (name == "data[0]") {
      d0 = fi.handle;
    }
    if (name == "data[1]") {
      d1 = fi.handle;
    }
    if (name == "data[2]") {
      d2 = fi.handle;
    }
    if (name == "data[3]") {
      d3 = fi.handle;
    }
  }

  // data[0] should have 2 rows across 2 chunks
  auto s0_or = f.toolbox.readSeries(d0);
  ASSERT_TRUE(s0_or.has_value());
  auto s0 = std::move(*s0_or);
  ASSERT_EQ(s0.timestamps().size(), 2U);
  EXPECT_EQ(s0.timestamps()[0], 100);
  EXPECT_EQ(s0.timestamps()[1], 200);
  ASSERT_EQ(s0.type(), PrimitiveType::kFloat64);
  EXPECT_DOUBLE_EQ(s0.valuesAsFloat64()[0], 10.0);
  EXPECT_DOUBLE_EQ(s0.valuesAsFloat64()[1], 11.0);

  // data[2] should have 1 row (only in chunk 2)
  auto s2_or = f.toolbox.readSeries(d2);
  ASSERT_TRUE(s2_or.has_value());
  auto s2 = std::move(*s2_or);
  ASSERT_EQ(s2.timestamps().size(), 1U);
  EXPECT_EQ(s2.timestamps()[0], 200);
  ASSERT_EQ(s2.type(), PrimitiveType::kFloat64);
  EXPECT_DOUBLE_EQ(s2.valuesAsFloat64()[0], 31.0);

  auto s1_or = f.toolbox.readSeries(d1);
  ASSERT_TRUE(s1_or.has_value());
  ASSERT_EQ(s1_or->type(), PrimitiveType::kFloat64);
  ASSERT_EQ(s1_or->rowCount(), 2U);
  EXPECT_EQ(s1_or->timestamps()[0], 100);
  EXPECT_EQ(s1_or->timestamps()[1], 200);
  EXPECT_DOUBLE_EQ(s1_or->valuesAsFloat64()[0], 20.0);
  EXPECT_DOUBLE_EQ(s1_or->valuesAsFloat64()[1], 21.0);
  auto s3_or = f.toolbox.readSeries(d3);
  ASSERT_TRUE(s3_or.has_value());
  ASSERT_EQ(s3_or->type(), PrimitiveType::kFloat64);
  ASSERT_EQ(s3_or->rowCount(), 1U);
  EXPECT_EQ(s3_or->timestamps()[0], 200);
  EXPECT_DOUBLE_EQ(s3_or->valuesAsFloat64()[0], 41.0);
}

}  // namespace
}  // namespace PJ
