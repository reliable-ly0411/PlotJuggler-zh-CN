// SPDX-License-Identifier: MPL-2.0
#pragma once

#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QTemporaryDir>
#include <QUuid>
#include <cstdlib>

// A fresh test-owned tree. Never delete through a changed root or a link/junction;
// refusal intentionally leaves this run's evidence instead of risking other data.
class PjTestOwnedDirectory {
 public:
  PjTestOwnedDirectory() : directory_(temporaryParent() + QStringLiteral("/pj-native-fixture-XXXXXX")) {
    directory_.setAutoRemove(false);
    if (!directory_.isValid()) {
      qFatal("Cannot create private test directory");
    }
    root_ = QFileInfo(directory_.path()).canonicalFilePath();
    token_ = QUuid::createUuid().toByteArray();
    QFile marker(root_ + QStringLiteral("/.pj-test-owner"));
    if (!plainDirectory(root_) || !marker.open(QIODevice::WriteOnly | QIODevice::NewOnly) ||
        marker.write(token_) != token_.size() || !marker.flush()) {
      qFatal("Cannot establish private test directory ownership");
    }
  }

  PjTestOwnedDirectory(const PjTestOwnedDirectory&) = delete;
  PjTestOwnedDirectory& operator=(const PjTestOwnedDirectory&) = delete;

  const QString& path() const {
    return root_;
  }

  // Check the owned root and every entry before recursive cleanup. The tests are
  // single-writer; this is not protection against a hostile concurrent filesystem.
  bool ownsTree() const {
    if (root_.isEmpty() || directory_.path() != root_ || !plainDirectory(root_)) {
      return false;
    }
    return hasOwnershipMarker() && safeTree(root_);
  }

  // Delete only a canonical descendant, never an empty/relative/default path.
  bool removeChildTree(const QString& path) const {
    if (!plainDirectory(root_) || !hasOwnershipMarker() || path.isEmpty() || !QDir::isAbsolutePath(path) ||
        !QDir::cleanPath(path).startsWith(root_ + '/')) {
      return false;
    }
    const QFileInfo info(path);
    if (!info.exists()) {
      return !info.isSymbolicLink() && !info.isJunction() && plainDirectory(info.dir().absolutePath());
    }
    return plainDirectory(path) && safeTree(path) && QDir(path).removeRecursively();
  }

  ~PjTestOwnedDirectory() {
    if (!ownsTree() || !QDir(root_).removeRecursively()) {
      qCritical("Refusing unsafe or failed private test directory cleanup");
      std::_Exit(EXIT_FAILURE);
    }
  }

 private:
  bool hasOwnershipMarker() const {
    const QFileInfo info(root_ + QStringLiteral("/.pj-test-owner"));
    if (info.isSymbolicLink() || info.isJunction()) {
      return false;
    }
    QFile marker(info.filePath());
    return marker.open(QIODevice::ReadOnly) && marker.readAll() == token_;
  }

  // Resolve the OS temp location before allocating; reject unresolved parents.
  static QString temporaryParent() {
    const QString parent = QDir(QDir::tempPath()).canonicalPath();
    if (parent.isEmpty() || !plainDirectory(parent)) {
      qFatal("No usable canonical parent for private test directory");
    }
    return parent;
  }

  static bool plainDirectory(const QString& path) {
    for (QString current = path;;) {
      const QFileInfo info(current);
      if (!info.isDir() || info.isSymbolicLink() || info.isJunction() || info.canonicalFilePath() != current) {
        return false;
      }
      const QString parent = info.dir().absolutePath();
      if (parent == current) {
        return true;
      }
      current = parent;
    }
  }

  static bool safeTree(const QString& path) {
    const auto entries =
        QDir(path).entryInfoList(QDir::AllEntries | QDir::NoDotAndDotDot | QDir::Hidden | QDir::System);
    for (const QFileInfo& entry : entries) {
      if (entry.isSymbolicLink() || entry.isJunction() || entry.canonicalFilePath() != entry.absoluteFilePath()) {
        return false;
      }
      if (entry.isDir() && !safeTree(entry.absoluteFilePath())) {
        return false;
      }
    }
    return true;
  }

  QTemporaryDir directory_;
  QString root_;
  QByteArray token_;
};
