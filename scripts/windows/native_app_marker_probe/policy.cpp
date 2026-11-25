// SPDX-License-Identifier: MPL-2.0
#include "policy.h"

#include <QRegularExpression>
#include <cstring>

namespace marker_probe {

bool isMarkerName(const QString& name) {
  static const QRegularExpression record_name(QStringLiteral("^active_widgets\\.(\\d+)\\.json$"));
  return record_name.match(name).hasMatch();
}

bool permitsRestrictingSidCount(qint64 count) {
  return count == 0;
}

bool parseRestrictingSidCount(const unsigned char* data, std::size_t size, std::size_t groups_offset,
                              std::size_t group_size, quint32& count) {
  if (!data || size < sizeof(quint32)) return false;
  quint32 value = 0;
  std::memcpy(&value, data, sizeof(value));
  if (value != 0 && (groups_offset < sizeof(quint32) || group_size == 0 || size < groups_offset ||
                     value > (size - groups_offset) / group_size)) return false;
  count = value;
  return true;
}

int decide(const Facts& facts) {
  if (!facts.identity_ok) return 4;
  if (!facts.qt_ok) return 5;
  if (!facts.path_ok || !facts.marker_enumeration_ok) return 6;
  if (facts.marker_count != 0) return 7;
  if (!facts.process_enumeration_ok || facts.other_process_count != 0) return 8;
  return 0;
}

}  // namespace marker_probe
