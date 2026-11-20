// SPDX-License-Identifier: MPL-2.0
#pragma once

#include <optional>
#include <pj_plugins/host/widget_data_view.hpp>
#include <string_view>

namespace PJ::detail {

/// Parse once for both typed access and diffing, preserving malformed-input rejection.
inline std::optional<WidgetDataView> parseWidgetDataView(std::string_view raw) {
  WidgetDataView view(raw);
  // The SDK normalizes a parse error to an empty object. Validate only that
  // ambiguous case; nonempty payloads already own their complete parsed tree.
  if (view.raw().is_object() && view.raw().empty() && !nlohmann::json::accept(raw)) {
    return std::nullopt;
  }
  return view;
}

}  // namespace PJ::detail
