// SPDX-License-Identifier: MPL-2.0
#pragma once

#include <qt_windows.h>

// Win32's generic API macro must not rewrite the PJ::MessageBox widget type.
#ifdef MessageBox
#undef MessageBox
#endif

#include <QSettings>
#include <QUuid>
#include <cstdio>
#include <cstdlib>
#include <string>

// Process-local HKCU fixture, installed before QApplication or any QSettings.
// This is not a sandbox: child processes, HKLM and KnownFolder paths are outside
// its scope. Opt in only runners whose process/file side effects are audited.
class PjTestWindowsRegistry {
 public:
  PjTestWindowsRegistry() = default;
  PjTestWindowsRegistry(const PjTestWindowsRegistry&) = delete;
  PjTestWindowsRegistry& operator=(const PjTestWindowsRegistry&) = delete;

  // Never reuse or clean a pre-existing key. Qt creates non-volatile child keys,
  // so the root must also be non-volatile; a crash can leave this unique fixture.
  bool initialize() {
    name_ = (QStringLiteral("PlotJugglerTest-") + QUuid::createUuid().toString(QUuid::WithoutBraces)).toStdWString();
    if (!check(RegOpenCurrentUser(KEY_READ | KEY_WRITE, &parent_))) {
      return false;
    }
    DWORD disposition = 0;
    if (!check(RegCreateKeyExW(
            parent_, name_.c_str(), 0, nullptr, REG_OPTION_NON_VOLATILE, KEY_READ | KEY_WRITE | DELETE, nullptr, &root_,
            &disposition))) {
      return false;
    }
    if (disposition != REG_CREATED_NEW_KEY) {
      RegCloseKey(root_);
      root_ = nullptr;
      return check(ERROR_ALREADY_EXISTS);
    }
    std::fprintf(stderr, "Private test registry: HKCU\\%ls\n", name_.c_str());
    // Keep the mapping through process exit, including Qt's static destructors.
    // Restoring HKCU after QApplication dies could let late writes hit real data.
    if (!check(RegOverridePredefKey(HKEY_CURRENT_USER, root_))) {
      return false;
    }

    HKEY qt_root = nullptr;
    if (!check(RegCreateKeyExW(
            root_, L"Software\\QtProject\\OrganizationDefaults", 0, nullptr, REG_OPTION_NON_VOLATILE,
            KEY_READ | KEY_WRITE, nullptr, &qt_root, nullptr))) {
      return false;
    }
    const DWORD sentinel = 0x504a3401;
    const LSTATUS seeded = RegSetValueExW(
        qt_root, L"pj_test_registry_probe", 0, REG_DWORD, reinterpret_cast<const BYTE*>(&sentinel), sizeof(sentinel));
    RegCloseKey(qt_root);
    if (!check(seeded)) {
      return false;
    }
    // Read our own sentinel before letting Qt write anything. This exercises the
    // exact native organization-only constructor used by QFileDialog, not INI.
    QSettings settings(QSettings::UserScope, QStringLiteral("QtProject"));
    settings.setFallbacksEnabled(false);
    if (settings.value(QStringLiteral("pj_test_registry_probe")).toUInt() != sentinel) {
      return check(ERROR_INVALID_DATA);
    }
    settings.setValue(QStringLiteral("pj_test_registry_probe"), static_cast<uint>(sentinel + 1));
    settings.sync();
    if (settings.status() != QSettings::NoError) {
      return check(ERROR_WRITE_FAULT);
    }
    DWORD actual = 0;
    DWORD size = sizeof(actual);
    if (!check(RegGetValueW(
            root_, L"Software\\QtProject\\OrganizationDefaults", L"pj_test_registry_probe", RRF_RT_REG_DWORD, nullptr,
            &actual, &size)) ||
        actual != sentinel + 1) {
      return check(ERROR_INVALID_DATA);
    }
    settings.remove(QStringLiteral("pj_test_registry_probe"));
    settings.sync();
    return settings.status() == QSettings::NoError;
  }

  // The saved handle, never a reconstructed user path, bounds all cleanup. Leave
  // HKCU mapped to this deleted key so late access fails closed. An abrupt exit
  // may leave only this run's fixture; never sweep other runs' keys on startup.
  ~PjTestWindowsRegistry() {
    if (!root_) {
      if (parent_) {
        RegCloseKey(parent_);
      }
      return;
    }
    const bool removed = check(RegDeleteTreeW(root_, nullptr)) && check(RegDeleteKeyW(parent_, name_.c_str()));
    RegCloseKey(root_);
    RegCloseKey(parent_);
    if (!removed) {
      std::_Exit(EXIT_FAILURE);
    }
  }

 private:
  // Report only an error code, never registry contents from the user's account.
  static bool check(LSTATUS status) {
    if (status == ERROR_SUCCESS) {
      return true;
    }
    std::fprintf(stderr, "Private test registry failed (Windows error %ld); refusing test execution.\n", status);
    return false;
  }

  // Only initialization and exact owned-child deletion use this real parent.
  HKEY parent_ = nullptr;
  HKEY root_ = nullptr;
  std::wstring name_;
};

// Read only existence, never contents, of system QFileDialog fallback memory.
// This snapshot is a deterministic-test precondition, not a concurrent sandbox.
inline bool pjTestSystemFileDialogMemoryAbsent() {
  HKEY key = nullptr;
  LSTATUS status =
      RegOpenKeyExW(HKEY_LOCAL_MACHINE, L"Software\\QtProject\\OrganizationDefaults\\FileDialog", 0, KEY_READ, &key);
  if (status == ERROR_SUCCESS) {
    RegCloseKey(key);
    std::fprintf(stderr, "System QFileDialog memory exists; native test precondition is not met.\n");
    return false;
  }
  if (status != ERROR_FILE_NOT_FOUND) {
    std::fprintf(stderr, "Cannot establish absence of system file-dialog memory (%ld).\n", status);
    return false;
  }
  status = RegOpenKeyExW(HKEY_LOCAL_MACHINE, L"Software\\QtProject\\OrganizationDefaults\\Qt", 0, KEY_READ, &key);
  if (status == ERROR_FILE_NOT_FOUND) {
    return true;
  }
  if (status == ERROR_SUCCESS) {
    status = RegQueryValueExW(key, L"filedialog", nullptr, nullptr, nullptr, nullptr);
    RegCloseKey(key);
    if (status == ERROR_FILE_NOT_FOUND) {
      return true;
    }
  }
  std::fprintf(stderr, "System legacy QFileDialog memory is present or inaccessible (%ld).\n", status);
  return false;
}
