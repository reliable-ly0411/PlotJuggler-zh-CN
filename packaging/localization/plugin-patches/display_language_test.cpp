// Copyright 2026 PlotJuggler Chinese localization contributors
// SPDX-License-Identifier: MIT
#include <pj_display_language.hpp>
#include <cctype>
#include <iostream>
#include <stdexcept>
#include <string>
// This focused path/prose fixture reads no compressed MCAP data. Production
// plugin and upstream tests keep their normal LZ4/Zstd build configuration.
#ifdef PJ_TEST_MCAP
#define MCAP_IMPLEMENTATION
#define MCAP_COMPRESSION_NO_LZ4
#define MCAP_COMPRESSION_NO_ZSTD
#include "data_load_mcap/mcap_helpers.hpp"
#endif
#ifdef PJ_TEST_ASSISTANT
#include "toolbox_assistant_agent/src/chat_session.hpp"
#endif

static void require(bool ok, const char* message) {
  if (!ok) throw std::runtime_error(message);
}

int main(int argc, char** argv) {
  require(argc == 2, "expected language argument");
  const bool chinese = std::string(argv[1]) == "zh_CN";
  require(pj_zh_localization::isChinese() == chinese, "startup language mismatch");
  require(std::string(pj_zh_localization::text("Ready", "就绪")) ==
              (chinese ? "就绪" : "Ready"), "fixed prose mismatch");
#ifdef PJ_TEST_MCAP
  const std::string missing_path = "__pj_nonexistent_raw_%1_Parser Error.yaml";
  const auto recording = PJ::McapHelpers::resolveRecordingFiles(missing_path);
  require(recording.paths.empty(), "invalid recording unexpectedly resolved");
  require(recording.error == std::string(chinese ? "无法打开 " : "Cannot open ") + missing_path,
          "MCAP fixed prose or raw path changed");
  const std::string raw_mcap = "raw_%1_Parser Error.mcap";
  const auto plain = PJ::McapHelpers::resolveRecordingFiles(raw_mcap);
  require(plain.error.empty() && plain.paths == std::vector<std::string>{raw_mcap},
          "MCAP canonical path changed");
#endif
  const std::string raw = "**Assistant:**\nError: %1\nSOURCE NOTICE:\n用户数据 ```cpp int x=1;```";
#ifdef PJ_TEST_ASSISTANT
  assistant_agent::ChatSession session;
  session.addUser(raw);
  session.addAssistant(raw);
  session.addSystem("Error: " + raw,
      std::string(pj_zh_localization::text("Error: ", "错误：")) + raw);
  const auto rendered = session.renderMarkdown();
  require(rendered.find(chinese ? "**你：**" : "**You:**") != std::string::npos,
          "user role must use display language");
  require(rendered.find(chinese ? "**助手：**" : "**Assistant:**") != std::string::npos,
          "assistant role must use display language");
  require(session.messages()[0].text == raw && session.messages()[1].text == raw,
          "raw user/model content changed");
  require(session.messages()[2].text == "Error: " + raw, "canonical system content changed");
  std::size_t position = 0;
  int occurrences = 0;
  while ((position = rendered.find(raw, position)) != std::string::npos) {
    ++occurrences;
    position += raw.size();
  }
  require(occurrences == 2, "display formatting changed embedded user/model content");
  const std::string system_body = std::string(chinese ? "错误：" : "Error: ") + raw;
  std::string escaped;
  for (char ch : system_body) {
    const auto byte = static_cast<unsigned char>(ch);
    if (byte < 128 && std::ispunct(byte) != 0) escaped.push_back('\\');
    escaped.push_back(ch);
  }
  require(rendered.find(escaped) != std::string::npos,
          "system display override or existing Markdown escaping lost");
#else
  require(std::string(pj_zh_localization::text("Error: ", "错误：")) + raw ==
              (chinese ? "错误：" : "Error: ") + raw, "raw payload changed");
#endif
  std::cout << "offline display and canonical-data checks passed\n";
}
