# SPDX-License-Identifier: MPL-2.0
"""Prepare exact pinned source/resource inputs; never run downloaded applications."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

p = argparse.ArgumentParser()
p.add_argument('--out', required=True)
a = p.parse_args()
root = Path(__file__).resolve().parents[1]
baseline = '3117288ce8d710bde4f7a86ca5ed5240ebb1c301'
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()

def read(rev, name):
    return ((root / name).read_bytes() if rev is None else
            subprocess.check_output(['git', 'show', rev + ':' + name], cwd=root))

report = {'baseline': baseline, 'candidate': head, 'datasets': {}}
for label, revision in [('zh3', baseline), ('zh4', None)]:
    output = Path(a.out).resolve() / label
    output.mkdir(parents=True, exist_ok=True)
    catalog = json.loads(read(revision, 'plotjuggler_app/resources/memes/zh_CN.json'))
    names = [f'meme_{i:02d}.jpg' for i in range(106)] + ['zh_CN.json']
    names += (sorted(catalog['assets']) if revision is None else
              sorted({entry['asset'] for entry in catalog['images'] if entry.get('asset')}))
    resource = ET.Element('RCC')
    prefix = ET.SubElement(resource, 'qresource', prefix='/')
    hashes = {}
    for name in names:
        assert '..' not in name and '\\' not in name and not name.startswith('/')
        data = read(revision, 'plotjuggler_app/resources/memes/' + name)
        path = output / 'resources/memes' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        ET.SubElement(prefix, 'file').text = 'resources/memes/' + name
        hashes[name] = hashlib.sha256(data).hexdigest()
    ET.ElementTree(resource).write(output / 'images.qrc', encoding='utf-8', xml_declaration=True)
    for name in ('localized_meme.cpp', 'localized_meme.h'):
        (output / name).write_bytes(read(revision, 'plotjuggler_app/' + name))
    report['datasets'][label] = hashes
assert all(report['datasets']['zh3'][f'meme_{i:02d}.jpg'] ==
           report['datasets']['zh4'][f'meme_{i:02d}.jpg'] for i in range(106))
Path(a.out, 'inputs.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('Prepared exact baseline/candidate image inputs; all 106 English hashes match.')
