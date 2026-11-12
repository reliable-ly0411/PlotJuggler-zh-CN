// Copyright 2026 Davide Faconti
// SPDX-License-Identifier: MPL-2.0
// Native-kit-only Windows test: check the actual library and stdlib used by a
// real pj_scripting test process. It is not a general DLL-sandbox claim.

#include <gtest/gtest.h>
#include <pybind11/embed.h>
#include <pybind11/stl.h>

#include <array>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <optional>
#include <sstream>
#include <string>
#include <system_error>
#include <vector>

#include "python_sandbox.h"

// CNG declarations require the Windows types before including bcrypt.h.
// clang-format off
#include <windows.h>
#include <bcrypt.h>
// clang-format on

namespace py = pybind11;

namespace {

std::optional<std::string> sha256(const std::filesystem::path& file) {
  // CNG uses this caller-owned buffer until the hash handle is destroyed.
  std::vector<UCHAR> object;
  struct Handles {
    BCRYPT_ALG_HANDLE algorithm = nullptr;
    BCRYPT_HASH_HANDLE hash = nullptr;
    ~Handles() {
      if (hash) {
        BCryptDestroyHash(hash);
      }
      if (algorithm) {
        BCryptCloseAlgorithmProvider(algorithm, 0);
      }
    }
  } handles;
  if (BCryptOpenAlgorithmProvider(&handles.algorithm, BCRYPT_SHA256_ALGORITHM, nullptr, 0) < 0) {
    return std::nullopt;
  }
  DWORD object_size = 0, written = 0;
  if (BCryptGetProperty(
          handles.algorithm, BCRYPT_OBJECT_LENGTH, reinterpret_cast<PUCHAR>(&object_size),
          static_cast<ULONG>(sizeof(object_size)), &written, 0) < 0 ||
      written != static_cast<DWORD>(sizeof(object_size)) || !object_size) {
    return std::nullopt;
  }
  object.resize(object_size);
  if (BCryptCreateHash(handles.algorithm, &handles.hash, object.data(), object_size, nullptr, 0, 0) < 0) {
    return std::nullopt;
  }
  std::ifstream input(file, std::ios::binary);
  if (!input) {
    return std::nullopt;
  }
  std::array<char, 65536> buffer{};
  while (input) {
    input.read(buffer.data(), static_cast<std::streamsize>(buffer.size()));
    const auto count = input.gcount();
    if (count > 0 &&
        BCryptHashData(handles.hash, reinterpret_cast<PUCHAR>(buffer.data()), static_cast<ULONG>(count), 0) < 0) {
      return std::nullopt;
    }
  }
  if (!input.eof()) {
    return std::nullopt;
  }
  std::array<UCHAR, 32> result{};
  if (BCryptFinishHash(handles.hash, result.data(), static_cast<ULONG>(result.size()), 0) < 0) {
    return std::nullopt;
  }
  std::ostringstream text;
  for (const auto byte : result) {
    text << std::hex << std::setw(2) << std::setfill('0') << static_cast<unsigned>(byte);
  }
  return text.str();
}

bool within(const std::filesystem::path& file, const std::filesystem::path& home) {
  std::error_code error;
  const auto canonical_file = std::filesystem::canonical(file, error);
  if (error) {
    return false;
  }
  const auto canonical_home = std::filesystem::canonical(home, error);
  if (error) {
    return false;
  }
  const auto relative = canonical_file.lexically_relative(canonical_home);
  return !relative.empty() && !relative.is_absolute() && *relative.begin() != std::filesystem::path("..");
}

}  // namespace

TEST(WindowsPythonRuntimeIdentity, ConanLibraryAndStdlibAreActuallyLoaded) {
  const std::filesystem::path home(PJ_NATIVE_EXPECTED_PYTHON_HOME);
  const auto expected_dll = home / "python312.dll";
  const HMODULE module = GetModuleHandleW(L"python312.dll");
  ASSERT_NE(module, nullptr);
  std::vector<wchar_t> buffer(32768);
  const DWORD size = GetModuleFileNameW(module, buffer.data(), static_cast<DWORD>(buffer.size()));
  ASSERT_GT(size, 0u);
  ASSERT_LT(static_cast<std::size_t>(size), buffer.size());
  const std::filesystem::path loaded_dll(std::wstring(buffer.data(), size));
  std::error_code error;
  const bool same = std::filesystem::equivalent(loaded_dll, expected_dll, error);
  ASSERT_FALSE(error) << error.message();
  ASSERT_TRUE(same) << "loaded=" << loaded_dll.string() << " expected=" << expected_dll.string();
  const auto dll_sha256 = sha256(loaded_dll);
  ASSERT_TRUE(dll_sha256.has_value());
  ASSERT_EQ(*dll_sha256, PJ_NATIVE_EXPECTED_PYTHON_SHA256);
  const std::string version(Py_GetVersion());
  const std::string compiled(PY_VERSION);
  ASSERT_EQ(version.compare(0, compiled.size(), compiled), 0) << version;
  ASSERT_TRUE(version.size() == compiled.size() || version[compiled.size()] == ' ') << version;

  PJ::scripting::detail::ensureInterpreter();
  py::gil_scoped_acquire gil;
  const auto prefix = std::filesystem::path(py::module_::import("sys").attr("prefix").cast<std::wstring>());
  const bool same_prefix = std::filesystem::equivalent(prefix, home, error);
  ASSERT_FALSE(error) << error.message();
  ASSERT_TRUE(same_prefix) << "prefix=" << prefix.string() << " expected=" << home.string();
  const auto unicodedata =
      std::filesystem::path(py::module_::import("unicodedata").attr("__file__").cast<std::wstring>());
  ASSERT_TRUE(within(unicodedata, home)) << "unicodedata=" << unicodedata.string()
                                         << " expected home=" << home.string();
  const bool same_extension = std::filesystem::equivalent(unicodedata, home / "DLLs" / "unicodedata.pyd", error);
  ASSERT_FALSE(error) << error.message();
  ASSERT_TRUE(same_extension);
  const auto unicodedata_sha256 = sha256(unicodedata);
  ASSERT_TRUE(unicodedata_sha256.has_value());
  ASSERT_EQ(*unicodedata_sha256, PJ_NATIVE_EXPECTED_UNICODEDATA_SHA256);
  std::cout << "[native-python-binding] compiled=" << compiled << " runtime=" << version
            << " dll=" << loaded_dll.string() << " dll_sha256=" << *dll_sha256 << " prefix=" << prefix.string()
            << " unicodedata=" << unicodedata.string() << " unicodedata_sha256=" << *unicodedata_sha256 << std::endl;
}
