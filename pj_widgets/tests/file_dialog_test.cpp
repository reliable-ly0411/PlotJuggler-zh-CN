// Copyright 2026 Davide Faconti
// SPDX-License-Identifier: MPL-2.0

#include <gtest/gtest.h>

#include <QApplication>
#include <QCheckBox>
#include <QDir>
#include <QDeadlineTimer>
#include <QEventLoop>
#include <QThread>
#include <QFileDialog>
#include <QFile>
#include <QFileSystemModel>
#include <QAbstractProxyModel>
#include <QLocale>
#include <QMimeDatabase>
#include <QScopeGuard>
#include <QTemporaryDir>
#include <QTimer>
#include <filesystem>

#include "pj_widgets/FileDialog.h"
using namespace Qt::StringLiterals;

namespace {

class FileDialogTest : public ::testing::Test {};

// The dialog is modal — we close it from a single-shot timer so the test
// doesn't hang. We verify the embedded extras checkbox state is reported
// back to the caller, which is the whole reason the overload exists.
TEST_F(FileDialogTest, GetSaveFileNameWithOptionsReportsCheckboxState) {
  PJ::FileDialog::ExtraOption opt{u"Save Data Source"_s, /*default_checked=*/true};
  QTemporaryDir temp;
  ASSERT_TRUE(temp.isValid());
  const QString save_path = QDir(temp.path()).filePath(u"_pj4_filedialog_test.pjl4"_s);

  // Fire after the modal dialog is up; find the checkbox by its label and
  // toggle it off, then accept by hitting the Save button.
  QTimer::singleShot(0, [save_path] {
    QWidget* active = QApplication::activeModalWidget();
    ASSERT_NE(active, nullptr);
    auto* checkbox = active->findChild<QCheckBox*>();
    ASSERT_NE(checkbox, nullptr);
    EXPECT_TRUE(checkbox->isChecked());
    checkbox->setChecked(false);
    auto* file_dialog = active->findChild<QFileDialog*>();
    ASSERT_NE(file_dialog, nullptr);
    file_dialog->selectFile(save_path);
    QMetaObject::invokeMethod(file_dialog, "accept", Qt::QueuedConnection);
  });

  const auto result = PJ::FileDialog::getSaveFileNameWithOptions(
      /*parent=*/nullptr, u"Save"_s, temp.path(), u"PJ4 Layout (*.pjl4)"_s, u"pjl4"_s, {opt});

  EXPECT_FALSE(result.path.isEmpty());
  ASSERT_EQ(result.option_states.size(), 1u);
  EXPECT_FALSE(result.option_states[0]);  // toggled off in the timer
}

TEST_F(FileDialogTest, GetSaveFileNameWithOptionsCancelReturnsEmpty) {
  PJ::FileDialog::ExtraOption opt{u"Save Data Source"_s, true};
  QTemporaryDir temp;
  ASSERT_TRUE(temp.isValid());
  QTimer::singleShot(0, [] {
    QWidget* active = QApplication::activeModalWidget();
    ASSERT_NE(active, nullptr);
    auto* file_dialog = active->findChild<QFileDialog*>();
    ASSERT_NE(file_dialog, nullptr);
    QMetaObject::invokeMethod(file_dialog, "reject", Qt::QueuedConnection);
  });

  const auto result = PJ::FileDialog::getSaveFileNameWithOptions(
      nullptr, u"Save"_s, temp.path(), u"PJ4 Layout (*.pjl4)"_s, u"pjl4"_s, {opt});

  EXPECT_TRUE(result.path.isEmpty());
  ASSERT_EQ(result.option_states.size(), 1u);
  EXPECT_TRUE(result.option_states[0]);  // defaults preserved on cancel
}

TEST_F(FileDialogTest, LocalizedDetailsPreserveNamesRolesPathsAndSourceSorting) {
  const QVariant previous = qApp->property("interfaceLanguage");
  const auto restore = qScopeGuard([&] { qApp->setProperty("interfaceLanguage", previous); });
  qApp->setProperty("interfaceLanguage", u"zh_CN"_s);
  QTemporaryDir temp;
  ASSERT_TRUE(temp.isValid());
  const QString path = QDir(temp.path()).filePath(u"原始 Name %1.xml"_s);
  QFile file(path);
  ASSERT_TRUE(file.open(QIODevice::WriteOnly));
  ASSERT_EQ(file.write("<root/>", 7), 7);
  file.close();
  PJ::FileDialog picker;
  picker.setDirectory(temp.path());
  auto* inner = picker.findChild<QFileDialog*>();
  ASSERT_NE(inner, nullptr);
  auto* proxy = inner->proxyModel();
  ASSERT_NE(proxy, nullptr);
  auto* source = qobject_cast<QFileSystemModel*>(proxy->sourceModel());
  ASSERT_NE(source, nullptr);
  const QModelIndex original = source->index(path);
  ASSERT_TRUE(original.isValid());
  const QModelIndex shown = proxy->mapFromSource(original);
  ASSERT_TRUE(shown.isValid());
  EXPECT_EQ(proxy->data(shown).toString(), u"原始 Name %1.xml"_s);
  EXPECT_EQ(proxy->data(shown, QFileSystemModel::FilePathRole).toString(), path);
  EXPECT_EQ(proxy->data(shown, Qt::EditRole), source->data(original, Qt::EditRole));
  EXPECT_EQ(proxy->data(shown.siblingAtColumn(1)).toString(),
            QLocale(QLocale::Chinese, QLocale::China).formattedDataSize(7));
  EXPECT_EQ(proxy->data(shown.siblingAtColumn(2)).toString(),
            QCoreApplication::translate("PJ::FileDialog", "XML document"));
  picker.selectFile(path);
  EXPECT_EQ(picker.selectedFile(), path);
  qApp->setProperty("interfaceLanguage", u"en_US"_s);
  EXPECT_EQ(proxy->data(shown.siblingAtColumn(1)), source->data(original.siblingAtColumn(1)));
  EXPECT_EQ(proxy->data(shown.siblingAtColumn(2)), source->data(original.siblingAtColumn(2)))
        << "actual=" << proxy->data(shown.siblingAtColumn(2)).toString().toStdString()
        << " expected=" << source->data(original.siblingAtColumn(2)).toString().toStdString();
}

TEST_F(FileDialogTest, FileLinksKeepOriginalIdentityAndLocalizedMimeType) {
  const QVariant previous = qApp->property("interfaceLanguage");
  const auto restore = qScopeGuard([&] { qApp->setProperty("interfaceLanguage", previous); });
  qApp->setProperty("interfaceLanguage", u"zh_CN"_s);
  QTemporaryDir temp;
  ASSERT_TRUE(temp.isValid());
  const QDir directory(temp.path());
  const QString target = directory.filePath(u"原始 %1 [target].txt"_s);
  QFile file(target);
  ASSERT_TRUE(file.open(QIODevice::WriteOnly));
  ASSERT_EQ(file.write("plain text", 10), 10);
  file.close();
  ASSERT_TRUE(directory.mkdir(u"folder"_s));
  const QStringList names{u"same.txt"_s, u"different.xml"_s, u"folder-link"_s, u"broken-link"_s};
  const QStringList targets{target, target, directory.filePath(u"folder"_s), directory.filePath(u"missing"_s)};
  for (int i = 0; i < names.size(); ++i) {
    std::error_code error;
    const auto link = QFileInfo(directory.filePath(names[i])).filesystemFilePath();
    const auto destination = QFileInfo(targets[i]).filesystemFilePath();
    if (i == 2) std::filesystem::create_directory_symlink(destination, link, error);
    else std::filesystem::create_symlink(destination, link, error);
#ifdef Q_OS_WIN
    if (error) GTEST_SKIP() << "Native symbolic link creation unavailable: " << error.message();
#else
    ASSERT_FALSE(error) << error.message();
#endif
  }
  PJ::FileDialog picker;
  picker.setDirectory(temp.path());
  auto* inner = picker.findChild<QFileDialog*>();
  ASSERT_NE(inner, nullptr);
  // Qt's default listing excludes dangling links. Include System only in this
  // model-level regression, not in the production picker, to exercise its roles.
  inner->setFilter(inner->filter() | QDir::System);
  auto* proxy = inner->proxyModel();
  ASSERT_NE(proxy, nullptr);
  auto* source = qobject_cast<QFileSystemModel*>(proxy->sourceModel());
  ASSERT_NE(source, nullptr);
  picker.show();
  for (int i = 0; i < names.size(); ++i) {
    const QString path = directory.filePath(names[i]);
    SCOPED_TRACE(names[i].toStdString());
    QDeadlineTimer deadline(5000);
    while (!source->index(path).isValid() && !deadline.hasExpired()) {
      QCoreApplication::processEvents(QEventLoop::AllEvents, 50);
      QThread::msleep(1);
    }
    const QModelIndex original = source->index(path);
    ASSERT_TRUE(original.isValid()) << names[i].toStdString();
    const QModelIndex shown = proxy->mapFromSource(original);
    ASSERT_TRUE(shown.isValid());
    EXPECT_EQ(proxy->data(shown, QFileSystemModel::FilePathRole).toString(), path);
    EXPECT_EQ(proxy->data(shown, Qt::EditRole), source->data(original, Qt::EditRole));
    EXPECT_EQ(proxy->mapToSource(shown), original);
    EXPECT_EQ(proxy->data(shown).toString(), names[i]);
    if (i < 2) {
      const QString mime = QMimeDatabase().mimeTypeForFile(QFileInfo(path)).name();
      ASSERT_TRUE(mime == u"text/plain"_s || mime == u"application/xml"_s || mime == u"text/xml"_s);
      EXPECT_EQ(proxy->data(shown.siblingAtColumn(2)).toString(), QCoreApplication::translate(
          "PJ::FileDialog", mime == u"text/plain"_s ? "Plain text document" : "XML document"));
    } else {
      EXPECT_EQ(proxy->data(shown.siblingAtColumn(2)), source->data(original.siblingAtColumn(2)))
        << "actual=" << proxy->data(shown.siblingAtColumn(2)).toString().toStdString()
        << " expected=" << source->data(original.siblingAtColumn(2)).toString().toStdString();
    }
  }
}

}  // namespace
