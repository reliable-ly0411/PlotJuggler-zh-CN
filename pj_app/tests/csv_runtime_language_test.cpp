// SPDX-License-Identifier: MPL-2.0
// Opt-in real fixed CSV DSO + FileLoader/DiagnosticDump regression. Each language
// has its own process because plugin display selection is immutable after loading.
#include <QAbstractButton>
#include <QDir>
#include <QJsonArray>
#include <QLabel>
#include <QPlainTextEdit>
#include <QPushButton>

#include "AppLanguage.h"
#include "DiagnosticDump.h"
#include "pj_marketplace/platform_utils.hpp"
#include "pj_marketplace/qt_diagnostic_bridge.hpp"
#include "pj_runtime/AppSession.h"
#include "pj_runtime/ExtensionCatalogService.h"
#include "pj_runtime/SessionManager.h"
#include "pj_widgets/MessageBox.h"
#include "support/loader_test_support.h"

using namespace Qt::StringLiterals;

namespace {

QString expected(const char* english, const char* simplified, const char* traditional) {
  const QByteArray language = qgetenv("PLOTJUGGLER_UI_LANGUAGE");
  return QString::fromUtf8(language == "zh_CN" ? simplified : language == "zh_TW" ? traditional : english);
}

class CsvRuntimeFileLoader : public ::testing::Test {
 protected:
  void SetUp() override {
    ASSERT_TRUE(extensions_.isValid());
    ASSERT_TRUE(data_.isValid());
    language_ = std::make_unique<PJ::AppLanguage>(*qApp, QString::fromUtf8(qgetenv("PLOTJUGGLER_UI_LANGUAGE")));
    const QString plugin = QString::fromUtf8(PJ_CSV_RUNTIME_PLUGIN);
    ASSERT_TRUE(QFile::copy(plugin, extensions_.filePath(QFileInfo(plugin).fileName())));
    session_ = std::make_unique<PJ::AppSession>(extensions_.path());
    const auto sources = session_->extensionCatalog().findSourcesForExtension(u".csv"_s);
    ASSERT_EQ(sources.size(), 1U);
    ASSERT_EQ(sources.front()->id, "csv-loader");
    ASSERT_EQ(sources.front()->version, "1.0.7");
    loader_ = std::make_unique<PJ::FileLoader>(
        session_->sessionManager(), session_->extensionCatalog(), session_->catalogModel());
    loader_->setDiagnosticSink(bridge_.sink());
  }

  QString writeCsv(const QByteArray& contents) {
    const QString path = data_.filePath(u"空值%1'CSV parsing failed'測試.csv"_s);
    QFile file(path);
    EXPECT_TRUE(file.open(QIODevice::WriteOnly));
    EXPECT_EQ(file.write(contents), contents.size());
    return path;
  }

  PJ::LoadHints hints(const QString& path) const {
    PJ::LoadHints result;
    result.expected_manifest_id = u"csv-loader"_s;
    result.require_expected_plugin = true;
    result.preset_config_json = pj_app_test::compactJson(
        {{u"filepath"_s, path},
         {u"delimiter"_s, u","_s},
         {u"detect_delimiter"_s, false},
         {u"time_mode"_s, u"row_number"_s}});
    result.dialog_policy = PJ::DialogPolicy::kPreferPreset;
    return result;
  }

  // Capture the actual GUI representation before selecting a button or closing.
  void checkWarning(bool long_body, int answer) {
    QByteArray csv("a,b,c\n0,10,20\n1,11,21\n");
    const int last_line = long_body ? 24 : 4;
    QString detail;
    for (int line = 4; line <= last_line; ++line) {
      csv += "2,12\n";
      detail += expected("Line ", "行 ", "行 ") + QString::number(line) +
                expected(": Expected 3 columns, got 2\n", ": 预期 3 列，实际 2\n", ": 預期 3 欄，實際 2\n");
    }
    const QString body = expected(
                             "Some rows have an incorrect number of columns and will be skipped:\n\n",
                             "部分行的列数不正确，将被跳过：\n\n", "部分資料列的欄數不正確，將被略過：\n\n") +
                         detail + expected("\nContinue loading?", "\n是否继续加载？", "\n是否繼續載入？");
    QWidget parent;
    bool inspected = false;
    bool done = false;
    bool success = false;
    QTimer answer_timer;
    answer_timer.setInterval(5);
    QObject::connect(&answer_timer, &QTimer::timeout, [&]() {
      for (QDialog* dialog : parent.findChildren<QDialog*>()) {
        if (!dialog->isVisible() || inspected) {
          continue;
        }
        const auto title = expected("Rows Skipped", "跳过行", "略過資料列");
        bool title_found = dialog->windowTitle() == title;
        for (auto* label : dialog->findChildren<QLabel*>()) {
          title_found |= label->text() == title;
        }
        EXPECT_TRUE(title_found);
        auto* scroll = dialog->findChild<QPlainTextEdit*>();
        if (long_body) {
          ASSERT_NE(scroll, nullptr);
          EXPECT_EQ(scroll->toPlainText(), body.mid(body.indexOf('\n') + 1).trimmed());
          EXPECT_TRUE(scroll->isReadOnly());
          EXPECT_LE(dialog->height(), 600);
        } else {
          EXPECT_EQ(scroll, nullptr);
          auto* label = dialog->findChild<QLabel*>(u"pjMessageBoxBody"_s);
          ASSERT_NE(label, nullptr);
          EXPECT_EQ(label->text(), body);
        }
        const QString continue_label = QCoreApplication::translate("QObject", "Continue");
        const QString abort_label = QCoreApplication::translate("QObject", "Abort");
        QAbstractButton* selected = nullptr;
        bool has_continue = false, has_abort = false;
        for (auto* button : dialog->findChildren<QAbstractButton*>()) {
          has_continue |= button->text() == continue_label;
          has_abort |= button->text() == abort_label;
          if (button->text() == (answer == 1 ? continue_label : abort_label)) {
            selected = button;
          }
        }
        EXPECT_TRUE(has_continue);
        EXPECT_TRUE(has_abort);
        inspected = true;
        if (answer < 0) {
          dialog->reject();
        } else if (selected != nullptr) {
          selected->click();
        } else {
          dialog->reject();
        }
        return;
      }
    });
    QObject::connect(loader_.get(), &PJ::FileLoader::fileLoaded, &parent, [&]() {
      success = true;
      done = true;
    });
    QObject::connect(loader_.get(), &PJ::FileLoader::fileLoadFailed, &parent, [&]() { done = true; });
    answer_timer.start();
    const QString path = writeCsv(csv);
    loader_->loadFile(path, &parent, hints(path));
    EXPECT_TRUE(pj_app_test::pumpUntil([&]() { return done; }));
    EXPECT_TRUE(inspected);
    EXPECT_EQ(success, answer == 1);
    const auto reader = session_->sessionManager().createReader();
    const auto datasets = reader.listDatasets();
    if (success) {
      ASSERT_EQ(datasets.size(), 1U);
      EXPECT_EQ(pj_app_test::singleTopicValues(reader, datasets.front()), (std::vector<double>{0, 1}));
    } else {
      EXPECT_TRUE(datasets.empty());
    }
    answer_timer.stop();
    loader_->joinForShutdown();
  }

  QTemporaryDir extensions_, data_;
  std::unique_ptr<PJ::AppLanguage> language_;
  PJ::QtDiagnosticBridge bridge_;
  std::unique_ptr<PJ::AppSession> session_;
  std::unique_ptr<PJ::FileLoader> loader_;
};

TEST_F(CsvRuntimeFileLoader, EmptyCsvWritesTranslatedPrefixedDiagnosticJson) {
  const QString diagnostic_path = data_.filePath(u"diagnostics.json"_s);
  PJ::DiagnosticDump dump(diagnostic_path);
  dump.attachTo(&bridge_);
  const QString path = writeCsv({});
  EXPECT_FALSE(pj_app_test::loadAndWait(*loader_, path, hints(path)));
  ASSERT_TRUE(dump.write());
  const QString evidence = qEnvironmentVariable("PJ_CSV_DIAGNOSTIC_DIR");
  if (!evidence.isEmpty()) {
    ASSERT_TRUE(QDir().mkpath(evidence));
    const QString destination =
        QDir(evidence).filePath(QString::fromUtf8(qgetenv("PLOTJUGGLER_UI_LANGUAGE")) + u".json"_s);
    QFile output(destination);
    ASSERT_TRUE(output.open(QIODevice::WriteOnly | QIODevice::Truncate));
    QFile input(diagnostic_path);
    ASSERT_TRUE(input.open(QIODevice::ReadOnly));
    const auto bytes = input.readAll();
    ASSERT_EQ(output.write(bytes), bytes.size());
  }
  QFile json(diagnostic_path);
  ASSERT_TRUE(json.open(QIODevice::ReadOnly));
  const auto envelope = QJsonDocument::fromJson(json.readAll()).object();
  ASSERT_EQ(envelope.value(u"version"_s).toInt(), 1);
  int failures = 0;
  for (const auto& value : envelope.value(u"records"_s).toArray()) {
    const auto record = value.toObject();
    if (record.value(u"id"_s).toString() != u"data-source-load-failed"_s) {
      continue;
    }
    ++failures;
    const QString message = record.value(u"message"_s).toString();
    EXPECT_TRUE(message.contains(path));
    EXPECT_TRUE(message.contains(
        u"plugin: "_s + QCoreApplication::translate("PJ::BundledPluginDiagnostics", "CSV parsing failed")))
        << message.toStdString();
    EXPECT_EQ(record.value(u"level"_s).toString(), u"error"_s);
  }
  EXPECT_EQ(failures, 1);
  EXPECT_TRUE(session_->sessionManager().createReader().listDatasets().empty());
}

TEST_F(CsvRuntimeFileLoader, ShortWarningContinue) {
  checkWarning(false, 1);
}
TEST_F(CsvRuntimeFileLoader, ShortWarningAbort) {
  checkWarning(false, 0);
}
TEST_F(CsvRuntimeFileLoader, ShortWarningClose) {
  checkWarning(false, -1);
}
TEST_F(CsvRuntimeFileLoader, LongWarningContinue) {
  checkWarning(true, 1);
}
TEST_F(CsvRuntimeFileLoader, LongWarningAbort) {
  checkWarning(true, 0);
}
TEST_F(CsvRuntimeFileLoader, LongWarningClose) {
  checkWarning(true, -1);
}

}  // namespace

// The real AppSession also owns data/cache paths, not only QSettings.
int main(int argc, char** argv) {
  qputenv("QT_QPA_PLATFORM", "offscreen");
  ::testing::InitGoogleTest(&argc, argv);
  QApplication app(argc, argv);
  QCoreApplication::setOrganizationName(u"PJ4Tests"_s);
  QCoreApplication::setApplicationName(u"CsvRuntimeFileLoader"_s);
  const QTemporaryDir profile;
  QString error;
  if (!profile.isValid() || !PJ::PlatformUtils::initializeProfile(profile.path(), &error)) {
    qCritical("Cannot initialize isolated CSV acceptance profile: %s", qPrintable(error));
    return 1;
  }
  return RUN_ALL_TESTS();
}
