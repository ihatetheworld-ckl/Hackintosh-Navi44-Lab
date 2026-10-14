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
}
