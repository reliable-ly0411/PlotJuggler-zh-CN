// SPDX-License-Identifier: MPL-2.0
#include <gtest/gtest.h>

#include <QApplication>
#include <QComboBox>
#include <QLabel>
#include <QSettings>
#include <QTemporaryDir>

#include "AppLanguage.h"
#include "PreferencesDialog.h"
#include "Theme.h"
#include "support/gui_test_env.h"

using namespace Qt::StringLiterals;

namespace {

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
