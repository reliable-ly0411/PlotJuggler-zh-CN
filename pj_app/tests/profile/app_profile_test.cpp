// SPDX-License-Identifier: MPL-2.0
#include <QAbstractItemView>
#include <QApplication>
#include <QComboBox>
#include <QDir>
#include <QDirIterator>
#include <QEventLoop>
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QJsonObject>
#include <QNetworkProxy>
#include <QProcess>
#include <QSettings>
#include <QStandardPaths>
#include <QTcpServer>
#include <QTcpSocket>
#include <QTemporaryDir>
#include <QTimer>
#include <cstdio>
#include <filesystem>
#include <stdexcept>

#include "AppProfile.h"
#include "WidgetTuner.h"
#include "pj_marketplace/platform_utils.hpp"
#include "pj_widgets/FrameworkTokens.h"
#include "url_fetcher.h"

namespace {

/// Fail with a useful standalone/CTest diagnostic without relying on NDEBUG.
void require(bool condition, const QString& message) {
  if (!condition) {
    throw std::runtime_error(message.toStdString());
  }
}

QByteArray readFile(const QString& path) {
  QFile file(path);
  require(file.open(QIODevice::ReadOnly), QStringLiteral("Cannot read %1").arg(path));
  return file.readAll();
}

void writeFile(const QString& path, const QByteArray& contents) {
  require(QDir().mkpath(QFileInfo(path).absolutePath()), QStringLiteral("Cannot create parent for %1").arg(path));
  QFile file(path);
  require(file.open(QIODevice::WriteOnly), QStringLiteral("Cannot write %1").arg(path));
  require(file.write(contents) == contents.size(), QStringLiteral("Short write: %1").arg(path));
}

/// Surrogate production scopes, inside the test directory, never the registry.
void prepareHostSettings(const QString& root) {
  QSettings::setDefaultFormat(QSettings::IniFormat);
  QSettings::setPath(QSettings::IniFormat, QSettings::UserScope, root + QStringLiteral("/host/user"));
  QSettings::setPath(QSettings::IniFormat, QSettings::SystemScope, root + QStringLiteral("/host/system"));
  QSettings user;
  user.setValue(QStringLiteral("host_user_only"), true);
  user.setValue(QStringLiteral("StyleSheet::theme"), QStringLiteral("dark"));
  user.sync();
  require(user.status() == QSettings::NoError, QStringLiteral("Cannot seed host user fixture"));
  QSettings system(
      QSettings::IniFormat, QSettings::SystemScope, QCoreApplication::organizationName(),
      QCoreApplication::applicationName());
  system.setValue(QStringLiteral("host_system_only"), true);
  system.sync();
  require(system.status() == QSettings::NoError, QStringLiteral("Cannot seed host system fixture"));
}

bool inside(const QString& root, const QString& path) {
#ifdef Q_OS_WIN
  constexpr Qt::CaseSensitivity sensitivity = Qt::CaseInsensitive;
#else
  constexpr Qt::CaseSensitivity sensitivity = Qt::CaseSensitive;
#endif
  return QDir::cleanPath(path).startsWith(QDir::cleanPath(root) + '/', sensitivity);
}

/// A cacheable loopback response proves the real UrlFetcher writes inside the
/// profile. No public site, plugin, or user data participates in this request.
void checkModelCache(const QString& profile) {
  QTcpServer server;
  require(server.listen(QHostAddress::LocalHost), QStringLiteral("Cannot start loopback cache fixture"));
  QObject::connect(&server, &QTcpServer::newConnection, &server, [&server]() {
    QTcpSocket* socket = server.nextPendingConnection();
    QObject::connect(socket, &QTcpSocket::readyRead, socket, [socket]() {
      if (socket->property("responded").toBool()) {
        return;
      }
      socket->readAll();
      socket->setProperty("responded", true);
      socket->write(
          "HTTP/1.1 200 OK\r\nCache-Control: public, max-age=3600\r\n"
          "Content-Type: text/plain\r\nContent-Length: 13\r\nConnection: close\r\n\r\nprofile-model");
      socket->disconnectFromHost();
    });
  });
  pj::scene3d::UrlFetcher fetcher;
  QEventLoop loop;
  QTimer deadline;
  deadline.setSingleShot(true);
  QObject::connect(&deadline, &QTimer::timeout, &loop, &QEventLoop::quit);
  bool fetched = false;
  fetcher.fetch(
      QUrl(QStringLiteral("http://127.0.0.1:%1/model").arg(server.serverPort())),
      [&loop, &fetched](pj::scene3d::FetchResult result) {
        fetched = result.ok && result.bytes == "profile-model";
        loop.quit();
      });
  deadline.start(5000);
  loop.exec();
  require(fetched, QStringLiteral("Actual model fetch did not finish"));
  QDirIterator cache_files(PJ::PlatformUtils::modelCacheDir(), QDir::Files, QDirIterator::Subdirectories);
  bool cached = false;
  while (cache_files.hasNext()) {
    const QString path = cache_files.next();
    if (QFileInfo(path).fileName() != QStringLiteral(".profile-path-test")) {
      require(inside(profile, QFileInfo(path).canonicalFilePath()), QStringLiteral("Model cache file escaped"));
      cached = true;
    }
  }
  require(cached, QStringLiteral("Actual model HTTP cache did not write a profile-local artifact"));
}

/// Both CLI spellings exercise actual production paths, settings and model cache.
void checkIsolatedPaths(const QString& base, bool equals, bool widget) {
  prepareHostSettings(base);
  const QString host_user = QSettings().fileName();
  const QString host_system = QSettings(
                                  QSettings::IniFormat, QSettings::SystemScope, QCoreApplication::organizationName(),
                                  QCoreApplication::applicationName())
                                  .fileName();
  const QByteArray user_before = readFile(host_user);
  const QByteArray system_before = readFile(host_system);
  const QString profile = base + QString::fromUtf8("/独立 profile");
  const QString external_model = base + QStringLiteral("/external-model-cache");
  qputenv("PJ_MODEL_CACHE_DIR", external_model.toUtf8());
  QString error;
  const QStringList arguments =
      equals ? QStringList{QStringLiteral("plotjuggler4"), QStringLiteral("--profile-dir=") + profile}
             : QStringList{QStringLiteral("plotjuggler4"), QStringLiteral("--profile-dir"), profile};
  require(PJ::initializeAppProfile(arguments, &error), error);
  const QString canonical = QFileInfo(profile).canonicalFilePath();
  require(PJ::PlatformUtils::profileDir() == canonical, QStringLiteral("Profile root was not canonicalized"));
  require(QSettings::defaultFormat() == QSettings::IniFormat, QStringLiteral("Profile did not select INI settings"));
  QSettings settings;
  require(inside(canonical, settings.fileName()), QStringLiteral("User settings escaped the profile"));
  require(
      !settings.contains(QStringLiteral("host_user_only")) && !settings.contains(QStringLiteral("host_system_only")),
      QStringLiteral("Settings inherited a surrogate production value"));
  QSettings system(
      QSettings::IniFormat, QSettings::SystemScope, QCoreApplication::organizationName(),
      QCoreApplication::applicationName());
  require(inside(canonical, system.fileName()), QStringLiteral("System fallback escaped the profile"));
  system.setValue(QStringLiteral("profile_system_only"), true);
  system.sync();
  settings.setValue(QStringLiteral("profile_user_only"), QStringLiteral("kept"));
  settings.sync();
  require(
      settings.status() == QSettings::NoError && system.status() == QSettings::NoError,
      QStringLiteral("Cannot persist isolated INI scopes"));
  require(
      QSettings().value(QStringLiteral("profile_user_only")).toString() == QStringLiteral("kept"),
      QStringLiteral("Profile settings did not survive a new reader"));
  require(
      QSettings().value(QStringLiteral("profile_system_only")).toBool(),
      QStringLiteral("Isolated SystemScope fallback does not work"));

  const QString data = PJ::PlatformUtils::configDir();
  require(
      data == canonical + QStringLiteral("/data") && PJ::PlatformUtils::localDataDir() == data,
      QStringLiteral("Core data roots escaped the profile"));
  const QString extensions = PJ::PlatformUtils::extensionsDir();
  QStringList paths{
      data,
      PJ::PlatformUtils::localDataDir(),
      PJ::PlatformUtils::temporaryDir(),
      PJ::PlatformUtils::modelCacheDir(),
      extensions,
      PJ::PlatformUtils::pendingDir(),
      PJ::PlatformUtils::backupDir(),
      data + QStringLiteral("/source_cache"),
      data + QStringLiteral("/recordings")};
  for (const QString& suffix :
       {QStringLiteral(".artifacts"), QStringLiteral(".extraction"), QStringLiteral(".profiles"),
        QStringLiteral(".state"), QStringLiteral(".install_stage"), QStringLiteral(".seed_stage")}) {
    paths.append(PJ::PlatformUtils::canonicalStoreRoot(extensions) + suffix);
  }
  for (const QString& path : paths) {
    require(inside(canonical, QFileInfo(path).canonicalFilePath()), QStringLiteral("Core path escaped: %1").arg(path));
    writeFile(QDir(path).filePath(QStringLiteral(".profile-path-test")), "isolated");
  }
  const QString lock = QDir(QFileInfo(extensions).absolutePath()).filePath(QStringLiteral(".extensions.lock"));
  require(inside(canonical, lock), QStringLiteral("Store lock escaped"));
  writeFile(lock, "test-only lock path");
  require(QFile::remove(lock), QStringLiteral("Cannot remove test lock"));

  QTemporaryDir extracted(QDir(PJ::PlatformUtils::temporaryDir()).filePath(QStringLiteral("urdf-assets-XXXXXX")));
  require(extracted.isValid() && inside(canonical, extracted.path()), QStringLiteral("Temporary assets escaped"));
  checkModelCache(canonical);
  require(!QFileInfo::exists(external_model), QStringLiteral("Profile honored external model-cache environment"));
  require(
      QCoreApplication::testAttribute(Qt::AA_DisableShaderDiskCache),
      QStringLiteral("Shader disk cache is not disabled"));

  if (widget) {
    PJ::WidgetTuner tuner;
    qApp->installEventFilter(&tuner);
    QComboBox combo;
    combo.ensurePolished();
    require(
        combo.view()->palette().color(QPalette::Base) ==
            PJ::theme::surface(PJ::theme::Surface::Input, PJ::theme::Theme::Light),
        QStringLiteral("Early WidgetTuner read the host dark theme"));
    qApp->removeEventFilter(&tuner);
  }
  require(
      readFile(host_user) == user_before && readFile(host_system) == system_before,
      QStringLiteral("Surrogate production settings changed"));
  QJsonObject receipt{
      {QStringLiteral("profile"), canonical},
      {QStringLiteral("settings"), settings.fileName()},
      {QStringLiteral("system_settings"), system.fileName()},
      {QStringLiteral("data"), data},
      {QStringLiteral("models"), PJ::PlatformUtils::modelCacheDir()},
      {QStringLiteral("temporary_assets"), extracted.path()}};
  writeFile(base + QStringLiteral("/paths.json"), QJsonDocument(receipt).toJson());
}

void checkDefaultPaths(const QString& base) {
  const auto original_format = QSettings::defaultFormat();
  const bool shader_disabled = QCoreApplication::testAttribute(Qt::AA_DisableShaderDiskCache);
  QString error;
  require(PJ::initializeAppProfile({QStringLiteral("plotjuggler4"), QStringLiteral("--nosplash")}, &error), error);
  require(
      PJ::PlatformUtils::profileDir().isEmpty() && QSettings::defaultFormat() == original_format,
      QStringLiteral("No-option startup changed the default settings backend"));
  require(
      PJ::PlatformUtils::configDir() == QStandardPaths::writableLocation(QStandardPaths::AppDataLocation) &&
          PJ::PlatformUtils::localDataDir() == QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation) &&
          PJ::PlatformUtils::temporaryDir() == QDir::tempPath(),
      QStringLiteral("No-option startup changed platform data paths"));
  require(
      QCoreApplication::testAttribute(Qt::AA_DisableShaderDiskCache) == shader_disabled,
      QStringLiteral("No-option startup changed shader caching"));
  qunsetenv("PJ_MODEL_CACHE_DIR");
  require(
      PJ::PlatformUtils::modelCacheDir() == PJ::PlatformUtils::configDir() + QStringLiteral("/models"),
      QStringLiteral("Default model cache changed"));
  qputenv("PJ_MODEL_CACHE_DIR", (base + QStringLiteral("/custom-models")).toUtf8());
  require(
      PJ::PlatformUtils::modelCacheDir() == base + QStringLiteral("/custom-models"),
      QStringLiteral("No-option environment override changed"));
  prepareHostSettings(base);
  const QString file = QSettings().fileName();
  require(
      PJ::initializeAppProfile(
          {QStringLiteral("plotjuggler4"), QStringLiteral("--"), QStringLiteral("--profile-dir"),
           QStringLiteral("ignored")},
          &error),
      error);
  require(
      QSettings().fileName() == file && QSettings().value(QStringLiteral("host_user_only")).toBool(),
      QStringLiteral("No-option or -- handling changed existing settings"));
}

void checkRejected(const QStringList& args) {
  QString error;
  const auto format = QSettings::defaultFormat();
  require(!PJ::initializeAppProfile(args, &error), QStringLiteral("Invalid profile unexpectedly accepted"));
  require(
      !error.isEmpty() && PJ::PlatformUtils::profileDir().isEmpty() && QSettings::defaultFormat() == format,
      QStringLiteral("Rejection changed process defaults or omitted the error"));
}

/// Guard the executable's call order as well as the isolated helper's behavior.
void checkStartupOrder() {
  const QByteArray main = readFile(QStringLiteral(PJ_PROFILE_SOURCE_DIR "/pj_app/src/main.cpp"));
  const qsizetype gui = main.indexOf("QApplication app(argc, argv);");
  const qsizetype bootstrap = main.indexOf("PJ::initializeAppProfile(app.arguments()", gui);
  require(gui >= 0 && bootstrap > gui, QStringLiteral("No early native GUI profile bootstrap"));
  for (const QByteArray& consumer :
       {QByteArray("new PJ::WidgetTuner"), QByteArray("parser.process(app)"),
        QByteArray("const QSettings language_settings"), QByteArray("PJ::MainWindow window")}) {
    require(
        main.indexOf(consumer, gui) > bootstrap,
        QStringLiteral("Profile bootstrap follows %1").arg(QString::fromUtf8(consumer)));
  }
  const qsizetype selftest = main.indexOf("return selftestPython()");
  require(
      main.indexOf("PJ::initializeAppProfile(app.arguments()") < selftest,
      QStringLiteral("Headless selftest bypasses profile validation"));
  for (const QString& file :
       {QStringLiteral("pj_runtime/src/SourceCacheStore.cpp"), QStringLiteral("pj_runtime/src/RecordingService.cpp")}) {
    const QByteArray source = readFile(QStringLiteral(PJ_PROFILE_SOURCE_DIR "/") + file);
    require(
        source.contains("PlatformUtils::localDataDir()") && source.contains("PlatformUtils::profileDir()"),
        QStringLiteral("Runtime path consumer lost its profile route: %1").arg(file));
  }
  require(
      readFile(QStringLiteral(PJ_PROFILE_SOURCE_DIR "/pj_scene3D/widgets/src/urdf_package_resolver.cpp"))
          .contains("PJ::PlatformUtils::temporaryDir()"),
      QStringLiteral("Embedded assets lost their profile temp route"));
}

}  // namespace

int main(int argc, char* argv[]) {
  QApplication app(argc, argv);
  QCoreApplication::setOrganizationName(QStringLiteral("PlotJuggler"));
  QCoreApplication::setApplicationName(QStringLiteral("PlotJuggler4"));
  QNetworkProxy::setApplicationProxy(QNetworkProxy(QNetworkProxy::NoProxy));
  const QStringList arguments = app.arguments();
  if (arguments.size() != 3) {
    std::fprintf(stderr, "usage: app_profile_test <case> <dedicated-test-directory>\n");
    return 64;
  }
  const QString mode = arguments[1];
  try {
    require(QDir().mkpath(arguments[2]), QStringLiteral("Cannot prepare dedicated test directory"));
    QTemporaryDir run(QDir(arguments[2]).filePath(mode + QStringLiteral("-XXXXXX")));
    require(run.isValid(), QStringLiteral("Cannot create dedicated test run"));
    run.setAutoRemove(false);  // receipts remain in the build tree for review
    const QString base = run.path();
    const QString profile = base + QStringLiteral("/profile");
    const QStringList profile_args{QStringLiteral("plotjuggler4"), QStringLiteral("--profile-dir"), profile};
    if (mode == QStringLiteral("DefaultPaths")) {
      checkDefaultPaths(base);
    } else if (
        mode == QStringLiteral("IsolatedPaths") || mode == QStringLiteral("EqualsSyntax") ||
        mode == QStringLiteral("EarlyWidgetSettings")) {
      checkIsolatedPaths(base, mode == QStringLiteral("EqualsSyntax"), mode == QStringLiteral("EarlyWidgetSettings"));
    } else if (mode == QStringLiteral("InvalidArguments")) {
      for (const QStringList& args :
           {QStringList{QStringLiteral("app"), QStringLiteral("--profile-dir")},
            QStringList{QStringLiteral("app"), QStringLiteral("--profile-dir=")},
            QStringList{QStringLiteral("app"), QStringLiteral("--profile-dir"), QStringLiteral("relative")},
            QStringList{QStringLiteral("app"), QStringLiteral("--profile-dir"), QStringLiteral("--help")},
            QStringList{
                QStringLiteral("app"), QStringLiteral("--profile-dir"), profile,
                QStringLiteral("--profile-dir=") + profile}}) {
        checkRejected(args);
      }
      require(!QFileInfo::exists(profile), QStringLiteral("Invalid arguments created a profile"));
    } else if (mode == QStringLiteral("RootIsFile") || mode == QStringLiteral("ChildIsFile")) {
      writeFile(mode == QStringLiteral("RootIsFile") ? profile : profile + QStringLiteral("/data"), "not a directory");
      checkRejected(profile_args);
    } else if (mode == QStringLiteral("UnwritableDirectory") || mode == QStringLiteral("UnwritableSettings")) {
      const bool directory = mode == QStringLiteral("UnwritableDirectory");
#ifdef Q_OS_WIN
      if (directory) {
        std::fprintf(
            stdout,
            "SKIP: Windows directory writability requires an ACL fixture; read-only INI is covered separately\n");
        return 77;
      }
#endif
      const QString blocked =
          directory ? profile : profile + QStringLiteral("/settings/user/PlotJuggler/PlotJuggler4.ini");
      if (directory) {
        require(QDir().mkpath(blocked), QStringLiteral("Cannot create permission fixture"));
      } else {
        writeFile(blocked, "[fixture]\nkept=true\n");
      }
      const auto original = QFile::permissions(blocked);
      const auto read_only = QFileDevice::ReadOwner | QFileDevice::ReadUser |
                             (directory ? QFileDevice::ExeOwner | QFileDevice::ExeUser : QFileDevice::Permissions{});
      require(QFile::setPermissions(blocked, read_only), QStringLiteral("Cannot make fixture read-only"));
      QString error;
      const bool accepted = PJ::initializeAppProfile(profile_args, &error);
      const bool restored = QFile::setPermissions(blocked, original);
      require(restored, QStringLiteral("Cannot restore fixture permissions"));
      require(
          !accepted && !error.isEmpty() && PJ::PlatformUtils::profileDir().isEmpty(),
          QStringLiteral("Unwritable profile was not rejected"));
    } else if (mode == QStringLiteral("LinkedJunction")) {
#ifdef Q_OS_WIN
      const QString target = base + QStringLiteral("/outside");
      const QString link = profile + QStringLiteral("/data");
      require(QDir().mkpath(target) && QDir().mkpath(profile), QStringLiteral("Cannot prepare junction fixture"));
      const int result = QProcess::execute(
          QStringLiteral("cmd.exe"),
          {QStringLiteral("/d"), QStringLiteral("/c"), QStringLiteral("mklink"), QStringLiteral("/J"),
           QDir::toNativeSeparators(link), QDir::toNativeSeparators(target)});
      require(result == 0 && QFileInfo(link).isJunction(), QStringLiteral("Cannot create a Windows junction fixture"));
      checkRejected(profile_args);
      require(QDir(target).isEmpty(), QStringLiteral("Rejected junction target was modified"));
#else
      throw std::runtime_error("Junction fixture is Windows-only");
#endif
    } else if (mode == QStringLiteral("LinkedDirectory") || mode == QStringLiteral("LinkedSettingsFile")) {
      const bool directory = mode == QStringLiteral("LinkedDirectory");
      const QString target = base + QStringLiteral("/outside");
      const QString link = profile + (directory ? QStringLiteral("/data")
                                                : QStringLiteral("/settings/user/PlotJuggler/PlotJuggler4.ini"));
      require(QDir().mkpath(QFileInfo(link).absolutePath()), QStringLiteral("Cannot prepare link fixture"));
      if (directory) {
        require(QDir().mkpath(target), QStringLiteral("Cannot prepare external directory fixture"));
      } else {
        writeFile(target, "external sentinel");
      }
      std::error_code ec;
      const std::filesystem::path target_path(target.toStdU16String());
      const std::filesystem::path link_path(link.toStdU16String());
      if (directory) {
        std::filesystem::create_directory_symlink(target_path, link_path, ec);
      } else {
        std::filesystem::create_symlink(target_path, link_path, ec);
      }
      if (ec) {
        std::fprintf(stdout, "SKIP: cannot create a native symlink fixture: %s\n", ec.message().c_str());
        return 77;
      }
      checkRejected(profile_args);
      if (!directory) {
        require(readFile(target) == "external sentinel", QStringLiteral("External linked settings changed"));
      }
    } else if (mode == QStringLiteral("StartupOrder")) {
      checkStartupOrder();
    } else {
      throw std::runtime_error("Unknown test case");
    }
    std::printf("[app-profile] PASS %s; test data: %s\n", qPrintable(mode), qPrintable(base));
    return 0;
  } catch (const std::exception& error) {
    std::fprintf(stderr, "[app-profile] FAIL %s: %s\n", qPrintable(mode), error.what());
    return 1;
  }
}
