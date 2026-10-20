#!/usr/bin/env bash
# SPDX-License-Identifier: MPL-2.0
# Execute only the downloaded original artifacts in a bare supported distro.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive PJ_DISABLE_TELEMETRY=1 APPIMAGE_EXTRACT_AND_RUN=1
cd /pkg
sha256sum -c SHA256SUMS-Linux.txt
# First prove Depends and uninstall behavior using the upstream smoke contract.
bash /src/packaging/deb/smoke_test.sh
# Reinstall the same immutable package for language/BIN acceptance.
apt-get install -y -qq /pkg/*.deb >/dev/null
apt-get install -y -qq python3 imagemagick >/dev/null
real=/src/3rdparty/plotjuggler-apbin-plugins/tests/logs/00000001.BIN
xvfb-run -a --server-args='-screen 0 1440x1000x24' python3 /src/packaging/localization/verify_package.py \
  --prefix /opt/plotjuggler4 --executable /usr/bin/plotjuggler4 --real-bin "$real" --output /reports/deb --expected-source "$EXPECTED_SOURCE_SHA" --expected-version "$EXPECTED_VERSION" --capture
mkdir /tmp/appimage
cp /pkg/*.AppImage /tmp/appimage/app.AppImage
chmod +x /tmp/appimage/app.AppImage
cd /tmp/appimage
./app.AppImage --appimage-extract >/dev/null
xvfb-run -a --server-args='-screen 0 1440x1000x24' python3 /src/packaging/localization/verify_package.py \
  --prefix /tmp/appimage/squashfs-root/usr --executable /tmp/appimage/app.AppImage \
  --real-bin "$real" --output /reports/appimage --expected-source "$EXPECTED_SOURCE_SHA" --expected-version "$EXPECTED_VERSION" --capture
cd /pkg
sha256sum -c SHA256SUMS-Linux.txt
