// SPDX-License-Identifier: MPL-2.0
// This probe performs read-only identity and Qt temporary-directory checks.
// It must run in the actual interactive test session before CTest discovery.
#include <QByteArray>
#include <QCoreApplication>
#include <QDir>
#include <QFileInfo>
#include <QHash>
#include <QJsonDocument>
#include <QJsonObject>
#include <QString>
#include <QStringList>
#include <QtGlobal>
#include <cstdio>
#include <string>
#include <vector>

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#include <sddl.h>
#endif

namespace {

int fail(const char* message) {
  std::fprintf(stderr, "native-temp-probe: %s\n", message);
  return 1;
}

#ifdef _WIN32
struct ScopedHandle {
  HANDLE handle = nullptr;
  ~ScopedHandle() {
    if (handle != nullptr) {
      CloseHandle(handle);
    }
  }
};

// The token handle remains open while the returned buffer is in use.
bool readToken(HANDLE handle, TOKEN_INFORMATION_CLASS type, std::vector<unsigned char>& data) {
  DWORD size = 0;
  if (GetTokenInformation(handle, type, nullptr, 0, &size) || GetLastError() != ERROR_INSUFFICIENT_BUFFER ||
      size == 0) {
    return false;
  }
  data.resize(size);
  return GetTokenInformation(handle, type, data.data(), size, &size) != 0;
}

// Do not accept a junction or other reparse point in any parent directory.
bool hasReparseAncestor(const QString& path) {
  QString current = QDir::cleanPath(QDir::fromNativeSeparators(path));
  for (int depth = 0; depth < 512; ++depth) {
    const std::wstring native = QDir::toNativeSeparators(current).toStdWString();
    const DWORD attributes = GetFileAttributesW(native.c_str());
    if (attributes == INVALID_FILE_ATTRIBUTES || (attributes & FILE_ATTRIBUTE_REPARSE_POINT) != 0) {
      return true;
    }
    const QString parent = QFileInfo(current).dir().absolutePath();
    if (parent.compare(current, Qt::CaseInsensitive) == 0) {
      return false;
    }
    current = parent;
  }
  return true;
}
#endif

}  // namespace

int main(int argc, char* argv[]) {
  QCoreApplication app(argc, argv);
#ifndef _WIN32
  return fail("Windows token and session verification is unavailable on this platform");
#else
  const QStringList args = app.arguments();
  if (args.size() != 15) {
    return fail(
        "expected --run-root PATH --temp PATH --session ID --sid SID --integrity RID --qt VERSION --qt-core DLL");
  }
  const QStringList allowed{QStringLiteral("--run-root"), QStringLiteral("--temp"),      QStringLiteral("--session"),
                            QStringLiteral("--sid"),      QStringLiteral("--integrity"), QStringLiteral("--qt"),
                            QStringLiteral("--qt-core")};
  QHash<QString, QString> options;
  for (qsizetype i = 1; i < args.size(); i += 2) {
    if (!allowed.contains(args[i]) || options.contains(args[i]) || args[i + 1].isEmpty()) {
      return fail("invalid or duplicate option");
    }
    options.insert(args[i], args[i + 1]);
  }
  bool session_ok = false;
  bool integrity_ok = false;
  const uint expected_session = options.value(QStringLiteral("--session")).toUInt(&session_ok);
  const uint expected_integrity = options.value(QStringLiteral("--integrity")).toUInt(&integrity_ok);
  if (!session_ok || expected_session == 0 || !integrity_ok || expected_integrity == 0 ||
      !QDir::isAbsolutePath(options.value(QStringLiteral("--temp"))) ||
      !QDir::isAbsolutePath(options.value(QStringLiteral("--run-root")))) {
    return fail("invalid expected session, integrity or absolute directory path");
  }
  if (options.value(QStringLiteral("--qt")) != QString::fromLatin1(qVersion())) {
    return fail("Qt runtime version differs from the expected version");
  }
  const HMODULE qt_core = GetModuleHandleW(L"Qt6Core.dll");
  std::vector<wchar_t> module_path(32768);
  const DWORD module_length =
      qt_core == nullptr ? 0 : GetModuleFileNameW(qt_core, module_path.data(), static_cast<DWORD>(module_path.size()));
  if (module_length == 0 || module_length >= static_cast<DWORD>(module_path.size())) {
    return fail("cannot identify the loaded Qt Core module");
  }
  const QFileInfo actual_core(QString::fromWCharArray(module_path.data(), static_cast<qsizetype>(module_length)));
  const QFileInfo expected_core(options.value(QStringLiteral("--qt-core")));
  const QString actual_core_path = actual_core.canonicalFilePath();
  const QString expected_core_path = expected_core.canonicalFilePath();
  if (!QDir::isAbsolutePath(expected_core.filePath()) || !actual_core.isFile() || !expected_core.isFile() ||
      actual_core_path.isEmpty() || expected_core_path.isEmpty() ||
      actual_core_path.compare(expected_core_path, Qt::CaseInsensitive) != 0 ||
      hasReparseAncestor(actual_core.absoluteFilePath()) || hasReparseAncestor(expected_core.absoluteFilePath())) {
    return fail("loaded Qt Core module differs from the expected unlinked file");
  }
  const QString root = QDir::cleanPath(QDir::fromNativeSeparators(options.value(QStringLiteral("--run-root"))));
  if (root.size() < 3 || !root[0].isLetter() || root[1] != u':' || root[2] != u'/') {
    return fail("run root must be an absolute drive path");
  }
  const QFileInfo root_info(root);
  const QFileInfo expected_info(options.value(QStringLiteral("--temp")));
  const QFileInfo actual_info(QDir::tempPath());
  const QString canonical_root = root_info.canonicalFilePath();
  const QString expected_temp = expected_info.canonicalFilePath();
  const QString actual_temp = actual_info.canonicalFilePath();
  const QString required_temp = QDir(canonical_root).filePath(QStringLiteral("tmp"));
  if (!root_info.isDir() || !expected_info.isDir() || !actual_info.isDir() || canonical_root.isEmpty() ||
      expected_temp.isEmpty() || actual_temp.isEmpty() || root.compare(canonical_root, Qt::CaseInsensitive) != 0 ||
      expected_temp.compare(required_temp, Qt::CaseInsensitive) != 0 ||
      expected_temp.compare(actual_temp, Qt::CaseInsensitive) != 0 || hasReparseAncestor(root) ||
      hasReparseAncestor(expected_temp)) {
    return fail("Qt temporary directory is not the existing, unlinked run-root/tmp directory");
  }
  DWORD session = 0;
  if (!ProcessIdToSessionId(GetCurrentProcessId(), &session) || session != expected_session) {
    return fail("process session does not match the expected interactive session");
  }
  ScopedHandle token;
  if (!OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &token.handle)) {
    return fail("cannot open the process token");
  }
  std::vector<unsigned char> user_data;
  std::vector<unsigned char> integrity_data;
  if (!readToken(token.handle, TokenUser, user_data) || !readToken(token.handle, TokenIntegrityLevel, integrity_data)) {
    return fail("cannot read process token identity or integrity");
  }
  const auto* user = reinterpret_cast<const TOKEN_USER*>(user_data.data());
  const auto* integrity = reinterpret_cast<const TOKEN_MANDATORY_LABEL*>(integrity_data.data());
  if (!IsValidSid(user->User.Sid) || !IsValidSid(integrity->Label.Sid)) {
    return fail("invalid token SID");
  }
  LPWSTR sid_text = nullptr;
  if (!ConvertSidToStringSidW(user->User.Sid, &sid_text)) {
    return fail("cannot render process token SID");
  }
  const QString sid = QString::fromWCharArray(sid_text);
  LocalFree(sid_text);
  const UCHAR count = *GetSidSubAuthorityCount(integrity->Label.Sid);
  if (count == 0) {
    return fail("invalid integrity SID");
  }
  const DWORD integrity_rid = *GetSidSubAuthority(integrity->Label.Sid, static_cast<DWORD>(count - 1));
  if (sid == QStringLiteral("S-1-5-18") || sid == QStringLiteral("S-1-5-19") || sid == QStringLiteral("S-1-5-20") ||
      sid.compare(options.value(QStringLiteral("--sid")), Qt::CaseInsensitive) != 0 ||
      integrity_rid != expected_integrity) {
    return fail("process token SID or integrity differs from the expected identity");
  }
  QJsonObject evidence;
  evidence.insert(QStringLiteral("pid"), static_cast<qint64>(GetCurrentProcessId()));
  evidence.insert(QStringLiteral("session"), static_cast<qint64>(session));
  evidence.insert(QStringLiteral("user_sid"), sid);
  evidence.insert(QStringLiteral("integrity_rid"), static_cast<qint64>(integrity_rid));
  evidence.insert(QStringLiteral("qt_version"), QString::fromLatin1(qVersion()));
  evidence.insert(QStringLiteral("qt_core"), actual_core_path);
  evidence.insert(QStringLiteral("run_root"), canonical_root);
  evidence.insert(QStringLiteral("qt_temp"), actual_temp);
  const QByteArray output = QJsonDocument(evidence).toJson(QJsonDocument::Compact) + '\n';
  return std::fwrite(output.constData(), 1, static_cast<size_t>(output.size()), stdout) ==
                 static_cast<size_t>(output.size())
             ? 0
             : fail("cannot write probe evidence");
#endif
}
