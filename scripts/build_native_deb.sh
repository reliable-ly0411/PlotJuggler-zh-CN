#!/usr/bin/env bash
# SPDX-License-Identifier: MPL-2.0
# Native Debian/Ubuntu payload, dependency generation and compression; no release writes.
set -euo pipefail
distribution="${PJ_DEB_DISTRO:?Set PJ_DEB_DISTRO to 24.04, bookworm or trixie}"
case "$distribution" in 24.04|bookworm|trixie) ;; *) exit 2 ;; esac
. /etc/os-release
test "$VERSION_CODENAME" = "${distribution/24.04/noble}"
test "$(dpkg --print-architecture)" = amd64
version="$(python3 -c 'import json; print(json.load(open("build/FORK-VERSION.json"))["version"])')"
stage="$PWD/package"
mkdir -p "$stage/usr/lib/plotjuggler" "$stage/usr/bin" "$stage/DEBIAN" \
  "$stage/usr/share/applications" "$stage/usr/share/icons/hicolor/512x512/apps" \
  "$stage/usr/share/icons/hicolor/scalable/apps" package-metadata/debian output
cp build/bin/plotjuggler build/bin/plotjuggler-launcher build/bin/*.so "$stage/usr/lib/plotjuggler/"
# Only copied product binaries are rewritten. The build tree remains intact.
python3 scripts/linux_stage_elfs.py normalize --root "$stage/usr/lib/plotjuggler" \
  --build-bin "$PWD/build/bin" --layout deb --report acceptance/linux-deb-stage-elfs.json
python3 scripts/linux_stage_elfs.py audit --root "$stage" \
  --private-root "$PWD" --private-root "$(realpath build)" --private-root "${RUNNER_TEMP:-$PWD}" \
  --report acceptance/linux-deb-private-paths.json
python3 scripts/stage_fork_notices.py "$stage/usr/lib/plotjuggler"
ln -s ../lib/plotjuggler/plotjuggler "$stage/usr/bin/plotjuggler"
ln -s ../lib/plotjuggler/plotjuggler-launcher "$stage/usr/bin/plotjuggler-launcher"
cp io.plotjuggler.PlotJuggler.desktop "$stage/usr/share/applications/"
cp plotjuggler.png "$stage/usr/share/icons/hicolor/512x512/apps/"
cp plotjuggler.svg "$stage/usr/share/icons/hicolor/scalable/apps/"
printf 'Source: plotjuggler\nSection: science\nPriority: optional\nMaintainer: PlotJuggler zh-CN <125791929+reliable-ly0411@users.noreply.github.com>\n\nPackage: plotjuggler\nArchitecture: any\nDescription: PlotJuggler zh-CN\n' > package-metadata/debian/control
args=()
for elf in "$stage"/usr/lib/plotjuggler/plotjuggler "$stage"/usr/lib/plotjuggler/plotjuggler-launcher "$stage"/usr/lib/plotjuggler/*.so; do
  readelf -h "$elf" | grep -E 'Machine:.*Advanced Micro Devices X86-64'
  args+=("-e$elf")
done
deps="$(cd package-metadata && dpkg-shlibdeps -O -l"$stage/usr/lib/plotjuggler" "${args[@]}" | sed -n 's/^shlibs:Depends=//p')"
test -n "$deps"
deb_version="${version/-/\~}"
dpkg --validate-version "$deb_version"
printf 'Package: plotjuggler\nVersion: %s\nArchitecture: amd64\nSection: science\nPriority: optional\nMaintainer: PlotJuggler zh-CN <125791929+reliable-ly0411@users.noreply.github.com>\nDepends: %s, ca-certificates, fonts-noto-cjk\nHomepage: https://github.com/reliable-ly0411/PlotJuggler-zh-CN\nDescription: PlotJuggler zh-CN with ArduPilot DataFlash BIN support\n' "$deb_version" "$deps" > "$stage/DEBIAN/control"
dpkg-deb --root-owner-group --build "$stage" "output/PlotJuggler-${version}-${distribution}-amd64.deb"
test "$(dpkg-deb -f output/*.deb Version)" = "$deb_version"
test "$(dpkg-deb -f output/*.deb Architecture)" = amd64
private_roots="${PJ_PRIVATE_BUILD_ROOTS:?A private build roots manifest is required}"
python3 scripts/package_size_audit.py --payload package --package output/*.deb --private-build-roots "$private_roots" --out acceptance/package-size.json
extracted="$(mktemp -d)"
trap 'rm -rf "$extracted"' EXIT
dpkg-deb -x output/*.deb "$extracted"
python3 scripts/package_size_audit.py --payload "$extracted" --package output/*.deb --private-build-roots "$private_roots" --out acceptance/deb-extracted-size.json
