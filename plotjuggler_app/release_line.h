// SPDX-License-Identifier: MPL-2.0
#pragma once
#include "semver.h"
#include <QJsonArray>
#include <QJsonObject>
#include <QUrl>

namespace PJ {
// Search all bounded pages before notifying: GitHub sorts by creation, not SemVer.
// A stable install receives stable releases only; prerelease installs may receive
// newer prereleases or stable releases, but never a different major line.
struct ReleaseLineSelection
{
  static constexpr int PageSize = 100;
  static constexpr int MaxPages = 10;
  enum Result { More, Complete, Failed };
  explicit ReleaseLineSelection(QString version) : installed(std::move(version)) {}
  QString installed, tag, name, url;
  int pages = 0;
  Result consume(const QJsonArray& releases)
  {
    const auto current = parseSemVer(installed);
    if (!current.hasMatch() || releases.size() > PageSize || ++pages > MaxPages)
      return Failed;
    for (const auto& value : releases)
    {
      if (!value.isObject()) return Failed;
      const auto object = value.toObject();
      if (!object.value("draft").isBool() || !object.value("prerelease").isBool())
        return Failed;
      if (object.value("draft").toBool()) continue;
      const QString candidate = object.value("tag_name").toString();
      const auto parsed = parseSemVer(candidate);
      if (!parsed.hasMatch() || parsed.captured(1) != current.captured(1)) continue;
      if (current.captured(4).isEmpty() &&
          (object.value("prerelease").toBool() || !parsed.captured(4).isEmpty())) continue;
      if (!isNewerSemVer(candidate, installed) ||
          (!tag.isEmpty() && !isNewerSemVer(candidate, tag))) continue;
      const QUrl link(object.value("html_url").toString(), QUrl::StrictMode);
      // Links must remain on this repository; no credentials, port or fragment.
      if (!link.isValid() || link.scheme() != "https" || link.host() != "github.com" ||
          !link.userInfo().isEmpty() || link.port() != -1 || link.hasQuery() || link.hasFragment() ||
          link.path() != "/reliable-ly0411/PlotJuggler-zh-CN/releases/tag/" + candidate) continue;
      tag = candidate;
      name = object.value("name").toString();
      if (name.isEmpty()) name = tag;
      url = link.toString(QUrl::FullyEncoded);
    }
    if (releases.size() < PageSize) return Complete;
    return pages < MaxPages ? More : Failed;
  }
};
} // namespace PJ
