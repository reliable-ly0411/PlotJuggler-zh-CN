// Copyright 2026 Davide Faconti
// SPDX-License-Identifier: MPL-2.0

// Regression coverage for completed-row flushes, bulk-column row counts,
// and out-of-order chunks and queries. Build from the repo root (./build.sh), then:
//   ctest --test-dir build -R 'pj_datastore_tests\.RegressionTest\.'
// The excess-column assertion requires Debug or PJ_ASSERT_THROWS; that case
// explicitly skips when NDEBUG disables assertions.

#include <gtest/gtest.h>

#include <utility>
#include <vector>

#include "pj_base/type_tree.hpp"
#include "pj_datastore/chunk.hpp"
#include "pj_datastore/engine.hpp"
#include "pj_datastore/query.hpp"
#include "pj_datastore/topic_storage.hpp"
#include "pj_datastore/writer.hpp"

namespace PJ {
namespace {

// ---------------------------------------------------------------------------
// Helper: build and seal a test chunk with given time range.
// Reuses the same pattern as topic_storage_test.cpp::make_test_chunk.
// ---------------------------------------------------------------------------

TopicChunk makeChunkWithRange(TopicId tid, Timestamp t_start, Timestamp t_end, uint32_t num_rows) {
  std::vector<ColumnDescriptor> cols = {{0, PrimitiveType::kFloat32, "v"}};
  TopicChunkBuilder b(tid, /*schema_id=*/1, cols, num_rows);
  Timestamp step = (num_rows > 1) ? (t_end - t_start) / static_cast<Timestamp>(num_rows - 1) : 0;
  for (uint32_t i = 0; i < num_rows; ++i) {
    b.beginRow(t_start + static_cast<Timestamp>(i) * step);
    b.set(0, static_cast<float>(i));
    b.finishRow();
  }
  return b.seal();
}

// ===========================================================================
// Bug #1 — flush() with an in-progress row corrupts chunk stats
//
// Only finished rows belong in a flushed chunk; the active row must remain
// writable without leaking its values or statistics into the completed rows.
// ===========================================================================

TEST(RegressionTest, Bug1_FlushWithRowInProgress_CorruptsChunkStats) {
  DataEngine engine;
  auto ds = *engine.createDataset(DatasetDescriptor{.source_name = "test", .time_domain_id = 0});
  DataWriter writer = engine.createWriter();

  auto schema = makePrimitive("v", PrimitiveType::kFloat64);
  auto sid = *writer.registerSchema("s", schema);
  auto tid = *writer.registerTopic(ds, TopicDescriptor{.name = "t", .schema_id = sid});

  // Commit one complete row at t=100.
  ASSERT_TRUE(writer.beginRow(tid, 100).has_value());
  writer.set(tid, 0, 1.0);
  ASSERT_TRUE(writer.finishRow(tid).has_value());

  // Start a second row at t=200 but do NOT call finishRow().
  ASSERT_TRUE(writer.beginRow(tid, 200).has_value());
  writer.set(tid, 0, 2.0);

  // flush() should only seal the one committed row.
  auto chunks = writer.flush(tid);

  ASSERT_EQ(chunks.size(), 1u);
  EXPECT_EQ(chunks[0].stats.row_count, 1u);
  EXPECT_EQ(chunks[0].stats.t_max, 100);
  EXPECT_EQ(chunks[0].timestamps.size(), 1u);
  EXPECT_DOUBLE_EQ(chunks[0].readNumericAsDouble(0, 0), 1.0);
  ASSERT_TRUE(chunks[0].stats.column_stats[0].max_value.has_value());
  EXPECT_DOUBLE_EQ(*chunks[0].stats.column_stats[0].max_value, 1.0);
  EXPECT_TRUE(chunks[0].stats.column_stats[0].is_constant);
  EXPECT_TRUE(writer.flush(tid).empty());

  ASSERT_TRUE(writer.finishRow(tid).has_value());
  auto remaining = writer.flush(tid);
  ASSERT_EQ(remaining.size(), 1u);
  EXPECT_EQ(remaining[0].timestamps, (std::vector<Timestamp>{200}));
  EXPECT_DOUBLE_EQ(remaining[0].readNumericAsDouble(0, 0), 2.0);
  EXPECT_EQ(remaining[0].stats.row_count, 1u);
  EXPECT_GT(remaining[0].id, chunks[0].id);
}

// Bulk batches pad missing values with nulls, but reject excess column rows.
TEST(RegressionTest, ShortBulkColumnIsPaddedWithoutLosingValues) {
  std::vector<ColumnDescriptor> cols = {{1, PrimitiveType::kFloat32, "x"}};
  const std::vector<Timestamp> ts = {100, 200, 300};
  const std::vector<float> vals = {1.0F, 2.0F};
  TopicChunkBuilder builder(/*topic_id=*/1, /*schema_id=*/1, cols, /*max_rows=*/100);
  builder.appendTimestamps(ts);
  builder.appendColumn<float>(0, vals);
  builder.finishBulkAppend();
  const TopicChunk chunk = builder.seal();
  ASSERT_EQ(chunk.stats.row_count, 3U);
  for (std::size_t i = 0; i < ts.size(); ++i) {
    EXPECT_EQ(chunk.readTimestamp(i), ts[i]);
  }
  EXPECT_FALSE(chunk.isNull(0, 0));
  EXPECT_FALSE(chunk.isNull(0, 1));
  EXPECT_DOUBLE_EQ(chunk.readNumericAsDouble(0, 0), 1.0);
  EXPECT_DOUBLE_EQ(chunk.readNumericAsDouble(0, 1), 2.0);
  EXPECT_TRUE(chunk.isNull(0, 2));
}

TEST(RegressionTest, ExcessBulkColumnRowsTriggerAssertion) {
  std::vector<ColumnDescriptor> cols = {{1, PrimitiveType::kFloat32, "x"}};
  const std::vector<Timestamp> ts = {100, 200};
  const std::vector<float> vals = {1.0F, 2.0F, 3.0F};
  const auto append_excess = [&] {
    TopicChunkBuilder builder(/*topic_id=*/1, /*schema_id=*/1, cols, /*max_rows=*/100);
    builder.appendTimestamps(ts);
    builder.appendColumn<float>(0, vals);
    builder.finishBulkAppend();
  };
#ifdef PJ_ASSERT_THROWS
  EXPECT_THROW(append_excess(), std::runtime_error);
#elif !defined(NDEBUG)
  EXPECT_DEATH(append_excess(), "finishBulkAppend: column has more rows than the batch");
#else
  GTEST_SKIP() << "Excess-row assertion requires Debug or PJ_ASSERT_THROWS";
#endif
}

// ===========================================================================
// Bug #3 (recontracted) — out-of-order chunks are retained and reported
//
// Historically appendSealedChunk rejected out-of-order chunks and commitChunks
// still reported the topic as changed (spurious derived recomputes on dropped
// data). Under lossless out-of-order ingest the chunk is retained, so the
// topic IS changed and must be reported.
// ===========================================================================

TEST(RegressionTest, Bug3_CommitChunks_OutOfOrderChunkRetainedAndReported) {
  DataEngine engine;
  auto ds = *engine.createDataset(DatasetDescriptor{.source_name = "test", .time_domain_id = 0});
  DataWriter writer = engine.createWriter();

  auto schema = makePrimitive("v", PrimitiveType::kFloat32);
  auto sid = *writer.registerSchema("s", schema);
  auto tid = *writer.registerTopic(ds, TopicDescriptor{.name = "t", .schema_id = sid});

  // First commit: chunk at t=[100, 200]. Accepted.
  std::vector<std::pair<TopicId, TopicChunk>> batch1;
  batch1.emplace_back(tid, makeChunkWithRange(tid, 100, 200, 2));
  auto changed1 = engine.commitChunks(std::move(batch1));
  ASSERT_EQ(changed1.size(), 1u);

  // Second commit: chunk at t=[50, 150] — out of order. Retained and reported.
  std::vector<std::pair<TopicId, TopicChunk>> batch2;
  batch2.emplace_back(tid, makeChunkWithRange(tid, 50, 150, 2));
  std::vector<TopicId> changed2;
  ASSERT_NO_THROW(changed2 = engine.commitChunks(std::move(batch2)));
  EXPECT_EQ(changed2, (std::vector<TopicId>{tid}));

  const TopicStorage* storage = engine.getTopicStorage(tid);
  ASSERT_NE(storage, nullptr);
  EXPECT_EQ(storage->sealedChunks().size(), 2u);
  EXPECT_EQ(storage->timeMin(), 50);
  EXPECT_EQ(storage->timeMax(), 200);
}

// ===========================================================================
// Bug #4 (recontracted) — queries stay correct over overlapping chunks
//
// Chunk ranges may overlap after out-of-order ingest. latestAt() and
// RangeCursor no longer assume disjoint, time-ordered chunks: latestAt scans
// candidate chunks (later-committed wins timestamp ties) and the row cursor
// merges chunks into one globally time-ordered stream.
// ===========================================================================

TEST(RegressionTest, Bug4_QueriesStayCorrectOverOverlappingChunks) {
  TopicDescriptor desc;
  desc.name = "t";
  desc.schema_id = 1;
  desc.dataset_id = 1;
  TopicStorage storage(/*topic_id=*/1, std::move(desc));

  // Chunk1: rows at 100,200,300,400,500. Chunk2: rows at 400,500,600 —
  // overlapping [400, 500].
  ASSERT_TRUE(storage.appendSealedChunk(makeChunkWithRange(1, 100, 500, 5)).has_value());
  ASSERT_TRUE(storage.appendSealedChunk(makeChunkWithRange(1, 400, 600, 3)).has_value());

  // Row cursor: one ascending stream across both chunks, duplicates included.
  std::vector<Timestamp> timestamps;
  rangeQuery(storage.sealedChunks(), 0, 1000).forEach([&timestamps](const SampleRow& row) {
    timestamps.push_back(row.timestamp);
  });
  EXPECT_EQ(timestamps, (std::vector<Timestamp>{100, 200, 300, 400, 400, 500, 500, 600}));

  // latestAt inside the overlap: both chunks hold a row at t=400; the
  // later-committed chunk wins the tie (commit order).
  const auto at_450 = latestAt(storage.sealedChunks(), 450);
  ASSERT_TRUE(at_450.has_value());
  EXPECT_EQ(at_450->timestamp, 400);
  EXPECT_EQ(at_450->chunk, &storage.sealedChunks()[1]);

  // latestAt past everything returns the global maximum.
  const auto at_end = latestAt(storage.sealedChunks(), 1000);
  ASSERT_TRUE(at_end.has_value());
  EXPECT_EQ(at_end->timestamp, 600);
}

}  // namespace
}  // namespace PJ
