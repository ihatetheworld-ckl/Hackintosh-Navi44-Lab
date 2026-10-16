"""Bounded Mach-O and independent project KPI policy, BSD-3-Clause.

Reference exports are evidence level C, never a target-binary/ABI certificate.
Input files are never executed. This parser supplements real Apple nm/otool.
"""
import struct,hashlib
MAX_FILE=32<<20
CPUS={"x86_64":0x1000007,"arm64":0x100000c}
class AuditError(ValueError):pass
def inspect(raw,arch,kind=1):
    if len(raw)<32 or len(raw)>MAX_FILE:raise AuditError("file_size")
    def unpack(fmt,pos):
        if pos<0 or pos+struct.calcsize(fmt)>len(raw):raise AuditError("truncated_structure")
        return struct.unpack_from(fmt,raw,pos)
    def span(offset,size):
        if offset<0 or size<0 or offset>len(raw) or size>len(raw)-offset:raise AuditError("file_range")
    magic,cpu,subtype,ft,n,cmdbytes,flags,_=unpack("<IiiIIIII",0)
    if magic!=0xfeedfacf or cpu!=CPUS[arch] or ft!=kind:raise AuditError("architecture_or_type")
    if n>4096:raise AuditError("load_command_budget")
    span(32,cmdbytes);pos=32;sections=[];segments=[];commands=[];symtab=None;dysym=None;versions=[]
    for _ in range(n):
        cmd,length=unpack("<II",pos)
        if length<8 or length%8 or pos+length>32+cmdbytes:raise AuditError("load_command_range")
        if cmd in (4,5,0xc,0xd,0x80000018,0x8000001f,0x20,0x80000023,0x80000028):raise AuditError("runtime_entry_or_dylib")
        if cmd not in (2,11,0x19,0x1b,0x26,0x29,0x2a,0x2e,0x32):raise AuditError("unapproved_load_command")
        commands.append(dict(command=cmd,bytes=length))
        if cmd==0x19:
            if length<72:raise AuditError("segment_short")
            name=raw[pos+8:pos+24].split(b"\0")[0].decode();va,vs,fo,fs=unpack("<QQQQ",pos+24);span(fo,fs)
            count=unpack("<I",pos+64)[0]
            if count>1024 or 72+count*80!=length:raise AuditError("section_count")
            segments.append(dict(name=name,address=va,size=vs,file_offset=fo,file_size=fs))
            for i in range(count):
                at=pos+72+i*80;sn=raw[at:at+16].split(b"\0")[0].decode();sg=raw[at+16:at+32].split(b"\0")[0].decode()
                addr,size,offset,alignment,reloff,nreloc,sflags=unpack("<QQIIIII",at+32)
                if alignment>31 or nreloc>1<<20:raise AuditError("section_budget")
                if (sflags&255) not in (1,12):span(offset,size)
                span(reloff,nreloc*8)
                if sn in ("__mod_init_func","__mod_term_func","__gcc_except_tab","__eh_frame","__compact_unwind","__thread_vars","__init","__fini"):raise AuditError("initializer_eh_or_tls")
                sections.append(dict(name=sn,segment=sg,address=addr,size=size,offset=offset,reloff=reloff,nreloc=nreloc,flags=sflags))
        elif cmd==2:
            if length!=24 or symtab is not None:raise AuditError("symbol_command")
            symtab=unpack("<IIII",pos+8)
        elif cmd==11:
            if length!=80 or dysym is not None:raise AuditError("dysym_command")
            dysym=unpack("<18I",pos+8)
        elif cmd==0x32:
            if length<24:raise AuditError("build_version_command")
            platform,minimum,sdk,tools=unpack("<IIII",pos+8)
            if platform!=1 or 24+tools*8!=length:raise AuditError("platform_or_tools")
            versions.append(dict(platform=platform,minimum=minimum,sdk=sdk))
        elif cmd in (0x26,0x29,0x2e):
            if length!=16:raise AuditError("linkedit_command")
            offset,size=unpack("<II",pos+8);span(offset,size)
        elif cmd==0x1b and length!=24:raise AuditError("uuid_command")
        elif cmd==0x2a and length!=16:raise AuditError("source_version_command")
        pos+=length
    if pos!=32+cmdbytes or symtab is None or (kind==1 and not versions):raise AuditError("missing_commands")
    off,count,stroff,strsize=symtab
    if count>1<<20:raise AuditError("symbol_budget")
    span(off,count*16);span(stroff,strsize);symbols=[]
    for i in range(count):
        index,typ,sect,desc,value=unpack("<IBBHQ",off+i*16)
        if index>=strsize:raise AuditError("string_index")
        end=raw.find(b"\0",stroff+index,stroff+strsize)
        if end<0:raise AuditError("unterminated_symbol")
        name=raw[stroff+index:end].decode("utf-8")
        if not (typ&0xe0) and (typ&14)==14 and not 1<=sect<=len(sections):raise AuditError("symbol_section")
        undefined=not(typ&0xe0) and typ&1 and (typ&14)==0
        if undefined and (not name or value):raise AuditError("empty_or_common_import")
        symbols.append(dict(name=name,type=typ,section=sect,description=desc,value=value,undefined=bool(undefined),
            external=bool(typ&1) and not(typ&0xe0),weak=bool(desc&0x80)))
    relocations=[]
    def relocs(offset,count,limit,origin):
        span(offset,count*8)
        for i in range(count):
            address,word=unpack("<II",offset+i*8)
            if address&0x80000000:raise AuditError("unsupported_scattered_relocation")
            number=word&0xffffff;external=bool(word&(1<<27));width=1<<((word>>25)&3);rt=word>>28
            if rt>({"x86_64":9,"arm64":11}[arch]):raise AuditError("relocation_type")
            if address>limit or width>limit-address:raise AuditError("relocation_address")
            addend=arch=="arm64" and rt==10
            if external and number>=len(symbols):raise AuditError("relocation_symbol_index")
            if not external and not addend and number>len(sections):raise AuditError("relocation_section_index")
            relocations.append(dict(origin=origin,address=address,type=rt,external=external,symbol=symbols[number]["name"] if external else None,index=number))
    for s in sections:relocs(s["reloff"],s["nreloc"],s["size"],s["name"])
    if dysym:
        il,nl,ide,nde,iu,nu,*_=dysym
        if any(start>count or length>count-start for start,length in [(il,nl),(ide,nde),(iu,nu)]):raise AuditError("dysym_symbol_range")
        indirect,nindirect,ext,ne,loc,nloc=dysym[12:18];span(indirect,nindirect*4)
        for i in range(nindirect):
            sym=unpack("<I",indirect+i*4)[0]
            if not sym&0xc0000000 and sym>=count:raise AuditError("indirect_symbol_index")
        limit=max((x["address"]+x["size"] for x in segments),default=0)
        relocs(ext,ne,limit,"dynamic_external");relocs(loc,nloc,limit,"dynamic_local")
    return dict(arch=arch,cpu=cpu,subtype=subtype,file_type=ft,flags=flags,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),
        commands=commands,versions=versions,sections=sections,symbols=symbols,relocations=relocations)
def runtime_reason(name):
    if any(x in name for x in ("__cxa_throw","__cxa_allocate_exception","__gxx_personality","_Unwind")):return "EXCEPTION_RUNTIME"
    if any(x in name for x in ("__dynamic_cast","__ZTI","__ZTS")):return "RTTI_RUNTIME"
    if name in ("_puts","_malloc","_free","_fwrite") or any(x in name for x in ("_pthread_","stack_chk","__ZNSt")):return "HOST_RUNTIME"
    if any(x in name for x in ("__Znwm","__Znam","__Zdl","__Zda","__cxa_pure_virtual")):return "UNPLANNED_CPP_RUNTIME"
    return None
def audit(objects,allowed_sources,allowed_imports,exports,provider_rules=None):
    """All object metadata comes from explicit recorded compile sources/options.

    Export presence is kept separate from the narrower offline-target allowlist.
    Apple API implementations are never accepted from project object providers.
    """
    errors=[];defined={};imports={};provider_rules=provider_rules or {}
    for o in objects:
        if o['source'] not in allowed_sources:errors.append(dict(source=o['source'],reason='SOURCE_NOT_ALLOWED'))
        flags=o.get('flags',[])
        if any(x not in flags for x in ['-fno-exceptions','-fno-rtti','-mkernel','-fapple-kext','-nostdinc++']):errors.append(dict(source=o['source'],reason='ABI_OPTIONS_MISMATCH'))
        for s in o['image']['symbols']:
            if s['undefined']:imports.setdefault(s['name'],[]).append(o['source'])
            elif s['external']:defined.setdefault(s['name'],[]).append((o['source'],s['weak']))
    for symbol,providers in defined.items():
        metadata=symbol=='_kmod_info' and all(p[0]=='tests/unit/m11_kmod_compile.cpp' for p in providers)
        if (symbol in allowed_imports or symbol in exports) and not metadata:errors.append(dict(symbol=symbol,reason='APPLE_API_PROVIDER_CONFLICT',providers=[p[0] for p in providers]))
        if len([p for p in providers if not p[1]])>1:errors.append(dict(symbol=symbol,reason='DUPLICATE_STRONG_PROVIDER'))
        if symbol in provider_rules and any(p[0] not in provider_rules[symbol] for p in providers):errors.append(dict(symbol=symbol,reason='WRONG_SYMBOL_PROVIDER'))
    rows=[]
    for symbol,users in sorted(imports.items()):
        reason=runtime_reason(symbol)
        if reason:classification=reason;errors.append(dict(symbol=symbol,reason=reason))
        elif symbol in defined:classification='INTERNAL_RESOLVED'
        elif symbol in allowed_imports and symbol in exports:classification='EXPECTED_KERNEL_IMPORT_WITH_SOURCE_REFERENCE'
        else:
            classification='UNSUPPORTED_KERNEL_IMPORT' if symbol in exports else 'UNKNOWN_IMPORT'
            errors.append(dict(symbol=symbol,reason=classification))
        rows.append(dict(symbol=symbol,classification=classification,users=users,providers=[p[0] for p in defined.get(symbol,[])],reference=exports.get(symbol),target_binary_verified=False))
    return dict(status='REJECTED' if errors else 'PASS',errors=errors,per_symbol=rows,target_ABI='UNVERIFIED',full_target_link_closure='BLOCKED')
