"""CPU-only reference implementation. No device IO, drivers or GPU libraries.

New code: BSD-3-Clause, see ../LICENSE. Binary layouts are documented by
upstream/references/linux-discovery.h and LLVM ELF.h at provenance.json pins.
Fixtures are synthetic. OfflineReady never authorizes hardware initialization.
"""
from dataclasses import dataclass, field
from enum import Enum
import struct


class Invalid(ValueError):
    pass


class Target(Enum):
    UNKNOWN = 0
    GFX1200 = 0x48
    GFX1201 = 0x4E


@dataclass(frozen=True)
class Profile:
    vendor: int
    device: int
    revision: int | None
    asic: str
    target: Target
    expected_gc: tuple[int, int, int]
    revision_verified: bool = False
    capabilities: frozenset = frozenset()


def identify(vendor, device, revision=None):
    if revision is not None and (not isinstance(revision, int) or not 0 <= revision <= 255):
        raise Invalid("revision_range")
    if vendor != 0x1002:
        raise Invalid("unknown_vendor")
    if device == 0x7590:
        return Profile(vendor, device, revision, "Navi44", Target.GFX1200, (12, 0, 0))
    if device in (0x7550, 0x7551):
        return Profile(vendor, device, revision, "Navi48", Target.GFX1201, (12, 0, 1))
    raise Invalid("unknown_device")


def bounded(total, offset, length):
    # Subtraction form translates safely to fixed-width C++ size_t.
    if not all(isinstance(x, int) for x in (total, offset, length)):
        raise Invalid("range_type")
    if min(total, offset, length) < 0 or max(total, offset, length) > 0xFFFFFFFFFFFFFFFF:
        raise Invalid("range_overflow")
    if offset > total or length > total - offset:
        raise Invalid("out_of_bounds")


def read(data, offset, fmt):
    bounded(len(data), offset, struct.calcsize(fmt))
    return struct.unpack_from(fmt, data, offset)


@dataclass(frozen=True)
class Ip:
    hw_id: int
    instance: int
    version: tuple
    bases: tuple


@dataclass(frozen=True)
class Discovery:
    binary_version: tuple
    ipds_version: int
    address_bits: int
    ips: tuple
    gc_info: tuple | None  # SE, RB per SE: described data, not active topology.
    unknown_ids: tuple


def parse_discovery(data):
    """Parse one binary at offset zero; caller may slice a ROM offline.

    Supports binary v1.0..1.3/v2.0 and IPDS v3/v4, one die.
    Other versions fail closed. Unknown IPs are retained, not made capable.
    64-bit register bases remain 64-bit and are never truncated.
    """
    if not isinstance(data, (bytes, bytearray)):
        raise Invalid("buffer_type")
    magic, major, minor, checksum, size = read(data, 0, "<IHHHH")
    if magic != 0x28211407:
        raise Invalid("binary_magic")
    if (major == 1 and minor > 3) or (major == 2 and minor != 0) or major not in (1, 2):
        raise Invalid("binary_version")
    bounded(len(data), 0, size)
    start = 12 if major == 1 else 16
    count = 6 if major == 1 else read(data, 12, "<H")[0]
    if not 1 <= count <= 6:
        raise Invalid("table_count")
    if major == 2 and read(data, 14, '<H')[0]:
        raise Invalid('binary_reserved')
    bounded(size, start, count * 8)
    if sum(data[10:size]) & 0xFFFF != checksum:
        raise Invalid("binary_checksum")
    tables = []
    occupied = []
    for index in range(count):
        off, check, length, reserved = read(data, start + 8 * index, "<HHHH")
        if reserved:
            raise Invalid('table_reserved')
        if off == length == check == 0:
            tables.append(None)
            continue
        if not off or not length or off < start + count * 8:
            raise Invalid("table_range")
        bounded(size, off, length)
        if any(off < end and begin < off + length for begin, end in occupied):
            raise Invalid("table_overlap")
        occupied.append((off, off + length))
        if sum(data[off:off + length]) & 0xFFFF != check:
            raise Invalid("table_checksum")
        tables.append((off, length))
    if not tables[0]:
        raise Invalid("missing_ipds")
    off, length = tables[0]
    bounded(length, 0, 80)
    sig, version, declared, table_id, dies = read(data, off, "<IHHIH")
    if sig != 0x53445049 or table_id != 0:
        raise Invalid("ipds_magic_or_id")
    if version not in (3, 4):
        raise Invalid("ipds_version")
    if declared != length or dies != 1:
        raise Invalid("ipds_size_or_die_count")
    flags = data[off + 78]
    if data[off + 79] or flags & ~1 or (version == 3 and flags):
        raise Invalid("ipds_flags")
    width = 8 if flags & 1 else 4
    die_id, die_off = read(data, off + 14, "<HH")
    if die_off < off + 80:
        raise Invalid("die_offset")
    bounded(off + length, die_off, 4)
    actual_id, nips = read(data, die_off, "<HH")
    if actual_id != die_id or not 1 <= nips <= 256:
        raise Invalid("die_id_or_ip_count")
    p = die_off + 4
    ips, seen = [], set()
    for _ in range(nips):
        bounded(off + length, p, 8)
        hw, instance, nb, a, b, c, _flags = read(data, p, "<HBBBBBB")
        if not 1 <= nb <= 16:
            raise Invalid("base_count")
        bounded(off + length, p + 8, nb * width)
        bases = read(data, p + 8, "<" + ("Q" if width == 8 else "I") * nb)
        if any(base > 0xFFFFFFFFFFFFFFFF // 4 for base in bases):
            raise Invalid("register_address_overflow")
        key = (hw, instance)
        if key in seen:
            raise Invalid("duplicate_ip")
        seen.add(key)
        ips.append(Ip(hw, instance, (a, b, c), bases))
        p += 8 + nb * width
    topology = None
    if len(tables) > 1 and tables[1]:
        gc, glen = tables[1]
        bounded(glen, 0, 28)
        gid, ga, gb, gsize = read(data, gc, "<IHHI")
        # Support complete base layouts only; later minor extensions unverified.
        if gid != 0x4347 or (ga, gb) not in ((1, 0), (2, 0)):
            raise Invalid("gc_info_version")
        minimum = 88 if ga == 1 else 80
        if gsize != glen or glen < minimum:
            raise Invalid("gc_info_size")
        se = read(data, gc + 12, "<I")[0]
        rb = read(data, gc + 24, "<I")[0]
        if not se or not rb:
            raise Invalid("gc_info_zero")
        topology = (se, rb)
    known = {1, 11, 34, 40, 41, 42, 108, 150, 255, 271}
    unknown = tuple(sorted({ip.hw_id for ip in ips if ip.hw_id not in known}))
    return Discovery((major, minor), version, width * 8, tuple(ips), topology, unknown)


def validate_discovery(profile, discovery):
    gc = [ip for ip in discovery.ips if ip.hw_id == 11 and ip.instance == 0]
    if len(gc) != 1 or gc[0].version != profile.expected_gc:
        raise Invalid("gc_profile_mismatch")
    if discovery.gc_info is None:
        raise Invalid("topology_unknown")
    return True  # Only a subset, never validates actual active CU/BAR geometry.


@dataclass(frozen=True)
class FirmwareNeed:
    block: str
    ip: tuple
    component: str


def firmware_requirements(profile, discovery):
    validate_discovery(profile, discovery)
    needs = []
    # Linux IP-derived naming reference, not a claim Navi44 IPs were captured.
    for hw, block, components in (
        (11, "gc", ("pfp", "me", "mec", "rlc", "imu", "mes", "mes1")),
        (255, "psp", ("sos", "ta")), (1, "smu", ("smu",)),
        (42, "sdma", ("sdma",)), (271, "dcn", ("dmub",))):
        entries = [ip for ip in discovery.ips if ip.hw_id == hw and ip.instance == 0]
        if len(entries) != 1:
            raise Invalid("required_ip_missing:" + block)
        for component in components:
            needs.append(FirmwareNeed(block, entries[0].version, component))
    return tuple(needs)


@dataclass(frozen=True)
class FirmwareBlob:
    need: FirmwareNeed
    data: bytes
    provenance: str  # 'synthetic' does not mean AMD signature verified.


def validate_firmware(needs, blobs):
    """AMDGPU common header validation only; no signature verification/load.

    Only header v1.0 is supported. Component-specific bodies remain unverified.
    Unknown versions fail closed. Synthetic blobs prove parser behavior only.
    """
    found = {}
    for blob in blobs:
        if blob.need in found:
            raise Invalid("duplicate_firmware")
        found[blob.need] = blob
    for need in needs:
        if need not in found:
            raise Invalid("required_firmware_missing")
        data = found[need].data
        size, header, major, minor, ia, ib, _uv, payload, offset, crc = read(data, 0, "<IIHHHHIIII")
        if (major, minor) != (1, 0):
            raise Invalid("firmware_header_version")
        if size != len(data) or header < 32 or header > size or offset < header or not payload:
            raise Invalid("firmware_size")
        bounded(size, offset, payload)
        if (ia, ib) != need.ip[:2]:
            raise Invalid("firmware_ip_mismatch")
        if need.component not in ('pfp','me','mec','rlc','imu','mes','mes1','sos','ta','smu','sdma','dmub'):
            raise Invalid("firmware_component_unsupported")
        # Do not invent a CRC convention or claim signature checks.
        if crc != 0:
            raise Invalid("firmware_crc_unverified")
    return True


def decode_metadata(data, node_budget=512):
    """Bounded MsgPack subset; unsupported encodings explicitly rejected."""
    used = 0
    def parse(p, depth=0):
        nonlocal used
        if depth > 16:
            raise Invalid("metadata_depth")
        bounded(len(data), p, 1)
        if used >= node_budget:
            raise Invalid('metadata_budget')
        used += 1
        tag, p = data[p], p + 1
        if tag < 0x80:
            return tag, p
        if 0xA0 <= tag <= 0xBF or tag in (0xD9, 0xDA, 0xDB):
            if tag >= 0xA0 and tag <= 0xBF:
                length = tag & 31
            else:
                width = {0xD9: 1, 0xDA: 2, 0xDB: 4}[tag]
                bounded(len(data), p, width)
                length = int.from_bytes(data[p:p+width], 'big'); p += width
            bounded(len(data), p, length)
            try: text = data[p:p+length].decode('utf-8')
            except UnicodeError: raise Invalid("metadata_utf8") from None
            return text, p + length
        is_map = 0x80 <= tag <= 0x8F or tag in (0xDE, 0xDF)
        is_array = 0x90 <= tag <= 0x9F or tag in (0xDC, 0xDD)
        if is_map or is_array:
            if tag < 0xA0:
                count = tag & 15
            else:
                width = 2 if tag in (0xDC, 0xDE) else 4
                bounded(len(data), p, width)
                count = int.from_bytes(data[p:p+width], 'big'); p += width
            if count > 4096:
                raise Invalid("metadata_count")
            result = {} if is_map else []
            for _ in range(count):
                value, p = parse(p, depth + 1)
                if is_map:
                    if not isinstance(value, str) or value in result:
                        raise Invalid("metadata_key")
                    item, p = parse(p, depth + 1); result[value] = item
                else: result.append(value)
            return result, p
        if tag in (0xCC, 0xCD, 0xCE, 0xCF):
            width = {0xCC:1, 0xCD:2, 0xCE:4, 0xCF:8}[tag]
            bounded(len(data), p, width)
            return int.from_bytes(data[p:p+width], 'big'), p + width
        raise Invalid("metadata_encoding_unsupported")
    value, end = parse(0)
    if end != len(data) or not isinstance(value, dict):
        raise Invalid("metadata_envelope")
    version = value.get('amdhsa.version')
    kernels = value.get('amdhsa.kernels')
    if not isinstance(version, list) or len(version) != 2 or not all(type(x) is int for x in version):
        raise Invalid("metadata_version_missing")
    if version[0] != 1 or not 0 <= version[1] <= 2:
        raise Invalid("metadata_version_unsupported")
    if not isinstance(kernels, list) or not kernels:
        raise Invalid("metadata_kernels_missing")
    for kernel in kernels:
        if not isinstance(kernel, dict) or not all(isinstance(kernel.get(x), str) and kernel[x] for x in ('.name', '.symbol')):
            raise Invalid("metadata_kernel_identity_missing")
        if type(kernel.get('.kernarg_segment_size')) is not int or not 0 <= kernel['.kernarg_segment_size'] <= 0xffffffff:
            raise Invalid("metadata_kernarg_missing")
    return value


def validate_elf(data, target, node_budget=512):
    """Strict offline ELF envelope; not AMD metadata/shader execution proof."""
    if target not in (Target.GFX1200, Target.GFX1201):
        raise Invalid("unknown_target")
    if len(data)>16<<20:raise Invalid("elf_input_budget")
    bounded(len(data), 0, 64)
    if data[:7] != b"\x7fELF\x02\x01\x01":
        raise Invalid("elf_ident")
    etype, machine, version = read(data, 16, "<HHI")
    if etype != 3 or machine != 224 or version != 1:
        raise Invalid("elf_type_machine_version")
    flags = read(data, 48, "<I")[0]
    if flags & 0xFF != target.value:
        raise Invalid("elf_target_mismatch")
    eh, phsize, phnum, shsize, shnum = read(data, 52, "<HHHHH")
    phoff, shoff = read(data, 32, "<QQ")
    if eh != 64 or phsize != 56 or shsize != 64 or not phnum or not shnum:
        raise Invalid("elf_tables_missing")
    if phnum+shnum>4096:raise Invalid("elf_table_budget")
    bounded(len(data), phoff, phsize * phnum)
    bounded(len(data), shoff, shsize * shnum)
    # Validate the complete file envelope before any semantic metadata lookup.
    for i in range(shnum):
        p = shoff + i * shsize
        if read(data, p + 4, '<I')[0] != 8:
            off, size = read(data, p + 24, '<QQ')
            bounded(len(data), off, size)
    for i in range(shnum):
        s=shoff+i*shsize;kind=read(data,s+4,'<I')[0];size=read(data,s+32,'<Q')[0]
        link=read(data,s+40,'<I')[0];stride=read(data,s+56,'<Q')[0]
        if kind in (2,11) and size:
            if stride<24 or size%stride or link>=shnum or read(data,shoff+link*shsize+4,'<I')[0]!=3: raise Invalid('elf_symbols_invalid')
        if kind in (4,9) and size:
            expected=24 if kind==4 else 16
            if stride!=expected or size%stride or link>=shnum or read(data,s+44,'<I')[0]>=shnum: raise Invalid('elf_relocations_invalid')
            sym=shoff+link*shsize;stype=read(data,sym+4,'<I')[0];sstride=read(data,sym+56,'<Q')[0];ssize=read(data,sym+32,'<Q')[0]
            if stype not in (2,11) or sstride<24 or ssize%sstride: raise Invalid('elf_relocations_invalid')
            off=read(data,s+24,'<Q')[0]
            for p in range(0,size,stride):
                if read(data,off+p+8,'<Q')[0]>>32>=ssize//sstride: raise Invalid('elf_relocations_invalid')
            if read(data,s+8,'<Q')[0]&2: raise Invalid('elf_relocations_unsupported')
    loads, metadata = 0, False
    for i in range(phnum):
        p = phoff + i * phsize
        kind = read(data, p, "<I")[0]
        off, va, _pa, filesz, memsz = read(data, p + 8, "<QQQQQ")
        if kind == 1:
            bounded(len(data), off, filesz)
            bounded(16 << 20, va, memsz)
            if not filesz or filesz > memsz:
                raise Invalid("elf_load_size")
            loads += 1
    for i in range(shnum):
        p = shoff + i * shsize
        kind = read(data, p + 4, "<I")[0]
        off, size = read(data, p + 24, "<QQ")
        if kind != 8:
            bounded(len(data), off, size)
        if kind == 7:  # SHT_NOTE; check AMDGPU metadata MsgPack envelope.
            bounded(len(data), off, size)
            end, n = off + size, off
            while n < end:
                bounded(end, n, 12)
                namesz, descsz, note_type = read(data, n, "<III")
                name = n + 12
                desc = name + ((namesz + 3) & ~3)
                nxt = desc + ((descsz + 3) & ~3)
                bounded(end, name, namesz)
                bounded(end, desc, descsz)
                bounded(end, n, nxt - n)
                if data[name:name + namesz] == b"AMDGPU\0" and note_type == 32 and descsz:
                    if metadata:
                        raise Invalid("elf_duplicate_metadata")
                    decode_metadata(bytes(data[desc:desc+descsz]),node_budget=node_budget)
                    metadata = True
                n = nxt
    if not loads or not metadata:
        raise Invalid("elf_load_or_metadata_missing")
    return True  # Mandatory metadata subset, not all AMDHSA/shader semantics.


def validate_kernel(data, target, name='synthetic'):
    """Independent descriptor/symbol consistency checks; never executes code."""
    validate_elf(data, target)
    shoff = read(data, 40, '<Q')[0]
    shsize, shnum = read(data, 58, '<HH')
    sections = [data[shoff+i*shsize:shoff+(i+1)*shsize] for i in range(shnum)]
    selected = None
    for s in sections:
        if read(s, 4, '<I')[0] != 7: continue
        off, size = read(s, 24, '<QQ'); end=off+size
        while off < end:
            names, descs, kind = read(data, off, '<III')
            owner=off+12; desc=owner+((names+3)&~3)
            if data[owner:owner+names] == b'AMDGPU\0' and kind == 32:
                value=decode_metadata(bytes(data[desc:desc+descs]))
                matches=[k for k in value['amdhsa.kernels'] if k['.name']==name]
                if len(matches)>1: raise Invalid('elf_kernel_metadata_duplicate')
                if not matches: raise Invalid('elf_kernel_metadata_missing')
                selected=matches[0]
            off=desc+((descs+3)&~3)
    if selected is None: raise Invalid('elf_kernel_metadata_missing')
    if selected['.symbol'] != name+'.kd': raise Invalid('elf_kernel_symbol_mismatch')
    symbols={}
    for s in sections:
        if read(s,4,'<I')[0] not in (2,11): continue
        off,size=read(s,24,'<QQ'); link=read(s,40,'<I')[0]; entry=read(s,56,'<Q')[0]
        if entry<24 or link>=len(sections): continue
        bounded(len(data),off,size)
        stroff,strsize=read(sections[link],24,'<QQ'); bounded(len(data),stroff,strsize)
        strings=data[stroff:stroff+strsize]
        for pos in range(entry,size-size%entry,entry):
            at=off+pos; index=read(data,at,'<I')[0]
            if index>=len(strings): continue
            tail=strings[index:]; stop=tail.find(b'\0')
            if stop<0: continue
            symbol=bytes(tail[:stop])
            if symbol in (name.encode(),(name+'.kd').encode()):
                symbols[symbol]=(data[at+4]&15,read(data,at+8,'<Q')[0])
    def file_offset(va,length):
        for s in sections[1:]:
            kind=read(s,4,'<I')[0];flags=read(s,8,'<Q')[0];addr=read(s,16,'<Q')[0]
            off,size=read(s,24,'<QQ')
            if kind != 8 and flags&2 and va>=addr and va-addr<size:
                bounded(len(data),off,size)
                if length<=size-(va-addr): return off+va-addr
        raise Invalid('elf_descriptor_invalid')
    kd=symbols.get((name+'.kd').encode())
    code=symbols.get(name.encode())
    if not kd or kd[0]!=1: raise Invalid('elf_descriptor_invalid')
    kdpos=file_offset(kd[1],64)
    relative=read(data,kdpos+16,'<q')[0]
    va=kd[1]+relative
    if not 0<=va<=0xffffffffffffffff: raise Invalid('elf_descriptor_invalid')
    if code and (code[0]!=2 or code[1]!=va): raise Invalid('elf_descriptor_invalid')
    file_offset(va,4)
    group,private,kernarg=read(data,kdpos,'<III')
    if selected['.kernarg_segment_size'] != kernarg: raise Invalid('elf_descriptor_mismatch')
    for key,actual in (('.group_segment_fixed_size',group),('.private_segment_fixed_size',private)):
        if key in selected and selected[key]!=actual: raise Invalid('elf_descriptor_mismatch')
    return True


class State(Enum):
    UNKNOWN = "Unknown"
    PCI = "PciMatched"
    PROFILE = "ProfileValidated"
    DISCOVERY = "DiscoveryValidated"
    FIRMWARE = "FirmwareRequirementsValidated"
    READY = "OfflineReady"
    FAILED = "Failed"


@dataclass
class OfflineSession:
    state: State = State.UNKNOWN
    error: str | None = None

    def run(self, profile, discovery, blobs):
        if self.state != State.UNKNOWN:
            raise Invalid("session_not_fresh")
        try:
            if profile is None:
                raise Invalid("profile_missing")
            self.state = State.PCI
            if profile != identify(profile.vendor, profile.device, profile.revision):
                raise Invalid("profile_tampered")
            self.state = State.PROFILE
            validate_discovery(profile, discovery)
            self.state = State.DISCOVERY
            needs = firmware_requirements(profile, discovery)
            validate_firmware(needs, blobs)
            self.state = State.FIRMWARE
            self.state = State.READY
        except Invalid as exc:
            self.state, self.error = State.FAILED, str(exc)
            raise
        return self.state


def hardware_initialization_allowed(*_args, **_kwargs):
    return False  # No implementation to authorize in this offline build.


def encode_device_info(profile, topology=None):
    """Prototype wire v1, not compatible with N48N production ABI.

    Unknown fields are zero with validity bits unset. capabilities always zero.
    """
    if topology is not None:
        raise Invalid("active_topology_unverified")
    return struct.pack("<4sHHHHBBHQQ", b"N44I", 1, 32,
                       profile.vendor, profile.device, profile.revision or 0,
                       int(profile.revision is not None), profile.target.value, 0, 0)


def decode_device_info(data):
    if len(data) != 32:
        raise Invalid("abi_size")
    magic, version, size, vendor, device, rev, valid, target, capabilities, reserved = read(data, 0, "<4sHHHHBBHQQ")
    if magic != b"N44I" or version != 1 or size != 32 or valid not in (0, 1) or capabilities or reserved:
        raise Invalid("abi_header_or_capabilities")
    p = identify(vendor, device, rev if valid else None)
    if target != p.target.value or (not valid and rev):
        raise Invalid("abi_target_or_revision")
    return p


def parse_psp_package(data):
    """Structural PSP v2.0/v2.1(aux=0), never signature/load validation."""
    if len(data) < 36: raise Invalid('firmware_package_bounds')
    size,header,major,minor,_ia,_ib,_uc,length,payload,crc=read(data,0,'<IIHHHHIIII')
    if major != 2 or minor > 1: raise Invalid('firmware_package_version')
    base=40 if minor==1 else 36
    if size!=len(data) or header<base or header>size or payload<header or not length or payload>size or length>size-payload:
        raise Invalid('firmware_package_bounds')
    if crc: raise Invalid('firmware_crc_unverified')
    count=read(data,32,'<I')[0]
    if not 1<=count<=12 or base+count*16>len(data) or header<base+count*16: raise Invalid('firmware_package_count')
    if minor==1 and read(data,36,'<I')[0]: raise Invalid('firmware_package_aux_unverified')
    parts={}
    for i in range(count):
        kind,version,off,n=read(data,base+i*16,'<IIII')
        if not 1<=kind<=12 or not n: raise Invalid('firmware_package_component')
        if kind in parts: raise Invalid('firmware_package_duplicate')
        if off>length or n>length-off: raise Invalid('firmware_package_bounds')
        if any(off<x['offset']+x['size'] and x['offset']<off+n for x in parts.values()): raise Invalid('firmware_package_overlap')
        parts[kind]={'version':version,'offset':off,'size':n}
    if 1 not in parts or 2 not in parts: raise Invalid('firmware_package_required_missing')
    return {'parts':parts,'signature_verified':False}


def decode_device_info_v2(data):
    if len(data)!=96: raise Invalid('abi_v2_size')
    if data[:4]!=b'N44I' or read(data,4,'<HH')!=(2,96) or data[13]>1 or read(data,20,'<I')[0] or data[27] or read(data,64,'<I')[0]!=1:
        raise Invalid('abi_v2_header')
    if any(data[68:]): raise Invalid('abi_v2_reserved')
    vendor,device=read(data,8,'<HH')
    try: p=identify(vendor,device,data[12] if data[13] else None)
    except Invalid: raise Invalid('abi_v2_identity') from None
    if read(data,14,'<H')[0]!=p.target.value or (not data[13] and data[12]): raise Invalid('abi_v2_identity')
    present=read(data,16,'<I')[0]
    if present&~7: raise Invalid('abi_v2_presence')
    gc=tuple(data[24:27])
    if present&1:
        if gc!=p.expected_gc: raise Invalid('abi_v2_gc')
    elif any(gc): raise Invalid('abi_v2_unknown_gc')
    topology=read(data,28,'<IIIII')
    if present&2:
        if not all(topology): raise Invalid('abi_v2_topology')
    elif any(topology): raise Invalid('abi_v2_unknown_topology')
    memory=read(data,48,'<QQ')
    if present&4:
        if not all(memory) or memory[1]>memory[0]: raise Invalid('abi_v2_memory')
    elif any(memory): raise Invalid('abi_v2_unknown_memory')
    return {'target':p.target.value,'present':present,'gc':gc,'topology':topology,'memory':memory,'capabilities':0}
