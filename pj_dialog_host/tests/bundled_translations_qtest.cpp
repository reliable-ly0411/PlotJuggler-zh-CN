// SPDX-License-Identifier: MPL-2.0
#include <QApplication>
#include <QComboBox>
#include <QCryptographicHash>
#include <QFile>
#include <QFileInfo>
#include <QDir>
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
