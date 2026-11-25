// SPDX-License-Identifier: MPL-2.0
// Read-only launch preflight. Its successful result is a snapshot, not a lock.
#include "policy.h"

#include <QCoreApplication>
#include <QDateTime>
#include <QDir>
#include <QFileInfo>
#include <QJsonDocument>
#include <QJsonObject>
#include <QMap>
#include <QRegularExpression>
#include <QStandardPaths>
#include <QStringList>
#include <cstddef>
#include <cstdio>
#include <limits>
#include <string>

#ifdef Q_OS_WIN
#define NOMINMAX
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <sddl.h>
#include <tlhelp32.h>
#include <vector>
#endif

namespace {

// All output is one UTF-8 JSON document, including failures.
int emitResult(QJsonObject result, int code, const QString& reason) {
  result.insert("ok", code == 0);
  result.insert("exit_code", code);
  result.insert("reason", reason);
  result.insert("completed_at_utc", QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs));
  const QByteArray bytes = QJsonDocument(result).toJson(QJsonDocument::Compact) + '\n';
  if (std::fwrite(bytes.constData(), 1, static_cast<size_t>(bytes.size()), stdout) != static_cast<size_t>(bytes.size()) ||
      std::fflush(stdout) != 0) {
    return 9;
  }
  return code;
}

#ifdef Q_OS_WIN

// Own a Windows HANDLE, never a pseudo-handle or a FindFirstFile handle.
class Handle {
public:
  explicit Handle(HANDLE value = nullptr) : value_(value) {}
  ~Handle() { if (value_ && value_ != INVALID_HANDLE_VALUE) CloseHandle(value_); }
  Handle(const Handle&) = delete;
  Handle& operator=(const Handle&) = delete;
  HANDLE get() const { return value_; }
private:
  HANDLE value_;
};

struct Expected {
  QString sid;
  quint32 session = 0;
  quint32 integrity = 0;
  QString auth_luid;
  QString elevation;
  QString qt_core;
};

// These expectations are independently acquired by the launcher's caller.
bool parseExpected(const QStringList& args, Expected& out) {
  const QStringList keys{"--expect-sid", "--expect-session", "--expect-integrity-rid", "--expect-auth-luid",
                         "--expect-elevation-type", "--expect-qt-core"};
  if (args.size() != 1 + keys.size() * 2) return false;
  QMap<QString, QString> values;
  for (int i = 1; i < args.size(); i += 2) {
    if (!keys.contains(args[i]) || values.contains(args[i]) || args[i + 1].isEmpty()) return false;
    values.insert(args[i], args[i + 1]);
  }
  bool session_ok = false, integrity_ok = false;
  const qulonglong session = values["--expect-session"].toULongLong(&session_ok, 10);
  const qulonglong integrity = values["--expect-integrity-rid"].toULongLong(&integrity_ok, 10);
  if (!session_ok || !integrity_ok || session > std::numeric_limits<quint32>::max() ||
      integrity > std::numeric_limits<quint32>::max()) return false;
  static const QRegularExpression luid(QStringLiteral("^[0-9A-Fa-f]{8}:[0-9A-Fa-f]{8}$"));
  if (!luid.match(values["--expect-auth-luid"]).hasMatch()) return false;
  const QString elevation = values["--expect-elevation-type"];
  if (elevation != "default" && elevation != "full" && elevation != "limited") return false;
  const QString qt = QDir::fromNativeSeparators(values["--expect-qt-core"]);
  static const QRegularExpression drive_absolute(QStringLiteral("^[A-Za-z]:/"));
  if (!drive_absolute.match(qt).hasMatch() || QDir::cleanPath(qt) != qt ||
      QFileInfo(qt).fileName().compare("Qt6Core.dll", Qt::CaseInsensitive) != 0) return false;
  out = {values["--expect-sid"], static_cast<quint32>(session), static_cast<quint32>(integrity),
         values["--expect-auth-luid"].toLower(), elevation, qt};
  return true;
}

// Token buffers outlive all Win32 pointers into them.
bool tokenInfo(HANDLE token, TOKEN_INFORMATION_CLASS type, std::vector<unsigned char>& bytes) {
  DWORD size = 0;
  if (GetTokenInformation(token, type, nullptr, 0, &size)) return false;
  if (GetLastError() != ERROR_INSUFFICIENT_BUFFER || size == 0) return false;
  bytes.resize(size);
  if (!GetTokenInformation(token, type, bytes.data(), size, &size) || size > bytes.size()) return false;
  bytes.resize(size);
  return true;
}

// Return only the count of restricting SIDs; a zero count does not rule out filtering.
bool restrictingSidCount(HANDLE token, DWORD& count, std::size_t* returned_size = nullptr) {
  std::vector<unsigned char> restricting_sids;
  if (!tokenInfo(token, TokenRestrictedSids, restricting_sids)) return false;
  static_assert(sizeof(DWORD) == sizeof(quint32));
  quint32 parsed = 0;
  if (!marker_probe::parseRestrictingSidCount(restricting_sids.data(), restricting_sids.size(),
                                               offsetof(TOKEN_GROUPS, Groups), sizeof(SID_AND_ATTRIBUTES), parsed)) return false;
  count = parsed;
  if (returned_size) *returned_size = restricting_sids.size();
  return true;
}

// Check only these specific service identities; a different SID is not proof of an interactive session.
bool forbiddenServiceIdentity(PSID sid, bool& forbidden) {
  forbidden = false;
  constexpr WELL_KNOWN_SID_TYPE service_types[]{WinLocalSystemSid, WinLocalServiceSid, WinNetworkServiceSid};
  for (const auto type : service_types) {
    alignas(DWORD) BYTE known_sid[SECURITY_MAX_SID_SIZE];
    DWORD known_size = sizeof(known_sid);
    if (!CreateWellKnownSid(type, nullptr, known_sid, &known_size)) return false;
    if (EqualSid(sid, known_sid)) forbidden = true;
  }
  return true;
}

// Refuse forbidden service identities, session 0, restricting SIDs and identity mismatches.
bool checkIdentity(const Expected& expected, QJsonObject& report, QString& reason) {
  HANDLE raw_thread = nullptr;
  if (OpenThreadToken(GetCurrentThread(), TOKEN_QUERY, TRUE, &raw_thread)) {
    CloseHandle(raw_thread);
    reason = "thread_impersonation";
    return false;
  }
  if (GetLastError() != ERROR_NO_TOKEN) { reason = "thread_token_unavailable"; return false; }
  HANDLE raw = nullptr;
  if (!OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &raw)) { reason = "process_token_unavailable"; return false; }
  Handle token(raw);
  std::vector<unsigned char> user, session, integrity, statistics, elevation, token_type, container;
  if (!tokenInfo(token.get(), TokenUser, user) || !tokenInfo(token.get(), TokenSessionId, session) ||
      !tokenInfo(token.get(), TokenIntegrityLevel, integrity) || !tokenInfo(token.get(), TokenStatistics, statistics) ||
      !tokenInfo(token.get(), TokenElevationType, elevation) || !tokenInfo(token.get(), TokenType, token_type) ||
      !tokenInfo(token.get(), TokenIsAppContainer, container)) {
    reason = "token_information_unavailable";
    return false;
  }
  const auto* token_user = reinterpret_cast<const TOKEN_USER*>(user.data());
  const auto* label = reinterpret_cast<const TOKEN_MANDATORY_LABEL*>(integrity.data());
  if (!IsValidSid(token_user->User.Sid) || !IsValidSid(label->Label.Sid) ||
      *GetSidSubAuthorityCount(label->Label.Sid) == 0) { reason = "invalid_token_sid"; return false; }
  LPWSTR sid_string = nullptr;
  if (!ConvertSidToStringSidW(token_user->User.Sid, &sid_string)) { reason = "sid_conversion_failed"; return false; }
  const QString sid = QString::fromWCharArray(sid_string);
  LocalFree(sid_string);
  const DWORD session_id = *reinterpret_cast<const DWORD*>(session.data());
  DWORD process_session = 0;
  if (!ProcessIdToSessionId(GetCurrentProcessId(), &process_session)) { reason = "process_session_unavailable"; return false; }
  const auto authority_index = *GetSidSubAuthorityCount(label->Label.Sid) - 1;
  const DWORD integrity_rid = *GetSidSubAuthority(label->Label.Sid, authority_index);
  const auto* stats = reinterpret_cast<const TOKEN_STATISTICS*>(statistics.data());
  const QString auth_luid = QStringLiteral("%1:%2")
      .arg(static_cast<quint32>(stats->AuthenticationId.HighPart), 8, 16, QLatin1Char('0'))
      .arg(static_cast<quint32>(stats->AuthenticationId.LowPart), 8, 16, QLatin1Char('0'));
  const auto elevation_type = *reinterpret_cast<const TOKEN_ELEVATION_TYPE*>(elevation.data());
  QString elevation_name;
  if (elevation_type == TokenElevationTypeDefault) elevation_name = "default";
  else if (elevation_type == TokenElevationTypeFull) elevation_name = "full";
  else if (elevation_type == TokenElevationTypeLimited) elevation_name = "limited";
  DWORD restricting_sid_count = 0;
  if (!restrictingSidCount(token.get(), restricting_sid_count)) { reason = "restricting_sids_unavailable"; return false; }
  const bool app_container = *reinterpret_cast<const DWORD*>(container.data()) != 0;
  report = {{"sid", sid}, {"session", static_cast<qint64>(session_id)},
            {"process_session", static_cast<qint64>(process_session)},
            {"integrity_rid", static_cast<qint64>(integrity_rid)}, {"auth_luid", auth_luid},
            {"elevation_type", elevation_name}, {"restricting_sid_count", static_cast<qint64>(restricting_sid_count)},
            {"app_container", app_container}};
  PSID expected_sid = nullptr;
  const std::wstring sid_text = expected.sid.toStdWString();
  if (!ConvertStringSidToSidW(sid_text.c_str(), &expected_sid)) { reason = "invalid_expected_sid"; return false; }
  const bool sid_matches = EqualSid(token_user->User.Sid, expected_sid) != FALSE;
  LocalFree(expected_sid);
  bool service_identity = false;
  if (!forbiddenServiceIdentity(token_user->User.Sid, service_identity)) { reason = "service_sid_unavailable"; return false; }
  if (!sid_matches || session_id != expected.session || integrity_rid != expected.integrity ||
      auth_luid != expected.auth_luid || elevation_name.isEmpty() || elevation_name != expected.elevation) {
    reason = "identity_attribute_mismatch"; return false;
  }
  if (service_identity || session_id == 0 || process_session != session_id ||
      *reinterpret_cast<const TOKEN_TYPE*>(token_type.data()) != TokenPrimary ||
      !marker_probe::permitsRestrictingSidCount(restricting_sid_count) || app_container) {
    reason = "identity_forbidden_token"; return false;
  }
  return true;
}

// Require the exact Qt DLL path pinned independently to the app's launch kit.
bool checkQt(const Expected& expected, QJsonObject& report, QString& reason) {
  const QString runtime = QString::fromLatin1(qVersion());
  report.insert("runtime_version", runtime);
  report.insert("compiled_version", QStringLiteral(PROBE_QT_VERSION));
  HMODULE qt = GetModuleHandleW(L"Qt6Core.dll");
  if (!qt) { reason = "qt_core_module_missing"; return false; }
  std::vector<wchar_t> module_path(32768);
  const DWORD size = GetModuleFileNameW(qt, module_path.data(), static_cast<DWORD>(module_path.size()));
  if (size == 0 || size >= module_path.size()) { reason = "qt_core_module_path_unavailable"; return false; }
  const QString actual = QDir::fromNativeSeparators(QString::fromWCharArray(module_path.data(), size));
  report.insert("core_module_path", actual);
  if (runtime != QStringLiteral(PROBE_QT_VERSION) || QDir::cleanPath(actual) != actual ||
      actual.compare(expected.qt_core, Qt::CaseInsensitive) != 0) {
    reason = "qt_version_or_module_mismatch"; return false;
  }
  return true;
}

using OpenDirectory = HANDLE (WINAPI*)(LPCWSTR, DWORD, DWORD, LPSECURITY_ATTRIBUTES, DWORD, DWORD, HANDLE);

// Opening with OPEN_REPARSE_POINT prevents accepting an existing junction as a directory.
bool inspectDirectory(const QString& path, bool& missing, QString& reason, OpenDirectory open_directory = CreateFileW) {
  const std::wstring native = QDir::toNativeSeparators(path).toStdWString();
  Handle dir(open_directory(native.c_str(), FILE_READ_ATTRIBUTES, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                            nullptr, OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, nullptr));
  if (dir.get() == INVALID_HANDLE_VALUE) {
    const DWORD error = GetLastError();
    if (error == ERROR_FILE_NOT_FOUND || error == ERROR_PATH_NOT_FOUND) { missing = true; return true; }
    reason = QStringLiteral("directory_open_failed:%1").arg(error); return false;
  }
  FILE_ATTRIBUTE_TAG_INFO info{};
  if (!GetFileInformationByHandleEx(dir.get(), FileAttributeTagInfo, &info, sizeof(info))) {
    reason = QStringLiteral("directory_attributes_failed:%1").arg(GetLastError()); return false;
  }
  if (!(info.FileAttributes & FILE_ATTRIBUTE_DIRECTORY) || (info.FileAttributes & FILE_ATTRIBUTE_REPARSE_POINT)) {
    reason = "non_directory_or_reparse"; return false;
  }
  std::vector<wchar_t> final_path(32768);
  const DWORD size = GetFinalPathNameByHandleW(dir.get(), final_path.data(), static_cast<DWORD>(final_path.size()),
                                               FILE_NAME_NORMALIZED | VOLUME_NAME_DOS);
  if (size == 0 || size >= final_path.size()) { reason = "directory_final_path_unavailable"; return false; }
  QString resolved = QString::fromWCharArray(final_path.data(), size);
  if (!resolved.startsWith(QStringLiteral("\\\\?\\"))) { reason = "directory_final_path_uncertain"; return false; }
  resolved = QDir::cleanPath(QDir::fromNativeSeparators(resolved.mid(4)));
  if (resolved.compare(QDir::cleanPath(path), Qt::CaseInsensitive) != 0) {
    reason = "directory_alias_or_changed_path"; return false;
  }
  return true;
}

// Enumerate metadata only; the optional count never reads record contents.
bool enumerateDirectory(const QString& path, qint64* count, QString& reason) {
  const std::wstring query = (QDir::toNativeSeparators(path) + QStringLiteral("\\*")).toStdWString();
  WIN32_FIND_DATAW entry{};
  HANDLE find = FindFirstFileW(query.c_str(), &entry);
  if (find == INVALID_HANDLE_VALUE) {
    const DWORD error = GetLastError();
    if (error == ERROR_FILE_NOT_FOUND) return true;
    reason = QStringLiteral("directory_enumeration_failed:%1").arg(error); return false;
  }
  bool ok = true;
  do {
    if (count && marker_probe::isMarkerName(QString::fromWCharArray(entry.cFileName))) ++*count;
  } while (FindNextFileW(find, &entry));
  const DWORD error = GetLastError();
  if (error != ERROR_NO_MORE_FILES) { reason = QStringLiteral("directory_enumeration_failed:%1").arg(error); ok = false; }
  FindClose(find);
  return ok;
}

// Check every ancestor from the volume root, then enumerate only the default path.
bool scanMarkerDirectory(const QString& path, bool& exists, qint64& count, QString& reason,
                         OpenDirectory open_directory = CreateFileW) {
  const QString portable = QDir::fromNativeSeparators(path);
  static const QRegularExpression drive_absolute(QStringLiteral("^[A-Za-z]:/"));
  if (!drive_absolute.match(portable).hasMatch() || QDir::cleanPath(portable) != portable ||
      portable.size() <= 3) { reason = "marker_path_uncertain"; return false; }
  QString current = portable.left(3);
  const std::wstring root = QDir::toNativeSeparators(current).toStdWString();
  if (GetDriveTypeW(root.c_str()) != DRIVE_FIXED) { reason = "marker_volume_not_fixed"; return false; }
  bool missing = false;
  if (!inspectDirectory(current, missing, reason, open_directory) || missing) {
    if (missing) reason = "volume_root_missing";
    return false;
  }
  for (const QString& part : portable.mid(3).split('/', Qt::SkipEmptyParts)) {
    const QString parent = current;
    current = QDir(current).filePath(part);
    if (!inspectDirectory(current, missing, reason, open_directory)) return false;
    if (missing) {
      // An absent child is only trusted if its existing parent is enumerable.
      if (!enumerateDirectory(parent, nullptr, reason)) return false;
      exists = false;
      return true;
    }
  }
  exists = true;
  return enumerateDirectory(current, &count, reason);
}

using NextProcess = BOOL (WINAPI*)(HANDLE, LPPROCESSENTRY32W);

// Results are usable only on success; arbitrary renames remain a documented limit.
bool scanProcesses(qint64& count, QString& reason, DWORD observed_pid = 0, bool* observed_candidate = nullptr,
                   NextProcess next_process = Process32NextW) {
  if (observed_candidate) *observed_candidate = false;
  Handle snapshot(CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0));
  if (snapshot.get() == INVALID_HANDLE_VALUE) { reason = "process_snapshot_failed"; return false; }
  PROCESSENTRY32W entry{};
  entry.dwSize = sizeof(entry);
  if (!Process32FirstW(snapshot.get(), &entry)) { reason = "process_enumeration_failed"; return false; }
  do {
    const QString name = QString::fromWCharArray(entry.szExeFile).toCaseFolded();
    if (entry.th32ProcessID != GetCurrentProcessId() &&
        ((name.contains("plotjuggler") && name.endsWith(".exe")) || name == "pj_app.exe")) {
      ++count;
      if (observed_candidate && entry.th32ProcessID == observed_pid) *observed_candidate = true;
    }
  } while (next_process(snapshot.get(), &entry));
  if (GetLastError() != ERROR_NO_MORE_FILES) { reason = "process_enumeration_failed"; return false; }
  return true;
}
#endif  // Q_OS_WIN
}  // namespace

#ifndef MARKER_PROBE_NO_MAIN
int main(int argc, char** argv) {
  QCoreApplication app(argc, argv);
  QCoreApplication::setOrganizationName(QStringLiteral("PlotJuggler"));
  QCoreApplication::setApplicationName(QStringLiteral("PlotJuggler4"));
  QJsonObject result{{"schema", "pj-native-app-marker-probe/v1"},
                     {"checked_at_utc", QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs)},
                     {"probe_pid", QCoreApplication::applicationPid()},
                     {"token", QJsonValue::Null}, {"qt", QJsonValue::Null},
                     {"marker_directory", QJsonValue::Null}, {"marker_directory_exists", QJsonValue::Null},
                     {"marker_enumeration_ok", QJsonValue::Null}, {"matching_marker_count", QJsonValue::Null},
                     {"process_enumeration_ok", QJsonValue::Null}, {"other_app_process_count", QJsonValue::Null}};
#ifndef Q_OS_WIN
  result.insert("platform", "unsupported");
  return emitResult(result, 3, "windows_required");
#else
  result.insert("platform", "windows");
  Expected expected;
  if (!parseExpected(app.arguments(), expected)) return emitResult(result, 2, "invalid_arguments");
  marker_probe::Facts facts;
  QString reason;
  QJsonObject token_report;
  facts.identity_ok = checkIdentity(expected, token_report, reason);
  result.insert("token", token_report);
  if (!facts.identity_ok) return emitResult(result, 4, reason);
  QJsonObject qt_report;
  facts.qt_ok = checkQt(expected, qt_report, reason);
  result.insert("qt", qt_report);
  if (!facts.qt_ok) return emitResult(result, 5, reason);
  const QString directory = QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation);
  result.insert("marker_directory", directory);
  bool exists = false;
  facts.path_ok = scanMarkerDirectory(directory, exists, facts.marker_count, reason);
  facts.marker_enumeration_ok = facts.path_ok;
  result.insert("marker_enumeration_ok", facts.marker_enumeration_ok);
  if (!facts.path_ok) return emitResult(result, 6, reason);
  result.insert("marker_directory_exists", exists);
  result.insert("matching_marker_count", facts.marker_count);
  facts.process_enumeration_ok = scanProcesses(facts.other_process_count, reason);
  result.insert("process_enumeration_ok", facts.process_enumeration_ok);
  if (facts.process_enumeration_ok) result.insert("other_app_process_count", facts.other_process_count);
  const int code = marker_probe::decide(facts);
  if (code == 7) reason = "matching_marker_present";
  else if (code == 8 && facts.process_enumeration_ok) reason = "other_app_process_present";
  else if (code == 0) reason = "clean_snapshot";
  return emitResult(result, code, reason);
#endif
}
#endif
