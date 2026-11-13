// SPDX-License-Identifier: MPL-2.0
#pragma once
#include <QStringList>
struct LauncherAcceptance {
  bool enabled = false;
  QString output, scenario;
};
bool parseLauncherAcceptance(const QStringList& args, LauncherAcceptance& test, QStringList& forwarded);
