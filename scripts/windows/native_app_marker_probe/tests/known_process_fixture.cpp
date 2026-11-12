// SPDX-License-Identifier: MPL-2.0
// A harmless child for process enumeration; it exits when its test closes stdin.
#include <cstdio>
int main() {
  while (std::getchar() != EOF) {}
  return 0;
}
