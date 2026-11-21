// SPDX-License-Identifier: MPL-2.0
#include <gtest/gtest.h>
#include <QComboBox>
#include <QPushButton>
#include <QSignalSpy>
#include <QSettings>
#include <QScopeGuard>
#include "ui/LeftPanel.h"
using namespace Qt::StringLiterals;
namespace PJ {
TEST(LeftPanelLocalizedSourcesTest, CanonicalSelectionSurvivesRefreshAndLanguageChange) {
  QSettings settings;
  const QString key = u"MainWindow.streamingSource"_s;
  const bool existed = settings.contains(key);
  const QVariant previous = settings.value(key);
  const auto restore = qScopeGuard([&] {
    if (existed) settings.setValue(key, previous);
    else settings.remove(key);
  });
  LeftPanel panel;
  auto* combo = panel.findChild<QComboBox*>(u"comboStreaming"_s);
  ASSERT_NE(combo, nullptr);
  settings.remove(key);
  auto* start = panel.findChild<QPushButton*>(u"buttonStreamingOptions"_s);
  ASSERT_NE(start, nullptr);
  QSignalSpy started(&panel, &LeftPanel::streamingStartRequested);
  panel.setStreamingSources({{u"Dummy Streamer"_s, u"模拟数据流"_s},
                             {u"WebRTC Video Client"_s, u"WebRTC 视频客户端"_s}});
  combo->setCurrentIndex(1);
  EXPECT_EQ(combo->currentText(), u"WebRTC 视频客户端"_s);
  EXPECT_FALSE(settings.contains(key));
  start->click();
  ASSERT_EQ(started.size(), 1);
  EXPECT_EQ(started.takeFirst().at(0).toString(), u"WebRTC Video Client"_s);
  emit combo->activated(combo->currentIndex());
  EXPECT_EQ(settings.value(key).toString(), u"WebRTC Video Client"_s);
  QDomDocument doc;
  const auto saved = panel.saveSourcesState(doc, false);
  EXPECT_EQ(saved.attribute(u"streaming_source"_s), u"WebRTC Video Client"_s);
  panel.setStreamingSources({{u"Dummy Streamer"_s, u"Dummy Streamer"_s},
                             {u"WebRTC Video Client"_s, u"WebRTC Video Client"_s}});
  EXPECT_EQ(combo->currentData().toString(), u"WebRTC Video Client"_s);
  EXPECT_TRUE(started.empty());
  combo->setCurrentIndex(0);
  panel.restoreSourcesState(saved, std::nullopt);
  EXPECT_EQ(settings.value(key).toString(), u"WebRTC Video Client"_s);
  EXPECT_EQ(combo->currentData().toString(), u"WebRTC Video Client"_s);
}
}  // namespace PJ
