// SPDX-License-Identifier: MPL-2.0
#include <QByteArray>
#include <QCoreApplication>
#include <QFile>
#include <QLocale>
#include <QSettings>
#include <QTemporaryDir>
#include <QTest>

#include "../../pj_widgets/include/pj_widgets/BundledPluginText.h"
#include "AppLanguage.h"

using namespace Qt::StringLiterals;

// Runs with Qt Core alone against the same resource-bearing static library as
// pj_app_shell. In particular, no loose .qm file is on the runtime search path.
class AppLanguageTest : public QObject {
  Q_OBJECT

 private slots:
  void fixedCsvDiagnosticsPreserveExactSdkDomainAndUnknownValues() {
    const QStringList errors = {
        u"invalid config JSON"_s, u"invalid config"_s, u"no filepath configured"_s, u"CSV parsing failed"_s,
        u"Loading aborted by user"_s};
    for (const QString& language : {u"zh_CN"_s, u"zh_TW"_s, u"en_US"_s}) {
      const PJ::AppLanguage selected(*QCoreApplication::instance(), language);
      for (const QString& error : errors) {
        const QString translated = QCoreApplication::translate("PJ::BundledPluginDiagnostics", error.toUtf8());
        QCOMPARE(PJ::bundledPluginError(u"csv-loader"_s, u"1.0.7"_s, error), translated);
        QCOMPARE(
            PJ::bundledPluginError(u"csv-loader"_s, u"1.0.7"_s, u"plugin: "_s + error), u"plugin: "_s + translated);
        if (language != u"en_US"_s) {
          QVERIFY(translated != error);
        }
        for (const QString& id : {u"unknown"_s, u"CSV Loader"_s}) {
          QCOMPARE(PJ::bundledPluginError(id, u"1.0.7"_s, u"plugin: "_s + error), u"plugin: "_s + error);
        }
        QCOMPARE(PJ::bundledPluginError(u"csv-loader"_s, u"1.0.8"_s, u"plugin: "_s + error), u"plugin: "_s + error);
        for (const QString& prefix : {u"other: "_s, u"plugin: plugin: "_s, u"plugin:"_s}) {
          QCOMPARE(PJ::bundledPluginError(u"csv-loader"_s, u"1.0.7"_s, prefix + error), prefix + error);
        }
      }
      const QString unknown = u"plugin: cannot open file: /資料/%1/'CSV parsing failed'.csv"_s;
      QCOMPARE(PJ::bundledPluginError(u"csv-loader"_s, u"1.0.7"_s, unknown), unknown);
      QCOMPARE(
          PJ::bundledPluginError(u"csv-loader"_s, u"1.0.7"_s, u"plugin: CSV parsing failed\n"_s),
          u"plugin: CSV parsing failed\n"_s);
    }
  }

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
        QCOMPARE(
            QCoreApplication::translate("QAbstractFileIconProvider", "Folder", "All other platforms"), u"資料夾"_s);
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

  void clockControlsAndBrowserReadErrorsUseTheirLiveContexts_data() {
    QTest::addColumn<QString>("language");
    QTest::addColumn<QString>("local_label");
    QTest::addColumn<QString>("zone_label");
    QTest::newRow("simplified") << u"zh_CN"_s << u"本地"_s << u"时钟时区："_s;
    QTest::newRow("traditional") << u"zh_TW"_s << u"本機"_s << u"時鐘時區："_s;
  }

  void clockControlsAndBrowserReadErrorsUseTheirLiveContexts() {
    QFETCH(QString, language);
    QFETCH(QString, local_label);
    QFETCH(QString, zone_label);
    const QLocale data_locale;
    const PJ::AppLanguage selected(*QCoreApplication::instance(), language);
    QVERIFY(selected.catalogLoaded());
    QCOMPARE(QCoreApplication::translate("PJ::PreferencesDialog", "local"), local_label);
    QCOMPARE(QCoreApplication::translate("PJ::PreferencesDialog", "UTC"), u"UTC"_s);
    QCOMPARE(QCoreApplication::translate("PreferencesContent", "Clock time zone:"), zone_label);
    const char* offset =
        "Use time offset: show time relative to each dataset's start (axis begins at 0) "
        "instead of absolute time";
    QVERIFY(QCoreApplication::translate("TimelineWidget", offset) != QString::fromUtf8(offset));
    QCOMPARE(QCoreApplication::translate("PJ::MainWindow", offset), QString::fromUtf8(offset));
    const char* clock = "Show time as clock time (HH:mm:ss) instead of seconds";
    const QString translated_clock = QCoreApplication::translate("TimelineWidget", clock);
    QVERIFY(translated_clock != QString::fromUtf8(clock));
    QVERIFY(translated_clock.contains(u"HH:mm:ss"_s));
    const char* read_error = "The browser could not read %1 (moved or changed since it was picked?).";
    const QString translated_error = QCoreApplication::translate("PJ::FileSelectionService", read_error);
    QVERIFY(translated_error != QString::fromUtf8(read_error));
    const QString browser_name = u"原始資料 %2 测试.bin"_s;
    QVERIFY(translated_error.arg(browser_name).contains(browser_name));
    QCOMPARE(QLocale(), data_locale);
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
          QCoreApplication::translate("pj::scene3d::MeshDiagnostics", "mesh import threw: %1").arg(path),
          u"网格导入时发生异常：%1"_s.arg(path));
    }
    const PJ::AppLanguage english(*QCoreApplication::instance(), u"en_US"_s);
    QCOMPARE(
        QCoreApplication::translate("PJ::MarketplaceDiagnostics", "Cannot read \"%1\"").arg(path),
        u"Cannot read \"%1\""_s.arg(path));
  }

  void reviewedTranslationBackport() {
    {
      const PJ::AppLanguage language(*QCoreApplication::instance(), u"zh_CN"_s);
      QCOMPARE(QCoreApplication::translate("CurveListPanel", "Custom Topics", nullptr, -1), u"自定义话题"_s);
      QCOMPARE(QCoreApplication::translate("CurveListPanel", "Add custom topic", nullptr, -1), u"添加自定义话题"_s);
      QCOMPARE(
          QCoreApplication::translate("CurveListPanel", "Edit the selected custom topic", nullptr, -1),
          u"编辑选中的自定义话题"_s);
      QCOMPARE(
          QCoreApplication::translate("CurveListPanel", "Custom topics options", nullptr, -1), u"自定义话题选项"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "DatasetMergeActions",
              "These object topics share a name but have incompatible types, formats or marker descriptions, so the "
              "datasets cannot be merged:",
              nullptr, -1),
          u"这些对象话题名称相同，但类型、格式或标记描述不兼容，因此无法合并数据集："_s);
      QCOMPARE(
          QCoreApplication::translate("PJ::CurveListPanel", "Edit the selected custom topic", nullptr, -1),
          u"编辑选中的自定义话题"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::DockWidget", "%1 topics cannot be displayed on their own, but a plugin panel can read them.",
              nullptr, -1),
          u"%1 个话题无法单独显示，但插件面板可以读取它们。"_s);
      QCOMPARE(
          QCoreApplication::translate("PJ::MainWindow", "Delete derived topic?", nullptr, -1), u"删除派生话题？"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::MainWindow",
              "These derived topics read what you are deleting. They stay, but report a missing input:\n\n• %1",
              nullptr, -1),
          u"以下派生话题读取了将要删除的内容。它们会保留，但会报告缺少输入：\n\n• %1"_s);
      QCOMPARE(QCoreApplication::translate("PJ::Scene3DConfigPanel", "Topics", nullptr, -1), u"话题"_s);
      QCOMPARE(QCoreApplication::translate("PJ::Scene3DConfigPanel", "Topic", nullptr, -1), u"话题"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::SceneDockWidget", "This view shows dataset %1; a topic from dataset %2 cannot be added to it.",
              nullptr, -1),
          u"此视图显示数据集 %1；无法向其中添加数据集 %2 的话题。"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "QObject",
              "Camera calibration topic, used automatically by 2D and 3D views. It cannot be displayed on its own, but "
              "a plugin panel can read it.",
              nullptr, -1),
          u"相机标定话题，由二维和三维视图自动使用。无法单独显示，但插件面板可以读取。"_s);
      QCOMPARE(QCoreApplication::translate("pj::scene3d::RobotModelLayer", "Topic", nullptr, -1), u"话题"_s);
      QCOMPARE(QCoreApplication::translate("PJ::CurveListPanel", "Refresh derived", nullptr, -1), u"刷新派生标记"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PreferencesContent",
              "Automatic re-runs a changed marker rule on its own, at the reload rate below. Manual only flags it as "
              "needing a refresh, reachable from the dataset's \"Refresh derived\" action.",
              nullptr, -1),
          u"自动模式按下方的重新加载频率自动重新运行已更改的标记规则。手动模式仅将其标记为需要刷新，可通过数据集的“刷新派生标记”操作进行刷新。"_s);
      QCOMPARE(
          QCoreApplication::translate("PJ::MainWindow", "Show point in plot", nullptr, -1),
          u"显示光标处数据点的数值"_s);
      QCOMPARE(QCoreApplication::translate("DatasetMergeActions", "canonical %1", nullptr, -1), u"%1（规范格式）"_s);
      QCOMPARE(
          QCoreApplication::translate("PJ::ExtensionManager", "Not available for this platform (%1)", nullptr, -1),
          u"不适用于此平台（%1）"_s);
      QCOMPARE(QCoreApplication::translate("PJ::SourcePromotionHost", "promoted", nullptr, -1), u"已转为文件数据源"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::MainWindow", "Failed to publish the source-promotion service for '%1': %2", nullptr, -1),
          u"无法为“%1”发布数据源转换服务：%2"_s);
      QCOMPARE(
          QCoreApplication::translate("PJ::Scene3DConfigPanel", "Meshes opacity", nullptr, -1), u"模型网格不透明度"_s);
      QCOMPARE(
          QCoreApplication::translate("PJ::Scene3DConfigPanel", "Show/hide visual meshes", nullptr, -1),
          u"显示或隐藏外观模型网格"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::Scene3DDockWidget",
              "Only depth-encoded images can be displayed in a 3D view. Use a 2D view for colour images.", nullptr, -1),
          u"三维视图只能显示深度编码图像。彩色图像请使用二维视图。"_s);
      QCOMPARE(
          QCoreApplication::translate("QObject", "SceneEntities decode received no snapshot", nullptr, -1),
          u"SceneEntities 解码未收到快照"_s);
      QCOMPARE(
          QCoreApplication::translate("QObject", "SceneEntities conversion failed: %1", nullptr, -1),
          u"SceneEntities 转换失败：%1"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "LayoutXml", "Data source '%1' is a file on a local machine, which a web layout cannot open.", nullptr,
              -1),
          u"数据源“%1”是本机文件，网络托管的布局无法打开。"_s);
      QCOMPARE(QCoreApplication::translate("LeftPanel", "Stream", nullptr, -1), u"数据流"_s);
      QCOMPARE(QCoreApplication::translate("LeftPanel", "Start streaming", nullptr, -1), u"开始接收数据流"_s);
      QCOMPARE(QCoreApplication::translate("LeftPanel", "Pause streaming", nullptr, -1), u"暂停接收数据流"_s);
      QCOMPARE(
          QCoreApplication::translate("LeftPanel", "Streaming buffer length (seconds)", nullptr, -1),
          u"数据流缓冲时长（秒）"_s);
      QCOMPARE(
          QCoreApplication::translate("LeftPanel", "Streaming buffer (seconds)", nullptr, -1), u"数据流缓冲（秒）"_s);
      QCOMPARE(QCoreApplication::translate("MarketplaceWindow", "Data Streamers", nullptr, -1), u"流数据插件"_s);
      QCOMPARE(
          QCoreApplication::translate("MarketplaceWindow", "Extensions that stream data continuously", nullptr, -1),
          u"用于持续接收数据流的扩展"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::CurveListPanel", "Not subscribed. Drop it into a view to start streaming.", nullptr, -1),
          u"尚未订阅。拖入视图即可开始接收数据流。"_s);
      QCOMPARE(
          QCoreApplication::translate("PJ::CurveListPanel", "Stop forced streaming", nullptr, -1),
          u"停止强制接收数据流"_s);
      QCOMPARE(
          QCoreApplication::translate("PJ::CurveListPanel", "Force topic streaming", nullptr, -1),
          u"强制接收话题数据流"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::ImageLayer",
              "Undistort the image using its matching CameraInfo. Turn off to show the raw image,\nfor example when "
              "the stream is already rectified.",
              nullptr, -1),
          u"使用匹配的 CameraInfo 对图像进行畸变校正。关闭此选项可显示原始图像，\n例如当数据流已经过校正时。"_s);
      QCOMPARE(QCoreApplication::translate("PJ::LeftPanel", "Resume streaming", nullptr, -1), u"恢复接收数据流"_s);
      QCOMPARE(QCoreApplication::translate("PJ::LeftPanel", "Pause streaming", nullptr, -1), u"暂停接收数据流"_s);
      QCOMPARE(QCoreApplication::translate("PJ::MainWindow", "Start Streaming", nullptr, -1), u"开始接收数据流"_s);
      QCOMPARE(QCoreApplication::translate("PJ::MainWindow", "Streaming", nullptr, -1), u"数据流"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::MainWindow", "Nothing to record: start a streaming source first.", nullptr, -1),
          u"没有可录制的内容：请先启动一个流式数据源。"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::MainWindow", "Layout '%1' records %n streaming source(s); the desktop loader does not start them.",
              nullptr, 7),
          u"布局“%1”包含 7 个流式数据源；桌面加载器不会启动它们。"_s);
      QCOMPARE(
          QCoreApplication::translate("PJ::MainWindow", "Stream '%1' cannot start: %2", nullptr, -1),
          u"数据流“%1”无法启动：%2"_s);
      QCOMPARE(
          QCoreApplication::translate("PJ::MainWindow", "Stream '%1' could not start: %2", nullptr, -1),
          u"数据流“%1”未能启动：%2"_s);
      QCOMPARE(
          QCoreApplication::translate("PJ::StreamingSourceManager", "No stream source selected.", nullptr, -1),
          u"未选择流式数据源。"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::StreamingSourceManager", "Stream plugin '%1' is not installed.", nullptr, -1),
          u"未安装流数据插件“%1”。"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::Timeline", "Streaming: pause playback to interact with the timeline", nullptr, -1),
          u"正在接收数据流：暂停回放后可操作时间轴"_s);
      QCOMPARE(QCoreApplication::translate("LeftPanel", "Open cloud browser", nullptr, -1), u"浏览云端文件"_s);
      QCOMPARE(
          QCoreApplication::translate("CustomWidgetConfigPanel", "Double-click a series to wire it.", nullptr, -1),
          u"双击序列即可将其接入此输入。"_s);
      QCOMPARE(
          QCoreApplication::translate("PJ::CustomWidgetConfigPanel", "Double-click a series to wire it.", nullptr, -1),
          u"双击序列即可将其接入此输入。"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "LayoutXml", "The layout records its streaming sources more than once.", nullptr, -1),
          u"布局中的流式数据源列表出现了多次。"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::MainWindow", "The layout's data sources exceed the %1 MiB a downloaded layout may load.", nullptr,
              -1),
          u"布局的数据源总大小超过了下载布局允许加载的上限（%1 MiB）。"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::MainWindow", "Select '%1' to replay this layout (selected '%2').", nullptr, -1),
          u"请选择“%1”以重新载入此布局（当前选择的是“%2”）。"_s);
      QCOMPARE(QCoreApplication::translate("PJ::FileLoader", "Import discarded", nullptr, -1), u"已放弃导入"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::MainWindow", "%n scene layer(s) could not be rebound and were omitted.", nullptr, 7),
          u"7 个场景图层无法重新绑定，已跳过。"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PreferencesContent",
              "Every Record press creates one folder here holding one standard MCAP file per recorded source. "
              "Recordings capture the raw messages of the topics each stream is subscribed to; sources that write "
              "decoded samples directly (no message format) are not recorded.",
              nullptr, -1),
          u"每次点击录制都会在此创建一个文件夹，为每个参与录制的数据源保存一个标准 MCAP 文件。录制内容为各数据流已订阅话题的原始消息；直接写入解码后样本的数据源（无消息格式）不会参与录制。"_s);
      QCOMPARE(QCoreApplication::translate("PJ::MainWindow", "Sticks", nullptr, -1), u"针状线"_s);
      QCOMPARE(QCoreApplication::translate("PJ::Scene3DConfigPanel", "Line grid", nullptr, -1), u"线条网格"_s);
      QCOMPARE(QCoreApplication::translate("pj::scene3d::RobotModelLayer", "Visual", nullptr, -1), u"视觉模型"_s);
      QCOMPARE(
          QCoreApplication::translate("PJ::VisualizationPlaceholderWidget", "State Transitions", nullptr, -1),
          u"状态转换"_s);
      QCOMPARE(QCoreApplication::translate("PJ::PreferencesDialog", "per plot", nullptr, -1), u"按图表"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PreferencesContent",
              "Rescale a plot's vertical axis to fit its curves whenever a curve is added or removed (the shared time "
              "axis is left unchanged).",
              nullptr, -1),
          u"添加或移除曲线时，自动调整图表纵轴以适应曲线范围（共享时间轴保持不变）。"_s);
      QCOMPARE(QCoreApplication::translate("QObject", "computed at %1 s", nullptr, -1), u"在 %1 秒处计算"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "pj::scene3d::SceneViewWidget", "A scene pipeline has no HDR variant on this GPU", nullptr, -1),
          u"此 GPU 上某个场景管线没有 HDR 变体"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "pj::scene3d::OccupancyGridLayer", "Occupancy updates in this seek window exceed the %1 MiB limit",
              nullptr, -1),
          u"此跳转时间窗口内的占据栅格更新超出 %1 MiB 上限"_s);
      QCOMPARE(
          QCoreApplication::translate("pj::scene3d::PosesInFrameLayer", "Override color:", nullptr, -1),
          u"自定义颜色："_s);
      QCOMPARE(
          QCoreApplication::translate("pj::scene3d::SceneEntitiesLayer", "Override color:", nullptr, -1),
          u"自定义颜色："_s);
      QCOMPARE(QCoreApplication::translate("QObject", "start", nullptr, -1), u"起始"_s);
      QCOMPARE(QCoreApplication::translate("PJ::DatasetInfoDialog", "Descriptor", nullptr, -1), u"描述符"_s);
      QCOMPARE(
          QCoreApplication::translate("PJ::LayoutImportBatch", "descriptor refused by provider", nullptr, -1),
          u"提供方拒绝了描述符"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::LayoutImportBatch", "Provider '%1' refused the import descriptor for '%2'%3", nullptr, -1),
          u"提供方“%1”拒绝了“%2”的导入描述符%3"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "SourceConfigVariables",
              "The source configuration uses %1, which is not a deployment variable this PlotJuggler knows.", nullptr,
              -1),
          u"数据源配置使用了 %1，但当前版本的 PlotJuggler 无法识别该部署变量。"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::DockWidget", "\"%1\" cannot be displayed on its own, but a plugin panel can read it.", nullptr, -1),
          u"“%1”无法单独显示，但插件面板可以读取它。"_s);
      QCOMPARE(QCoreApplication::translate("PJ::PlotWidget", "%1 vs %2", nullptr, -1), u"%1 vs %2"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::FileLoader", "Plugin '%1': the saved configuration is not a JSON object and cannot be replayed.",
              nullptr, -1),
          u"插件“%1”：已保存的配置不是 JSON 对象，无法重新应用。"_s);
      QCOMPARE(
          QCoreApplication::translate("PJ::FileLoader", "Could not load '%1': %2", nullptr, -1), u"无法加载“%1”：%2"_s);
      QCOMPARE(
          QCoreApplication::translate("PJ::MainWindow", "'%1' cannot be loaded: %2", nullptr, -1),
          u"无法加载“%1”：%2"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::MainWindow", "Data source '%1' records a malformed content fingerprint.", nullptr, -1),
          u"数据源“%1”记录的内容指纹格式错误。"_s);
      QCOMPARE(
          QCoreApplication::translate("PJ::MainWindow", "Data source '%1' could not be downloaded: %2", nullptr, -1),
          u"无法下载数据源“%1”：%2"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::MainWindow",
              "Data source '%1' is not the file its layout was saved with (its content fingerprint differs).", nullptr,
              -1),
          u"数据源“%1”不是保存布局时所用的文件（内容指纹不同）。"_s);
      QCOMPARE(
          QCoreApplication::translate("PJ::MainWindow", "'%1' could not be downloaded: %2", nullptr, -1),
          u"无法下载“%1”：%2"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::MainWindow", "'%1' has no owner and cannot be deleted from here", nullptr, -1),
          u"“%1”没有所有者，无法在此删除"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::MainWindow", "'%1' was created by %2 and cannot be deleted from here", nullptr, -1),
          u"“%1”由 %2 创建，无法在此删除"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::MainWindow", "'%1' cannot be deleted: '%2' of %3 reads its output", nullptr, -1),
          u"无法删除“%1”：%3 的“%2”正在读取其输出"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::MainWindow", "'%1' cannot be deleted: the protected '%2' reads its output", nullptr, -1),
          u"无法删除“%1”：受保护的“%2”正在读取其输出"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::PresetController", "Preset '%1' cannot be opened: this page's preset list is invalid.", nullptr, -1),
          u"无法打开预设“%1”：此页面的预设列表无效。"_s);
      QCOMPARE(
          QCoreApplication::translate("PJ::PresetController", "This page has no preset named '%1'.", nullptr, -1),
          u"此页面没有名为“%1”的预设。"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::StreamingSourceManager", "Plugin '%1' refused the saved configuration: %2", nullptr, -1),
          u"插件“%1”拒绝了已保存的配置：%2"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::MainWindow",
              "Nothing to record: %n active source(s) write decoded samples directly, which cannot be recorded.",
              nullptr, 7),
          u"没有可录制的内容：7 个活动数据源直接写入解码后的样本，无法录制。"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::MainWindow", "%n source(s) write decoded samples directly and are not recorded: %1", nullptr, 7),
          u"7 个数据源直接写入解码后的样本，未参与录制：%1"_s);
    }
    {
      const PJ::AppLanguage language(*QCoreApplication::instance(), u"en_US"_s);
      QCOMPARE(QCoreApplication::translate("CurveListPanel", "Custom Topics", nullptr, -1), u"Custom Topics"_s);
      QCOMPARE(QCoreApplication::translate("CurveListPanel", "Add custom topic", nullptr, -1), u"Add custom topic"_s);
      QCOMPARE(
          QCoreApplication::translate("CurveListPanel", "Edit the selected custom topic", nullptr, -1),
          u"Edit the selected custom topic"_s);
      QCOMPARE(
          QCoreApplication::translate("CurveListPanel", "Custom topics options", nullptr, -1),
          u"Custom topics options"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "DatasetMergeActions",
              "These object topics share a name but have incompatible types, formats or marker descriptions, so the "
              "datasets cannot be merged:",
              nullptr, -1),
          u"These object topics share a name but have incompatible types, formats or marker descriptions, so the datasets cannot be merged:"_s);
      QCOMPARE(
          QCoreApplication::translate("PJ::CurveListPanel", "Edit the selected custom topic", nullptr, -1),
          u"Edit the selected custom topic"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::DockWidget", "%1 topics cannot be displayed on their own, but a plugin panel can read them.",
              nullptr, -1),
          u"%1 topics cannot be displayed on their own, but a plugin panel can read them."_s);
      QCOMPARE(
          QCoreApplication::translate("PJ::MainWindow", "Delete derived topic?", nullptr, -1),
          u"Delete derived topic?"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::MainWindow",
              "These derived topics read what you are deleting. They stay, but report a missing input:\n\n• %1",
              nullptr, -1),
          u"These derived topics read what you are deleting. They stay, but report a missing input:\n\n• %1"_s);
      QCOMPARE(QCoreApplication::translate("PJ::Scene3DConfigPanel", "Topics", nullptr, -1), u"Topics"_s);
      QCOMPARE(QCoreApplication::translate("PJ::Scene3DConfigPanel", "Topic", nullptr, -1), u"Topic"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::SceneDockWidget", "This view shows dataset %1; a topic from dataset %2 cannot be added to it.",
              nullptr, -1),
          u"This view shows dataset %1; a topic from dataset %2 cannot be added to it."_s);
      QCOMPARE(
          QCoreApplication::translate(
              "QObject",
              "Camera calibration topic, used automatically by 2D and 3D views. It cannot be displayed on its own, but "
              "a plugin panel can read it.",
              nullptr, -1),
          u"Camera calibration topic, used automatically by 2D and 3D views. It cannot be displayed on its own, but a plugin panel can read it."_s);
      QCOMPARE(QCoreApplication::translate("pj::scene3d::RobotModelLayer", "Topic", nullptr, -1), u"Topic"_s);
      QCOMPARE(QCoreApplication::translate("PJ::CurveListPanel", "Refresh derived", nullptr, -1), u"Refresh derived"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PreferencesContent",
              "Automatic re-runs a changed marker rule on its own, at the reload rate below. Manual only flags it as "
              "needing a refresh, reachable from the dataset's \"Refresh derived\" action.",
              nullptr, -1),
          u"Automatic re-runs a changed marker rule on its own, at the reload rate below. Manual only flags it as needing a refresh, reachable from the dataset's \"Refresh derived\" action."_s);
      QCOMPARE(
          QCoreApplication::translate("PJ::MainWindow", "Show point in plot", nullptr, -1), u"Show point in plot"_s);
      QCOMPARE(QCoreApplication::translate("DatasetMergeActions", "canonical %1", nullptr, -1), u"canonical %1"_s);
      QCOMPARE(
          QCoreApplication::translate("PJ::ExtensionManager", "Not available for this platform (%1)", nullptr, -1),
          u"Not available for this platform (%1)"_s);
      QCOMPARE(QCoreApplication::translate("PJ::SourcePromotionHost", "promoted", nullptr, -1), u"promoted"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::MainWindow", "Failed to publish the source-promotion service for '%1': %2", nullptr, -1),
          u"Failed to publish the source-promotion service for '%1': %2"_s);
      QCOMPARE(
          QCoreApplication::translate("PJ::Scene3DConfigPanel", "Meshes opacity", nullptr, -1), u"Meshes opacity"_s);
      QCOMPARE(
          QCoreApplication::translate("PJ::Scene3DConfigPanel", "Show/hide visual meshes", nullptr, -1),
          u"Show/hide visual meshes"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::Scene3DDockWidget",
              "Only depth-encoded images can be displayed in a 3D view. Use a 2D view for colour images.", nullptr, -1),
          u"Only depth-encoded images can be displayed in a 3D view. Use a 2D view for colour images."_s);
      QCOMPARE(
          QCoreApplication::translate("QObject", "SceneEntities decode received no snapshot", nullptr, -1),
          u"SceneEntities decode received no snapshot"_s);
      QCOMPARE(
          QCoreApplication::translate("QObject", "SceneEntities conversion failed: %1", nullptr, -1),
          u"SceneEntities conversion failed: %1"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "LayoutXml", "Data source '%1' is a file on a local machine, which a web layout cannot open.", nullptr,
              -1),
          u"Data source '%1' is a file on a local machine, which a web layout cannot open."_s);
      QCOMPARE(QCoreApplication::translate("LeftPanel", "Stream", nullptr, -1), u"Stream"_s);
      QCOMPARE(QCoreApplication::translate("LeftPanel", "Start streaming", nullptr, -1), u"Start streaming"_s);
      QCOMPARE(QCoreApplication::translate("LeftPanel", "Pause streaming", nullptr, -1), u"Pause streaming"_s);
      QCOMPARE(
          QCoreApplication::translate("LeftPanel", "Streaming buffer length (seconds)", nullptr, -1),
          u"Streaming buffer length (seconds)"_s);
      QCOMPARE(
          QCoreApplication::translate("LeftPanel", "Streaming buffer (seconds)", nullptr, -1),
          u"Streaming buffer (seconds)"_s);
      QCOMPARE(QCoreApplication::translate("MarketplaceWindow", "Data Streamers", nullptr, -1), u"Data Streamers"_s);
      QCOMPARE(
          QCoreApplication::translate("MarketplaceWindow", "Extensions that stream data continuously", nullptr, -1),
          u"Extensions that stream data continuously"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::CurveListPanel", "Not subscribed. Drop it into a view to start streaming.", nullptr, -1),
          u"Not subscribed. Drop it into a view to start streaming."_s);
      QCOMPARE(
          QCoreApplication::translate("PJ::CurveListPanel", "Stop forced streaming", nullptr, -1),
          u"Stop forced streaming"_s);
      QCOMPARE(
          QCoreApplication::translate("PJ::CurveListPanel", "Force topic streaming", nullptr, -1),
          u"Force topic streaming"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::ImageLayer",
              "Undistort the image using its matching CameraInfo. Turn off to show the raw image,\nfor example when "
              "the stream is already rectified.",
              nullptr, -1),
          u"Undistort the image using its matching CameraInfo. Turn off to show the raw image,\nfor example when the stream is already rectified."_s);
      QCOMPARE(QCoreApplication::translate("PJ::LeftPanel", "Resume streaming", nullptr, -1), u"Resume streaming"_s);
      QCOMPARE(QCoreApplication::translate("PJ::LeftPanel", "Pause streaming", nullptr, -1), u"Pause streaming"_s);
      QCOMPARE(QCoreApplication::translate("PJ::MainWindow", "Start Streaming", nullptr, -1), u"Start Streaming"_s);
      QCOMPARE(QCoreApplication::translate("PJ::MainWindow", "Streaming", nullptr, -1), u"Streaming"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::MainWindow", "Nothing to record: start a streaming source first.", nullptr, -1),
          u"Nothing to record: start a streaming source first."_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::MainWindow", "Layout '%1' records %n streaming source(s); the desktop loader does not start them.",
              nullptr, 7),
          u"Layout '%1' records 7 streaming source(s); the desktop loader does not start them."_s);
      QCOMPARE(
          QCoreApplication::translate("PJ::MainWindow", "Stream '%1' cannot start: %2", nullptr, -1),
          u"Stream '%1' cannot start: %2"_s);
      QCOMPARE(
          QCoreApplication::translate("PJ::MainWindow", "Stream '%1' could not start: %2", nullptr, -1),
          u"Stream '%1' could not start: %2"_s);
      QCOMPARE(
          QCoreApplication::translate("PJ::StreamingSourceManager", "No stream source selected.", nullptr, -1),
          u"No stream source selected."_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::StreamingSourceManager", "Stream plugin '%1' is not installed.", nullptr, -1),
          u"Stream plugin '%1' is not installed."_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::Timeline", "Streaming: pause playback to interact with the timeline", nullptr, -1),
          u"Streaming: pause playback to interact with the timeline"_s);
      QCOMPARE(QCoreApplication::translate("LeftPanel", "Open cloud browser", nullptr, -1), u"Open cloud browser"_s);
      QCOMPARE(
          QCoreApplication::translate("CustomWidgetConfigPanel", "Double-click a series to wire it.", nullptr, -1),
          u"Double-click a series to wire it."_s);
      QCOMPARE(
          QCoreApplication::translate("PJ::CustomWidgetConfigPanel", "Double-click a series to wire it.", nullptr, -1),
          u"Double-click a series to wire it."_s);
      QCOMPARE(
          QCoreApplication::translate(
              "LayoutXml", "The layout records its streaming sources more than once.", nullptr, -1),
          u"The layout records its streaming sources more than once."_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::MainWindow", "The layout's data sources exceed the %1 MiB a downloaded layout may load.", nullptr,
              -1),
          u"The layout's data sources exceed the %1 MiB a downloaded layout may load."_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::MainWindow", "Select '%1' to replay this layout (selected '%2').", nullptr, -1),
          u"Select '%1' to replay this layout (selected '%2')."_s);
      QCOMPARE(QCoreApplication::translate("PJ::FileLoader", "Import discarded", nullptr, -1), u"Import discarded"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::MainWindow", "%n scene layer(s) could not be rebound and were omitted.", nullptr, 7),
          u"7 scene layer(s) could not be rebound and were omitted."_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PreferencesContent",
              "Every Record press creates one folder here holding one standard MCAP file per recorded source. "
              "Recordings capture the raw messages of the topics each stream is subscribed to; sources that write "
              "decoded samples directly (no message format) are not recorded.",
              nullptr, -1),
          u"Every Record press creates one folder here holding one standard MCAP file per recorded source. Recordings capture the raw messages of the topics each stream is subscribed to; sources that write decoded samples directly (no message format) are not recorded."_s);
      QCOMPARE(QCoreApplication::translate("PJ::MainWindow", "Sticks", nullptr, -1), u"Sticks"_s);
      QCOMPARE(QCoreApplication::translate("PJ::Scene3DConfigPanel", "Line grid", nullptr, -1), u"Line grid"_s);
      QCOMPARE(QCoreApplication::translate("pj::scene3d::RobotModelLayer", "Visual", nullptr, -1), u"Visual"_s);
      QCOMPARE(
          QCoreApplication::translate("PJ::VisualizationPlaceholderWidget", "State Transitions", nullptr, -1),
          u"State Transitions"_s);
      QCOMPARE(QCoreApplication::translate("PJ::PreferencesDialog", "per plot", nullptr, -1), u"per plot"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PreferencesContent",
              "Rescale a plot's vertical axis to fit its curves whenever a curve is added or removed (the shared time "
              "axis is left unchanged).",
              nullptr, -1),
          u"Rescale a plot's vertical axis to fit its curves whenever a curve is added or removed (the shared time axis is left unchanged)."_s);
      QCOMPARE(QCoreApplication::translate("QObject", "computed at %1 s", nullptr, -1), u"computed at %1 s"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "pj::scene3d::SceneViewWidget", "A scene pipeline has no HDR variant on this GPU", nullptr, -1),
          u"A scene pipeline has no HDR variant on this GPU"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "pj::scene3d::OccupancyGridLayer", "Occupancy updates in this seek window exceed the %1 MiB limit",
              nullptr, -1),
          u"Occupancy updates in this seek window exceed the %1 MiB limit"_s);
      QCOMPARE(
          QCoreApplication::translate("pj::scene3d::PosesInFrameLayer", "Override color:", nullptr, -1),
          u"Override color:"_s);
      QCOMPARE(
          QCoreApplication::translate("pj::scene3d::SceneEntitiesLayer", "Override color:", nullptr, -1),
          u"Override color:"_s);
      QCOMPARE(QCoreApplication::translate("QObject", "start", nullptr, -1), u"start"_s);
      QCOMPARE(QCoreApplication::translate("PJ::DatasetInfoDialog", "Descriptor", nullptr, -1), u"Descriptor"_s);
      QCOMPARE(
          QCoreApplication::translate("PJ::LayoutImportBatch", "descriptor refused by provider", nullptr, -1),
          u"descriptor refused by provider"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::LayoutImportBatch", "Provider '%1' refused the import descriptor for '%2'%3", nullptr, -1),
          u"Provider '%1' refused the import descriptor for '%2'%3"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "SourceConfigVariables",
              "The source configuration uses %1, which is not a deployment variable this PlotJuggler knows.", nullptr,
              -1),
          u"The source configuration uses %1, which is not a deployment variable this PlotJuggler knows."_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::DockWidget", "\"%1\" cannot be displayed on its own, but a plugin panel can read it.", nullptr, -1),
          u"\"%1\" cannot be displayed on its own, but a plugin panel can read it."_s);
      QCOMPARE(QCoreApplication::translate("PJ::PlotWidget", "%1 vs %2", nullptr, -1), u"%1 vs %2"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::FileLoader", "Plugin '%1': the saved configuration is not a JSON object and cannot be replayed.",
              nullptr, -1),
          u"Plugin '%1': the saved configuration is not a JSON object and cannot be replayed."_s);
      QCOMPARE(
          QCoreApplication::translate("PJ::FileLoader", "Could not load '%1': %2", nullptr, -1),
          u"Could not load '%1': %2"_s);
      QCOMPARE(
          QCoreApplication::translate("PJ::MainWindow", "'%1' cannot be loaded: %2", nullptr, -1),
          u"'%1' cannot be loaded: %2"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::MainWindow", "Data source '%1' records a malformed content fingerprint.", nullptr, -1),
          u"Data source '%1' records a malformed content fingerprint."_s);
      QCOMPARE(
          QCoreApplication::translate("PJ::MainWindow", "Data source '%1' could not be downloaded: %2", nullptr, -1),
          u"Data source '%1' could not be downloaded: %2"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::MainWindow",
              "Data source '%1' is not the file its layout was saved with (its content fingerprint differs).", nullptr,
              -1),
          u"Data source '%1' is not the file its layout was saved with (its content fingerprint differs)."_s);
      QCOMPARE(
          QCoreApplication::translate("PJ::MainWindow", "'%1' could not be downloaded: %2", nullptr, -1),
          u"'%1' could not be downloaded: %2"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::MainWindow", "'%1' has no owner and cannot be deleted from here", nullptr, -1),
          u"'%1' has no owner and cannot be deleted from here"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::MainWindow", "'%1' was created by %2 and cannot be deleted from here", nullptr, -1),
          u"'%1' was created by %2 and cannot be deleted from here"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::MainWindow", "'%1' cannot be deleted: '%2' of %3 reads its output", nullptr, -1),
          u"'%1' cannot be deleted: '%2' of %3 reads its output"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::MainWindow", "'%1' cannot be deleted: the protected '%2' reads its output", nullptr, -1),
          u"'%1' cannot be deleted: the protected '%2' reads its output"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::PresetController", "Preset '%1' cannot be opened: this page's preset list is invalid.", nullptr, -1),
          u"Preset '%1' cannot be opened: this page's preset list is invalid."_s);
      QCOMPARE(
          QCoreApplication::translate("PJ::PresetController", "This page has no preset named '%1'.", nullptr, -1),
          u"This page has no preset named '%1'."_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::StreamingSourceManager", "Plugin '%1' refused the saved configuration: %2", nullptr, -1),
          u"Plugin '%1' refused the saved configuration: %2"_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::MainWindow",
              "Nothing to record: %n active source(s) write decoded samples directly, which cannot be recorded.",
              nullptr, 7),
          u"Nothing to record: 7 active source(s) write decoded samples directly, which cannot be recorded."_s);
      QCOMPARE(
          QCoreApplication::translate(
              "PJ::MainWindow", "%n source(s) write decoded samples directly and are not recorded: %1", nullptr, 7),
          u"7 source(s) write decoded samples directly and are not recorded: %1"_s);
    }
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
