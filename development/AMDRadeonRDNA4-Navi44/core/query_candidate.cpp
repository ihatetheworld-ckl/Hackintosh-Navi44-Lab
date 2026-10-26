#include "query_candidate.hpp"
namespace NaviCore {
namespace {
uint16_t u16(const uint8_t*p){return uint16_t(p[0])|uint16_t(p[1])<<8;}
uint32_t u32(const uint8_t*p){return uint32_t(u16(p))|uint32_t(u16(p+2))<<16;}
uint64_t u64(const uint8_t*p){return uint64_t(u32(p))|uint64_t(u32(p+4))<<32;}
}
Result decodeQuery(View v,QueryCandidate&out){
    out={};if(!v.data||v.size!=QueryCandidateSize)return failure("query_size",Error::Bounds);
    const uint8_t*d=v.data;
    if(d[0]!='N'||d[1]!='4'||d[2]!='4'||d[3]!='Q'||u16(d+4)!=1||u16(d+6)!=0||u16(d+8)!=128)
        return failure("query_version",Error::Unsupported);
    if(u16(d+10)||d[12]>2||d[13]||d[14]||d[15]||u32(d+20)||!u64(d+24))return failure("query_unverified_header");
    QueryCandidate result{};Result r=decodeDeviceInfo({d+32,96},result.device);if(!r.ok())return r;
    if(u32(d+16)!=result.device.present||(d[12]==0&&result.device.present))return failure("query_presence");
    result.provenance=Provenance(d[12]);result.generation=u64(d+24);out=result;return success();
}
Result encodeQuery(const QueryCandidate&q,uint8_t*out,size_t length){
    if(!out||length!=QueryCandidateSize)return failure("query_size",Error::Bounds);
    uint8_t raw[QueryCandidateSize]{};raw[0]='N';raw[1]='4';raw[2]='4';raw[3]='Q';raw[4]=1;raw[8]=128;
    raw[12]=uint8_t(q.provenance);
    for(unsigned i=0;i<4;++i)raw[16+i]=uint8_t(q.device.present>>(8*i));
    for(unsigned i=0;i<8;++i)raw[24+i]=uint8_t(q.generation>>(8*i));
    Result r=encodeDeviceInfo(q.device,raw+32,96);if(!r.ok())return r;
    QueryCandidate verified{};r=decodeQuery({raw,sizeof(raw)},verified);if(!r.ok())return r;
    for(size_t i=0;i<length;++i)out[i]=raw[i];return success();
}
Result OfflineOwner::prepare(const QueryCandidate&q){
    if(failed||active||leased||q.generation<=lastGeneration)return failure("owner_state",Error::Protocol);
    uint8_t raw[QueryCandidateSize]{};Result r=encodeQuery(q,raw,sizeof(raw));
    if(!r.ok()){failed=true;current={};return r;}
    r=decodeQuery({raw,sizeof(raw)},current);if(!r.ok()){failed=true;return r;}
    lastGeneration=current.generation;active=true;return success();
}
Result OfflineOwner::borrow(QueryCandidate&out){
    out={};if(failed||!active||leased)return failure("owner_unavailable",Error::Protocol);
    out=current;leased=true;return success();
}
Result OfflineOwner::giveBack(uint64_t generation){
    if(!active||!leased||generation!=current.generation){failed=true;close();return failure("owner_stale_lease",Error::Protocol);}
    leased=false;return success();
}
namespace {
void w16(uint8_t*p,uint16_t x){p[0]=uint8_t(x);p[1]=uint8_t(x>>8);}
void w32(uint8_t*p,uint32_t x){w16(p,uint16_t(x));w16(p+2,uint16_t(x>>16));}
void w64(uint8_t*p,uint64_t x){w32(p,uint32_t(x));w32(p+4,uint32_t(x>>32));}
}
Result projectToCobaltInfo(const QueryCandidate&q,CobaltQueryProjection&out,uint8_t*wire192,size_t wireLen){
    out={};
    if(wire192&&wireLen!=CobaltQueryInfoSize)return failure("cobalt_wire_size",Error::Bounds);
    uint8_t verifiedWire[QueryCandidateSize]{};
    Result r=encodeQuery(q,verifiedWire,sizeof(verifiedWire));
    if(!r.ok())return r;
    if(q.device.profile.family!=Asic::Family::Navi44||q.device.profile.target!=Asic::Target::Gfx1200)
        return failure("cobalt_target_not_navi44",Error::Mismatch);
    CobaltQueryProjection p{};
    p.abiVersion=1u;
    p.kextBuild=0u;
    p.flags=0u; // Never set N48N_INFO_NATIVE_BOOT or S1B_POSITIVE offline
    p.vmid=0u;
    if(q.device.present&1u){
        p.gcVersion=(uint32_t(q.device.gcMajor)<<16)|(uint32_t(q.device.gcMinor)<<8)|uint32_t(q.device.gcRevision);
    }
    if(q.device.present&2u){
        p.gbAddrConfig=q.device.gbAddrConfig;
    }
    if(q.device.present&4u){
        p.vramVisTotal=q.device.visibleBarBytes;
        p.vramVisFree=0u; // Offline projection never advertises allocatable VRAM pool
        p.vramHiTotal=q.device.vramBytes>q.device.visibleBarBytes?(q.device.vramBytes-q.device.visibleBarBytes):0u;
        p.vramHiFree=0u;
    }
    p.vaLowFirst=0x10000ULL;
    p.vaLowLast=0x7FFFFFFFFFFFULL;
    p.vaHighFirst=0xFFFF800000000000ULL;
    p.vaHighLast=0xFFFFFFFFFFFFFFFFULL;
    p.vendorId=q.device.profile.vendor;
    p.deviceId=q.device.profile.device;
    p.gfxTarget=uint16_t(q.device.profile.target);
    p.revisionId=q.device.profile.revisionKnown?q.device.profile.revision:0u;
    p.provenance=uint8_t(q.provenance);
    p.presenceMask=q.device.present;
    p.ownerPolicy=1u;
    p.generation=q.generation;
    if(wire192){
        uint8_t raw[CobaltQueryInfoSize]{};
        w32(raw+0,p.abiVersion);w32(raw+4,p.kextBuild);w32(raw+8,p.flags);w32(raw+12,p.vmid);
        w32(raw+16,p.gbAddrConfig);w32(raw+20,p.gcVersion);w32(raw+24,p.ringSizeDw);w32(raw+28,p.maxIbs);
        w64(raw+32,p.vramVisTotal);w64(raw+40,p.vramVisFree);w64(raw+48,p.vramHiTotal);w64(raw+56,p.vramHiFree);
        w64(raw+64,p.gttCap);w64(raw+72,p.gttUsed);w64(raw+80,p.gttMaxBo);
        w64(raw+88,p.ptCap);w64(raw+96,p.ptUsed);
        w64(raw+104,p.seqEmitted);w64(raw+112,p.seqRetired);
        w64(raw+120,p.vaLowFirst);w64(raw+128,p.vaLowLast);
        w64(raw+136,p.vaHighFirst);w64(raw+144,p.vaHighLast);
        w32(raw+152,p.maxBos);w32(raw+156,p.fenceSlots);
        // Reserved[0..7] at offsets 160..191 carry explicit Navi44 candidate tags:
        // [0]: 'N','4','4','P' (0x5034344E LE)
        // [1]: vendorId (16) | deviceId (16)
        // [2]: gfxTarget (16) | revisionId (8) | provenance (8)
        // [3]: presenceMask
        // [4]: ownerPolicy
        // [5..6]: generation (64-bit LE)
        // [7]: 0 (must remain zero)
        raw[160]='N';raw[161]='4';raw[162]='4';raw[163]='P';
        w16(raw+164,p.vendorId);w16(raw+166,p.deviceId);
        w16(raw+168,p.gfxTarget);raw[170]=p.revisionId;raw[171]=p.provenance;
        w32(raw+172,p.presenceMask);
        w32(raw+176,p.ownerPolicy);
        w64(raw+180,p.generation);
        w32(raw+188,0u);
        for(size_t i=0;i<CobaltQueryInfoSize;++i)wire192[i]=raw[i];
    }
    out=p;return success();
}
Result decodeCobaltProjection(View v,CobaltQueryProjection&out){
    out={};
    if(!v.data||v.size!=CobaltQueryInfoSize)return failure("cobalt_wire_size",Error::Bounds);
    const uint8_t*d=v.data;
    if(d[160]!='N'||d[161]!='4'||d[162]!='4'||d[163]!='P')return failure("cobalt_projection_magic",Error::Format);
    if(u32(d+0)!=1u||u32(d+8)!=0u||u32(d+188)!=0u||u32(d+176)!=1u)return failure("cobalt_projection_header",Error::Protocol);
    if(u64(d+40)!=0u||u64(d+56)!=0u)return failure("cobalt_offline_free_pool_nonzero",Error::Protocol);
    const uint16_t vendor=u16(d+164),device=u16(d+166),target=u16(d+168);
    const uint8_t rev=d[170],prov=d[171];
    if(vendor!=0x1002||device!=0x7590||target!=uint16_t(Asic::Target::Gfx1200)||prov==0||prov>2)
        return failure("cobalt_projection_identity",Error::Mismatch);
    const uint32_t present=u32(d+172);
    if(present&~7u)return failure("cobalt_projection_presence",Error::Format);
    const uint32_t gc=u32(d+20),gb=u32(d+16);
    const uint64_t vis=u64(d+32),hi=u64(d+48),gen=u64(d+180);
    if(!gen)return failure("cobalt_projection_generation",Error::Protocol);
    if((present&1u)?(gc!=((12u<<16)|(0u<<8)|0u)):(gc!=0u))return failure("cobalt_projection_gc",Error::Mismatch);
    if((present&2u)?(gb==0u):(gb!=0u))return failure("cobalt_projection_topology",Error::Mismatch);
    if((present&4u)?(vis==0u):(vis!=0u||hi!=0u))return failure("cobalt_projection_memory",Error::Mismatch);
    out.abiVersion=u32(d+0);out.kextBuild=u32(d+4);out.flags=u32(d+8);out.vmid=u32(d+12);
    out.gbAddrConfig=gb;out.gcVersion=gc;out.ringSizeDw=u32(d+24);out.maxIbs=u32(d+28);
    out.vramVisTotal=vis;out.vramVisFree=0u;out.vramHiTotal=hi;out.vramHiFree=0u;
    out.vaLowFirst=u64(d+120);out.vaLowLast=u64(d+128);
    out.vaHighFirst=u64(d+136);out.vaHighLast=u64(d+144);
    out.vendorId=vendor;out.deviceId=device;out.gfxTarget=target;
    out.revisionId=rev;out.provenance=prov;out.presenceMask=present;
    out.ownerPolicy=1u;out.generation=gen;
    return success();
}
}
