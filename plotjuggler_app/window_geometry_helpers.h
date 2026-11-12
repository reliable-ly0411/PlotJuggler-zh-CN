// SPDX-License-Identifier: MPL-2.0
#pragma once
#include <QMargins>
#include <QRect>
#include <QVector>
#include <algorithm>
#include <limits>
// Input/output rectangles are frame coordinates in Qt logical pixels.
inline QRect fitWindowFrame(QRect frame, const QRect& available, const QMargins& margins)
{
  const int horizontal = margins.left() + margins.right();
  const int vertical = margins.top() + margins.bottom();
  const int width = std::min(frame.width(), available.width());
  const int height = std::min(frame.height(), available.height());
  frame.setSize(QSize(std::max(width, horizontal + 1), std::max(height, vertical + 1)));
  frame.moveLeft(std::max(available.left(), std::min(frame.left(), available.right() - frame.width() + 1)));
  frame.moveTop(std::max(available.top(), std::min(frame.top(), available.bottom() - frame.height() + 1)));
  return frame;
}

// Prefer the largest visible portion, then the screen nearest the old frame.
inline int chooseScreen(const QRect& frame, const QVector<QRect>& screens)
{
  int best = -1;
  qint64 bestArea = -1;
  qint64 bestDistance = std::numeric_limits<qint64>::max();
  const QPoint center = frame.center();
  for (int i = 0; i < screens.size(); ++i)
  {
    const QRect intersection = frame.intersected(screens[i]);
    const qint64 area = qint64(intersection.width()) * intersection.height();
    const qint64 dx = qint64(center.x()) - std::max(screens[i].left(), std::min(center.x(), screens[i].right()));
    const qint64 dy = qint64(center.y()) - std::max(screens[i].top(), std::min(center.y(), screens[i].bottom()));
    const qint64 distance = dx * dx + dy * dy;
    if (area > bestArea || (area == bestArea && distance < bestDistance))
    {
      best = i;
      bestArea = area;
      bestDistance = distance;
    }
  }
  return best;
}
