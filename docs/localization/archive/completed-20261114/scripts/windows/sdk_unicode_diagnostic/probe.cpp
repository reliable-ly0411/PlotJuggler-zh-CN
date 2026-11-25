// SPDX-License-Identifier: Apache-2.0
#include <filesystem>
#include <fstream>
#include <iostream>
#include <system_error>
#ifdef _WIN32
#define NOMINMAX
#include <windows.h>
#endif
#include "pj_plugins/host/plugin_catalog.hpp"

// Every operation is isolated so one conversion failure cannot hide later cases.
template <typename F> bool check(const char* name, F action) {
  try {
    const bool ok = action();
    std::cout << "case=" << name << " result=" << (ok ? "pass" : "fail") << '\n';
    return ok;
  } catch (const std::system_error& e) {
    std::cout << "case=" << name << " exception=system_error code=" << e.code().value() << '\n';
  } catch (...) {
    std::cout << "case=" << name << " exception=other\n";
  }
  return false;
}

int main(int argc, char** argv) {
  if (argc != 2) return 2;
#ifdef _WIN32
  std::cout << "ACP=" << GetACP() << '\n';
  const char* suffix = ".dll";
#elif defined(__APPLE__)
  const char* suffix = ".dylib";
#else
  const char* suffix = ".so";
#endif
  // Refuse an existing destination; only remove a directory this process created.
  const std::filesystem::path root(argv[1]);
  if (!std::filesystem::create_directory(root)) return 2;
  const auto dir = root / std::filesystem::path(u8"資料-🚀");
  const auto utf8 = dir.u8string();
  const std::string expected(utf8.begin(), utf8.end());
  bool pass = true;
  const auto contains = [&](const auto& r) { return !r && r.error().find(expected) != std::string::npos; };
  pass &= check("missing-directory", [&] { return contains(PJ::scanPluginDsos(dir)); });
  std::filesystem::create_directory(dir);
  const auto broken = dir / (std::string("broken") + suffix);
  { std::ofstream file(broken); file << "invalid native library"; if (!file) return 2; }
  pass &= check("invalid-library", [&] { return contains(PJ::inspectPluginDso(broken)); });
  pass &= check("null-handle", [&] { return contains(PJ::inspectPluginDso(std::shared_ptr<void>{}, broken)); });
  pass &= check("unsupported-unicode-suffix", [&] { return contains(PJ::inspectPluginDso(dir / std::filesystem::path(u8"file.🚀"))); });
  pass &= check("scan-invalid-library", [&] {
    auto r = PJ::scanPluginDsos(dir);
    return r && r->plugins.empty() && r->diagnostics.size() == 1 && r->diagnostics[0].message.find(expected) != std::string::npos;
  });
  pass &= check("file-as-directory", [&] { return contains(PJ::scanPluginDsos(broken)); });
  std::error_code ec;
  std::filesystem::remove_all(root, ec);
  if (ec) { std::cout << "cleanup=failed\n"; pass = false; }
  return pass ? 0 : 1;
}
