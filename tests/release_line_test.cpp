// SPDX-License-Identifier: MPL-2.0
#include "release_line.h"
#include <iostream>

int main()
{
  auto release = [](QString tag, bool prerelease = false, bool draft = false) {
    return QJsonObject{{"tag_name", tag}, {"name", "<b>untrusted</b>"},
                       {"html_url", "https://github.com/reliable-ly0411/PlotJuggler-zh-CN/releases/tag/" + tag},
                       {"draft", draft}, {"prerelease", prerelease}};
  };
  PJ::ReleaseLineSelection stable("3.18.0+zh.1");
  if (stable.consume({release("4.1.0"), release("3.19.0-rc.1", true),
                      release("3.20.0", false, true), release("v3.18.2"), release("3.18.1")}) !=
      PJ::ReleaseLineSelection::Complete || stable.tag != "v3.18.2") return 5;
  PJ::ReleaseLineSelection preview("3.18.1-rc.14+upstream.3.17.2");
  if (preview.consume({release("4.0.0"), release("3.18.1-rc.15", true)}) !=
      PJ::ReleaseLineSelection::Complete || preview.tag != "3.18.1-rc.15") return 6;
  PJ::ReleaseLineSelection promotion("3.18.1-rc.15");
  promotion.consume({release("3.18.1-rc.16", true), release("3.18.1")});
  if (promotion.tag != "3.18.1") return 7;
  PJ::ReleaseLineSelection pages("3.18.0");
  QJsonArray first;
  for (int i = 0; i < PJ::ReleaseLineSelection::PageSize; ++i) first.append(release("4.1.0"));
  if (pages.consume(first) != PJ::ReleaseLineSelection::More || !pages.tag.isEmpty()) return 8;
  if (pages.consume({release("3.18.3")}) != PJ::ReleaseLineSelection::Complete || pages.tag != "3.18.3") return 9;
  PJ::ReleaseLineSelection bounded("3.18.0");
  for (int i = 1; i < PJ::ReleaseLineSelection::MaxPages; ++i)
    if (bounded.consume(first) != PJ::ReleaseLineSelection::More) return 10;
  if (bounded.consume(first) != PJ::ReleaseLineSelection::Failed) return 11;
  PJ::ReleaseLineSelection malformed("3.18.0");
  if (malformed.consume({QJsonObject{{"tag_name", "3.19.0"}}}) != PJ::ReleaseLineSelection::Failed) return 12;
  PJ::ReleaseLineSelection links("3.18.0");
  for (const auto& url : {"http://github.com/reliable-ly0411/PlotJuggler-zh-CN/releases/tag/3.19.0",
                          "https://github.com/attacker/repo/releases/tag/3.19.0",
                          "https://user@github.com/reliable-ly0411/PlotJuggler-zh-CN/releases/tag/3.19.0",
                          "https://github.com/reliable-ly0411/PlotJuggler-zh-CN/releases/tag/3.19.0?x=1"})
  {
    auto bad = release("3.19.0"); bad["html_url"] = url;
    links.consume({bad});
    if (!links.tag.isEmpty()) return 13;
  }
  PJ::ReleaseLineSelection flags("3.18.0");
  flags.consume({release("3.19.0", true), release("3.19.0-rc.1", false), release("3.019.0")});
  if (!flags.tag.isEmpty()) return 14;
  PJ::ReleaseLineSelection metadata("3.18.0+zh.1");
  metadata.consume({release("3.18.0+zh.2")});
  if (!metadata.tag.isEmpty()) return 15;
  std::cout << "PASS: maintenance line, channel, pagination and URL policy\n";
  return 0;
}
