// SPDX-License-Identifier: MPL-2.0
#pragma once
#include <QRegularExpression>
#include <QStringList>
#include <array>

namespace PJ {
/// Compare complete SemVer 2.0.0 values; build metadata never changes precedence.
inline bool isNewerSemVer(QString candidate, QString installed)
{
  static const QRegularExpression syntax(
      R"(^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$)");
  static const QRegularExpression digits("^[0-9]+$");
  auto parse = [&](QString value) {
    if (value.startsWith('v')) value.remove(0, 1);
    return syntax.match(value);
  };
  const auto left = parse(candidate);
  const auto right = parse(installed);
  if (!left.hasMatch() || !right.hasMatch()) return false;
  const auto left_pre = left.captured(4).split('.', Qt::SkipEmptyParts);
  const auto right_pre = right.captured(4).split('.', Qt::SkipEmptyParts);
  for (const auto& identifiers : {left_pre, right_pre})
    for (const auto& identifier : identifiers)
      if (digits.match(identifier).hasMatch() && identifier.size() > 1 && identifier.startsWith('0')) return false;
  auto numericCompare = [](const QString& a, const QString& b) {
    if (a.size() != b.size()) return a.size() > b.size() ? 1 : -1;
    return QString::compare(a, b, Qt::CaseSensitive);
  };
  for (int i = 1; i <= 3; ++i)
  {
    const int difference = numericCompare(left.captured(i), right.captured(i));
    if (difference) return difference > 0;
  }
  if (left_pre.isEmpty() || right_pre.isEmpty()) return !left_pre.isEmpty() ? false : !right_pre.isEmpty();
  const int shared = qMin(left_pre.size(), right_pre.size());
  for (int i = 0; i < shared; ++i)
  {
    const bool a_numeric = digits.match(left_pre[i]).hasMatch();
    const bool b_numeric = digits.match(right_pre[i]).hasMatch();
    if (a_numeric != b_numeric) return !a_numeric;
    const int difference = a_numeric ? numericCompare(left_pre[i], right_pre[i])
                                     : QString::compare(left_pre[i], right_pre[i], Qt::CaseSensitive);
    if (difference) return difference > 0;
  }
  return left_pre.size() > right_pre.size();
}
}  // namespace PJ
