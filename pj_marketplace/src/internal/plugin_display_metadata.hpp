// SPDX-License-Identifier: MPL-2.0
#pragma once

#include <nlohmann/json.hpp>
#include <pj_plugins/host/data_source_library.hpp>
#include <pj_plugins/host/dialog_library.hpp>
#include <pj_plugins/host/message_parser_library.hpp>
#include <pj_plugins/host/plugin_catalog.hpp>
#include <pj_plugins/host/toolbox_library.hpp>
#include <string>
#include <string_view>

namespace PJ::marketplace_internal {

/// Optional presentation fields deliberately kept outside the pinned SDK descriptor/ABI.
struct PluginDisplayMetadata {
  std::string author;
  std::string license;
  std::string website;
  std::string repository;
};

/// Read only string-valued display fields from the same identity that discovery admitted.
/// Malformed optional fields do not change plugin admission or compatibility decisions.
inline PluginDisplayMetadata decodePluginDisplayMetadata(
    std::string_view manifest, const PluginDescriptor& descriptor) {
  const auto json = nlohmann::json::parse(manifest, nullptr, false);
  if (!json.is_object()) {
    return {};
  }
  const auto string = [&](const char* key) -> std::string {
    const auto it = json.find(key);
    return it != json.end() && it->is_string() ? it->get<std::string>() : std::string{};
  };
  if (string("id") != descriptor.id || string("version") != descriptor.version) {
    return {};
  }
  return {string("author"), string("license"), string("website"), string("repository")};
}

/// The SDK loaders validate ABI, vtable size and symbol provenance before exposing a manifest.
/// No plugin instance is created for direct-vtable families.
template <typename Library>
PluginDisplayMetadata directPluginDisplayMetadata(const PluginDescriptor& descriptor) {
  auto library = Library::load(descriptor.dso_path);
  if (!library || library->vtable()->manifest_json == nullptr) {
    return {};
  }
  return decodePluginDisplayMetadata(library->vtable()->manifest_json, descriptor);
}

/// Supplement an already-discovered DSO using public SDK 0.34.1 APIs, never a sidecar.
/// Admission callers must run this in the same disposable helper as discovery.
inline PluginDisplayMetadata readPluginDisplayMetadata(const PluginDescriptor& descriptor) {
  switch (descriptor.family) {
    case PluginFamily::kDataSource:
      return directPluginDisplayMetadata<DataSourceLibrary>(descriptor);
    case PluginFamily::kMessageParser:
      return directPluginDisplayMetadata<MessageParserLibrary>(descriptor);
    case PluginFamily::kToolbox:
      return directPluginDisplayMetadata<ToolboxLibrary>(descriptor);
    case PluginFamily::kDialog: {
      auto library = DialogLibrary::load(descriptor.dso_path);
      if (!library) {
        return {};
      }
      const auto* vtable = library->vtable();
      if (PJ_HAS_TAIL_SLOT(PJ_dialog_vtable_t, vtable, manifest_json)) {
        return decodePluginDisplayMetadata(vtable->manifest_json, descriptor);
      }
      auto handle = library->createHandle();
      return handle.context() != nullptr ? decodePluginDisplayMetadata(handle.manifest(), descriptor)
                                         : PluginDisplayMetadata{};
    }
    case PluginFamily::kUnknown:
      return {};
  }
  return {};
}

}  // namespace PJ::marketplace_internal
