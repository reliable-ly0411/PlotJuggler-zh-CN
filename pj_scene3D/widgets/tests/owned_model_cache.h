// SPDX-License-Identifier: MPL-2.0
#pragma once

#include "../../../cmake/test_mains/pj_test_owned_directory.h"

namespace pj_scene3d_test {

// Both model-fetch environments share one validated fixture; registration order
// must not replace the cache path with an unrelated environment's temporary dir.
inline PjTestOwnedDirectory& modelCacheRoot() {
  static PjTestOwnedDirectory root;
  return root;
}

inline QString modelCachePath() {
  return modelCacheRoot().path() + QStringLiteral("/models");
}

inline void installModelCache() {
  auto& root = modelCacheRoot();
  if (!root.ownsTree() || !QDir().mkpath(modelCachePath()) || !root.ownsTree()) {
    qFatal("Cannot prepare private model cache");
  }
  qputenv("PJ_MODEL_CACHE_DIR", modelCachePath().toUtf8());
}

inline bool clearModelCache() {
  auto& root = modelCacheRoot();
  if (qEnvironmentVariable("PJ_MODEL_CACHE_DIR") != modelCachePath() || !root.ownsTree()) {
    return false;
  }
  const QString path = modelCachePath();
  return !QFileInfo::exists(path) || QDir(path).removeRecursively();
}

}  // namespace pj_scene3d_test
