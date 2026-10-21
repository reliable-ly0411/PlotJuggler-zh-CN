#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Stage the pinned fork payload without modifying build outputs."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import urllib.request

from version_map import versions
from collect_licenses import collect

ROOT = Path(__file__).resolve().parents[2]
FONT_REV = '523d033d6cb47f4a80c58a35753646f5c3608a78'
FONT_SHA = '2c76254f6fc379fddfce0a7e84fb5385bb135d3e399294f6eeb6680d0365b74b'
FONT_LICENSE_SHA = '6a73f9541c2de74158c0e7cf6b0a58ef774f5a780bf191f2d7ec9cc53efe2bf2'
REGISTRY_REV = '2696403e106c6960541b8da19987ece35a24597e'
CORE_PLUGINS = ['mcap-loader', 'csv-loader', 'parquet-loader', 'ulog-loader',
                'mp4-loader', 'pointcloud-3d-loader', 'dummy-streamer', 'foxglove-bridge',
                'plotjuggler-bridge', 'webrtc-client', 'ros-parser', 'protobuf-parser',
                'json-parser', 'data-tamer-parser', 'toolbox-quaternion',
                'toolbox-transform-editor', 'toolbox-mosaico', 'arrow-parser']
TOOLS = {
    'linuxdeploy': ('linuxdeploy/linuxdeploy', '8aea8da0f7f7039d2a2cecb14657d752a222a5e1d3825caeef186c82f751cdd1'),
    'linuxdeploy-plugin-qt': ('linuxdeploy/linuxdeploy-plugin-qt', 'cfc1055b2b9dbc08412b579f20990b7b41a17b61beaa5847dc9477c96c9e9617'),
    'appimagetool': ('AppImage/appimagetool', '95cbe7cce9717fce90c484e34052ee7c7f1d7635b33c12525b4776826a7d29b6'),
}


def download(url, target, expected):
    """Fail closed if a pinned upstream payload changes."""
    target.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=180) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError(f'checksum mismatch: {url}')
    target.write_bytes(data)


def stage(build, prefix, config, linux_tools):
    """Copy the exact CMake-selected DSO plus its legal and font payload."""
    build, prefix = build.resolve(), prefix.resolve()
    if prefix.exists():
        raise ValueError(f'Use an empty staging destination: {prefix}')
    binary = Path((build / f'ardupilot-package-path-{config}.txt').read_text(encoding='utf-8').strip())
    if not binary.is_file():
        raise ValueError(f'missing built BIN plugin: {binary}')
    plugin = prefix / 'lib/plotjuggler/plugins/ardupilot-dataflash'
    plugin.mkdir(parents=True)
    shutil.copy2(binary, plugin / binary.name)
    manifest = build / 'ardupilot-dataflash/ardupilot_source_plugin.pjmanifest.json'
    shutil.copy2(manifest, plugin / 'manifest.json')
    source = ROOT / '3rdparty/plotjuggler-apbin-plugins/sdk4'
    licenses = prefix / 'share/licenses'
    licenses.mkdir(parents=True)
    for name in ['LICENSE', 'COPYING.GPL3', 'LICENSE.APACHE2', 'UPSTREAM.md']:
        dest = licenses / 'ardupilot-dataflash' / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / name, dest)
    if (source / 'licenses').is_dir():
        shutil.copytree(source / 'licenses', licenses / 'ardupilot-dataflash/dependencies')
    shutil.copy2(ROOT / 'LICENSE', licenses / 'PlotJuggler-MPL-2.0.txt')
    shutil.copy2(ROOT / 'resources/fonts/NotoSans/OFL.txt', licenses / 'NotoSans-OFL.txt')
    base = f'https://raw.githubusercontent.com/notofonts/noto-cjk/{FONT_REV}/'
    download(base + 'Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf',
             prefix / 'bin/fonts/NotoSansCJKsc-Regular.otf', FONT_SHA)
    download(base + 'LICENSE', licenses / 'NotoSansCJK-OFL.txt', FONT_LICENSE_SHA)
    qt = ROOT / '.qt/6.11.1' / ('gcc_64' if linux_tools else 'msvc2022_64')
    collect(ROOT, build, qt, licenses, download)
    values = dict(x.split('=', 1) for x in (ROOT / 'versions.env').read_text(encoding='utf-8').splitlines()
                  if x and not x.startswith('#'))
    baseline = json.loads((ROOT / 'docs/localization/upstream-baseline.json').read_text(encoding='utf-8'))
    plugin_manifest = json.loads(manifest.read_text(encoding='utf-8'))
    assert plugin_manifest['license'] == baseline['ardupilot_plugin']['license'] == 'LGPL-3.0-only'
    assert plugin_manifest['version'] == baseline['ardupilot_plugin']['version']
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    tree = subprocess.check_output(['git', 'rev-parse', 'HEAD^{tree}'], cwd=ROOT, text=True).strip()
    record = {'version': values['PJ_APP_VERSION'], 'source_commit': revision, 'source_tree': tree,
              'upstream_commit': baseline['upstream_commit'], 'sdk_version': '0.34.1',
              'bin_plugin_commit': baseline['ardupilot_plugin']['commit'],
              'bin_plugin_version': plugin_manifest['version'], 'bin_plugin_license': plugin_manifest['license'],
              'registry_commit': REGISTRY_REV, 'cjk_font_sha256': FONT_SHA,
              'ifw_package_version': versions(values['PJ_APP_VERSION'])['ifw'],
              'debian_version': versions(values['PJ_APP_VERSION'])['deb']}
    locked = json.loads((ROOT / 'packaging/localization/registry-lock.json').read_text(encoding='utf-8'))
    ids = CORE_PLUGINS + (['toolbox-assistant-agent', 'ros2-topic-subscriber'] if linux_tools else [])
    record['expected_plugins'] = [f"{x['id']}={x['version']}" for x in locked['extensions'] if x['id'] in ids]
    assert len(record['expected_plugins']) == len(ids)
    record['expected_plugins'].append('ardupilot-dataflash=' + record['bin_plugin_version'])
    originals = json.loads((ROOT / 'packaging/localization/preserved-upstream-plugins.json').read_text())
    original = originals['linux-x86_64' if linux_tools else 'windows-x86_64']
    upstream = next(item for item in locked['extensions'] if item['id'] == original['id'])
    platform = 'linux-x86_64' if linux_tools else 'windows-x86_64'
    assert upstream['version'] == original['version']
    assert upstream['platforms'][platform]['checksum'] == 'sha256:' + original['archive_sha256']
    record['preserved_upstream_plugins'] = [original]
    record['localization_exceptions'] = [{'id': 'toolbox-mosaico', 'version': '1.3.0',
        'issue': 'https://github.com/reliable-ly0411/PlotJuggler-zh-CN/issues/20',
        'status': 'Original official binary; mixed Info/status text retains English to preserve user data.'}]

    out = prefix / 'share/plotjuggler4/release.json'
    out.parent.mkdir(parents=True)
    out.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    if linux_tools:
        for tool, (repo, digest) in TOOLS.items():
            name = f'{tool}-x86_64.AppImage'
            path = ROOT / 'packaging/appimage' / name
            download(f'https://github.com/{repo}/releases/download/continuous/{name}', path, digest)
            path.chmod(0o755)
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', type=Path, default=ROOT / 'build')
    p.add_argument('--prefix', type=Path, required=True)
    p.add_argument('--config', default='RelWithDebInfo')
    p.add_argument('--linux-tools', action='store_true')
    a = p.parse_args()
    stage(a.build, a.prefix, a.config, a.linux_tools)
