// SPDX-License-Identifier: MPL-2.0
#pragma once
#include <QStringList>
class QDialog;
struct LauncherAcceptance {
  bool enabled = false;
  QString output, scenario, target;
};
bool parseLauncherAcceptance(const QStringList& args, LauncherAcceptance& test, QStringList& forwarded);
void driveLauncherAcceptance(QDialog* dialog, const LauncherAcceptance& test);
