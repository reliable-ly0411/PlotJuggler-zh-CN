// Copyright 2026 Davide Faconti
// SPDX-License-Identifier: MPL-2.0

#include <QCoreApplication>
#include <QDir>
#include <QDirIterator>
#include <QFile>
#include <QFileInfo>
#include <QSettings>
#include <QStandardPaths>
#include <QSysInfo>
#include <QTemporaryFile>

#include "pj_marketplace/platform_utils.hpp"

namespace PJ {
namespace {

// Set once at startup, before any worker or service can resolve a path.
QString g_profile_directory;

bool refuseProfile(QString* error, const QString& message) {
  if (error != nullptr) {
    *error = message;
  }
  return false;
}

// Compare canonical paths, with a separator boundary so /profile-other is not
// accepted as a descendant of /profile. Windows names are case-insensitive.
bool isInsideProfile(const QString& root, const QString& path) {
#ifdef Q_OS_WIN
  constexpr Qt::CaseSensitivity sensitivity = Qt::CaseInsensitive;
#else
  constexpr Qt::CaseSensitivity sensitivity = Qt::CaseSensitive;
#endif
  const QString prefix = root.endsWith('/') ? root : root + '/';
  return path.compare(root, sensitivity) == 0 || path.startsWith(prefix, sensitivity);
}

// Existing child links could redirect writes out of the selected profile.
// Reject links rather than following them, including Windows junctions. This
// does not promise protection against concurrent hostile path replacement.
bool checkProfileTree(const QString& root, QString* error) {
  QDirIterator entries(
      root, QDir::AllEntries | QDir::Hidden | QDir::System | QDir::NoDotAndDotDot, QDirIterator::Subdirectories);
  while (entries.hasNext()) {
    entries.next();
    const QFileInfo info = entries.fileInfo();
    if (info.isSymbolicLink() || info.isJunction() || !isInsideProfile(root, info.canonicalFilePath())) {
      return refuseProfile(
          error, QStringLiteral("Profile contains a link or unresolved path: %1").arg(info.filePath()));
    }
  }
  return true;
}

// A real create/write/rename/delete probe catches ACL and read-only-volume
// failures that permission bits alone cannot represent, particularly on Windows.
bool prepareProfileDirectory(const QString& root, const QString& relative, QString* error) {
  const QString path = QDir(root).filePath(relative);
  if (!QDir().mkpath(path) || !isInsideProfile(root, QFileInfo(path).canonicalFilePath())) {
    return refuseProfile(error, QStringLiteral("Cannot create profile directory: %1").arg(path));
  }
  QTemporaryFile probe(QDir(path).filePath(QStringLiteral(".pj-profile-probe-XXXXXX")));
  if (!probe.open() || probe.write("profile", 7) != 7 || !probe.flush()) {
    return refuseProfile(
        error, QStringLiteral("Profile directory is not writable: %1 (%2)").arg(path, probe.errorString()));
  }
  const QString renamed = probe.fileName() + QStringLiteral(".renamed");
  if (!probe.rename(renamed) || !probe.remove()) {
    return refuseProfile(error, QStringLiteral("Profile directory does not support file replacement: %1").arg(path));
  }
  return true;
}

}  // namespace

bool PlatformUtils::initializeProfile(const QString& directory, QString* error) {
  if (!g_profile_directory.isEmpty()) {
    return refuseProfile(error, QStringLiteral("A profile is already active for this process"));
  }
  if (directory.isEmpty() || !QDir::isAbsolutePath(directory)) {
    return refuseProfile(error, QStringLiteral("--profile-dir requires an absolute directory"));
  }
  if (!QDir().mkpath(directory)) {
    return refuseProfile(error, QStringLiteral("Cannot create profile directory: %1").arg(directory));
  }
  const QString root = QFileInfo(directory).canonicalFilePath();
  if (root.isEmpty() || !QFileInfo(root).isDir()) {
    return refuseProfile(
        error, QStringLiteral("Profile is not a usable directory or contains linked paths: %1").arg(directory));
  }
  if (!checkProfileTree(root, error)) {
    return false;
  }

  // Include store siblings: their canonical derivation must stay beside the
  // isolated extensions directory, never beside an installed user store.
  const QStringList directories{
      QStringLiteral("."),
      QStringLiteral("settings/user"),
      QStringLiteral("settings/system"),
      QStringLiteral("data"),
      QStringLiteral("data/extensions"),
      QStringLiteral("data/.extension_staging"),
      QStringLiteral("data/.backup"),
      QStringLiteral("data/extensions.artifacts"),
      QStringLiteral("data/extensions.extraction"),
      QStringLiteral("data/extensions.profiles"),
      QStringLiteral("data/extensions.state"),
      QStringLiteral("data/extensions.install_stage"),
      QStringLiteral("data/extensions.seed_stage"),
      QStringLiteral("data/source_cache"),
      QStringLiteral("data/recordings"),
      QStringLiteral("data/models"),
      QStringLiteral("tmp")};
  for (const QString& relative : directories) {
    if (!prepareProfileDirectory(root, relative, error)) {
      return false;
    }
  }
  const QString organization = QCoreApplication::organizationName();
  const QString application = QCoreApplication::applicationName();
  if (organization.isEmpty() || application.isEmpty() || organization.contains('/') || organization.contains('\\') ||
      application.contains('/') || application.contains('\\')) {
    return refuseProfile(error, QStringLiteral("Set a valid application identity before initializing the profile"));
  }
  for (const QString& scope : {QStringLiteral("user"), QStringLiteral("system")}) {
    const QString relative = QStringLiteral("settings/%1/%2").arg(scope, organization);
    if (!prepareProfileDirectory(root, relative, error)) {
      return false;
    }
    // Existing INI files must be readable/writable too; opening ReadWrite does
    // not truncate or migrate them, and never follows a path outside this root.
    for (const QString& file_name :
         {QDir(root).filePath(relative + '/' + application + QStringLiteral(".ini")),
          QDir(root).filePath(QStringLiteral("settings/%1/%2.ini").arg(scope, organization))}) {
      if (QFileInfo::exists(file_name)) {
        QFile existing(file_name);
        if (!existing.open(QIODevice::ReadWrite)) {
          return refuseProfile(error, QStringLiteral("Cannot read and write profile settings: %1").arg(file_name));
        }
      }
    }
  }
  // Probe the actual INI backend without touching the profile's real keys or
  // installing a half-validated process-wide settings configuration.
  QString settings_probe_path;
  {
    QTemporaryFile settings_probe(QDir(root).filePath(QStringLiteral("settings/user/.pj-settings-probe-XXXXXX.ini")));
    if (!settings_probe.open()) {
      return refuseProfile(
          error, QStringLiteral("Cannot create profile settings probe: %1").arg(settings_probe.errorString()));
    }
    settings_probe_path = settings_probe.fileName();
    settings_probe.setAutoRemove(false);
    // close() alone keeps QTemporaryFile's native handle open internally.
    // Destroy it before QSettings atomically replaces the file on Windows.
  }
  bool settings_ok = false;
  {
    QSettings probe(settings_probe_path, QSettings::IniFormat);
    probe.setFallbacksEnabled(false);
    probe.setAtomicSyncRequired(true);
    probe.setValue(QStringLiteral("profile/probe"), true);
    probe.sync();
    settings_ok = probe.status() == QSettings::NoError;
  }
  const bool probe_removed = QFile::remove(settings_probe_path);
  if (!settings_ok || !probe_removed) {
    return refuseProfile(error, QStringLiteral("Cannot synchronize profile INI settings: %1").arg(settings_probe_path));
  }
  QSettings::setPath(QSettings::IniFormat, QSettings::UserScope, QDir(root).filePath(QStringLiteral("settings/user")));
  QSettings::setPath(
      QSettings::IniFormat, QSettings::SystemScope, QDir(root).filePath(QStringLiteral("settings/system")));
  QSettings::setDefaultFormat(QSettings::IniFormat);
  // Qt's shader program cache is framework-owned, outside the core path seam.
  // Disable its disk persistence in an isolated session before any GL widgets.
  QCoreApplication::setAttribute(Qt::AA_DisableShaderDiskCache);
  g_profile_directory = root;
  return true;
}

QString PlatformUtils::profileDir() {
  return g_profile_directory;
}

QString PlatformUtils::currentPlatform() {
  // QSysInfo::kernelType() returns "linux", "winnt", "darwin", etc.
  // Normalise to the friendlier names used in registry artifact keys.
  const QString kernel = QSysInfo::kernelType();
  const QString arch = QSysInfo::currentCpuArchitecture();

  QString os;
  if (kernel == "linux") {
    os = "linux";
  } else if (kernel == "winnt") {
    os = "windows";
  } else if (kernel == "darwin") {
    os = "macos";
  } else {
    os = kernel;
  }

  return os + "-" + arch;
}

std::string PlatformUtils::pluginExtension() {
#if defined(Q_OS_WIN)
  return ".dll";
#elif defined(Q_OS_MACOS)
  return ".dylib";
#else
  return ".so";
#endif
}

bool PlatformUtils::isWindows() {
#ifdef Q_OS_WIN
  return true;
#else
  return false;
#endif
}

QString PlatformUtils::configDir() {
  return g_profile_directory.isEmpty() ? QStandardPaths::writableLocation(QStandardPaths::AppDataLocation)
                                       : QDir(g_profile_directory).filePath(QStringLiteral("data"));
}

QString PlatformUtils::localDataDir() {
  return g_profile_directory.isEmpty() ? QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation)
                                       : configDir();
}

QString PlatformUtils::temporaryDir() {
  return g_profile_directory.isEmpty() ? QDir::tempPath() : QDir(g_profile_directory).filePath(QStringLiteral("tmp"));
}

QString PlatformUtils::modelCacheDir() {
  if (g_profile_directory.isEmpty()) {
    const QString override_dir = qEnvironmentVariable("PJ_MODEL_CACHE_DIR");
    if (!override_dir.isEmpty()) {
      return override_dir;
    }
  }
  return configDir() + QStringLiteral("/models");
}

QString PlatformUtils::extensionsDir() {
  return configDir() + "/extensions";
}

QString PlatformUtils::pendingDir() {
  return configDir() + "/.extension_staging";
}

QString PlatformUtils::backupDir() {
  return configDir() + "/.backup";
}

QString PlatformUtils::canonicalStoreRoot(const QString& store_dir) {
  const QString canonical = QFileInfo(store_dir).canonicalFilePath();
  return canonical.isEmpty() ? QDir::cleanPath(store_dir) : canonical;
}

}  // namespace PJ
