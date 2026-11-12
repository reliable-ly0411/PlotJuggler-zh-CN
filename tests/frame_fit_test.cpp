// SPDX-License-Identifier: MPL-2.0
#include "plotjuggler_app/window_geometry_helpers.h"
#include <QApplication>
#include <QEventLoop>
#include <QDebug>
#include <QMainWindow>
#include <QScreen>
#include <QTimer>
#include <QWindow>
#include <iostream>

static bool check(bool condition, const char* message)
{
  if (!condition) std::cerr << "FAIL: " << message << '\n';
  return condition;
}
static void waitForEvents(int ms)
{
  QEventLoop loop;
  QTimer::singleShot(ms, &loop, &QEventLoop::quit);
  loop.exec();
}
int main(int argc, char** argv)
{
  QApplication app(argc, argv);
  const QVector<QRect> screens{QRect(-1920, -120, 1920, 1040), QRect(0, 0, 1600, 860)};
  const QMargins margin(8, 30, 8, 8);
  bool ok = true;
  ok &= check(chooseScreen(QRect(-1800, 20, 800, 600), screens) == 0, "negative-origin screen");
  ok &= check(chooseScreen(QRect(2000, 20, 800, 600), screens) == 1, "disconnected-screen fallback");
  ok &= check(chooseScreen(QRect(-50, 20, 600, 600), screens) == 1, "largest intersection");
  ok &= check(chooseScreen(QRect(0, 0, 100, 100), {}) == -1, "no screen");
  for (const QRect area : screens)
  {
    for (const QRect frame : {QRect(-4000, -3000, 3000, 2000), QRect(5000, 4000, 1200, 900)})
      ok &= check(area.contains(fitWindowFrame(frame, area, margin)), "oversized/offscreen frame");
    const QRect already(area.x() + 10, area.y() + 10, 500, 400);
    ok &= check(fitWindowFrame(already, area, margin) == already, "preserve fitting frame");
  }
  const QRect area(0, 26, 1536, 838), topOutside(0, 25, 1000, 680);
  ok &= check(fitWindowFrame(topOutside, area, QMargins(0, 30, 0, 0)).top() == 26,
              "fractional-scale boundary remains strict");
  if (app.arguments().contains("--native") || app.arguments().contains("--native-default"))
  {
    if (QGuiApplication::platformName() == "offscreen" || QGuiApplication::platformName() == "minimal")
    {
      std::cerr << "SKIP: --native requires a real window manager\n";
      return 77;
    }
    QMainWindow window;
    const bool testDefault = app.arguments().contains("--native-default");
    window.resize(1058, testDefault ? 830 : 700);
    window.show();
    waitForEvents(700);
    auto* handle = window.windowHandle();
    if (!check(handle && handle->screen(), "native window and screen")) return 1;
    const QRect available = handle->screen()->availableGeometry();
    if (!testDefault)
      window.move(available.left() + 100, available.bottom() - 100);
    waitForEvents(400);
    qInfo() << "before correction" << window.frameGeometry() << "state" << window.windowState();
    ok &= check(!window.isMaximized() && !window.isFullScreen(), "normal-window test precondition");
    if (!testDefault)
      ok &= check(!available.contains(window.frameGeometry()), "initial frame must be out of bounds");
    const QMargins nativeMargin = handle->frameMargins();
    const QRect fitted = fitWindowFrame(window.frameGeometry(), available, nativeMargin);
    window.resize(fitted.width() - nativeMargin.left() - nativeMargin.right(),
                  fitted.height() - nativeMargin.top() - nativeMargin.bottom());
    window.move(fitted.topLeft());
    waitForEvents(700);
    qInfo() << "available" << available << "margins" << nativeMargin << "requested frame" << fitted << "actual frame" << window.frameGeometry();
    ok &= check(available.contains(window.frameGeometry()), "native decorated frame containment");
    const auto saved = window.saveGeometry();
    QMainWindow restored;
    ok &= check(restored.restoreGeometry(saved), "restore normal geometry");
    restored.show();
    waitForEvents(700);
    qInfo() << "restored frame" << restored.frameGeometry();
    ok &= check(restored.windowHandle() && restored.windowHandle()->screen() &&
                    restored.windowHandle()->screen()->availableGeometry().contains(restored.frameGeometry()),
                "restored native decorated frame containment");
  }
  if (ok) std::cout << "frame fit checks passed\n";
  return ok ? 0 : 1;
}
