//
//  atombios.cpp
//  AMDRadeonRDNA4
//
//  Freestanding AtomBIOS parser — see atombios.hpp for scope and the ROM the
//  layout was validated against.
//

#include "atombios.hpp"

// Offsets within the legacy VBIOS image (validated against the Navi 48 ROM).
// Image signature 0x55 0xAA sits at offset 0x00.
static constexpr size_t kRomSizeBlocksOffset  = 0x02;   // length in 512-byte blocks
static constexpr size_t kAtomRomHeaderPointer = 0x48;   // u16 -> atom_rom_header
// atom_rom_header_v2_x field offsets (relative to the header):
static constexpr size_t kAtomSignatureOffset  = 0x04;   // "ATOM"
static constexpr size_t kConfigFilenameOffset = 0x0c;   // u16 image-relative ptr
static constexpr size_t kSubsysVidOffset      = 0x18;
static constexpr size_t kSubsysIdOffset       = 0x1a;
static constexpr size_t kMasterHwFunctionOffset = 0x1e; // u16 image-relative ptr
static constexpr size_t kMasterDataTableOffset  = 0x20; // u16 image-relative ptr

bool AtomBios::readU8(size_t off, uint8_t &v) const {
	if (!contains(off,1)) return false;
	v = data[off];
	return true;
}

bool AtomBios::readU16(size_t off, uint16_t &v) const {
	if (!contains(off,2)) return false;
	v = static_cast<uint16_t>(data[off] | (data[off + 1] << 8));
	return true;
}

bool AtomBios::readU32(size_t off, uint32_t &v) const {
	if (!contains(off,4)) return false;
	v = static_cast<uint32_t>(data[off]) |
	    (static_cast<uint32_t>(data[off + 1]) << 8) |
	    (static_cast<uint32_t>(data[off + 2]) << 16) |
	    (static_cast<uint32_t>(data[off + 3]) << 24);
	return true;
}

bool AtomBios::readTableHeader(size_t absOffset, TableHeader &out) const {
	out = {}; if (!contains(absOffset,4)) return false;
    uint16_t tsize; uint8_t frev, crev;
	if (!readU16(absOffset, tsize) || !readU8(absOffset + 2, frev) || !readU8(absOffset + 3, crev))
		return false;
	if (tsize < 4 || !contains(absOffset,tsize))
		return false;
	out.size = tsize;
	out.formatRev = frev;
	out.contentRev = crev;
	return true;
}

bool AtomBios::validateImage(size_t offset) {
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
    if(data[atom+kAtomSignatureOffset]!='A'||data[atom+kAtomSignatureOffset+1]!='T'||
       data[atom+kAtomSignatureOffset+2]!='O'||data[atom+kAtomSignatureOffset+3]!='M')
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
}

bool AtomBios::getCommandTable(uint8_t index, CmdTableInfo &out) const {
    out = {};
	if (!valid || !masterCmdTable || index >= CmdFunctionCount)
		return false;

	TableHeader mctHdr;
	if (!readTableHeader(masterCmdTable, mctHdr))
		return false;
	size_t entries = (mctHdr.size - 4) / 2;
	if (index >= entries)
		return false;

	uint16_t rel;
	if (!readU16(masterCmdTable + 4 + 2u * index, rel) || rel == 0)
		return false;

	size_t abs = base + rel;
	TableHeader th;
	if (!readTableHeader(abs, th))
		return false;

	out.offset = abs;
	out.size = th.size;
	out.formatRev = th.formatRev;
	out.contentRev = th.contentRev;
	return true;
}

bool AtomBios::init(const uint8_t *romData,size_t romSize) {
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
}

size_t AtomBios::configName(char *out, size_t outLen) const {
    if (out && outLen) out[0]='\0';
	if (!valid || !out || outLen == 0)
		return 0;

	uint16_t hdrPtr, namePtr;
	if (!readU16(base + kAtomRomHeaderPointer, hdrPtr) ||
	    !readU16(base + hdrPtr + kConfigFilenameOffset, namePtr) || namePtr == 0)
		return 0;

	size_t src = base + namePtr;
	size_t n = 0;
	while (n + 1 < outLen) {
		uint8_t c;
		if (!readU8(src + n, c) || c == 0)
			break;
		out[n++] = static_cast<char>(c);
	}
	// Trim trailing spaces (the ROM pads with blanks: "NAVI48.bin  ").
	while (n > 0 && out[n - 1] == ' ')
		n--;
	out[n] = '\0';
	return n;
}

size_t AtomBios::dataTable(DataTable table, TableHeader *header) const {
    if (header) *header = {};
	if (!valid || table >= MaxDataTable)
		return 0;

	TableHeader mdtHdr;
	if (!readTableHeader(masterDataTable, mdtHdr))
		return 0;
	size_t entries = (mdtHdr.size - 4) / 2;
	if (table >= entries)
		return 0;

	uint16_t rel;
	if (!readU16(masterDataTable + 4 + 2 * table, rel) || rel == 0)
		return 0;

	size_t abs = base + rel;
	TableHeader th;
	if (!readTableHeader(abs, th))
		return 0;
	if (header)
		*header = th;
	return abs;
}

bool AtomBios::getFirmwareInfo(FirmwareInfo3 &out) const {
    out = {};
    TableHeader th;
	size_t off = dataTable(FirmwareInfo, &th);
	if (!off || th.formatRev != 3 || th.contentRev < 1 || th.contentRev > 5 || th.size < 20)
		return false;

	out.header = th;
	return readU32(off + 4,  out.firmwareRevision) &&
	       readU32(off + 8,  out.bootupSclk10KHz) &&
	       readU32(off + 12, out.bootupMclk10KHz) &&
	       readU32(off + 16, out.firmwareCapability);
}

size_t AtomBios::getDisplayPaths(DisplayPath *paths,size_t maxPaths) const {
    if(!paths||!maxPaths||maxPaths>MaxDisplayPaths){fail("display_storage");return 0;}
    for(size_t i=0;i<maxPaths;++i)paths[i]={};
    TableHeader th{};const size_t off=dataTable(DisplayObjectInfo,&th);
    if(!off||th.formatRev!=1||th.contentRev!=5||th.size<8){fail("display_version");return 0;}
    const uint8_t count=data[off+6];
    if(!count||count>MaxDisplayPaths||count>maxPaths||8u+size_t(count)*16>th.size||data[off+7]){
        fail("display_count");return 0;
    }
    DisplayPath candidate[MaxDisplayPaths]{};
    for(size_t i=0;i<count;++i){
        const size_t p=off+8+i*16;uint16_t object=0,record=0,encoder=0,tag=0;
        readU16(p,object);readU16(p+2,record);readU16(p+4,encoder);readU16(p+12,tag);
        uint16_t reserved=0;
        const unsigned slots[]={6u,8u,10u,14u};for(unsigned n:slots){readU16(p+n,reserved);if(reserved){fail("display_reserved");return 0;}}
        if(!object||((object>>12)&7)!=3||!encoder||((encoder>>12)&7)!=2||!tag||
           (record&&(record<8+size_t(count)*16||record>th.size-2))){fail("display_path");return 0;}
        for(size_t j=0;j<i;++j)if(candidate[j].connectorObjId==object){fail("display_duplicate");return 0;}
        candidate[i]={object,record,encoder,tag};
    }
    for(size_t i=0;i<count;++i)paths[i]=candidate[i];
    lastError=nullptr;return count;
}

bool AtomBios::getPathRecords(const DisplayPath &path,PathRecords &out) const {
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
}

size_t AtomBios::getGpioPins(GpioPin *pins, size_t maxPins) const {
	if (!pins || maxPins == 0)
		return 0;

	TableHeader th;
	size_t off = dataTable(GpioPinLut, &th);
	if (!off || th.formatRev != 2 || th.size < 4 + 8)
		return 0;

	// atom_gpio_pin_assignment: u32 data_a_reg_index, u8 gpio_bitshift,
	// u8 gpio_mask_bitshift, u8 gpio_id, u8 reserved — 8 bytes each.
	size_t npins = (th.size - 4u) / 8;
	size_t count = 0;
	for (size_t i = 0; i < npins && count < maxPins; i++) {
		size_t p = off + 4 + i * 8;
		GpioPin pin {};
		uint8_t resv;
		if (!readU32(p, pin.regIndex) || !readU8(p + 4, pin.shift) ||
		    !readU8(p + 5, pin.maskShift) || !readU8(p + 6, pin.gpioId) ||
		    !readU8(p + 7, resv))
			break;
		if (pin.gpioId == 0)
			continue;
		pins[count++] = pin;
	}
	return count;
}

bool AtomBios::findGpioPin(uint8_t gpioId, GpioPin &out) const {
	GpioPin pins[MaxGpioPins];
	size_t n = getGpioPins(pins, MaxGpioPins);
	for (size_t i = 0; i < n; i++) {
		if (pins[i].gpioId == gpioId) {
			out = pins[i];
			return true;
		}
	}
	return false;
}

AtomBios::ConnectorType AtomBios::connectorType(uint16_t connectorObjId) {
	// Object id: bits 12-14 = object type (3 = connector), bits 8-11 = enum
	// instance, low byte = connector object id (atombios object ids).
	if (((connectorObjId >> 12) & 0x7) != 3)
		return ConnectorUnknown;
	switch (connectorObjId & 0xFF) {
		case 0x13: return ConnectorDP;
		case 0x0C: return ConnectorHDMIA;
		case 0x02:
		case 0x04: return ConnectorDVID;
		case 0x05: return ConnectorVGA;
		case 0x17: return ConnectorUSBC;
		default:   return ConnectorUnknown;
	}
}

const char *AtomBios::connectorName(ConnectorType type) {
	switch (type) {
		case ConnectorDP:    return "DisplayPort";
		case ConnectorHDMIA: return "HDMI-A";
		case ConnectorDVID:  return "DVI-D";
		case ConnectorVGA:   return "VGA";
		case ConnectorUSBC:  return "USB-C";
		default:             return "Unknown";
	}
}
