#!/usr/bin/env bash
set -euo pipefail
actual="$(git rev-parse HEAD)"
test "$actual" = "$SOURCE_SHA"
test "$(git rev-parse "$SOURCE_TAG^{}")" = "$SOURCE_SHA"
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y build-essential cmake ninja-build python3 python3-dev qtbase5-dev qttools5-dev-tools qttools5-dev libqt5svg5-dev libqt5websockets5-dev libqt5opengl5-dev libqt5x11extras5-dev libqt5serialport5-dev libprotoc-dev ccache libmosquitto-dev ca-certificates lsb-release wget libcurl4-openssl-dev libzmq3-dev libprotobuf-dev protobuf-compiler libgrpc++-dev pkg-config xvfb xauth fonts-noto-cjk dpkg-dev file patchelf
wget -q "https://packages.apache.org/artifactory/arrow/$(lsb_release --id --short | tr 'A-Z' 'a-z')/apache-arrow-apt-source-latest-$(lsb_release --codename --short).deb" -O /tmp/apache-arrow-source.deb
apt-get install -y /tmp/apache-arrow-source.deb
apt-get update
apt-get install -y libarrow-dev libarrow-flight-dev libparquet-dev
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DPJ_INSTALLATION="$TARGET_DISTRO" -DPJ_PLUGINS_DIRECTORY=bin -DBUILD_TESTING=OFF
cmake --build build --parallel 2
python3 tests/check_translations.py --fresh
if test -f tests/check_memes.py; then python3 tests/check_memes.py; fi
python3 tests/check_version.py
QT_QPA_PLATFORM=offscreen ctest --test-dir build --output-on-failure --no-tests=error
xvfb-run -a python3 scripts/zh_acceptance.py --app build/bin/plotjuggler --plugin build/bin/libDataAPBin.so --out acceptance/source
version="$(python3 -c 'import json;print(json.load(open("build/FORK-VERSION.json"))["version"])')"
test "$version" = "${SOURCE_TAG#v}+upstream.3.17.2.apbin.1.g${SOURCE_SHA:0:12}"
test -f build/bin/libDataLoadParquet.so
test -f build/bin/libToolboxMosaico.so
mkdir -p output
if test "$TARGET_DISTRO" = appimage; then
  test "$(uname -m)" = aarch64
  ARCH=aarch64 BUILD_DIR="$PWD/build" SKIP_BUILD=1 APPIMAGE_EXTRACT_AND_RUN=1 bash appimage/build_appimage.sh
  # linuxdeploy excludes these desktop libraries by default. Bundle them explicitly
  # so a minimal ARM64 host does not need a separately installed Qt font stack.
  extra=()
  for lib in libharfbuzz.so.0 libfreetype.so.6 libfontconfig.so.1 libgmp.so.10 libcom_err.so.2 libexpat.so.1 libuuid.so.1 libX11-xcb.so.1 libSM.so.6 libICE.so.6 libgpg-error.so.0; do
    path="$(ldconfig -p | awk -v name="$lib" '$1 == name && !found {path=$NF; found=1} END {print path}')"
    test -n "$path"
    extra+=(--library "$path")
  done
  rm PlotJuggler-aarch64.AppImage
  ARCH=aarch64 APPIMAGE_EXTRACT_AND_RUN=1 ./linuxdeploy-aarch64.AppImage --appimage-extract-and-run --appdir AppDir "${extra[@]}" --output appimage
  name="PlotJuggler-${version}-aarch64.AppImage"
  mv PlotJuggler-aarch64.AppImage "output/$name"
  readelf -h AppDir/usr/bin/plotjuggler | grep -E 'Machine:.*AArch64'
  readelf -h AppDir/usr/bin/libDataAPBin.so | grep -E 'Machine:.*AArch64'
  APPIMAGE_EXTRACT_AND_RUN=1 xvfb-run -a python3 scripts/zh_acceptance.py --app "output/$name" --plugin AppDir/usr/bin/libDataAPBin.so --out acceptance/packaged
  python3 -c 'import json,os; j=json.load(open("AppDir/usr/bin/BUILD-INFO.json")); assert j["commit"]==os.environ["SOURCE_SHA"];print(j)'
else
  test "$(dpkg --print-architecture)" = amd64
  stage="$PWD/package"
  mkdir -p "$stage/usr/lib/plotjuggler" "$stage/usr/bin" "$stage/DEBIAN" "$stage/usr/share/applications" "$stage/usr/share/icons/hicolor/512x512/apps" "$stage/usr/share/icons/hicolor/scalable/apps"
  cp build/bin/plotjuggler build/bin/*.so "$stage/usr/lib/plotjuggler/"
  python3 scripts/stage_fork_notices.py "$stage/usr/lib/plotjuggler"
  ln -s ../lib/plotjuggler/plotjuggler "$stage/usr/bin/plotjuggler"
  cp io.plotjuggler.PlotJuggler.desktop "$stage/usr/share/applications/"
  cp plotjuggler.png "$stage/usr/share/icons/hicolor/512x512/apps/"
  cp plotjuggler.svg "$stage/usr/share/icons/hicolor/scalable/apps/"
  # A native Debian prerelease sorts before 3.18.0. The full original SemVer is embedded unchanged.
  deb_version="${version/-zh./~zh.}"
  mkdir -p debian
  printf 'Source: plotjuggler\nSection: science\nPriority: optional\nMaintainer: PlotJuggler zh-CN <125791929+reliable-ly0411@users.noreply.github.com>\n\nPackage: plotjuggler\nArchitecture: any\nDescription: PlotJuggler zh-CN\n' > debian/control
  args=()
  for elf in "$stage"/usr/lib/plotjuggler/plotjuggler "$stage"/usr/lib/plotjuggler/*.so; do
    readelf -h "$elf" | grep -E 'Machine:.*Advanced Micro Devices X86-64'
    args+=("-e$elf")
  done
  deps="$(dpkg-shlibdeps -O -l"$stage/usr/lib/plotjuggler" "${args[@]}" | sed -n 's/^shlibs:Depends=//p')"
  test -n "$deps"
  # Arrow 26 on trixie omits this transitive runtime requirement from its Depends.
  if test "$TARGET_DISTRO" = trixie; then deps="$deps, opentelemetry-cpp"; fi
  printf 'Package: plotjuggler\nVersion: %s\nArchitecture: amd64\nSection: science\nPriority: optional\nMaintainer: PlotJuggler zh-CN <125791929+reliable-ly0411@users.noreply.github.com>\nDepends: %s, ca-certificates, fonts-noto-cjk\nHomepage: https://github.com/reliable-ly0411/PlotJuggler-zh-CN\nDescription: PlotJuggler zh-CN with ArduPilot DataFlash BIN support\n' "$deb_version" "$deps" > "$stage/DEBIAN/control"
  name="PlotJuggler-${version}-${TARGET_DISTRO}-amd64.deb"
  dpkg-deb --root-owner-group --build "$stage" "output/$name"
  test "$(dpkg-deb -f "output/$name" Version)" = "$deb_version"
  test "$(dpkg-deb -f "output/$name" Architecture)" = amd64
  dpkg-deb -I "output/$name"
  apt-get install -y "$PWD/output/$name"
  xvfb-run -a python3 scripts/zh_acceptance.py --app /usr/bin/plotjuggler --plugin /usr/lib/plotjuggler/libDataAPBin.so --out acceptance/packaged
  python3 -c 'import json,os; j=json.load(open("/usr/lib/plotjuggler/BUILD-INFO.json")); assert j["commit"]==os.environ["SOURCE_SHA"];print(j)'
fi
sha256sum output/*
cat acceptance/packaged/summary.json
# Checkout remains exactly at the release source: packaging does not rewrite product sources.
git diff --exit-code
