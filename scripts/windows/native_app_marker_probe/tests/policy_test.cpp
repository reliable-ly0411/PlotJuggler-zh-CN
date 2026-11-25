// SPDX-License-Identifier: MPL-2.0
#include "policy.h"

#include <QCoreApplication>
#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>
#include <QProcess>
#include <QSet>
#include <QTemporaryDir>
#include <QDir>
#include <cstdio>
#include <cstring>
#include <limits>

namespace {
int failures = 0;
void require(bool condition, const char* label) {
  if (!condition) {
    std::fprintf(stderr, "FAIL: %s\n", label);
    ++failures;
  }
}
}

int main(int argc, char** argv) {
  QCoreApplication app(argc, argv);
  if (argc > 1) {
    QProcess process;
    process.start(QString::fromLocal8Bit(argv[1]), {});
    require(process.waitForFinished(10000), "probe exits");
    require(process.exitStatus() == QProcess::NormalExit && process.exitCode() == 3, "unsupported exit");
    const auto json = QJsonDocument::fromJson(process.readAllStandardOutput()).object();
    require(json.value("schema").toString() == "pj-native-app-marker-probe/v1", "schema");
    require(!json.value("ok").toBool(true), "unsupported does not allow launch");
    require(json.value("exit_code").toInt() == 3, "JSON exit agrees with process");
    return failures ? 1 : 0;
  }

  marker_probe::Facts good{true, true, true, true, 0, true, 0};
  require(marker_probe::decide(good) == 0, "all verified empty facts");
  auto x = good; x.identity_ok = false; require(marker_probe::decide(x) == 4, "identity failure");
  x = good; x.qt_ok = false; require(marker_probe::decide(x) == 5, "Qt failure");
  x = good; x.path_ok = false; require(marker_probe::decide(x) == 6, "path failure");
  x = good; x.marker_enumeration_ok = false; require(marker_probe::decide(x) == 6, "marker enumeration failure");
  x = good; x.marker_count = 1; require(marker_probe::decide(x) == 7, "marker present");
  x = good; x.process_enumeration_ok = false; require(marker_probe::decide(x) == 8, "process enumeration failure");
  x = good; x.other_process_count = 1; require(marker_probe::decide(x) == 8, "other process present");
  require(marker_probe::decide({}) != 0, "unknown facts fail closed");
  require(marker_probe::permitsRestrictingSidCount(0), "empty restricting SID list");
  require(!marker_probe::permitsRestrictingSidCount(1), "nonempty restricting SID list");
  require(!marker_probe::permitsRestrictingSidCount(-1), "unknown restricting SID count");
  QByteArray groups(24, '\0');
  quint32 parsed = 99;
  const auto* bytes = reinterpret_cast<const unsigned char*>(groups.constData());
  require(marker_probe::parseRestrictingSidCount(bytes, 4, 8, 16, parsed) && parsed == 0, "four-byte empty group buffer");
  require(marker_probe::parseRestrictingSidCount(bytes, 8, 8, 16, parsed) && parsed == 0, "eight-byte empty group buffer");
  require(!marker_probe::parseRestrictingSidCount(bytes, 3, 8, 16, parsed), "short count rejected");
  quint32 group_count = 1;
  std::memcpy(groups.data(), &group_count, sizeof(group_count));
  bytes = reinterpret_cast<const unsigned char*>(groups.constData());
  require(!marker_probe::parseRestrictingSidCount(bytes, 23, 8, 16, parsed), "truncated nonempty group rejected");
  require(marker_probe::parseRestrictingSidCount(bytes, 24, 8, 16, parsed) && parsed == 1, "complete nonempty group");
  require(!marker_probe::parseRestrictingSidCount(bytes, 24, 8, 0, parsed), "zero group size rejected");
  group_count = std::numeric_limits<quint32>::max();
  std::memcpy(groups.data(), &group_count, sizeof(group_count));
  bytes = reinterpret_cast<const unsigned char*>(groups.constData());
  require(!marker_probe::parseRestrictingSidCount(bytes, 24, 8, 16, parsed), "oversized group count rejected");

  // Only this test's own temporary directory is populated; the production path is never touched.
  QTemporaryDir fixture;
  require(fixture.isValid(), "owned fixture");
  const QStringList names{"active_widgets.0.json", "active_widgets.123.json", "active_widgets.99999999999999999999.json",
                          "active_widgets.12.json.bak", "active_widgets.-1.json", "ACTIVE_WIDGETS.12.json",
                          "active_widgets..json", "active_widgets.13.JSON"};
  QSet<QString> folded_names;
  for (const auto& name : names) {
    require(!folded_names.contains(name.toCaseFolded()), "fixture names remain distinct ignoring case");
    folded_names.insert(name.toCaseFolded());
    QFile file(QDir(fixture.path()).filePath(name));
    require(file.open(QIODevice::WriteOnly | QIODevice::NewOnly), "create owned fixture entry");
  }
  int count = 0;
  for (const auto& name : QDir(fixture.path()).entryList(QDir::Files | QDir::Hidden | QDir::System)) {
    if (marker_probe::isMarkerName(name)) ++count;
  }
  require(count == 3, "exact names and overflow are conservatively detected");
  require(!marker_probe::isMarkerName("ACTIVE_WIDGETS.12.json"), "case-sensitive prefix");
  require(!marker_probe::isMarkerName("active_widgets.13.JSON"), "case-sensitive suffix");
  require(!marker_probe::isMarkerName("active_widgets.١٢.json"), "ASCII digit semantics");
  return failures ? 1 : 0;
}
