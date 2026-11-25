// SPDX-License-Identifier: MPL-2.0
#pragma once

#include "../../../cmake/test_mains/pj_test_owned_directory.h"
#include "CustomWidgetController.h"
#include "MainWindow.h"
#include "pj_runtime/ActiveWidgetsMarker.h"

namespace pj_app_test {
namespace detail {

// Constructed before MainWindow and destroyed after it. Preparing the marker
// first leaves no allocation/failure gap between a completed window and injection.
struct MainWindowMarkerFixture {
  MainWindowMarkerFixture() : marker(std::make_shared<PJ::ActiveWidgetsMarker>(directory.path())) {}
  PjTestOwnedDirectory directory;
  std::shared_ptr<PJ::ActiveWidgetsMarker> marker;
};

}  // namespace detail

// Test-only shell with a private marker. This isolates the marker only, not
// QSettings, the extension store, QFileDialog, or other KnownFolder consumers.
class IsolatedMainWindow : private detail::MainWindowMarkerFixture, public PJ::MainWindow {
 public:
  explicit IsolatedMainWindow(QWidget* parent = nullptr) : PJ::MainWindow(parent) {
    installMarker();
  }
  explicit IsolatedMainWindow(QString extensions, QWidget* parent = nullptr)
      : PJ::MainWindow(std::move(extensions), parent) {
    installMarker();
  }

 private:
  void installMarker() noexcept {
    auto* controller = findChild<PJ::CustomWidgetController*>();
    if (controller == nullptr) {
      qFatal("Missing controller for private test marker injection");
    }
    controller->activeWidgetsMarker() = marker;
  }
};

}  // namespace pj_app_test
