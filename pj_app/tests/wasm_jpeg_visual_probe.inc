// SPDX-License-Identifier: MPL-2.0
// Acceptance-only Qt consumer: compiled solely with the existing ingress probe.
#include "../src/LocalizedOriginalMeme.h"

namespace {
/// Displays decoded resource pixels through Qt's real WASM backing store.
class JpegVisualProbe final : public QWidget {
 public:
  explicit JpegVisualProbe(QWidget* parent) : QWidget(parent) {}
  QImage image;
  QString label;
  int index = -1;
  bool reported = false;

 protected:
  void paintEvent(QPaintEvent*) override {
    QPainter painter(this);
    painter.fillRect(rect(), QColor(32, 32, 32));
    painter.setPen(Qt::white);
    painter.drawText(QPoint(16, 25), label);
    const QSize bound = size() - QSize(32, 56);
    const QSize shown = image.size().boundedTo(bound);
    const QImage pixels =
        shown == image.size() ? image : image.scaled(bound, Qt::KeepAspectRatio, Qt::SmoothTransformation);
    const QPoint at((width() - pixels.width()) / 2, 40 + (height() - 40 - pixels.height()) / 2);
    painter.drawImage(at, pixels);
    if (!reported) {
      reported = true;
      qInfo(
          "PJ_WASM_JPEG_PAINT index=%d width=%d height=%d shownw=%d shownh=%d alpha=%d", index, image.width(),
          image.height(), pixels.width(), pixels.height(), image.hasAlphaChannel());
    }
  }
};
}  // namespace

extern "C" EMSCRIPTEN_KEEPALIVE void pj_wasm_test_show_jpeg_visual(int index) {
  static QPointer<JpegVisualProbe> view;
  static const QStringList paths = {
      QStringLiteral(":/resources/memes/zh_CN/meme_00.png"),
      QStringLiteral(":/resources/memes/zh_CN/meme_08.png"),
      QStringLiteral(":/resources/memes/zh_CN/meme_4x_01.png"),
      QStringLiteral(":/resources/memes/zh_CN/meme_4x_03.png"),
      QStringLiteral(":/resources/memes/zh_CN/meme_4x_04.png"),
      QStringLiteral(":/resources/memes/zh_CN/meme_4x_05.png"),
      QStringLiteral(":/resources/memes/zh_CN/meme_4x_06.png"),
      QStringLiteral(":/resources/memes/zh_CN/meme_4x_07.png"),
      QStringLiteral(":/resources/memes/zh_CN/meme_4x_08.png"),
      QStringLiteral(":/resources/memes/zh_CN/meme_4x_10.png"),
      QStringLiteral(":/resources/memes/zh_CN/meme_4x_12.png"),
      QStringLiteral(":/resources/memes/zh_CN/meme_4x_14.png"),
      QStringLiteral(":/resources/memes/zh_CN/meme_4x_22.png"),
      QStringLiteral(":/resources/memes/zh_CN/meme_4x_28.png"),
      QStringLiteral(":/resources/memes/zh_CN/meme_4x_36.png"),
      QStringLiteral(":/resources/memes/zh_CN/meme_4x_37.png"),
      QStringLiteral(":/resources/memes/zh_CN/meme_52.png"),
      QStringLiteral(":/resources/memes/zh_CN/meme_60.png"),
      QStringLiteral(":/resources/memes/zh_CN/meme_93.png"),
      QStringLiteral(":/resources/memes/zh_CN/meme_97.png"),
      QStringLiteral(":/resources/memes/zh_CN/patches/atlas_103.png"),
      QStringLiteral(":/resources/memes/zh_CN/patches/atlas_14.png"),
      QStringLiteral(":/resources/memes/zh_CN/patches/atlas_25.png"),
      QStringLiteral(":/resources/memes/zh_CN/patches/atlas_35.png"),
      QStringLiteral(":/resources/memes/zh_CN/patches/atlas_42.png"),
      QStringLiteral(":/resources/memes/zh_CN/patches/atlas_45.png"),
      QStringLiteral(":/resources/memes/zh_CN/patches/atlas_61.png"),
      QStringLiteral(":/resources/memes/zh_CN/patches/atlas_71.png"),
      QStringLiteral(":/resources/memes/zh_CN/patches/atlas_79.png"),
      QStringLiteral(":/resources/memes/zh_CN/patches/atlas_89.png"),
      QStringLiteral(":/resources/memes/zh_CN/patches/atlas_95.png")};
  const auto ids = PJ::localizedOriginalMemeIds();
  const int total = static_cast<int>(paths.size() + ids.size());
  if (index < 0 || index >= total) {
    qInfo("PJ_WASM_JPEG_COUNT raw=%d composed=%d total=%d", int(paths.size()), int(ids.size()), total);
    return;
  }
  if (!view) {
    for (auto* widget : QApplication::topLevelWidgets()) {
      if (auto* window = qobject_cast<PJ::MainWindow*>(widget)) {
        view = new JpegVisualProbe(window);
        break;
      }
    }
  }
  if (!view) {
    qWarning("PJ_WASM_JPEG_ERROR no window");
    return;
  }
  view->index = index;
  if (index < paths.size()) {
    QImageReader reader(paths[index]);
    view->image = reader.read();
    view->label = paths[index];
  } else {
    const auto id = ids[index - paths.size()];
    view->image = PJ::localizedOriginalMeme(id.toInt()).toImage();
    view->label = "composed original slot " + id;
  }
  if (view->image.isNull()) {
    qWarning("PJ_WASM_JPEG_ERROR decode index=%d", index);
    return;
  }
  view->reported = false;
  view->setGeometry(view->parentWidget()->rect());
  view->show();
  view->raise();
  view->update();
}
