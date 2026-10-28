// SPDX-License-Identifier: MPL-2.0
#include <QApplication>
#ifdef PJ_TEST_PRODUCTION_CATALOG
#include "AppLanguage.h"
#endif
#include <QComboBox>
#include <QCryptographicHash>
#include <QDir>
#include <QDomDocument>
#include <QFile>
#include <QFileInfo>
#include <QLabel>
#include <QLineEdit>
#include <QTest>
#include <QTranslator>
#include <pj_plugins/host_qt/bundled_translations.hpp>

class Translation : public QTranslator {
 public:
  QString translate(const char* context, const char* source, const char*, int) const override {
    if (QByteArray(context) != "PJ::BundledPlugins") {
      return {};
    }
    const QByteArray text(source);
    if (text == "Output:") return QStringLiteral("输出：");
    if (text == "e.g. /imu/rpy/") return QStringLiteral("例如 /imu/rpy/");
    if (text == "CSV Loader") {
      return QStringLiteral("CSV 加载器");
    }
    if (text == "Number of Rows") {
      return QStringLiteral("行号");
    }
    if (text == "Values in \"%1\" are not monotonically increasing. Will sort these automatically") {
      return QStringLiteral("“%1”列中的值不是单调递增的，将自动排序");
    }
    if (text == "Transform Editor: %1") {
      return QStringLiteral("变换编辑器：%1");
    }
    if (text == "Transform Editor: created %1 series.") {
      return QStringLiteral("变换编辑器：已创建 %1 条曲线。");
    }
    return {};
  }
  bool isEmpty() const override {
    return false;
  }
};
class BundledTranslationsTest : public QObject {
  Q_OBJECT
 private slots:
  void fftStaticDynamicAndDataBoundaries() {
#ifdef PJ_TEST_PRODUCTION_CATALOG
    QFile file(QFileInfo(QStringLiteral(PJ_CSV_UI_FIXTURE)).dir().filePath(QStringLiteral("fft_1_0_1.ui")));
    QVERIFY(file.open(QIODevice::ReadOnly));
    const auto raw = file.readAll().replace("\r\n", "\n");
    for (const QString& code : {QStringLiteral("zh_CN"), QStringLiteral("zh_TW"), QStringLiteral("en_US")}) {
      PJ::AppLanguage language(*qApp, code);
      QByteArray scope;
      const auto localized = PJ::localizeBundledUi(raw, &scope);
      QCOMPARE(scope, QByteArray("f7d484492d4b2033fc141c9ea3a9f83e9a976049947ba9dd90079df2d19099c0"));
      QDomDocument original, translated;
      QVERIFY(original.setContent(raw));
      QVERIFY(translated.setContent(localized));
      const auto before = original.elementsByTagName(QStringLiteral("string"));
      const auto after = translated.elementsByTagName(QStringLiteral("string"));
      QCOMPARE(before.size(), after.size());
      for (int i = 0; i < before.size(); ++i) {
        const auto value = before.at(i).toElement().text();
        const auto shown = after.at(i).toElement().text();
        if (value.isEmpty() || value == QStringLiteral("_FFT") || value == QStringLiteral("rangeGroup") ||
            code == QStringLiteral("en_US")) {
          QCOMPARE(shown, value);
        } else {
          QVERIFY2(shown != value, qPrintable(value));
        }
      }
      QLabel label;
      label.setProperty(PJ::kBundledUiScope, scope);
      label.setObjectName(QStringLiteral("selected_value"));
      const QString empty = QStringLiteral("No input selected");
      const auto inactive = [](const char*) -> std::optional<bool> { return false; };
      const auto active = [](const char*) -> std::optional<bool> { return true; };
      const auto missing = [](const char*) -> std::optional<bool> { return std::nullopt; };
      QCOMPARE(PJ::bundledDisplayText(&label, "text", empty, active), empty);
      QCOMPARE(PJ::bundledDisplayText(&label, "text", empty, missing), empty);
      QCOMPARE(PJ::bundledDisplayText(&label, "text", empty), empty);
      QCOMPARE(PJ::bundledDisplayText(&label, "text", empty, inactive) == empty, code == QStringLiteral("en_US"));
      label.setObjectName(QStringLiteral("status_label"));
      const QString field = QStringLiteral("用户/使用者 %1 %2 ' <raw>\nNo input selected_FFT");
      const QString status =
          QStringLiteral("Exported '") + field + QStringLiteral("' with frequency_hz and amplitude columns (65 rows)");
      const auto shown = PJ::bundledDisplayText(&label, "text", status);
      QVERIFY(shown.contains(field));
      QVERIFY(shown.contains(QStringLiteral("frequency_hz")) && shown.contains(QStringLiteral("amplitude")));
      QCOMPARE(shown == status, code == QStringLiteral("en_US"));
      const QString numeric =
          QStringLiteral("Computed 65 bins from 128 samples · 1000.000 Hz sample rate · 7.812 Hz resolution");
      const auto numeric_shown = PJ::bundledDisplayText(&label, "text", numeric);
      for (const auto* value : {"65", "128", "1000.000 Hz", "7.812 Hz"}) {
        QVERIFY(numeric_shown.contains(QLatin1String(value)));
      }
      QCOMPARE(numeric_shown == numeric, code == QStringLiteral("en_US"));
      const auto unknown = QStringLiteral("A new upstream status: %1 42.125 Hz");
      QCOMPARE(PJ::bundledDisplayText(&label, "text", unknown), unknown);
      label.setObjectName(QStringLiteral("user_field"));
      QCOMPARE(PJ::bundledDisplayText(&label, "text", status), status);
      QByteArray crlf = raw;
      crlf.replace("\n", "\r\n");
      QCOMPARE(PJ::localizeBundledUi(crlf, &scope), localized);
      QCOMPARE(PJ::localizeBundledUi(raw + "\n", &scope), raw + "\n");
      QVERIFY(scope.isEmpty());
    }
#else
    QSKIP("Production application catalog unavailable");
#endif
  }

  void traditionalCatalogKeepsPinnedUiAndUserDataBoundaries() {
#ifdef PJ_TEST_PRODUCTION_CATALOG
    PJ::AppLanguage language(*qApp, QStringLiteral("zh_TW"));
    QVERIFY(language.catalogLoaded());
    QFile file(QStringLiteral(PJ_CSV_UI_FIXTURE));
    QVERIFY(file.open(QIODevice::ReadOnly));
    const auto raw = file.readAll().replace("\r\n", "\n");
    QByteArray scope;
    const auto localized = PJ::localizeBundledUi(raw, &scope);
    QVERIFY(!scope.isEmpty());
    QVERIFY(localized.contains(QStringLiteral("CSV 載入器").toUtf8()));
    QComboBox combo;
    combo.setObjectName(QStringLiteral("timeAxisModeCombo"));
    combo.setProperty(PJ::kBundledUiScope, scope);
    const QString canonical = QStringLiteral("Number of Rows");
    const QString display = PJ::bundledDisplayText(&combo, "text", canonical);
    QVERIFY(display != canonical);
    combo.addItem(display);
    combo.setItemData(0, canonical, PJ::kCanonicalComboTextRole);
    QCOMPARE(PJ::canonicalComboText(&combo, 0), canonical);
    combo.setEditable(true);
    const QString field = QStringLiteral("使用者 %1 %2 / Number of Rows <raw> / 檔案");
    combo.setEditText(field);
    QCOMPARE(PJ::canonicalComboText(&combo, 0), field);
    QLabel label;
    label.setObjectName(QStringLiteral("labelWarning"));
    label.setProperty(PJ::kBundledUiScope, scope);
    const QString warning = QStringLiteral("Values in \"") + field +
        QStringLiteral("\" are not monotonically increasing. Will sort these automatically");
    const QString translated = PJ::bundledDisplayText(&label, "text", warning);
    QVERIFY(translated != warning);
    QVERIFY(translated.contains(field));
    label.setObjectName(QStringLiteral("userData"));
    QCOMPARE(PJ::bundledDisplayText(&label, "text", warning), warning);
    QCOMPARE(PJ::localizeBundledUi(raw + "\n", &scope), raw + "\n");
    QVERIFY(scope.isEmpty());
#else
    QSKIP("Production application catalog is unavailable when PJ4_BUILD_APP is disabled");
#endif
  }

  void pinnedPlaceholdersUseProductionCatalogWithoutChangingValues() {
#ifdef PJ_TEST_PRODUCTION_CATALOG
    PJ::AppLanguage language(*qApp, QStringLiteral("zh_CN"));
    QVERIFY(language.catalogLoaded());
    const QDir fixtures = QFileInfo(QStringLiteral(PJ_CSV_UI_FIXTURE)).dir();
    struct Case { const char* file; const char* widget; const char* english; const char* chinese; };
    const Case cases[] = {
        {"webrtc_1_0_1.ui", "lineEditManualPath", "e.g. cam0", "例如 cam0"},
        {"json_1_3_0.ui", "lineEditTimestampField", "e.g. timestamp, ts, time", "例如 timestamp, ts, time"},
        {"protobuf_1_2_0.ui", "lineEditTimestampField", "e.g. timestamp, ts, time", "例如 timestamp, ts, time"}};
    for (const auto& item : cases) {
      QFile file(fixtures.filePath(QString::fromLatin1(item.file)));
      QVERIFY(file.open(QIODevice::ReadOnly));
      const auto raw = file.readAll().replace("\r\n", "\n");
      QByteArray scope;
      const auto localized = PJ::localizeBundledUi(raw, &scope);
      QVERIFY(!scope.isEmpty());
      QVERIFY(localized.contains(item.chinese));
      QLineEdit input;
      input.setObjectName(QString::fromLatin1(item.widget));
      input.setProperty(PJ::kBundledUiScope, scope);
      const QString original = QStringLiteral("User_%1 timestamp, ts, time e.g. cam0");
      input.setText(original);
      QCOMPARE(PJ::bundledDisplayText(&input, "placeholderText", QString::fromLatin1(item.english)),
               QString::fromUtf8(item.chinese));
      QCOMPARE(PJ::bundledDisplayText(&input, "text", original), original);
      QCOMPARE(input.text(), original);
      QCOMPARE(PJ::localizeBundledUi(raw + "\n", &scope), raw + "\n");
      QVERIFY(scope.isEmpty());
    }
#else
    QSKIP("Production application catalog is unavailable when PJ4_BUILD_APP is disabled");
#endif
  }
  void exactUiGateAndLanguage() {
    QFile file(QStringLiteral(PJ_CSV_UI_FIXTURE));
    QVERIFY(file.open(QIODevice::ReadOnly));
    // Git may check this fixture out with CRLF on Windows. Identity uses LF.
    const auto ui = file.readAll().replace("\r\n", "\n");
    QByteArray scope;
    Translation translator;
    QCoreApplication::installTranslator(&translator);
    const auto localized = PJ::localizeBundledUi(ui, &scope);
    QVERIFY(!scope.isEmpty());
    QVERIFY(localized.contains(QStringLiteral("CSV 加载器").toUtf8()));
    QCOMPARE(scope, QCryptographicHash::hash(ui, QCryptographicHash::Sha256).toHex());
    QByteArray windows = ui;
    windows.replace("\n", "\r\n");
    QVERIFY(PJ::localizeBundledUi(windows, &scope).contains(QStringLiteral("CSV 加载器").toUtf8()));
    QCOMPARE(scope, QCryptographicHash::hash(ui, QCryptographicHash::Sha256).toHex());
    const auto changed = ui + "\n";
    QCOMPARE(PJ::localizeBundledUi(changed, &scope), changed);
    QVERIFY(scope.isEmpty());
    QCoreApplication::removeTranslator(&translator);
    const auto english = PJ::localizeBundledUi(ui, &scope);
    QVERIFY(english.contains("CSV Loader"));
  }
  void anonymousLabelIsBoundToExactQuaternionUi() {
    QFile file(QFileInfo(QStringLiteral(PJ_CSV_UI_FIXTURE)).dir().filePath(QStringLiteral("quaternion_1_0_1.ui")));
    QVERIFY(file.open(QIODevice::ReadOnly));
    const auto raw = file.readAll().replace("\r\n", "\n");
    Translation translator;
    QCoreApplication::installTranslator(&translator);
    QByteArray scope;
    const auto translated = PJ::localizeBundledUi(raw, &scope);
    QVERIFY(translated.contains(QStringLiteral("输出：").toUtf8()));
    QVERIFY(translated.contains(QStringLiteral("例如 /imu/rpy/").toUtf8()));
    QCOMPARE(PJ::localizeBundledUi(raw + "\n", &scope), raw + "\n");
    QCoreApplication::removeTranslator(&translator);
  }
  void specificDiagnosticPrecedesFallback() {
    Translation translator;
    QCoreApplication::installTranslator(&translator);
    QCOMPARE(
        PJ::bundledPluginMessage(
            QStringLiteral("toolbox-transform-editor"), QStringLiteral("1.0.4"),
            QStringLiteral("Transform Editor: created 3 series.")),
        QStringLiteral("变换编辑器：已创建 3 条曲线。"));
    QCoreApplication::removeTranslator(&translator);
  }
  void scopedDataAndCanonicalCombo() {
    QFile file(QStringLiteral(PJ_CSV_UI_FIXTURE));
    QVERIFY(file.open(QIODevice::ReadOnly));
    const auto scope = QCryptographicHash::hash(file.readAll().replace("\r\n", "\n"), QCryptographicHash::Sha256).toHex();
    Translation translator;
    QCoreApplication::installTranslator(&translator);
    QComboBox combo;
    combo.setObjectName(QStringLiteral("timeAxisModeCombo"));
    combo.setProperty(PJ::kBundledUiScope, scope);
    const auto canonical = QStringLiteral("Number of Rows");
    const auto visible = PJ::bundledDisplayText(&combo, "text", canonical);
    QCOMPARE(visible, QStringLiteral("行号"));
    combo.addItem(visible);
    combo.setItemData(0, canonical, PJ::kCanonicalComboTextRole);
    QCOMPARE(PJ::canonicalComboText(&combo, 0), canonical);
    combo.setEditable(true);
    combo.setEditText(QStringLiteral("user %1 / Number of Rows"));
    QCOMPARE(PJ::canonicalComboText(&combo, 0), combo.currentText());
    QLabel label;
    label.setProperty(PJ::kBundledUiScope, scope);
    label.setObjectName(QStringLiteral("labelWarning"));
    const auto field = QStringLiteral("raw %2 / 中文\\path\nfield");
    const auto warning = QStringLiteral("Values in \"") + field +
                         QStringLiteral("\" are not monotonically increasing. Will sort these automatically");
    QCOMPARE(
        PJ::bundledDisplayText(&label, "text", warning),
        QStringLiteral("“") + field + QStringLiteral("”列中的值不是单调递增的，将自动排序"));
    label.setObjectName(QStringLiteral("userData"));
    QCOMPARE(PJ::bundledDisplayText(&label, "text", warning), warning);
    label.setObjectName(QStringLiteral("labelWarning"));
    label.setProperty(PJ::kBundledUiScope, QByteArray("unknown"));
    QCOMPARE(PJ::bundledDisplayText(&label, "text", warning), warning);
    QCoreApplication::removeTranslator(&translator);
  }
};
// A console entry point preserves QTest failure output on Windows runners.
int main(int argc, char** argv) {
  QApplication app(argc, argv);
  BundledTranslationsTest test;
  return QTest::qExec(&test, argc, argv);
}
#include "bundled_translations_qtest.moc"
