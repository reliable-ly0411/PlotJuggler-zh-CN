// SPDX-License-Identifier: MPL-2.0
#pragma once

#include <QImage>
#include <QJsonObject>
#include <QString>

namespace PJ
{
// Files are relative to root; no locale or plugin is assumed. Invalid variants
// return the original atomically and set ok to false. An empty description is
// a successful, intentional original-image fallback.
QImage resourceImageVariant(const QImage& original, const QJsonObject& description,
                            const QString& root, bool* ok = nullptr,
                            QString* error = nullptr);
}  // namespace PJ
