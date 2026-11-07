// Copyright 2026 Davide Faconti
// SPDX-License-Identifier: MPL-2.0
//
// A file dragged over any part of the main window reaches MainWindow's drop
// handling: the widgets that accept drops for curves (plot placeholders, plots,
// docks) leave a file drag ignored, and Qt then offers it to their ancestors.

#include <gtest/gtest.h>

#include <QAbstractSpinBox>
#include <QDragEnterEvent>
#include <QDropEvent>
#include <QFile>
#include <QLineEdit>
#include <QMimeData>
#include <QPlainTextEdit>
#include <QPointer>
#include <QSignalSpy>
#include <QTemporaryDir>
#include <QTest>
#include <QTextEdit>
#include <QUrl>
#include <memory>
#include <vector>

#include "FileLoader.h"
#include "MainWindow.h"
#include "pj_runtime/AppSession.h"
#include "pj_runtime/ExtensionCatalogService.h"
#include "pj_runtime/SessionManager.h"
#include "pj_widgets/VisualizationPlaceholderWidget.h"
#include "support/filepath_echo_source.h"
#include "support/gui_test_env.h"
#include "support/loader_test_support.h"

namespace PJ {

// Access to the real loader/session and independently guarded drop handlers.
class MainWindowFileDropTestPeer {
 public:
  [[nodiscard]] static AppSession& session(MainWindow& window) {
    return *window.session_;
  }

  [[nodiscard]] static FileLoader& loader(MainWindow& window) {
    return *window.file_loader_;
  }

  // Qt suppresses move/drop dispatch after a rejected enter. Invoke each handler
  // directly too, so a missing guard cannot hide behind that dispatch behavior.
  static void enter(MainWindow& window, QDragEnterEvent& event) {
    window.dragEnterEvent(&event);
  }

  static void move(MainWindow& window, QDragMoveEvent& event) {
    window.dragMoveEvent(&event);
  }

  static void drop(MainWindow& window, QDropEvent& event) {
    window.dropEvent(&event);
  }
};

}  // namespace PJ

namespace {

// Text inputs take a dropped URL as text, by design.
[[nodiscard]] bool isTextInput(const QWidget* widget) {
  return qobject_cast<const QLineEdit*>(widget) != nullptr || qobject_cast<const QTextEdit*>(widget) != nullptr ||
         qobject_cast<const QPlainTextEdit*>(widget) != nullptr ||
         qobject_cast<const QAbstractSpinBox*>(widget) != nullptr;
}

TEST(MainWindowFileDropTest, FileDragOverAnyDropTargetIsTakenAsACopy) {
  QTemporaryDir dir;
  ASSERT_TRUE(dir.isValid());
  QFile file(dir.filePath(QStringLiteral("data.csv")));
  ASSERT_TRUE(file.open(QIODevice::WriteOnly));
  file.write("t,x\n0,1\n");
  file.close();

  PJ::MainWindow window;
  window.show();
  ASSERT_TRUE(QTest::qWaitForWindowExposed(&window));

  QMimeData mime;
  mime.setUrls({QUrl::fromLocalFile(file.fileName())});

  int placeholders = 0;
  for (QWidget* leaf : window.findChildren<QWidget*>()) {
    if (!leaf->acceptDrops() || !leaf->isVisible() || isTextInput(leaf)) {
      continue;
    }
    if (qobject_cast<PJ::VisualizationPlaceholderWidget*>(leaf) != nullptr) {
      ++placeholders;
    }
    SCOPED_TRACE((leaf->metaObject()->className() + QStringLiteral(" ") + leaf->objectName()).toStdString());

    // Sent to the leaf, as QWidgetWindow does; QApplication::notify walks the ancestors.
    QDragEnterEvent enter(QPointF(1, 1), Qt::CopyAction | Qt::MoveAction, &mime, Qt::LeftButton, Qt::NoModifier);
    enter.setDropAction(Qt::MoveAction);
    QApplication::sendEvent(leaf, &enter);
    EXPECT_TRUE(enter.isAccepted());
    EXPECT_EQ(enter.dropAction(), Qt::CopyAction);

    QDragMoveEvent move(QPointF(2, 2), Qt::CopyAction | Qt::MoveAction, &mime, Qt::LeftButton, Qt::NoModifier);
    move.setDropAction(Qt::MoveAction);
    QApplication::sendEvent(leaf, &move);
    EXPECT_TRUE(move.isAccepted());
    EXPECT_EQ(move.dropAction(), Qt::CopyAction);

    QDragLeaveEvent leave;
    QApplication::sendEvent(leaf, &leave);
  }
  EXPECT_GT(placeholders, 0) << "the empty window should show a plot placeholder";
}

using DropPeer = PJ::MainWindowFileDropTestPeer;

// Each ctest case owns one shell and an isolated extension directory. The echo
// source uses the production plugin ABI and reads synthetic numeric file bytes.
class MainWindowFileDropLoadingTest : public ::testing::Test {
 protected:
  void SetUp() override {
    ASSERT_TRUE(extensions_.isValid());
    ASSERT_TRUE(data_.isValid());
    window_ = std::make_unique<PJ::MainWindow>(extensions_.path());
    ASSERT_TRUE(pj_app_test::registerFilepathEcho(DropPeer::session(*window_).extensionCatalog().pluginCatalog()));
    window_->show();
    ASSERT_TRUE(QTest::qWaitForWindowExposed(window_.get()));
  }

  // The MIME object and event die before queued loading, just as an OS drop
  // does. Snapshot the probe so repeated drops also prove synchronous deferral.
  void dropFiles(const QStringList& paths, Qt::DropActions actions = Qt::CopyAction | Qt::MoveAction) {
    const auto configs_before = pj_app_test::filepathEchoProbe().configs;
    const auto opened_before = pj_app_test::filepathEchoProbe().opened;
    QMimeData mime;
    QList<QUrl> urls;
    for (const QString& path : paths) {
      urls.push_back(QUrl::fromLocalFile(path));
    }
    mime.setUrls(urls);
    QDragEnterEvent enter(QPointF(1, 1), actions, &mime, Qt::LeftButton, Qt::NoModifier);
    QApplication::sendEvent(window_.get(), &enter);
    ASSERT_TRUE(enter.isAccepted());
    EXPECT_EQ(enter.dropAction(), Qt::CopyAction);
    QDragMoveEvent move(QPointF(2, 2), actions, &mime, Qt::LeftButton, Qt::NoModifier);
    QApplication::sendEvent(window_.get(), &move);
    ASSERT_TRUE(move.isAccepted());
    EXPECT_EQ(move.dropAction(), Qt::CopyAction);

    QDropEvent drop(QPointF(2, 2), actions, &mime, Qt::LeftButton, Qt::NoModifier);
    if (actions.testFlag(Qt::MoveAction)) {
      drop.setDropAction(Qt::MoveAction);
    }
    QApplication::sendEvent(window_.get(), &drop);
    EXPECT_TRUE(drop.isAccepted());
    EXPECT_EQ(drop.dropAction(), Qt::CopyAction);
    EXPECT_FALSE(DropPeer::loader(*window_).isBusy());
    EXPECT_EQ(pj_app_test::filepathEchoProbe().configs, configs_before);
    EXPECT_EQ(pj_app_test::filepathEchoProbe().opened, opened_before);
  }

  // Pre-accept events to check explicit rejection rather than their default state.
  void expectRejected(QMimeData& mime, Qt::DropActions actions) {
    QSignalSpy loaded(&DropPeer::loader(*window_), &PJ::FileLoader::fileLoaded);
    QSignalSpy failed(&DropPeer::loader(*window_), &PJ::FileLoader::fileLoadFailed);
    QSignalSpy finished(&DropPeer::loader(*window_), &PJ::FileLoader::loadFinished);
    QDragEnterEvent enter(QPointF(1, 1), actions, &mime, Qt::LeftButton, Qt::NoModifier);
    QApplication::sendEvent(window_.get(), &enter);
    EXPECT_FALSE(enter.isAccepted());
    enter.accept();
    DropPeer::enter(*window_, enter);
    EXPECT_FALSE(enter.isAccepted());

    QDragMoveEvent move(QPointF(2, 2), actions, &mime, Qt::LeftButton, Qt::NoModifier);
    move.accept();
    DropPeer::move(*window_, move);
    EXPECT_FALSE(move.isAccepted());

    QDropEvent drop(QPointF(2, 2), actions, &mime, Qt::LeftButton, Qt::NoModifier);
    drop.accept();
    DropPeer::drop(*window_, drop);
    EXPECT_FALSE(drop.isAccepted());
    pj_app_test::flushQueuedEvents();
    EXPECT_FALSE(DropPeer::loader(*window_).isBusy());
    EXPECT_TRUE(loaded.isEmpty());
    EXPECT_TRUE(failed.isEmpty());
    EXPECT_TRUE(finished.isEmpty());
    EXPECT_TRUE(pj_app_test::filepathEchoProbe().configs.empty());
    EXPECT_TRUE(pj_app_test::filepathEchoProbe().opened.empty());
    EXPECT_TRUE(DropPeer::session(*window_).sessionManager().createReader().listDatasets().empty());
  }

  // Match by the retained source path, not by dataset ordering or display name.
  [[nodiscard]] std::vector<double> valuesAt(const QString& path) {
    auto& session = DropPeer::session(*window_).sessionManager();
    const auto reader = session.createReader();
    for (const auto id : reader.listDatasets()) {
      if (session.datasetSourcePath(id) == path) {
        return pj_app_test::singleTopicValues(reader, id);
      }
    }
    return {};
  }

  void expectSourceBytes(const QString& path, const QByteArray& expected) {
    QFile file(path);
    ASSERT_TRUE(file.open(QIODevice::ReadOnly)) << path.toStdString();
    EXPECT_EQ(file.readAll(), expected);
  }

  QTemporaryDir extensions_;
  QTemporaryDir data_;
  std::unique_ptr<PJ::MainWindow> window_;
};

TEST_F(MainWindowFileDropLoadingTest, MoveOnlyAndIgnoreActionRejectWithoutLoading) {
  const QString path =
      pj_app_test::writeEchoFile(data_.filePath(QStringLiteral("不可移动.echo")), {QStringLiteral("31")});
  QMimeData mime;
  mime.setUrls({QUrl::fromLocalFile(path)});
  for (const auto action : {Qt::MoveAction, Qt::IgnoreAction}) {
    SCOPED_TRACE(static_cast<int>(action));
    ASSERT_NO_FATAL_FAILURE(expectRejected(mime, action));
    expectSourceBytes(path, QByteArray("31"));
  }
}

TEST_F(MainWindowFileDropLoadingTest, CopyActionRejectsNonFileUrlsAndTextWithoutLoading) {
  QMimeData mime;
  mime.setUrls(
      {QUrl::fromLocalFile(data_.path()), QUrl::fromLocalFile(data_.filePath(QStringLiteral("不存在.echo"))),
       QUrl(QStringLiteral("https://example.com/remote.echo"))});
  ASSERT_NO_FATAL_FAILURE(expectRejected(mime, Qt::CopyAction));
  mime.clear();
  mime.setText(QStringLiteral("not a file URL"));
  ASSERT_NO_FATAL_FAILURE(expectRejected(mime, Qt::CopyAction));
}

TEST_F(MainWindowFileDropLoadingTest, CopyOnlyDropLoadsAndRetainsSourceBytes) {
  const QString path = pj_app_test::writeEchoFile(
      data_.filePath(QStringLiteral("仅复制.echo")), {QStringLiteral("37"), QStringLiteral("41")});
  QSignalSpy loaded(&DropPeer::loader(*window_), &PJ::FileLoader::fileLoaded);
  ASSERT_NO_FATAL_FAILURE(dropFiles({path}, Qt::CopyAction));
  EXPECT_TRUE(loaded.isEmpty());
  ASSERT_TRUE(pj_app_test::pumpUntil([&] { return loaded.count() == 1 && !DropPeer::loader(*window_).isBusy(); }));
  EXPECT_EQ(pj_app_test::filepathEchoProbe().opened, (std::vector<std::string>{path.toStdString()}));
  EXPECT_EQ(valuesAt(path), (std::vector<double>{37, 41}));
  expectSourceBytes(path, QByteArray("37\n41"));
}

TEST_F(MainWindowFileDropLoadingTest, ChinesePathDropLoadsAfterReturningAndRetainsSourceBytes) {
  const QString path = pj_app_test::writeEchoFile(
      data_.filePath(QStringLiteral("合成数据/飞行 记录.echo")), {QStringLiteral("1.25"), QStringLiteral("-2.5")});
  QSignalSpy loaded(&DropPeer::loader(*window_), &PJ::FileLoader::fileLoaded);
  QSignalSpy failed(&DropPeer::loader(*window_), &PJ::FileLoader::fileLoadFailed);

  ASSERT_NO_FATAL_FAILURE(dropFiles({path}));
  EXPECT_TRUE(loaded.isEmpty());
  EXPECT_TRUE(DropPeer::session(*window_).sessionManager().createReader().listDatasets().empty());
  ASSERT_TRUE(pj_app_test::pumpUntil([&] { return loaded.count() == 1 && !DropPeer::loader(*window_).isBusy(); }));
  EXPECT_TRUE(failed.isEmpty());
  EXPECT_EQ(pj_app_test::filepathEchoProbe().opened, (std::vector<std::string>{path.toStdString()}));
  EXPECT_EQ(valuesAt(path), (std::vector<double>{1.25, -2.5}));
  expectSourceBytes(path, QByteArray("1.25\n-2.5"));
}

TEST_F(MainWindowFileDropLoadingTest, MultipleFilesAndRepeatedDropKeepValuesSeparateAndSourcesIntact) {
  const QString first = pj_app_test::writeEchoFile(
      data_.filePath(QStringLiteral("中文目录/第一.echo")), {QStringLiteral("3"), QStringLiteral("7")});
  const QString second = pj_app_test::writeEchoFile(
      data_.filePath(QStringLiteral("中文目录/第二.echo")), {QStringLiteral("11"), QStringLiteral("19")});
  QSignalSpy loaded(&DropPeer::loader(*window_), &PJ::FileLoader::fileLoaded);
  QSignalSpy failed(&DropPeer::loader(*window_), &PJ::FileLoader::fileLoadFailed);

  ASSERT_NO_FATAL_FAILURE(dropFiles({first, second}));
  EXPECT_TRUE(loaded.isEmpty());
  ASSERT_TRUE(pj_app_test::pumpUntil([&] { return loaded.count() == 2 && !DropPeer::loader(*window_).isBusy(); }));
  EXPECT_EQ(valuesAt(first), (std::vector<double>{3, 7}));
  EXPECT_EQ(valuesAt(second), (std::vector<double>{11, 19}));

  ASSERT_NO_FATAL_FAILURE(dropFiles({first}));
  EXPECT_EQ(loaded.count(), 2);
  ASSERT_TRUE(pj_app_test::pumpUntil([&] { return loaded.count() == 3 && !DropPeer::loader(*window_).isBusy(); }));
  EXPECT_TRUE(failed.isEmpty());
  EXPECT_EQ(DropPeer::session(*window_).sessionManager().createReader().listDatasets().size(), 2u);
  EXPECT_EQ(valuesAt(first), (std::vector<double>{3, 7}));
  EXPECT_EQ(valuesAt(second), (std::vector<double>{11, 19}));
  EXPECT_EQ(
      pj_app_test::filepathEchoProbe().opened,
      (std::vector<std::string>{first.toStdString(), second.toStdString(), first.toStdString()}));
  expectSourceBytes(first, QByteArray("3\n7"));
  expectSourceBytes(second, QByteArray("11\n19"));
}

TEST_F(MainWindowFileDropLoadingTest, ClosingAndDestroyingWindowCancelsQueuedDrop) {
  const QString path =
      pj_app_test::writeEchoFile(data_.filePath(QStringLiteral("待加载.echo")), {QStringLiteral("23")});
  ASSERT_NO_FATAL_FAILURE(dropFiles({path}));
  QPointer<PJ::MainWindow> guard(window_.get());
  ASSERT_TRUE(window_->close());
  window_.reset();
  ASSERT_TRUE(guard.isNull());

  // A context-free deferred callback would now dereference the freed shell.
  pj_app_test::flushQueuedEvents();
  EXPECT_TRUE(pj_app_test::filepathEchoProbe().configs.empty());
  EXPECT_TRUE(pj_app_test::filepathEchoProbe().opened.empty());
  expectSourceBytes(path, QByteArray("23"));
}

}  // namespace
