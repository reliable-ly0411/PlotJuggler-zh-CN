// Copyright 2026 Davide Faconti
// SPDX-License-Identifier: MPL-2.0

#include <gtest/gtest.h>

#include "pj_runtime/UpdateVersion.h"

using PJ::isNewerVersion;
using PJ::versionToComparable;

namespace {

TEST(UpdateVersionTest, ParsesFullSemver) {
  EXPECT_EQ(versionToComparable("4.0.0"), 4'000'000);
  EXPECT_EQ(versionToComparable("3.999.0"), 3'999'000);
  EXPECT_EQ(versionToComparable("3.999.1"), 3'999'001);
  EXPECT_EQ(versionToComparable("0.0.0"), 0);
}

TEST(UpdateVersionTest, StripsLeadingV) {
  EXPECT_EQ(versionToComparable("v4.0.1"), versionToComparable("4.0.1"));
  EXPECT_EQ(versionToComparable("V3.999.0"), versionToComparable("3.999.0"));
}

TEST(UpdateVersionTest, IgnoresPreReleaseAndBuildSuffix) {
  EXPECT_EQ(versionToComparable("4.0.0-dev"), versionToComparable("4.0.0"));
  EXPECT_EQ(versionToComparable("4.0.0-rc1"), versionToComparable("4.0.0"));
  EXPECT_EQ(versionToComparable("4.0.0+build.7"), versionToComparable("4.0.0"));
  EXPECT_EQ(versionToComparable("v3.999.0-beta"), versionToComparable("3.999.0"));
}

TEST(UpdateVersionTest, PadsMissingComponents) {
  EXPECT_EQ(versionToComparable("4"), versionToComparable("4.0.0"));
  EXPECT_EQ(versionToComparable("4.1"), versionToComparable("4.1.0"));
}

TEST(UpdateVersionTest, ReturnsNegativeOnGarbage) {
  EXPECT_LT(versionToComparable(""), 0);
  EXPECT_LT(versionToComparable("   "), 0);
  EXPECT_LT(versionToComparable("dev"), 0);
  EXPECT_LT(versionToComparable("latest"), 0);
  EXPECT_LT(versionToComparable("4.x.0"), 0);
}

TEST(UpdateVersionTest, RejectsComponentThatWouldOverflowField) {
  EXPECT_EQ(versionToComparable("4.999.999"), 4'999'999);  // max in-range
  EXPECT_LT(versionToComparable("4.1000.0"), 0);           // minor overflows its field
  EXPECT_LT(versionToComparable("4.0.1000"), 0);           // patch overflows its field
}

TEST(UpdateVersionTest, OrdersAcrossComponents) {
  EXPECT_GT(versionToComparable("4.0.0"), versionToComparable("3.999.0"));
  EXPECT_GT(versionToComparable("4.1.0"), versionToComparable("4.0.99"));
  EXPECT_GT(versionToComparable("4.0.2"), versionToComparable("4.0.1"));
}

TEST(UpdateVersionTest, IsNewerVersionComparesStrictly) {
  EXPECT_TRUE(isNewerVersion("4.0.0", "3.999.0"));
  EXPECT_TRUE(isNewerVersion("v4.0.0", "3.999.0"));
  EXPECT_FALSE(isNewerVersion("3.999.0", "3.999.0"));  // equal is not newer
  EXPECT_FALSE(isNewerVersion("3.998.0", "3.999.0"));  // older
}

// A malformed tag (either side) must never be treated as an available update.
TEST(UpdateVersionTest, IsNewerVersionRejectsUnparseable) {
  EXPECT_FALSE(isNewerVersion("garbage", "3.999.0"));
  EXPECT_FALSE(isNewerVersion("4.0.0", "garbage"));
  EXPECT_FALSE(isNewerVersion("", ""));
}

TEST(UpdateVersionTest, LocalizedStableIdentityAndPrecedence) {
  EXPECT_TRUE(PJ::isLocalizedBuildVersion("4.1.0+zh.1"));
  EXPECT_TRUE(PJ::isLocalizedBuildVersion("4.1.0-zh.1.dev.1"));
  EXPECT_FALSE(PJ::isLocalizedBuildVersion("4.1.0"));
  EXPECT_FALSE(PJ::isLocalizedBuildVersion("4.1.0+other.zh.1"));
  EXPECT_FALSE(PJ::isLocalizedBuildVersion("4.01.0+zh.1"));
  EXPECT_TRUE(PJ::isStableLocalizedVersion("4.1.0+zh.1"));
  EXPECT_FALSE(PJ::isStableLocalizedVersion("4.1.0-zh.1"));
  EXPECT_TRUE(PJ::isNewerLocalizedVersion("v4.1.0+zh.1", "4.1.0-zh.99.rc.100"));
  EXPECT_TRUE(PJ::isNewerLocalizedVersion("4.1.0+zh.1", "4.1.0-zh.1"));
  EXPECT_FALSE(PJ::isNewerLocalizedVersion("4.1.0-zh.2.rc.1", "4.1.0+zh.1"));
  EXPECT_FALSE(PJ::isNewerLocalizedVersion("4.1.0+zh.2", "4.1.0+zh.1"));
  EXPECT_FALSE(PJ::isNewerLocalizedVersion("4.1.0+zh.1", "4.1.0+zh.2"));
  EXPECT_TRUE(PJ::isNewerLocalizedVersion("4.1.1+zh.1", "4.1.0+zh.1"));
  EXPECT_FALSE(PJ::isNewerLocalizedVersion("5.0.0+zh.1", "4.1.0+zh.1"));
  EXPECT_FALSE(PJ::isNewerLocalizedVersion("4.1.0-zh.1.dev.2", "4.0.0-zh.1.rc.4"));
  EXPECT_FALSE(PJ::isNewerLocalizedVersion("4.2.0+zh.999999999999999999999", "4.1.0+zh.1"));
  EXPECT_TRUE(PJ::isNewerLocalizedVersion("4.0.0-zh.1.rc.10", "4.0.0-zh.1.rc.9"));
  EXPECT_TRUE(PJ::isNewerLocalizedVersion("4.0.0-zh.2.rc.1", "4.0.0-zh.1"));
}

}  // namespace
