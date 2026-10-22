// Copyright 2026 PlotJuggler Chinese localization contributors
// SPDX-License-Identifier: MIT
#pragma once
#include <cstdlib>
#include <cstring>

// The host sets this once at startup, before loading plugins or starting workers.
// UI preference only; never used for protocol/configuration/data translation.
namespace pj_zh_localization {
inline bool isChinese() {
  // Take an owned, immutable decision once per plugin image. Never retain a
  // pointer into the environment or race worker threads with preference writes.
  static const bool use_chinese = [] {
#ifdef _WIN32
    char language[16] = {};
    std::size_t size = 0;
    return getenv_s(&size, language, sizeof(language), "PLOTJUGGLER_UI_LANGUAGE") == 0 &&
           std::strcmp(language, "zh_CN") == 0;
#else
    const char* language = std::getenv("PLOTJUGGLER_UI_LANGUAGE");
    return language != nullptr && std::strcmp(language, "zh_CN") == 0;
#endif
  }();
  return use_chinese;
}
inline const char* text(const char* english, const char* chinese) {
  return isChinese() ? chinese : english;
}
}  // namespace pj_zh_localization
