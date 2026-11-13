#pragma once
// Copyright 2026 Davide Faconti
// SPDX-License-Identifier: MPL-2.0

// Test support: an ExtensionCatalogService whose marketplace and bundled roots
// live in a private temp dir. The marketplace dir is always a scan tier and
// seeding runs in every mode, so a test that constructed the service with only
// an explicit plugin dir would otherwise scan — and seed into — the real user
// profile.

#include <utility>

#include "../../cmake/test_mains/pj_test_owned_directory.h"
#include "pj_runtime/ExtensionCatalogService.h"

namespace PJ::test {

struct HermeticCatalog {
  explicit HermeticCatalog(const QString& install_dir) : service(paths(install_dir), DiagnosticSink{}, nullptr) {}

  explicit HermeticCatalog(StaticPluginSet static_plugins, DiagnosticSink sink = {})
      : service(paths(QString()), std::move(sink), std::move(static_plugins), nullptr) {}

  // Parent outlives service. Store siblings (.artifacts/.extraction/.profiles,
  // .install_stage/.seed_stage) are children of this parent, not its siblings.
  PjTestOwnedDirectory sandbox;
  ExtensionCatalogService service;

 private:
  ExtensionCatalogService::Paths paths(const QString& install_dir) {
    if (!sandbox.ownsTree() || !QDir(sandbox.path()).mkdir(QStringLiteral("marketplace")) || !sandbox.ownsTree()) {
      qFatal("Cannot prepare owned hermetic catalog before service construction");
    }
    return {install_dir, sandbox.path() + "/marketplace", sandbox.path() + "/no_bundled"};
  }
};

}  // namespace PJ::test
