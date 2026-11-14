# SPDX-License-Identifier: MPL-2.0
"""Review prototype: pinned public ELF records; never a module-wide exemption."""
import hashlib
import json
from pathlib import Path
import struct

# Digest pins the entire review manifest, including source identity and ranges.
MANIFEST_SHA256 = '09f00122768c4748430c17098135ddcd3c3dea68f906826dec000bc9afd02304'
MANIFEST = Path(__file__).resolve().parents[1] / 'tests/data/linux-public-elf-records.json'


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _soname(data):
    """Return SONAME only for bounded, little-endian ELF64 x86-64 ET_DYN."""
    try:
        if data[:7] != b'\x7fELF\x02\x01\x01' or struct.unpack_from('<HH', data, 16) != (3, 62):
            return None
        phoff, = struct.unpack_from('<Q', data, 32)
        entsize, count = struct.unpack_from('<HH', data, 54)
        if entsize != 56 or not count or phoff + entsize * count > len(data):
            return None
        loads, dyn = [], None
        for i in range(count):
            ptype, _, off, vaddr, _, filesz, _, _ = struct.unpack_from('<IIQQQQQQ', data, phoff + i * entsize)
            if off + filesz > len(data): return None
            if ptype == 1: loads.append((vaddr, off, filesz))
            if ptype == 2:
                if dyn is not None: return None
                dyn = (off, filesz)
        if dyn is None: return None
        tags = {}
        for pos in range(dyn[0], dyn[0] + dyn[1] - 15, 16):
            tag, value = struct.unpack_from('<qQ', data, pos)
            if tag == 0: break
            if tag in (5, 10, 14):
                if tag in tags: return None
                tags[tag] = value
        if not all(x in tags for x in (5, 10, 14)) or tags[14] >= tags[10]: return None
        for va, off, size in loads:
            delta = tags[5] - va
            if delta >= 0 and delta + tags[10] <= size:
                table = data[off + delta:off + delta + tags[10]]
                end = table.find(b'\0', tags[14])
                if end < 0: return None
                return table[tags[14]:end].decode('ascii')
    except (ValueError, UnicodeDecodeError, struct.error, OverflowError):
        pass
    return None


def reviewed_spans(data, name):
    """Return only approved rule/match spans; any mismatch means no exemption."""
    try:
        raw = MANIFEST.read_bytes()
        if _sha(raw) != MANIFEST_SHA256: return set()
        rec = json.loads(raw)['records'].get(name)
        if not rec or _sha(data) != rec['elf_sha256'] or _soname(data) != rec['soname']:
            return set()
        spans = set()
        for item in rec['nul_records']:
            start, end = item['start'], item['end']
            a, b = item['match_start'], item['match_end']
            if not (0 < start <= a < b <= end < len(data)):
                return set()
            if data[start-1] != 0 or data[end] != 0 or b'\0' in data[start:end]:
                return set()
            if _sha(data[start:end]) != item['record_sha256']:
                return set()
            spans.add((item['rule'], a, b))
        if len(spans) != len(rec['nul_records']): return set()
        return spans
    except (OSError, ValueError, KeyError, TypeError, IndexError, json.JSONDecodeError):
        return set()
