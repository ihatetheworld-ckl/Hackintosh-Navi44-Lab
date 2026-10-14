// Host-only bounded scratch convenience. Core owns no heap or OS resources.
#ifndef Navi44HostValidationAdapter_hpp
#define Navi44HostValidationAdapter_hpp
#include "../core/validation.hpp"
namespace NaviHost {
struct MetadataBuffer {
    NaviCore::Node nodes[512];
    NaviCore::Scratch scratch {nodes,512,0};
};
inline NaviCore::View text(const char*s) {
    if(!s)return {nullptr,0};size_t n=0;
    // Legacy C-string contract; future Core callers use length-qualified View.
    while(n<128&&s[n])++n;
    return {reinterpret_cast<const uint8_t*>(s),n};
}
inline bool result(NaviCore::Result r,const char**why){if(why)*why=r.detail;return r.ok();}
}
#endif
