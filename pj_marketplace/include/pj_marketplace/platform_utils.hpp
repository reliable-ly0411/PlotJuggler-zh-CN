#pragma once
// Copyright 2026 Davide Faconti
// SPDX-License-Identifier: MPL-2.0

#include <QString>
#include <string>

namespace PJ {

// Static helpers for platform detection and standard directory resolution.
//
// Path getters do not create directories. initializeProfile() is the explicit
// startup-only exception; without it, platform defaults remain unchanged.
class PlatformUtils {
 public:
  // The platform id used as key in registry artifact maps: "<os>-<arch>", e.g. "linux-x86_64", "windows-x86_64",
  // "macos-arm64".
  static QString currentPlatform();

  // True on Windows builds.
  static bool isWindows();

  // The shared-library extension of the platform: ".so", ".dll" or ".dylib".
  static std::string pluginExtension();

  // Install a dedicated native profile before any app-owned QSettings, store,
  // cache, or widget is constructed. Requires an absolute, writable directory.
  // Validates core subdirectories and both INI settings scopes before publishing
  // the root; failure leaves the process defaults unchanged. Call once, on the
  // main thread. This is data separation, not a sandbox for external plugins.
  [[nodiscard]] static bool initializeProfile(const QString& directory, QString* error);

  // Empty unless initializeProfile() succeeded for this process.
  static QString profileDir();

  // <profile>/data when explicitly isolated; otherwise AppDataLocation, i.e. the
  // PlotJuggler/PlotJuggler4 org/app pair):
  //   Linux:   ~/.local/share/PlotJuggler/PlotJuggler4/
  //   Windows: %LOCALAPPDATA%/PlotJuggler/PlotJuggler4/
  //   macOS:   ~/Library/Application Support/PlotJuggler/PlotJuggler4/
  static QString configDir();

  // <profile>/data, or the unchanged platform AppLocalDataLocation.
  static QString localDataDir();

  // <profile>/tmp, or the platform temporary directory. Use an explicit
  // QTemporaryDir template with this parent for core-owned temporary assets.
  static QString temporaryDir();

  // <profile>/data/models takes precedence over PJ_MODEL_CACHE_DIR. With no
  // profile, retain the environment override and AppDataLocation fallback.
  static QString modelCacheDir();

  // <config-root>/extensions/ — active, loaded extensions.
  static QString extensionsDir();

  // <config-root>/.extension_staging/ — where staged updates wait for the restart that promotes them (all platforms).
  static QString pendingDir();

  // <config-root>/.backup/ — the previous version of an extension is moved here when a staged update is promoted.
  static QString backupDir();

  // Identity of a managed store: `store_dir` made absolute with symlinks resolved. Everything placed BESIDE a store
  // (the writer lease, the install staging area, the removal journal, the content-addressed store, and the bundled
  // seed's staging area in pj_runtime's ExtensionCatalogService) must derive from this, not from the configured
  // string: derived textually, a sibling lands next to a symlink, possibly on another filesystem than the store, which
  // turns promote-by-rename into EXDEV, and two names for one store would yield two lock files and two writer leases.
  // Falls back to the cleaned path when resolution fails (a path that does not exist yet); create the store first to
  // avoid that.
  static QString canonicalStoreRoot(const QString& store_dir);
};

}  // namespace PJ
