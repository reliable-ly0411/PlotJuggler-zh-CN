// SPDX-License-Identifier: MPL-2.0
#include <QCoreApplication>
#include <QFile>
#include <QTemporaryDir>
#include <QTest>
#include <algorithm>
#include <filesystem>
#include <vector>

#include "AppLanguage.h"
#include "pj_runtime/PluginRuntimeCatalog.h"

using namespace Qt::StringLiterals;

// Scan real DSOs only after installing the production startup translator.
class RuntimeCatalogLanguageTest : public QObject {
  Q_OBJECT

 private slots:
  void successfulLoadsPreserveIdentitiesAndUnknownErrors() {
    QTemporaryDir temporary;
    QVERIFY(temporary.isValid());
    const auto dir = std::filesystem::path((temporary.path() + u"/資料 from %1"_s).toStdU16String());
    std::filesystem::create_directories(dir);
    for (const char* fixture :
         {PJ_LANGUAGE_SOURCE_PATH, PJ_LANGUAGE_PARSER_PATH, PJ_LANGUAGE_TOOLBOX_PATH, PJ_LANGUAGE_WIDGET_PATH}) {
      const std::filesystem::path source(fixture);
      std::filesystem::copy_file(source, dir / source.filename());
    }
    // Discovery errors are not rewritten by the success-message translations.
    const auto extension = std::filesystem::path(PJ_LANGUAGE_WIDGET_PATH).extension();
    const auto broken = dir / std::filesystem::path("broken").replace_extension(extension);
    QFile invalid(QString::fromStdU16String(broken.u16string()));
    QVERIFY(invalid.open(QIODevice::WriteOnly));
    invalid.write("unknown loader error fixture");
    invalid.close();
    std::vector<std::string> english_errors;
    for (const QString& language : {u"en_US"_s, u"zh_CN"_s, u"zh_TW"_s}) {
      const PJ::AppLanguage selected(*QCoreApplication::instance(), language);
      QCOMPARE(selected.catalogLoaded(), language != u"en_US"_s);
      std::vector<PJ::Diagnostic> diagnostics;
      PJ::PluginRuntimeCatalog catalog(dir, [&](const PJ::Diagnostic& d) { diagnostics.push_back(d); }, "test-source");
      catalog.scanDirectory();
      QCOMPARE(catalog.dataSources().size(), size_t{1});
      QCOMPARE(catalog.messageParsers().size(), size_t{1});
      QCOMPARE(catalog.toolboxes().size(), size_t{1});
      QCOMPARE(catalog.widgets().size(), size_t{1});
      QCOMPARE(catalog.widgets().front().name, std::string("Unicode 元件 from %2"));
      QVERIFY(catalog.widgets().front().qt_compatible);
      const QStringList kinds =
          language == u"zh_CN"_s   ? QStringList{u"数据源"_s, u"消息解析器"_s, u"工具箱"_s, u"控件"_s}
          : language == u"zh_TW"_s ? QStringList{u"資料來源"_s, u"訊息解析器"_s, u"工具箱"_s, u"元件"_s}
                                   : QStringList{u"DataSource"_s, u"MessageParser"_s, u"Toolbox"_s, u"Widget"_s};
      int index = 0;
      const auto check = [&](const auto& plugin, const char* fixture) {
        const QString kind = kinds.at(index++);
        const QString name = QString::fromStdString(plugin.name);
        // Derive the expected bytes from the installed fixture, not catalog output.
        const auto expected_path =
            std::filesystem::canonical(dir / std::filesystem::path(fixture).filename()).u8string();
        const std::string expected_utf8(expected_path.begin(), expected_path.end());
        QVERIFY(expected_utf8.find("資料 from %1") != std::string::npos);
        QCOMPARE(plugin.path, expected_utf8);
        const QString path = QString::fromStdString(expected_utf8);
        const QString expected = language == u"zh_CN"_s   ? u"已从 "_s + path + u" 加载"_s + kind + u" "_s + name
                                 : language == u"zh_TW"_s ? u"已從 "_s + path + u" 載入"_s + kind + u" "_s + name
                                                          : u"Loaded "_s + kind + u" "_s + name + u" from "_s + path;
        QCOMPARE(
            std::count_if(
                diagnostics.begin(), diagnostics.end(),
                [&](const PJ::Diagnostic& d) {
                  return d.level == PJ::DiagnosticLevel::kInfo && d.source == "test-source" && d.id == plugin.id &&
                         d.message == expected.toStdString();
                }),
            1);
      };
      check(catalog.dataSources().front(), PJ_LANGUAGE_SOURCE_PATH);
      check(catalog.messageParsers().front(), PJ_LANGUAGE_PARSER_PATH);
      check(catalog.toolboxes().front(), PJ_LANGUAGE_TOOLBOX_PATH);
      check(catalog.widgets().front(), PJ_LANGUAGE_WIDGET_PATH);
      std::vector<std::string> errors;
      for (const auto& d : diagnostics) {
        if (d.level == PJ::DiagnosticLevel::kError) {
          errors.push_back(d.message);
        }
      }
      QVERIFY(!errors.empty());
      if (language == u"en_US"_s) {
        english_errors = errors;
      } else {
        QCOMPARE(errors, english_errors);
      }
    }
  }
};

QTEST_GUILESS_MAIN(RuntimeCatalogLanguageTest)
#include "runtime_catalog_language_test.moc"
