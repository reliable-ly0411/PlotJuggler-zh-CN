// SPDX-License-Identifier: MPL-2.0
#pragma once
class QApplication;
/// Install the selected Qt translators before constructing any application widget.
void installApplicationLanguage(QApplication& app);
