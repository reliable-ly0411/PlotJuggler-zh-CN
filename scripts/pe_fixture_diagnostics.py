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
    mappings=[]
    for i in range(count):
        off=pe+24+optional+i*40
        u('<40s',off)
        name=raw[off:off+8].rstrip(b'\0').decode('ascii',errors='replace')
        size, start=u('<II',off+16)
        virtual,=u('<I',off+12)
        mappings.append((virtual,size,start))
        if start+size>len(raw): raise ValueError('section outside PE')
        sections.append({'name':name,'offset':start,'bytes':size,'sha256':hashlib.sha256(raw[start:start+size]).hexdigest()})
    def rva(value, length=1):
        for virtual,size,start in mappings:
            if virtual<=value and value+length<=virtual+size: return start+value-virtual
        raise ValueError('RVA outside raw sections')
    debug=[]; exports=[]
    if optional:
        if optional<112 or u('<H',pe+24)[0]!=0x20b: raise ValueError('fixture requires PE32+')
        directories=u('<I',pe+24+108)[0]
        if 112+directories*8>optional: raise ValueError('directory exceeds optional header')
        if directories>6:
            addr,size=u('<II',pe+24+112+6*8)
            if size%28: raise ValueError('invalid debug directory size')
            if size:
                off=rva(addr,size)
                for n in range(size//28):
                    stamp=u('<I',off+n*28+4)[0];kind=u('<I',off+n*28+12)[0]
                    debug.append({'timestamp':stamp,'timestamp_offset':off+n*28+4,'type':kind})
        if directories:
            addr,size=u('<II',pe+24+112)
            if size:
                off=rva(addr,40); count=u('<I',off+24)[0];names=u('<I',off+32)[0]
                if count>10000: raise ValueError('too many exports')
                table=rva(names,count*4)
                for n in range(count):
                    pos=rva(u('<I',table+n*4)[0]);end=raw.find(b'\0',pos,pos+1024)
                    if end<0: raise ValueError('unterminated export')
                    exports.append(raw[pos:end].decode('ascii'))
    def present(value):
        # Include both path separator forms and both common string encodings.
        forms={value,value.replace('\\','/'),value.replace('/','\\')}
        return any(s.encode(enc) in raw for s in forms for enc in ('utf-8','utf-16le'))
    return {'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'machine':machine,
            'timestamp':timestamp,'timestamp_offset':pe+8,'debug_directory':debug,'exports':exports,'characteristics':flags,'sections':sections,
            'forbidden_paths_found':[p for p in forbidden if present(p)],
            'object_names_found':[p for p in object_names if present(p)],'byte_rewriting':False}
