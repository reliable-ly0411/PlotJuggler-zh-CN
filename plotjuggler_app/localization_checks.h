// SPDX-License-Identifier: MPL-2.0
#pragma once
#include <QJsonObject>
#include <QString>
class QMainWindow;
QJsonObject checkLocalizedUi(QMainWindow* window, const QString& output, bool chinese);
