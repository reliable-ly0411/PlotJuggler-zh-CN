#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Host provenance follows authoritative pins, independently of plugin history."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packaging/localization'))
from host_versions import read_host_versions
from collect_licenses import collect


class HostPackageVersionsTests(unittest.TestCase):
    def fixture(self, root):
        """Use future pins so hardcoded present-day values cannot pass."""
        (root / 'versions.env').write_text('PJ_APP_VERSION=4.2.0+zh.2\nPJ_QT_VERSION=6.13.2\n', encoding='utf-8')
        (root / 'conanfile.txt').write_text('[requires]\nplotjuggler_sdk/0.40.2 # host\n[options]\nfoo/*:shared=True\nfoo/*:other=False\n', encoding='utf-8')

    def test_current_and_future_host_pins(self):
        host = read_host_versions(ROOT)
        self.assertIn(f"PJ_QT_VERSION={host['qt_version']}", (ROOT / 'versions.env').read_text(encoding='utf-8'))
        self.assertIn(f"plotjuggler_sdk/{host['sdk_version']}", (ROOT / 'conanfile.txt').read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            self.assertEqual(read_host_versions(root), {'version': '4.2.0+zh.2', 'qt_version': '6.13.2', 'sdk_version': '0.40.2'})
            for refs in ['', 'plotjuggler_sdk/[>=0.40]', 'plotjuggler_sdk/0.40.2\nplotjuggler_sdk/0.41.0']:
                (root / 'conanfile.txt').write_text('[requires]\n' + refs, encoding='utf-8')
                with self.assertRaises(ValueError):
                    read_host_versions(root)

    def test_license_collection_uses_selected_host_sdk_and_qt(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            build, qt, licenses = root/'build', root/'qt', root/'licenses'
            for path in [build, qt/'mkspecs', qt/'sbom', licenses, root/'sdk/licenses']:
                path.mkdir(parents=True)
            graph = {'graph': {'nodes': {'1': {'ref': 'plotjuggler_sdk/0.40.2#revision',
                     'context': 'host', 'package_folder': str(root/'sdk')}}}}
            (build/'conan-graph.json').write_text(json.dumps(graph), encoding='utf-8')
            (root/'sdk/licenses/LICENSE').write_text('SDK notice', encoding='utf-8')
            (qt/'mkspecs/qconfig.pri').write_text('QT_VERSION = 6.13.2\n', encoding='utf-8')
            (qt/'sbom/qtbase.spdx.json').write_text('{"packages": []}', encoding='utf-8')
            for relative in ['3rdparty/Qt-Advanced-Docking/LICENSE', 'build/_deps/qwt_upstream-src/COPYING',
                             '3rdparty/nanocdr/include/nanocdr/nanocdr.hpp']:
                path = root/relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('notice', encoding='utf-8')
            lock = root/'packaging/localization/qt-license-lock.json'
            lock.parent.mkdir(parents=True)
            lock.write_text(json.dumps({'repository':'qt/qtbase', 'commit':'pinned',
                            'files': {'LGPL-3.0-only.txt':'hash'}}), encoding='utf-8')
            collect(root, build, qt, licenses, lambda url, path, digest: path.write_text('license', encoding='utf-8'))
            self.assertIn('/qt/6.13/6.13.2/single/', (licenses/'Qt-6.13.2/SOURCE.txt').read_text(encoding='utf-8'))
            self.assertFalse((licenses/'Qt-6.11.1').exists())
            graph['graph']['nodes']['1']['ref'] = 'plotjuggler_sdk/0.34.1#old'
            (build/'conan-graph.json').write_text(json.dumps(graph), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Resolved host SDK'):
                collect(root, build, qt, licenses, None)
            graph['graph']['nodes']['1']['ref'] = 'plotjuggler_sdk/0.40.2#revision'
            (build/'conan-graph.json').write_text(json.dumps(graph), encoding='utf-8')
            (qt/'mkspecs/qconfig.pri').write_text('QT_VERSION = 6.11.1\n', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Selected Qt SDK'):
                collect(root, build, qt, licenses, None)


if __name__ == '__main__':
    unittest.main()
