// SPDX-License-Identifier: MPL-2.0
// Exercise the pinned DSO through the real asynchronous file loader and catalog,
// rather than substituting a mock host or testing the parser in isolation.
#include <gtest/gtest.h>

#include <QApplication>
#include <QDialog>
#include <QFile>
#include <QFileInfo>
#include <QTemporaryDir>
#include <limits>
#include <memory>
#include <variant>

#include "AppLanguage.h"
#include "FileLoader.h"
#include "pj_datastore/reader.hpp"
#include "pj_runtime/AppSession.h"
#include "pj_runtime/CatalogModel.h"
#include "pj_runtime/ExtensionCatalogService.h"
#include "pj_runtime/SessionManager.h"
#include "support/loader_test_support.h"

using namespace Qt::StringLiterals;

namespace {

class ArduPilotFileLoaderTest : public ::testing::Test {
 protected:
  void SetUp() override {
    ASSERT_TRUE(extensions_.isValid());
    ASSERT_TRUE(data_.isValid());
    const QString library = QString::fromUtf8(PJ_ARDUPILOT_PLUGIN_PATH);
    ASSERT_TRUE(QFile::copy(library, extensions_.filePath(QFileInfo(library).fileName())));
    language_ = std::make_unique<PJ::AppLanguage>(*qApp, u"zh_CN"_s);
    ASSERT_TRUE(language_->catalogLoaded());
    session_ = std::make_unique<PJ::AppSession>(extensions_.path());
    ASSERT_FALSE(session_->extensionCatalog().findSourcesForExtension(u".bin"_s).empty());
    loader_ = std::make_unique<PJ::FileLoader>(
        session_->sessionManager(), session_->extensionCatalog(), session_->catalogModel());
    QObject::connect(
        loader_.get(), &PJ::FileLoader::fileLoadFailed, loader_.get(),
        [this](const QString&, const QString& reason) { failure_ = reason; });
  }

  void TearDown() override {
    loader_.reset();
    // Failed imports may leave a non-modal warning. Every window here belongs
    // to this dedicated test process, so dismissal cannot affect another suite.
    for (QWidget* widget : QApplication::topLevelWidgets()) {
      if (auto* dialog = qobject_cast<QDialog*>(widget)) {
        dialog->reject();
      }
    }
    pj_app_test::flushQueuedEvents();
    session_.reset();
    language_.reset();
  }

  // Copy into private storage so reload/Unicode-path tests never modify fixtures.
  [[nodiscard]] QString fixture(const QString& name, const QString& destination = {}) {
    const QString path = data_.filePath(destination.isEmpty() ? name : destination);
    const QString source = QString::fromUtf8(PJ_ARDUPILOT_FIXTURES) + u"/"_s + name;
    EXPECT_TRUE(QFile::copy(source, path));
    return path;
  }

  [[nodiscard]] bool load(const QString& path) {
    PJ::LoadHints hints;
    hints.expected_manifest_id = u"ardupilot-dataflash"_s;
    hints.require_expected_plugin = true;
    hints.dialog_policy = PJ::DialogPolicy::kNever;
    failure_.clear();
    const bool loaded = pj_app_test::loadAndWait(*loader_, path, hints);
    pj_app_test::flushQueuedEvents();
    return loaded;
  }

  // Check the same catalog field/column identity consumed by plotted curves.
  void expectValue(
      PJ::DatasetId dataset, const QString& topic, const QString& field, double value, PJ::Timestamp timestamp) {
    for (const auto& item : session_->catalogModel().items()) {
      const auto* scalar = std::get_if<PJ::ScalarFieldPayload>(&item.payload);
      if (item.dataset_id != dataset || item.topic_name != topic || scalar == nullptr || scalar->field_name != field) {
        continue;
      }
      const auto reader = session_->sessionManager().createReader();
      const auto metadata = reader.getMetadata(scalar->topic_id);
      ASSERT_TRUE(metadata.has_value());
      EXPECT_EQ(metadata->time_range_max, timestamp);
      const auto latest =
          reader.latestNumericAt({scalar->topic_id, std::numeric_limits<PJ::Timestamp>::max()}, scalar->column_index);
      ASSERT_TRUE(latest.has_value());
      ASSERT_TRUE(latest->has_value());
      EXPECT_DOUBLE_EQ(**latest, value);
      return;
    }
    FAIL() << "Missing catalog field " << topic.toStdString() << '/' << field.toStdString();
  }

  QTemporaryDir extensions_;
  QTemporaryDir data_;
  std::unique_ptr<PJ::AppLanguage> language_;
  std::unique_ptr<PJ::AppSession> session_;
  std::unique_ptr<PJ::FileLoader> loader_;
  QString failure_;
};

TEST_F(ArduPilotFileLoaderTest, UnicodeImportReloadAndSecondFilePreserveValuesAndIdentity) {
  const auto first = fixture(u"synthetic.BIN"_s, u"\u98de\u884c\u65e5\u5fd7.BIN"_s);
  ASSERT_TRUE(load(first)) << failure_.toStdString();
  const auto datasets = session_->sessionManager().createReader().listDatasets();
  ASSERT_EQ(datasets.size(), 1u);
  const auto id = datasets.front();
  const auto count = session_->catalogModel().items().size();
  expectValue(id, u"/TST/#0"_s, u"Value\t[V]"_s, 1.23, 1000000000);
  expectValue(id, u"/TST/#200"_s, u"Value\t[V]"_s, 3.45, 3000000000);

  ASSERT_TRUE(load(first)) << failure_.toStdString();
  EXPECT_EQ(session_->sessionManager().createReader().listDatasets(), datasets);
  EXPECT_EQ(session_->catalogModel().items().size(), count);
  expectValue(id, u"/TST/#0"_s, u"Value\t[V]"_s, 1.23, 1000000000);

  ASSERT_TRUE(load(fixture(u"second.BIN"_s))) << failure_.toStdString();
  const auto after = session_->sessionManager().createReader().listDatasets();
  ASSERT_EQ(after.size(), 2u);
  const auto second_id = after.front() == id ? after.back() : after.front();
  expectValue(second_id, u"/TST"_s, u"Value"_s, 2.5, 4000000000);
}

TEST_F(ArduPilotFileLoaderTest, InvalidSchemaDoesNotReplaceExistingData) {
  const auto path = fixture(u"second.BIN"_s);
  ASSERT_TRUE(load(path)) << failure_.toStdString();
  const auto before = session_->sessionManager().createReader().listDatasets();
  ASSERT_EQ(before.size(), 1u);
  EXPECT_FALSE(load(fixture(u"invalid_fmt.BIN"_s)));
  EXPECT_FALSE(failure_.isEmpty());
  EXPECT_EQ(session_->sessionManager().createReader().listDatasets(), before);
  expectValue(before.front(), u"/TST"_s, u"Value"_s, 2.5, 4000000000);
}

TEST_F(ArduPilotFileLoaderTest, UpstreamRealLogReachesTheCurveCatalog) {
  ASSERT_TRUE(load(QString::fromUtf8(PJ_ARDUPILOT_REAL_LOG))) << failure_.toStdString();
  EXPECT_EQ(session_->sessionManager().createReader().listDatasets().size(), 1u);
  EXPECT_EQ(session_->catalogModel().items().size(), 1940u);
}

}  // namespace

PJ_APP_TEST_MAIN("ardupilot_file_loader_test")
