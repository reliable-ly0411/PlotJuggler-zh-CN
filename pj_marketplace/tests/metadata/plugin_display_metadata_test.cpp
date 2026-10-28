// SPDX-License-Identifier: MPL-2.0
#include <QApplication>
#include <QDesktopServices>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QPushButton>
#include <QSettings>
#include <QTableWidget>
#include <QTemporaryDir>
#include <QTest>
#include <QTextBrowser>
#ifndef Q_MOC_RUN
#include "AppLanguage.h"
#include "internal/plugin_display_metadata.hpp"
#include "pj_marketplace/download_manager.hpp"
#include "pj_marketplace/extension_manager.hpp"
#include "pj_marketplace/marketplace_window.hpp"
#include "pj_marketplace/plugin_check_runner.hpp"
#endif

using namespace Qt::StringLiterals;

class PluginDisplayMetadataTest : public QObject {
  Q_OBJECT
  QTemporaryDir profile_;
  QUrl opened_;

  // A successful click is intercepted in-process, never sent to the user's browser.
  QPushButton* websiteButton(QWidget& window) {
    for (auto* button : window.findChildren<QPushButton*>()) {
      if (button->isVisible() &&
          button->text() == QCoreApplication::translate("PJ::MarketplaceWindow", "Visit Website")) {
        return button;
      }
    }
    return nullptr;
  }

 private slots:
  void openWebsite(const QUrl& url) {
    opened_ = url;
  }

  void initTestCase();

  void cleanupTestCase() {
    QDesktopServices::unsetUrlHandler(u"https"_s);
  }

  void optionalFieldsNeverChangeAdmissionIdentity();

  void installedMetadata_data();

  void installedMetadata();
  void websiteFallback_data();
  void websiteFallback();
  void installedApbin();
};
void PluginDisplayMetadataTest::initTestCase() {
  QVERIFY(profile_.isValid());
  QSettings::setDefaultFormat(QSettings::IniFormat);
  QSettings::setPath(QSettings::IniFormat, QSettings::UserScope, profile_.path());
  QCoreApplication::setOrganizationName(u"PJMetadataRegression"_s);
  QCoreApplication::setApplicationName(u"Isolated"_s);
  QCoreApplication::setApplicationVersion(u"4.0.0"_s);
  QDesktopServices::setUrlHandler(u"https"_s, this, "openWebsite");
}

void PluginDisplayMetadataTest::optionalFieldsNeverChangeAdmissionIdentity() {
  PJ::PluginDescriptor descriptor;
  descriptor.id = "fixture";
  descriptor.version = "1.0.0";
  const auto parse = [&](std::string_view json) {
    return PJ::marketplace_internal::decodePluginDisplayMetadata(json, descriptor);
  };
  QVERIFY(parse("not json").author.empty());
  QVERIFY(parse(R"json({"id":"other","version":"1.0.0","author":"wrong"})json").author.empty());
  QVERIFY(parse(R"json({"id":"fixture","version":"2.0.0","author":"stale"})json").author.empty());
  const auto typed = parse(
      R"json({"id":"fixture","version":"1.0.0","author":12,"license":[],"website":{},"repository":"https://example.org"})json");
  QVERIFY(typed.author.empty() && typed.license.empty() && typed.website.empty());
  QCOMPARE(typed.repository, std::string("https://example.org"));
}

void PluginDisplayMetadataTest::installedMetadata_data() {
  QTest::addColumn<QString>("language");
  QTest::addColumn<bool>("registry_entry");
  for (const auto& language : {u"en_US"_s, u"zh_CN"_s, u"zh_TW"_s}) {
    QTest::newRow(qPrintable(language + "/local-only")) << language << false;
    QTest::newRow(qPrintable(language + "/registry-fallback")) << language << true;
  }
}

void PluginDisplayMetadataTest::installedMetadata() {
  QFETCH(QString, language);
  QFETCH(bool, registry_entry);
  PJ::AppLanguage translator(*qApp, language);
  QTemporaryDir temp;
  QVERIFY(temp.isValid());
  const auto plugin_dir = temp.path() + u"/extensions/metadata-fixture"_s;
  QVERIFY(QDir().mkpath(plugin_dir));
  QVERIFY(QFile::copy(
      QString::fromUtf8(PJ_METADATA_FIXTURE),
      plugin_dir + "/" + QFileInfo(QString::fromUtf8(PJ_METADATA_FIXTURE)).fileName()));
  QFile sidecar(plugin_dir + u"/manifest.json"_s);
  QVERIFY(sidecar.open(QIODevice::WriteOnly));
  sidecar.write(
      R"json({"id":"metadata-fixture","version":"1.2.3","author":"Sidecar impostor","repository":"https://wrong.invalid"})json");
  sidecar.close();
  const PJ::PluginCheckRunner helper({std::chrono::seconds(15), QString::fromUtf8(PJ_PLUGIN_CHECK_HELPER_PATH)});
  const auto admitted = helper.run(plugin_dir);
  QVERIFY2(admitted.ok, qPrintable(admitted.parent_error));
  QCOMPARE(admitted.plugins.size(), 1);
  QCOMPARE(admitted.plugins[0].author, u"Fixture <author> & contributors"_s);
  QCOMPARE(admitted.plugins[0].license, u"MIT"_s);
  QCOMPARE(admitted.plugins[0].repository, u"https://example.org/plugins/metadata"_s);
  PJ::DownloadManager downloader;
  PJ::ExtensionManager manager(&downloader, temp.path() + u"/extensions"_s, temp.path() + u"/pending"_s);
  const auto installed = manager.installedExtensions();
  QVERIFY(installed.contains(u"metadata-fixture"_s));
  QCOMPARE(installed.value(u"metadata-fixture"_s).repository, admitted.plugins[0].repository);
  QCOMPARE(installed.value(u"metadata-fixture"_s).author, admitted.plugins[0].author);

  QJsonArray entries;
  if (registry_entry) {
    entries.append(QJsonObject{
        {"id", "metadata-fixture"},
        {"name", "Registry fixture"},
        {"version", "1.2.3"},
        {"category", "toolbox"},
        {"author", "Registry author"},
        {"platforms",
         QJsonObject{
             {PJ::PlatformUtils::currentPlatform(),
              QJsonObject{{"url", "https://example.org/unrequested.zip"}, {"checksum", "sha256:unused"}}}}}});
  }
  QFile registry(temp.path() + u"/registry.json"_s);
  QVERIFY(registry.open(QIODevice::WriteOnly));
  registry.write(QJsonDocument(QJsonObject{{"schema_version", "1.0.0"}, {"extensions", entries}}).toJson());
  registry.close();
  PJ::MarketplaceWindow window(&manager, QUrl::fromLocalFile(registry.fileName()));
  window.resize(1100, 550);
  window.show();
  auto* table = window.findChild<QTableWidget*>(u"plugin_table_"_s);
  QVERIFY(table);
  QTRY_COMPARE(table->rowCount(), 1);
  if (registry_entry) {
    QTRY_COMPARE(table->item(0, 0)->text(), u"Registry fixture"_s);
  }
  table->selectRow(0);
  QTRY_VERIFY(websiteButton(window));
  auto* details = window.findChild<QTextBrowser*>(u"detail_text_"_s);
  QVERIFY(details);
  const QString author = registry_entry ? u"Registry author"_s : u"Fixture <author> & contributors"_s;
  QVERIFY2(details->toPlainText().contains(author), qPrintable(details->toPlainText()));
  QVERIFY(details->toPlainText().contains(u"MIT"_s));
  opened_ = QUrl{};
  websiteButton(window)->click();
  QCOMPARE(opened_, QUrl(u"https://example.org/plugins/metadata"_s));

  // Website takes priority; same-version display-only edits must refresh the footer.
  auto changed = manager.installedExtensions();
  changed[u"metadata-fixture"_s].website = u"https://example.org/home"_s;
  changed[u"metadata-fixture"_s].author = u"Updated author"_s;
  PJ::MarketplaceWindow snapshot_window(&manager, QUrl::fromLocalFile(registry.fileName()), changed);
  snapshot_window.show();
  auto* snapshot_table = snapshot_window.findChild<QTableWidget*>(u"plugin_table_"_s);
  QVERIFY(snapshot_table);
  QTRY_COMPARE(snapshot_table->rowCount(), 1);
  snapshot_table->selectRow(0);
  QTRY_VERIFY(websiteButton(snapshot_window));
  websiteButton(snapshot_window)->click();
  QCOMPARE(opened_, QUrl(u"https://example.org/home"_s));
  // The next activation re-reads the original DSO: version is unchanged,
  // but display fields differ from the supplied startup snapshot.
  snapshot_window.activateEmbedded();
  snapshot_table->selectRow(0);
  QTRY_VERIFY(websiteButton(snapshot_window));
  websiteButton(snapshot_window)->click();
  QCOMPARE(opened_, QUrl(u"https://example.org/plugins/metadata"_s));

  const QString evidence = qEnvironmentVariable("PJ_TEST_SCREENSHOT_DIR");
  if (!evidence.isEmpty()) {
    QVERIFY(QDir().mkpath(evidence));
    QVERIFY(window.grab().save(evidence + "/metadata-" + language + (registry_entry ? "-registry.png" : "-local.png")));
  }
}

void PluginDisplayMetadataTest::websiteFallback_data() {
  QTest::addColumn<QString>("language");
  QTest::addColumn<QString>("local_website");
  QTest::addColumn<QString>("local_repository");
  QTest::addColumn<QString>("registry_website");
  QTest::addColumn<QString>("registry_repository");
  QTest::addColumn<QString>("expected_url");
  QTest::addColumn<bool>("registry_entry");
  for (const auto& language : {u"en_US"_s, u"zh_CN"_s, u"zh_TW"_s}) {
    QTest::newRow(qPrintable(language + "/website-first"))
        << language << u" https://example.org/home "_s << u"https://example.org/source"_s << QString{} << QString{}
        << u"https://example.org/home"_s << false;
    QTest::newRow(qPrintable(language + "/trimmed-repository"))
        << language << u" \t "_s << u" https://example.org/source "_s << QString{} << QString{}
        << u"https://example.org/source"_s << false;
    QTest::newRow(qPrintable(language + "/empty-link-hidden"))
        << language << QString{} << QString{} << QString{} << QString{} << QString{} << false;
    QTest::newRow(qPrintable(language + "/blank-link-hidden"))
        << language << u" \t "_s << u" \n "_s << QString{} << QString{} << QString{} << false;
    QTest::newRow(qPrintable(language + "/registry-website-preserved"))
        << language << u"https://example.org/local-home"_s << u"https://example.org/local-source"_s
        << u" https://example.org/registry-home "_s << u"https://example.org/registry-source"_s
        << u"https://example.org/registry-home"_s << true;
    QTest::newRow(qPrintable(language + "/registry-repository-preserved"))
        << language << QString{} << u"https://example.org/local-source"_s << QString{}
        << u" https://example.org/registry-source "_s << u"https://example.org/registry-source"_s << true;
  }
}

void PluginDisplayMetadataTest::websiteFallback() {
  QFETCH(QString, language);
  QFETCH(QString, local_website);
  QFETCH(QString, local_repository);
  QFETCH(QString, registry_website);
  QFETCH(QString, registry_repository);
  QFETCH(QString, expected_url);
  QFETCH(bool, registry_entry);
  PJ::AppLanguage translator(*qApp, language);
  QTemporaryDir temp;
  QVERIFY(temp.isValid());
  PJ::DownloadManager downloader;
  PJ::ExtensionManager manager(&downloader, temp.path() + u"/extensions"_s, temp.path() + u"/pending"_s);
  PJ::InstalledExtension installed;
  installed.id = u"fallback-fixture"_s;
  installed.name = u"Fallback fixture"_s;
  installed.version = u"1.0.0"_s;
  installed.category = u"toolbox"_s;
  installed.author = u"Local <author> & contributors"_s;
  installed.license = u"MIT"_s;
  installed.website = local_website;
  installed.repository = local_repository;
  QJsonArray entries;
  if (registry_entry) {
    entries.append(QJsonObject{
        {"id", installed.id},
        {"name", "Registry fallback fixture"},
        {"version", installed.version},
        {"category", installed.category},
        {"author", "Registry <author> & contributors"},
        {"license", "Apache-2.0"},
        {"website", registry_website},
        {"repository", registry_repository},
        {"platforms",
         QJsonObject{
             {PJ::PlatformUtils::currentPlatform(),
              QJsonObject{{"url", "https://example.org/unrequested.zip"}, {"checksum", "sha256:unused"}}}}}});
  }
  QFile registry(temp.path() + u"/registry.json"_s);
  QVERIFY(registry.open(QIODevice::WriteOnly));
  registry.write(QJsonDocument(QJsonObject{{"schema_version", "1.0.0"}, {"extensions", entries}}).toJson());
  registry.close();
  PJ::MarketplaceWindow window(
      &manager, QUrl::fromLocalFile(registry.fileName()),
      QMap<QString, PJ::InstalledExtension>{{installed.id, installed}});
  window.show();
  auto* table = window.findChild<QTableWidget*>(u"plugin_table_"_s);
  QVERIFY(table);
  QTRY_COMPARE(table->rowCount(), 1);
  QTRY_COMPARE(table->item(0, 0)->text(), registry_entry ? u"Registry fallback fixture"_s : installed.name);
  table->selectRow(0);
  auto* details = window.findChild<QTextBrowser*>(u"detail_text_"_s);
  QVERIFY(details);
  QVERIFY(details->toPlainText().contains(registry_entry ? u"Registry <author> & contributors"_s : installed.author));
  QVERIFY(details->toPlainText().contains(registry_entry ? u"Apache-2.0"_s : installed.license));
  QTRY_COMPARE(websiteButton(window) != nullptr, !expected_url.isEmpty());
  if (!expected_url.isEmpty()) {
    opened_ = QUrl{};
    websiteButton(window)->click();
    QCOMPARE(opened_, QUrl(expected_url));
  }
}

void PluginDisplayMetadataTest::installedApbin() {
  const QString source = qEnvironmentVariable("PJ_APBIN_TEST_DIR");
  if (source.isEmpty()) {
    QSKIP("Set PJ_APBIN_TEST_DIR to test an existing APBIN package copy");
  }
  for (const auto& language : {u"zh_CN"_s, u"zh_TW"_s, u"en_US"_s}) {
    PJ::AppLanguage translator(*qApp, language);
    QTemporaryDir temp;
    QVERIFY(temp.isValid());
    const QString destination = temp.path() + u"/extensions/apbin"_s;
    QVERIFY(QDir().mkpath(destination));
    // Only read the installed payload; all scans, store files and UI state use
    // the private copy. No access to the user's active ExtensionManager.
    const auto files = QDir(source).entryInfoList({"*.so", "*.dll", "*.dylib"}, QDir::Files);
    QVERIFY(!files.isEmpty());
    for (const auto& file : files) {
      QVERIFY(QFile::copy(file.absoluteFilePath(), destination + "/" + file.fileName()));
    }
    PJ::PluginCheckRunner helper({std::chrono::seconds(15), QString::fromUtf8(PJ_PLUGIN_CHECK_HELPER_PATH)});
    const auto admitted = helper.run(destination);
    QVERIFY2(admitted.ok, qPrintable(admitted.parent_error));
    QCOMPARE(admitted.plugins.size(), 1);
    const auto& record = admitted.plugins.front();
    QCOMPARE(record.id, u"ardupilot-dataflash"_s);
    QCOMPARE(record.version, u"1.2.0-pj4.rc.1"_s);
    QVERIFY(!record.author.isEmpty());
    QCOMPARE(record.license, u"LGPL-3.0-only"_s);
    QCOMPARE(record.repository, u"https://github.com/reliable-ly0411/plotjuggler-apbin-plugins"_s);
    PJ::DownloadManager downloader;
    PJ::ExtensionManager manager(&downloader, temp.path() + u"/extensions"_s, temp.path() + u"/pending"_s);
    QCOMPARE(manager.installedExtensions().value(record.id).repository, record.repository);
    QFile registry(temp.path() + u"/registry.json"_s);
    QVERIFY(registry.open(QIODevice::WriteOnly));
    registry.write("{\"extensions\":[]}");
    registry.close();
    PJ::MarketplaceWindow window(&manager, QUrl::fromLocalFile(registry.fileName()));
    window.resize(1100, 550);
    window.show();
    auto* table = window.findChild<QTableWidget*>(u"plugin_table_"_s);
    QVERIFY(table);
    QTRY_COMPARE(table->rowCount(), 1);
    table->selectRow(0);
    QTRY_VERIFY(websiteButton(window));
    auto* details = window.findChild<QTextBrowser*>(u"detail_text_"_s);
    QVERIFY(details);
    QVERIFY(details->toPlainText().contains(record.author));
    QVERIFY(details->toPlainText().contains(record.license));
    opened_ = QUrl{};
    websiteButton(window)->click();
    QCOMPARE(opened_, QUrl(record.repository));
    const QString evidence = qEnvironmentVariable("PJ_TEST_SCREENSHOT_DIR");
    if (!evidence.isEmpty()) {
      QVERIFY(QDir().mkpath(evidence));
      QVERIFY(window.grab().save(evidence + "/apbin-" + language + ".png"));
    }
  }
}

QTEST_MAIN(PluginDisplayMetadataTest)
#include "plugin_display_metadata_test.moc"
