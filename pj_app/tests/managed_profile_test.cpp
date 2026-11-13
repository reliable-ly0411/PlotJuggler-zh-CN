// SPDX-License-Identifier: MPL-2.0
#include <gtest/gtest.h>

#include <QFileInfo>

#include "pj_marketplace/platform_utils.hpp"
#include "support/isolated_main_window.h"

TEST(ManagedProfile, TwoWindowsShareTheProcessStoreAndDoNotOwnItsLifetime) {
  const QString root = PJ::PlatformUtils::profileDir();
  ASSERT_FALSE(root.isEmpty());
  const QString config = PJ::PlatformUtils::configDir();
  const QString extensions = PJ::PlatformUtils::extensionsDir();
  const QString pending = PJ::PlatformUtils::pendingDir();
  const QString backup = PJ::PlatformUtils::backupDir();
  for (const QString& path : {config, extensions, pending, backup}) {
    ASSERT_TRUE(QFileInfo(path).canonicalFilePath().startsWith(root + '/'));
  }
  {
    pj_app_test::IsolatedMainWindow first;
    {
      pj_app_test::IsolatedMainWindow second;
      EXPECT_EQ(PJ::PlatformUtils::profileDir(), root);
      EXPECT_EQ(PJ::PlatformUtils::extensionsDir(), extensions);
      EXPECT_EQ(PJ::PlatformUtils::pendingDir(), pending);
    }
    EXPECT_TRUE(QFileInfo(root).isDir());
  }
  EXPECT_TRUE(QFileInfo(root).isDir());
  EXPECT_EQ(PJ::PlatformUtils::configDir(), config);
  EXPECT_EQ(PJ::PlatformUtils::backupDir(), backup);
}
