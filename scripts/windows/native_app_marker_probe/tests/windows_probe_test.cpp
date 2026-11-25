// SPDX-License-Identifier: MPL-2.0
// Exercises the actual private Win32 helpers without adding test options to the production CLI.
#define MARKER_PROBE_NO_MAIN
#include "../main.cpp"

#include <QElapsedTimer>
#include <QFile>
#include <QJsonParseError>
#include <QProcess>
#include <QTemporaryDir>
#include <QThread>
#include <winioctl.h>
#include <algorithm>
#include <cstring>

namespace {

// Failures do not turn unavailable Windows features into successful test evidence.
int fail(const char* message) {
  std::fprintf(stderr, "FAIL: %s (Win32 %lu)\n", message, static_cast<unsigned long>(GetLastError()));
  return 1;
}
int skip(const char* message) {
  std::fprintf(stderr, "SKIP: %s (Win32 %lu)\n", message, static_cast<unsigned long>(GetLastError()));
  return 77;
}

// Independent test query: expectations are not copied from probe output or its token helper.
bool directTokenInfo(HANDLE token, TOKEN_INFORMATION_CLASS type, std::vector<unsigned char>& bytes) {
  DWORD needed = 0;
  if (GetTokenInformation(token, type, nullptr, 0, &needed) || GetLastError() != ERROR_INSUFFICIENT_BUFFER || needed == 0) {
    return false;
  }
  bytes.resize(needed);
  DWORD returned = 0;
  if (!GetTokenInformation(token, type, bytes.data(), needed, &returned) || returned > needed) return false;
  bytes.resize(returned);
  return true;
}

// Query the current token independently rather than treating the probe's JSON as an expectation.
bool expectedFromToken(HANDLE token, Expected& expected) {
  std::vector<unsigned char> user, session, integrity, statistics, elevation;
  if (!directTokenInfo(token, TokenUser, user) || !directTokenInfo(token, TokenSessionId, session) ||
      !directTokenInfo(token, TokenIntegrityLevel, integrity) || !directTokenInfo(token, TokenStatistics, statistics) ||
      !directTokenInfo(token, TokenElevationType, elevation)) return false;
  const auto* token_user = reinterpret_cast<const TOKEN_USER*>(user.data());
  const auto* label = reinterpret_cast<const TOKEN_MANDATORY_LABEL*>(integrity.data());
  if (!IsValidSid(token_user->User.Sid) || !IsValidSid(label->Label.Sid) ||
      *GetSidSubAuthorityCount(label->Label.Sid) == 0) return false;
  LPWSTR sid = nullptr;
  if (!ConvertSidToStringSidW(token_user->User.Sid, &sid)) return false;
  expected.sid = QString::fromWCharArray(sid);
  LocalFree(sid);
  expected.session = *reinterpret_cast<const DWORD*>(session.data());
  expected.integrity = *GetSidSubAuthority(label->Label.Sid, *GetSidSubAuthorityCount(label->Label.Sid) - 1);
  const auto* stats = reinterpret_cast<const TOKEN_STATISTICS*>(statistics.data());
  expected.auth_luid = QStringLiteral("%1:%2")
      .arg(static_cast<quint32>(stats->AuthenticationId.HighPart), 8, 16, QLatin1Char('0'))
      .arg(static_cast<quint32>(stats->AuthenticationId.LowPart), 8, 16, QLatin1Char('0'));
  const auto kind = *reinterpret_cast<const TOKEN_ELEVATION_TYPE*>(elevation.data());
  if (kind == TokenElevationTypeDefault) expected.elevation = "default";
  else if (kind == TokenElevationTypeFull) expected.elevation = "full";
  else if (kind == TokenElevationTypeLimited) expected.elevation = "limited";
  else return false;
  return true;
}

// Independently decide whether this exact process token is eligible for the positive check.
bool expectedEligibility(HANDLE token, const Expected& expected, bool& eligible, bool& impersonating, DWORD& count) {
  std::vector<unsigned char> groups, type, container;
  if (!directTokenInfo(token, TokenRestrictedSids, groups) || groups.size() < sizeof(DWORD) ||
      !directTokenInfo(token, TokenType, type) || type.size() < sizeof(TOKEN_TYPE) ||
      !directTokenInfo(token, TokenIsAppContainer, container) || container.size() < sizeof(DWORD)) return false;
  std::memcpy(&count, groups.data(), sizeof(count));
  DWORD process_session = 0;
  if (!ProcessIdToSessionId(GetCurrentProcessId(), &process_session)) return false;
  HANDLE raw_thread = nullptr;
  impersonating = false;
  if (OpenThreadToken(GetCurrentThread(), TOKEN_QUERY, TRUE, &raw_thread)) {
    CloseHandle(raw_thread);
    impersonating = true;
  } else if (GetLastError() != ERROR_NO_TOKEN) {
    return false;
  }
  const bool service = expected.sid == "S-1-5-18" || expected.sid == "S-1-5-19" || expected.sid == "S-1-5-20";
  eligible = !impersonating && !service && expected.session != 0 && expected.session == process_session && count == 0 &&
             *reinterpret_cast<const TOKEN_TYPE*>(type.data()) == TokenPrimary &&
             *reinterpret_cast<const DWORD*>(container.data()) == 0;
  return true;
}

// An additional restricted token is only queried as a handle, never applied to a process or thread.
int identityCase() {
  HANDLE raw = nullptr;
  if (!OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY | TOKEN_DUPLICATE, &raw)) return fail("open process token");
  Handle token(raw);
  Expected expected;
  if (!expectedFromToken(token.get(), expected)) return fail("query actual token attributes");
  bool eligible = false;
  bool impersonating = false;
  DWORD independent_count = 0;
  if (!expectedEligibility(token.get(), expected, eligible, impersonating, independent_count)) {
    return fail("query independent eligibility");
  }
  if (impersonating) return skip("test thread is impersonating");
  DWORD actual_count = 0;
  std::size_t returned_size = 0;
  if (!restrictingSidCount(token.get(), actual_count, &returned_size)) return fail("query actual restricting SID list");
  std::fprintf(stdout, "TokenRestrictedSids ReturnLength=%zu, GroupCount=%lu\n", returned_size,
               static_cast<unsigned long>(actual_count));
  if (actual_count != independent_count) return fail("independent restricting SID count mismatch");
  DWORD invalid_count = 0;
  if (restrictingSidCount(INVALID_HANDLE_VALUE, invalid_count)) return fail("invalid token query must fail");
  QJsonObject report;
  QString reason;
  const bool actual_allowed = checkIdentity(expected, report, reason);
  if (actual_allowed != eligible || (!eligible && reason != "identity_forbidden_token")) {
    return fail("actual token eligibility differs from independent facts");
  }
  if (report.value("sid").toString() != expected.sid ||
      report.value("session").toInteger(-1) != expected.session ||
      report.value("integrity_rid").toInteger(-1) != expected.integrity ||
      report.value("auth_luid").toString() != expected.auth_luid ||
      report.value("elevation_type").toString() != expected.elevation) return fail("actual token evidence mismatch");
  QList<Expected> wrong;
  auto mismatch = expected; mismatch.sid = expected.sid == "S-1-5-18" ? "S-1-5-19" : "S-1-5-18"; wrong << mismatch;
  mismatch = expected; mismatch.session ^= 1u; wrong << mismatch;
  mismatch = expected; mismatch.integrity ^= 1u; wrong << mismatch;
  mismatch = expected; mismatch.auth_luid[mismatch.auth_luid.size() - 1] = mismatch.auth_luid.endsWith('0') ? '1' : '0'; wrong << mismatch;
  mismatch = expected; mismatch.elevation = expected.elevation == "default" ? "full" : "default"; wrong << mismatch;
  for (const auto& incorrect : wrong) {
    reason.clear();
    if (checkIdentity(incorrect, report, reason) || reason != "identity_attribute_mismatch") {
      return fail("an independently constructed wrong token attribute was accepted");
    }
  }
  if (report.value("restricting_sid_count").toInteger(-1) != actual_count) return fail("observed count mismatch");
  for (const auto type : {WinLocalSystemSid, WinLocalServiceSid, WinNetworkServiceSid}) {
    alignas(DWORD) BYTE service_sid[SECURITY_MAX_SID_SIZE];
    DWORD sid_size = sizeof(service_sid);
    bool forbidden = false;
    if (!CreateWellKnownSid(type, nullptr, service_sid, &sid_size) ||
        !forbiddenServiceIdentity(service_sid, forbidden) || !forbidden) return fail("service SID classification");
  }
  alignas(DWORD) BYTE world_sid[SECURITY_MAX_SID_SIZE];
  DWORD world_size = sizeof(world_sid);
  if (!CreateWellKnownSid(WinWorldSid, nullptr, world_sid, &world_size)) return fail("create test SID");
  SID_AND_ATTRIBUTES restriction{world_sid, 0};
  HANDLE restricted_raw = nullptr;
  if (!CreateRestrictedToken(token.get(), 0, 0, nullptr, 0, nullptr, 1, &restriction, &restricted_raw)) {
    return skip("restricted-token handle unavailable");
  }
  Handle restricted(restricted_raw);
  DWORD restricted_count = 0;
  std::size_t restricted_size = 0;
  if (!restrictingSidCount(restricted.get(), restricted_count, &restricted_size) || restricted_count == 0 ||
      marker_probe::permitsRestrictingSidCount(restricted_count)) return fail("restricting SID list was not detected");
  std::fprintf(stdout, "Restricted test token ReturnLength=%zu, GroupCount=%lu\n", restricted_size,
               static_cast<unsigned long>(restricted_count));
  if (!eligible) return skip("actual process token is ineligible for positive identity check");
  return 0;
}

// Verify the actual QtCore module against both its observed path and an intentionally different path.
int qtCase() {
  HMODULE qt = GetModuleHandleW(L"Qt6Core.dll");
  if (!qt) return fail("QtCore is not loaded");
  std::vector<wchar_t> path(32768);
  const DWORD size = GetModuleFileNameW(qt, path.data(), static_cast<DWORD>(path.size()));
  if (size == 0 || size >= path.size()) return fail("QtCore module path unavailable");
  Expected expected;
  expected.qt_core = QDir::fromNativeSeparators(QString::fromWCharArray(path.data(), size));
  QJsonObject report;
  QString reason;
  if (!checkQt(expected, report, reason)) return fail("actual QtCore path/version not accepted");
  expected.qt_core = QDir(QFileInfo(expected.qt_core).absolutePath()).filePath("nonexistent-test-path/Qt6Core.dll");
  if (checkQt(expected, report, reason) || reason != "qt_version_or_module_mismatch") return fail("Qt path mismatch");
  return 0;
}

struct ProbeRun {
  int exit_code = -1;
  QJsonObject json;
};

// Capture the real executable's complete single-object output and native exit status.
bool runProductionProbe(const QStringList& arguments, ProbeRun& result) {
  QProcess process;
  process.start(QDir(QCoreApplication::applicationDirPath()).filePath("native_app_marker_probe.exe"), arguments);
  if (!process.waitForStarted(5000) || !process.waitForFinished(10000) || process.exitStatus() != QProcess::NormalExit) {
    return false;
  }
  const QByteArray output = process.readAllStandardOutput();
  const QByteArray error_output = process.readAllStandardError();
  std::fprintf(stdout, "production probe exit=%d stdout:\n", process.exitCode());
  if (output.size() <= 1024 * 1024) std::fwrite(output.constData(), 1, static_cast<size_t>(output.size()), stdout);
  else std::fprintf(stderr, "production probe output exceeds limit\n");
  if (!error_output.isEmpty()) std::fwrite(error_output.constData(), 1, static_cast<size_t>(error_output.size()), stderr);
  if (output.size() > 1024 * 1024 || !output.endsWith('\n')) return false;
  QJsonParseError error{};
  const QJsonDocument document = QJsonDocument::fromJson(output, &error);
  if (error.error != QJsonParseError::NoError || !document.isObject()) return false;
  result.exit_code = process.exitCode();
  result.json = document.object();
  return result.json.value("schema").toString() == "pj-native-app-marker-probe/v1" &&
         result.json.value("exit_code").toInt(-1) == result.exit_code;
}

// CLI arguments come from independently queried process facts, never from probe output.
QStringList expectedArguments(const Expected& expected) {
  return {"--expect-sid", expected.sid, "--expect-session", QString::number(expected.session),
          "--expect-integrity-rid", QString::number(expected.integrity), "--expect-auth-luid", expected.auth_luid,
          "--expect-elevation-type", expected.elevation, "--expect-qt-core", expected.qt_core};
}

// The actual default path is checked only read-only by the production executable.
int cliCase() {
  ProbeRun invalid;
  if (!runProductionProbe({}, invalid) || invalid.exit_code != 2 || invalid.json.value("ok").toBool(true) ||
      invalid.json.value("reason").toString() != "invalid_arguments" ||
      !invalid.json.value("marker_directory").isNull()) return fail("production invalid-argument response");
  HANDLE raw = nullptr;
  if (!OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &raw)) return fail("open token for production CLI");
  Handle token(raw);
  Expected expected;
  if (!expectedFromToken(token.get(), expected)) return fail("query expected production CLI identity");
  HMODULE qt = GetModuleHandleW(L"Qt6Core.dll");
  std::vector<wchar_t> qt_path(32768);
  const DWORD size = qt ? GetModuleFileNameW(qt, qt_path.data(), static_cast<DWORD>(qt_path.size())) : 0;
  if (size == 0 || size >= qt_path.size()) return fail("production CLI QtCore path");
  expected.qt_core = QDir::fromNativeSeparators(QString::fromWCharArray(qt_path.data(), size));
  Expected wrong = expected;
  wrong.session ^= 1u;
  ProbeRun mismatch;
  if (!runProductionProbe(expectedArguments(wrong), mismatch) || mismatch.exit_code != 4 ||
      mismatch.json.value("ok").toBool(true) || mismatch.json.value("reason").toString() != "identity_attribute_mismatch" ||
      !mismatch.json.value("marker_directory").isNull() || !mismatch.json.value("marker_directory_exists").isNull() ||
      !mismatch.json.value("marker_enumeration_ok").isNull() || !mismatch.json.value("matching_marker_count").isNull() ||
      !mismatch.json.value("process_enumeration_ok").isNull()) return fail("production identity mismatch response");
  bool eligible = false, impersonating = false;
  DWORD count = 0;
  if (!expectedEligibility(token.get(), expected, eligible, impersonating, count)) return fail("production CLI eligibility");
  if (!eligible || impersonating) return skip("current token is not eligible for the production CLI positive check");
  ProbeRun positive;
  if (!runProductionProbe(expectedArguments(expected), positive)) return fail("production positive probe execution or JSON");
  if (positive.exit_code == 6 || positive.exit_code == 7 || positive.exit_code == 8) {
    return skip("real default path or process snapshot is not clean and verifiable");
  }
  const QJsonObject actual_token = positive.json.value("token").toObject();
  const QJsonObject actual_qt = positive.json.value("qt").toObject();
  const QString actual_directory = QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation);
  if (positive.exit_code != 0 || !positive.json.value("ok").toBool() ||
      positive.json.value("platform").toString() != "windows" || positive.json.value("reason").toString() != "clean_snapshot" ||
      positive.json.value("probe_pid").toInteger(-1) <= 0 ||
      !QDateTime::fromString(positive.json.value("checked_at_utc").toString(), Qt::ISODateWithMs).isValid() ||
      !QDateTime::fromString(positive.json.value("completed_at_utc").toString(), Qt::ISODateWithMs).isValid() ||
      !positive.json.value("marker_directory_exists").isBool() ||
      !positive.json.value("marker_enumeration_ok").toBool() || positive.json.value("matching_marker_count").toInt(-1) != 0 ||
      !positive.json.value("process_enumeration_ok").toBool() || positive.json.value("other_app_process_count").toInt(-1) != 0 ||
      positive.json.value("marker_directory").toString() != actual_directory || actual_directory.isEmpty() ||
      actual_token.value("sid").toString() != expected.sid || actual_token.value("session").toInteger(-1) != expected.session ||
      actual_token.value("process_session").toInteger(-1) != expected.session ||
      actual_token.value("integrity_rid").toInteger(-1) != expected.integrity ||
      actual_token.value("auth_luid").toString() != expected.auth_luid ||
      actual_token.value("elevation_type").toString() != expected.elevation ||
      actual_token.value("restricting_sid_count").toInt(-1) != 0 ||
      !actual_token.value("app_container").isBool() || actual_token.value("app_container").toBool(true) ||
      actual_qt.value("core_module_path").toString().compare(expected.qt_core, Qt::CaseInsensitive) != 0 ||
      actual_qt.value("runtime_version").toString() != QStringLiteral(PROBE_QT_VERSION) ||
      actual_qt.value("compiled_version").toString() != QStringLiteral(PROBE_QT_VERSION)) {
    return fail("production positive evidence mismatch");
  }
  return 0;
}

// All paths come from this process's newly created root and fixed child names, never a caller argument.
struct OwnedFixture {
  QTemporaryDir root{QDir::tempPath() + "/pj_marker_probe_XXXXXX"};
  QString pending_junction;
  QString child(const char* name) const { return QDir(root.path()).filePath(QString::fromLatin1(name)); }
  ~OwnedFixture() {
    if (pending_junction.isEmpty()) return;
    const std::wstring path = QDir::toNativeSeparators(pending_junction).toStdWString();
    const DWORD attributes = GetFileAttributesW(path.c_str());
    if (attributes == INVALID_FILE_ATTRIBUTES || !RemoveDirectoryW(path.c_str())) {
      root.setAutoRemove(false);
      std::fprintf(stderr, "Owned fixture retained after cleanup failure: %s\n", qPrintable(root.path()));
    }
  }
};

QString injected_denial;
HANDLE WINAPI mockOpenDirectory(LPCWSTR path, DWORD access, DWORD sharing, LPSECURITY_ATTRIBUTES security,
                                DWORD disposition, DWORD flags, HANDLE template_file) {
  if (QString::fromWCharArray(path).compare(injected_denial, Qt::CaseInsensitive) == 0) {
    SetLastError(ERROR_ACCESS_DENIED);
    return INVALID_HANDLE_VALUE;
  }
  return CreateFileW(path, access, sharing, security, disposition, flags, template_file);
}

// This header matches the mount-point reparse payload accepted by FSCTL_SET_REPARSE_POINT.
struct MountPointBuffer {
  DWORD tag;
  WORD data_length;
  WORD reserved;
  WORD substitute_offset;
  WORD substitute_length;
  WORD print_offset;
  WORD print_length;
  wchar_t path_buffer[1];
};

// Create a junction only at a child of the owned root, targeting another child of that same root.
bool createOwnedJunction(const QString& link, const QString& target) {
  const std::wstring native_link = QDir::toNativeSeparators(link).toStdWString();
  const std::wstring native_target = QDir::toNativeSeparators(target).toStdWString();
  const std::wstring substitute = L"\\??\\" + native_target;
  const size_t path_bytes = (substitute.size() + native_target.size() + 2) * sizeof(wchar_t);
  if (path_bytes + 8 > std::numeric_limits<WORD>::max()) { SetLastError(ERROR_BUFFER_OVERFLOW); return false; }
  std::vector<unsigned char> bytes(offsetof(MountPointBuffer, path_buffer) + path_bytes, 0);
  auto* data = reinterpret_cast<MountPointBuffer*>(bytes.data());
  data->tag = IO_REPARSE_TAG_MOUNT_POINT;
  data->data_length = static_cast<WORD>(8 + path_bytes);
  data->substitute_offset = 0;
  data->substitute_length = static_cast<WORD>(substitute.size() * sizeof(wchar_t));
  data->print_offset = static_cast<WORD>((substitute.size() + 1) * sizeof(wchar_t));
  data->print_length = static_cast<WORD>(native_target.size() * sizeof(wchar_t));
  std::memcpy(data->path_buffer, substitute.c_str(), (substitute.size() + 1) * sizeof(wchar_t));
  std::memcpy(reinterpret_cast<unsigned char*>(data->path_buffer) + data->print_offset,
              native_target.c_str(), (native_target.size() + 1) * sizeof(wchar_t));
  Handle link_handle(CreateFileW(native_link.c_str(), GENERIC_WRITE,
                                FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, nullptr, OPEN_EXISTING,
                                FILE_FLAG_OPEN_REPARSE_POINT | FILE_FLAG_BACKUP_SEMANTICS, nullptr));
  if (link_handle.get() == INVALID_HANDLE_VALUE) return false;
  DWORD returned = 0;
  return DeviceIoControl(link_handle.get(), FSCTL_SET_REPARSE_POINT, bytes.data(), static_cast<DWORD>(bytes.size()),
                         nullptr, 0, &returned, nullptr) != FALSE;
}

// If cleanup is uncertain, retain the owned root rather than traversing a junction.
bool removeOwnedJunction(OwnedFixture& fixture, const QString& link) {
  const std::wstring path = QDir::toNativeSeparators(link).toStdWString();
  const DWORD attributes = GetFileAttributesW(path.c_str());
  if (attributes == INVALID_FILE_ATTRIBUTES || !RemoveDirectoryW(path.c_str())) {
    fixture.root.setAutoRemove(false);
    fixture.pending_junction.clear();
    std::fprintf(stderr, "Owned fixture retained after cleanup failure: %s\n", qPrintable(fixture.root.path()));
    return false;
  }
  fixture.pending_junction.clear();
  return true;
}

// Exercise production path scanning against only this test's owned objects.
int markerPathsCase() {
  OwnedFixture fixture;
  if (!fixture.root.isValid()) return fail("owned temporary root");
  bool exists = true;
  qint64 count = 0;
  QString reason;
  if (!scanMarkerDirectory(fixture.child("absent"), exists, count, reason) || exists || count != 0) {
    return fail("absent path");
  }
  if (!QDir().mkdir(fixture.child("records"))) return fail("create records fixture");
  QFile marker(QDir(fixture.child("records")).filePath("active_widgets.123.json"));
  if (!marker.open(QIODevice::WriteOnly | QIODevice::NewOnly)) return fail("create owned marker");
  marker.close();
  const std::wstring marker_path = QDir::toNativeSeparators(marker.fileName()).toStdWString();
  if (!SetFileAttributesW(marker_path.c_str(), FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM)) return fail("set fixture attributes");
  exists = false; count = 0; reason.clear();
  const bool enumerated = scanMarkerDirectory(fixture.child("records"), exists, count, reason);
  const bool attributes_restored = SetFileAttributesW(marker_path.c_str(), FILE_ATTRIBUTE_NORMAL) != FALSE;
  if (!attributes_restored || !enumerated || !exists || count != 1) return fail("hidden/system marker metadata");
  QFile plain(fixture.child("ordinary_file"));
  if (!plain.open(QIODevice::WriteOnly | QIODevice::NewOnly)) return fail("create owned non-directory");
  plain.close();
  exists = false; count = 0; reason.clear();
  if (scanMarkerDirectory(fixture.child("ordinary_file"), exists, count, reason)) return fail("non-directory accepted");
  if (!QDir().mkdir(fixture.child("mock_denied"))) return fail("create mock denial target");
  injected_denial = QDir::toNativeSeparators(fixture.child("mock_denied"));
  exists = false; count = 0; reason.clear();
  const bool mock_accepted = scanMarkerDirectory(fixture.child("mock_denied"), exists, count, reason, mockOpenDirectory);
  injected_denial.clear();
  if (mock_accepted || reason != "directory_open_failed:5") return fail("mock ACCESS_DENIED not rejected");
  if (!QDir().mkdir(fixture.child("junction_target")) || !QDir().mkdir(fixture.child("junction"))) {
    return fail("create owned junction directories");
  }
  fixture.pending_junction = fixture.child("junction");
  const bool made = createOwnedJunction(fixture.child("junction"), fixture.child("junction_target"));
  const DWORD creation_error = GetLastError();
  if (!made) {
    if (!removeOwnedJunction(fixture, fixture.child("junction"))) return fail("junction cleanup");
    SetLastError(creation_error);
    return skip("owned junction creation unavailable");
  }
  exists = false; count = 0; reason.clear();
  const bool reparse_accepted = scanMarkerDirectory(fixture.child("junction"), exists, count, reason);
  const bool removed = removeOwnedJunction(fixture, fixture.child("junction"));
  if (!removed || reparse_accepted || reason != "non_directory_or_reparse") return fail("junction not rejected");
  return 0;
}

// The denied directory's DACL is set only at creation inside our own disposable root.
int accessDeniedCase() {
  OwnedFixture fixture;
  if (!fixture.root.isValid()) return fail("owned temporary root");
  HANDLE raw = nullptr;
  if (!OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &raw)) return fail("open token for owned DACL");
  Handle token(raw);
  std::vector<unsigned char> user;
  if (!tokenInfo(token.get(), TokenUser, user)) return fail("query DACL principal");
  const auto* token_user = reinterpret_cast<const TOKEN_USER*>(user.data());
  LPWSTR sid = nullptr;
  if (!IsValidSid(token_user->User.Sid) || !ConvertSidToStringSidW(token_user->User.Sid, &sid)) return fail("DACL SID");
  const QString sddl = QStringLiteral("D:P(D;;0x00000080;;;%1)(A;;0x001F01FF;;;%1)").arg(QString::fromWCharArray(sid));
  LocalFree(sid);
  PSECURITY_DESCRIPTOR descriptor = nullptr;
  const std::wstring native_sddl = sddl.toStdWString();
  if (!ConvertStringSecurityDescriptorToSecurityDescriptorW(native_sddl.c_str(), SDDL_REVISION_1, &descriptor, nullptr)) {
    return fail("create owned security descriptor");
  }
  SECURITY_ATTRIBUTES attributes{sizeof(attributes), descriptor, FALSE};
  const std::wstring path = QDir::toNativeSeparators(fixture.child("acl_denied")).toStdWString();
  const bool created = CreateDirectoryW(path.c_str(), &attributes) != FALSE;
  const DWORD creation_error = GetLastError();
  LocalFree(descriptor);
  if (!created) { SetLastError(creation_error); return fail("create owned ACL fixture"); }
  HANDLE raw_directory = CreateFileW(path.c_str(), FILE_READ_ATTRIBUTES, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                                     nullptr, OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, nullptr);
  const DWORD open_error = GetLastError();
  if (raw_directory != INVALID_HANDLE_VALUE) CloseHandle(raw_directory);
  bool exists = false;
  qint64 count = 0;
  QString reason;
  const bool accepted = scanMarkerDirectory(fixture.child("acl_denied"), exists, count, reason);
  const bool removed = RemoveDirectoryW(path.c_str()) != FALSE;
  if (!removed) {
    fixture.root.setAutoRemove(false);
    std::fprintf(stderr, "Owned fixture retained after cleanup failure: %s\n", qPrintable(fixture.root.path()));
    return fail("remove owned ACL fixture");
  }
  if (raw_directory != INVALID_HANDLE_VALUE) return skip("current token bypasses owned access-denial fixture");
  if (open_error != ERROR_ACCESS_DENIED || accepted || reason != "directory_open_failed:5") {
    return fail("real ACCESS_DENIED not rejected");
  }
  return 0;
}

DWORD injected_process_pid = 0;
BOOL WINAPI failProcessEnumerationAfterMatch(HANDLE snapshot, LPPROCESSENTRY32W entry) {
  if (entry->th32ProcessID == injected_process_pid) {
    SetLastError(ERROR_ACCESS_DENIED);
    return FALSE;
  }
  return Process32NextW(snapshot, entry);
}

// Start only the benign test executable; it exits on stdin EOF and never launches PlotJuggler.
int processesCase() {
  qint64 baseline = 0;
  QString reason;
  if (!scanProcesses(baseline, reason)) return fail("initial process snapshot");
  if (baseline != 0) return skip("another candidate process already exists");
  QProcess child;
  child.start(QDir(QCoreApplication::applicationDirPath()).filePath("plotjuggler_marker_test_fixture.exe"), {});
  if (!child.waitForStarted(5000)) return fail("start owned process fixture");
  QElapsedTimer timer;
  timer.start();
  bool found = false;
  bool scan_success = false;
  while (timer.elapsed() < 3000) {
    qint64 count = 0;
    scan_success = scanProcesses(count, reason, static_cast<DWORD>(child.processId()), &found);
    if (!scan_success) break;
    if (found) break;
    QThread::msleep(25);
  }
  bool injected_rejected = false;
  if (scan_success && found) {
    injected_process_pid = static_cast<DWORD>(child.processId());
    qint64 partial_count = 0;
    bool partial_found = false;
    reason.clear();
    const bool partial_success = scanProcesses(partial_count, reason, injected_process_pid, &partial_found,
                                               failProcessEnumerationAfterMatch);
    injected_rejected = !partial_success && partial_found && reason == "process_enumeration_failed";
    injected_process_pid = 0;
  }
  child.closeWriteChannel();
  const bool ended = child.waitForFinished(5000) && child.exitStatus() == QProcess::NormalExit && child.exitCode() == 0;
  if (!ended || !scan_success || !found || !injected_rejected) {
    return fail("owned process detection or post-match enumeration failure check");
  }
  return 0;
}
}  // namespace

int main(int argc, char** argv) {
  QCoreApplication app(argc, argv);
  QCoreApplication::setOrganizationName(QStringLiteral("PlotJuggler"));
  QCoreApplication::setApplicationName(QStringLiteral("PlotJuggler4"));
  const QStringList args = app.arguments();
  if (args.size() != 2) return fail("one fixed case name is required");
  if (args[1] == "identity") return identityCase();
  if (args[1] == "qt") return qtCase();
  if (args[1] == "cli") return cliCase();
  if (args[1] == "marker_paths") return markerPathsCase();
  if (args[1] == "access_denied") return accessDeniedCase();
  if (args[1] == "processes") return processesCase();
  return fail("unknown case");
}
