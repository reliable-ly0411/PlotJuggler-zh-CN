// SPDX-License-Identifier: MPL-2.0
#pragma once

// Managed stores are a native-test fixture, not a WebAssembly dependency.
#ifndef __EMSCRIPTEN__

#include <QCoreApplication>
#include <QSettings>

#include "pj_marketplace/platform_utils.hpp"
#include "pj_test_owned_directory.h"

#ifdef Q_OS_WIN
#include "pj_test_windows_registry.h"
// Custom mains need their own mapping; shared GUI mains already install it.
#define PJ_TEST_INITIALIZE_PRIVATE_HKCU \
  PjTestWindowsRegistry registry;       \
  if (!registry.initialize()) {         \
    return EXIT_FAILURE;                \
  }
#else
#define PJ_TEST_INITIALIZE_PRIVATE_HKCU
#endif

// One per process, declared before QApplication and initialized before any
// AppSession. Never switch a live multi-window process between profiles.
// Production profile contracts must not use this test adapter.
class PjTestManagedProfile {
 public:
  using Initializer = bool (*)(const QString&, QString*);

  // Preserve an already selected INI user's fixture path; use a new private
  // system fallback. Native stays Native (HKCU must be separately guarded).
  // The injectable initializer is only for failure-path regression tests.
  // ini_owner, if needed, must outlive this profile and every settings user.
  bool initialize(
      const PjTestOwnedDirectory* ini_owner = nullptr,
      Initializer initialize_profile = PJ::PlatformUtils::initializeProfile) {
    if (!PJ::PlatformUtils::profileDir().isEmpty() || !directory_.ownsTree()) {
      return false;
    }
    const auto format = QSettings::defaultFormat();
    const bool shader_cache_disabled = QCoreApplication::testAttribute(Qt::AA_DisableShaderDiskCache);
    const QString organization = QCoreApplication::organizationName();
    const QString application = QCoreApplication::applicationName();
    const QString probe_name = QStringLiteral("PjFixtureProbe-") + QUuid::createUuid().toString(QUuid::WithoutBraces);
    QString ini_user_root;
    if (format == QSettings::IniFormat) {
      if (ini_owner == nullptr || !ini_owner->ownsTree()) {
        qCritical("Prior INI user path has no verified live fixture owner");
        return false;
      }
      // fileName alone is a read-only path query for a never-used identity.
      // Qt INI layout is <scope-root>/<organization>/<application>.ini.
      const QSettings probe(QSettings::IniFormat, QSettings::UserScope, probe_name, probe_name);
      QDir parent = QFileInfo(probe.fileName()).absoluteDir();
      if (!parent.cdUp()) {
        return false;
      }
      ini_user_root = parent.absolutePath();
      if (!verifiedIniRoot(*ini_owner, ini_user_root)) {
        qCritical("Prior INI user path is outside its verified fixture owner");
        return false;
      }
    }
    // Some core mains have no identity until gtest Environment::SetUp. Use a
    // unique temporary identity only for profile validation, then restore it.
    QCoreApplication::setOrganizationName(probe_name);
    QCoreApplication::setApplicationName(probe_name);
    QString error;
    const bool initialized = initialize_profile(directory_.path(), &error);
    QCoreApplication::setOrganizationName(organization);
    QCoreApplication::setApplicationName(application);
    QCoreApplication::setAttribute(Qt::AA_DisableShaderDiskCache, shader_cache_disabled);
    QSettings::setDefaultFormat(format);
    if (!initialized) {
      qCritical("Cannot initialize managed test profile: %s", qPrintable(error));
      return false;
    }
    if (!ini_user_root.isEmpty()) {
      if (!verifiedIniRoot(*ini_owner, ini_user_root)) {
        return false;
      }
      QSettings::setPath(QSettings::IniFormat, QSettings::UserScope, ini_user_root);
    }
    return directory_.ownsTree() && PJ::PlatformUtils::profileDir() == directory_.path();
  }

  const QString& path() const {
    return directory_.path();
  }

 private:
  // A concrete owner/token, not membership in a broad TEMP directory, is proof.
  // ownsTree rejects links/junctions in the root ancestry and every descendant.
  static bool verifiedIniRoot(const PjTestOwnedDirectory& owner, const QString& root) {
    if (!owner.ownsTree() || !QDir::isAbsolutePath(root)) {
      return false;
    }
    const QString canonical = QFileInfo(root).canonicalFilePath();
#ifdef Q_OS_WIN
    constexpr auto sensitivity = Qt::CaseInsensitive;
#else
    constexpr auto sensitivity = Qt::CaseSensitive;
#endif
    if (canonical.isEmpty() || !QFileInfo(root).isDir() || canonical.compare(QDir::cleanPath(root), sensitivity) != 0) {
      return false;
    }
    return canonical.compare(owner.path(), sensitivity) == 0 || canonical.startsWith(owner.path() + '/', sensitivity);
  }

  PjTestOwnedDirectory directory_;
};

// Custom mains use the same native-only gate as the CMake opt-in runners.
#define PJ_TEST_INITIALIZE_MANAGED_PROFILE \
  PjTestManagedProfile managed_profile;    \
  if (!managed_profile.initialize()) {     \
    return EXIT_FAILURE;                   \
  }
#else
#define PJ_TEST_INITIALIZE_PRIVATE_HKCU
#define PJ_TEST_INITIALIZE_MANAGED_PROFILE
#endif
