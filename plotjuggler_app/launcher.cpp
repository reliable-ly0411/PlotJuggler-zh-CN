// SPDX-License-Identifier: MPL-2.0
#include "app_language.h"
#include "app_settings.h"
#include "launcher_acceptance.h"
#include <QApplication>
#include <QComboBox>
#include <QDialog>
#include <QDialogButtonBox>
#include <QDir>
#include <QFileInfo>
#include <QFormLayout>
#include <QIcon>
#include <QLabel>
#include <QMessageBox>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QSaveFile>
#include <QProcess>
#include <QPushButton>
#include <QSettings>
#include <QScreen>
#include <QTextStream>
#include <QTimer>

class Launcher : public QObject
{
  Q_OBJECT
public:
  Launcher(QStringList arguments, bool interactive, QObject* parent = nullptr)
    : QObject(parent), arguments_(std::move(arguments)), interactive_(interactive)
  {
#ifdef Q_OS_WIN
    program_ = QDir(QCoreApplication::applicationDirPath()).filePath("plotjuggler.exe");
#else
    program_ = QDir(QCoreApplication::applicationDirPath()).filePath("plotjuggler");
#endif
    process_.setWorkingDirectory(QDir::currentPath());
    process_.setProcessChannelMode(QProcess::ForwardedChannels);
    connect(&process_, &QProcess::started, this, [this] {
      const QString output = qApp->property("launcherAcceptanceOutput").toString();
      if (!output.isEmpty())
      {
        QSaveFile file(QDir(output).filePath("child-started.json"));
        const auto data = QJsonDocument(QJsonObject{
          {"program", process_.program()}, {"arguments", QJsonArray::fromStringList(process_.arguments())},
          {"cwd", process_.workingDirectory()}, {"platform", QGuiApplication::platformName()},
          {"version", QStringLiteral(PJ_FORK_SEMVER)}}).toJson();
        if (!file.open(QIODevice::WriteOnly) || file.write(data) != data.size() || !file.commit())
        {
          process_.kill();
          qApp->exit(3);
        }
      }
    });
    connect(&process_, &QProcess::errorOccurred, this, [this](QProcess::ProcessError error) {
      if (error == QProcess::FailedToStart)
        finish(127, tr("Unable to start PlotJuggler:\n%1\n%2").arg(program_, process_.errorString()));
    });
    connect(&process_, QOverload<int, QProcess::ExitStatus>::of(&QProcess::finished), this,
            [this](int code, QProcess::ExitStatus status) {
              if (status == QProcess::CrashExit) finish(128, tr("PlotJuggler stopped unexpectedly."));
              else if (code != 0) finish(code, tr("PlotJuggler exited with code %1.").arg(code));
              else finish(0, {});
            });
    QTimer::singleShot(0, this, [this] { process_.start(program_, arguments_); });
  }
private:
  void finish(int code, const QString& error)
  {
    if (completed_) return;
    completed_ = true;
    if (!error.isEmpty())
    {
      QTextStream(stderr) << error << '\n';
      if (interactive_) QMessageBox::critical(nullptr, tr("Launch failed"), error);
    }
    qApp->exit(code);
  }
  QStringList arguments_;
  bool interactive_;
  bool completed_ = false;
  QString program_;
  QProcess process_;
};

int main(int argc, char** argv)
{
  QCoreApplication::setAttribute(Qt::AA_EnableHighDpiScaling);
  QCoreApplication::setAttribute(Qt::AA_UseHighDpiPixmaps);
  QApplication app(argc, argv);
  app.setQuitOnLastWindowClosed(false);
  QApplication::setStyle("Fusion");
  LauncherAcceptance acceptance;
  QStringList arguments;
  if (!parseLauncherAcceptance(app.arguments().mid(1), acceptance, arguments))
  {
    QTextStream(stderr) << "Invalid launcher acceptance arguments or isolation paths\n";
    return 2;
  }
  if (!configureApplicationSettings(app))
  {
    return 2;
  }
  installApplicationLanguage(app);
  const bool interactive = arguments.isEmpty();
  for (int i = 0; i < arguments.size() && arguments[i] != "--";)
  {
    if (arguments[i] == "--help-launcher")
    {
      QTextStream(stdout) << "plotjuggler-launcher [--launch] [PlotJuggler options]\n"
                             "--launch: accepted for compatibility; starts immediately\n"
                             "--language en_US|zh_CN|zh_TW: session language\n"
                             "--config-dir DIRECTORY: isolated configuration directory\n";
      return 0;
    }
    if (arguments[i] == "--launch")
    {
      arguments.removeAt(i);
    }
    else
    {
      ++i;
    }
  }
  if (acceptance.enabled) app.setProperty("launcherAcceptanceOutput", acceptance.output);
  Launcher launcher(arguments, interactive);
  return app.exec();
}

#include "launcher.moc"
