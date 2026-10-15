// SPDX-License-Identifier: MPL-2.0
#include "semver.h"
#include <iostream>

int main()
{
  const QStringList ordered{"1.0.0-alpha", "1.0.0-alpha.1", "1.0.0-alpha.beta", "1.0.0-beta",
                            "1.0.0-beta.2", "1.0.0-beta.11", "1.0.0-rc.1", "1.0.0"};
  for (int i = 1; i < ordered.size(); ++i)
    if (!PJ::isNewerSemVer(ordered[i], ordered[i - 1]) || PJ::isNewerSemVer(ordered[i - 1], ordered[i])) return 1;
  if (PJ::isNewerSemVer("3.18.0-zh.1+build.2", "3.18.0-zh.1+build.1")) return 2;
  if (!PJ::isNewerSemVer("3.18.0-zh.10", "3.18.0-zh.2")) return 3;
  for (const auto& invalid : {"03.18.0", "3.18", "3.18.0-zh.01", "3.18.0+", "3.18.0-a..b"})
    if (PJ::isNewerSemVer(invalid, "1.0.0")) return 4;
  std::cout << "PASS: SemVer core, prerelease ordering, invalid identifiers, metadata equality\n";
  return 0;
}
