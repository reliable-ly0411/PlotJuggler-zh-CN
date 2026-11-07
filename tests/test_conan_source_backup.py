"""Exercise the actual 4.x CI source-cache seeding block without network access."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github/workflows/zh-4x-ci.yml'
FFMPEG_SHA = 'cf38e0e28c7e5605942c4a77755349b0145804a397af37eb1fb4c77cb237f635'


def seed_script():
    workflow = WORKFLOW.read_text(encoding='utf-8')
    marker = 'python - "$conan_home/global.conf" "$cache_dir" <<\'PY\'\n'
    script = workflow.split(marker, 1)[1].split('\n          PY\n', 1)[0]
    return textwrap.dedent(script)


class ConanSourceBackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.seeds = self.root / '.github/conan/source-backup'
        self.seeds.mkdir(parents=True)
        data = b'local synthetic source archive\n'
        self.sha = hashlib.sha256(data).hexdigest()
        self.blob = self.seeds / self.sha
        self.blob.write_bytes(data)
        self.sidecar = self.blob.with_suffix('.json')
        self.sidecar.write_text(json.dumps({'references': {'fixture/1.0': ['https://example.invalid/source']}}), encoding='utf-8')
        (self.seeds / 'README.md').write_text('Not a cache entry.\n', encoding='utf-8')
        self.conf = self.root / 'global.conf'
        self.conf.write_text('tools.build:jobs=2\ncore.sources:download_cache=/old\ncore.sources:download_urls=["origin"]\n', encoding='utf-8')
        self.cache = self.root / 'cache'

    def run_seed(self):
        return subprocess.run([sys.executable, '-', str(self.conf), str(self.cache)],
                              input=seed_script(), text=True, cwd=self.root,
                              capture_output=True, check=False)

    def assert_rejected(self, message):
        before = self.conf.read_bytes()
        result = self.run_seed()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(message, result.stderr)
        self.assertEqual(self.conf.read_bytes(), before)
        self.assertFalse(self.cache.exists())

    def test_valid_seed_and_configuration_are_idempotent(self):
        for _ in range(2):
            result = self.run_seed()
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.cache / 's' / self.sha).read_bytes(), self.blob.read_bytes())
        self.assertEqual((self.cache / 's' / (self.sha + '.json')).read_bytes(), self.sidecar.read_bytes())
        self.assertEqual(len(list((self.cache / 's').iterdir())), 2)
        conf = self.conf.read_text(encoding='utf-8')
        self.assertIn('tools.build:jobs=2\n', conf)
        self.assertEqual(conf.count('core.sources:download_cache='), 1)
        self.assertEqual(conf.count('core.sources:download_urls='), 1)
        self.assertIn('["origin", "https://c3i.jfrog.io/', conf)

    def test_corrupt_source_is_rejected_before_copy(self):
        self.blob.write_bytes(b'corrupted archive')
        self.assert_rejected('SHA256 mismatch')

    def test_missing_sidecar_is_rejected_before_copy(self):
        self.sidecar.unlink()
        self.assert_rejected('FileNotFoundError')

    def test_invalid_sidecar_is_rejected_before_copy(self):
        self.sidecar.write_text('not json', encoding='utf-8')
        self.assert_rejected('JSONDecodeError')

    def test_empty_references_are_rejected_before_copy(self):
        self.sidecar.write_text('{"references": {}}', encoding='utf-8')
        self.assert_rejected('metadata missing references')

    def test_ffmpeg_seed_matches_exact_locked_recipe(self):
        path = ROOT / '.github/conan/source-backup' / FFMPEG_SHA
        self.assertEqual(path.stat().st_size, 12036420)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), FFMPEG_SHA)
        metadata = json.loads(path.with_suffix('.json').read_text(encoding='utf-8'))
        self.assertEqual(metadata['references']['ffmpeg/9.0.1'],
                         ['https://ffmpeg.org/releases/ffmpeg-9.0.1.tar.xz'])
        lock = (ROOT / 'conan.lock').read_text(encoding='utf-8')
        self.assertIn('ffmpeg/9.0.1#e1b7a11d16ed758bcbc0771208d32597', lock)


if __name__ == '__main__':
    unittest.main()
