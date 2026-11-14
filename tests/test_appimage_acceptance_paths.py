"""AppImage provenance and fail-closed symlink diagnostics regression checks."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('launcher_acceptance', ROOT/'scripts/launcher_acceptance.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

class Paths(unittest.TestCase):
    def test_owned_extraction_and_exact_child(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); image = root/'fixture.AppImage'
            image.write_text('#!/bin/sh\n[ "$1" = --appimage-extract ] || exit 9\nmkdir -p squashfs-root/usr/bin\nprintf app > squashfs-root/usr/bin/plotjuggler\nprintf entry > squashfs-root/AppRun\n')
            image.chmod(0o700)
            evidence = root/'evidence'; evidence.mkdir()
            with m.prepare_launcher(image, evidence/'case', 5) as (entry, child, fingerprint):
                self.assertFalse(entry.is_relative_to(evidence))
                self.assertEqual(entry.name, 'AppRun'); self.assertEqual(fingerprint, m.digest(image))
                m.verify_child(str(child), child, m.digest(child))
                impostor = root/'plotjuggler'; impostor.write_bytes(child.read_bytes())
                with self.assertRaises(AssertionError): m.verify_child(str(impostor), child, m.digest(child))
                old = m.digest(child); child.write_text('modified')
                with self.assertRaises(AssertionError): m.verify_child(str(child), child, old)
                extracted = entry.parent.parent
            self.assertFalse(extracted.exists())
            self.assertEqual(list(evidence.iterdir()), [])
            with self.assertRaisesRegex(RuntimeError, 'test abort'):
                with m.prepare_launcher(image, evidence/'case', 5) as (entry, _, _):
                    aborted = entry.parent.parent
                    raise RuntimeError('test abort')
            self.assertFalse(aborted.exists())
            self.assertEqual(list(evidence.iterdir()), [])

    def test_symlink_failures_are_diagnostic_and_closed(self):
        for kind in ['missing', 'escape', 'loop', 'private']:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                base=Path(tmp); payload=base/'payload'; payload.mkdir(); out=base/'audit.json'
                external=base/'external';external.write_text('outside')
                target={'missing':'missing-file','escape':'../external','loop':'bad-link',
                        'private':'/home/PrivateOwner/do-not-disclose'}[kind]
                (payload/'bad-link').symlink_to(target)
                manifest=base/'roots.json'
                manifest.write_text(json.dumps({'schema':'private-build-roots/v1','platform':'unix',
                    'roots':{'source':[str(ROOT),'/home/PrivateOwner'],'build':[str(base)],'cache':{'not_applicable':True},'sdk':[]}}))
                p=subprocess.run([sys.executable,str(ROOT/'scripts/package_size_audit.py'),'--payload',str(payload),
                    '--out',str(out),'--private-build-roots',str(manifest)],capture_output=True,text=True)
                self.assertNotEqual(p.returncode,0); self.assertFalse(out.exists())
                report=json.loads(Path(str(out)+'.failure.json').read_text())
                self.assertEqual(report['path'],'bad-link')
                self.assertEqual(report['reason'],{'missing':'target-missing-or-loop','escape':'target-outside-payload',
                    'loop':'target-missing-or-loop','private':'target-metadata-rejected'}[kind])
                self.assertNotIn('/home/PrivateOwner',p.stdout+p.stderr+json.dumps(report))

if __name__=='__main__': unittest.main()
