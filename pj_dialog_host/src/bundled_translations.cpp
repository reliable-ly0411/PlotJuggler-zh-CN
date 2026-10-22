// Copyright 2026 PlotJuggler Chinese localization contributors
// SPDX-License-Identifier: MIT
#include "pj_plugins/host_qt/bundled_translations.hpp"

#include <QComboBox>
#include <QCoreApplication>
#include <QCryptographicHash>
#include <QDomDocument>
#include <QRegularExpression>
#include <QWidget>

namespace PJ {
namespace {
struct DisplayEntry {
  const char* scope;
  const char* widget;
  const char* property;
  const char* source;
};
struct TemplateEntry {
  const char* scope;
  const char* widget;
  const char* property;
  const char* pattern;
  const char* source;
};
#include "bundled_translation_entries.hpp"

QString translate(const QByteArray& scope, const QString& widget, const QString& property, const QString& source) {
  for (const auto& entry : kDisplayEntries) {
    if (scope == entry.scope && widget == QLatin1String(entry.widget) && property == QLatin1String(entry.property) &&
        source == QString::fromUtf8(entry.source)) {
      return QCoreApplication::translate("PJ::BundledPlugins", entry.source);
    }
  }
  for (const auto& entry : kTemplateEntries) {
    if (scope != entry.scope || widget != QLatin1String(entry.widget) || property != QLatin1String(entry.property)) {
      continue;
    }
    const auto match = QRegularExpression(QString::fromUtf8(entry.pattern)).match(source);
    if (!match.hasMatch()) {
      continue;
    }
    const auto translated = QCoreApplication::translate("PJ::BundledPlugins", entry.source);
    if (translated == QString::fromUtf8(entry.source)) {
      return source;
    }
    // Append captured user data once: QString::arg chaining could reinterpret
    // percent sequences contained in a path, field name or external diagnostic.
    QString result;
    qsizetype previous = 0;
    auto placeholders = QRegularExpression(QStringLiteral("%([1-9][0-9]*)")).globalMatch(translated);
    while (placeholders.hasNext()) {
      const auto token = placeholders.next();
      result += translated.mid(previous, token.capturedStart() - previous);
      result += match.captured(token.captured(1).toInt());
      previous = token.capturedEnd();
    }
    return result + translated.mid(previous);
  }
  return source;
}
QString ownerName(QDomNode node) {
  while (!node.isNull()) {
    const auto e = node.toElement();
    if (e.tagName() == QLatin1String("widget") || e.tagName() == QLatin1String("action")) {
      return e.attribute(QStringLiteral("name"));
    }
    node = node.parentNode();
  }
  return {};
}
}  // namespace

QByteArray localizeBundledUi(const QByteArray& ui, QByteArray* scope) {
  scope->clear();
  // Official Windows plugin builds embed CRLF checkouts; XML normalizes these
  // newlines too. Normalize only CRLF for identity, never trim or rewrite data.
  QByteArray identity = ui;
  identity.replace("\r\n", "\n");
  const auto hash = QCryptographicHash::hash(identity, QCryptographicHash::Sha256).toHex();
  bool known = false;
  for (const auto* accepted : kBundledUiHashes) {
    known |= (hash == accepted);
  }
  if (!known) {
    return ui;
  }
  QDomDocument doc;
  if (!doc.setContent(ui)) {
    return ui;
  }
  *scope = hash;
  const auto strings = doc.elementsByTagName(QStringLiteral("string"));
  for (int i = 0; i < strings.count(); ++i) {
    auto element = strings.at(i).toElement();
    if (element.attribute(QStringLiteral("notr")) == QLatin1String("true")) {
      continue;
    }
    auto parent = element.parentNode().toElement();
    if (parent.tagName() == QLatin1String("stringlist")) {
      parent = parent.parentNode().toElement();
    }
    if (parent.tagName() != QLatin1String("property") && parent.tagName() != QLatin1String("attribute")) {
      continue;
    }
    const auto original = element.text();
    const auto translated = translate(hash, ownerName(parent), parent.attribute(QStringLiteral("name")), original);
    if (translated == original) {
      continue;
    }
    while (!element.firstChild().isNull()) {
      element.removeChild(element.firstChild());
    }
    element.appendChild(doc.createTextNode(translated));
  }
  return doc.toByteArray();
}

void initializeBundledWidgets(QWidget* root, const QByteArray& original, const QByteArray& scope) {
  root->setProperty(kBundledUiScope, scope);
  for (auto* widget : root->findChildren<QWidget*>()) {
    widget->setProperty(kBundledUiScope, scope);
  }
  QDomDocument doc;
  if (!doc.setContent(original)) {
    return;
  }
  const auto widgets = doc.elementsByTagName(QStringLiteral("widget"));
  for (int i = 0; i < widgets.count(); ++i) {
    const auto element = widgets.at(i).toElement();
    const auto name = element.attribute(QStringLiteral("name"));
    auto* combo = root->findChild<QComboBox*>(name);
    if (!combo || combo->isEditable()) {
      continue;
    }
    int index = 0;
    for (auto item = element.firstChildElement(QStringLiteral("item")); !item.isNull();
         item = item.nextSiblingElement(QStringLiteral("item")), ++index) {
      for (auto prop = item.firstChildElement(QStringLiteral("property")); !prop.isNull();
           prop = prop.nextSiblingElement(QStringLiteral("property"))) {
        if (prop.attribute(QStringLiteral("name")) == QLatin1String("text")) {
          combo->setItemData(index, prop.firstChildElement(QStringLiteral("string")).text(), kCanonicalComboTextRole);
        }
      }
    }
  }
}

QString bundledDisplayText(const QWidget* widget, const char* property, const QString& source) {
  return translate(
      widget->property(kBundledUiScope).toByteArray(), widget->objectName(), QLatin1String(property), source);
}

QString bundledNamedDisplayText(
    const QWidget* root, const QString& objectName, const char* property, const QString& source) {
  return translate(root->property(kBundledUiScope).toByteArray(), objectName, QLatin1String(property), source);
}

QString bundledPluginMessage(const QString& id, const QString& version, const QString& source) {
  return translate(
      (QStringLiteral("plugin:") + id + QStringLiteral("@") + version).toUtf8(), QStringLiteral("message-source:") + id,
      QStringLiteral("message"), source);
}

QString canonicalComboText(const QComboBox* combo, int index) {
  if (combo->isEditable()) {
    return combo->currentText();
  }
  {
    const auto canonical = combo->itemData(index, kCanonicalComboTextRole);
    if (canonical.isValid()) {
      return canonical.toString();
    }
  }
  return index >= 0 ? combo->itemText(index) : combo->currentText();
}
}  // namespace PJ
