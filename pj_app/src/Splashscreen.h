// Copyright 2026 Davide Faconti
// SPDX-License-Identifier: MPL-2.0
#pragma once

#include <QPixmap>
#include <QString>
#include <QStringList>

class QSettings;

namespace PJ {

// Persisted QSettings key and values.
inline const QString kSplashModeKey = QStringLiteral("Preferences::splash_mode");
inline const QString kSplashModeMemes = QStringLiteral("memes");
inline const QString kSplashModeSerious = QStringLiteral("serious");

// Pixels, along either axis: the pool mixes landscape and portrait art, and screen height is the scarcer one.
inline constexpr int kMaxMemeExtent = 600;

// Keeps the aspect ratio and never upscales, which scaled(..., Qt::KeepAspectRatio) alone would.
QPixmap capMemeToSplashBox(const QPixmap& pixmap);

// Read at startup without rewriting an explicit preference, in every language.
QString startupSplashMode(const QSettings& settings);

// Translate afresh for each call, never cache strings across translator lifetimes.
QStringList seriousSplashSubtitles();

// Paired captions for the text-free two-panel meme compositions, translated afresh.
QStringList localizedMemeCaptions();

// Simplified Chinese: reviewed raster variants plus eight compositions.
// Traditional Chinese: the eight captioned, text-free-artwork compositions only.
QStringList chineseMemeIds();
QPixmap chineseMemePixmap(const QString& id);

// Deterministic composition entry point for pixel/translation regression tests.
QPixmap localizedMemeForTest(int index);

// Builds the startup splash pixmap honouring Preferences::splash_mode:
// "serious" → a composed branded banner (logo + wordmark + random subtitle),
// Otherwise use a localized meme composition or an English bundled meme, falling back
// to the serious banner if no image can be loaded.
QPixmap makeStartupSplash();

}  // namespace PJ
