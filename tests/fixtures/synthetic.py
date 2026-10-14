"""Synthetic format fixtures, NEVER captured from RX9060XT or any GPU."""
import struct


def discovery(gc=(12, 0, 0), width=4, topology=True, extra=(), binary=1, ipds=None):
    version = ipds or (4 if width == 8 else 3)
    entries = [(11, 0, gc, (0x100,)), (255, 0, (14, 0, 2), (0x200,)),
               (1, 0, (14, 0, 2), (0x300,)), (42, 0, (7, 0, 0), (0x400,)),
               (271, 0, (4, 1, 0), (0x500,))] + list(extra)
    # All non-GC versions above are arbitrary synthetic examples, not card data.
    ip = bytearray(80)
    die_off = 128 + 80
    struct.pack_into('<IHHIH', ip, 0, 0x53445049, version, 0, 0, 1)
    struct.pack_into('<HH', ip, 14, 0, die_off)
    ip[78] = int(width == 8)
    ip += struct.pack('<HH', 0, len(entries))
    for hw, inst, ver, bases in entries:
        ip += struct.pack('<HBBBBBB', hw, inst, len(bases), *ver, 0)
        ip += struct.pack('<' + ('Q' if width == 8 else 'I') * len(bases), *bases)
    struct.pack_into('<H', ip, 6, len(ip))
    gcdata = bytearray(88 if topology else 0)
    if topology:
        struct.pack_into('<IHHI', gcdata, 0, 0x4347, 1, 0, len(gcdata))
        struct.pack_into('<I', gcdata, 12, 2)  # synthetic, not real SE count
        struct.pack_into('<I', gcdata, 24, 2)  # synthetic, not real RB count
    data = bytearray(128) + ip + gcdata
    struct.pack_into('<IHHHH', data, 0, 0x28211407, binary, 0, 0, len(data))
    start = 12 if binary == 1 else 16
    if binary == 2:
        struct.pack_into('<H', data, 12, 6)
    struct.pack_into('<HHHH', data, start, 128, sum(ip) & 0xffff, len(ip), 0)
    if topology:
        struct.pack_into('<HHHH', data, start + 8, 128 + len(ip), sum(gcdata) & 0xffff, len(gcdata), 0)
    reseal(data)
    return data


def reseal(data, tables=True):
    start = 12 if struct.unpack_from('<H', data, 4)[0] == 1 else 16
    if tables:
        for i in range(6):
            off, _, size, _ = struct.unpack_from('<HHHH', data, start + i * 8)
            if off and off + size <= len(data):
                struct.pack_into('<H', data, start + i * 8 + 2, sum(data[off:off+size]) & 0xffff)
    struct.pack_into('<H', data, 8, sum(data[10:]) & 0xffff)


def msgpack(value):
    if isinstance(value, int) and 0 <= value < 128: return bytes([value])
    if isinstance(value, str):
        b=value.encode('utf-8')
        return (bytes([0xa0+len(b)]) if len(b)<32 else bytes([0xd9,len(b)])) + b
    if isinstance(value, list): return bytes([0x90+len(value)])+b''.join(msgpack(x) for x in value)
    if isinstance(value, dict): return bytes([0x80+len(value)])+b''.join(msgpack(k)+msgpack(v) for k,v in value.items())
    raise ValueError('unsupported synthetic MsgPack')


def elf(machine=0x48, metadata=True, metadata_value=None):
    data = bytearray(512)
    data[:7] = b'\x7fELF\x02\x01\x01'
    struct.pack_into('<HHI', data, 16, 3, 224, 1)
    struct.pack_into('<QQ', data, 32, 64, 128)
    struct.pack_into('<I', data, 48, machine)
    struct.pack_into('<HHHHHH', data, 52, 64, 56, 1, 64, 2, 0)
    struct.pack_into('<IIQQQQQQ', data, 64, 1, 5, 480, 256, 256, 4, 4, 256)
    if metadata:
        struct.pack_into('<I', data, 192 + 4, 7)
        if metadata_value is None:
            metadata_value={'amdhsa.version':[1,0],'amdhsa.kernels':[
                {'.name':'synthetic','.symbol':'synthetic.kd','.kernarg_segment_size':0}]}
        payload=msgpack(metadata_value)
        note_size=20+((len(payload)+3)&~3)
        struct.pack_into('<QQ', data, 192 + 24, 256, note_size)
        struct.pack_into('<III', data, 256, 7, len(payload), 32)
        data[268:275] = b'AMDGPU\0'
        data[276:276+len(payload)] = payload
    return data


def firmware(need):
    return struct.pack('<IIHHHHIIII', 36, 32, 1, 0, *need.ip[:2], 0, 4, 32, 0) + b'TEST'


def kernel_elf(machine=0x48):
    """Full synthetic symbol/descriptor layout; NOT compiler-generated ISA."""
    data=bytearray(1200);data[:7]=b'\x7fELF\x02\x01\x01'
    struct.pack_into('<HHI',data,16,3,224,1)
    struct.pack_into('<QQ',data,32,64,192);struct.pack_into('<I',data,48,machine)
    struct.pack_into('<HHHHHH',data,52,64,56,2,64,6,0)
    struct.pack_into('<IIQQQQQQ',data,64,1,4,832,0x1000,0x1000,64,64,64)
    struct.pack_into('<IIQQQQQQ',data,120,1,5,896,0x2000,0x2000,4,4,256)
    meta=msgpack({'amdhsa.version':[1,0],'amdhsa.kernels':[
        {'.name':'synthetic','.symbol':'synthetic.kd','.kernarg_segment_size':8,
         '.group_segment_fixed_size':16,'.private_segment_fixed_size':0}]})
    struct.pack_into('<III',data,608,7,len(meta),32);data[620:627]=b'AMDGPU\0'
    data[628:628+len(meta)]=meta
    def section(index,kind,flags,va,off,size,link=0,entry=0):
        struct.pack_into('<IIQQQQIIQQ',data,192+index*64,0,kind,flags,va,off,size,link,0,1,entry)
    section(1,7,0,0,608,20+((len(meta)+3)&~3))
    section(2,1,6,0x2000,896,4);section(3,1,2,0x1000,832,64)
    strings=b'\0synthetic\0synthetic.kd\0';data[928:928+len(strings)]=strings
    section(4,3,0,0,928,len(strings));section(5,2,0,0,1008,72,4,24)
    struct.pack_into('<IBBHQQ',data,1032,1,2,0,2,0x2000,4)
    struct.pack_into('<IBBHQQ',data,1056,11,1,0,3,0x1000,64)
    struct.pack_into('<III',data,832,16,0,8);struct.pack_into('<q',data,848,0x1000)
    data[896:900]=b'TEST'
    return data
