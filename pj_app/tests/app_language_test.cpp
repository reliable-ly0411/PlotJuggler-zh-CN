// SPDX-License-Identifier: MPL-2.0
#include <QByteArray>
#include <QCoreApplication>
#include <QFile>
#include <QLocale>
#include <QSettings>
#include <QTemporaryDir>
#include <QTest>

#include "AppLanguage.h"

using namespace Qt::StringLiterals;

// Runs with Qt Core alone against the same resource-bearing static library as
// pj_app_shell. In particular, no loose .qm file is on the runtime search path.
class AppLanguageTest : public QObject {
  Q_OBJECT

 private slots:
  void normalizesSupportedLanguages_data() {
    QTest::addColumn<QString>("requested");
    QTest::addColumn<QString>("expected");
    QTest::newRow("chinese") << u"zh_CN"_s << u"zh_CN"_s;
    QTest::newRow("bcp47-chinese") << u"zh-CN"_s << u"zh_CN"_s;
    QTest::newRow("traditional-chinese") << u"zh_TW"_s << u"zh_TW"_s;
    QTest::newRow("bcp47-traditional-chinese") << u"zh-TW"_s << u"zh_TW"_s;
    QTest::newRow("english") << u"en_US"_s << u"en_US"_s;
    QTest::newRow("bcp47-english") << u"en-US"_s << u"en_US"_s;
    QTest::newRow("unsupported") << u"fr_FR"_s << u"en_US"_s;
    QTest::newRow("unsupported-region") << u"zh_HK"_s << u"en_US"_s;
    QTest::newRow("ambiguous-chinese") << u"zh"_s << u"en_US"_s;
    QTest::newRow("script-without-region") << u"zh-Hant"_s << u"en_US"_s;
    QTest::newRow("empty") << QString{} << u"en_US"_s;
  }

  void normalizesSupportedLanguages() {
    QFETCH(QString, requested);
    QFETCH(QString, expected);
    QCOMPARE(PJ::AppLanguage::normalizedLanguage(requested), expected);
  }

  void languageChoicesHaveDistinctEndonymsAndCanonicalCodes() {
    const auto choices = PJ::AppLanguage::supportedLanguages();
    QCOMPARE(choices.size(), 3);
    QCOMPARE(choices.at(0).code, u"zh_CN"_s);
    QCOMPARE(choices.at(0).native_name, u"简体中文"_s);
    QCOMPARE(choices.at(1).code, u"zh_TW"_s);
    QCOMPARE(choices.at(1).native_name, u"繁體中文（台灣）"_s);
    QCOMPARE(choices.at(2).code, u"en_US"_s);
    for (const auto& choice : choices) {
      QCOMPARE(PJ::AppLanguage::normalizedLanguage(choice.code), choice.code);
    }
  }

  void pluginLanguageHintMatchesStartupAndRestoresEnvironment() {
    const bool existed = qEnvironmentVariableIsSet("PLOTJUGGLER_UI_LANGUAGE");
    const QByteArray original = qgetenv("PLOTJUGGLER_UI_LANGUAGE");
    qputenv("PLOTJUGGLER_UI_LANGUAGE", "external-original");
    {
      const PJ::AppLanguage chinese(*QCoreApplication::instance(), u"zh-CN"_s);
      QCOMPARE(qgetenv("PLOTJUGGLER_UI_LANGUAGE"), QByteArray("zh_CN"));
    }
    QCOMPARE(qgetenv("PLOTJUGGLER_UI_LANGUAGE"), QByteArray("external-original"));
    {
      const PJ::AppLanguage traditional(*QCoreApplication::instance(), u"zh-TW"_s);
      QCOMPARE(qgetenv("PLOTJUGGLER_UI_LANGUAGE"), QByteArray("zh_TW"));
    }
    QCOMPARE(qgetenv("PLOTJUGGLER_UI_LANGUAGE"), QByteArray("external-original"));
    qunsetenv("PLOTJUGGLER_UI_LANGUAGE");
    {
      const PJ::AppLanguage english(*QCoreApplication::instance(), u"en_US"_s);
      QCOMPARE(qgetenv("PLOTJUGGLER_UI_LANGUAGE"), QByteArray("en_US"));
    }
    QVERIFY(!qEnvironmentVariableIsSet("PLOTJUGGLER_UI_LANGUAGE"));
    if (existed) {
      qputenv("PLOTJUGGLER_UI_LANGUAGE", original);
    }
  }

  void freshProfileDefaultsToChineseWithoutWritingSettings() {
    QTemporaryDir directory;
    QVERIFY(directory.isValid());
    const QSettings settings(directory.filePath(u"preferences.ini"_s), QSettings::IniFormat);
    QCOMPARE(PJ::AppLanguage::preferredLanguage(settings), u"zh_CN"_s);
    QVERIFY(!settings.contains(PJ::AppLanguage::kPreferenceKey));
  }

  void savedLanguageSurvivesANewSettingsInstance() {
    QTemporaryDir directory;
    QVERIFY(directory.isValid());
    const QString path = directory.filePath(u"preferences.ini"_s);
    {
      QSettings settings(path, QSettings::IniFormat);
      settings.setValue(PJ::AppLanguage::kPreferenceKey, u"en_US"_s);
      settings.sync();
      QCOMPARE(settings.status(), QSettings::NoError);
    }
    const QSettings settings(path, QSettings::IniFormat);
    QCOMPARE(PJ::AppLanguage::preferredLanguage(settings), u"en_US"_s);
  }

  void traditionalPreferenceSurvivesRestartAndSessionOverride() {
    QTemporaryDir directory;
    QVERIFY(directory.isValid());
    const QString path = directory.filePath(u"preferences.ini"_s);
    {
      QSettings settings(path, QSettings::IniFormat);
      settings.setValue(PJ::AppLanguage::kPreferenceKey, u"zh_TW"_s);
      settings.sync();
      QCOMPARE(settings.status(), QSettings::NoError);
    }
    const QSettings settings(path, QSettings::IniFormat);
    QCOMPARE(PJ::AppLanguage::preferredLanguage(settings), u"zh_TW"_s);
    {
      const PJ::AppLanguage english(*QCoreApplication::instance(), u"en_US"_s);
      QCOMPARE(PJ::AppLanguage::preferredLanguage(settings), u"zh_TW"_s);
      QCOMPARE(QCoreApplication::translate("PreferencesContent", "Language:"), u"Language:"_s);
    }
    const PJ::AppLanguage restarted(*QCoreApplication::instance(), PJ::AppLanguage::preferredLanguage(settings));
    QVERIFY(restarted.catalogLoaded());
    QCOMPARE(restarted.language(), u"zh_TW"_s);
    QCOMPARE(QCoreApplication::translate("PreferencesContent", "Language:"), u"語言："_s);
  }

  void traditionalCatalogUsesTaiwanTermsWithoutLeakingIntoOtherLanguages() {
    for (int repeat = 0; repeat < 2; ++repeat) {
      {
        const PJ::AppLanguage traditional(*QCoreApplication::instance(), u"zh_TW"_s);
        QVERIFY(traditional.catalogLoaded());
        QVERIFY(QFile::exists(u":/i18n/plotjuggler4_zh_TW.qm"_s));
        QCOMPARE(QCoreApplication::instance()->property("interfaceLanguage").toString(), u"zh_TW"_s);
        QCOMPARE(QCoreApplication::translate("PJ::DockWidget", "Plot"), u"繪圖"_s);
        QCOMPARE(QCoreApplication::translate("QPlatformTheme", "Save"), u"儲存"_s);
        QCOMPARE(QCoreApplication::translate("QPlatformTheme", "Cancel"), u"取消"_s);
        QCOMPARE(QCoreApplication::translate("QAbstractFileIconProvider", "File"), u"檔案"_s);
        QCOMPARE(QCoreApplication::translate("QAbstractFileIconProvider", "Folder", "All other platforms"),
                 u"資料夾"_s);
        const QString path = u"/資料/%2/{raw}/測試.bin"_s;
        const QString source = u"Cannot read \"%1\""_s;
        const QString translated = QCoreApplication::translate("PJ::MarketplaceDiagnostics", "Cannot read \"%1\"");
        QVERIFY(translated != source);
        QVERIFY(translated.arg(path).contains(path));
      }
      QCOMPARE(QCoreApplication::translate("PJ::DockWidget", "Plot"), u"Plot"_s);
      {
        const PJ::AppLanguage simplified(*QCoreApplication::instance(), u"zh_CN"_s);
        QCOMPARE(QCoreApplication::translate("PJ::DockWidget", "Plot"), u"绘图"_s);
        QCOMPARE(QCoreApplication::translate("QPlatformTheme", "Save"), u"保存"_s);
      }
      const PJ::AppLanguage unsupported(*QCoreApplication::instance(), u"zh_HK"_s);
      QVERIFY(!unsupported.catalogLoaded());
      QCOMPARE(QCoreApplication::translate("QPlatformTheme", "Save"), u"Save"_s);
    }
  }

  void invalidSavedLanguageFallsBackWithoutOverwritingIt() {
    QTemporaryDir directory;
    QVERIFY(directory.isValid());
    QSettings settings(directory.filePath(u"preferences.ini"_s), QSettings::IniFormat);
    settings.setValue(PJ::AppLanguage::kPreferenceKey, u"unsupported"_s);
    QCOMPARE(PJ::AppLanguage::preferredLanguage(settings), u"en_US"_s);
    QCOMPARE(settings.value(PJ::AppLanguage::kPreferenceKey).toString(), u"unsupported"_s);
  }

  void shippedCatalogTranslatesWidgetsAndQtButtons() {
    const PJ::AppLanguage language(*QCoreApplication::instance(), u"zh_CN"_s);
    QVERIFY(language.catalogLoaded());
    QVERIFY(QFile::exists(u":/i18n/plotjuggler4_zh_CN.qm"_s));
    QCOMPARE(QCoreApplication::translate("PJ::DockWidget", "Plot"), u"绘图"_s);
    QCOMPARE(QCoreApplication::translate("PJ::TabbedPlotWidget", "tab%1").arg(2), u"标签页2"_s);
    QCOMPARE(language.language(), u"zh_CN"_s);
    QCOMPARE(QCoreApplication::instance()->property("interfaceLanguage").toString(), u"zh_CN"_s);
    const QString label = QCoreApplication::translate("PreferencesContent", "Language:");
    QVERIFY(!label.isEmpty());
    QVERIFY(label != "Language:"_L1);
    const QString title = QCoreApplication::translate("PJ::PreferencesDialog", "Preferences");
    QVERIFY(!title.isEmpty());
    QVERIFY(title != "Preferences"_L1);
    QCOMPARE(QCoreApplication::translate("QPlatformTheme", "Cancel"), u"取消"_s);
  }

  void diagnosticTemplatesPreserveDynamicData() {
    const QString path = u"/tmp/原始 logs/Checksum mismatch.bin"_s;
    {
      const PJ::AppLanguage chinese(*QCoreApplication::instance(), u"zh_CN"_s);
      QVERIFY(chinese.catalogLoaded());
      QCOMPARE(
          QCoreApplication::translate("PJ::MarketplaceDiagnostics", "Cannot read \"%1\"").arg(path),
          u"无法读取“%1”"_s.arg(path));
      QCOMPARE(QCoreApplication::translate("PJ::MarketplaceDiagnostics", "Checksum mismatch"), u"校验和不匹配"_s);
      QCOMPARE(
          QCoreApplication::translate("PJ::ArchiveDiagnostics", "archive holds more than %1 entries").arg(123),
          u"压缩包包含的条目数超过 123"_s);
      QCOMPARE(
          QCoreApplication::translate("pj::scene3d::UrdfParser", "Parse error: <robot> has no <link> elements"),
          u"解析错误：<robot> 中没有 <link> 元素"_s);
      QCOMPARE(
          QCoreApplication::translate("pj::scene3d::MeshDiagnostics", "mesh load threw: %1").arg(path),
          u"加载网格时发生异常：%1"_s.arg(path));
    }
    const PJ::AppLanguage english(*QCoreApplication::instance(), u"en_US"_s);
    QCOMPARE(
        QCoreApplication::translate("PJ::MarketplaceDiagnostics", "Cannot read \"%1\"").arg(path),
        u"Cannot read \"%1\""_s.arg(path));
  }

  void embeddedCatalogTranslatesCurrentQtFileDialogKeys_data() {
    QTest::addColumn<QByteArray>("context");
    QTest::addColumn<QByteArray>("source");
    QTest::addColumn<QByteArray>("comment");
    QTest::addColumn<QString>("expected");
    QTest::newRow("QFileDialog-0") << QByteArray("QFileDialog") << QByteArray("&Look in:") << QByteArray("")
                                   << u"查找范围(&L)："_s;
    QTest::newRow("QFileDialog-1") << QByteArray("QFileDialog") << QByteArray("Files of &type:") << QByteArray("")
                                   << u"文件类型(&T)："_s;
    QTest::newRow("QAbstractFileIconProvider-2")
        << QByteArray("QAbstractFileIconProvider") << QByteArray("Drive") << QByteArray("") << u"驱动器"_s;
    QTest::newRow("QAbstractFileIconProvider-3")
        << QByteArray("QAbstractFileIconProvider") << QByteArray("File") << QByteArray("") << u"文件"_s;
    QTest::newRow("QAbstractFileIconProvider-4")
        << QByteArray("QAbstractFileIconProvider") << QByteArray("Unknown") << QByteArray("") << u"未知"_s;
    QTest::newRow("QAbstractFileIconProvider-5") << QByteArray("QAbstractFileIconProvider") << QByteArray("File Folder")
                                                 << QByteArray("Match Windows Explorer") << u"文件夹"_s;
    QTest::newRow("QAbstractFileIconProvider-6") << QByteArray("QAbstractFileIconProvider") << QByteArray("Folder")
                                                 << QByteArray("All other platforms") << u"文件夹"_s;
    QTest::newRow("QAbstractFileIconProvider-7")
        << QByteArray("QAbstractFileIconProvider") << QByteArray("Alias") << QByteArray("macOS Finder") << u"替身"_s;
    QTest::newRow("QAbstractFileIconProvider-8") << QByteArray("QAbstractFileIconProvider") << QByteArray("Shortcut")
                                                 << QByteArray("All other platforms") << u"快捷方式"_s;
  }

  void embeddedCatalogTranslatesCurrentQtFileDialogKeys() {
    QFETCH(QByteArray, context);
    QFETCH(QByteArray, source);
    QFETCH(QByteArray, comment);
    QFETCH(QString, expected);
    const char* disambiguation = comment.isEmpty() ? nullptr : comment.constData();
    {
      const PJ::AppLanguage chinese(*QCoreApplication::instance(), u"zh_CN"_s);
      QVERIFY(chinese.catalogLoaded());
      QCOMPARE(QCoreApplication::translate(context.constData(), source.constData(), disambiguation), expected);
    }
    const PJ::AppLanguage english(*QCoreApplication::instance(), u"en_US"_s);
    QCOMPARE(
        QCoreApplication::translate(context.constData(), source.constData(), disambiguation),
        QString::fromUtf8(source));
  }

  void englishUsesSourceTextAndDoesNotOverwriteThePreference() {
    QTemporaryDir directory;
    QVERIFY(directory.isValid());
    QSettings settings(directory.filePath(u"preferences.ini"_s), QSettings::IniFormat);
    settings.setValue(PJ::AppLanguage::kPreferenceKey, u"zh_CN"_s);
    const PJ::AppLanguage language(*QCoreApplication::instance(), u"en_US"_s);
    QVERIFY(!language.catalogLoaded());
    QCOMPARE(language.language(), u"en_US"_s);
    QCOMPARE(QCoreApplication::translate("PreferencesContent", "Language:"), u"Language:"_s);
    QCOMPARE(PJ::AppLanguage::preferredLanguage(settings), u"zh_CN"_s);
  }

  void translatorLifetimeDoesNotLeakIntoEnglishStartup() {
    {
      const PJ::AppLanguage chinese(*QCoreApplication::instance(), u"zh_CN"_s);
      QVERIFY(chinese.catalogLoaded());
      QVERIFY(QCoreApplication::translate("PreferencesContent", "Language:") != "Language:"_L1);
    }
    const PJ::AppLanguage english(*QCoreApplication::instance(), u"en_US"_s);
    QCOMPARE(QCoreApplication::translate("PreferencesContent", "Language:"), u"Language:"_s);
    QCOMPARE(QCoreApplication::translate("QPlatformTheme", "Cancel"), u"Cancel"_s);
  }

  void repeatedChineseStartupDoesNotAccumulateTranslators() {
    for (int launch = 0; launch < 3; ++launch) {
      {
        const PJ::AppLanguage chinese(*QCoreApplication::instance(), u"zh_CN"_s);
        QVERIFY(chinese.catalogLoaded());
        QVERIFY(QCoreApplication::translate("PreferencesContent", "Language:") != "Language:"_L1);
      }
      QCOMPARE(QCoreApplication::translate("PreferencesContent", "Language:"), u"Language:"_s);
    }
  }

  void changingThePreferenceNeedsANewStartup() {
    QTemporaryDir directory;
    QVERIFY(directory.isValid());
    QSettings settings(directory.filePath(u"preferences.ini"_s), QSettings::IniFormat);
    {
      const PJ::AppLanguage language(*QCoreApplication::instance(), PJ::AppLanguage::preferredLanguage(settings));
      QVERIFY(language.catalogLoaded());
      settings.setValue(PJ::AppLanguage::kPreferenceKey, u"en_US"_s);
      QCOMPARE(language.language(), u"zh_CN"_s);
      QVERIFY(QCoreApplication::translate("PreferencesContent", "Language:") != "Language:"_L1);
    }
    const PJ::AppLanguage restarted(*QCoreApplication::instance(), PJ::AppLanguage::preferredLanguage(settings));
    QCOMPARE(restarted.language(), u"en_US"_s);
    QCOMPARE(QCoreApplication::translate("PreferencesContent", "Language:"), u"Language:"_s);
  }

  void interfaceLanguagePreservesTheNumericLocale() {
    const QLocale original;
    for (const QString& code : {u"zh_CN"_s, u"zh_TW"_s, u"en_US"_s}) {
      const PJ::AppLanguage language(*QCoreApplication::instance(), code);
      QCOMPARE(QLocale(), original);
      QCOMPARE(QLocale().toString(1234.5), original.toString(1234.5));
    }
  }
};

QTEST_GUILESS_MAIN(AppLanguageTest)
#include "app_language_test.moc"
