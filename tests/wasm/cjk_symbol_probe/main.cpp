// SPDX-License-Identifier: MPL-2.0
#include <QApplication>
#include <QFontDatabase>
#include <QGlyphRun>
#include <QLabel>
#include <QImage>
#include <QPainter>
#include <QRawFont>
#include <QPainterPath>
#include <QTextLayout>
#include <QTextOption>
#include <QTimer>
#include <QVBoxLayout>
#include <array>
#include "BundledFont.h"
using namespace Qt::StringLiterals;
int main(int argc, char** argv) {
  QApplication app(argc, argv);
#include "setup.inc"
  QWidget window;
  auto* rows = new QVBoxLayout(&window);
  const std::array<QPair<QString, QString>, 2> samples{{
#include "samples.inc"
  }};
  std::array<QLabel*, 2> labels{};
  for (std::size_t i=0; i<labels.size(); ++i) {
    labels[i] = new QLabel(samples[i].second, &window);
    auto font = labels[i]->font();
    font.setPixelSize(25);
    labels[i]->setFont(font);
    labels[i]->setTextFormat(Qt::PlainText);
    rows->addWidget(labels[i]);
  }
  window.resize(650, 150);
  window.show();
  QTimer::singleShot(0, &window, [&] {
    for (std::size_t i=0; i<labels.size(); ++i) {
      const auto* label = labels[i];
      const auto index = label->text().indexOf(QChar(0x25b8));
      QTextLayout layout(label->text(), label->font());
      QTextOption options;
      options.setWrapMode(QTextOption::NoWrap);
      layout.setTextOption(options);
      layout.beginLayout();
      auto line = layout.createLine();
      if (!line.isValid()) qFatal("No Qt text line was laid out");
      line.setLineWidth(650);
      layout.endLayout();
      if (index < 0 || line.textStart() != 0 || line.textLength() != label->text().size())
        qFatal("The Qt line does not cover the full Chinese sample");
      const auto flags = QTextLayout::RetrieveGlyphIndexes | QTextLayout::RetrieveGlyphPositions |
          QTextLayout::RetrieveStringIndexes;
      int total=0, missing=0, matches=0, glyph=0;
      for (const auto& run : line.glyphRuns(0, line.textLength(), flags)) {
        for (auto g : run.glyphIndexes()) {
          ++total;
          missing += g == 0;
        }
      }
      bool cmap=false, outline=false, split=false;
      QString family;
      const auto targeted = line.glyphRuns(static_cast<int>(index), 1, flags);
      for (const auto& run : targeted) {
        split = split || run.flags().testFlag(QGlyphRun::SplitLigature);
        for (auto g : run.glyphIndexes()) {
          ++matches;
          const auto raw = run.rawFont();
          family = raw.familyName();
          glyph = static_cast<int>(g);
          outline = raw.isValid() && !raw.pathForGlyph(g).isEmpty();
          const auto own = raw.glyphIndexesForString(QString(QChar(0x25b8)));
          cmap = own.size() == 1 && own.front() == g;
        }
      }
      if (total == 0 || matches != 1 || missing || !glyph || split || family != u"Noto Sans Symbols 2"_s || !cmap || !outline)
        qFatal("PJ_QA_FAIL %s index=%lld total=%d ranges=%lld matches=%d missing=%d glyph=%d family=%s cmap=%d outline=%d split=%d",
            qPrintable(samples[i].first), static_cast<long long>(index), total, static_cast<long long>(targeted.size()),
            matches, missing, glyph, qPrintable(family), cmap, outline, split);
      QImage rendered(650, 60, QImage::Format_RGB32);
      rendered.fill(Qt::white);
      {
        QPainter painter(&rendered);
        painter.setPen(Qt::black);
        layout.draw(&painter, {});
      }
      int ink = 0;
      for (int y = 0; y < rendered.height(); ++y)
        for (int x = 0; x < rendered.width(); ++x)
          ink += rendered.pixel(x, y) != qRgb(255, 255, 255);
      if (ink <= 100) qFatal("Qt drew insufficient ink for the localized glyph sample");
      qInfo("PJ_QA_GLYPH %s index=%lld glyph=%d family=%s cmap=%d outline=%d missing=%d ink=%d",
          qPrintable(samples[i].first), static_cast<long long>(index), glyph, qPrintable(family), cmap, outline, missing, ink);
    }
  });
  return app.exec();
}
