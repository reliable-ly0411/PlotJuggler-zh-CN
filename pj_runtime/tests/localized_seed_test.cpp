// SPDX-License-Identifier: MPL-2.0
#include <QJsonDocument>
#include <QTemporaryDir>
#include <QTest>

#include "pj_runtime/LocalizedPluginSeed.h"
using namespace Qt::StringLiterals;
using namespace PJ::LocalizedPluginSeed;

class LocalizedSeedTest : public QObject {
  Q_OBJECT
 private slots:
  void identityPolicy() {
    const Build build{u"new-fork"_s, {u"official"_s, u"rc2-fork"_s}};
    QCOMPARE(decide(build, u"official"_s, {}, false), Decision::Migrate);
    QCOMPARE(decide(build, u"rc2-fork"_s, {}, false), Decision::Migrate);
    QCOMPARE(decide(build, u"unknown-user-build"_s, {}, false), Decision::Preserve);
    QCOMPARE(decide(build, u"newer-upstream-build"_s, {}, false), Decision::Preserve);
    QCOMPARE(decide(build, {}, {}, false), Decision::Preserve);
    QCOMPARE(decide(build, u"old-fork"_s, u"old-fork"_s, false), Decision::Migrate);
    QCOMPARE(decide(build, u"official"_s, u"old-fork"_s, false), Decision::Preserve);
    QCOMPARE(decide(build, u"new-fork"_s, {}, false), Decision::AlreadyCurrent);
    QCOMPARE(decide(build, u"official"_s, {}, true), Decision::Preserve);
    QCOMPARE(decide(build, u"new-fork"_s, {}, true), Decision::AlreadyCurrent);
  }

  void receiptsCommitOnlyAfterSuccessAndFailureRetries() {
    QTemporaryDir dir;
    QSettings settings(dir.filePath(u"receipts.ini"_s), QSettings::IniFormat);
    const QString key = receiptKey(dir.path(), u"plugin"_s, u"1.0"_s);
    QVERIFY(begin(settings, key, u"fork"_s));
    QVERIFY(!settings.contains(key + u"/applied"_s));
    failed(settings, key);
    QVERIFY(!settings.contains(key + u"/pending"_s));
    QVERIFY(begin(settings, key, u"fork"_s));
    QVERIFY(complete(settings, key, u"fork"_s));
    QSettings reloaded(dir.filePath(u"receipts.ini"_s), QSettings::IniFormat);
    QCOMPARE(reloaded.value(key + u"/applied"_s).toString(), u"fork"_s);
    QVERIFY(!reloaded.contains(key + u"/pending"_s));
    const Build build{u"fork"_s, {u"official"_s}};
    QCOMPARE(decide(build, u"official"_s, reloaded.value(key + u"/applied"_s).toString(), false), Decision::Preserve);
    QVERIFY(key != receiptKey(dir.path(), u"plugin"_s, u"2.0"_s));
    QVERIFY(key != receiptKey(dir.path() + u"/other"_s, u"plugin"_s, u"1.0"_s));
  }

  void unwritableReceiptRefusesBegin() {
    QTemporaryDir dir;
    QSettings settings(dir.path(), QSettings::IniFormat);
    QVERIFY(!begin(settings, u"key"_s, u"hash"_s));
  }

  void validatesActualBundledBytesAndIdentity() {
    QTemporaryDir dir;
    const QString dso = dir.filePath(u"plugin.dll"_s);
    QFile binary(dso);
    QVERIFY(binary.open(QIODevice::WriteOnly));
    binary.write("fork");
    binary.close();
    const auto hash = fileHash(dso);
    QJsonObject marker{
        {"schema", 1},
        {"kind", "fork-localized-rebuild"},
        {"id", "id"},
        {"version", "1.0"},
        {"dso", "plugin.dll"},
        {"sha256", hash},
        {"legacy_sha256", QJsonArray{QString(64, QChar('a'))}}};
    QFile file(dir.filePath(QString::fromLatin1(kMarker)));
    QVERIFY(file.open(QIODevice::WriteOnly));
    file.write(QJsonDocument(marker).toJson());
    file.close();
    QVERIFY(readBuild(dir.path(), dso, u"id"_s, u"1.0"_s).has_value());
    QVERIFY(!readBuild(dir.path(), dso, u"other"_s, u"1.0"_s));
    QVERIFY(!readBuild(dir.path(), dso, u"id"_s, u"2.0"_s));
    QVERIFY(binary.open(QIODevice::WriteOnly));
    binary.write("tampered");
    binary.close();
    QVERIFY(!readBuild(dir.path(), dso, u"id"_s, u"1.0"_s));
  }

  void stagingPreservesUserExtrasAndRejectsLinks() {
    QTemporaryDir dir;
    const auto installed = std::filesystem::path(dir.filePath(u"installed"_s).toStdString());
    const auto staged = std::filesystem::path(dir.filePath(u"staged"_s).toStdString());
    std::filesystem::create_directories(installed / "user");
    QFile extra(QString::fromStdString((installed / "user" / "notes.txt").string()));
    QVERIFY(extra.open(QIODevice::WriteOnly));
    extra.write("keep");
    extra.close();
    QVERIFY(!preserveFiles(installed, staged));
    QVERIFY(std::filesystem::exists(staged / "user" / "notes.txt"));
    std::error_code ec;
    std::filesystem::create_symlink(installed / "user" / "notes.txt", installed / "link", ec);
    if (!ec) {
      QVERIFY(preserveFiles(installed, staged / "blocked"));
    }
  }
};
QTEST_GUILESS_MAIN(LocalizedSeedTest)
#include "localized_seed_test.moc"
