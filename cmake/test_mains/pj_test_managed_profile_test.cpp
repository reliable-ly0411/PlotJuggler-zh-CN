// SPDX-License-Identifier: MPL-2.0
#include "pj_test_managed_profile.h"

#include <QFile>
#include <QTextStream>

static bool reject(const QString& path, QString* error) {
  if (!QDir::isAbsolutePath(path) || !QFileInfo(path).isDir()) {
    std::abort();
  }
  *error = QStringLiteral("injected profile initialization failure");
  return false;
}

int main(int argc, char** argv) {
  if (argc != 2) {
    return 11;
  }
  PJ_TEST_INITIALIZE_PRIVATE_HKCU
  const QString mode = QString::fromLocal8Bit(argv[1]);
  PjTestOwnedDirectory settings;
  const QString user = settings.path() + "/user";
  const QString system = settings.path() + "/system";
  if (!QDir().mkpath(user) || !QDir().mkpath(system)) {
    return 1;
  }
  QSettings::setPath(QSettings::IniFormat, QSettings::UserScope, user);
  QSettings::setPath(QSettings::IniFormat, QSettings::SystemScope, system);
  const auto format = mode == "native" ? QSettings::NativeFormat : QSettings::IniFormat;
  QSettings::setDefaultFormat(format);
  QCoreApplication::setOrganizationName("ProfileProbe");
  QCoreApplication::setApplicationName("Runner");
  const bool shader = QCoreApplication::testAttribute(Qt::AA_DisableShaderDiskCache);
  {
    QSettings old_system(QSettings::IniFormat, QSettings::SystemScope, "ProfileProbe", "Runner");
    old_system.setValue("external", true);
    old_system.sync();
  }
  QString managed_root;
  {
    PjTestManagedProfile profile;
    managed_root = profile.path();
    if (mode == "fail") {
      if (profile.initialize(&settings, reject) || !PJ::PlatformUtils::profileDir().isEmpty() ||
          QSettings::defaultFormat() != format || QCoreApplication::organizationName() != "ProfileProbe" ||
          QCoreApplication::testAttribute(Qt::AA_DisableShaderDiskCache) != shader) {
        return 2;
      }
      QSettings after(QSettings::IniFormat, QSettings::UserScope, "ProfileProbe", "Runner");
      if (after.fileName() != user + "/ProfileProbe/Runner.ini") {
        return 3;
      }
      QTextStream(stdout) << "failure refused before tests, original configuration preserved\n";
      return 0;
    }
    if (mode == "unverified" || mode == "wrong_owner") {
      PjTestOwnedDirectory other;
      const auto* proof = mode == "wrong_owner" ? &other : nullptr;
      if (profile.initialize(proof) || !PJ::PlatformUtils::profileDir().isEmpty() ||
          QSettings::defaultFormat() != format || QFileInfo::exists(user + "/ProfileProbe/Runner.ini")) {
        return 14;
      }
      QTextStream(stdout) << "unverified or unrelated INI owner refused before profile initialization\n";
      return 0;
    }
    if (!profile.initialize(&settings)) {
      return 4;
    }
    QCoreApplication app(argc, argv);
    if (QSettings::defaultFormat() != format ||
        QCoreApplication::testAttribute(Qt::AA_DisableShaderDiskCache) != shader) {
      return 5;
    }
    for (const QString& path :
         {PJ::PlatformUtils::configDir(), PJ::PlatformUtils::extensionsDir(), PJ::PlatformUtils::pendingDir(),
          PJ::PlatformUtils::backupDir(), PJ::PlatformUtils::temporaryDir()}) {
      if (!QFileInfo(path).canonicalFilePath().startsWith(managed_root + '/')) {
        return 6;
      }
    }
    QSettings private_system(QSettings::IniFormat, QSettings::SystemScope, "ProfileProbe", "Runner");
    if (!private_system.fileName().startsWith(managed_root + '/')) {
      return 7;
    }
    private_system.setValue("private_fallback", true);
    private_system.sync();
    QSettings actual(QSettings::IniFormat, QSettings::UserScope, "ProfileProbe", "Runner");
    if ((format == QSettings::IniFormat && actual.fileName() != user + "/ProfileProbe/Runner.ini") ||
        actual.contains("external") || !actual.value("private_fallback").toBool()) {
      return 8;
    }
    // Explicit Native remains Native. On Windows this requires the registry
    // smoke's real guard; Linux only checks format, not Win32 behavior.
    QSettings native(QSettings::NativeFormat, QSettings::UserScope, "ProfileProbe", "Runner");
    if (native.format() != QSettings::NativeFormat) {
      return 9;
    }
#ifdef Q_OS_WIN
    native.setValue("private_native_probe", 42);
    native.sync();
    if (native.status() != QSettings::NoError || native.value("private_native_probe").toInt() != 42) {
      return 12;
    }
#endif
    if (mode == "duplicate") {
      PjTestManagedProfile second;
      if (second.initialize() || PJ::PlatformUtils::profileDir() != managed_root) {
        return 13;
      }
    }
  }
  if (QFileInfo::exists(managed_root)) {
    return 10;
  }
  QTextStream(stdout)
      << "owned paths, settings format/user/fallback, shader attribute, app-before-root lifetime passed\n";
  return 0;
}
