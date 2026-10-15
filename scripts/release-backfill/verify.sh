#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates wget lsb-release python3 xvfb xauth fonts-noto-cjk file binutils libgl1 libegl1 libxkbcommon-x11-0 libxcb-cursor0
mkdir -p build
if test "$TARGET_DISTRO" = appimage; then
  file="$(find artifacts -name '*.AppImage')"
  test -n "$file"
  chmod +x "$file"
  "$file" --appimage-extract >/dev/null
  cp squashfs-root/usr/bin/BUILD-INFO.json build/FORK-VERSION.json
  while IFS= read -r -d '' elf; do
    output="$(LD_LIBRARY_PATH="$PWD/squashfs-root/usr/lib" ldd "$elf")"
    echo "$output"
    if grep -q 'not found' <<< "$output"; then exit 1; fi
  done < <(find squashfs-root/usr/bin squashfs-root/usr/lib -type f -name '*.so*' -print0)
  readelf -h squashfs-root/usr/bin/plotjuggler | grep -E 'Machine:.*AArch64'
  APPIMAGE_EXTRACT_AND_RUN=1 xvfb-run -a python3 scripts/zh_acceptance.py --app "$file" --plugin squashfs-root/usr/bin/libDataAPBin.so --out acceptance/clean-runtime
else
  wget -q "https://packages.apache.org/artifactory/arrow/$(lsb_release --id --short | tr 'A-Z' 'a-z')/apache-arrow-apt-source-latest-$(lsb_release --codename --short).deb" -O /tmp/apache-arrow-source.deb
  apt-get install -y /tmp/apache-arrow-source.deb
  apt-get update
  file="$(find artifacts -name '*.deb')"
  apt-get install -y "$PWD/$file"
  dpkg-deb -I "$file"
  for elf in /usr/lib/plotjuggler/plotjuggler /usr/lib/plotjuggler/*.so; do
    output="$(ldd "$elf")"
    echo "$output"
    if grep -q 'not found' <<< "$output"; then exit 1; fi
  done
  cp /usr/lib/plotjuggler/BUILD-INFO.json build/FORK-VERSION.json
  readelf -h /usr/lib/plotjuggler/plotjuggler | grep -E 'Machine:.*Advanced Micro Devices X86-64'
  xvfb-run -a python3 scripts/zh_acceptance.py --app /usr/bin/plotjuggler --plugin /usr/lib/plotjuggler/libDataAPBin.so --out acceptance/clean-runtime
fi
python3 -c 'import json,os; j=json.load(open("build/FORK-VERSION.json")); assert j["commit"]==os.environ["SOURCE_SHA"]; assert j["version"]==os.environ["SOURCE_TAG"][1:]+"+upstream.3.17.2.apbin.1.g"+os.environ["SOURCE_SHA"][:12];print(j)'
cat acceptance/clean-runtime/summary.json
sha256sum "$file"
# Inspect decompressed payload and Debian metadata before any release publication.
if test "$TARGET_DISTRO" = appimage; then
  scan_root="$PWD/squashfs-root"
else
  dpkg-deb --control "$file" /tmp/package-control
  scan_root=/usr/lib/plotjuggler
fi
python3 - "$scan_root" <<'PY'
import pathlib,re,sys
roots=[pathlib.Path(sys.argv[1]),pathlib.Path('/tmp/package-control')]
pattern=re.compile(br'@[qQ][qQ][.]com')
for root in roots:
    if not root.exists(): continue
    for path in root.rglob('*'):
        if path.is_file() and pattern.search(path.read_bytes()):
            raise SystemExit('Unexpected personal contact in package: '+str(path))
print('PASS: unpacked payload and control metadata contain no QQ contact addresses')
PY
