// SPDX-License-Identifier: MPL-2.0
#include <array>

#include <QApplication>
#include <QDialogButtonBox>
#include <QFileDialog>
#include <QFileIconProvider>
#include <QFileInfo>
#include <QLocale>
#include <QPushButton>
#include <QSettings>
#include <QTemporaryDir>
#include <QTest>

#include "AppLanguage.h"

using namespace Qt::StringLiterals;

namespace {
struct LanguageCase {
  QString language;
  QString look_in;
  QString file_type;
  QString cancel;
  QString folder;
};

const std::array<LanguageCase, 5> kLanguageCases{{
    {u"en_US"_s, u"&Look in:"_s, u"Files of &type:"_s, u"Cancel"_s, u"Folder"_s},
    {u"zh_CN"_s, u"查找范围(&L)："_s, u"文件类型(&T)："_s, u"取消"_s, u"文件夹"_s},
    {u"en_US"_s, u"&Look in:"_s, u"Files of &type:"_s, u"Cancel"_s, u"Folder"_s},
    {u"zh_TW"_s, u"尋找範圍(&L)："_s, u"檔案型別(&T)："_s, u"取消"_s, u"資料夾"_s},
    {u"en_US"_s, u"&Look in:"_s, u"Files of &type:"_s, u"Cancel"_s, u"Folder"_s},
}};
}  // namespace

class QtFileDialogLanguageTest : public QObject {
  Q_OBJECT

 private slots:
#if defined(Q_OS_LINUX)
  void repeatedNonNativeFileDialogsUseSelectedLanguage() {
    for (const auto& entry : kLanguageCases) {
      const PJ::AppLanguage language(*qApp, entry.language);
      QCOMPARE(language.language(), entry.language);
      QFileDialog dialog;
      dialog.setOption(QFileDialog::DontUseNativeDialog);
      QCOMPARE(dialog.labelText(QFileDialog::LookIn), entry.look_in);
      QCOMPARE(dialog.labelText(QFileDialog::FileType), entry.file_type);
    }
  }
#endif

  void repeatedWidgetLookupsDoNotChangeTheNumericLocale() {
    const QLocale original;
    const QString original_number = original.toString(1234.5);
    QTemporaryDir directory;
    QVERIFY(directory.isValid());
    for (const auto& entry : kLanguageCases) {
      const PJ::AppLanguage language(*qApp, entry.language);
      QCOMPARE(language.language(), entry.language);
      QDialogButtonBox buttons(QDialogButtonBox::Cancel);
      QCOMPARE(buttons.button(QDialogButtonBox::Cancel)->text(), entry.cancel);
      QFileIconProvider icons;
      const QString folder_type = icons.type(QFileInfo(directory.path()));
      if (entry.language == "en_US"_L1) {
        QVERIFY(folder_type == entry.folder || folder_type == "File Folder"_L1);
      } else {
        QCOMPARE(folder_type, entry.folder);
      }
      QCOMPARE(QLocale(), original);
      QCOMPARE(QLocale().toString(1234.5), original_number);
    }
  }
};

int main(int argc, char** argv) {
  QTemporaryDir settings_directory;
  if (!settings_directory.isValid()) {
    return 1;
  }
  QSettings::setDefaultFormat(QSettings::IniFormat);
  QSettings::setPath(QSettings::IniFormat, QSettings::UserScope, settings_directory.path());
#if defined(Q_OS_LINUX)
  // QFileDialog writes under QtProject using NativeFormat. Redirect that too.
  QSettings::setPath(QSettings::NativeFormat, QSettings::UserScope, settings_directory.path());
#endif
  QApplication app(argc, argv);
  QtFileDialogLanguageTest test;
  return QTest::qExec(&test, argc, argv);
}
#include "qt_file_dialog_language_test.moc"
