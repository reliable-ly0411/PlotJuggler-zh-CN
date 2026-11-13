"""Read-only COFF fixture diagnostics. No byte normalization or acceptance masks."""
import hashlib
import re
import struct


def sha(data): return hashlib.sha256(data).hexdigest()


def codeview_objects(payload, base_offset):
    """Decode C13 S_OBJNAME records, retaining original offsets and names."""
    if len(payload)<4 or struct.unpack_from('<I',payload)[0]!=4:
        raise ValueError('unsupported CodeView signature')
    result=[];offset=4
    while offset<len(payload):
        if offset+8>len(payload):raise ValueError('truncated CodeView subsection')
        kind,size=struct.unpack_from('<II',payload,offset)
        start=offset+8;end=start+size
        if end>len(payload):raise ValueError('truncated CodeView subsection body')
        if kind==0xf1:
            record=start
            while record<end:
                if record+4>end:raise ValueError('truncated CodeView symbol')
                length,typ=struct.unpack_from('<HH',payload,record)
                stop=record+2+length
                if length<2 or stop>end:raise ValueError('invalid CodeView symbol length')
                if typ==0x1101:
                    if length<7:raise ValueError('invalid S_OBJNAME')
                    name=payload[record+8:stop]
                    if b'\0' not in name:raise ValueError('unterminated S_OBJNAME')
                    name=name.split(b'\0',1)[0]
                    result.append({'record_offset':base_offset+record,
                                   'name_offset':base_offset+record+8,
                                   'object_name':name.decode('utf-8',errors='backslashreplace'),
                                   'sha256':sha(name)})
                record=stop
        offset=(end+3)&~3
    return result


def inspect_object(data):
    def take(offset, size):
        if offset < 0 or size < 0 or offset + size > len(data):
            raise ValueError('COFF field extends beyond file')
        return data[offset:offset+size]
    take(0,20)
    if data[:4] == b'\0\0\xff\xff':
        take(0,56)
        version,machine,timestamp=struct.unpack_from('<HHI',data,4)
        if version < 2 or data[12:28] != bytes.fromhex('c7a1bad1eebaa94baf20faf66aa4dcb8'):
            raise ValueError('unsupported anonymous COFF format')
        sections,symptr,symcount=struct.unpack_from('<III',data,44)
        header_size,symbol_size=56,20
        kind='bigobj'
    else:
        machine,sections,timestamp,symptr,symcount,optional,flags=struct.unpack_from('<HHIIIHH',data)
        if optional: raise ValueError('not a plain COFF object')
        header_size,symbol_size=20,18
        kind='coff'
    if machine not in (0x14c,0x8664,0xaa64): raise ValueError('unrecognized COFF machine')
    if not 0 < sections <= 65536: raise ValueError('invalid section count')
    take(header_size, sections*40)
    symbols=take(symptr,symcount*symbol_size) if symcount else b''
    strings=b''
    if symptr:
        start=symptr+symcount*symbol_size
        size=struct.unpack('<I',take(start,4))[0]
        if size < 4: raise ValueError('invalid string table size')
        strings=take(start,size)
    result={'format':kind,'bytes':len(data),'sha256':sha(data),'machine':hex(machine),
            'timestamp':timestamp,'header_bytes':header_size,'header_sha256':sha(data[:header_size]),
            'symbol_count':symcount,'symbol_offset':symptr,'symbols_sha256':sha(symbols),
            'strings_sha256':sha(strings),'sections':[],'codeview_object_names':[]}
    for i in range(sections):
        offset=header_size+i*40
        name_raw=data[offset:offset+8].split(b'\0',1)[0]
        if name_raw.startswith(b'/'):
            try: index=int(name_raw[1:])
            except ValueError: raise ValueError('invalid long section name')
            if not 4 <= index < len(strings): raise ValueError('invalid section name offset')
            name_raw=strings[index:].split(b'\0',1)[0]
        name=name_raw.decode('ascii',errors='backslashreplace')
        size,pointer,reloc,line,nreloc,nline,characteristics=struct.unpack_from('<IIIIHHI',data,offset+16)
        payload=take(pointer,size) if pointer else b''
        if name=='.debug$S':
            result['codeview_object_names'].extend(codeview_objects(payload,pointer))
        # Overflow relocation count is recorded separately; first relocation is the count.
        actual_reloc=nreloc
        if nreloc==65535 and characteristics & 0x01000000:
            actual_reloc=struct.unpack('<I',take(reloc,4))[0]
        relocs=take(reloc,actual_reloc*10) if actual_reloc else b''
        lines=take(line,nline*6) if nline else b''
        result['sections'].append({'index':i,'name':name,'header_offset':offset,'raw_offset':pointer,
                                  'raw_size':size,'sha256':sha(payload),'relocations':actual_reloc,
                                  'relocations_sha256':sha(relocs),'lines_sha256':sha(lines),
                                  'characteristics':hex(characteristics)})
    # Evidence only, not a scan exemption. Raw fixture objects remain unchanged.
    candidates=[]
    for match in re.finditer(rb'[\x20-\x7e]{6,}',data):
        value=match.group()
        if b':/' in value or b':\\' in value or b'/pathmap:' in value:
            candidates.append({'offset':match.start(),'text':value[:512].decode('ascii'),
                               'bytes':len(value),'sha256':sha(value)})
    result['path_strings']=candidates[:80]
    result['path_strings_count']=len(candidates)
    return result


def compare_objects(left,right):
    a,b=inspect_object(left),inspect_object(right)
    ranges=[];start=None
    for i in range(max(len(left),len(right))):
        different=i >= len(left) or i >= len(right) or left[i] != right[i]
        if different and start is None:start=i
        if start is not None and (not different or i==max(len(left),len(right))-1):
            end=i if not different else i+1
            ranges.append({'offset':start,'bytes':end-start});start=None
    fields=['format','bytes','machine','timestamp','header_sha256','symbol_count','symbol_offset','symbols_sha256','strings_sha256']
    changes={key:{'left':a[key],'right':b[key]} for key in fields if a[key]!=b[key]}
    return {'equal':left==right,'left':a,'right':b,'changed_header_or_tables':changes,
            'differing_ranges':ranges[:100],'differing_range_count':len(ranges),
            'changed_sections':[{'index':i,'left':x,'right':y} for i,(x,y) in enumerate(zip(a['sections'],b['sections'])) if x!=y],
            'section_count_changed':len(a['sections'])!=len(b['sections']),
            'policy':'diagnostic only; raw byte equality remains required'}
