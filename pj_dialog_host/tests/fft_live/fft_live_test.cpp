// SPDX-License-Identifier: MPL-2.0
// Focused ABI/UI acceptance, not a replacement for a full MainWindow smoke test.
// The official plugin and its embedded UI are unmodified. The host uses the
// production UI loader, translation boundary and preview charts, with only the
// FFT subset of widget-data application below (no AppSession/plotting backend).
#include <QTest>
#ifndef Q_MOC_RUN
#include <QAbstractButton>
#include <QApplication>
#include <QBuffer>
#include <QComboBox>
#include <QDir>
#include <QLabel>
#include <QLineEdit>
#include <QMenu>
#include <QSettings>
#include <QSplitter>
#include <QTemporaryDir>
#include <QVBoxLayout>
#include <cmath>
#include <memory>
#include <numbers>

#include "AppLanguage.h"
#include "chart_placeholder_overlay.hpp"
#include "pj_plugins/host/dialog_handle.hpp"
#include "pj_plugins/host/service_registry_builder.hpp"
#include "pj_plugins/host/toolbox_library.hpp"
#include "pj_plugins/host/widget_data_view.hpp"
#include "pj_plugins/host/widget_event_builder.hpp"
#include "pj_plugins/host_qt/bundled_translations.hpp"
#include "pj_plugins/host_qt/chart_preview_widget.hpp"
#include "pj_plugins/host_qt/pj_ui_loader.hpp"
#if defined(__GNUC__)
#pragma GCC diagnostic push
// SDK 0.34.1's test helper omits the optional trailing runtime slot.
#pragma GCC diagnostic ignored "-Wmissing-field-initializers"
#endif
#include "pj_plugins/testing/toolbox_test_store.hpp"
#if defined(__GNUC__)
#pragma GCC diagnostic pop
#endif
#include "pj_widgets/BundledPluginText.h"
#endif

using namespace Qt::StringLiterals;

namespace {
void applyFftData(QWidget& root, const PJ::WidgetDataView& view) {
  for (auto* widget : root.findChildren<QWidget*>()) {
    const auto name = widget->objectName().toStdString();
    if (auto value = view.enabled(name)) {
      widget->setEnabled(*value);
    }
    if (auto* label = qobject_cast<QLabel*>(widget)) {
      if (auto value = view.text(name)) {
        label->setText(PJ::bundledDisplayText(
            label, "text", QString::fromStdString(*value), [&](const char* control) { return view.enabled(control); }));
      }
    } else if (auto* edit = qobject_cast<QLineEdit*>(widget)) {
      if (auto value = view.text(name)) {
        edit->setText(QString::fromStdString(*value));
      }
    } else if (auto* button = qobject_cast<QAbstractButton*>(widget)) {
      if (auto value = view.checked(name)) {
        button->setChecked(*value);
      }
    } else if (auto* combo = qobject_cast<QComboBox*>(widget)) {
      if (auto items = view.items(name)) {
        combo->clear();
        for (const auto& item : *items) {
          const auto source = QString::fromStdString(item);
          combo->addItem(PJ::bundledDisplayText(combo, "text", source));
          combo->setItemData(combo->count() - 1, source, PJ::kCanonicalComboTextRole);
        }
      }
      if (auto index = view.currentIndex(name)) {
        combo->setCurrentIndex(*index);
      }
    }
  }
  for (const auto* name : {"chart_input", "chart_fft"}) {
    auto* frame = root.findChild<QWidget*>(QString::fromLatin1(name));
    if (!frame) {
      continue;
    }
    auto* chart = frame->findChild<PJ::ChartPreviewWidget*>();
    if (!chart) {
      auto* layout = new QVBoxLayout(frame);
      layout->setContentsMargins(0, 0, 0, 0);
      chart = new PJ::ChartPreviewWidget(frame);
      layout->addWidget(chart);
      new PJ::ChartPlaceholderOverlay(frame);
    }
    std::vector<PJ::ChartPreviewWidget::Series> series;
    if (auto incoming = view.chartSeries(name)) {
      for (const auto& item : *incoming) {
        series.push_back({item.label, item.points, item.color});
      }
    }
    chart->setSeries(series);
    auto* overlay = frame->findChild<PJ::ChartPlaceholderOverlay*>();
    if (auto message = view.chartPlaceholder(name)) {
      overlay->setMessage(PJ::bundledDisplayText(frame, "chartPlaceholder", QString::fromStdString(*message)));
    }
    overlay->setVisible(series.empty());
  }
}

QString labelText(QWidget& root, const char* name) {
  auto* label = root.findChild<QLabel*>(QString::fromLatin1(name));
  return label ? label->text() : QString{};
}
}  // namespace

class FftLiveTest : public QObject {
  Q_OBJECT
 private slots:
  void officialBinary_data();
  void officialBinary();
};

void FftLiveTest::officialBinary_data() {
  QTest::addColumn<QString>("language");
  for (const auto& language : {u"zh_CN"_s, u"zh_TW"_s, u"en_US"_s}) {
    QTest::newRow(qPrintable(language)) << language;
  }
}

void FftLiveTest::officialBinary() {
  QFETCH(QString, language);
  PJ::AppLanguage translator(*qApp, language);
  auto library = PJ::ToolboxLibrary::load(PJ_FFT_TEST_PLUGIN);
  QVERIFY2(library.has_value(), library ? "" : library.error().c_str());
  auto handle = library->createHandle();
  PJ::testing::ToolboxTestStore store;
  PJ::ServiceRegistryBuilder registry;
  std::vector<int64_t> timestamps(128);
  std::vector<double> values(128);
  for (std::size_t i = 0; i < timestamps.size(); ++i) {
    timestamps[i] = static_cast<int64_t>(i) * 1000000;
    values[i] = 2.0 * std::sin(2.0 * std::numbers::pi * 62.5 * static_cast<double>(i) / 1000.0);
  }
  store.addTopic("synthetic").addField("synthetic", "signal", timestamps, values);
  store.addTopic("short").addField("short", "signal", {0, 1000000, 2000000}, {1., 2., 3.});
  auto irregular = timestamps;
  irregular[64] += 500000;
  store.addTopic("irregular").addField("irregular", "signal", irregular, values);
  registry.registerService<PJ::sdk::ToolboxHostService>(store.makeHost());
  registry.registerService<PJ::sdk::ToolboxRuntimeHostService>(store.makeRuntimeHost());
  QVERIFY(handle.bind(registry.view()));
  auto dialog = PJ::DialogHandle::fromBorrowed(handle.getDialog());
  const auto manifest = nlohmann::json::parse(dialog.manifest());
  QCOMPARE(manifest.at("id").get<std::string>(), std::string("toolbox-fft"));
  QCOMPARE(manifest.at("version").get<std::string>(), std::string("1.0.1"));
  QByteArray ui = QByteArray::fromStdString(dialog.ui_content());
  QByteArray scope;
  PJ::localizeBundledUi(ui, &scope);
  QCOMPARE(scope, QByteArray("f7d484492d4b2033fc141c9ea3a9f83e9a976049947ba9dd90079df2d19099c0"));
  QBuffer buffer(&ui);
  QVERIFY(buffer.open(QIODevice::ReadOnly));
  PJ::PjUiLoader loader;
  std::unique_ptr<QWidget> root(loader.load(&buffer));
  QVERIFY2(root != nullptr, qPrintable(loader.errorString()));
  root->resize(1080, 760);
  root->show();
  const bool english = language == u"en_US"_s;
  const auto title = PJ::bundledPluginText("toolbox-fft", "1.0.1", "Fast Fourier Transform");
  QMenu menu;
  auto* action = menu.addAction(title);
  action->setToolTip(PJ::bundledPluginText(
      "toolbox-fft", "1.0.1", QString::fromStdString(manifest.at("description").get<std::string>())));
  QCOMPARE(title == u"Fast Fourier Transform"_s, english);
  QCOMPARE(action->toolTip().startsWith(u"Compute"_s), english);
  QCOMPARE(root->windowTitle(), QCoreApplication::translate("PJ::BundledPlugins", "FFT Toolbox"));

  const auto apply = [&] {
    const PJ::WidgetDataView view(dialog.widget_data());
    applyFftData(*root, view);
    QCoreApplication::processEvents();
  };
  const auto save = [&](const char* phase) {
    const QString evidence = qEnvironmentVariable("PJ_TEST_SCREENSHOT_DIR");
    if (evidence.isEmpty()) {
      return true;
    }
    return QDir().mkpath(evidence) && root->grab().save(evidence + "/fft-" + language + "-" + phase + ".png");
  };
  apply();
  // Match a useful user-adjusted panel size; the bare .ui has no saved splitter
  // state and its empty lower pane would otherwise collapse in this harness.
  root->findChild<QSplitter*>(u"mainSplitter"_s)->setSizes({450, 270});
  QCoreApplication::processEvents();
  QCOMPARE(labelText(*root, "selected_value") == u"No input selected"_s, english);
  QCOMPARE(root->findChild<QLineEdit*>(u"suffix_edit"_s)->text(), u"_FFT"_s);
  const auto* window_combo = root->findChild<QComboBox*>(u"window_combo"_s);
  QVERIFY(window_combo);
  QCOMPARE(PJ::canonicalComboText(window_combo, 0), u"Hann (recommended)"_s);
  QCOMPARE(PJ::canonicalComboText(window_combo, 1), u"Rectangular"_s);
  QVERIFY(save("initial"));

  QVERIFY(dialog.sendEvent("inputFrame", PJ::WidgetEventBuilder::itemsDropped({"synthetic/signal"})));
  QVERIFY(dialog.sendEvent("btn_compute", PJ::WidgetEventBuilder::clicked()));
  const auto computed = nlohmann::json::parse(dialog.widget_data());
  const auto& points = computed.at("chart_fft").at("chart_series").at(0).at("points");
  QCOMPARE(points.size(), std::size_t{65});
  QVERIFY(std::abs(points.at(8).at(0).get<double>() - 62.5) < 1e-12);
  QVERIFY(std::abs(points.at(8).at(1).get<double>() - 2.0) < 1e-6);
  apply();
  QCOMPARE(labelText(*root, "selected_value"), u"synthetic/signal"_s);
  const auto status = labelText(*root, "status_label");
  QCOMPARE(status.startsWith(u"Computed"_s), english);
  for (const auto& value : {"65", "128", "1000.000", "7.812", "Hz"}) {
    QVERIFY(status.contains(QLatin1String(value)));
  }
  QVERIFY(save("computed"));

  QVERIFY(dialog.sendEvent("btn_save", PJ::WidgetEventBuilder::clicked()));
  QCOMPARE(store.writtenRecords().size(), std::size_t{65});
  QCOMPARE(store.notifyDataChangedCalls(), 1);
  const auto& fields = store.writtenRecords().at(8).fields;
  QCOMPARE(fields.size(), std::size_t{2});
  QCOMPARE(fields.at(0).name, std::string("frequency_hz"));
  QCOMPARE(fields.at(1).name, std::string("amplitude"));
  QVERIFY(std::abs(fields.at(0).numeric - 62.5) < 1e-12);
  QVERIFY(std::abs(fields.at(1).numeric - 2.0) < 1e-6);
  apply();
  const auto exported = labelText(*root, "status_label");
  QCOMPARE(exported.startsWith(u"Exported"_s), english);
  for (const auto& text : {"synthetic/signal_FFT", "frequency_hz", "amplitude", "65"}) {
    QVERIFY(exported.contains(QLatin1String(text)));
  }
  QVERIFY(save("exported"));
  std::string config;
  QVERIFY(handle.saveConfig(config));
  const auto saved = nlohmann::json::parse(config);
  QCOMPARE(saved.at("suffix").get<std::string>(), std::string("_FFT"));
  QCOMPARE(saved.at("window").get<std::string>(), std::string("hann"));

  QVERIFY(dialog.sendEvent("inputFrame", PJ::WidgetEventBuilder::itemsDropped({"short/signal"})));
  QVERIFY(dialog.sendEvent("btn_compute", PJ::WidgetEventBuilder::clicked()));
  apply();
  QCOMPARE(labelText(*root, "status_label").startsWith(u"Need at least"_s), english);
  QVERIFY(labelText(*root, "status_label").contains(u"3"_s));
  QVERIFY(save("short-error"));
  QVERIFY(dialog.sendEvent("inputFrame", PJ::WidgetEventBuilder::itemsDropped({"irregular/signal"})));
  QVERIFY(dialog.sendEvent("btn_compute", PJ::WidgetEventBuilder::clicked()));
  apply();
  QCOMPARE(labelText(*root, "status_label").startsWith(u"Error:"_s), english);
  QVERIFY(save("sampling-error"));
}

int main(int argc, char** argv) {
  QApplication app(argc, argv);
  QTemporaryDir profile;
  QSettings::setDefaultFormat(QSettings::IniFormat);
  QSettings::setPath(QSettings::IniFormat, QSettings::UserScope, profile.path());
  QCoreApplication::setOrganizationName(u"PJFftRegression"_s);
  QCoreApplication::setApplicationName(u"Isolated"_s);
  FftLiveTest test;
  return QTest::qExec(&test, argc, argv);
}
#include "fft_live_test.moc"
