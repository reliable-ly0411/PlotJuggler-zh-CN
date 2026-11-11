// SPDX-License-Identifier: MPL-2.0
#pragma once
#include <QString>
class QApplication;
QString normalizedApplicationLanguage(QString language);
QString selectedApplicationLanguage(const QApplication& app);
/// Install the selected Qt translators before constructing any application widget.
void installApplicationLanguage(QApplication& app);
