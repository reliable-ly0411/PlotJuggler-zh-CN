// SPDX-License-Identifier: MPL-2.0
// Full-native integration: actual services, not stand-ins or copied path math.
#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QSettings>
#include <QTemporaryDir>
#include <algorithm>
#include <cstdio>
#include <filesystem>
#include <memory>
#include <stdexcept>

#include "pj_marketplace/extension_manager.hpp"
#include "pj_marketplace/platform_utils.hpp"
#include "pj_marketplace/store_lease.hpp"
#include "pj_marketplace/store_session.hpp"
#include "pj_runtime/ExtensionCatalogService.h"
#include "pj_runtime/LocalizedPluginSeed.h"
#include "pj_runtime/QSettingsBackend.h"
#include "pj_runtime/RecordingService.h"
#include "pj_runtime/SourceCacheStore.h"
#ifdef PJ_PROFILE_WITH_URDF
#include "urdf_package_resolver.h"
#endif

namespace {

void require(bool condition, const QString& message) {
  if (!condition) {
    throw std::runtime_error(message.toStdString());
  }
}

QString asQString(const std::filesystem::path& path) {
  return QString::fromStdU16String(path.u16string());
}

bool inside(const QString& root, const QString& path) {
#ifdef Q_OS_WIN
  constexpr Qt::CaseSensitivity sensitivity = Qt::CaseInsensitive;
#else
  constexpr Qt::CaseSensitivity sensitivity = Qt::CaseSensitive;
#endif
  return QDir::cleanPath(path).startsWith(QDir::cleanPath(root) + '/', sensitivity);
}

/// Record one source with the production MCAP sink and publish that real file
/// through the production source cache, despite external saved/caller paths.
void checkCaptureServices(const QString& profile, const QString& outside) {
  QSettings settings;
  settings.setValue(QStringLiteral("Preferences::source_cache_directory"), outside + QStringLiteral("/cache"));
  settings.setValue(QStringLiteral("Preferences::recording_directory"), outside + QStringLiteral("/recordings"));
  settings.sync();
  require(settings.status() == QSettings::NoError, QStringLiteral("Cannot save profile fixture settings"));
  const auto loaded_cache = PJ::SourceCacheStore::loadSettings();
  const auto loaded_recording = PJ::RecordingService::loadSettings();
  require(
      inside(profile, loaded_cache.directory) && inside(profile, loaded_recording.directory),
      QStringLiteral("Saved output override escaped the active profile"));
  require(
      inside(profile, asQString(PJ::SourceCacheStore::defaultRoot())) &&
          inside(profile, PJ::RecordingService::defaultDirectory()),
      QStringLiteral("Runtime default output escaped the active profile"));

  PJ::RecordingService recorder;
  PJ::RecordingService::Settings recording_settings;
  recording_settings.directory = outside + QStringLiteral("/caller-recordings");
  recorder.setSettings(recording_settings);
  std::shared_ptr<PJ::RecordTap> tap;
  PJ::RecordingTarget target;
  target.target_key = 1;
  target.source_id = "profile-fixture";
  target.plugin_id = "synthetic-source";
  target.attach = [&tap](std::shared_ptr<PJ::RecordTap> installed) {
    tap = std::move(installed);
    return true;
  };
  const auto started = recorder.start({target}, "profile-test");
  require(started.has_value(), started ? QString{} : QString::fromStdString(started.error()));
  require(inside(profile, *started), QStringLiteral("Actual recording was created outside the profile"));
  recorder.stop();
  require(tap == nullptr, QStringLiteral("Recording tap was not detached"));
  const auto files = QDir(*started).entryList({QStringLiteral("*.mcap")}, QDir::Files);
  require(files.size() == 1, QStringLiteral("Actual recording did not create one MCAP file"));

  PJ::SourceCacheStore::Settings cache_settings;
  cache_settings.directory = outside + QStringLiteral("/caller-cache");
  auto cache = PJ::SourceCacheStore::fromSettings(cache_settings);
  require(inside(profile, asQString(cache->root())), QStringLiteral("Caller cache path escaped the profile"));
  constexpr char identity[] = "profile-fixture";
  auto transaction = cache->beginPublish(identity);
  require(transaction.has_value(), QStringLiteral("Cannot begin profile-local cache publication"));
  const QString partial = asQString(transaction->partialPath());
  require(inside(profile, partial), QStringLiteral("Cache partial file escaped the profile"));
  QFile recording(QDir(*started).filePath(files.front()));
  require(recording.open(QIODevice::ReadOnly), QStringLiteral("Cannot read fixture MCAP"));
  const QByteArray bytes = recording.readAll();
  QFile destination(partial);
  require(destination.open(QIODevice::WriteOnly | QIODevice::Truncate), QStringLiteral("Cannot write cache partial"));
  require(destination.write(bytes) == bytes.size(), QStringLiteral("Cannot copy fixture MCAP"));
  destination.close();
  auto published = cache->publish(identity, std::move(*transaction));
  require(published.has_value(), QStringLiteral("Cannot publish recorded MCAP to the profile cache"));
  require(inside(profile, asQString(published->path)), QStringLiteral("Published cache artifact escaped"));
  require(
      !QFileInfo::exists(outside), QStringLiteral("A persisted/caller output override created an external directory"));
}

void checkMarketplace(const QString& profile) {
  PJ::ExtensionCatalogService::Paths paths;
  paths.install_dir = profile + QStringLiteral("/插件 discovery-override");
  paths.bundled_dir = profile + QStringLiteral("/随包 bundled-fixture");
  const QString id = QStringLiteral("mock-data-source");
  const QString version = QStringLiteral("2.0.0");
  const QString payload = QDir(paths.bundled_dir).filePath(id);
  require(QDir().mkpath(payload), QStringLiteral("Cannot prepare bundled source"));
  const QString original = QString::fromUtf8(PJ_PROFILE_PLUGIN_PATH);
  const QString filename = QFileInfo(original).fileName();
  const QString bundled_dso = QDir(payload).filePath(filename);
  require(QFile::copy(original, bundled_dso), QStringLiteral("Cannot copy real fixture plugin"));
  const QString hash = PJ::LocalizedPluginSeed::fileHash(bundled_dso);
  require(hash.size() == 64, QStringLiteral("Cannot hash Unicode fixture path"));
  const QJsonObject object{
      {"schema", 1},    {"kind", "fork-localized-rebuild"}, {"id", id}, {"version", version}, {"dso", filename},
      {"sha256", hash}, {"legacy_sha256", QJsonArray{}}};
  QFile marker(QDir(payload).filePath(QString::fromLatin1(PJ::LocalizedPluginSeed::kMarker)));
  require(marker.open(QIODevice::WriteOnly), QStringLiteral("Cannot write fixture marker"));
  const QByteArray marker_bytes = QJsonDocument(object).toJson();
  require(marker.write(marker_bytes) == marker_bytes.size(), QStringLiteral("Cannot complete fixture marker"));
  marker.close();

  const auto check_catalog = [&](const PJ::ExtensionCatalogService::Paths& roots) {
    PJ::ExtensionCatalogService catalog(roots, {});
    const QString store = catalog.extensionManager().extensionsDir();
    require(
        store == PJ::PlatformUtils::extensionsDir() && inside(profile, store),
        QStringLiteral("Discovery override redirected the managed store"));
    require(
        catalog.extensionManager().hasStoreWriteAccess(), QStringLiteral("Isolated store could not acquire its lease"));
    const auto layout = PJ::StoreLayout::create(store);
    require(layout.has_value(), QStringLiteral("Cannot create the production store layout"));
    for (const QString& path :
         {layout->storeRoot(), layout->artifactsRoot(), layout->extractionRoot(), layout->profilesRoot(),
          PJ::storeLockPath(layout->storeRoot()), PJ::PlatformUtils::pendingDir(), PJ::PlatformUtils::backupDir()}) {
      require(inside(profile, path), QStringLiteral("Marketplace lifecycle path escaped: %1").arg(path));
    }
    const QString installed_dso = QDir(store).filePath(id + '/' + filename);
    require(
        PJ::LocalizedPluginSeed::fileHash(installed_dso) == hash,
        QStringLiteral("Unicode bundled plugin was not seeded with identical bytes"));
    const QString key = PJ::LocalizedPluginSeed::receiptKey(store, id, version);
    QSettings settings;
    require(
        settings.value(key + QStringLiteral("/applied")).toString() == hash &&
            !settings.contains(key + QStringLiteral("/pending")),
        QStringLiteral("Unicode seed receipt was not committed to the isolated settings"));
    const auto& plugins = catalog.dataSources();
    require(
        std::any_of(plugins.begin(), plugins.end(), [](const auto& plugin) { return plugin.id == "mock-data-source"; }),
        QStringLiteral("Real fixture plugin was not loaded from the Unicode store"));
  };
  check_catalog(paths);  // --plugin-dir does not disable seeding or relocate the managed store.
  paths.install_dir.clear();
  check_catalog(paths);  // A subsequent default-mode startup uses the same receipt and bytes.
}

/// Real parser DSOs exercise native loading and the shipped-signature trust
/// boundary. Removing the shipped reference must remove the provenance advantage.
void checkParserProvenance(const QString& profile) {
  const QString bundled = profile + QStringLiteral("/随包 parser-fixture");
  const QString absent = profile + QStringLiteral("/无随包 parser-fixture");
  require(QDir().mkpath(bundled) && QDir().mkpath(absent), QStringLiteral("Cannot create parser fixture roots"));
  const auto place = [](const QString& root, const QString& id, const char* original) {
    const QString directory = QDir(root).filePath(id);
    require(QDir().mkpath(directory), QStringLiteral("Cannot create parser payload"));
    const QString source = QString::fromUtf8(original);
    require(
        QFile::copy(source, QDir(directory).filePath(QFileInfo(source).fileName())),
        QStringLiteral("Cannot copy native parser fixture"));
  };
  place(bundled, QStringLiteral("zzz-profile-bundled"), PJ_PROFILE_BUNDLED_PARSER_PATH);
  place(
      PJ::PlatformUtils::extensionsDir(), QStringLiteral("aaa-profile-marketplace"),
      PJ_PROFILE_MARKETPLACE_PARSER_PATH);
  const auto winner = [](const QString& shipped) {
    PJ::ExtensionCatalogService::Paths paths;
    paths.bundled_dir = shipped;
    PJ::ExtensionCatalogService catalog(paths, {});
    require(catalog.messageParsers().size() == 2, QStringLiteral("Both real Unicode parser DSOs must load"));
    const auto selection = catalog.resolveParserRoutes("json", "profile/Message", {}, "{}");
    require(selection.route_dispatch && selection.scalar.has_value(), QStringLiteral("No registered scalar route"));
    return selection.scalar->provider_id;
  };
  require(winner(bundled) == "zzz-profile-bundled", QStringLiteral("Unicode bundled parser lost shipped provenance"));
  require(winner(absent) == "aaa-profile-marketplace", QStringLiteral("Unshipped parser retained bundled provenance"));
}

}  // namespace

int main(int argc, char* argv[]) {
  QCoreApplication app(argc, argv);
  QCoreApplication::setOrganizationName(QStringLiteral("PlotJuggler"));
  QCoreApplication::setApplicationName(QStringLiteral("PlotJuggler4"));
  if (app.arguments().size() != 2) {
    return 64;
  }
  const char* stage = "profile initialization";
  try {
    const QString dedicated = app.arguments()[1];
    require(QDir().mkpath(dedicated), QStringLiteral("Cannot prepare dedicated test directory"));
    QTemporaryDir run(QDir(dedicated).filePath(QStringLiteral("RuntimeServices-XXXXXX")));
    require(run.isValid(), QStringLiteral("Cannot prepare isolated runtime test"));
    run.setAutoRemove(false);
    QString error;
    require(PJ::PlatformUtils::initializeProfile(run.filePath(QStringLiteral("独立 profile")), &error), error);
    const QString profile = PJ::PlatformUtils::profileDir();
    PJ::QSettingsBackend backend;
    backend.setString("profile/host-backend", "isolated");
    require(
        QSettings().value(QStringLiteral("profile/host-backend")).toString() == QStringLiteral("isolated"),
        QStringLiteral("Plugin host settings backend does not use the isolated INI"));
    stage = "recording and source cache";
    checkCaptureServices(profile, run.filePath(QStringLiteral("forbidden-override")));
    stage = "marketplace seeding and runtime catalog";
    checkMarketplace(profile);
    stage = "Unicode parser provenance";
    checkParserProvenance(profile);
#ifdef PJ_PROFILE_WITH_URDF
    stage = "embedded URDF extraction";
    QString asset;
    {
      pj::scene3d::UrdfPackageResolver resolver;
      resolver.setEmbeddedAssets({{QStringLiteral("package://fixture/mesh.stl"), QByteArray("embedded model")}});
      const auto resolved = resolver.resolveUri("package://fixture/mesh.stl", "", false);
      asset = QString::fromStdString(resolved.path);
      require(
          resolved.resolved && inside(profile, asset) && QFileInfo::exists(asset),
          QStringLiteral("Actual embedded URDF extraction escaped the profile"));
    }
    require(!QFileInfo::exists(asset), QStringLiteral("Embedded URDF temporary file was not removed"));
#endif
    QSettings().sync();
    std::printf("[app-profile-services] PASS; test data: %s\n", qPrintable(run.path()));
    return 0;
  } catch (const std::exception& error) {
    std::fprintf(stderr, "[app-profile-services] FAIL (%s): %s\n", stage, error.what());
    return 1;
  }
}
