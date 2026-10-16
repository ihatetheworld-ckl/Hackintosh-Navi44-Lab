#include "displayid.hpp"
namespace NaviDisplay {
using namespace NaviCore;
Result displayIdSection(View input,DisplayIdSection&out){
    out={};if(!input.data||input.size!=128)return failure("displayid_extension_size",Error::Bounds);
    const auto*d=input.data;const uintptr_t p=reinterpret_cast<uintptr_t>(d);
    if(127>UINTPTR_MAX-p)return failure("displayid_address",Error::Bounds);
    if(d[0]!=0x70)return failure("displayid_extension_tag",Error::Unsupported);
    if(d[1]!=0x12&&d[1]!=0x13&&d[1]!=0x20)return failure("displayid_version",Error::Unsupported);
    if(d[4])return failure("displayid_continuation",Error::Unsupported);
    const size_t end=5+size_t(d[2]);if(end>=127)return failure("displayid_section_bounds",Error::Bounds);
    unsigned outer=0,inner=0;for(size_t i=0;i<128;++i)outer+=d[i];
    for(size_t i=1;i<=end;++i)inner+=d[i];
    if((outer&255)||(inner&255))return failure("displayid_checksum");
    for(size_t i=end+1;i<127;++i)if(d[i])return failure("displayid_padding",Error::Unsupported);
    DisplayIdSection result{};result.version=d[1];result.primaryUse=d[3];
    if((d[1]==0x20&&d[3]>8)||(d[1]!=0x20&&d[3]>6))return failure("displayid_primary_use",Error::Unsupported);
    for(size_t at=5;at<end;){
        if(end-at<3||size_t(d[at+2])>end-at-3)return failure("displayid_block_bounds",Error::Bounds,at);
        if(result.count==32)return failure("displayid_block_budget",Error::Budget,at);
        result.blocks[result.count++]={d[at],d[at+1],d[at+2],static_cast<uint16_t>(at)};
        at+=3+size_t(d[at+2]);
    }
    out=result;return success();
}
}
