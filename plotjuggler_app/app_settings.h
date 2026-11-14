// SPDX-License-Identifier: MPL-2.0
#pragma once
class QApplication;
// Retain the legacy 3.x identity; never import or overwrite another installation's settings.
bool configureApplicationSettings(const QApplication& app);
