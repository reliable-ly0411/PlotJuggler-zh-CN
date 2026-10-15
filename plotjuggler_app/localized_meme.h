// SPDX-License-Identifier: MPL-2.0
#pragma once
#include <QPixmap>
#include <QString>

QPixmap localizedMeme(int index, bool chinese, bool* text_fits = nullptr);
bool exportLocalizedMemes(const QString& directory, bool chinese);
