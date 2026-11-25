#pragma once
// Copyright 2026 PlotJuggler Chinese localization contributors
// SPDX-License-Identifier: MIT
#include <QByteArray>
#include <QString>
#include <functional>
#include <optional>
class QWidget;
class QComboBox;
namespace PJ {
// Presentation-only scope: exact pinned UI bytes, never plugin-controlled IDs.
inline constexpr auto kBundledUiScope = "_pj_bundled_ui_sha256";
inline constexpr int kCanonicalComboTextRole = 0x0100 + 729;
QByteArray localizeBundledUi(const QByteArray& ui, QByteArray* scope);
void initializeBundledWidgets(QWidget* root, const QByteArray& original, const QByteArray& scope);
/// Read a control state from the same plugin update, never from stale painted widgets.
using BundledEnabledLookup = std::function<std::optional<bool>(const char*)>;
QString bundledDisplayText(
    const QWidget* widget, const char* property, const QString& source, const BundledEnabledLookup& enabled = {});
QString bundledNamedDisplayText(
    const QWidget* root, const QString& objectName, const char* property, const QString& source);
QString bundledPluginMessage(const QString& id, const QString& version, const QString& source);
QString canonicalComboText(const QComboBox* combo, int index);
}  // namespace PJ
