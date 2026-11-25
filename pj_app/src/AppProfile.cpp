// SPDX-License-Identifier: MPL-2.0
#include "AppProfile.h"

#include "pj_marketplace/platform_utils.hpp"

namespace PJ {

bool initializeAppProfile(const QStringList& arguments, QString* error) {
  QString directory;
  bool seen = false;
  for (qsizetype index = 1; index < arguments.size(); ++index) {
    const QString& argument = arguments[index];
    if (argument == QStringLiteral("--")) {
      break;
    }
    if (argument != QStringLiteral("--profile-dir") && !argument.startsWith(QStringLiteral("--profile-dir="))) {
      continue;
    }
    if (seen) {
      if (error != nullptr) {
        *error = QStringLiteral("Specify --profile-dir only once");
      }
      return false;
    }
    seen = true;
    if (argument == QStringLiteral("--profile-dir")) {
      if (index + 1 >= arguments.size() || arguments[index + 1].startsWith('-')) {
        if (error != nullptr) {
          *error = QStringLiteral("--profile-dir requires an absolute directory");
        }
        return false;
      }
      directory = arguments[++index];
    } else {
      directory = argument.sliced(QStringLiteral("--profile-dir=").size());
    }
  }
  return !seen || PlatformUtils::initializeProfile(directory, error);
}

}  // namespace PJ
