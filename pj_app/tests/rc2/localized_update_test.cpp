// SPDX-License-Identifier: MPL-2.0
#include <QFile>
#include <QSignalSpy>
#include <QTcpServer>
#include <QTcpSocket>
#include <QTemporaryDir>
#include <QTest>

#include "pj_runtime/UpdateChecker.h"
#include "pj_runtime/UpdateVersion.h"
using namespace Qt::StringLiterals;

#include "local_http_server.h"

class LocalizedUpdateTest : public QObject {
  Q_OBJECT
 private slots:
  void initTestCase() {
    qRegisterMetaType<PJ::ReleaseInfo>();
  }
  void versions() {
    QVERIFY(PJ::isNewerLocalizedVersion(u"v4.0.0-zh.1.rc.10"_s, u"4.0.0-zh.1.rc.2"_s));
    QVERIFY(PJ::isNewerLocalizedVersion(u"v4.0.0-zh.1"_s, u"4.0.0-zh.1.rc.2"_s));
    QVERIFY(!PJ::isNewerLocalizedVersion(u"4.0.0-zh.1.rc.2"_s, u"4.0.0-zh.1"_s));
    for (const QString& tag :
         {u"v3.99.0-zh.9"_s, u"v5.0.0-zh.1"_s, u"v4.1.0"_s, u"v4.0.0-zh.1.rc.2+new-build"_s, u"v4.0.0-zh.2.dev"_s}) {
      QVERIFY(!PJ::isNewerLocalizedVersion(tag, u"4.0.0-zh.1.rc.2"_s));
    }
  }
  void localizedDefault() {
    PJ::UpdateChecker checker;
    checker.setCurrentVersion(u"4.0.0-zh.1.rc.2"_s);
    QVERIFY(checker.releaseApiUrl().toString().contains(u"reliable-ly0411/PlotJuggler-zh-CN/releases?"_s));
  }
  void newestForkOnly() {
    Server server(
        "[{\"tag_name\":\"v3.18.0-zh.99\"},{\"tag_name\":\"v4.9.0\"},\n      "
        "{\"tag_name\":\"v4.0.0-zh.99\",\"draft\":true},{\"tag_name\":\"v4.0.0-zh.1.rc.10\",\"html_url\":\"https://"
        "bad.invalid\"},\n      {\"tag_name\":\"v4.0.0-zh.1.rc.3\"}]");
    PJ::UpdateChecker checker;
    checker.setCurrentVersion(u"4.0.0-zh.1.rc.2"_s);
    checker.setInstallation(u"windows"_s);
    checker.setMaintenanceToolPath(QCoreApplication::applicationFilePath());
    checker.setReleaseApiUrl(server.url());
    QSignalSpy update(&checker, &PJ::UpdateChecker::updateAvailable);
    QSignalSpy failed(&checker, &PJ::UpdateChecker::checkFailed);
    checker.checkLatestRelease();
    QVERIFY(update.wait(3000));
    QCOMPARE(failed.size(), 0);
    const auto info = update.first().first().value<PJ::ReleaseInfo>();
    QCOMPARE(info.name, u"v4.0.0-zh.1.rc.10"_s);
    QCOMPARE(info.route, PJ::UpdateRoute::Download);
    QCOMPARE(info.html_url, u"https://github.com/reliable-ly0411/PlotJuggler-zh-CN/releases/tag/v4.0.0-zh.1.rc.10"_s);
  }
  void noEligibleUpdate() {
    Server server("[{\"tag_name\":\"v3.99.0-zh.9\"},{\"tag_name\":\"v4.0.0-zh.1.rc.2\"}]");
    PJ::UpdateChecker checker;
    checker.setCurrentVersion(u"4.0.0-zh.1.rc.2"_s);
    checker.setInstallation(u"deb"_s);
    checker.setAptCacheProgram(QCoreApplication::applicationFilePath());
    checker.setReleaseApiUrl(server.url());
    QSignalSpy done(&checker, &PJ::UpdateChecker::upToDate);
    checker.checkLatestRelease();
    QVERIFY(done.wait(3000));
  }
  void malformedResponse() {
    Server server("{}");
    PJ::UpdateChecker checker;
    checker.setCurrentVersion(u"4.0.0-zh.1.rc.2"_s);
    checker.setReleaseApiUrl(server.url());
    QSignalSpy failed(&checker, &PJ::UpdateChecker::checkFailed);
    checker.checkLatestRelease();
    QVERIFY(failed.wait(3000));
  }
#ifndef Q_OS_WIN
  void maintenanceErrorFallsBack() {
    QTemporaryDir temporary;
    const QString path = temporary.filePath(u"maintenance"_s);
    QFile script(path);
    QVERIFY(script.open(QIODevice::WriteOnly));
    script.write("#!/bin/sh\necho 'no repository'\nexit 1\n");
    script.close();
    QVERIFY(script.setPermissions(QFile::ReadOwner | QFile::WriteOwner | QFile::ExeOwner));
    Server server("{\"tag_name\":\"4.1.0\",\"html_url\":\"https://example.test/release\"}");
    PJ::UpdateChecker checker;
    checker.setCurrentVersion(u"4.0.0"_s);
    checker.setInstallation(u"windows"_s);
    checker.setMaintenanceToolPath(path);
    checker.setReleaseApiUrl(server.url());
    QSignalSpy update(&checker, &PJ::UpdateChecker::updateAvailable);
    checker.checkLatestRelease();
    QVERIFY(update.wait(3000));
    QCOMPARE(update.first().first().value<PJ::ReleaseInfo>().route, PJ::UpdateRoute::Download);
  }
#endif
};
QTEST_GUILESS_MAIN(LocalizedUpdateTest)
#include "localized_update_test.moc"
