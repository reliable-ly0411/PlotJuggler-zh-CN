// SPDX-License-Identifier: MPL-2.0
#pragma once

#include <QString>
#include <cstddef>

namespace marker_probe {

// Return true for the same case-sensitive record-name expression used by take().
// The name alone is inspected, including names whose PID would overflow qint64.
bool isMarkerName(const QString& name);

// A successful TokenRestrictedSids query must report an empty list.
bool permitsRestrictingSidCount(qint64 count);

// Parse the count without assuming a zero-entry buffer contains array padding.
bool parseRestrictingSidCount(const unsigned char* data, std::size_t size, std::size_t groups_offset,
                              std::size_t group_size, quint32& count);

// Facts are valid only for the instant at which the platform probe collected them.
struct Facts {
  bool identity_ok = false;
  bool qt_ok = false;
  bool path_ok = false;
  bool marker_enumeration_ok = false;
  qint64 marker_count = 0;
  bool process_enumeration_ok = false;
  qint64 other_process_count = 0;
};

// Fail closed on every unknown fact; nonzero codes are part of the CLI contract.
int decide(const Facts& facts);

}  // namespace marker_probe
