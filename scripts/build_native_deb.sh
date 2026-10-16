#!/usr/bin/env bash
# SPDX-License-Identifier: MPL-2.0
# Same native Ubuntu 24.04 payload/compression recipe as zh.3, without release writes.
set -euo pipefail
version="$(python3 -c 'import json; print(json.load(open("build/FORK-VERSION.json"))["version"])')"
stage="$PWD/package"
mkdir -p "$stage/usr/lib/plotjuggler" "$stage/usr/bin" "$stage/DEBIAN" \
  "$stage/usr/share/applications" "$stage/usr/share/icons/hicolor/512x512/apps" \
  "$stage/usr/share/icons/hicolor/scalable/apps" package-metadata/debian output
cp build/bin/plotjuggler build/bin/*.so "$stage/usr/lib/plotjuggler/"
python3 scripts/stage_fork_notices.py "$stage/usr/lib/plotjuggler"
ln -s ../lib/plotjuggler/plotjuggler "$stage/usr/bin/plotjuggler"
cp io.plotjuggler.PlotJuggler.desktop "$stage/usr/share/applications/"
cp plotjuggler.png "$stage/usr/share/icons/hicolor/512x512/apps/"
cp plotjuggler.svg "$stage/usr/share/icons/hicolor/scalable/apps/"
printf 'Source: plotjuggler\nSection: science\nPriority: optional\nMaintainer: PlotJuggler zh-CN <125791929+reliable-ly0411@users.noreply.github.com>\n\nPackage: plotjuggler\nArchitecture: any\nDescription: PlotJuggler zh-CN\n' > package-metadata/debian/control
args=()
for elf in "$stage"/usr/lib/plotjuggler/plotjuggler "$stage"/usr/lib/plotjuggler/*.so; do
  readelf -h "$elf" | grep -E 'Machine:.*Advanced Micro Devices X86-64'
  args+=("-e$elf")
done
deps="$(cd package-metadata && dpkg-shlibdeps -O -l"$stage/usr/lib/plotjuggler" "${args[@]}" | sed -n 's/^shlibs:Depends=//p')"
test -n "$deps"
deb_version="${version/-zh./~zh.}"
printf 'Package: plotjuggler\nVersion: %s\nArchitecture: amd64\nSection: science\nPriority: optional\nMaintainer: PlotJuggler zh-CN <125791929+reliable-ly0411@users.noreply.github.com>\nDepends: %s, ca-certificates, fonts-noto-cjk\nHomepage: https://github.com/reliable-ly0411/PlotJuggler-zh-CN\nDescription: PlotJuggler zh-CN with ArduPilot DataFlash BIN support\n' "$deb_version" "$deps" > "$stage/DEBIAN/control"
dpkg-deb --root-owner-group --build "$stage" "output/PlotJuggler-${version}-24.04-amd64.deb"
test "$(dpkg-deb -f output/*.deb Version)" = "$deb_version"
test "$(dpkg-deb -f output/*.deb Architecture)" = amd64
python3 scripts/package_size_audit.py --payload package --package output/*.deb --out acceptance/package-size.json
