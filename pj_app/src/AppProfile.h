// SPDX-License-Identifier: MPL-2.0
#pragma once

#include <QString>
#include <QStringList>

namespace PJ {

// Pre-parse the native-only isolation option before installing WidgetTuner or
// constructing any app-owned QSettings/service. Other options remain for the
// main CLI parser. No option means no changes to settings or path defaults.
[[nodiscard]] bool initializeAppProfile(const QStringList& arguments, QString* error);

}  // namespace PJ
