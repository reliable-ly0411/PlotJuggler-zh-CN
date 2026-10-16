# SPDX-License-Identifier: MPL-2.0
"""Check only the four proposed additions against the exact official 3.17.2 tree."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

p = argparse.ArgumentParser()
p.add_argument('--root', required=True)
p.add_argument('--out', required=True)
a = p.parse_args()
root = Path(a.root).resolve()
base = '034a5cc919909aebb124e0dc1abbe2029c3eed0f'

def git(*args):
    return subprocess.check_output(['git', '-C', str(root), *args]).decode('utf-8').strip()

assert git('rev-parse', 'HEAD') == base
expected = {'plotjuggler_app/resource_image.h', 'plotjuggler_app/resource_image.cpp',
            'tests/resource_image_variant_test.cpp', 'tests/resource_image_variant/CMakeLists.txt'}
changes = [line.split('\t', 1) for line in git('diff', '--cached', '--name-status').splitlines()]
assert {path for status, path in changes} == expected and all(status == 'A' for status, path in changes)
protected = ['CMakeLists.txt', 'plotjuggler_app/CMakeLists.txt', 'plotjuggler_app/main.cpp',
             'plotjuggler_app/resource.qrc', 'LICENSE.md']
for name in protected:
    original = subprocess.check_output(['git', '-C', str(root), 'show', base+':'+name])
    assert (root/name).read_bytes().replace(b'\r\n', b'\n') == original.replace(b'\r\n', b'\n')
images = []
for line in git('ls-tree', '-r', base, '--', 'plotjuggler_app/resources/memes').splitlines():
    fields, name = line.split('\t', 1)
    if name.endswith('.jpg'):
        blob = fields.split()[2]
        data = (root/name).read_bytes()
        assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest() == blob
        images.append({'path': name, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)})
assert len(images) == 106
report = {'official_tag': '3.17.2', 'official_sha': base, 'patch_changes': changes,
          'protected_application_files_unchanged': protected,
          'default_application_build_graph_unchanged': True,
          'default_locale_and_resource_files_unchanged': True,
          'english_images_byte_identical': 106, 'english_images': images,
          'scope': 'Four additive Core/Gui/test files; standalone test target only; no translated data, parser or application target changes.'}
out = Path(a.out)
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
print('PASS: exact official 3.17.2; only four additive files; application/default locale/QRC and all 106 English JPEG bytes unchanged.')
