// SPDX-License-Identifier: MPL-2.0
#include <QApplication>
#include <QDir>
#include <QFile>
#include <QTemporaryDir>
#include <QtTest/QtTest>

#include "pj_widgets/ExternalUrl.h"
#include "pj_widgets/ToastNotification.h"

using namespace Qt::StringLiterals;

namespace {

// Decode env -0 without losing empty values, Unicode, or newlines.
QProcessEnvironment readEnvironment(const QByteArray& bytes) {
  QProcessEnvironment result;
  for (const auto& entry : bytes.split('\0')) {
    const auto separator = entry.indexOf('=');
    if (separator > 0) {
      result.insert(QString::fromUtf8(entry.first(separator)), QString::fromUtf8(entry.sliced(separator + 1)));
    }
  }
  return result;
}

// All fixture executables live in a temporary test tree and only record input.
bool writeExecutable(const QString& path, const QByteArray& bytes) {
  QFile file(path);
  return file.open(QIODevice::WriteOnly) && file.write(bytes) == bytes.size() &&
         file.setPermissions(QFile::ReadOwner | QFile::WriteOwner | QFile::ExeOwner);
}

QByteArray readBytes(const QString& path) {
  QFile file(path);
  return file.open(QIODevice::ReadOnly) ? file.readAll() : QByteArray{};
}

}  // namespace

class AppImageExternalUrlTest : public QObject {
  Q_OBJECT

 private slots:
  void restoreAndLaunch_data() {
    QTest::addColumn<int>("state");
    QTest::addColumn<QString>("broken_snapshot");
    QTest::newRow("unset") << 0 << QString{};
    QTest::newRow("empty") << 1 << QString{};
    QTest::newRow("unicode-spaces-newline") << 2 << QString{};
    QTest::newRow("http-mixed-states") << 3 << QString{};
    for (const char* key :
         {"LD_LIBRARY_PATH", "QT_PLUGIN_PATH", "XDG_DATA_DIRS", "PYTHONHOME", "GRPC_DEFAULT_SSL_ROOTS_FILE_PATH",
          "QT_IM_MODULE"}) {
      const auto saved = QByteArray("PJ_APPIMAGE_HOST_") + key;
      QTest::newRow((saved + "-missing-flag").constData()) << 2 << QString::fromLatin1(saved + "_SET");
      QTest::newRow((saved + "-missing-value").constData()) << 2 << QString::fromLatin1(saved);
    }
    QTest::newRow("invalid-state") << 2 << u"invalid-state"_s;
  }

  void restoreAndLaunch() {
    QFETCH(int, state);
    QFETCH(QString, broken_snapshot);
    const bool complete = broken_snapshot.isEmpty();
    QTemporaryDir directory;
    QVERIFY(directory.isValid());
    const auto root = directory.path();
    QVERIFY(QDir().mkpath(root + u"/usr/bin"_s));
    QVERIFY(QDir().mkpath(root + u"/desktop opener"_s));
    QVERIFY(writeExecutable(root + u"/usr/bin/plotjuggler4"_s, "#!/bin/sh\nexec /usr/bin/env -0\n"));
    QVERIFY(writeExecutable(
        root + u"/desktop opener/xdg-open"_s,
        "#!/bin/sh\nset -e\n/usr/bin/env -0 > \"$PJ_TEST_OPEN_ENV\"\n"
        "printf '%s\\0' \"$@\" > \"$PJ_TEST_OPEN_ARGS\"\n"
        "printf done > \"$PJ_TEST_OPEN_DONE\"\n"));

    auto host = QProcessEnvironment::systemEnvironment();
    const QStringList keys = {u"LD_LIBRARY_PATH"_s,
                              u"QT_PLUGIN_PATH"_s,
                              u"XDG_DATA_DIRS"_s,
                              u"PYTHONHOME"_s,
                              u"GRPC_DEFAULT_SSL_ROOTS_FILE_PATH"_s,
                              u"QT_IM_MODULE"_s};
    for (qsizetype index = 0; index < keys.size(); ++index) {
      const auto& key = keys.at(index);
      const auto value_state = state == 3 ? index % 3 : state;
      host.remove(key);
      if (value_state != 0) {
        host.insert(key, value_state == 1 ? QString{} : u"/host path/中文\nsecond line:"_s + key);
      }
    }
    host.insert(u"APPDIR"_s, root);
    host.insert(u"PATH"_s, root + u"/desktop opener:"_s + host.value(u"PATH"_s));
    host.insert(u"PJ_TEST_OPEN_ENV"_s, root + u"/opened.env"_s);
    host.insert(u"PJ_TEST_OPEN_ARGS"_s, root + u"/opened.args"_s);
    host.insert(u"PJ_TEST_OPEN_DONE"_s, root + u"/opened.done"_s);
    host.insert(u"PJ_TEST_AFTER"_s, root + u"/after.txt"_s);
    host.insert(u"PJ_TEST_UNRELATED"_s, u"retained 中文"_s);

    QProcess launcher;
    launcher.setProcessEnvironment(host);
    launcher.start(u"/bin/bash"_s, {QString::fromUtf8(PJ_APPRUN_SOURCE)});
    QVERIFY(launcher.waitForFinished(5000));
    QCOMPARE(launcher.exitCode(), 0);
    auto bundled = readEnvironment(launcher.readAllStandardOutput());
    QCOMPARE(bundled.value(u"PJ_APPIMAGE_HOST_ENV"_s), u"1"_s);
    QVERIFY(bundled.value(u"LD_LIBRARY_PATH"_s).startsWith(root + u"/usr/lib"_s));
    QVERIFY(!bundled.contains(u"QT_IM_MODULE"_s));
    if (broken_snapshot == u"invalid-state") {
      bundled.insert(u"PJ_APPIMAGE_HOST_QT_IM_MODULE_SET"_s, u"invalid"_s);
    } else if (!complete) {
      bundled.remove(broken_snapshot);
    }

    QUrl url(u"https://example.invalid/中文?space=one two&literal=$(nothing);quote=\"x\""_s);
    if (state == 3) {
      url.setScheme(u"http"_s);
    }
    QProcess helper;
    helper.setProcessEnvironment(bundled);
    helper.start(QCoreApplication::applicationFilePath(), {u"--launch-test-url"_s, url.toString(QUrl::FullyEncoded)});
    QVERIFY(helper.waitForFinished(5000));
    QCOMPARE(helper.exitCode(), complete ? 0 : 1);
    QCOMPARE(readBytes(root + u"/after.txt"_s), QByteArray("unchanged"));
    if (!complete) {
      QVERIFY(!QFile::exists(root + u"/opened.done"_s));
      return;
    }
    QTRY_VERIFY_WITH_TIMEOUT(QFile::exists(root + u"/opened.done"_s), 5000);
    const auto opened = readEnvironment(readBytes(root + u"/opened.env"_s));
    for (const auto& key : keys) {
      QCOMPARE(opened.contains(key), host.contains(key));
      QCOMPARE(opened.value(key), host.value(key));
      QVERIFY(!opened.contains(u"PJ_APPIMAGE_HOST_"_s + key));
      QVERIFY(!opened.contains(u"PJ_APPIMAGE_HOST_"_s + key + u"_SET"_s));
    }
    QCOMPARE(opened.value(u"PJ_TEST_UNRELATED"_s), host.value(u"PJ_TEST_UNRELATED"_s));
    QVERIFY(!opened.contains(u"PJ_APPIMAGE_HOST_ENV"_s));
    QCOMPARE(readBytes(root + u"/opened.args"_s), url.toString(QUrl::FullyEncoded).toUtf8() + QByteArray(1, '\0'));
  }

  void init() {
    marker_was_set_ = qEnvironmentVariableIsSet("PJ_APPIMAGE_HOST_ENV");
    original_marker_ = qgetenv("PJ_APPIMAGE_HOST_ENV");
  }

  void defaultHandlerWithoutAppImage() {
    qunsetenv("PJ_APPIMAGE_HOST_ENV");
    QDesktopServices::setUrlHandler(u"https"_s, this, "rememberUrl");
    const QUrl url(u"https://example.invalid/native"_s);
    QVERIFY(PJ::openExternalUrl(url));
    QCOMPARE(received_, url);
  }

  void toastLinkUsesSharedOpener() {
    qunsetenv("PJ_APPIMAGE_HOST_ENV");
    QDesktopServices::setUrlHandler(u"https"_s, this, "rememberUrl");
    const QUrl url(u"https://example.invalid/release"_s);
    PJ::ToastNotification toast(u"<a href=\"https://example.invalid/release\">Release</a>"_s);
    auto* label = toast.findChild<QLabel*>(u"toastMessage"_s);
    QVERIFY(label);
    QVERIFY(!label->openExternalLinks());
    Q_EMIT label->linkActivated(url.toString());
    QCOMPARE(received_, url);
  }

  void customSchemeRemainsQtHandled_data() {
    QTest::addColumn<QUrl>("url");
    QTest::newRow("custom-scheme") << QUrl(u"pj-url-test:manual-update"_s);
    QTest::newRow("file-directory") << QUrl::fromLocalFile(QDir::tempPath());
  }

  void customSchemeRemainsQtHandled() {
    QFETCH(QUrl, url);
    // An intentionally incomplete AppImage snapshot must not affect non-HTTP URLs.
    qputenv("PJ_APPIMAGE_HOST_ENV", "1");
    QDesktopServices::setUrlHandler(url.scheme(), this, "rememberUrl");
    QVERIFY(PJ::openExternalUrl(url));
    QCOMPARE(received_, url);
  }

  void cleanup() {
    if (marker_was_set_) {
      qputenv("PJ_APPIMAGE_HOST_ENV", original_marker_);
    } else {
      qunsetenv("PJ_APPIMAGE_HOST_ENV");
    }
    QDesktopServices::unsetUrlHandler(u"https"_s);
    QDesktopServices::unsetUrlHandler(u"pj-url-test"_s);
    QDesktopServices::unsetUrlHandler(u"file"_s);
    received_.clear();
  }

 public slots:
  void rememberUrl(const QUrl& url) {
    received_ = url;
  }

 private:
  QUrl received_;
  QByteArray original_marker_;
  bool marker_was_set_ = false;
};

int main(int argc, char** argv) {
  if (argc == 3 && QString::fromLocal8Bit(argv[1]) == u"--launch-test-url") {
    QCoreApplication application(argc, argv);
    const auto arguments = application.arguments();
    const auto before = QProcessEnvironment::systemEnvironment();
    const bool started = PJ::openExternalUrl(QUrl(arguments.at(2)));
    QFile result(before.value(u"PJ_TEST_AFTER"_s));
    if (!result.open(QIODevice::WriteOnly)) {
      return 2;
    }
    result.write(before == QProcessEnvironment::systemEnvironment() ? "unchanged" : "changed");
    return started ? 0 : 1;
  }
  QApplication application(argc, argv);
  AppImageExternalUrlTest test;
  return QTest::qExec(&test, argc, argv);
}

#include "appimage_external_url_test.moc"
