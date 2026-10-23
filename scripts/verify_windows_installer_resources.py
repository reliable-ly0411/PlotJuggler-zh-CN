#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Probe synthetic IFW languages, then isolated synthetic install/replacement.

The language fixture never installs. The separate upgrade fixture installs only
its freshly generated inert receipt payload, through the production GUI slot.
Windows-only integration smoke. Requires PowerShell, 7z and a Qt kit (Linguist,
rcc and qtbase_zh_CN.qm). Downloads only the existing hash-pinned official IFW
helper's package. This is not application packaging or installation acceptance.
"""
import base64
import gzip
import argparse
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
MARKER = 'pj_zh_cn_resource_smoke_marker.txt'


def run(command, *, cwd=None):
    result = subprocess.run([str(arg) for arg in command], cwd=cwd, check=True,
                            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300)
    print(result.stdout, end='')
    if result.stderr:
        print(result.stderr, file=sys.stderr, end='')
    return result.stdout + result.stderr


def stage_inputs(root, temporary):
    """Copy real metadata unchanged except required version/date placeholders."""
    installer = root / 'packaging/installer'
    packages = temporary / 'packages'
    component = packages / 'io.plotjuggler.application'
    shutil.copytree(installer / 'packages/io.plotjuggler.application/meta', component / 'meta')
    script = component / 'meta/installscript.qs'
    source = script.read_text(encoding='utf-8')
    marker = '__PJ_REPLACEMENT_HELPER_GZIP__'
    if source.count(marker) != 1:
        raise ValueError('Replacement supervisor placeholder missing or duplicated')
    helper = base64.b64encode(gzip.compress((installer / 'replacement_guard.ps1').read_bytes(), mtime=0)).decode('ascii')
    script.write_text(source.replace(marker, helper), encoding='utf-8')
    config = temporary / 'config.xml'
    shutil.copy2(installer / 'config.xml', config)
    for path in (config, component / 'meta/package.xml'):
        path.write_text(path.read_text(encoding='utf-8').replace('__PJ_VERSION__', '0.0.0')
                        .replace('__PJ_RELEASE_DATE__', '2000-01-01'), encoding='utf-8')
    data = component / 'data'
    data.mkdir()
    (data / 'SYNTHETIC-NOT-AN-APPLICATION.txt').write_text(
        'Resource smoke fixture only. Never install this fixture. No application payload.\n',
        encoding='utf-8')
    translations = temporary / 'translations'
    translations.mkdir()
    (translations / MARKER).write_text('Synthetic resource embedding probe.\n', encoding='utf-8')
    resource = ET.Element('RCC')
    group = ET.SubElement(resource, 'qresource', prefix='/translations_new')
    for name in ('ifw_zh_CN.qm', 'qt_zh_CN.qm', MARKER):
        ET.SubElement(group, 'file').text = name
    qrc = translations / 'translations.qrc'
    ET.ElementTree(resource).write(qrc, encoding='utf-8', xml_declaration=True)
    return config, packages, component / 'meta', translations, qrc


def verify_pe_resources(path):
    content = path.read_bytes()
    if len(content) < 64 or content[:2] != b'MZ':
        raise ValueError('Fixture is not a PE executable')
    pe_offset = struct.unpack_from('<I', content, 0x3c)[0]
    if content[pe_offset:pe_offset + 4] != b'PE\0\0':
        raise ValueError('Fixture PE signature missing')
    # Qt RCC name tables use UTF-16BE, independent of payload compression.
    # The unique marker proves this additional qresource was not silently dropped.
    for name in ('ifw_zh_CN.qm', 'qt_zh_CN.qm', MARKER):
        if name.encode('utf-16-be') not in content:
            raise ValueError(f'Embedded translation resource name missing: {name}')


def smoke(lrelease, rcc=None, qtbase=None):
    if sys.platform != 'win32':
        raise RuntimeError('This integration smoke requires Windows; no GUI emulation is used')
    lrelease = Path(lrelease).resolve(strict=True)
    kit = lrelease.parent.parent
    if rcc:
        rcc = Path(rcc)  # Explicit tool paths never silently fall back.
    else:
        rcc = kit / 'bin/rcc.exe'
        if not rcc.is_file():
            rcc = kit / 'libexec/rcc.exe'
    rcc = rcc.resolve(strict=True)
    qtbase = (Path(qtbase) if qtbase else kit / 'translations/qtbase_zh_CN.qm').resolve(strict=True)
    shell = shutil.which('pwsh') or shutil.which('powershell')
    if not shell:
        raise RuntimeError('PowerShell is required')
    # A space in this root exercises argument boundaries in every real tool call.
    with tempfile.TemporaryDirectory(prefix='pj installer resource smoke ') as directory:
        temporary = Path(directory)
        tools = temporary / 'IFW tools'
        run([shell, '-NoProfile', '-NonInteractive', '-File',
             ROOT / 'packaging/installer/install_ifw.ps1', '-Destination', tools])
        version = run([tools / 'bin/installerbase.exe', '--version'])
        if 'IFW Version: 4.10.0, built with Qt ' not in version:
            raise RuntimeError('Pinned IFW runtime version mismatch')
        config, packages, meta, translations, qrc = stage_inputs(ROOT, temporary)
        run([lrelease, ROOT / 'packaging/installer/translations/ifw_zh_CN.ts',
             meta / 'zh_CN.ts', '-qm', translations / 'ifw_zh_CN.qm'])
        shutil.copy2(qtbase, translations / 'qt_zh_CN.qm')
        qm_magic = bytes.fromhex('3cb86418caef9c95cd211cbf60a1bddd')
        for catalog in (translations / 'ifw_zh_CN.qm',
                        translations / 'qt_zh_CN.qm'):
            if not catalog.read_bytes().startswith(qm_magic):
                raise RuntimeError(f'Invalid compiled Qt catalog: {catalog}')
        compiled = translations / 'translations.rcc'
        run([rcc, '--binary', qrc, '-o', compiled])
        if not compiled.read_bytes().startswith(b'qres'):
            raise RuntimeError('Qt rcc did not produce a binary resource')
        fixture = temporary / 'SYNTHETIC-DO-NOT-INSTALL.exe'
        run([tools / 'bin/binarycreator.exe', '--offline-only', '-r', qrc,
             '-c', config, '-p', packages, fixture], cwd=temporary)
        verify_pe_resources(fixture)
        print('PASS: real IFW fixture PE embeds both Chinese catalogs and resource marker.')
        from windows_installer_live import probe_gui
        probe_gui(fixture, temporary, shell, ROOT / 'scripts/windows_installer_live.qs.in')
        print('PASS: language GUI mechanism only; no payload installed by the language probe.')
        from windows_installer_upgrade import probe_upgrade
        probe_upgrade(tools / 'bin/binarycreator.exe', qrc, shell, stage_inputs)
        print('PASS: synthetic mechanisms only. Full application/human acceptance is separate.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lrelease', required=True, help='Selected Qt kit lrelease.exe')
    parser.add_argument('--rcc', help='Optional explicit matching Qt rcc.exe')
    parser.add_argument('--qtbase-catalog', help='Optional explicit qtbase_zh_CN.qm')
    args = parser.parse_args()
    smoke(args.lrelease, args.rcc, args.qtbase_catalog)


if __name__ == '__main__':
    main()
