# SPDX-License-Identifier: MPL-2.0
"""Stage version-pinned Arrow source texts; never treat this as license closure."""
import hashlib
import json
import os
from pathlib import Path
import tarfile

RELEASES = {
    '21.0.0': '5d3f8db7e72fb9f65f4785b7a1634522e8d8e9657a445af53d4a34a3849857b5',
    '24.0.0': '9a8094d24fa33b90c672ab77fdda253f29300c8b0dd3f0b8e55a29dbd98b82c9',
    '26.0.1': '1dd1b6701d9de58a4ed82b107539682f46ef6b9e22747e18e03204125c05a987',
}
TEXT_HASHES = {
    '21.0.0': {'LICENSE.txt': '82f5f9b0e6592da7f79022fc930add132a76c56727d29813f94058157a2b2d11',
               'NOTICE.txt': 'c946470d6b024c77feebdfb686bf92a828402c0ffc27c769bca7d8bef08e1db7'},
    '24.0.0': {'LICENSE.txt': 'd1c981370f1ffd4edcdd2fb3565c8939cc40c75e24e1f92d581d04e54f0dff81',
               'NOTICE.txt': 'afd895d61a00101f6d5a41cf518c83865d815e8109e956f512a0ce4ea9738c06'},
    '26.0.1': {'LICENSE.txt': 'cd03925a27219d326d622609fbcae6567279af8b8885c33d5969a9e4ef5d7525',
               'NOTICE.txt': 'afd895d61a00101f6d5a41cf518c83865d815e8109e956f512a0ce4ea9738c06'},
}
VENDORED = Path(__file__).resolve().parents[1] / 'licenses/apache-arrow'


def stage(version, destination, archive=None):
    """Caller selects exact dependency version; archive overrides vendored text."""
    if version not in RELEASES:
        raise ValueError(f'Unsupported Arrow version: {version}')
    url = f'https://archive.apache.org/dist/arrow/arrow-{version}/apache-arrow-{version}.tar.gz'
    evidence = {'version': version, 'status': 'missing', 'closure_status': 'incomplete',
                'archive_url': url, 'archive_sha256': RELEASES[version],
                'review': 'Verify binary and recipe correspondence and all applicable transitive notices.'}
    archive = archive or os.environ.get('PLOTJUGGLER_ARROW_SOURCE_ARCHIVE')
    texts = {}
    if archive:
        digest = hashlib.sha256()
        with Path(archive).open('rb') as f:
            for block in iter(lambda: f.read(1024 * 1024), b''):
                digest.update(block)
        if digest.hexdigest() != RELEASES[version]:
            raise RuntimeError(f'Arrow {version}: source archive SHA256 mismatch')
        with tarfile.open(archive, 'r:gz') as tar:
            members = tar.getmembers()
            for name in ('LICENSE.txt', 'NOTICE.txt'):
                expected = f'apache-arrow-{version}/{name}'
                matches = [m for m in members if m.name == expected]
                if len(matches) != 1 or not matches[0].isfile() or matches[0].size > 1024 * 1024:
                    raise RuntimeError(f'Arrow {version}: invalid or missing {expected}')
                texts[name] = tar.extractfile(matches[0]).read()
        status = 'source-texts-sha256-verified'
    else:
        manifest_path = VENDORED / 'manifest.json'
        files = {name: VENDORED / version / name for name in ('LICENSE.txt', 'NOTICE.txt')}
        if not manifest_path.is_file() or any(not p.is_file() for p in files.values()):
            return evidence
        catalog = json.loads(manifest_path.read_text(encoding='utf-8'))['releases']
        expected = {'archive_url': url, 'archive_sha256': RELEASES[version], 'files': TEXT_HASHES[version]}
        if catalog.get(version) != expected:
            raise RuntimeError(f'Arrow {version}: vendored source manifest mismatch')
        texts = {name: path.read_bytes() for name, path in files.items()}
        status = 'pinned-vendored-source-texts'
    hashes = {name: hashlib.sha256(data).hexdigest() for name, data in texts.items()}
    if hashes != TEXT_HASHES[version]:
        raise RuntimeError(f'Arrow {version}: source text SHA256 mismatch')
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    for name, content in texts.items():
        target = destination / name
        if target.exists() and target.read_bytes() != content:
            raise RuntimeError(f'Arrow {version}: conflicting existing {target}')
    for name, content in texts.items():
        (destination / name).write_bytes(content)
    evidence.update(status=status, files=hashes)
    return evidence
