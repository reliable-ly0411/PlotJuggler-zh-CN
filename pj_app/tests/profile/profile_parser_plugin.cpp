// SPDX-License-Identifier: MPL-2.0
// Same wildcard claim, different identities: bundled provenance must outrank
// the alphabetically earlier marketplace provider, regardless of Unicode paths.
#include "mock_message_parser_vtable.h"

extern "C" PJ_MESSAGE_PARSER_EXPORT const uint32_t pj_plugin_abi_version = PJ_ABI_VERSION;

extern "C" PJ_MESSAGE_PARSER_EXPORT const PJ_message_parser_vtable_t* PJ_get_message_parser_vtable() noexcept {
#ifdef PROFILE_BUNDLED_PARSER
  static const auto table = pj_mock::makeMockMessageParserVtable(
      R"({"id":"zzz-profile-bundled","name":"Bundled Parser","version":"1.0.0","encoding":["json"]})");
#else
  static const auto table = pj_mock::makeMockMessageParserVtable(
      R"({"id":"aaa-profile-marketplace","name":"Marketplace Parser","version":"1.0.0","encoding":["json"]})");
#endif
  return &table;
}
