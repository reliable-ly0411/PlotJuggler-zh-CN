// SPDX-License-Identifier: MPL-2.0
#pragma once

#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QTemporaryDir>
#include <QUuid>
#include <cstdio>
#include <cstdlib>

// A fresh test-owned tree. Never delete through a changed root or a link/junction;
// refusal intentionally leaves this run's evidence instead of risking other data.
class PjTestOwnedDirectory {
 public:
  enum class Cleanup { Immediate, AfterChildExit };

  // AfterChildExit is reserved for fixtures whose DLLs stay mapped until exit.
  explicit PjTestOwnedDirectory(Cleanup cleanup = Cleanup::Immediate)
      : cleanup_(cleanup), directory_(allocationParent(cleanup) + QStringLiteral("/pj-native-fixture-XXXXXX")) {
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

  const QByteArray& ownershipToken() const {
    return token_;
  }

  static bool validParentLease() {
    const QString root = QString::fromUtf8(qgetenv("PJ_TEST_PARENT_TREE"));
    const QByteArray token = qgetenv("PJ_TEST_PARENT_TOKEN");
    if (root.isEmpty() || token.isEmpty() || !plainDirectory(root)) {
      return false;
    }
    const QFileInfo info(root + QStringLiteral("/.pj-test-owner"));
    if (!info.isFile() || info.isSymbolicLink() || info.isJunction()) {
      return false;
    }
    QFile marker(info.filePath());
    return marker.open(QIODevice::ReadOnly) && marker.readAll() == token;
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
    const bool deferred = cleanup_ == Cleanup::AfterChildExit;
    if (!ownsTree() || (deferred && !validParentLease()) || (!deferred && !QDir(root_).removeRecursively())) {
      std::fprintf(stderr, "Refusing unsafe or failed private test directory cleanup: %s\n", qPrintable(root_));
      std::fflush(stderr);
      std::_Exit(EXIT_FAILURE);
    }
  }

 private:
  static QString allocationParent(Cleanup cleanup) {
    if (cleanup == Cleanup::Immediate) {
      return temporaryParent();
    }
    if (!validParentLease()) {
      qFatal("No verified parent for process-lifetime test fixture");
    }
    return QString::fromUtf8(qgetenv("PJ_TEST_PARENT_TREE"));
  }

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

  Cleanup cleanup_;
  QTemporaryDir directory_;
  QString root_;
  QByteArray token_;
};
