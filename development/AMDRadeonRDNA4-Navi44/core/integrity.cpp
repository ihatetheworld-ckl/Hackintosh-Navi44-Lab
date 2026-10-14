#include "integrity.hpp"
namespace NaviCore {
Result payloadChecksum(View v,uint32_t expected,CrcConvention convention,Integrity&out){
    out={};if(convention!=CrcConvention::IsoHdlc)return failure("crc_convention_unverified",Error::Unsupported);
    if(!v.inside(0,v.size)||v.size>(16u<<20))return failure("crc_payload_budget",Error::Budget);
    uint32_t crc=0xffffffff;
    for(size_t i=0;i<v.size;++i){crc^=v.data[i];for(unsigned b=0;b<8;++b)crc=(crc>>1)^((crc&1)?0xedb88320u:0u);}
    const uint32_t computed=crc^0xffffffff;
    if(computed!=expected)return failure("crc_mismatch",Error::Mismatch);
    out={computed,true,false,false};return success();
}
}
