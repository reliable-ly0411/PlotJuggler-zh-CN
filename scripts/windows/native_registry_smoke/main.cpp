// SPDX-License-Identifier: MPL-2.0
#include <QCoreApplication>
#include <QSettings>
#include <QUuid>
#include <qt_windows.h>
#include <cstdio>
#include <cstdlib>
#include <string>

// Compile-time injection affects only the test's guard, never production code.
static LSTATUS injectedDeleteTree(HKEY key, LPCWSTR path) {
  if (qEnvironmentVariableIsSet("PJ_FIXTURE_FAIL_CLEANUP")) {
    std::fprintf(stderr, "Injected owned-key cleanup failure: %ld\n", static_cast<long>(ERROR_ACCESS_DENIED));
    std::fflush(stderr);
    return ERROR_ACCESS_DENIED;
  }
  return RegDeleteTreeW(key, path);
}
#define RegDeleteTreeW injectedDeleteTree
#include "pj_test_windows_registry.h"
#undef RegDeleteTreeW

// Own a fresh real sentinel identity before remapping. A broken late mapping may
// write ONLY this generated identity, never the user's QtProject preferences.
struct LateProbe {
  HKEY parent = nullptr;
  HKEY owned = nullptr;
  QString organization;
  std::wstring name;
  void prepare() {
    organization = QStringLiteral("PJFixtureLate-") + QUuid::createUuid().toString(QUuid::WithoutBraces);
    name = organization.toStdWString();
    DWORD disposition = 0;
    if (RegOpenKeyExW(HKEY_CURRENT_USER, L"Software", 0, KEY_READ | KEY_WRITE, &parent) != ERROR_SUCCESS ||
        RegCreateKeyExW(parent, name.c_str(), 0, nullptr, 0, KEY_READ | KEY_WRITE | DELETE,
                        nullptr, &owned, &disposition) != ERROR_SUCCESS || disposition != REG_CREATED_NEW_KEY) {
      std::_Exit(2);
    }
    std::fprintf(stderr,"Owned late sentinel: HKCU\\Software\\%ls\n",name.c_str());
  }
  ~LateProbe() {
    if (!owned) return;
    bool failed_closed = false;
    {
      QSettings late(QSettings::UserScope, organization);
      late.setFallbacksEnabled(false);
      late.setValue(QStringLiteral("late_fixture_probe"), 1);
      late.sync();
      failed_closed = late.status() == QSettings::AccessError;
    }
    HKEY unexpected = nullptr;
    const LSTATUS untouched = RegOpenKeyExW(owned, L"OrganizationDefaults", 0, KEY_READ, &unexpected);
    if (unexpected) RegCloseKey(unexpected);
    const bool cleaned = RegDeleteTreeW(owned, nullptr) == ERROR_SUCCESS &&
                         RegDeleteKeyW(parent, name.c_str()) == ERROR_SUCCESS;
    RegCloseKey(owned); RegCloseKey(parent);
    if (!failed_closed || untouched != ERROR_FILE_NOT_FOUND || !cleaned) std::_Exit(3);
    std::fprintf(stderr,"Late QSettings write failed closed; self-owned real sentinel untouched.\n");
  }
} late_probe;

int main(int argc, char** argv) {
  late_probe.prepare();
  PjTestWindowsRegistry registry;
  if (!registry.initialize()) return 4;
  QCoreApplication app(argc, argv);
  std::fprintf(stderr,"Native guard initialized; QApplication-free lifecycle probe.\n");
  std::fflush(stderr);
  return 0;
}
