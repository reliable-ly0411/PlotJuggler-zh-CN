// SPDX-License-Identifier: MPL-2.0
#include "app_settings.h"
#include <QApplication>
#include <QDebug>
#include <QDir>
#include <QSettings>

bool configureApplicationSettings(const QApplication& app)
{
  QCoreApplication::setOrganizationName("PlotJuggler");
  QCoreApplication::setApplicationName("io.plotjuggler.PlotJuggler.zh-CN");
  QSettings::setDefaultFormat(QSettings::IniFormat);
  const auto arguments = app.arguments();
  QString directory;
  bool explicit_directory = false;
  for (int i = 1; i < arguments.size(); ++i)
  {
    if (arguments[i] == "--") break;
    if (arguments[i].startsWith("--config-dir="))
    {
      explicit_directory = true;
      directory = arguments[i].mid(13);
    }
    else if (arguments[i] == "--config-dir")
    {
      explicit_directory = true;
      if (i + 1 >= arguments.size() || arguments[i + 1].startsWith("--"))
      {
        qCritical() << "--config-dir requires a directory";
        return false;
      }
      directory = arguments[++i];
    }
  }
  if (explicit_directory && directory.isEmpty())
  {
    qCritical() << "--config-dir requires a non-empty directory";
    return false;
  }
  if (directory.isEmpty())
  {
    const int test = arguments.indexOf("--self-test-ui");
    if (test >= 0 && test + 1 < arguments.size()) directory = arguments[test + 1] + "/settings";
  }
  if (!directory.isEmpty())
    QSettings::setPath(QSettings::IniFormat, QSettings::UserScope,
                       QDir(directory).absolutePath());
  return true;
}
