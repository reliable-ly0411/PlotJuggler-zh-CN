// SPDX-License-Identifier: MPL-2.0
#include "app_language.h"
#include "app_settings.h"
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
#include <QProcess>
#include <QPushButton>
#include <QSettings>
#include <QScreen>
#include <QTextStream>
#include <QTimer>

class Launcher : public QDialog
{
  Q_OBJECT
public:
  Launcher(QStringList arguments, bool immediate) : arguments_(std::move(arguments)),
                                                   immediate_(immediate)
  {
    setObjectName("PlotJuggler3Launcher");
    setWindowTitle(tr("PlotJuggler 3 launcher"));
    setWindowIcon(QIcon(":/launcher/plotjuggler.svg"));
    auto* layout = new QFormLayout(this);
    auto* version = new QLabel(QStringLiteral("PlotJuggler %1").arg(PJ_FORK_SEMVER), this);
    version->setWordWrap(true);
    layout->addRow(version);
    language_ = new QComboBox(this);
    language_->setObjectName("launcherLanguage");
    language_->addItem(QStringLiteral("English"), "en_US");
    language_->addItem(QString::fromUtf8("简体中文"), "zh_CN");
    language_->addItem(QString::fromUtf8("繁體中文"), "zh_TW");
    language_->setCurrentIndex(language_->findData(qApp->property("interfaceLanguage")));
    layout->addRow(tr("Interface language:"), language_);
    auto* hint = new QLabel(tr("The selected language is saved when you click Start. "
                              "Files and command-line options are passed to PlotJuggler."), this);
    hint->setWordWrap(true);
    layout->addRow(hint);
    auto* buttons = new QDialogButtonBox(QDialogButtonBox::Cancel, this);
    auto* start = buttons->addButton(tr("Start"), QDialogButtonBox::AcceptRole);
    start->setObjectName("launcherStart");
    start->setDefault(true);
    layout->addRow(buttons);
    connect(buttons, &QDialogButtonBox::accepted, this, &Launcher::start);
    connect(buttons, &QDialogButtonBox::rejected, this, &Launcher::reject);
    connect(&process_, &QProcess::started, this, &QWidget::hide);
    connect(&process_, &QProcess::errorOccurred, this, [this](QProcess::ProcessError error) {
      if (error == QProcess::FailedToStart)
        finish(127, tr("Unable to start PlotJuggler:\n%1\n%2").arg(program_, process_.errorString()));
    });
    connect(&process_, QOverload<int, QProcess::ExitStatus>::of(&QProcess::finished), this,
            [this](int code, QProcess::ExitStatus status) {
      if (status == QProcess::CrashExit)
        finish(128, tr("PlotJuggler stopped unexpectedly."));
      else if (code != 0)
        finish(code, tr("PlotJuggler exited with code %1.").arg(code));
      else finish(0, {});
    });
    // Resolve only the bundled sibling, never a different version from PATH.
#ifdef Q_OS_WIN
    program_ = QDir(QCoreApplication::applicationDirPath()).filePath("plotjuggler.exe");
#else
    program_ = QDir(QCoreApplication::applicationDirPath()).filePath("plotjuggler");
#endif
    // Retain the caller's directory so relative -d/-l paths keep their meaning.
    process_.setWorkingDirectory(QDir::currentPath());
    process_.setProcessChannelMode(QProcess::ForwardedChannels);
    const int width = qMin(460, QApplication::primaryScreen()->availableGeometry().width() - 40);
    resize(qMax(280, width), sizeHint().height());
    if (immediate_) QTimer::singleShot(0, this, &Launcher::start);
  }

  void reject() override { qApp->exit(0); }

private:
  void start()
  {
    if (process_.state() != QProcess::NotRunning || completed_) return;
    QStringList child_arguments = arguments_;
    if (!immediate_)
    {
      const QString language = language_->currentData().toString();
      QSettings settings;
      settings.setValue("Preferences::language", language);
      settings.sync();
      if (settings.status() != QSettings::NoError)
      {
        QMessageBox::critical(this, tr("Language"),
                              tr("Unable to save the language preference:\n%1").arg(settings.fileName()));
        return;
      }
      // Insert before '--', if present, so an end-of-options marker is preserved.
      int position = child_arguments.indexOf("--");
      if (position < 0) position = child_arguments.size();
      child_arguments.insert(position, "--language=" + language);
    }
    process_.start(program_, child_arguments);
  }

  void finish(int code, const QString& error)
  {
    if (completed_) return;
    completed_ = true;
    if (!error.isEmpty())
    {
      QTextStream(stderr) << error << '\n';
      if (!immediate_) QMessageBox::critical(this, tr("Launch failed"), error);
    }
    qApp->exit(code);
  }

  QStringList arguments_;
  bool immediate_;
  bool completed_ = false;
  QString program_;
  QComboBox* language_;
  QProcess process_;
};

int main(int argc, char** argv)
{
  QCoreApplication::setAttribute(Qt::AA_EnableHighDpiScaling);
  QCoreApplication::setAttribute(Qt::AA_UseHighDpiPixmaps);
  QApplication app(argc, argv);
  app.setQuitOnLastWindowClosed(false);
  QApplication::setStyle("Fusion");
  if (!configureApplicationSettings(app)) return 2;
  installApplicationLanguage(app);
  QStringList arguments = app.arguments().mid(1);
  if (arguments.contains("--help-launcher"))
  {
    QTextStream(stdout) << "plotjuggler-launcher [--launch] [PlotJuggler options]\n"
                          "--launch: start immediately without saving preferences\n"
                          "--language en_US|zh_CN|zh_TW: session language\n"
                          "--config-dir DIRECTORY: isolated configuration directory\n";
    return 0;
  }
  bool immediate = false;
  for (int i = 0; i < arguments.size() && arguments[i] != "--";)
  {
    if (arguments[i] == "--launch")
    {
      immediate = true;
      arguments.removeAt(i);
    }
    else ++i;
  }
  Launcher launcher(arguments, immediate);
  if (!immediate) launcher.show();
  return app.exec();
}

#include "launcher.moc"
