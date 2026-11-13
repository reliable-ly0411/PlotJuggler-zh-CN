# SPDX-License-Identifier: MPL-2.0
"""Exercise the media workflow's APT package provenance block offline."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / '.github/workflows/zh-4x-ci.yml').read_text(encoding='utf-8')
MEDIA = WORKFLOW.split('  windows-native-media:\n', 1)[1].split('\n  windows-native-test-build:', 1)[0]
BLOCK = MEDIA.split('          python3 - "$evidence" "$version" <<\'PY\'\n', 1)[1].split('          PY\n', 1)[0]
SCRIPT = textwrap.dedent(BLOCK)


class AptProvenanceTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.evidence = Path(temp.name)
        (self.evidence / 'downloads').mkdir()
        self.package = self.evidence / 'downloads/ffmpeg_7%3a1.0_amd64.deb'
        self.package.write_bytes(b'synthetic package bytes')
        self.version = '7:1.0'
        self.fields = {'Package': 'ffmpeg', 'Version': self.version,
                       'Filename': 'pool/universe/f/ffmpeg/ffmpeg_1.0_amd64.deb',
                       'Size': str(self.package.stat().st_size),
                       'SHA256': hashlib.sha256(self.package.read_bytes()).hexdigest(),
                       'SHA512': hashlib.sha512(self.package.read_bytes()).hexdigest()}
        self.write_show(self.fields)
        self.write_uri('SHA512', self.fields['SHA512'])

    def write_show(self, fields):
        (self.evidence / 'apt-show.txt').write_text(
            ''.join(f'{key}: {value}\n' for key, value in fields.items()) + '\n', encoding='utf-8')

    def write_uri(self, algorithm, checksum):
        (self.evidence / 'apt-download-uri.txt').write_text(
            f"'http://archive.ubuntu.com/ubuntu/{self.fields['Filename']}' {self.package.name} "
            f"{self.fields['Size']} {algorithm}:{checksum}\n", encoding='utf-8')

    def run_block(self, version=None):
        return subprocess.run([sys.executable, '-c', SCRIPT, str(self.evidence), version or self.version],
                              capture_output=True, text=True)

    def test_sha256_and_sha512_uri_checksums_both_pass(self):
        for algorithm in ('SHA256', 'SHA512'):
            with self.subTest(algorithm=algorithm):
                self.write_uri(algorithm, self.fields[algorithm])
                result = self.run_block()
                self.assertEqual(result.returncode, 0, result.stderr)
                provenance = json.loads((self.evidence / 'tool-provenance.json').read_text(encoding='utf-8'))
                self.assertEqual(provenance['sha256'], self.fields['SHA256'])
                self.assertEqual(provenance['version'], self.version)
                self.assertEqual((self.evidence / 'ffmpeg-deb-path.txt').read_text(encoding='utf-8').strip(), str(self.package))

    def test_wrong_uri_hash_and_unknown_algorithm_are_rejected(self):
        for algorithm in ('SHA256', 'SHA512'):
            with self.subTest(algorithm=algorithm):
                self.write_uri(algorithm, '0' * len(self.fields[algorithm]))
                self.assertNotEqual(self.run_block().returncode, 0)
                self.assertFalse((self.evidence / 'tool-provenance.json').exists())
        self.write_uri('MD5Sum', hashlib.md5(self.package.read_bytes()).hexdigest())
        self.assertNotEqual(self.run_block().returncode, 0)

    def test_signed_apt_show_hash_and_size_must_match(self):
        for key, value in [('SHA256', '0' * 64), ('SHA512', '0' * 128), ('Size', '1')]:
            with self.subTest(field=key):
                self.write_show(dict(self.fields, **{key: value}))
                self.assertNotEqual(self.run_block().returncode, 0)
                self.assertFalse((self.evidence / 'tool-provenance.json').exists())

    def test_version_and_filename_must_match_signed_apt_show(self):
        self.assertNotEqual(self.run_block('7:1.1').returncode, 0)
        self.write_show(dict(self.fields, Filename='pool/universe/f/ffmpeg/other.deb'))
        self.assertNotEqual(self.run_block().returncode, 0)

    def test_archive_bytes_and_printed_filename_must_match(self):
        original = self.package.read_bytes()
        self.package.write_bytes(b'x' * len(original))
        self.assertNotEqual(self.run_block().returncode, 0)
        self.package.write_bytes(original)
        uri = (self.evidence / 'apt-download-uri.txt').read_text(encoding='utf-8')
        (self.evidence / 'apt-download-uri.txt').write_text(uri.replace(self.package.name, 'other.deb'), encoding='utf-8')
        self.assertNotEqual(self.run_block().returncode, 0)

    def test_apt_update_and_signature_verification_still_precede_provenance(self):
        block = 'python3 - "$evidence" "$version" <<\'PY\''
        self.assertLess(MEDIA.index('apt-get "${opts[@]}" update'), MEDIA.index(block))
        self.assertLess(MEDIA.index('gpgv --keyring'), MEDIA.index(block))
        self.assertIn('signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg', MEDIA)
        self.assertNotIn('--allow-insecure', MEDIA)


if __name__ == '__main__':
    unittest.main()
