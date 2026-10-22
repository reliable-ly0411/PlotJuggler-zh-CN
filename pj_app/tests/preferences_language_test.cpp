// SPDX-License-Identifier: MPL-2.0
#include <gtest/gtest.h>

#include <QApplication>
#include <QComboBox>
#include <QDir>
#include <QFontMetrics>
#include <QImage>
#include <QLabel>
#include <QMenu>
#include <QPixmap>
#include <QScrollArea>
#include <QSettings>
#include <QStackedWidget>
#include <QTemporaryDir>
#include <QTest>
#include <iomanip>

#include "AppLanguage.h"
#include "MainWindow.h"
#include "PreferencesDialog.h"
#include "Theme.h"
#include "TitleBar.h"
#include "support/gui_test_env.h"

using namespace Qt::StringLiterals;

namespace {

// Optional CI artifacts contain only this process's synthetic data and private
// profile. The pixel grab is exercised locally too, without writing screenshots.
void captureAcceptance(QWidget& widget, const QString& name) {
  widget.show();
  QTest::qWait(100);
  ASSERT_TRUE(widget.isVisible());
  const QImage image = widget.grab().toImage();
  ASSERT_FALSE(image.isNull());
  const QString directory = qEnvironmentVariable("PJ_GUI_ACCEPTANCE_DIR");
  if (!directory.isEmpty()) {
    ASSERT_TRUE(QDir().mkpath(directory));
    EXPECT_TRUE(image.save(QDir(directory).filePath(name + u".png"_s), "PNG"));
  }
  // A nonempty screenshot and correct translated strings can still contain
  // only missing-glyph boxes when a headless platform has no font database.
  const QFontMetrics metrics(widget.font());
  for (const auto codepoint : u"PlotJuggler中文文件语言首选项"_s.toUcs4()) {
    EXPECT_TRUE(metrics.inFontUcs4(codepoint)) << "Missing UI glyph U+" << std::hex << codepoint;
  }
}

// Use the actual shell and its menu widget, not translation lookups alone. Each
// discovered test owns a fresh process, as required by MainWindow teardown.
void renderMainWindow(const QString& language) {
  const PJ::AppLanguage running(*qApp, language);
  EXPECT_EQ(running.catalogLoaded(), language == u"zh_CN"_s);
  const QTemporaryDir extensions;
  ASSERT_TRUE(extensions.isValid());
  PJ::MainWindow window(extensions.path());
  ASSERT_TRUE(window.populateTestData());
  window.resize(1280, 800);
  const QString file_title = window.titleBar()->fileMenu()->title();
  if (language == u"zh_CN"_s) {
    EXPECT_NE(file_title, u"&File"_s);
    EXPECT_EQ(file_title, QCoreApplication::translate("PJ::TitleBar", "&File"));
  } else {
    EXPECT_EQ(file_title, u"&File"_s);
  }
  captureAcceptance(window, u"main-window-"_s + language);
}

void renderPreferences(const QString& language) {
  const PJ::AppLanguage running(*qApp, language);
  PJ::Theme theme;
  PJ::PreferencesDialog dialog(theme);
  dialog.showPage(PJ::PreferencesDialog::kAppearancePage);
  const auto* label = dialog.findChild<QLabel*>(u"labelLanguage"_s);
  ASSERT_NE(label, nullptr);
  if (language == u"zh_CN"_s) {
    EXPECT_NE(label->text(), u"Language:"_s);
    EXPECT_EQ(label->text(), QCoreApplication::translate("PreferencesContent", "Language:"));
  } else {
    EXPECT_EQ(label->text(), u"Language:"_s);
  }
  captureAcceptance(dialog, u"preferences-"_s + language);
  EXPECT_TRUE(label->isVisible());
  const auto* combo = dialog.findChild<QComboBox*>(u"languageCombo"_s);
  ASSERT_NE(combo, nullptr);
  EXPECT_TRUE(combo->isVisible());
}

TEST(PreferencesLanguageTest, ChineseMainWindowRendersWithTranslatedMenus) {
  renderMainWindow(u"zh_CN"_s);
}

TEST(PreferencesLanguageTest, EnglishMainWindowRendersWithSourceMenus) {
  renderMainWindow(u"en_US"_s);
}

TEST(PreferencesLanguageTest, ChinesePreferencesRendersLanguageControls) {
  renderPreferences(u"zh_CN"_s);
}

TEST(PreferencesLanguageTest, EnglishPreferencesRendersLanguageControls) {
  renderPreferences(u"en_US"_s);
}

TEST(PreferencesLanguageTest, FreshProfileOffersChineseAndEnglishWithARestartNotice) {
  PJ::Theme theme;
  PJ::PreferencesDialog dialog(theme);
  const auto* combo = dialog.findChild<QComboBox*>(u"languageCombo"_s);
  ASSERT_NE(combo, nullptr);
  ASSERT_EQ(combo->count(), 2);
  EXPECT_EQ(combo->currentData().toString(), u"zh_CN"_s);
  EXPECT_EQ(combo->itemData(1).toString(), u"en_US"_s);
  const auto* notice = dialog.findChild<QLabel*>(u"labelLanguageRestart"_s);
  ASSERT_NE(notice, nullptr);
  EXPECT_FALSE(notice->text().isEmpty());
}

TEST(PreferencesLanguageTest, AcceptSavesNextLaunchLanguageWithoutRetranslatingTheSession) {
  const PJ::AppLanguage running(*qApp, u"zh_CN"_s);
  ASSERT_TRUE(running.catalogLoaded());
  PJ::Theme theme;
  {
    PJ::PreferencesDialog dialog(theme);
    auto* combo = dialog.findChild<QComboBox*>(u"languageCombo"_s);
    ASSERT_NE(combo, nullptr);
    combo->setCurrentIndex(combo->findData(u"en_US"_s));
    EXPECT_FALSE(QSettings().contains(PJ::AppLanguage::kPreferenceKey));
    dialog.accept();
  }
  EXPECT_EQ(QSettings().value(PJ::AppLanguage::kPreferenceKey).toString(), u"en_US"_s);
  EXPECT_EQ(qApp->property("interfaceLanguage").toString(), u"zh_CN"_s);
  EXPECT_NE(QCoreApplication::translate("PreferencesContent", "Language:"), u"Language:"_s);
  PJ::PreferencesDialog reopened(theme);
  const auto* combo = reopened.findChild<QComboBox*>(u"languageCombo"_s);
  ASSERT_NE(combo, nullptr);
  EXPECT_EQ(combo->currentData().toString(), u"en_US"_s);
}

TEST(PreferencesLanguageTest, CancelLeavesTheSavedLanguageAlone) {
  QSettings().setValue(PJ::AppLanguage::kPreferenceKey, u"en_US"_s);
  PJ::Theme theme;
  {
    PJ::PreferencesDialog dialog(theme);
    auto* combo = dialog.findChild<QComboBox*>(u"languageCombo"_s);
    ASSERT_NE(combo, nullptr);
    EXPECT_EQ(combo->currentData().toString(), u"en_US"_s);
    combo->setCurrentIndex(combo->findData(u"zh_CN"_s));
    dialog.reject();
  }
  EXPECT_EQ(QSettings().value(PJ::AppLanguage::kPreferenceKey).toString(), u"en_US"_s);
}

TEST(PreferencesLanguageTest, SessionOverrideDoesNotChangeTheNextLaunchSelection) {
  const PJ::AppLanguage running(*qApp, u"en_US"_s);
  PJ::Theme theme;
  PJ::PreferencesDialog dialog(theme);
  const auto* combo = dialog.findChild<QComboBox*>(u"languageCombo"_s);
  ASSERT_NE(combo, nullptr);
  EXPECT_EQ(combo->currentData().toString(), u"zh_CN"_s);
  EXPECT_EQ(qApp->property("interfaceLanguage").toString(), u"en_US"_s);
}

TEST(PreferencesLanguageTest, MinimumSizeKeepsTranslatedAppearanceControlsReachable) {
  for (const QString& requested : {u"en_US"_s, u"zh_CN"_s}) {
    SCOPED_TRACE(requested.toStdString());
    const PJ::AppLanguage running(*qApp, requested);
    EXPECT_EQ(running.catalogLoaded(), requested == u"zh_CN"_s);
    PJ::Theme theme;
    PJ::PreferencesDialog dialog(theme);
    dialog.resize(420, 300);
    dialog.show();
    QTest::qWait(20);
    ASSERT_EQ(dialog.size(), QSize(420, 300));
    auto* pages = dialog.findChild<QStackedWidget*>(u"pagesStack"_s);
    auto* scroll = dialog.findChild<QScrollArea*>(u"appearanceScrollArea"_s);
    auto* label = dialog.findChild<QLabel*>(u"labelLanguage"_s);
    auto* combo = dialog.findChild<QComboBox*>(u"languageCombo"_s);
    auto* notice = dialog.findChild<QLabel*>(u"labelLanguageRestart"_s);
    auto* last_control = dialog.findChild<QWidget*>(u"telemetryToggle"_s);
    ASSERT_NE(pages, nullptr);
    ASSERT_NE(scroll, nullptr);
    ASSERT_NE(label, nullptr);
    ASSERT_NE(combo, nullptr);
    ASSERT_NE(notice, nullptr);
    ASSERT_NE(last_control, nullptr);
    EXPECT_EQ(pages->widget(PJ::PreferencesDialog::kAppearancePage), scroll);
    dialog.showPage(PJ::PreferencesDialog::kPluginsPage);
    ASSERT_NE(pages->currentWidget(), nullptr);
    EXPECT_EQ(pages->currentWidget()->objectName(), u"pagePlugins"_s);
    dialog.showPage(PJ::PreferencesDialog::kAppearancePage);
    EXPECT_EQ(pages->currentWidget(), scroll);
    EXPECT_GE(combo->width(), combo->minimumSizeHint().width());
    EXPECT_GE(notice->height(), notice->heightForWidth(notice->width()));
    for (QWidget* control :
         {static_cast<QWidget*>(label), static_cast<QWidget*>(combo), static_cast<QWidget*>(notice), last_control}) {
      scroll->ensureWidgetVisible(control, 0, 0);
      QCoreApplication::processEvents();
      EXPECT_TRUE(control->isVisible());
      const QRect visible_rect(control->mapTo(scroll->viewport(), QPoint(0, 0)), control->size());
      EXPECT_TRUE(scroll->viewport()->rect().contains(visible_rect)) << control->objectName().toStdString();
    }
    dialog.reject();
  }
}

// Each discovered case gets a private settings file, like the other shell
// preference tests, without touching the user's actual application profile.
class LanguageSettingsEnvironment : public ::testing::Environment {
 public:
  void SetUp() override {
    if (!pj_app_test::isTestSuiteSelected("PreferencesLanguageTest")) {
      return;
    }
    QCoreApplication::setOrganizationName(u"PlotJugglerTest"_s);
    QCoreApplication::setApplicationName(u"preferences_language_test"_s);
    QSettings::setDefaultFormat(QSettings::IniFormat);
    QSettings::setPath(QSettings::IniFormat, QSettings::UserScope, settings_dir_.path());
  }

 private:
  QTemporaryDir settings_dir_;
};

static auto* const kLanguageEnv = ::testing::AddGlobalTestEnvironment(new LanguageSettingsEnvironment);

}  // namespace
