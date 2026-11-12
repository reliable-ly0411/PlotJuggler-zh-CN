"""Compare portable ZIP file set and bytes to the staged Windows payload."""
import argparse
import hashlib
from pathlib import Path
import zipfile
from windows_ifw_payload import inventory

def verify(stage, archive):
    expected = inventory(Path(stage))
    with zipfile.ZipFile(archive) as z:
        items = [x for x in z.infolist() if not x.is_dir()]
        names = [x.filename.replace('\\', '/') for x in items]
        if len(set(n.casefold() for n in names)) != len(names) or set(names) != set(expected):
            raise ValueError('portable ZIP file set mismatch')
        for item, name in zip(items, names):
            h = hashlib.sha256(); count = 0
            with z.open(item) as stream:
                for data in iter(lambda: stream.read(1024 * 1024), b''):
                    h.update(data); count += len(data)
            if (count, h.hexdigest()) != expected[name]:
                raise ValueError('portable ZIP content mismatch')
    return len(expected)
if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--stage', required=True);p.add_argument('--zip',required=True)
    args = p.parse_args()
    try:
        print('Portable ZIP staged files verified:', verify(args.stage,args.zip))
    except (OSError, ValueError, zipfile.BadZipFile):
        raise SystemExit('Portable ZIP verification failed') from None
