#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Collect notices from the exact resolved graph and selected Qt SDK."""
import hashlib
import json
from pathlib import Path
import re
import shutil


def collect(root, build, qt, licenses, download):
    """Retain full dependency notices; never substitute a license identifier."""
    graph = json.loads((build / 'conan-graph.json').read_text(encoding='utf-8'))['graph']['nodes']
    components = []
    for node in graph.values():
        ref = node.get('ref')
        folder = node.get('package_folder')
        if not ref or not folder or node.get('context') == 'build':
            continue
        identity = ref.split('#')[0]
        source = Path(folder) / 'licenses'
        if not source.is_dir():
            # System wrapper packages distribute no code in this package.
            if '/system' in identity:
                components.append({'component': identity, 'kind': 'system dependency; not bundled'})
                continue
            raise ValueError(f'Conan package missing license texts: {identity}')
        destination = licenses / 'conan' / re.sub(r'[^A-Za-z0-9._-]', '_', identity)
        shutil.copytree(source, destination)
        components.append({'component': identity, 'reference': ref, 'license': node.get('license'),
                           'homepage': node.get('homepage'), 'notices': destination.relative_to(licenses).as_posix()})
    for name, source in [('Qt-Advanced-Docking', root / '3rdparty/Qt-Advanced-Docking/LICENSE'),
                         ('Qwt-6.3.0', build / '_deps/qwt_upstream-src/COPYING'),
                         ('nanocdr', root / '3rdparty/nanocdr/include/nanocdr/nanocdr.hpp')]:
        if not source.is_file() and name == 'nanocdr':
            candidates = list((root / '3rdparty/nanocdr').rglob('*.hpp'))
            if not candidates:
                raise ValueError('nanocdr source notice is absent')
            source = candidates[0]
        if not source.is_file():
            raise ValueError(f'Missing bundled dependency notice: {source}')
        destination = licenses / name
        destination.mkdir(parents=True)
        if name == 'nanocdr':
            # Keep the complete header: its attribution and Apache notice are in
            # the source, and this header-only dependency has no LICENSE file.
            shutil.copy2(source, destination / source.name)
        else:
            shutil.copy2(source, destination / source.name)
        components.append({'component': name, 'notices': name})
    qt_dest = licenses / 'Qt-6.11.1'
    qt_dest.mkdir()
    lock = json.loads((root / 'packaging/localization/qt-license-lock.json').read_text(encoding='utf-8'))
    for name, digest in lock['files'].items():
        download(f"https://raw.githubusercontent.com/{lock['repository']}/{lock['commit']}/LICENSES/{name}",
                 qt_dest / name, digest)
    for item in lock.get('additional_files', []):
        download(f"https://raw.githubusercontent.com/{item['repository']}/{item['commit']}/LICENSES/{item['name']}",
                 qt_dest / item['name'], item['sha256'])
    sboms = list((qt / 'sbom').glob('*.spdx.json'))
    if not sboms:
        raise ValueError('Selected Qt SDK has no SPDX notices')
    notice_text = []
    for source in sboms:
        shutil.copy2(source, qt_dest / source.name)
        document = json.loads(source.read_text(encoding='utf-8'))
        notice_text.append(source.name)
        for package in document.get('packages', []):
            notice_text.extend([str(package.get('name', '')), str(package.get('copyrightText', '')),
                                str(package.get('licenseDeclared', '')), str(package.get('licenseConcluded', '')),
                                str(package.get('licenseComments', '')), str(package.get('comment', '')),
                                str(package.get('downloadLocation', ''))])
        for extracted in document.get('hasExtractedLicensingInfos', []):
            notice_text.extend([str(extracted.get('licenseId', '')), str(extracted.get('extractedText', ''))])
    (qt_dest / 'THIRD-PARTY-NOTICES.txt').write_text('\n\n'.join(notice_text), encoding='utf-8')
    (qt_dest / 'SOURCE.txt').write_text(
        'Qt 6.11.1 source: https://download.qt.io/official_releases/qt/6.11/6.11.1/single/\n'
        'Qt libraries are dynamically linked and remain replaceable.\n', encoding='utf-8')
    # The generic LGPL text is the official unmodified Qt license, not the
    # historical PJ3 installer license with a different attribution header.
    shutil.copy2(qt_dest / 'LGPL-3.0-only.txt', licenses / 'Qt-LGPL.txt')
    files = [{'path': p.relative_to(licenses).as_posix(), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
             for p in sorted(licenses.rglob('*')) if p.is_file()]
    (licenses / 'DEPENDENCIES.json').write_text(json.dumps({'components': components, 'files': files},
                                                         indent=2) + '\n', encoding='utf-8')
