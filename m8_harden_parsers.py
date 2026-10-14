"""One-time, checked hardening of existing parsers; no hardware routines."""
from pathlib import Path
import sys,hashlib,json
sys.path.insert(0,str(Path(__file__).resolve().parent))
import m7_safety as safe
ROOT=safe.ROOT;SRC=ROOT/'development/AMDRadeonRDNA4-Navi44/src'
hashes=json.loads((ROOT/'reports/m8/baseline-sha256.json').read_text())
for name in ('edid.cpp','atombios.cpp','atombios.hpp'):
    rel=(SRC/name).relative_to(ROOT).as_posix()
    if hashlib.sha256((SRC/name).read_bytes()).hexdigest()!=hashes[rel]:
        raise SystemExit('Already changed or unexpected input: '+name)
text=(SRC/'edid.cpp').read_text()
text=text.replace('bool parseDetailedTiming(const uint8_t d[18], DetailedTiming &out) {',
                  'bool parseDetailedTiming(const uint8_t d[18], DetailedTiming &out) {\n\tout = {};\n\tif (!d) return false;')
text=text.replace('if (out.hActive == 0 || out.vActive == 0)\n\t\treturn false;',
'''if (!out.hActive || !out.vActive || !out.hBlank || !out.vBlank ||
        !out.hSyncWidth || !out.vSyncWidth ||
        uint32_t(out.hSyncOffset) + out.hSyncWidth > out.hBlank ||
        uint32_t(out.vSyncOffset) + out.vSyncWidth > out.vBlank) {
        out = {}; return false;
    }''')
text=text.replace('if (edid[18] != 1)','if (edid[18] != 1 || edid[19] > 4)')
text=text.replace('''if (!ext || ext[0] != 0x02)
		return false;
	out = CtaCaps {};''','''out = CtaCaps {};
    if (!ext || ext[0] != 0x02 || ext[1] != 3 || ext[2] > 127 ||
        (ext[2] != 0 && ext[2] < 4)) return false;''')
text=text.replace('''if (pos + 1 + len > end)
				break;''','''if (pos + 1 + len > end) { out = {}; return false; }''')
text=text.replace('''if (!parseDetailedTiming(ext + pos, t))
				break;''','''if (!(ext[pos] | ext[pos+1])) break;
            if (!parseDetailedTiming(ext + pos, t)) { out = {}; return false; }''')
safe.write(SRC/'edid.cpp',text)
header=(SRC/'atombios.hpp').read_text()
header=header.replace('DceInfo              = 26,','DceInfo              = 27,').replace('VramInfo             = 27,','VramInfo             = 28,').replace('VoltageObjectInfo    = 31,','VoltageObjectInfo    = 32,')
header=header.replace('bool isValid() const { return valid; }','bool isValid() const { return valid; }\n    const char *error() const { return lastError; }')
header=header.replace('bool valid { false };','bool valid { false };\n    size_t imageEnd {0};\n    mutable const char *lastError {"not_initialized"};\n    bool fail(const char *why) const { lastError=why; return false; }\n    bool contains(size_t off,size_t count) const {\n        const size_t end=imageEnd?imageEnd:size;\n        return data && off<=end && count<=end-off && (!imageEnd || off>=base);\n    }')
safe.write(SRC/'atombios.hpp',header)
text=(SRC/'atombios.cpp').read_text()
text=text.replace('if (off >= size) return false;','if (!contains(off,1)) return false;')
text=text.replace('if (off + 2 > size) return false;','if (!contains(off,2)) return false;')
text=text.replace('if (off + 4 > size) return false;','if (!contains(off,4)) return false;')
text=text.replace('''uint16_t tsize; uint8_t frev, crev;''','''out = {}; if (!contains(absOffset,4)) return false;
    uint16_t tsize; uint8_t frev, crev;''')
text=text.replace('if (tsize < 4 || absOffset + tsize > size)','if (tsize < 4 || !contains(absOffset,tsize))')
def replace(start,end,body):
    global text
    a=text.index(start);b=text.index(end,a);text=text[:a]+body+'\n\n'+text[b:]
replace('bool AtomBios::validateImage(', 'bool AtomBios::getCommandTable(','''bool AtomBios::validateImage(size_t offset) {
    imageEnd=0;base=0;length=0;masterDataTable=masterCmdTable=0;subsysVid=subsysId=0;
    if (!contains(offset,512) || data[offset]!=0x55 || data[offset+1]!=0xaa)
        return fail("rom_signature");
    const size_t bytes=size_t(data[offset+kRomSizeBlocksOffset])*512;
    if (!bytes || !contains(offset,bytes)) return fail("rom_length");
    uint8_t sum=0;for(size_t i=0;i<bytes;++i)sum=uint8_t(sum+data[offset+i]);
    if(sum) return fail("rom_checksum");
    base=offset;length=bytes;imageEnd=offset+bytes;
    uint16_t hdr=0,mdt=0;
    if(!readU16(base+kAtomRomHeaderPointer,hdr)||hdr<0x4a) return fail("atom_header_pointer");
    const size_t atom=base+hdr;TableHeader h{};
    if(!readTableHeader(atom,h)||h.size<40||h.formatRev!=2||(h.contentRev!=2&&h.contentRev!=3))
        return fail("atom_header_version");
    if(data[atom+4]!='A'||data[atom+5]!='T'||data[atom+6]!='O'||data[atom+7]!='M')
        return fail("atom_signature");
    if(!readU16(atom+kMasterDataTableOffset,mdt)||mdt<0x4a) return fail("master_pointer");
    TableHeader master{};masterDataTable=base+mdt;
    if(!readTableHeader(masterDataTable,master)||master.formatRev!=2||master.contentRev!=1||master.size!=74)
        return fail("master_version");
    auto overlap=[](size_t a,size_t n,size_t b,size_t m){return a<b+m&&b<a+n;};
    if(overlap(atom,h.size,masterDataTable,master.size))return fail("table_overlap");
    size_t offsets[MaxDataTable]{},sizes[MaxDataTable]{};
    for(size_t i=0;i<MaxDataTable;++i){
        uint16_t rel=0;if(!readU16(masterDataTable+4+2*i,rel))return fail("table_bounds");
        if(!rel)continue;
        TableHeader entry{};const size_t at=base+rel;
        if(rel<0x4a||!readTableHeader(at,entry))return fail("table_bounds");
        if(overlap(at,entry.size,atom,h.size)||overlap(at,entry.size,masterDataTable,master.size))return fail("table_overlap");
        for(size_t j=0;j<i;++j)if(sizes[j]&&overlap(at,entry.size,offsets[j],sizes[j]))return fail("table_overlap");
        offsets[i]=at;sizes[i]=entry.size;
    }
    if(!readU16(atom+kSubsysVidOffset,subsysVid)||!readU16(atom+kSubsysIdOffset,subsysId))return fail("atom_header_bounds");
    uint16_t mct=0;
    if(!readU16(atom+kMasterHwFunctionOffset,mct))return fail("command_pointer");
    if(mct){
        TableHeader command{};const size_t at=base+mct;
        if(mct<0x4a||!readTableHeader(at,command)||command.formatRev!=2||command.contentRev!=1)return fail("command_version");
        if(overlap(at,command.size,atom,h.size)||overlap(at,command.size,masterDataTable,master.size))return fail("table_overlap");
        for(size_t j=0;j<MaxDataTable;++j)if(sizes[j]&&overlap(at,command.size,offsets[j],sizes[j]))return fail("table_overlap");
        masterCmdTable=at;
    }
    lastError=nullptr;return true;
}''')
replace('bool AtomBios::init(', 'size_t AtomBios::configName(','''bool AtomBios::init(const uint8_t *romData,size_t romSize) {
    data=romData;size=romSize;valid=false;imageEnd=base=length=masterDataTable=masterCmdTable=0;
    subsysVid=subsysId=0;lastError="rom_bounds";
    // Fixed offline input budget; never scan hardware or an unbounded view.
    if(!data||size<512||size>(4u<<20))return false;
    for(size_t off=0;off<=size-512;off+=512){
        if(validateImage(off)){valid=true;return true;}
        // A signature-bearing image that fails validation is not silently bypassed.
        if(data[off]==0x55&&data[off+1]==0xaa)break;
    }
    const char*why=lastError;data=nullptr;size=0;imageEnd=base=length=masterDataTable=masterCmdTable=0;
    subsysVid=subsysId=0;lastError=why;return false;
}''')
text=text.replace('''bool AtomBios::getFirmwareInfo(FirmwareInfo3 &out) const {
	TableHeader th;''','''bool AtomBios::getFirmwareInfo(FirmwareInfo3 &out) const {
    out = {};
    TableHeader th;''')
text=text.replace('''if (!off || th.formatRev != 3 || th.size < 20)''','''if (!off || th.formatRev != 3 || th.contentRev < 1 || th.contentRev > 5 || th.size < 20)''')
replace('size_t AtomBios::getDisplayPaths(', 'bool AtomBios::getPathRecords(','''size_t AtomBios::getDisplayPaths(DisplayPath *paths,size_t maxPaths) const {
    if(!paths||!maxPaths)return 0;
    for(size_t i=0;i<maxPaths;++i)paths[i]={};
    TableHeader th{};const size_t off=dataTable(DisplayObjectInfo,&th);
    if(!off||th.formatRev!=1||th.contentRev!=5||th.size<8){fail("display_version");return 0;}
    const uint8_t count=data[off+6];
    if(!count||count>MaxDisplayPaths||count>maxPaths||8u+size_t(count)*16>th.size||data[off+7]){
        fail("display_count");return 0;
    }
    for(size_t i=0;i<count;++i){
        const size_t p=off+8+i*16;uint16_t object=0,record=0,encoder=0,tag=0;
        readU16(p,object);readU16(p+2,record);readU16(p+4,encoder);readU16(p+12,tag);
        uint16_t reserved=0;
        for(unsigned n: {6u,8u,10u,14u}){readU16(p+n,reserved);if(reserved){fail("display_reserved");return 0;}}
        if(!object||((object>>12)&7)!=3||!encoder||((encoder>>12)&7)!=2||!tag||
           (record&&(record<8+size_t(count)*16||record>th.size-2))){fail("display_path");return 0;}
        for(size_t j=0;j<i;++j)if(paths[j].connectorObjId==object){fail("display_duplicate");return 0;}
        paths[i]={object,record,encoder,tag};
    }
    lastError=nullptr;return count;
}''')
# Avoid initializer_list in kernel-friendly source.
text=text.replace('for(unsigned n: {6u,8u,10u,14u})','const unsigned slots[]={6u,8u,10u,14u};for(unsigned n:slots)')
replace('bool AtomBios::getPathRecords(', 'size_t AtomBios::getGpioPins(','''bool AtomBios::getPathRecords(const DisplayPath &path,PathRecords &out) const {
    out={};TableHeader th{};const size_t table=dataTable(DisplayObjectInfo,&th);
    DisplayPath paths[MaxDisplayPaths]{};const size_t count=getDisplayPaths(paths,MaxDisplayPaths);bool member=false;
    for(size_t i=0;i<count;++i)if(paths[i].connectorObjId==path.connectorObjId&&
        paths[i].recordOffset==path.recordOffset&&paths[i].encoderObjId==path.encoderObjId&&paths[i].deviceTag==path.deviceTag)member=true;
    if(!table||!member||!path.recordOffset)return fail("record_path");
    size_t p=table+path.recordOffset;const size_t end=table+th.size;PathRecords result{};
    unsigned budget=0;
    while(p<=end&&end-p>=2&&budget++<128){
        const uint8_t type=data[p],bytes=data[p+1];
        if(type==0||type==0xff){out=result;lastError=nullptr;return true;}
        if(bytes<2||bytes>end-p)return fail("record_bounds");
        if(type==1){
            if(bytes!=4||result.hasI2c)return fail("record_i2c");
            result.hasI2c=true;result.i2cId=data[p+2];result.i2cHwCapable=(data[p+2]&0x80)!=0;result.ddcLine=data[p+2]&15;
        }else if(type==2){
            if(bytes!=4||result.hasHpd)return fail("record_hpd");
            result.hasHpd=true;result.hpdPin=data[p+2];result.hpdPlugState=data[p+3];
        }
        p+=bytes;
    }
    return fail("record_unterminated");
}''')
safe.write(SRC/'atombios.cpp',text)
print('Existing EDID / AtomBios hardened')
