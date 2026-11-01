#!/usr/bin/env bash
# Rebuild Ubuntu Jammy's QtCore, retaining all distro patches, with upstream
# QTBUG-92188 + QTBUG-102484. Never install into the host's system directories.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:?usage: build_qt5_core_backport.sh ABSOLUTE_OUTPUT_DIRECTORY}"
[[ "$OUT" = /* && "$OUT" != / ]]
report_failure() {
  local status=$?
  trap - ERR
  for log in "$OUT/build/"*.log; do
    [[ -f "$log" ]] || continue
    echo "==> Last build output: $log" >&2
    tail -n 80 "$log" >&2
  done
  exit "$status"
}
trap report_failure ERR
VERSION=5.15.3+dfsg-2ubuntu0.2
[[ "$(dpkg-query -W -f='${Version}' libqt5core5a)" = "$VERSION" ]] || {
  echo "Refusing to replace a QtCore version other than $VERSION; review the source pin." >&2; exit 1;
}
# Qt 5.15.3's inline-assembly qt_version_tag aliases are not compatible with
# modern Ubuntu dpkg-buildflags' automatic LTO (assembler rejects @@Qt_5.15).
# Keep all hardening flags; disable only this unsupported link optimization.
export DEB_BUILD_MAINT_OPTIONS="${DEB_BUILD_MAINT_OPTIONS:-} optimize=-lto"
MULTIARCH="$(dpkg-architecture -qDEB_HOST_MULTIARCH)"
mkdir -p "$OUT/downloads" "$OUT/source" "$OUT/build" "$OUT/stage/lib" "$OUT/stage/source"
PATCHES="$ROOT/third_party/qt5-core-backport"
BASE=https://archive.ubuntu.com/ubuntu/pool/universe/q/qtbase-opensource-src
fetch() {
  local name="$1" hash="$2"
  if [[ ! -f "$OUT/downloads/$name" ]]; then
    curl --fail --location --retry 3 "$BASE/$name" -o "$OUT/downloads/$name"
  fi
  echo "$hash  $OUT/downloads/$name" | sha256sum --check
}
fetch qtbase-opensource-src_5.15.3+dfsg.orig.tar.xz 95d8ee6a62342840e9b40edef98c0fb75535902dc0b0fb0958f7594783f1a16c
fetch qtbase-opensource-src_5.15.3+dfsg-2ubuntu0.2.debian.tar.xz 8c21ea927a240066221de1155441536e57b7cc874faee1178f75b5edff99eca5
(cd "$PATCHES"; sha256sum --check SHA256SUMS)
# Empty build/source directories are required: no stale object or partially
# applied patch may be mistaken for a validated backport.
[[ ! -f "$OUT/build/Makefile" && ! -d "$OUT/source/qtbase-everywhere-src-5.15.3" ]]
tar -xf "$OUT/downloads/qtbase-opensource-src_5.15.3+dfsg.orig.tar.xz" -C "$OUT/source"
tar -xf "$OUT/downloads/qtbase-opensource-src_5.15.3+dfsg-2ubuntu0.2.debian.tar.xz" -C "$OUT/source"
SRC="$OUT/source/qtbase-everywhere-src-5.15.3"
(
  cd "$SRC"
  while IFS= read -r patch_name; do
    case "$patch_name" in ''|'#'*) continue ;; esac
    patch --fuzz=0 -p1 < "$OUT/source/debian/patches/$patch_name"
  done < "$OUT/source/debian/patches/series"
  # Upstream's first patch has this spelling correction in its context.
  sed -i 's/possibibilies/possibilities/' src/corelib/thread/qsemaphore.cpp
  patch --fuzz=0 -p1 < "$PATCHES/qtbug-92188.patch"
  patch --fuzz=0 -p1 < "$PATCHES/qtbug-102484.patch"
  echo '08d684683fb604271e9e1a29826b4f4ff72232b44e93459b216b3c34743a9c6a  src/corelib/thread/qsemaphore.cpp' | sha256sum --check
)
(
  cd "$OUT/build"
  # Match the distro's QtCore features and installed paths. Gui/Widgets/DBus
  # are not rebuilt or replaced. ICU, glib, compression, regex and numeric
  # conversion stay system-linked just as in the Ubuntu package.
  MAKEFLAGS="-j${PJ_QT_BUILD_JOBS:-2}" "$SRC/configure" \
    -opensource -confirm-license -release -shared \
    -prefix /usr -libdir "/usr/lib/$MULTIARCH" \
    -bindir /usr/lib/qt5/bin -docdir /usr/share/qt5/doc \
    -headerdir "/usr/include/$MULTIARCH/qt5" \
    -importdir "/usr/lib/$MULTIARCH/qt5/imports" \
    -translationdir /usr/share/qt5/translations \
    -hostdatadir "/usr/lib/$MULTIARCH/qt5" -sysconfdir /etc/xdg \
    -examplesdir "/usr/lib/$MULTIARCH/qt5/examples" \
    -archdatadir "/usr/lib/$MULTIARCH/qt5" -datadir /usr/share/qt5 \
    -plugindir "/usr/lib/$MULTIARCH/qt5/plugins" \
    -no-gui -no-widgets -no-dbus -no-openssl \
    -nomake tests -nomake examples -system-zlib -system-doubleconversion \
    -system-pcre -glib -icu -no-rpath -no-feature-relocatable \
    -no-mimetype-database -no-strip -no-separate-debug-info -no-use-gold-linker \
    "QMAKE_CFLAGS=$(dpkg-buildflags --get CFLAGS) $(dpkg-buildflags --get CPPFLAGS) $(getconf LFS_CFLAGS)" \
    "QMAKE_CXXFLAGS=$(dpkg-buildflags --get CXXFLAGS) $(dpkg-buildflags --get CPPFLAGS) $(getconf LFS_CFLAGS)" \
    "QMAKE_LFLAGS=$(dpkg-buildflags --get LDFLAGS)" \
    > configure.log 2>&1
  make sub-src-qmake_all > qmake.log 2>&1
  make -C src sub-corelib -j"${PJ_QT_BUILD_JOBS:-2}" > build.log 2>&1
)
cp -a "$OUT/build/lib/libQt5Core.so"* "$OUT/stage/lib/"
# No original public/private versioned export may disappear. QtGui uses the
# private ABI too, so testing only SONAME or Qt's public version is insufficient.
python3 - "/usr/lib/$MULTIARCH/libQt5Core.so.5" "$OUT/stage/lib/libQt5Core.so.5" <<'PYABI'
import subprocess,sys
def exports(path):
    lines=subprocess.check_output(["nm", "-D", "--defined-only", path], text=True).splitlines()
    return {parts[-1] for line in lines if len(parts:=line.split())==3 and parts[-2]!="A"}
missing=exports(sys.argv[1])-exports(sys.argv[2])
if missing:
    raise SystemExit("Backport lost original QtCore ABI symbols: " + repr(sorted(missing)))
print("Original QtCore exports, including private ABI, retained")
PYABI
# ABI compatibility is not enough: QLibraryInfo also controls translations,
# plugins and global settings. Compare every installed path with distro Qt.
cat > "$OUT/build/library-paths.cpp" <<'CPP'
#include <QCoreApplication>
#include <QLibraryInfo>
#include <iostream>
int main(int argc, char **argv) {
  QCoreApplication app(argc, argv);
  const QLibraryInfo::LibraryLocation paths[] = {
    QLibraryInfo::PrefixPath, QLibraryInfo::DocumentationPath,
    QLibraryInfo::HeadersPath, QLibraryInfo::LibrariesPath,
    QLibraryInfo::LibraryExecutablesPath, QLibraryInfo::BinariesPath,
    QLibraryInfo::PluginsPath, QLibraryInfo::ImportsPath,
    QLibraryInfo::Qml2ImportsPath, QLibraryInfo::ArchDataPath,
    QLibraryInfo::DataPath, QLibraryInfo::TranslationsPath,
    QLibraryInfo::ExamplesPath, QLibraryInfo::TestsPath, QLibraryInfo::SettingsPath};
  for (auto path : paths)
    std::cout << int(path) << ':' << QLibraryInfo::location(path).toStdString() << '\n';
}
CPP
g++ -std=c++11 -fPIC -I"/usr/include/$MULTIARCH/qt5" \
  -I"/usr/include/$MULTIARCH/qt5/QtCore" "$OUT/build/library-paths.cpp" \
  -lQt5Core -o "$OUT/build/library-paths"
env -u LD_LIBRARY_PATH "$OUT/build/library-paths" > "$OUT/stage/source/distro-library-paths.txt"
LD_LIBRARY_PATH="$OUT/stage/lib" "$OUT/build/library-paths" > "$OUT/stage/source/backport-library-paths.txt"
diff -u "$OUT/stage/source/distro-library-paths.txt" "$OUT/stage/source/backport-library-paths.txt"
# Keep debug symbols separate, but never remove the dependency's public ABI.
objcopy --only-keep-debug "$OUT/stage/lib/libQt5Core.so.5.15.3" "$OUT/stage/lib/Qt5Core.debug"
strip --strip-unneeded "$OUT/stage/lib/libQt5Core.so.5.15.3"
objcopy --add-gnu-debuglink="$OUT/stage/lib/Qt5Core.debug" "$OUT/stage/lib/libQt5Core.so.5.15.3"
# Corresponding source is staged alongside the library, not merely a link to
# a moving upstream branch. Candidate packages include this source bundle.
cp "$OUT/downloads/"*.tar.xz "$OUT/stage/source/"
mkdir -p "$OUT/stage/source/scripts" "$OUT/stage/source/third_party/qt5-core-backport"
cp "$PATCHES/"* "$OUT/stage/source/third_party/qt5-core-backport/"
cp "$0" "$OUT/stage/source/scripts/"
cp "$SRC/"LICENSE* "$OUT/stage/source/"
cp "$OUT/build/config.summary" "$OUT/stage/source/"
(cd "$OUT/stage/lib"; sha256sum libQt5Core.so.5.15.3 > SHA256SUMS)
printf '%s\n' "$VERSION + QTBUG-92188 + QTBUG-102484" > "$OUT/stage/source/VERSION"
ldd "$OUT/stage/lib/libQt5Core.so.5.15.3" | tee "$OUT/stage/source/dependencies.txt"
! grep -q 'not found' "$OUT/stage/source/dependencies.txt"
echo "Backported QtCore staged at $OUT/stage (system Qt unchanged)."
