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
  // Returns the platform identifier used as key in registry artifact maps.
  // Format: "<os>-<arch>", e.g. "linux-x86_64", "windows-x86_64", "macos-arm64".
  static QString currentPlatform();

  // Returns true on Windows builds.
  static bool isWindows();

  // Returns the shared library extension for the current platform:
  //   Linux:   ".so"
  //   Windows: ".dll"
  //   macOS:   ".dylib"
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

  // <config-root>/.extension_staging/ — restart staging for Windows updates.
  static QString pendingDir();

  // <config-root>/.backup/ — pre-update backups (F-12, deferred to April+).
  static QString backupDir();

  // Identity of a managed store: `store_dir` made absolute with symlinks resolved.
  //
  // Anything placed BESIDE a store must be derived from this rather than from the
  // configured string, because a configured path can be a symlink: a packaged
  // install pointing at a data volume, a developer linking the store elsewhere.
  // Derived textually, a sibling is created next to the LINK, which resolves onto
  // a different filesystem than the store itself and turns promote-by-rename into
  // EXDEV; and two names for one store yield two different sibling paths, so a
  // lock file keyed that way would hand out two writer leases for one store.
  //
  // Shared policy for every sibling PlotJuggler keeps next to the extensions dir:
  // the writer lease (ExtensionManager), the install transaction staging area
  // (ExtensionManager), and the bundled-seed staging area (pj_runtime's
  // ExtensionCatalogService).
  //
  // Falls back to the cleaned path when resolution fails — canonicalFilePath() is
  // empty for a path that does not exist, which is the first-run state rather than
  // an error. Create the store before deriving siblings from it to stay off that
  // path.
  static QString canonicalStoreRoot(const QString& store_dir);
};

}  // namespace PJ
