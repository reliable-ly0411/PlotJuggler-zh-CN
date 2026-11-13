"""Read-only PE fixture inspection. Never rewrites or masks bytes."""
import hashlib
import struct


def inspect_pe(raw, forbidden=(), object_names=()):
    def u(fmt, off):
        if off < 0 or off + struct.calcsize(fmt) > len(raw):
            raise ValueError('truncated PE')
        return struct.unpack_from(fmt, raw, off)
    if raw[:2] != b'MZ': raise ValueError('missing DOS signature')
    pe, = u('<I', 60)
    if raw[pe:pe+4] != b'PE\0\0': raise ValueError('missing PE signature')
    machine, count, timestamp, _, _, optional, flags = u('<HHIIIHH', pe+4)
    sections=[]
    for i in range(count):
        off=pe+24+optional+i*40
        u('<40s',off)
        name=raw[off:off+8].rstrip(b'\0').decode('ascii',errors='replace')
        size, start=u('<II',off+16)
        if start+size>len(raw): raise ValueError('section outside PE')
        sections.append({'name':name,'offset':start,'bytes':size,'sha256':hashlib.sha256(raw[start:start+size]).hexdigest()})
    def present(value):
        # Include both path separator forms and both common string encodings.
        forms={value,value.replace('\\','/'),value.replace('/','\\')}
        return any(s.encode(enc) in raw for s in forms for enc in ('utf-8','utf-16le'))
    return {'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'machine':machine,
            'timestamp':timestamp,'characteristics':flags,'sections':sections,
            'forbidden_paths_found':[p for p in forbidden if present(p)],
            'object_names_found':[p for p in object_names if present(p)],'byte_rewriting':False}
