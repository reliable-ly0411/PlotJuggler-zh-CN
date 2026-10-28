// SPDX-License-Identifier: MPL-2.0
#include <cstdlib>
#include <pj_base/sdk/toolbox_plugin_base.hpp>

namespace {
// Discovery must use the embedded manifest without constructing a toolbox instance.
class MetadataFixture : public PJ::ToolboxPluginBase {
 public:
  MetadataFixture() {
    std::abort();
  }
  uint64_t capabilities() const override {
    return 0;
  }
};
constexpr const char* kManifest = R"({
  "id":"metadata-fixture", "name":"Metadata fixture", "version":"1.2.3",
  "category":"toolbox", "description":"Installed outside every registry",
  "author":"Fixture <author> & contributors", "license":"MIT",
  "repository":"https://example.org/plugins/metadata"
})";
}  // namespace
PJ_TOOLBOX_PLUGIN(MetadataFixture, kManifest)
