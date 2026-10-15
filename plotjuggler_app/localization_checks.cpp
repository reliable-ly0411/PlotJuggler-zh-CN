// SPDX-License-Identifier: MPL-2.0
// Invoked only by --self-test-ui; no server or browser is contacted.
#include "localization_checks.h"
#include <QMainWindow>
#include <QMenu>
#include <QApplication>
#include <QAction>
#include <QDialog>
#include <QDialogButtonBox>
#include <QPushButton>
#include <QComboBox>
#include <QTableWidget>
#include <QTextBrowser>
#include <QTimer>
#include <QJsonArray>
#include <QRegularExpression>
#include <QUrl>

QJsonObject checkLocalizedUi(QMainWindow* window, const QString& output, bool chinese)
{
  QJsonObject result;
  const QRegularExpression han(QStringLiteral("[\\x{4e00}-\\x{9fff}]"));
  bool tools_ok = true;
  QJsonArray labels;
  for (const auto& id : {"CSV/Parquet Exporter", "Fast Fourier Transform",
                         "Quaternion to RPY", "Reactive Script Editor"})
  {
    auto* action = window->findChild<QAction*>(QString("toolbox:") + id);
    const QString text = action ? action->text() : QString();
    const bool valid = action && action->property("pluginId").toString() == id &&
      (chinese ? (text.contains(id) && han.match(text).hasMatch() &&
                  text.contains(QString::fromUtf8("（"))) : text == id);
    tools_ok = tools_ok && valid; labels.append(text);
  }
  result["toolbox_labels"] = labels;
  result["tools_ok"] = tools_ok;
  for (const auto& name : {"menuTools", "menuHelp"})
  {
    if (auto* menu = window->findChild<QMenu*>(name))
    {
      menu->popup(window->mapToGlobal(QPoint(80, 45)));
      QApplication::processEvents();
      result[QString(name) + "_screenshot"] = menu->grab().save(output + "/" + name + ".png");
      menu->hide();
    }
  }
  auto* report = window->findChild<QAction*>("actionTranslationReport");
  const bool report_ok = report && report->data().toUrl().host() == "github.com" &&
    report->data().toUrl().path() == "/reliable-ly0411/PlotJuggler-zh-CN/issues/new" &&
    (chinese ? han.match(report->text()).hasMatch() : report->text() == "Report a translation issue");
  result["report_action_ok"] = report_ok;
  result["report_url"] = report ? report->data().toUrl().toString() : QString();

  bool about_ok = false;
  QTimer::singleShot(200, window, [&]() {
    auto* dialog = window->findChild<QDialog*>("AboutDialog");
    if (!dialog) return;
    auto* body = dialog->findChild<QTextBrowser*>("bodyTextBrowser");
    auto* buttons = dialog->findChild<QDialogButtonBox*>("buttonBox");
    const QString html = body ? body->toHtml() : QString();
    const QString text = body ? body->toPlainText() : QString();
    auto* close = buttons ? buttons->button(QDialogButtonBox::Close) : nullptr;
    const QString button = close ? close->text() : QString();
    about_ok = html.contains("reliable-ly0411/PlotJuggler-zh-CN/issues/new") &&
      text.contains("Davide Faconti") && text.contains("Built with love") &&
      text.contains(QString::fromUtf8("向汉化项目报告问题")) &&
      (chinese ? button == QString::fromUtf8("关闭") : button == "Close");
    result["about_text"] = text;
    result["close_button"] = button;
    result["about_screenshot"] = dialog->grab().save(output + "/about.png");
    dialog->accept();
  });
  const bool invoked = QMetaObject::invokeMethod(window, "on_actionAbout_triggered", Qt::DirectConnection);
  result["about_ok"] = invoked && about_ok;

  auto* cloud = window->findChild<QAction*>("toolbox:Mosaico Cloud Server");
  bool cloud_ok = cloud;
  if (cloud)
  {
    cloud->trigger();
    QApplication::processEvents();
    QJsonArray headers;
    for (const auto& name : {"mosaicoSequences", "mosaicoTopics"})
    {
      auto* table = window->findChild<QTableWidget*>(name);
      cloud_ok = cloud_ok && table;
      if (!table) continue;
      for (int i = 0; i < table->columnCount(); ++i)
      {
        const QString title = table->horizontalHeaderItem(i)->text();
        headers.append(title);
        cloud_ok = cloud_ok && (chinese ? han.match(title).hasMatch() : !han.match(title).hasMatch());
      }
    }
    QJsonArray presets;
    for (const auto* button : window->findChildren<QPushButton*>())
    {
      if (!button->objectName().startsWith("mosaicoPreset")) continue;
      presets.append(button->text());
      cloud_ok = cloud_ok && (chinese ? han.match(button->text()).hasMatch() : !han.match(button->text()).hasMatch());
    }
    cloud_ok = cloud_ok && presets.size() == 4;
    auto* op = window->findChild<QComboBox*>("mosaicoOperator");
    const bool op_fits = op && op->width() >=
      op->fontMetrics().horizontalAdvance(op->placeholderText()) + 24;
    cloud_ok = cloud_ok && op_fits;
    result["mosaico_operator_fits"] = op_fits;
    result["mosaico_headers"] = headers; result["mosaico_presets"] = presets;
    result["mosaico_screenshot"] = window->grab().save(output + "/mosaico.png");
  }
  result["mosaico_ok"] = cloud_ok;
  result["ok"] = tools_ok && report_ok && about_ok && cloud_ok;
  return result;
}
