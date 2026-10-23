// Copyright 2026 Davide Faconti
// SPDX-License-Identifier: MPL-2.0

#include "Splashscreen.h"

#include <QApplication>
#include <QColor>
#include <QDir>
#include <QFont>
#include <QFontMetricsF>
#include <QLinearGradient>
#include <QPainter>
#include <QRandomGenerator>
#include <QRectF>
#include <QSettings>
#include <QSize>
#include <QStringList>
#include <QSvgRenderer>
#include <Qt>
#include <algorithm>

#include "LocalizedOriginalMeme.h"
#include "pj_widgets/FrameworkTokens.h"
using namespace Qt::StringLiterals;

namespace PJ {
namespace {

// Text-free artwork already shipped by the application. Captions are composed
// as meme panels, not painted over the English raster meme pool.
QPixmap makeLocalizedMeme(int index) {
  const QStringList captions = localizedMemeCaptions();
  const qsizetype pair = (qMax(0, index) % (captions.size() / 2)) * 2;
  const qreal dpr = qMax(1.0, qApp->devicePixelRatio());
  QPixmap pixmap(QSize(600, 390) * dpr);
  pixmap.setDevicePixelRatio(dpr);
  pixmap.fill(Qt::white);
  QPainter painter(&pixmap);
  painter.setRenderHints(QPainter::Antialiasing | QPainter::TextAntialiasing | QPainter::SmoothPixmapTransform);
  const QPixmap disappointed(u":/resources/crying_cat.png"_s);
  const QPixmap victorious(u":/resources/success_kid.png"_s);
  painter.drawPixmap(QRect(22, 112, 256, 256), disappointed);
  painter.drawPixmap(QRect(322, 112, 256, 256), victorious);
  painter.setPen(Qt::black);
  QFont font;
  font.setPixelSize(24);
  font.setBold(true);
  painter.setFont(font);
  painter.drawText(QRect(18, 12, 264, 92), Qt::AlignCenter | Qt::TextWordWrap, captions.at(pair));
  painter.drawText(QRect(318, 12, 264, 92), Qt::AlignCenter | Qt::TextWordWrap, captions.at(pair + 1));
  return pixmap;
}

// Picks a random "funny meme" from the bundled pool (:/resources/memes),
// avoiding the handful most recently shown (persisted in QSettings) so
// consecutive launches don't repeat until the pool cycles. The pool is
// enumerated at runtime, so adding a meme is a pure resource change — no code
// edit. Returns a null QPixmap when the pool is empty.
QPixmap getFunnySplashscreen() {
  if (QCoreApplication::instance()->property("interfaceLanguage").toString() == "zh_CN"_L1) {
    const QStringList ids = chineseMemeIds();
    if (ids.isEmpty()) {
      return {};
    }
    QSettings settings;
    QStringList recent = settings.value(u"previousLocalizedFunnyMemesList"_s).toStringList();
    const qsizetype avoid_count = std::min<qsizetype>(recent.size(), ids.size() - 1);
    QStringList choices = ids;
    for (const auto& id : recent.mid(recent.size() - avoid_count)) {
      choices.removeAll(id);
    }
    const QString chosen = choices.at(QRandomGenerator::global()->bounded(static_cast<int>(choices.size())));
    recent.append(chosen);
    while (recent.size() > 10) {
      recent.removeFirst();
    }
    settings.setValue(u"previousLocalizedFunnyMemesList"_s, recent);
    return capMemeToSplashBox(chineseMemePixmap(chosen));
  }
  QDir memes_dir(u":/resources/memes"_s);
  const QStringList files = memes_dir.entryList({u"*.jpg"_s}, QDir::Files, QDir::Name);
  if (files.isEmpty()) {
    return {};
  }

  QSettings settings;
  QStringList recent = settings.value(u"previousFunnyMemesList"_s).toStringList();
  // Never block more entries than (pool - 1), otherwise the pick loop below
  // could never find an unseen meme and would spin forever.
  const qsizetype avoid_count = std::min<qsizetype>(recent.size(), files.size() - 1);
  const QStringList avoid = recent.mid(recent.size() - avoid_count);

  QString chosen;
  do {
    chosen = files.at(QRandomGenerator::global()->bounded(static_cast<int>(files.size())));
  } while (avoid.contains(chosen));

  // Keep the 10 most-recent picks (PJ3's history depth).
  recent.append(chosen);
  while (recent.size() > 10) {
    recent.removeFirst();
  }
  settings.setValue(u"previousFunnyMemesList"_s, recent);

  return capMemeToSplashBox(QPixmap(memes_dir.filePath(chosen)));
}

// The pool of subtitles for the "serious" splashscreen; one is picked at random
// each launch.
// Renders the "serious" splashscreen: the PlotJuggler logo + wordmark over
// framework surface and brand-gradient tokens, with a random
// subtitle underneath. Composed with QPainter rather than baked into an image
// so every element stays crisp at any DPI and the subtitle can vary per launch.
QPixmap makeSeriousSplashscreen() {
  constexpr int kW = 720;
  constexpr int kH = 300;
  const qreal dpr = qMax(1.0, qApp->devicePixelRatio());

  QPixmap pixmap(QSize(kW, kH) * dpr);
  pixmap.setDevicePixelRatio(dpr);
  pixmap.fill(Qt::transparent);

  QPainter p(&pixmap);
  p.setRenderHints(QPainter::Antialiasing | QPainter::TextAntialiasing | QPainter::SmoothPixmapTransform);

  const QRectF canvas(0, 0, kW, kH);

  const auto token_theme = theme::themeFor(true);
  const auto brand = theme::gradient(theme::Gradient::Brand, token_theme);

  // Soft framework surface gradient.
  QLinearGradient bg(canvas.topLeft(), canvas.bottomRight());
  bg.setColorAt(0.0, theme::surface(theme::Surface::Backdrop, token_theme));
  bg.setColorAt(1.0, theme::surface(theme::Surface::Backdrop, token_theme));
  p.fillRect(canvas, bg);

  // A thin brand-gradient accent along the bottom edge.
  QLinearGradient accent(canvas.bottomLeft(), canvas.bottomRight());
  accent.setColorAt(0.0, brand.first);
  accent.setColorAt(1.0, brand.second);
  p.fillRect(QRectF(0, kH - 4, kW, 4), accent);

  // Logo, vertically centred on the left.
  constexpr qreal kLogoSize = 156;
  const QRectF logo_rect(56, (kH - kLogoSize) / 2.0, kLogoSize, kLogoSize);
  QSvgRenderer logo(u":/resources/plotjuggler.svg"_s);
  if (logo.isValid()) {
    logo.render(&p, logo_rect);
  }

  const qreal text_x = logo_rect.right() + 44;
  const qreal wordmark_baseline = kH / 2.0 - 18;

  // Wordmark "PlotJuggler": draw the whole word in slate grey, then overdraw the
  // two juggling capitals in the brand colours (P blue, J magenta). The coloured
  // glyphs land exactly on top of the grey ones, so the spacing is identical to
  // a single drawText of the full word.
  QFont wordmark_font;
  wordmark_font.setFamilies({u"Khula"_s, u"Roboto"_s, wordmark_font.defaultFamily()});
  wordmark_font.setPixelSize(76);
  wordmark_font.setWeight(QFont::Thin);  // thinnest available weight, for an airy banner look
  p.setFont(wordmark_font);
  const QString wordmark = u"PlotJuggler"_s;
  const QFontMetricsF wordmark_fm(wordmark_font);
  const qreal wordmark_width = wordmark_fm.horizontalAdvance(wordmark);
  const QColor wordmark_ink = theme::onSurface(theme::Surface::Backdrop, theme::Emphasis::Muted, token_theme);
  p.setPen(wordmark_ink);
  p.drawText(QPointF(text_x, wordmark_baseline), wordmark);
  p.setPen(brand.first);
  p.drawText(QPointF(text_x, wordmark_baseline), QStringLiteral("P"));
  p.setPen(brand.second);
  p.drawText(
      QPointF(text_x + wordmark_fm.horizontalAdvance(QStringLiteral("Plot")), wordmark_baseline), QStringLiteral("J"));

  // Random subtitle, centred horizontally under the wordmark, in the same ink.
  QFont subtitle_font;
  subtitle_font.setFamilies({u"Roboto"_s, subtitle_font.defaultFamily()});
  subtitle_font.setPixelSize(26);
  subtitle_font.setWeight(QFont::Light);  // thin, airy weight to match the banner
  p.setFont(subtitle_font);
  p.setPen(wordmark_ink);
  const QStringList subs = seriousSplashSubtitles();
  const QString subtitle = subs.at(QRandomGenerator::global()->bounded(static_cast<int>(subs.size())));
  const qreal subtitle_width = QFontMetricsF(subtitle_font).horizontalAdvance(subtitle);
  p.drawText(QPointF(text_x + (wordmark_width - subtitle_width) / 2.0, wordmark_baseline + 56), subtitle);

  // Version, small and unobtrusive in the corner.
  QFont version_font;
  version_font.setPixelSize(13);
  p.setFont(version_font);
  p.setPen(theme::onSurface(theme::Surface::Backdrop, theme::Emphasis::Disabled, token_theme));
  p.drawText(
      QRectF(0, kH - 30, kW - 18, 20), Qt::AlignRight | Qt::AlignVCenter, QCoreApplication::applicationVersion());

  p.end();
  return pixmap;
}

}  // namespace

QStringList seriousSplashSubtitles() {
  return {
      QCoreApplication::translate("PJ::Splashscreen", "Now you're plotting"),
      QCoreApplication::translate("PJ::Splashscreen", "The plot thickens"),
      QCoreApplication::translate("PJ::Splashscreen", "Hold my rosbag"),
      QCoreApplication::translate("PJ::Splashscreen", "Make your data confess"),
      QCoreApplication::translate("PJ::Splashscreen", "More than just curves now"),
      QCoreApplication::translate("PJ::Splashscreen", "Better than it has any right to be"),
      QCoreApplication::translate("PJ::Splashscreen", "Objectively the best. Probably."),
      QCoreApplication::translate("PJ::Splashscreen", "Still better than printf"),
      QCoreApplication::translate("PJ::Splashscreen", "Friends don't let friends use printf"),
      QCoreApplication::translate("PJ::Splashscreen", "Lovingly over-engineered"),
      QCoreApplication::translate("PJ::Splashscreen", "Suspiciously good for a free tool"),
      QCoreApplication::translate("PJ::Splashscreen", "Opening PlotJuggler. Again."),
      QCoreApplication::translate("PJ::Splashscreen", "Curves were just the beginning"),
      QCoreApplication::translate("PJ::Splashscreen", "Mostly written by an AI"),
      QCoreApplication::translate("PJ::Splashscreen", "An AI helped. Allegedly."),
  };
}

QStringList localizedMemeCaptions() {
  return {
      QCoreApplication::translate("PJ::Splashscreen", "The bug only happens in production"),
      QCoreApplication::translate("PJ::Splashscreen", "Good thing I recorded the data"),
      QCoreApplication::translate("PJ::Splashscreen", "Staring at ten thousand log lines"),
      QCoreApplication::translate("PJ::Splashscreen", "One plot later: found it"),
      QCoreApplication::translate("PJ::Splashscreen", "It must be the sensor"),
      QCoreApplication::translate("PJ::Splashscreen", "It was milliseconds versus seconds"),
      QCoreApplication::translate("PJ::Splashscreen", "Just one more printf"),
      QCoreApplication::translate("PJ::Splashscreen", "Drag, drop, mystery solved"),
      QCoreApplication::translate("PJ::Splashscreen", "The demo worked yesterday"),
      QCoreApplication::translate("PJ::Splashscreen", "Replay the good recording"),
      QCoreApplication::translate("PJ::Splashscreen", "My signal is all noise"),
      QCoreApplication::translate("PJ::Splashscreen", "FFT: allow me to introduce myself"),
      QCoreApplication::translate("PJ::Splashscreen", "Two curves, two different clocks"),
      QCoreApplication::translate("PJ::Splashscreen", "Time offset to the rescue"),
      QCoreApplication::translate("PJ::Splashscreen", "I forgot to save the layout"),
      QCoreApplication::translate("PJ::Splashscreen", "This time I saved the layout"),
  };
}

QStringList chineseMemeIds() {
  QStringList ids = localizedOriginalMemeIds();
  for (qsizetype i = 0; i < localizedMemeCaptions().size() / 2; ++i) {
    ids.append(u"extra:%1"_s.arg(i));
  }
  return ids;
}

QPixmap chineseMemePixmap(const QString& id) {
  if (!chineseMemeIds().contains(id)) {
    return {};
  }
  if (id.startsWith(u"extra:"_s)) {
    return makeLocalizedMeme(id.mid(6).toInt());
  }
  return localizedOriginalMeme(id.toInt());
}

QPixmap localizedMemeForTest(int index) {
  return makeLocalizedMeme(index);
}

QString startupSplashMode(const QSettings& settings) {
  const QString mode = settings.value(kSplashModeKey, kSplashModeMemes).toString();
  return mode == kSplashModeSerious ? kSplashModeSerious : kSplashModeMemes;
}

QPixmap capMemeToSplashBox(const QPixmap& pixmap) {
  if (pixmap.width() <= kMaxMemeExtent && pixmap.height() <= kMaxMemeExtent) {
    return pixmap;
  }
  return pixmap.scaled(QSize(kMaxMemeExtent, kMaxMemeExtent), Qt::KeepAspectRatio, Qt::SmoothTransformation);
}

QPixmap makeStartupSplash() {
  QSettings settings;
  const QString mode = startupSplashMode(settings);
  return mode == kSplashModeSerious ? makeSeriousSplashscreen() : getFunnySplashscreen();
}

}  // namespace PJ
