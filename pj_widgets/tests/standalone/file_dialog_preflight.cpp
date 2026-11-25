// SPDX-License-Identifier: MPL-2.0
// No application SDK or services: link the real file-dialog implementation.
#include <QApplication>
#include <QAbstractProxyModel>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QFileDialog>
#include <QFileSystemModel>
#include <QJsonDocument>
#include <QJsonObject>
#include <QMimeDatabase>
#include <QSettings>
#include <QLocale>
#include <QStandardPaths>
#include <QTemporaryDir>
#include <QtTest>
#include <filesystem>
#include "pj_widgets/FileDialog.h"
using namespace Qt::StringLiterals;

class FileDialogPreflight : public QObject {
  Q_OBJECT
 private slots:
  void linksKeepIdentity() {
    QTemporaryDir temp;
    QVERIFY(temp.isValid());
    const QDir dir(temp.path());
    QFile target(dir.filePath(u"原始 %1 [target].txt"_s));
    QVERIFY(target.open(QIODevice::WriteOnly));
    QCOMPARE(target.write("plain text", 10), 10);
    target.close();
    QVERIFY(dir.mkdir(u"folder"_s));
    QStringList names{u"same.txt"_s,u"different.xml"_s,u"folder-link"_s,u"broken-link"_s};
    QStringList destinations{target.fileName(),target.fileName(),dir.filePath(u"folder"_s),dir.filePath(u"missing"_s)};
    for (int i=0;i<names.size();++i) {
      std::error_code ec;
      const auto dest=QFileInfo(destinations[i]).filesystemFilePath();
      const auto link=QFileInfo(dir.filePath(names[i])).filesystemFilePath();
      if(i==2) std::filesystem::create_directory_symlink(dest,link,ec);
      else std::filesystem::create_symlink(dest,link,ec);
      QVERIFY2(!ec,ec.message().c_str());
    }
#ifdef Q_OS_WIN
    QVERIFY(QFile::link(target.fileName(),dir.filePath(u"native-shortcut.lnk"_s)));
    names.append(u"native-shortcut.lnk"_s);
#endif
    qApp->setProperty("interfaceLanguage",u"zh_CN"_s);
    PJ::FileDialog picker;
    picker.setDirectory(temp.path());
    auto* inner=picker.findChild<QFileDialog*>();
    QVERIFY(inner);
    inner->setFilter(inner->filter()|QDir::System);
    auto* proxy=inner->proxyModel();
    QVERIFY(proxy);
    auto* source=qobject_cast<QFileSystemModel*>(proxy->sourceModel());
    QVERIFY(source);
    picker.show();
    // Collect every row before asserting, so one failure does not hide platform semantics.
    bool all=true;
    for(int i=0;i<names.size();++i) {
      const QString path=dir.filePath(names[i]);
      QTRY_VERIFY_WITH_TIMEOUT(source->index(path).isValid(),5000);
      const QModelIndex original=source->index(path);
      const QModelIndex shown=proxy->mapFromSource(original);
      QVERIFY(shown.isValid());
      const QFileInfo direct(path), info=source->fileInfo(original.siblingAtColumn(2));
      const QString actual=proxy->data(shown.siblingAtColumn(2)).toString();
      const QString raw=source->data(original.siblingAtColumn(2)).toString();
      std::error_code ec;
      const bool regular=std::filesystem::is_regular_file(direct.filesystemFilePath(),ec);
      QJsonObject row{{"name",names[i]},{"path",path},{"modelPath",info.filePath()},
        {"isFile",info.isFile()},{"isDir",info.isDir()},{"isSymLink",info.isSymLink()},
        {"isSymbolicLink",info.isSymbolicLink()},{"isShortcut",info.isShortcut()},{"exists",info.exists()},
        {"directIsFile",direct.isFile()},{"regularFile",regular},{"statusError",QString::fromStdString(ec.message())},
        {"sourceType",raw},{"proxyType",actual},{"mime",QMimeDatabase().mimeTypeForFile(info).name()}};
      qInfo().noquote()<<QJsonDocument(row).toJson(QJsonDocument::Compact);
      QCOMPARE(proxy->mapToSource(shown),original);
      QCOMPARE(proxy->data(shown,Qt::EditRole),source->data(original,Qt::EditRole));
      QCOMPARE(proxy->data(shown,QFileSystemModel::FilePathRole),source->data(original,QFileSystemModel::FilePathRole));
      QCOMPARE(proxy->data(shown),source->data(original));
      if(i<4) {
        QCOMPARE(proxy->data(shown,QFileSystemModel::FilePathRole).toString(),path);
        QCOMPARE(proxy->data(shown).toString(),names[i]);
      }
      if(i<2) {
        const QString mime=QMimeDatabase().mimeTypeForFile(info).name();
        const QString expected=QCoreApplication::translate("PJ::FileDialog",mime==u"text/plain"_s?"Plain text document":"XML document");
        if(actual!=expected){qWarning()<<names[i]<<"expected"<<expected<<"actual"<<actual;all=false;}
        QCOMPARE(proxy->data(shown.siblingAtColumn(1)).toString(),
                 QLocale(QLocale::Chinese,QLocale::China).formattedDataSize(source->size(original)));
      } else if(i<4 && actual!=raw) {
        qWarning()<<names[i]<<"must preserve source Type"<<raw<<"but got"<<actual;all=false;
      }
      if(i==2 || i==3) {
        QCOMPARE(proxy->data(shown.siblingAtColumn(1)),source->data(original.siblingAtColumn(1)));
      }
#ifdef Q_OS_WIN
      if(i==4) {
        QVERIFY(info.isShortcut());
        QVERIFY(!info.isSymbolicLink());
        QCOMPARE(actual,QCoreApplication::translate("PJ::FileDialog","Binary file"));
        QCOMPARE(proxy->data(shown.siblingAtColumn(1)).toString(),
                 QLocale(QLocale::Chinese,QLocale::China).formattedDataSize(source->size(original)));
      }
#endif
      picker.selectFile(path);
      QCOMPARE(picker.selectedFile(),inner->selectedFiles().value(0));
      if(i<2) QCOMPARE(picker.selectedFile(),path);
      qApp->setProperty("interfaceLanguage",u"en_US"_s);
      QCOMPARE(proxy->data(shown.siblingAtColumn(2)).toString(),raw);
      QCOMPARE(proxy->data(shown.siblingAtColumn(1)),source->data(original.siblingAtColumn(1)));
      qApp->setProperty("interfaceLanguage",u"zh_CN"_s);
    }
    QVERIFY2(all,"See all row-specific Type diagnostics above; no failed row is skipped.");
  }
};
int main(int argc,char** argv) {
  QStandardPaths::setTestModeEnabled(true);
  QApplication app(argc,argv);
  QCoreApplication::setOrganizationName(u"PlotJugglerTest"_s);
  QCoreApplication::setApplicationName(u"FileDialogPreflight"_s);
  QSettings().clear();
  FileDialogPreflight test;
  return QTest::qExec(&test,argc,argv);
}
#include "file_dialog_preflight.moc"
