// SPDX-License-Identifier: MPL-2.0

#include <gtest/gtest.h>

#include <cmath>
#include <limits>
#include <string>
#include <utility>
#include <vector>

#include "pj_datastore/engine.hpp"
#include "pj_datastore/writer.hpp"

namespace PJ {
namespace {

/// Exercise both writer flush entry points with the same active-row inputs.
class WriterFlushTest : public ::testing::TestWithParam<bool> {
 protected:
  DataEngine engine_;
  DataWriter writer_{engine_};
  DatasetId dataset_ = *engine_.createDataset(DatasetDescriptor{.source_name = "flush"});
  uint32_t topic_count_ = 0;

  /// Create a schemaless topic with a controlled layout and capacity.
  TopicId topic(std::vector<PrimitiveType> types, uint32_t capacity = 1024) {
    auto id = *writer_.registerTopic(
        dataset_, TopicDescriptor{.name = std::to_string(++topic_count_), .max_chunk_rows = capacity});
    for (std::size_t col = 0; col < types.size(); ++col) {
      EXPECT_TRUE(writer_.ensureColumn(id, "c" + std::to_string(col), types[col]).has_value());
    }
    return id;
  }

  /// Normalize flushAll's topic-tagged output for these single-topic cases.
  std::vector<TopicChunk> flush(TopicId id) {
    if (!GetParam()) {
      return writer_.flush(id);
    }
    std::vector<TopicChunk> chunks;
    for (auto& [topic_id, chunk] : writer_.flushAll()) {
      EXPECT_EQ(topic_id, id);
      chunks.push_back(std::move(chunk));
    }
    return chunks;
  }
};

TEST_P(WriterFlushTest, IncompleteFirstRowSurvivesRepeatedFlush) {
  auto id = topic({PrimitiveType::kFloat64, PrimitiveType::kFloat64});
  ASSERT_TRUE(writer_.beginRow(id, -100).has_value());
  writer_.set(id, 0, 3.25);
  EXPECT_TRUE(flush(id).empty());
  EXPECT_TRUE(flush(id).empty());
  writer_.set(id, 1, 4.5);
  ASSERT_TRUE(writer_.finishRow(id).has_value());
  auto chunks = flush(id);
  ASSERT_EQ(chunks.size(), 1u);
  EXPECT_EQ(chunks[0].timestamps, (std::vector<Timestamp>{-100}));
  EXPECT_DOUBLE_EQ(chunks[0].readNumericAsDouble(0, 0), 3.25);
  EXPECT_DOUBLE_EQ(chunks[0].readNumericAsDouble(1, 0), 4.5);
  EXPECT_TRUE(flush(id).empty());
}

TEST_P(WriterFlushTest, PreservesEveryStorageKindNullAndUnsetColumn) {
  auto id = topic(
      {PrimitiveType::kFloat32, PrimitiveType::kFloat64, PrimitiveType::kInt32, PrimitiveType::kInt64,
       PrimitiveType::kUint64, PrimitiveType::kBool, PrimitiveType::kString, PrimitiveType::kFloat64,
       PrimitiveType::kFloat64});
  ASSERT_TRUE(writer_.beginRow(id, 100).has_value());
  writer_.set(id, 0, 1.25f);
  writer_.set(id, 1, 2.5);
  writer_.set(id, 2, int32_t{-3});
  writer_.set(id, 3, std::numeric_limits<int64_t>::min() + 13);
  writer_.set(id, 4, std::numeric_limits<uint64_t>::max() - 17);
  writer_.set(id, 5, true);
  writer_.set(id, 6, std::string_view{"complete"});
  writer_.set(id, 7, 7.0);
  writer_.set(id, 8, 8.0);
  ASSERT_TRUE(writer_.finishRow(id).has_value());

  ASSERT_TRUE(writer_.beginRow(id, -50).has_value());
  writer_.set(id, 0, -0.0f);
  writer_.set(id, 1, -9.75);
  writer_.set(id, 2, std::numeric_limits<int32_t>::min() + 5);
  writer_.set(id, 3, std::numeric_limits<int64_t>::max() - 13);
  writer_.set(id, 4, std::numeric_limits<uint64_t>::max() - 19);
  writer_.set(id, 5, false);
  const std::string expected(4096, 'x');
  std::string input = expected;
  writer_.set(id, 6, std::string_view{input});
  writer_.setNull(id, 7);
  auto chunks = flush(id);
  input.assign(input.size(), 'y');
  ASSERT_EQ(chunks.size(), 1u);
  const auto& complete = chunks[0];
  EXPECT_EQ(complete.stats.row_count, 1u);
  EXPECT_EQ(complete.timestamps, (std::vector<Timestamp>{100}));
  EXPECT_DOUBLE_EQ(complete.readNumericAsDouble(0, 0), 1.25);
  EXPECT_DOUBLE_EQ(complete.readNumericAsDouble(1, 0), 2.5);
  EXPECT_EQ(complete.readNumericAsInt64(2, 0), -3);
  EXPECT_EQ(complete.readNumericAsInt64(3, 0), std::numeric_limits<int64_t>::min() + 13);
  EXPECT_EQ(complete.readNumericAsUint64(4, 0), std::numeric_limits<uint64_t>::max() - 17);
  EXPECT_TRUE(complete.readBool(5, 0));
  EXPECT_EQ(complete.readString(6, 0), "complete");
  EXPECT_FALSE(complete.isNull(7, 0));
  EXPECT_EQ(complete.stats.column_stats[7].null_count, 0u);
  ASSERT_TRUE(complete.stats.column_stats[1].min_value.has_value());
  EXPECT_DOUBLE_EQ(*complete.stats.column_stats[1].min_value, 2.5);
  EXPECT_EQ(std::get<encoding::DictionaryEncoded>(complete.columns[6].data).count, 1u);
  EXPECT_TRUE(flush(id).empty());

  // New columns remain forbidden mid-row, but unset existing columns stay writable.
  EXPECT_FALSE(writer_.ensureColumn(id, "new", PrimitiveType::kFloat64).has_value());
  writer_.set(id, 8, 42.0);
  ASSERT_TRUE(writer_.finishRow(id).has_value());
  auto pending = flush(id);
  ASSERT_EQ(pending.size(), 1u);
  EXPECT_EQ(pending[0].timestamps, (std::vector<Timestamp>{-50}));
  EXPECT_EQ(pending[0].stats.row_count, 1u);
  EXPECT_TRUE(std::signbit(pending[0].readNumericAsDouble(0, 0)));
  EXPECT_DOUBLE_EQ(pending[0].readNumericAsDouble(1, 0), -9.75);
  EXPECT_EQ(pending[0].readNumericAsInt64(2, 0), std::numeric_limits<int32_t>::min() + 5);
  EXPECT_EQ(pending[0].readNumericAsInt64(3, 0), std::numeric_limits<int64_t>::max() - 13);
  EXPECT_EQ(pending[0].readNumericAsUint64(4, 0), std::numeric_limits<uint64_t>::max() - 19);
  EXPECT_FALSE(pending[0].readBool(5, 0));
  EXPECT_EQ(pending[0].readString(6, 0), expected);
  EXPECT_TRUE(pending[0].isNull(7, 0));
  EXPECT_EQ(pending[0].stats.column_stats[7].null_count, 1u);
  EXPECT_DOUBLE_EQ(pending[0].readNumericAsDouble(8, 0), 42.0);
  EXPECT_GT(pending[0].id, complete.id);
  ASSERT_EQ(pending[0].columns.size(), complete.columns.size());
  for (std::size_t col = 0; col < complete.columns.size(); ++col) {
    EXPECT_EQ(pending[0].columns[col].descriptor->field_id, complete.columns[col].descriptor->field_id);
    EXPECT_EQ(pending[0].columns[col].descriptor->logical_type, complete.columns[col].descriptor->logical_type);
  }
}

TEST_P(WriterFlushTest, ReturnsAutoSealedChunksAndCompletedPrefixWithoutDuplicates) {
  auto id = topic({PrimitiveType::kFloat64}, 2);
  for (int row = 1; row <= 3; ++row) {
    ASSERT_TRUE(writer_.beginRow(id, row * 100).has_value());
    writer_.set(id, 0, static_cast<double>(row));
    ASSERT_TRUE(writer_.finishRow(id).has_value());
  }
  ASSERT_TRUE(writer_.beginRow(id, 400).has_value());
  auto chunks = flush(id);
  ASSERT_EQ(chunks.size(), 2u);
  EXPECT_EQ(chunks[0].timestamps, (std::vector<Timestamp>{100, 200}));
  EXPECT_EQ(chunks[1].timestamps, (std::vector<Timestamp>{300}));
  EXPECT_TRUE(flush(id).empty());
  writer_.set(id, 0, 4.0);
  ASSERT_TRUE(writer_.finishRow(id).has_value());
  ASSERT_TRUE(writer_.beginRow(id, 500).has_value());
  writer_.set(id, 0, 5.0);
  ASSERT_TRUE(writer_.finishRow(id).has_value());
  // The retained builder still respects the original auto-seal capacity.
  ASSERT_TRUE(writer_.beginRow(id, 600).has_value());
  auto tail = flush(id);
  ASSERT_EQ(tail.size(), 1u);
  EXPECT_EQ(tail[0].timestamps, (std::vector<Timestamp>{400, 500}));
  ASSERT_TRUE(writer_.finishRow(id).has_value());
  auto last = flush(id);
  ASSERT_EQ(last.size(), 1u);
  EXPECT_EQ(last[0].timestamps, (std::vector<Timestamp>{600}));
  EXPECT_TRUE(last[0].isNull(0, 0));
}

TEST_P(WriterFlushTest, CompletedBulkRowsRemainStablySortedAndNullAligned) {
  auto id = topic({PrimitiveType::kFloat64, PrimitiveType::kFloat64});
  const std::vector<Timestamp> stamps{300, 100, 100};
  const std::vector<double> values{3.5, 1.5, 2.5};
  const std::vector<ColumnData> columns{ColumnData::float64(0, values)};
  ASSERT_TRUE(writer_.appendColumns(id, stamps, columns).has_value());
  ASSERT_TRUE(writer_.beginRow(id, -1).has_value());
  writer_.set(id, 0, -99.5);
  auto chunks = flush(id);
  ASSERT_EQ(chunks.size(), 1u);
  EXPECT_EQ(chunks[0].timestamps, (std::vector<Timestamp>{100, 100, 300}));
  EXPECT_EQ(chunks[0].stats.t_min, 100);
  EXPECT_EQ(chunks[0].stats.t_max, 300);
  EXPECT_DOUBLE_EQ(chunks[0].readNumericAsDouble(0, 0), 1.5);
  EXPECT_DOUBLE_EQ(chunks[0].readNumericAsDouble(0, 1), 2.5);
  EXPECT_DOUBLE_EQ(chunks[0].readNumericAsDouble(0, 2), 3.5);
  EXPECT_EQ(chunks[0].stats.column_stats[1].null_count, 3u);
  for (std::size_t row = 0; row < 3; ++row) {
    EXPECT_TRUE(chunks[0].isNull(1, row));
  }
  ASSERT_TRUE(writer_.finishRow(id).has_value());
  auto pending = flush(id);
  ASSERT_EQ(pending.size(), 1u);
  EXPECT_EQ(pending[0].timestamps, (std::vector<Timestamp>{-1}));
  EXPECT_DOUBLE_EQ(pending[0].readNumericAsDouble(0, 0), -99.5);
  EXPECT_TRUE(pending[0].isNull(1, 0));
}

/// Build a completed bulk string prefix, optionally retaining an active row.
TopicChunk stringPrefix(bool all, bool leading_empty, int active) {
  DataEngine engine;
  DataWriter writer{engine};
  const auto dataset = *engine.createDataset(DatasetDescriptor{.source_name = "string-prefix"});
  const auto id = *writer.registerTopic(dataset, TopicDescriptor{.name = "t"});
  EXPECT_TRUE(writer.ensureColumn(id, "s", PrimitiveType::kString).has_value());
  const std::vector<Timestamp> stamps = leading_empty ? std::vector<Timestamp>{1, 2} : std::vector<Timestamp>{1, 2, 3};
  const std::vector<uint32_t> offsets =
      leading_empty ? std::vector<uint32_t>{0, 0, 0} : std::vector<uint32_t>{0, 1, 1, 2};
  const std::string bytes = leading_empty ? "" : "xx";
  const std::vector<uint8_t> bits{static_cast<uint8_t>(leading_empty ? 2 : 5)};
  const std::vector<ColumnData> columns{
      ColumnData::string(0, offsets, Span<const char>(bytes.data(), bytes.size()), BitSpan{bits, 0, stamps.size()})};
  EXPECT_TRUE(writer.appendColumns(id, stamps, columns).has_value());
  if (active) {
    EXPECT_TRUE(writer.beginRow(id, 4).has_value());
    if (active == 2) {
      writer.set(id, 0, std::string_view{"pending"});
    } else if (active == 3) {
      writer.setNull(id, 0);
    }
  }
  std::vector<TopicChunk> chunks;
  if (all) {
    for (auto& [topic_id, chunk] : writer.flushAll()) {
      EXPECT_EQ(topic_id, id);
      chunks.push_back(std::move(chunk));
    }
  } else {
    chunks = writer.flush(id);
  }
  EXPECT_EQ(chunks.size(), 1u);
  if (active) {
    EXPECT_TRUE(writer.finishRow(id).has_value());
    auto tail = writer.flush(id);
    EXPECT_EQ(tail.size(), 1u);
    EXPECT_EQ(tail[0].isNull(0, 0), active != 2);
    if (active == 2) {
      EXPECT_EQ(tail[0].readString(0, 0), "pending");
    }
  }
  return std::move(chunks[0]);
}

TEST_P(WriterFlushTest, StringNullGapsPreserveCompletedBulkStats) {
  const auto control = stringPrefix(GetParam(), false, 0);
  ASSERT_TRUE(control.stats.column_stats[0].is_constant);
  ASSERT_EQ(control.stats.column_stats[0].run_count, 1u);
  for (int active : {1, 2, 3}) {
    SCOPED_TRACE(active);
    const auto actual = stringPrefix(GetParam(), false, active);
    EXPECT_EQ(actual.stats.column_stats[0].is_constant, control.stats.column_stats[0].is_constant);
    EXPECT_EQ(actual.stats.column_stats[0].run_count, control.stats.column_stats[0].run_count);
    EXPECT_EQ(actual.stats.column_stats[0].null_count, 1u);
    EXPECT_EQ(actual.readString(0, 0), "x");
    EXPECT_TRUE(actual.isNull(0, 1));
    EXPECT_EQ(actual.readString(0, 2), "x");
  }
}

TEST_P(WriterFlushTest, LeadingNullThenEmptyStringPreservesCompletedBulkStats) {
  const auto control = stringPrefix(GetParam(), true, 0);
  ASSERT_EQ(control.stats.column_stats[0].run_count, 1u);
  for (int active : {1, 2, 3}) {
    SCOPED_TRACE(active);
    const auto actual = stringPrefix(GetParam(), true, active);
    EXPECT_EQ(actual.stats.column_stats[0].run_count, control.stats.column_stats[0].run_count);
    EXPECT_TRUE(actual.stats.column_stats[0].is_constant);
    EXPECT_EQ(actual.stats.column_stats[0].null_count, 1u);
    EXPECT_TRUE(actual.isNull(0, 0));
    EXPECT_FALSE(actual.isNull(0, 1));
    EXPECT_EQ(actual.readString(0, 1), "");
  }
}

TEST_P(WriterFlushTest, LeadingNanPreservesCompletedBulkExtrema) {
  std::vector<TopicChunk> results;
  for (int active : {0, 1, 2, 3}) {
    DataEngine engine;
    DataWriter writer{engine};
    const auto dataset = *engine.createDataset(DatasetDescriptor{.source_name = "nan-prefix"});
    const auto id = *writer.registerTopic(dataset, TopicDescriptor{.name = "t"});
    ASSERT_TRUE(writer.ensureColumn(id, "f", PrimitiveType::kFloat64).has_value());
    const std::vector<Timestamp> stamps{1, 2};
    const std::vector<double> values{std::numeric_limits<double>::quiet_NaN(), 12.5};
    const std::vector<ColumnData> columns{ColumnData::float64(0, values)};
    ASSERT_TRUE(writer.appendColumns(id, stamps, columns).has_value());
    if (active) {
      ASSERT_TRUE(writer.beginRow(id, 3).has_value());
      if (active == 2) {
        writer.set(id, 0, -99.0);
      } else if (active == 3) {
        writer.setNull(id, 0);
      }
    }
    if (GetParam()) {
      auto chunks = writer.flushAll();
      ASSERT_EQ(chunks.size(), 1u);
      results.push_back(std::move(chunks[0].second));
    } else {
      auto chunks = writer.flush(id);
      ASSERT_EQ(chunks.size(), 1u);
      results.push_back(std::move(chunks[0]));
    }
    if (active) {
      ASSERT_TRUE(writer.finishRow(id).has_value());
    }
  }
  ASSERT_EQ(*results[0].stats.column_stats[0].min_value, 12.5);
  ASSERT_EQ(*results[0].stats.column_stats[0].max_value, 12.5);
  for (const auto& chunk : results) {
    const auto& stats = chunk.stats.column_stats[0];
    EXPECT_EQ(stats.min_value, results[0].stats.column_stats[0].min_value);
    EXPECT_EQ(stats.max_value, results[0].stats.column_stats[0].max_value);
    EXPECT_FALSE(stats.is_constant);
    EXPECT_EQ(stats.run_count, 2u);
    EXPECT_FALSE(stats.all_integral);
    EXPECT_TRUE(std::isnan(chunk.readNumericAsDouble(0, 0)));
    EXPECT_DOUBLE_EQ(chunk.readNumericAsDouble(0, 1), 12.5);
  }
}

TEST_P(WriterFlushTest, NonfiniteAndSignedZeroStatsExcludeTheActiveRowAcrossIngestPaths) {
  const double inf = std::numeric_limits<double>::infinity();
  const double nan = std::numeric_limits<double>::quiet_NaN();
  const std::vector<std::vector<double>> prefixes{{inf, inf}, {-inf, -inf}, {nan, 12.5}, {nan},
                                                  {nan, nan}, {-0.0, +0.0}, {5.0, 5.0}};
  for (int mode : {0, 1, 2}) {  // row, bulk, row then bulk
    for (const auto& prefix : prefixes) {
      for (bool active_null : {false, true}) {
        SCOPED_TRACE(::testing::Message() << mode << ":" << prefix[0] << ":" << active_null);
        const auto id = topic({PrimitiveType::kFloat64});
        for (std::size_t row = 0; row < prefix.size(); ++row) {
          if (mode == 1 || (mode == 2 && row > 0)) {
            const std::vector<Timestamp> stamps{static_cast<Timestamp>(row)};
            const std::vector<double> values{prefix[row]};
            const std::vector<ColumnData> columns{ColumnData::float64(0, values)};
            ASSERT_TRUE(writer_.appendColumns(id, stamps, columns).has_value());
          } else {
            ASSERT_TRUE(writer_.beginRow(id, static_cast<Timestamp>(row)).has_value());
            writer_.set(id, 0, prefix[row]);
            ASSERT_TRUE(writer_.finishRow(id).has_value());
          }
        }
        ASSERT_TRUE(writer_.beginRow(id, 100).has_value());
        if (active_null) {
          writer_.setNull(id, 0);
        } else {
          writer_.set(id, 0, -99.0);
        }
        auto chunks = flush(id);
        ASSERT_EQ(chunks.size(), 1u);
        const auto& stats = chunks[0].stats.column_stats[0];
        EXPECT_EQ(stats.null_count, 0u);
        if (std::isnan(prefix.back())) {
          EXPECT_FALSE(stats.min_value);
          EXPECT_FALSE(stats.max_value);
        } else {
          ASSERT_TRUE(stats.min_value);
          ASSERT_TRUE(stats.max_value);
          EXPECT_EQ(*stats.min_value, prefix.back());
          EXPECT_EQ(*stats.max_value, prefix.back());
        }
        const bool nan_run = std::isnan(prefix[0]) && prefix.size() > 1;
        EXPECT_EQ(stats.run_count, nan_run ? 2u : 1u);
        EXPECT_EQ(stats.is_constant, !nan_run);
        EXPECT_EQ(stats.all_integral, std::isfinite(prefix[0]) && std::floor(prefix[0]) == prefix[0]);
        for (std::size_t row = 0; row < prefix.size(); ++row) {
          const double actual = chunks[0].readNumericAsDouble(0, row);
          EXPECT_FALSE(chunks[0].isNull(0, row));
          if (std::isnan(prefix[row])) {
            EXPECT_TRUE(std::isnan(actual));
          } else {
            EXPECT_EQ(actual, prefix[row]);
            EXPECT_EQ(std::signbit(actual), std::signbit(prefix[row]));
          }
        }
        ASSERT_TRUE(writer_.finishRow(id).has_value());
        auto tail = flush(id);
        ASSERT_EQ(tail.size(), 1u);
        EXPECT_EQ(tail[0].isNull(0, 0), active_null);
        if (!active_null) {
          EXPECT_DOUBLE_EQ(tail[0].readNumericAsDouble(0, 0), -99.0);
        }
      }
    }
  }
}

INSTANTIATE_TEST_SUITE_P(PerTopicAndAll, WriterFlushTest, ::testing::Bool());

TEST(WriterFlushAllTest, KeepsIndependentTopicsAndActiveRows) {
  DataEngine engine;
  DataWriter writer{engine};
  auto dataset = *engine.createDataset(DatasetDescriptor{.source_name = "flush-all"});
  std::vector<TopicId> topics;
  for (int index = 0; index < 3; ++index) {
    const auto id = *writer.registerTopic(dataset, TopicDescriptor{.name = std::to_string(index)});
    ASSERT_TRUE(writer.ensureColumn(id, "value", PrimitiveType::kFloat64).has_value());
    topics.push_back(id);
    ASSERT_TRUE(writer.beginRow(id, index).has_value());
    writer.set(id, 0, static_cast<double>(index));
    if (index < 2) {
      ASSERT_TRUE(writer.finishRow(id).has_value());
    }
  }
  ASSERT_TRUE(writer.beginRow(topics[0], 10).has_value());
  writer.set(topics[0], 0, 10.0);
  auto first = writer.flush(topics[0]);
  ASSERT_EQ(first.size(), 1u);
  EXPECT_EQ(first[0].timestamps, (std::vector<Timestamp>{0}));
  auto others = writer.flushAll();
  ASSERT_EQ(others.size(), 1u);
  EXPECT_EQ(others[0].first, topics[1]);
  EXPECT_EQ(others[0].second.timestamps, (std::vector<Timestamp>{1}));
  EXPECT_TRUE(writer.flushAll().empty());
  ASSERT_TRUE(writer.finishRow(topics[0]).has_value());
  ASSERT_TRUE(writer.finishRow(topics[2]).has_value());
  auto final = writer.flushAll();
  ASSERT_EQ(final.size(), 2u);
  for (const auto& [id, chunk] : final) {
    ASSERT_TRUE(id == topics[0] || id == topics[2]);
    const Timestamp expected = id == topics[0] ? 10 : 2;
    EXPECT_EQ(chunk.timestamps, (std::vector<Timestamp>{expected}));
    EXPECT_DOUBLE_EQ(chunk.readNumericAsDouble(0, 0), static_cast<double>(expected));
  }
  EXPECT_TRUE(writer.flushAll().empty());
}

}  // namespace
}  // namespace PJ
