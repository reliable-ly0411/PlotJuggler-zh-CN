// SPDX-License-Identifier: MPL-2.0
#pragma once

#include <QCryptographicHash>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QSettings>
#include <QStringList>
#include <filesystem>
#include <optional>
#include <system_error>

namespace PJ::LocalizedPluginSeed {
inline constexpr auto kMarker = ".pj-localized-build.json";

// Binds a localized payload to exact bytes, not an upstream semantic version.
struct Build {
  QString sha256;
  QStringList legacy_sha256;
};

enum class Decision { Preserve, AlreadyCurrent, Migrate };

// A receipt survives marketplace replacement. A pending transaction fails closed
// after interruption, unless the installed bytes prove promotion completed.
inline Decision decide(const Build& build, const QString& installed_hash, const QString& receipt, bool pending) {
  if (installed_hash == build.sha256) {
    return Decision::AlreadyCurrent;
  }
  if (pending || installed_hash.isEmpty()) {
    return Decision::Preserve;
  }
  if (!receipt.isEmpty()) {
    return installed_hash == receipt ? Decision::Migrate : Decision::Preserve;
  }
  return build.legacy_sha256.contains(installed_hash) ? Decision::Migrate : Decision::Preserve;
}

// Empty means missing/unreadable; callers never interpret that as trusted identity.
inline QString fileHash(const QString& path) {
  QFile file(path);
  if (!file.open(QIODevice::ReadOnly)) {
    return {};
  }
  QCryptographicHash hash(QCryptographicHash::Sha256);
  if (!hash.addData(&file)) {
    return {};
  }
  return QString::fromLatin1(hash.result().toHex());
}

// The marker is only accepted for the descriptor/path the bundled scan selected.
inline std::optional<Build> readBuild(
    const QString& payload, const QString& dso, const QString& id, const QString& version) {
  QFile file(QDir(payload).filePath(QString::fromLatin1(kMarker)));
  if (!file.open(QIODevice::ReadOnly)) {
    return std::nullopt;
  }
  const auto object = QJsonDocument::fromJson(file.readAll()).object();
  if (object.value("schema").toInt() != 1 || object.value("id").toString() != id ||
      object.value("version").toString() != version ||
      object.value("kind").toString() != QStringLiteral("fork-localized-rebuild") ||
      object.value("dso").toString() != QDir(payload).relativeFilePath(dso)) {
    return std::nullopt;
  }
  Build build{object.value("sha256").toString(), {}};
  if (build.sha256.size() != 64 || fileHash(dso) != build.sha256) {
    return std::nullopt;
  }
  for (const auto& value : object.value("legacy_sha256").toArray()) {
    const auto hash = value.toString();
    if (hash.size() == 64) {
      build.legacy_sha256.push_back(hash);
    }
  }
  return build;
}

// Preserve extras before overlaying a same-version package; never traverse user symlinks.
inline std::error_code preserveFiles(const std::filesystem::path& installed, const std::filesystem::path& staged) {
  std::error_code ec;
  if (std::filesystem::is_symlink(installed, ec)) {
    return std::make_error_code(std::errc::operation_not_permitted);
  }
  for (std::filesystem::recursive_directory_iterator it(installed, ec), end; !ec && it != end; it.increment(ec)) {
    if (it->is_symlink(ec)) {
      return std::make_error_code(std::errc::operation_not_permitted);
    }
  }
  if (!ec) {
    std::filesystem::copy(installed, staged, std::filesystem::copy_options::recursive, ec);
  }
  return ec;
}

// Scope receipts to this store and plugin version, including portable/test stores.
inline QString receiptKey(const QString& store, const QString& id, const QString& version) {
  const auto identity = (QDir(store).absolutePath() + '\n' + id + '\n' + version).toUtf8();
  return QStringLiteral("LocalizedPluginSeeds/") +
         QString::fromLatin1(QCryptographicHash::hash(identity, QCryptographicHash::Sha256).toHex());
}

// Persist intent before mutation. If a later sync fails, an outstanding intent
// prevents a user-selected replacement from being mistaken for an unprocessed legacy build.
inline bool begin(QSettings& settings, const QString& key, const QString& target) {
  settings.setValue(key + QStringLiteral("/pending"), target);
  settings.sync();
  return settings.status() == QSettings::NoError;
}

// Called only after successful promotion or a byte-identical installed payload.
inline bool complete(QSettings& settings, const QString& key, const QString& target) {
  settings.setValue(key + QStringLiteral("/applied"), target);
  settings.remove(key + QStringLiteral("/pending"));
  settings.sync();
  return settings.status() == QSettings::NoError;
}

// An explicit failed promotion rolled back, so a subsequent launch may retry.
inline void failed(QSettings& settings, const QString& key) {
  settings.remove(key + QStringLiteral("/pending"));
  settings.sync();
}
}  // namespace PJ::LocalizedPluginSeed
