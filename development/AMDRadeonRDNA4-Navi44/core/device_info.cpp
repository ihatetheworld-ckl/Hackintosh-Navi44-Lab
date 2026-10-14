#include "device_info.hpp"
namespace NaviCore {
namespace {
uint16_t u16(const uint8_t*p){return uint16_t(p[0])|uint16_t(p[1])<<8;}
uint32_t u32(const uint8_t*p){return uint32_t(u16(p))|uint32_t(u16(p+2))<<16;}
uint64_t u64(const uint8_t*p){return uint64_t(u32(p))|uint64_t(u32(p+4))<<32;}
void w16(uint8_t*p,uint16_t x){p[0]=uint8_t(x);p[1]=uint8_t(x>>8);}
void w32(uint8_t*p,uint32_t x){w16(p,uint16_t(x));w16(p+2,uint16_t(x>>16));}
void w64(uint8_t*p,uint64_t x){w32(p,uint32_t(x));w32(p+4,uint32_t(x>>32));}
}
Result decodeDeviceInfo(View v,DeviceInfo&out){
    out=DeviceInfo{};if(!v.data||v.size!=kDeviceInfoSize)return failure("abi_v2_size");const uint8_t*d=v.data;
    if(d[0]!='N'||d[1]!='4'||d[2]!='4'||d[3]!='I'||u16(d+4)!=2||u16(d+6)!=96||d[13]>1||u32(d+20)||d[27]||u32(d+64)!=1)return failure("abi_v2_header");
    for(size_t i=68;i<96;++i)if(d[i])return failure("abi_v2_reserved");
    auto p=Asic::identify(u16(d+8),u16(d+10),d[12],d[13]!=0);
    if(p.family==Asic::Family::Unknown||u16(d+14)!=uint16_t(p.target)||(!d[13]&&d[12]))return failure("abi_v2_identity");
    const uint32_t present=u32(d+16);if(present&~7u)return failure("abi_v2_presence");
    if(present&1){if(d[24]!=p.expectedGc.major||d[25]!=p.expectedGc.minor||d[26]!=p.expectedGc.revision)return failure("abi_v2_gc");}
    else if(d[24]||d[25]||d[26])return failure("abi_v2_unknown_gc");
    uint32_t se=u32(d+28),cu=u32(d+32),rb=u32(d+36),tcc=u32(d+40),gb=u32(d+44);
    if(present&2){if(!se||!cu||!rb||!tcc||!gb)return failure("abi_v2_topology");}
    else if(se||cu||rb||tcc||gb)return failure("abi_v2_unknown_topology");
    uint64_t vram=u64(d+48),bar=u64(d+56);
    if(present&4){if(!vram||!bar||bar>vram)return failure("abi_v2_memory");}
    else if(vram||bar)return failure("abi_v2_unknown_memory");
    out={p,present,d[24],d[25],d[26],se,cu,rb,tcc,gb,vram,bar};return success();
}
Result encodeDeviceInfo(const DeviceInfo&i,uint8_t*out,size_t n){
    if(!out||n!=kDeviceInfoSize)return failure("abi_v2_size");
    const auto expected=Asic::identify(i.profile.vendor,i.profile.device,i.profile.revision,i.profile.revisionKnown);
    if(i.profile.family!=expected.family||i.profile.revisionVerified||i.profile.topology.verified)return failure("abi_v2_unverified_model");
    uint8_t raw[kDeviceInfoSize]{};raw[0]='N';raw[1]='4';raw[2]='4';raw[3]='I';w16(raw+4,2);w16(raw+6,96);
    w16(raw+8,i.profile.vendor);w16(raw+10,i.profile.device);raw[12]=i.profile.revision;raw[13]=i.profile.revisionKnown;
    w16(raw+14,uint16_t(i.profile.target));w32(raw+16,i.present);w32(raw+20,i.profile.capabilities);
    raw[24]=i.gcMajor;raw[25]=i.gcMinor;raw[26]=i.gcRevision;w32(raw+28,i.se);w32(raw+32,i.cu);w32(raw+36,i.rb);w32(raw+40,i.tcc);w32(raw+44,i.gbAddrConfig);
    w64(raw+48,i.vramBytes);w64(raw+56,i.visibleBarBytes);w32(raw+64,1);
    DeviceInfo validated;Result r=decodeDeviceInfo({raw,sizeof(raw)},validated);if(!r.ok())return r;
    for(size_t j=0;j<n;++j)out[j]=raw[j];return success();
}
}
