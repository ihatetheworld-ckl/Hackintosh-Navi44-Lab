// M7 compatibility adapter, BSD-3-Clause. No STL/throw/RTTI.
#include "offlinevalidation.hpp"
#include "../host/validation_adapter.hpp"
bool Offline::elf(const uint8_t*d,size_t n,Asic::Target t,const char**why){
    NaviHost::MetadataBuffer storage;
    return NaviHost::result(NaviCore::elf({d,n},t,storage.scratch),why);
}
bool Offline::elfKernel(const uint8_t*d,size_t n,Asic::Target t,const char*name,const char**why){
    if(!name||!*name){if(why)*why="elf_kernel_metadata_missing";return false;}
    NaviHost::MetadataBuffer storage;
    return NaviHost::result(NaviCore::elf({d,n},t,storage.scratch,NaviHost::text(name)),why);
}
bool Offline::firmware(const uint8_t*d,size_t n,uint16_t a,uint16_t b,const char*c,const char**why){
    return NaviHost::result(NaviCore::firmware({d,n},a,b,NaviHost::text(c)),why);
}
bool Offline::deviceInfo(const uint8_t*d,size_t n,Asic::Profile&out,const char**why){
    return NaviHost::result(NaviCore::deviceInfo({d,n},out),why);
}
bool Offline::firmwareRequirements(const Asic::Profile&p,const IpDiscovery&d,
                                  FirmwareRequirement (&out)[16],size_t&count,const char**why){
    return NaviHost::result(NaviCore::firmwareRequirements(p,d,out,count),why);
}
