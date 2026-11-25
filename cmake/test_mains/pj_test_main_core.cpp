// SPDX-License-Identifier: MPL-2.0
// Shared main() for QCoreApplication test runners (pj_add_test_runner MAIN core).
#include <gtest/gtest.h>

#ifdef PJ_TEST_MANAGED_PROFILE
#include "pj_test_managed_profile.h"
#endif

#include <QCoreApplication>
#include <clocale>

#if defined(Q_OS_WIN) && defined(PJ_TEST_PINNED_WIDGET_FIXTURES)
#include "pj_test_child_cleanup.h"
#endif

#if defined(Q_OS_WIN) && (defined(PJ_TEST_MANAGED_PROFILE) || defined(PJ_TEST_PRIVATE_HKCU))
#include "pj_test_windows_registry.h"
#endif

int main(int argc, char** argv) {
#if defined(Q_OS_WIN) && defined(PJ_TEST_PINNED_WIDGET_FIXTURES)
  if (auto result = pjRunWithChildCleanup(argc, argv)) {
    return *result;
  }
#endif
  ::testing::InitGoogleTest(&argc, argv);
#if defined(Q_OS_WIN) && (defined(PJ_TEST_MANAGED_PROFILE) || defined(PJ_TEST_PRIVATE_HKCU))
  PjTestWindowsRegistry registry;
  if (!registry.initialize()) {
    return EXIT_FAILURE;
  }
#endif
#ifdef PJ_TEST_MANAGED_PROFILE
  PjTestManagedProfile managed_profile;
  if (!managed_profile.initialize()) {
    return EXIT_FAILURE;
  }
#endif
  QCoreApplication app(argc, argv);
  std::setlocale(LC_NUMERIC, "C");  // as pj_app's main(): Luau cannot read "0.5" under a decimal-comma locale
  return RUN_ALL_TESTS();
}
