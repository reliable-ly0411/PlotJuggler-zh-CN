// SPDX-License-Identifier: MPL-2.0
#pragma once

#include <QCoreApplication>
#include <QProcess>
#include <QProcessEnvironment>
#include <optional>

#include "pj_test_owned_directory.h"

// Only the parent owns cleanup. Its child can keep widget images mapped, while
// crashes/timeouts still fail and ownership/link checks remain fail-closed.
inline std::optional<int> pjRunWithChildCleanup(int argc, char** argv, int timeout_ms = 110000) {
  if (qEnvironmentVariableIsSet("PJ_TEST_PARENT_TREE") || qEnvironmentVariableIsSet("PJ_TEST_PARENT_TOKEN")) {
    if (!PjTestOwnedDirectory::validParentLease()) {
      return EXIT_FAILURE;
    }
    return std::nullopt;
  }
  bool filtered = false;
  for (int i = 1; i < argc; ++i) {
    if (QByteArray(argv[i]).startsWith("--gtest_filter=")) {
      filtered = true;
    }
  }
  // Let gtest interpret repeated flags and discovery options in the child.
  // Every invocation of this dedicated runner has the same ownership contract.
  QCoreApplication app(argc, argv);
  PjTestOwnedDirectory parent;
  QProcess child;
  auto environment = QProcessEnvironment::systemEnvironment();
  environment.insert("PJ_TEST_PARENT_TREE", parent.path());
  environment.insert("PJ_TEST_PARENT_TOKEN", QString::fromUtf8(parent.ownershipToken()));
  child.setProcessEnvironment(environment);
  child.setProcessChannelMode(QProcess::ForwardedChannels);
  child.start(QCoreApplication::applicationFilePath(), QCoreApplication::arguments().mid(1));
  if (!child.waitForStarted()) {
    return EXIT_FAILURE;
  }
  // CTest has a 120-second case timeout; leave time for verified parent cleanup.
  if (!child.waitForFinished(filtered ? timeout_ms : -1)) {
    child.kill();
    child.waitForFinished(-1);
    std::fprintf(stderr, "Pinned widget test child timed out; cleaning after process exit\n");
    return EXIT_FAILURE;
  }
  if (child.exitStatus() != QProcess::NormalExit) {
    return EXIT_FAILURE;
  }
  return child.exitCode() == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
