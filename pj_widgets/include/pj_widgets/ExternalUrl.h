// SPDX-License-Identifier: MPL-2.0
#pragma once

#include <QDesktopServices>
#include <QUrl>

#if defined(Q_OS_LINUX) && QT_CONFIG(process)
#include <QProcess>
#include <QProcessEnvironment>

namespace PJ::external_url_detail {

// Restore the exact pre-AppRun environment in a child-only copy. An incomplete
// snapshot must not silently hand bundled libraries to a system application.
inline bool restoreHostEnvironment(QProcessEnvironment& environment) {
  constexpr const char* names[] = {
      "LD_LIBRARY_PATH", "QT_PLUGIN_PATH", "XDG_DATA_DIRS", "PYTHONHOME", "GRPC_DEFAULT_SSL_ROOTS_FILE_PATH",
      "QT_IM_MODULE"};
  for (const char* name : names) {
    const auto key = QString::fromLatin1(name);
    const auto saved = QStringLiteral("PJ_APPIMAGE_HOST_") + key;
    const auto flag = saved + QStringLiteral("_SET");
    const auto state = environment.value(flag);
    if (state == QStringLiteral("1") && environment.contains(saved)) {
      environment.insert(key, environment.value(saved));
    } else if (state == QStringLiteral("0")) {
      environment.remove(key);
    } else {
      return false;
    }
    environment.remove(saved);
    environment.remove(flag);
  }
  environment.remove(QStringLiteral("PJ_APPIMAGE_HOST_ENV"));
  return true;
}

}  // namespace PJ::external_url_detail
#endif

namespace PJ {

// Keep default URL handling outside AppImage HTTP(S), including custom schemes.
// A successful return means the desktop opener started, not that navigation
// completed. No process-global environment is changed around a browser launch.
inline bool openExternalUrl(const QUrl& url) {
#if defined(Q_OS_LINUX) && QT_CONFIG(process)
  auto environment = QProcessEnvironment::systemEnvironment();
  if (environment.value(QStringLiteral("PJ_APPIMAGE_HOST_ENV")) == QStringLiteral("1") &&
      (url.scheme() == QStringLiteral("http") || url.scheme() == QStringLiteral("https"))) {
    if (!url.isValid() || !external_url_detail::restoreHostEnvironment(environment)) {
      return false;
    }
    QProcess opener;
    opener.setProcessEnvironment(environment);
    opener.setProgram(QStringLiteral("xdg-open"));
    opener.setArguments({url.toString(QUrl::FullyEncoded)});
    return opener.startDetached();
  }
#endif
  return QDesktopServices::openUrl(url);
}

}  // namespace PJ
