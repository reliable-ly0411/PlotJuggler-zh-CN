// SPDX-License-Identifier: MPL-2.0
#include "../src/parsed_widget_data.hpp"

#include <gtest/gtest.h>

TEST(ParsedWidgetData, RejectsMalformedIncludingSdkEmptyObjectFallback) {
  for (const auto* raw : {"", "{", "null trailing", "{\"a\":NaN}", "{\"a\":1e999}", "{\"a\":2,}"}) {
    EXPECT_FALSE(PJ::detail::parseWidgetDataView(raw)) << raw;
  }
}

TEST(ParsedWidgetData, PreservesValidEmptyAndNonObjectPayloads) {
  for (const auto* raw : {"{}", " { } ", "[]", "null", "false", "0", "\"value\""}) {
    const auto view = PJ::detail::parseWidgetDataView(raw);
    ASSERT_TRUE(view) << raw;
    EXPECT_EQ(view->raw(), nlohmann::json::parse(raw));
  }
}

TEST(ParsedWidgetData, DiffCopyDoesNotConsumeCommandsOrMutateTypedView) {
  const auto view = PJ::detail::parseWidgetDataView(
      R"({"__request_close":"done","name":{"text":"\u6d4b\u8bd5"},"spin":{"value":1.25}})");
  ASSERT_TRUE(view);
  auto diff_data = view->raw();
  diff_data.erase("__request_close");
  diff_data["name"]["text"] = "changed";
  EXPECT_EQ(view->requestClose(), "done");
  EXPECT_EQ(view->text("name"), "\xe6\xb5\x8b\xe8\xaf\x95");
  EXPECT_EQ(view->valueDouble("spin"), 1.25);
}

TEST(ParsedWidgetData, PreservesEveryPreviewSampleAndIntegerRange) {
  nlohmann::json payload = {{"range", {0, -1, INT64_MIN, INT64_MAX, UINT64_MAX}}};
  auto& points = payload["preview"]["points"];
  for (int i = 0; i < 2000; ++i) {
    points.push_back({i * 0.001, i * i + 0.125});
  }
  const auto raw = payload.dump();
  const auto view = PJ::detail::parseWidgetDataView(raw);
  ASSERT_TRUE(view);
  EXPECT_EQ(view->raw(), nlohmann::json::parse(raw));
  EXPECT_EQ(view->raw()["preview"]["points"].size(), 2000U);
  EXPECT_EQ(view->raw()["range"][4].get<uint64_t>(), UINT64_MAX);
}
