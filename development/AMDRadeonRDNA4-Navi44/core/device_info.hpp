// N44I v2 pure serialization model; NOT Cobalt production ABI. BSD-3-Clause.
#ifndef Navi44CoreDeviceInfo_hpp
#define Navi44CoreDeviceInfo_hpp
#include "validation.hpp"
namespace NaviCore {
struct DeviceInfo {
    Asic::Profile profile;
    uint32_t present; // field presence, NOT hardware verification or capability
    uint8_t gcMajor,gcMinor,gcRevision;
    uint32_t se,cu,rb,tcc,gbAddrConfig;
    uint64_t vramBytes,visibleBarBytes;
};
constexpr size_t kDeviceInfoSize=96;
Result decodeDeviceInfo(View,DeviceInfo&);
Result encodeDeviceInfo(const DeviceInfo&,uint8_t*,size_t);
}
#endif
