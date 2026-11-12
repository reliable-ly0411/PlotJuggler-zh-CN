// SPDX-License-Identifier: MPL-2.0
#include <gtest/gtest.h>

#include <QScopeGuard>

#include "../../cmake/test_mains/pj_test_owned_directory.h"

TEST(OwnedTestDirectory, RemovesOnlyItsFreshTree) {
  QString path;
  {
    PjTestOwnedDirectory root;
    path = root.path();
    ASSERT_TRUE(root.ownsTree());
    ASSERT_TRUE(QDir().mkdir(path + QStringLiteral("/child")));
    EXPECT_TRUE(root.removeChildTree(path + QStringLiteral("/child")));
    EXPECT_TRUE(root.removeChildTree(path + QStringLiteral("/child")));
  }
  EXPECT_FALSE(QFileInfo::exists(path));
}

TEST(OwnedTestDirectory, RefusesEmptyRelativeAndOutsidePaths) {
  PjTestOwnedDirectory root;
  PjTestOwnedDirectory outside;
  EXPECT_FALSE(root.removeChildTree(QString()));
  EXPECT_FALSE(root.removeChildTree(QStringLiteral(".install_stage")));
  EXPECT_FALSE(root.removeChildTree(root.path()));
  EXPECT_FALSE(root.removeChildTree(outside.path()));
  EXPECT_TRUE(outside.ownsTree());
}

TEST(OwnedTestDirectory, RefusesChangedOwnershipTokenBeforeDeleting) {
  PjTestOwnedDirectory root;
  const QString child = root.path() + QStringLiteral("/child");
  ASSERT_TRUE(QDir().mkdir(child));
  QFile marker(root.path() + QStringLiteral("/.pj-test-owner"));
  ASSERT_TRUE(marker.open(QIODevice::ReadOnly));
  const QByteArray token = marker.readAll();
  marker.close();
  const auto restore = qScopeGuard([&] {
    if (!marker.open(QIODevice::WriteOnly | QIODevice::Truncate) || marker.write(token) != token.size()) {
      qFatal("Cannot restore owned test marker");
    }
    marker.close();
  });
  ASSERT_TRUE(marker.open(QIODevice::WriteOnly | QIODevice::Truncate));
  ASSERT_EQ(marker.write("not-the-owner"), 13);
  marker.close();
  EXPECT_FALSE(root.ownsTree());
  EXPECT_FALSE(root.removeChildTree(child));
  EXPECT_TRUE(QFileInfo::exists(child));
}
