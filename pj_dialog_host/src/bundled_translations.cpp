// Copyright 2026 PlotJuggler Chinese localization contributors
// SPDX-License-Identifier: MIT
#include "pj_plugins/host_qt/bundled_translations.hpp"

#include <QComboBox>
#include <QCoreApplication>
#include <QCryptographicHash>
#include <QDomDocument>
#include <QHBoxLayout>
#include <QLabel>
#include <QPushButton>
#include <QRegularExpression>
#include <QVBoxLayout>
#include <QWidget>

namespace PJ {
namespace {
struct DisplayEntry {
  const char* scope;
  const char* widget;
  const char* property;
  const char* source;
};
struct GuardedDisplayEntry {
  const char* scope;
  const char* widget;
  const char* property;
  const char* disabled_widget;
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

QString translate(
    const QByteArray& scope, const QString& widget, const QString& property, const QString& source,
    const BundledEnabledLookup& enabled = {}, bool static_ui = false) {
  for (const auto& entry : kGuardedDisplayEntries) {
    if (scope == entry.scope && widget == QLatin1String(entry.widget) && property == QLatin1String(entry.property)) {
      // This label can carry either fixed empty-state prose or an arbitrary field name.
      // Only the same update's explicit control state distinguishes their origins.
      const auto state = enabled ? enabled(entry.disabled_widget) : std::nullopt;
      if (source == QString::fromUtf8(entry.source) && (static_ui || (state && !*state))) {
        return QCoreApplication::translate("PJ::BundledPlugins", entry.source);
      }
      return source;
    }
  }
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

/// Keep the pinned FFT's wrapped status and actions outside the chart splitter.
/// A narrow control column cannot reserve enough height for dynamic status text.
void adaptFftActions(QWidget* root, const QByteArray& scope) {
  if (scope != "f7d484492d4b2033fc141c9ea3a9f83e9a976049947ba9dd90079df2d19099c0") {
    return;
  }
  auto* main = root->findChild<QVBoxLayout*>(QStringLiteral("mainLayout"));
  auto* controls = root->findChild<QVBoxLayout*>(QStringLiteral("ctrlCol"));
  auto* actions = root->findChild<QVBoxLayout*>(QStringLiteral("calcWrap"));
  auto* status = root->findChild<QLabel*>(QStringLiteral("status_label"));
  auto* compute = root->findChild<QPushButton*>(QStringLiteral("btn_compute"));
  auto* save = root->findChild<QPushButton*>(QStringLiteral("btn_save"));
  if (!main || !controls || !actions || !status || !compute || !save ||
      controls->indexOf(status) < 0 || controls->indexOf(actions) < 0 ||
      actions->indexOf(compute) < 0 || actions->indexOf(save) < 0) {
    return;
  }
  controls->removeWidget(status);
  actions->removeWidget(compute);
  actions->removeWidget(save);
  controls->removeItem(actions);
  delete actions;

  // Reparent the same widgets, retaining their names, bindings and enabled state.
  auto* footer = new QHBoxLayout;
  footer->setObjectName(QStringLiteral("fftActionsFooter"));
  footer->setContentsMargins(8, 8, 8, 8);
  status->setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Preferred);
  footer->addWidget(status, 1);
  footer->addWidget(compute);
  footer->addWidget(save);
  main->addLayout(footer);
  main->setStretch(0, 1);
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
    const auto translated =
        translate(hash, ownerName(parent), parent.attribute(QStringLiteral("name")), original, {}, true);
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
  adaptFftActions(root, scope);
}

QString bundledDisplayText(
    const QWidget* widget, const char* property, const QString& source, const BundledEnabledLookup& enabled) {
  return translate(
      widget->property(kBundledUiScope).toByteArray(), widget->objectName(), QLatin1String(property), source, enabled);
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
