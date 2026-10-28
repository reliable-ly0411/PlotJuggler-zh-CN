// SPDX-License-Identifier: MPL-2.0
// Optional acceptance with verified plugin copies and a fresh process/profile
// per language. All data comes from MainWindow::populateTestData().
#include <QTest>
#ifndef Q_MOC_RUN
#include <QAbstractButton>
#include <QApplication>
#include <QComboBox>
#include <QDataStream>
#include <QDesktopServices>
#include <QDir>
#include <QDirIterator>
#include <QDragEnterEvent>
#include <QDropEvent>
#include <QFile>
#include <QLabel>
#include <QLineEdit>
#include <QMenu>
#include <QMimeData>
#include <QPixmap>
#include <QPushButton>
#include <QSettings>
#include <QSplitter>
#include <QTableWidget>
#include <QTemporaryDir>
#include <QTextBrowser>
#include <QTimer>
#include <QTreeWidgetItemIterator>

#include "AppLanguage.h"
#include "MainWindow.h"
#include "PreferencesDialog.h"
#include "TitleBar.h"
#include "pj_marketplace/platform_utils.hpp"
#include "pj_plotting/PlotWidgetBase.h"
#include "pj_widgets/CurveTreeView.h"
#endif

using namespace Qt::StringLiterals;

class PluginFeedbackTest : public QObject {
  Q_OBJECT
 private slots:
  void mainWindowFlow();

 public slots:
  /// Intercept the website action without starting a browser.
  void acceptUrl(const QUrl& url) {
    opened_ = url;
  }

 private:
  QUrl opened_;

  /// Save only this isolated window, which contains generated sin/cos data.
  static bool capture(QWidget& window, const QString& name) {
    QCoreApplication::processEvents();
    const auto image = window.grab();
    const QString directory = qEnvironmentVariable("PJ_GUI_ACCEPTANCE_DIR");
    return !image.isNull() && (directory.isEmpty() ||
                               (QDir().mkpath(directory) && image.save(QDir(directory).filePath(name + u".png"_s))));
  }

  /// Check actual laid-out actions, not just their enabled flags or click slots.
  static bool actionFits(const QWidget& panel, const QAbstractButton* button) {
    const QRect bounds(button->mapTo(&panel, QPoint()), button->size());
    return button->isVisible() && button->isEnabled() && panel.rect().contains(bounds) &&
           button->visibleRegion().contains(button->rect()) &&
           button->width() >= button->sizeHint().width() && button->height() >= button->sizeHint().height();
  }

  /// Wrapped status must remain readable without taking space from the actions.
  static bool statusFits(const QLabel* status) {
    return status->isVisible() && status->visibleRegion().contains(status->rect()) &&
           status->height() >= status->heightForWidth(status->width());
  }
};

void PluginFeedbackTest::mainWindowFlow() {
  const QString extensions = qEnvironmentVariable("PJ_FEEDBACK_PLUGIN_DIR");
  if (extensions.isEmpty()) {
    QSKIP("Set PJ_FEEDBACK_PLUGIN_DIR to isolated verified APBIN and FFT plugin copies");
  }
  const QString language = qEnvironmentVariable("PJ_FEEDBACK_LANGUAGE", "en_US");
  QSettings settings;
  settings.setValue(PJ::AppLanguage::kPreferenceKey, language);
  const PJ::AppLanguage translator(*qApp, PJ::AppLanguage::preferredLanguage(settings));
  QCOMPARE(translator.catalogLoaded(), language != u"en_US"_s);
  // A plugin-dir override changes load priority, not the marketplace's managed
  // store. Seed the isolated profile with the actual installed-package copies.
  QVERIFY(!QDir(QCoreApplication::applicationDirPath() + u"/../lib/plotjuggler/plugins"_s).exists());
  const QDir source(extensions);
  const QDir destination(PJ::PlatformUtils::extensionsDir());
  QDirIterator files(source.absolutePath(), QDir::Files, QDirIterator::Subdirectories);
  while (files.hasNext()) {
    const QString from = files.next();
    const QString to = destination.filePath(source.relativeFilePath(from));
    QVERIFY(QDir().mkpath(QFileInfo(to).absolutePath()));
    QVERIFY(QFile::copy(from, to));
  }
  PJ::MainWindow window;
  QVERIFY(window.populateTestData());
  window.resize(1500, 830);
  window.show();
  QTest::qWait(100);
  QCOMPARE(window.size(), QSize(1500, 830));

  const QTemporaryDir registry_directory;
  QVERIFY(registry_directory.isValid());
  QFile registry(registry_directory.filePath(u"registry.json"_s));
  QVERIFY(registry.open(QIODevice::WriteOnly));
  QCOMPARE(registry.write("{\"extensions\":[]}"), qint64{17});
  registry.close();
  window.setRegistryUrlSetting(QUrl::fromLocalFile(registry.fileName()).toString());
  QVERIFY(QMetaObject::invokeMethod(&window, "onOpenMarketplace", Qt::DirectConnection));
  auto* table = window.findChild<QTableWidget*>(u"plugin_table_"_s);
  QVERIFY(table);
  QTRY_COMPARE_WITH_TIMEOUT(table->rowCount(), 2, 15000);
  const auto apbin_row = [table] {
    for (int row = 0; row < table->rowCount(); ++row) {
      if (table->item(row, 0)->data(Qt::UserRole).toString() == u"ardupilot-dataflash"_s) {
        return row;
      }
    }
    return -1;
  };
  QTRY_VERIFY_WITH_TIMEOUT(apbin_row() >= 0, 15000);
  table->selectRow(apbin_row());
  const auto website_button = [&window]() -> QPushButton* {
    for (auto* button : window.findChildren<QPushButton*>()) {
      if (button->isVisible() &&
          button->text() == QCoreApplication::translate("PJ::MarketplaceWindow", "Visit Website")) {
        return button;
      }
    }
    return nullptr;
  };
  QTRY_VERIFY(website_button());
  auto* details = window.findChild<QTextBrowser*>(u"detail_text_"_s);
  QVERIFY(details);
  QVERIFY(details->toPlainText().contains(u"LGPL-3.0-only"_s));
  QDesktopServices::setUrlHandler(u"https"_s, this, "acceptUrl");
  website_button()->click();
  QDesktopServices::unsetUrlHandler(u"https"_s);
  QCOMPARE(opened_, QUrl(u"https://github.com/reliable-ly0411/plotjuggler-apbin-plugins"_s));
  QVERIFY(capture(window, u"full-apbin-"_s + language));

  QVERIFY(QMetaObject::invokeMethod(&window, "onRebuildToolboxMenu", Qt::DirectConnection));
  QMenu* menu = window.titleBar()->toolboxMenu();
  menu->popup(window.mapToGlobal(QPoint(20, 20)));
  QCoreApplication::processEvents();
  QAction* fft = nullptr;
  const auto expected_title = QCoreApplication::translate("PJ::BundledPluginMetadata", "Fast Fourier Transform");
  for (auto* action : menu->actions()) {
    if (action->text() == expected_title) {
      fft = action;
      break;
    }
  }
  QVERIFY(fft);
  QCOMPARE(fft->text() == u"Fast Fourier Transform"_s, language == u"en_US"_s);
  QCOMPARE(fft->toolTip().startsWith(u"Compute"_s), language == u"en_US"_s);
  QVERIFY(capture(*menu, u"full-fft-menu-"_s + language));
  menu->hide();
  fft->trigger();
  QCoreApplication::processEvents();
  auto* panel = window.findChild<QWidget*>(u"FFTDialog"_s);
  QVERIFY(panel);
  QCOMPARE(panel->windowTitle(), QCoreApplication::translate("PJ::BundledPlugins", "FFT Toolbox"));
  auto* selected = panel->findChild<QLabel*>(u"selected_value"_s);
  auto* calculate = panel->findChild<QAbstractButton*>(u"btn_compute"_s);
  auto* save = panel->findChild<QAbstractButton*>(u"btn_save"_s);
  auto* status = panel->findChild<QLabel*>(u"status_label"_s);
  auto* suffix = panel->findChild<QLineEdit*>(u"suffix_edit"_s);
  QVERIFY(selected && calculate && save && status && suffix);
  QCOMPARE(selected->text(), QCoreApplication::translate("PJ::BundledPlugins", "No input selected"));
  QVERIFY(!calculate->isEnabled());
  QCOMPARE(suffix->text(), u"_FFT"_s);
  // Preserve the default splitter sizes: enlarging the input pane masks the
  // compact-window regression caused by long dynamic status text.
  QVERIFY(capture(window, u"full-fft-initial-"_s + language));

  QString key;
  for (auto* tree : window.findChildren<PJ::CurveTreeView*>()) {
    for (QTreeWidgetItemIterator it(tree); *it; ++it) {
      const auto candidate = (*it)->data(0, Qt::UserRole).toString();
      QStringList path;
      for (auto* ancestor = *it; ancestor != nullptr; ancestor = ancestor->parent()) {
        path.prepend(ancestor->text(0));
      }
      if (!candidate.isEmpty() && path.join('/').contains(u"test/sin"_s)) {
        key = candidate;
        break;
      }
    }
  }
  QVERIFY(!key.isEmpty());
  QMimeData mime;
  QByteArray encoded;
  QDataStream stream(&encoded, QIODevice::WriteOnly);
  stream << key;
  mime.setData(u"plotjuggler/catalog-items"_s, encoded);
  auto* input = panel->findChild<QWidget*>(u"inputFrame"_s);
  QVERIFY(input);
  const QPoint point = input->mapTo(panel, input->rect().center());
  QDragEnterEvent enter(point, Qt::CopyAction, &mime, Qt::LeftButton, Qt::NoModifier);
  QCoreApplication::sendEvent(panel, &enter);
  QVERIFY(enter.isAccepted());
  QDropEvent drop(QPointF(point), Qt::CopyAction, &mime, Qt::LeftButton, Qt::NoModifier);
  QCoreApplication::sendEvent(panel, &drop);
  QVERIFY(drop.isAccepted());
  QTRY_VERIFY(calculate->isEnabled());
  QVERIFY(selected->text().contains(u"test/sin"_s));
  QVERIFY(actionFits(*panel, calculate));
  QTest::mouseClick(calculate, Qt::LeftButton);
  QTRY_VERIFY_WITH_TIMEOUT(save->isEnabled(), 10000);
  QVERIFY(status->text().contains(u"Hz"_s));
  QCOMPARE(status->text().startsWith(u"Computed"_s), language == u"en_US"_s);
  QTRY_VERIFY(actionFits(*panel, calculate));
  QTRY_VERIFY(actionFits(*panel, save));
  QVERIFY(statusFits(status));
  QVERIFY(capture(window, u"full-fft-computed-"_s + language));
  QTest::mouseClick(save, Qt::LeftButton);
  QTRY_VERIFY(status->text().contains(u"_FFT"_s));
  QVERIFY(status->text().contains(u"frequency_hz"_s));
  QVERIFY(status->text().contains(u"amplitude"_s));
  QCOMPARE(status->text().startsWith(u"Exported"_s), language == u"en_US"_s);
  QCOMPARE(suffix->text(), u"_FFT"_s);
  const auto exported_field = [&window](const QString& field) {
    for (auto* tree : window.findChildren<PJ::CurveTreeView*>()) {
      for (QTreeWidgetItemIterator it(tree); *it; ++it) {
        if ((*it)->text(0) != field) {
          continue;
        }
        for (auto* ancestor = (*it)->parent(); ancestor != nullptr; ancestor = ancestor->parent()) {
          if (ancestor->text(0).contains(u"_FFT"_s)) {
            return true;
          }
        }
      }
    }
    return false;
  };
  QTRY_VERIFY(exported_field(u"frequency_hz"_s));
  QTRY_VERIFY(exported_field(u"amplitude"_s));
  QVERIFY(actionFits(*panel, calculate));
  QVERIFY(actionFits(*panel, save));
  QVERIFY(statusFits(status));
  QVERIFY(capture(window, u"full-fft-exported-"_s + language));

  window.resize(1280, 720);
  QTest::qWait(100);
  QCOMPARE(window.size(), QSize(1280, 720));
  QVERIFY(actionFits(*panel, calculate));
  QVERIFY(actionFits(*panel, save));
  QTest::mouseClick(calculate, Qt::LeftButton);
  QTRY_VERIFY(!status->text().contains(u"_FFT"_s));
  QVERIFY(status->text().contains(u"Hz"_s));
  QVERIFY(actionFits(*panel, calculate));
  QVERIFY(actionFits(*panel, save));
  QVERIFY(statusFits(status));
  QVERIFY(capture(window, u"full-fft-computed-compact-"_s + language));
  QTest::mouseClick(save, Qt::LeftButton);
  QTRY_VERIFY(status->text().contains(u"frequency_hz"_s));
  QVERIFY(status->text().contains(u"amplitude"_s));
  QVERIFY(actionFits(*panel, calculate));
  QVERIFY(actionFits(*panel, save));
  QVERIFY(statusFits(status));
  QVERIFY(capture(window, u"full-fft-exported-compact-"_s + language));

  // Language selection is saved for restart; the live FFT data and display
  // remain in the running language until the next application process.
  const QString next_language = language == u"zh_CN"_s ? u"zh_TW"_s : language == u"zh_TW"_s ? u"en_US"_s : u"zh_CN"_s;
  const QString running_status = status->text();
  bool preference_saved = false;
  QTimer::singleShot(0, &window, [&] {
    auto* dialog = qobject_cast<PJ::PreferencesDialog*>(QApplication::activeModalWidget());
    if (dialog == nullptr) {
      return;
    }
    dialog->showPage(PJ::PreferencesDialog::kAppearancePage);
    auto* combo = dialog->findChild<QComboBox*>(u"languageCombo"_s);
    if (combo == nullptr || combo->findData(next_language) < 0) {
      dialog->reject();
      return;
    }
    combo->setCurrentIndex(combo->findData(next_language));
    preference_saved = capture(*dialog, u"full-language-switch-"_s + language);
    dialog->accept();
  });
  QVERIFY(QMetaObject::invokeMethod(&window, "onShowPreferencesDialog", Qt::DirectConnection));
  QVERIFY(preference_saved);
  QCOMPARE(PJ::AppLanguage::preferredLanguage(QSettings()), next_language);
  QCOMPARE(qApp->property("interfaceLanguage").toString(), language);
  QCOMPARE(status->text(), running_status);
}

int main(int argc, char** argv) {
  QApplication application(argc, argv);
  QCoreApplication::setOrganizationName(u"PlotJugglerFeedbackTests"_s);
  QCoreApplication::setApplicationName(u"PluginFeedback"_s);
  const QTemporaryDir profile;
  QString error;
  if (!profile.isValid() || !PJ::PlatformUtils::initializeProfile(profile.path(), &error)) {
    qCritical("Cannot initialize isolated acceptance profile: %s", qPrintable(error));
    return 1;
  }
  PJ::PlotWidgetBase::setOpenGlDisabledOverride(true);
  PluginFeedbackTest test;
  return QTest::qExec(&test, argc, argv);
}

#include "plugin_feedback_test.moc"
