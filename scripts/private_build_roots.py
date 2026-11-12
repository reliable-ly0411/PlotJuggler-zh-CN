"""Draft: validate and scan caller-supplied, private build roots; never log them."""
import hashlib
import json
import ntpath
import posixpath
import re
from pathlib import Path

ROLES = ('source', 'build', 'cache', 'sdk')


def load_private_roots(path):
    try:
        manifest = Path(path)
        if manifest.is_symlink() or not manifest.is_file():
            raise ValueError()
        data = manifest.read_bytes()
        def unique_pairs(pairs):
            obj = {}
            for key, value in pairs:
                if key in obj:
                    raise ValueError()
                obj[key] = value
            return obj
        obj = json.loads(data.decode('utf-8'), object_pairs_hook=unique_pairs)
        if set(obj) != {'schema', 'platform', 'roots'} or obj['schema'] != 'private-build-roots/v1':
            raise ValueError()
        platform = obj['platform']
        roles = obj['roots']
        if platform not in ('windows', 'unix') or not isinstance(roles, dict) or set(roles) != set(ROLES):
            raise ValueError()
        paths = []
        for role in ROLES:
            values = roles[role]
            if role == 'cache' and isinstance(values, dict) and set(values) == {'not_applicable'} and values['not_applicable'] is True:
                continue
            if not isinstance(values, list) or (role != 'sdk' and not values):
                raise ValueError()
            for value in values:
                if not isinstance(value, str) or not value or any(ord(c) < 32 for c in value):
                    raise ValueError()
                if platform == 'windows':
                    norm = value.replace('\\', '/')
                    if not re.match(r'^[A-Za-z]:/', norm) or norm != ntpath.normpath(norm).replace('\\', '/') or norm.endswith(':/'):
                        raise ValueError()
                    norm = norm.casefold()
                else:
                    norm = value
                    if not norm.startswith('/') or norm != posixpath.normpath(norm) or norm == '/' or norm.startswith('//'):
                        raise ValueError()
                if any(x in ('.', '..') for x in norm.split('/')):
                    raise ValueError()
                paths.append(norm)
        return {'platform': platform, 'paths': tuple(paths), 'root_count': len(paths),
                'manifest_sha256': hashlib.sha256(data).hexdigest()}
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        raise ValueError('Invalid private build roots manifest') from None


def contains_private_root(data, spec):
    views = (data.decode('latin1'), data.decode('utf-8', errors='replace'),
             data.decode('utf-16le', errors='ignore'), data[1:].decode('utf-16le', errors='ignore'))
    for view in views:
        if spec['platform'] == 'windows':
            view = re.sub(r'/+', '/', view.replace('\\', '/')).casefold()
        for root in spec['paths']:
            offset = 0
            while True:
                at = view.find(root, offset)
                if at < 0:
                    break
                end = at + len(root)
                if end == len(view) or view[end] in '/\x00\r\n\t "\'=,;:)]}':
                    return True
                offset = at + 1
    return False


def stage_inventory_sha256(files):
    ordered = sorted(files, key=lambda item: item['path'])
    canonical = json.dumps(ordered, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')
    return hashlib.sha256(canonical).hexdigest()
