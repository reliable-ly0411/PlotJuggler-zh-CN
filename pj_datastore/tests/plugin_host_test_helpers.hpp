// SPDX-License-Identifier: MPL-2.0
#pragma once

#include <gtest/gtest.h>

#include <cstddef>
#include <cstdint>
#include <initializer_list>
#include <string>
#include <string_view>

#include "nanoarrow/nanoarrow.h"
#include "nanoarrow/nanoarrow.hpp"
#include "pj_base/sdk/plugin_data_api.hpp"

namespace PJ::test {

/// Owns the exported Arrow buffers so validity, packed bools, and strings remain readable.
class ArrowSeries {
 public:
  /// Replace any previous read, releasing the view before the buffers it references.
  Status read(const sdk::ToolboxHostView& toolbox, sdk::FieldHandle field) {
    view_.reset();
    array_.reset();
    schema_.reset();
    auto status = toolbox.readSeriesArrow(field, schema_.get(), array_.get());
    if (!status) {
      return status;
    }
    ArrowError error{};
    if (ArrowArrayViewInitFromSchema(view_.get(), schema_.get(), &error) != NANOARROW_OK ||
        ArrowArrayViewSetArray(view_.get(), array_.get(), &error) != NANOARROW_OK) {
      return unexpected(std::string(error.message));
    }
    if (view_->n_children != 2) {
      return unexpected("Expected timestamp and value columns");
    }
    return {};
  }

  [[nodiscard]] ArrowArrayView* values() const {
    return view_->children[1];
  }
  [[nodiscard]] std::string_view format() const {
    return schema_->children[1]->format;
  }

  /// Returned text aliases this instance's Arrow array; callers must check nulls first.
  [[nodiscard]] std::string_view stringAt(int64_t row) const {
    const auto value = ArrowArrayViewGetStringUnsafe(values(), row);
    return {value.data, static_cast<std::size_t>(value.size_bytes)};
  }

 private:
  nanoarrow::UniqueSchema schema_;
  nanoarrow::UniqueArray array_;
  nanoarrow::UniqueArrayView view_;
};

/// Check validity without assuming any value-buffer contents at null positions.
inline void expectNullRows(
    const sdk::ToolboxHostView& toolbox, sdk::FieldHandle field, std::initializer_list<bool> expected) {
  ArrowSeries series;
  ASSERT_TRUE(series.read(toolbox, field).has_value());
  ASSERT_EQ(series.values()->length, static_cast<int64_t>(expected.size()));
  int64_t row = 0;
  for (bool is_null : expected) {
    EXPECT_EQ(ArrowArrayViewIsNull(series.values(), row) != 0, is_null) << "row " << row;
    ++row;
  }
}

}  // namespace PJ::test
